"""Align registered team names with the names FPL actually shows.

A roster is typed by hand from a spreadsheet, so a name can differ from the one
FPL holds by a space, a capital letter or a zero typed as an "o". Before the
season starts those are transcription errors and FPL is right: it is the name
every manager sees in the game.

Once the season is under way the same difference means something else. The
rulebook forbids changing a team name mid-season, so a mismatch is evidence of
a violation and overwriting it would destroy that evidence. This command
therefore refuses to write after the first Gameweek is finalized unless it is
told to, and says why.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.cli.runner import configure_console
from vmf_api.cli.runner import run as run_async
from vmf_api.core.config import get_settings
from vmf_api.core.errors import NotFoundError, RuleValidationError
from vmf_api.db.session import get_engine, get_session_factory
from vmf_api.integrations.fpl import FPLClient, FPLClientError, HttpFPLClient
from vmf_api.integrations.fpl_parsers import SchemaQuarantineError, parse_entry
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import ManagerStatus
from vmf_api.models.manager import Manager, ManagerExternalProfile


@dataclass(frozen=True, slots=True)
class Rename:
    fpl_entry_id: int
    manager_name: str
    registered: str
    on_fpl: str


@dataclass(frozen=True, slots=True)
class SyncResult:
    checked: int
    matched: int
    renames: tuple[Rename, ...]
    unreachable: tuple[str, ...]
    applied: int
    dry_run: bool
    season_started: bool


async def _first_gameweek_finalized(session: AsyncSession, season_code: str) -> bool:
    season = await session.scalar(select(Season).where(Season.fpl_season_code == season_code))
    if season is None:
        raise NotFoundError(f"season {season_code!r} not found")
    gameweek = await session.scalar(
        select(Gameweek).where(Gameweek.season_id == season.id, Gameweek.number == 1)
    )
    return bool(gameweek and gameweek.is_finalized)


async def sync_team_names(
    session: AsyncSession,
    client: FPLClient,
    *,
    season_code: str,
    dry_run: bool = True,
    allow_after_kickoff: bool = False,
) -> SyncResult:
    started = await _first_gameweek_finalized(session, season_code)
    if started and not dry_run and not allow_after_kickoff:
        raise RuleValidationError(
            "GW1 is finalized, so a differing team name is a rulebook matter and "
            "not a typo; overwriting it would erase the evidence. Pass "
            "--allow-after-kickoff only with an organiser decision behind it"
        )

    managers = list(
        (
            await session.scalars(
                select(Manager)
                .where(Manager.active_status.not_in([ManagerStatus.DELETED]))
                .order_by(Manager.id)
            )
        )
        .unique()
        .all()
    )

    renames: list[Rename] = []
    unreachable: list[str] = []
    matched = 0

    for manager in managers:
        try:
            parsed = parse_entry(await client.entry(manager.fpl_entry_id))
        except (FPLClientError, SchemaQuarantineError) as error:
            unreachable.append(f"entry {manager.fpl_entry_id} could not be read ({error})")
            continue

        current = parsed.team_name
        if not current or current == manager.team_name:
            matched += 1
            continue

        renames.append(
            Rename(
                fpl_entry_id=manager.fpl_entry_id,
                manager_name=manager.manager_name,
                registered=manager.team_name,
                on_fpl=current,
            )
        )

        if dry_run:
            continue

        manager.team_name = current
        profile = await session.scalar(
            select(ManagerExternalProfile).where(ManagerExternalProfile.manager_id == manager.id)
        )
        if profile is not None:
            profile.current_team_name = current
            # The names now agree, so nothing is outstanding for review.
            profile.team_name_changed = False

    if not dry_run:
        await session.flush()

    return SyncResult(
        checked=len(managers),
        matched=matched,
        renames=tuple(renames),
        unreachable=tuple(unreachable),
        applied=0 if dry_run else len(renames),
        dry_run=dry_run,
        season_started=started,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Adopt the team names FPL shows. Reports what would change unless --apply is given."
        )
    )
    parser.add_argument("--season-code", default=None, help='For example "2026/27".')
    parser.add_argument("--apply", action="store_true", help="Write the names.")
    parser.add_argument(
        "--allow-after-kickoff",
        action="store_true",
        help="Write even though GW1 is finalized. Only with an organiser "
        "decision: mid-season renames are a rulebook matter.",
    )
    return parser


async def _run(*, season_code: str, apply: bool, allow_after_kickoff: bool) -> SyncResult:
    settings = get_settings()
    engine = get_engine()
    client = HttpFPLClient(
        base_url=settings.fpl_base_url,
        timeout_seconds=settings.fpl_timeout_seconds,
        user_agent=settings.fpl_user_agent,
        max_attempts=settings.fpl_max_attempts,
        retry_base_delay_seconds=settings.fpl_retry_base_delay_seconds,
        response_max_bytes=settings.fpl_response_max_bytes,
    )
    try:
        async with get_session_factory()() as session:
            try:
                result = await sync_team_names(
                    session,
                    client,
                    season_code=season_code,
                    dry_run=not apply,
                    allow_after_kickoff=allow_after_kickoff,
                )
                if apply:
                    await session.commit()
                else:
                    await session.rollback()
                return result
            except Exception:
                await session.rollback()
                raise
    finally:
        await client.close()
        await engine.dispose()


def _report(result: SyncResult) -> None:
    mode = "DRY RUN, nothing written" if result.dry_run else "APPLIED"
    print(f"Team names: {mode}")
    print(f"  checked            {result.checked}")
    print(f"  already correct    {result.matched}")
    print(f"  differ from FPL    {len(result.renames)}")
    if result.season_started:
        print("  note: GW1 is finalized; a differing name is a rulebook matter.")

    for rename in result.renames:
        print()
        print(f"  {rename.manager_name}  (entry {rename.fpl_entry_id})")
        print(f'    registered  "{rename.registered}"')
        print(f'    on FPL      "{rename.on_fpl}"')

    for problem in result.unreachable:
        print(f"  warning: {problem}")

    if result.dry_run and result.renames:
        print("\nRe-run with --apply to adopt the FPL names.")


def main(argv: Sequence[str] | None = None) -> int:
    configure_console()
    args = build_parser().parse_args(argv)
    season_code = args.season_code or get_settings().active_season_code

    try:
        result = run_async(
            _run(
                season_code=season_code,
                apply=args.apply,
                allow_after_kickoff=args.allow_after_kickoff,
            )
        )
    except (RuleValidationError, NotFoundError, ValueError) as error:
        print(f"Sync aborted: {error}", file=sys.stderr)
        return 2

    _report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
