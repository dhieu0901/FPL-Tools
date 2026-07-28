"""Import the confirmed roster from a CSV file.

The roster is the one input the system cannot derive from FPL: which forty
people are in this league, and which division each of them starts in. Getting
an ``fpl_entry_id`` wrong is the expensive mistake, because the manager looks
present in every listing while their squad silently never synchronises, so the
importer checks each entry against FPL before writing anything.

The command is idempotent. Running it twice creates nothing the second time,
and a row that disagrees with an already imported manager is reported as a
conflict rather than quietly overwriting a decision someone made earlier.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.cli.runner import configure_console
from vmf_api.cli.runner import run as run_async
from vmf_api.core.config import get_settings
from vmf_api.db.session import get_engine, get_session_factory
from vmf_api.integrations.fpl import FPLClient, FPLClientError, HttpFPLClient
from vmf_api.integrations.fpl_parsers import SchemaQuarantineError, parse_entry
from vmf_api.models.competition import CompetitionPhase, DivisionMembership, Season
from vmf_api.models.enums import Division, ManagerStatus, PhaseType, RegistrationStatus
from vmf_api.models.manager import Manager, ManagerExternalProfile

REQUIRED_COLUMNS = ("fpl_entry_id", "manager_name", "team_name", "division")
OPTIONAL_COLUMNS = ("phone_number", "facebook_url")

MAXIMUM_NAME_LENGTH = 120

#: The rulebook fixes the league at forty managers in two divisions of twenty.
EXPECTED_TOTAL = 40
EXPECTED_PER_DIVISION = 20


@dataclass(frozen=True, slots=True)
class RosterEntry:
    line: int
    fpl_entry_id: int
    manager_name: str
    team_name: str
    division: Division
    phone_number: str | None = None
    facebook_url: str | None = None


@dataclass(frozen=True, slots=True)
class ImportResult:
    created: int = 0
    already_present: int = 0
    memberships_created: int = 0
    verified: int = 0
    conflicts: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    dry_run: bool = False


@dataclass
class _Verification:
    verified: int = 0
    unreachable: list[str] = field(default_factory=list)
    renamed: list[str] = field(default_factory=list)
    profiles: dict[int, tuple[str | None, str | None]] = field(default_factory=dict)


class RosterError(ValueError):
    """The file cannot be imported as written."""


def _clean(value: object) -> str:
    return str(value or "").strip()


def parse_roster(rows: Iterable[dict[str, str]]) -> tuple[list[RosterEntry], list[str]]:
    """Read the CSV rows into entries, collecting every problem found.

    Every row is checked before anything is reported, so one run of the command
    surfaces all the typos in a file instead of one per attempt.
    """

    entries: list[RosterEntry] = []
    errors: list[str] = []
    seen_entry_ids: dict[int, int] = {}

    for index, row in enumerate(rows, start=2):  # Line 1 is the header.
        normalized = {(key or "").strip().lower(): value for key, value in row.items()}
        missing = [column for column in REQUIRED_COLUMNS if not _clean(normalized.get(column))]
        if missing:
            errors.append(f"line {index}: missing {', '.join(missing)}")
            continue

        raw_entry_id = _clean(normalized["fpl_entry_id"])
        try:
            entry_id = int(raw_entry_id)
        except ValueError:
            errors.append(f"line {index}: fpl_entry_id {raw_entry_id!r} is not a number")
            continue
        if entry_id <= 0:
            errors.append(f"line {index}: fpl_entry_id must be positive")
            continue
        if entry_id in seen_entry_ids:
            errors.append(
                f"line {index}: fpl_entry_id {entry_id} already appears on "
                f"line {seen_entry_ids[entry_id]}"
            )
            continue

        raw_division = _clean(normalized["division"]).upper()
        try:
            division = Division(raw_division)
        except ValueError:
            errors.append(
                f"line {index}: division {raw_division!r} must be one of "
                f"{', '.join(item.value for item in Division)}"
            )
            continue

        manager_name = _clean(normalized["manager_name"])
        team_name = _clean(normalized["team_name"])
        too_long = [
            name
            for name, value in (("manager_name", manager_name), ("team_name", team_name))
            if len(value) > MAXIMUM_NAME_LENGTH
        ]
        if too_long:
            errors.append(
                f"line {index}: {', '.join(too_long)} exceeds {MAXIMUM_NAME_LENGTH} characters"
            )
            continue

        seen_entry_ids[entry_id] = index
        entries.append(
            RosterEntry(
                line=index,
                fpl_entry_id=entry_id,
                manager_name=manager_name,
                team_name=team_name,
                division=division,
                phone_number=_clean(normalized.get("phone_number")) or None,
                facebook_url=_clean(normalized.get("facebook_url")) or None,
            )
        )

    return entries, errors


def check_roster_shape(entries: Sequence[RosterEntry]) -> list[str]:
    """Report departures from the forty-manager, two-division structure."""

    problems: list[str] = []
    if len(entries) != EXPECTED_TOTAL:
        problems.append(f"expected {EXPECTED_TOTAL} managers, found {len(entries)}")
    counts = Counter(entry.division for entry in entries)
    for division in Division:
        found = counts.get(division, 0)
        if found != EXPECTED_PER_DIVISION:
            problems.append(
                f"division {division.value}: expected {EXPECTED_PER_DIVISION}, found {found}"
            )
    return problems


async def _verify_against_fpl(
    entries: Sequence[RosterEntry],
    client: FPLClient,
) -> _Verification:
    """Confirm each entry exists, and record the names FPL currently shows."""

    verification = _Verification()
    for entry in entries:
        try:
            payload = await client.entry(entry.fpl_entry_id)
            parsed = parse_entry(payload)
        except (FPLClientError, SchemaQuarantineError) as error:
            verification.unreachable.append(
                f"line {entry.line}: FPL entry {entry.fpl_entry_id} could not be read ({error})"
            )
            continue

        verification.verified += 1
        verification.profiles[entry.fpl_entry_id] = (parsed.manager_name, parsed.team_name)
        if parsed.team_name and parsed.team_name != entry.team_name:
            verification.renamed.append(
                f"line {entry.line}: entry {entry.fpl_entry_id} is registered as "
                f"{entry.team_name!r} but FPL shows {parsed.team_name!r}"
            )
    return verification


async def import_roster(
    session: AsyncSession,
    entries: Sequence[RosterEntry],
    *,
    season_code: str,
    client: FPLClient | None = None,
    dry_run: bool = False,
) -> ImportResult:
    """Create the managers and their opening division membership.

    The caller owns the transaction. Nothing is written when ``dry_run`` is set,
    which makes the command usable as a validator against the real database.
    """

    season = await session.scalar(select(Season).where(Season.fpl_season_code == season_code))
    if season is None:
        raise RosterError(f"season {season_code!r} has not been bootstrapped")

    phase = await session.scalar(
        select(CompetitionPhase).where(
            CompetitionPhase.season_id == season.id,
            CompetitionPhase.phase_type == PhaseType.CLASSIC_SEASON_1,
        )
    )
    if phase is None:
        raise RosterError(
            f"season {season_code!r} has no {PhaseType.CLASSIC_SEASON_1.value} phase; "
            "run vmf-bootstrap-season first"
        )

    verification = _Verification()
    if client is not None:
        verification = await _verify_against_fpl(entries, client)
        if verification.unreachable:
            # An unreadable entry means the whole file is suspect, and a
            # partially imported roster is harder to reason about than none.
            raise RosterError(
                "FPL could not confirm every entry:\n  " + "\n  ".join(verification.unreachable)
            )

    existing = {
        manager.fpl_entry_id: manager
        for manager in await session.scalars(
            select(Manager).where(
                Manager.fpl_entry_id.in_([entry.fpl_entry_id for entry in entries])
            )
        )
    }
    memberships = {
        manager_id
        for manager_id in await session.scalars(
            select(DivisionMembership.manager_id).where(
                DivisionMembership.competition_phase_id == phase.id
            )
        )
    }

    conflicts: list[str] = []
    created = 0
    already_present = 0
    memberships_created = 0

    for entry in entries:
        record = existing.get(entry.fpl_entry_id)

        # Counting is decided before any writing, so a dry run reports exactly
        # the numbers the real run would produce.
        if record is None:
            created += 1
            needs_membership = True
        else:
            already_present += 1
            needs_membership = record.id not in memberships
            if record.division != entry.division:
                conflicts.append(
                    f"line {entry.line}: entry {entry.fpl_entry_id} is already in "
                    f"{record.division.value} but the file says {entry.division.value}"
                )
        if needs_membership:
            memberships_created += 1

        if dry_run:
            continue

        if record is None:
            record = Manager(
                fpl_entry_id=entry.fpl_entry_id,
                manager_name=entry.manager_name,
                team_name=entry.team_name,
                phone_number=entry.phone_number,
                facebook_url=entry.facebook_url,
                division=entry.division,
                active_status=ManagerStatus.ACTIVE,
                registration_status=RegistrationStatus.CONFIRMED,
                season_joined=season_code,
            )
            session.add(record)
            await session.flush()

            names = verification.profiles.get(entry.fpl_entry_id)
            if names is not None:
                current_manager_name, current_team_name = names
                session.add(
                    ManagerExternalProfile(
                        manager_id=record.id,
                        current_manager_name=current_manager_name,
                        current_team_name=current_team_name,
                        team_name_changed=bool(
                            current_team_name and current_team_name != entry.team_name
                        ),
                    )
                )

        if needs_membership:
            session.add(
                DivisionMembership(
                    manager_id=record.id,
                    competition_phase_id=phase.id,
                    division=entry.division,
                    start_gameweek=phase.start_gameweek,
                    end_gameweek=phase.end_gameweek,
                )
            )

    if conflicts:
        raise RosterError(
            "the file disagrees with managers already imported:\n  " + "\n  ".join(conflicts)
        )

    if not dry_run:
        await session.flush()

    return ImportResult(
        created=created,
        already_present=already_present,
        memberships_created=memberships_created,
        verified=verification.verified,
        warnings=tuple(verification.renamed),
        dry_run=dry_run,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RosterError(f"{path} is empty")
        header = {(name or "").strip().lower() for name in reader.fieldnames}
        missing = [column for column in REQUIRED_COLUMNS if column not in header]
        if missing:
            raise RosterError(
                f"{path} is missing the column(s) {', '.join(missing)}; "
                f"required: {', '.join(REQUIRED_COLUMNS)}"
            )
        return list(reader)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import the confirmed roster from a CSV file with the columns "
            f"{', '.join(REQUIRED_COLUMNS)}"
            f" (optional: {', '.join(OPTIONAL_COLUMNS)})."
        )
    )
    parser.add_argument("--file", required=True, type=Path, help="Path to the roster CSV.")
    parser.add_argument(
        "--season-code",
        required=True,
        help='FPL season code, for example "2026/27".',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report without writing anything.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip the FPL check. Only for offline testing; a wrong entry id "
        "produces a manager whose squad never synchronises.",
    )
    parser.add_argument(
        "--allow-imbalance",
        action="store_true",
        help=f"Permit a roster that is not {EXPECTED_TOTAL} managers "
        f"split {EXPECTED_PER_DIVISION}/{EXPECTED_PER_DIVISION}.",
    )
    return parser


async def _run(
    *,
    path: Path,
    season_code: str,
    dry_run: bool,
    verify: bool,
    allow_imbalance: bool,
) -> ImportResult:
    entries, errors = parse_roster(read_csv(path))
    if errors:
        raise RosterError(f"{path} has invalid rows:\n  " + "\n  ".join(errors))
    if not entries:
        raise RosterError(f"{path} contains no rows")

    shape_problems = check_roster_shape(entries)
    if shape_problems and not allow_imbalance:
        raise RosterError(
            "the roster does not match the rulebook structure:\n  "
            + "\n  ".join(shape_problems)
            + "\n  pass --allow-imbalance to import anyway"
        )

    settings = get_settings()
    engine = get_engine()
    client: HttpFPLClient | None = None
    try:
        if verify:
            client = HttpFPLClient(
                base_url=settings.fpl_base_url,
                timeout_seconds=settings.fpl_timeout_seconds,
                user_agent=settings.fpl_user_agent,
                max_attempts=settings.fpl_max_attempts,
                retry_base_delay_seconds=settings.fpl_retry_base_delay_seconds,
                response_max_bytes=settings.fpl_response_max_bytes,
            )
        async with get_session_factory()() as session:
            try:
                result = await import_roster(
                    session,
                    entries,
                    season_code=season_code,
                    client=client,
                    dry_run=dry_run,
                )
                if dry_run:
                    await session.rollback()
                else:
                    await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
    finally:
        if client is not None:
            await client.close()
        await engine.dispose()


def _print_result(result: ImportResult, *, path: Path) -> None:
    prefix = "Would import" if result.dry_run else "Imported"
    print(f"{prefix} from {path}:")
    print(f"  managers created           : {result.created}")
    print(f"  already present            : {result.already_present}")
    print(f"  division memberships added : {result.memberships_created}")
    print(f"  confirmed against FPL      : {result.verified}")
    for warning in result.warnings:
        print(f"  note: {warning}")
    if result.dry_run:
        print("  nothing was written")


def main(argv: Sequence[str] | None = None) -> int:
    configure_console()
    args = build_parser().parse_args(argv)
    try:
        result = run_async(
            _run(
                path=args.file,
                season_code=args.season_code,
                dry_run=args.dry_run,
                verify=not args.no_verify,
                allow_imbalance=args.allow_imbalance,
            )
        )
    except (RosterError, ValueError) as error:
        print(f"Import aborted: {error}", file=sys.stderr)
        return 2

    _print_result(result, path=args.file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
