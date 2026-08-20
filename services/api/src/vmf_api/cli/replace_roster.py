"""Swap a placeholder roster for the real one, before a ball is kicked.

A league is seeded with stand-in managers so the site can be built and checked
against something. Replacing them is a one-time operation and a destructive
one: managers, their division memberships and the whole H2H schedule go, and
the real roster is imported in their place.

The safety rail is that this refuses to remove a manager who has played. If a
Gameweek score, a settled H2H result, a violation or a Cup tie exists for
someone, this command stops and names them rather than deleting evidence. That
makes it safe to run against production before GW1 and impossible to run by
accident after it.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.cli.import_managers import (
    RosterEntry,
    RosterError,
    check_roster_shape,
    import_roster,
    parse_roster,
    read_csv,
)
from vmf_api.cli.runner import configure_console
from vmf_api.cli.runner import run as run_async
from vmf_api.core.config import get_settings
from vmf_api.db.session import get_engine, get_session_factory
from vmf_api.integrations.fpl import HttpFPLClient
from vmf_api.models.competition import DivisionMembership, Season
from vmf_api.models.cup import CupCompetition, CupMatch, CupRound
from vmf_api.models.governance import Violation, ViolationThresholdAction
from vmf_api.models.h2h import H2HMatch, H2HPenalty, H2HSchedule
from vmf_api.models.manager import Manager, ManagerExternalProfile
from vmf_api.models.scoring import ManagerGameweekScore


@dataclass(frozen=True, slots=True)
class ReplacementPlan:
    keep: tuple[int, ...]
    remove: tuple[tuple[int, int, str], ...]
    add: tuple[int, ...]
    schedules_removed: int
    matches_removed: int
    cups_removed: int
    #: Managers who cannot be removed because they hold competition data.
    blocked: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReplacementResult:
    plan: ReplacementPlan
    managers_deleted: int = 0
    managers_created: int = 0
    memberships_created: int = 0
    verified: int = 0
    warnings: tuple[str, ...] = ()
    dry_run: bool = True
    committed: bool = False


@dataclass
class _Evidence:
    """What a manager has done, which is what makes them undeletable."""

    scores: int = 0
    played_matches: int = 0
    violations: int = 0
    cup_ties: int = 0
    penalties: int = 0

    @property
    def has_any(self) -> bool:
        return bool(
            self.scores or self.played_matches or self.violations or self.cup_ties or self.penalties
        )

    def describe(self) -> str:
        parts: list[str] = []
        for count, noun in (
            (self.scores, "Gameweek score"),
            (self.played_matches, "played H2H match"),
            (self.violations, "violation"),
            (self.cup_ties, "Cup tie"),
            (self.penalties, "H2H penalty"),
        ):
            if count:
                parts.append(f"{count} {noun}{'s' if count != 1 else ''}")
        return ", ".join(parts)


async def _evidence_for(session: AsyncSession, manager_ids: Sequence[int]) -> dict[int, _Evidence]:
    evidence: dict[int, _Evidence] = {manager_id: _Evidence() for manager_id in manager_ids}
    if not manager_ids:
        return evidence

    async def tally(statement, attribute: str) -> None:
        for manager_id, count in (await session.execute(statement)).all():
            if manager_id in evidence:
                setattr(evidence[manager_id], attribute, count)

    await tally(
        select(ManagerGameweekScore.manager_id, func.count())
        .where(ManagerGameweekScore.manager_id.in_(manager_ids))
        .group_by(ManagerGameweekScore.manager_id),
        "scores",
    )
    await tally(
        select(Violation.manager_id, func.count())
        .where(Violation.manager_id.in_(manager_ids))
        .group_by(Violation.manager_id),
        "violations",
    )
    await tally(
        select(H2HPenalty.manager_id, func.count())
        .where(H2HPenalty.manager_id.in_(manager_ids))
        .group_by(H2HPenalty.manager_id),
        "penalties",
    )

    # A scheduled match nobody has played is not evidence; a scored one is.
    for column in (H2HMatch.home_manager_id, H2HMatch.away_manager_id):
        rows = (
            await session.execute(
                select(column, func.count())
                .where(
                    column.in_(manager_ids),
                    (H2HMatch.home_score.is_not(None)) | (H2HMatch.away_score.is_not(None)),
                )
                .group_by(column)
            )
        ).all()
        for manager_id, count in rows:
            if manager_id in evidence:
                evidence[manager_id].played_matches += count

    for column in (CupMatch.manager_a_id, CupMatch.manager_b_id):
        rows = (
            await session.execute(
                select(column, func.count()).where(column.in_(manager_ids)).group_by(column)
            )
        ).all()
        for manager_id, count in rows:
            if manager_id is not None and manager_id in evidence:
                evidence[manager_id].cup_ties += count

    return evidence


async def plan_replacement(
    session: AsyncSession,
    entries: Sequence[RosterEntry],
    *,
    season_code: str,
) -> ReplacementPlan:
    """Work out what would change, without changing anything."""

    season = await session.scalar(select(Season).where(Season.fpl_season_code == season_code))
    if season is None:
        raise RosterError(f"season {season_code!r} has not been bootstrapped")

    wanted = {entry.fpl_entry_id for entry in entries}
    current = list((await session.scalars(select(Manager))).unique().all())
    keep = [manager.id for manager in current if manager.fpl_entry_id in wanted]
    obsolete = [manager for manager in current if manager.fpl_entry_id not in wanted]

    evidence = await _evidence_for(session, [manager.id for manager in obsolete])
    blocked = tuple(
        f"{manager.manager_name} (entry {manager.fpl_entry_id}) has "
        f"{evidence[manager.id].describe()}"
        for manager in obsolete
        if evidence[manager.id].has_any
    )

    present = {manager.fpl_entry_id for manager in current}
    schedules = list(
        (await session.scalars(select(H2HSchedule).where(H2HSchedule.season_id == season.id)))
        .unique()
        .all()
    )
    match_count = 0
    if schedules:
        match_count = (
            await session.scalar(
                select(func.count()).where(
                    H2HMatch.schedule_id.in_([schedule.id for schedule in schedules])
                )
            )
        ) or 0
    cup_count = (
        await session.scalar(select(func.count()).where(CupCompetition.season_id == season.id))
    ) or 0

    return ReplacementPlan(
        keep=tuple(keep),
        remove=tuple(
            (manager.id, manager.fpl_entry_id, manager.manager_name) for manager in obsolete
        ),
        add=tuple(entry.fpl_entry_id for entry in entries if entry.fpl_entry_id not in present),
        schedules_removed=len(schedules),
        matches_removed=match_count,
        cups_removed=cup_count,
        blocked=blocked,
    )


async def replace_roster(
    session: AsyncSession,
    entries: Sequence[RosterEntry],
    *,
    season_code: str,
    client: HttpFPLClient | None = None,
    dry_run: bool = True,
) -> ReplacementResult:
    """Remove the outgoing managers and import the incoming roster."""

    plan = await plan_replacement(session, entries, season_code=season_code)
    if plan.blocked:
        raise RosterError(
            "these managers have competition data and will not be deleted:\n  "
            + "\n  ".join(plan.blocked)
            + "\n  the season has started; correct the roster by hand instead"
        )

    if dry_run:
        outcome = await import_roster(
            session,
            entries,
            season_code=season_code,
            client=None,
            dry_run=True,
        )
        return ReplacementResult(plan=plan, dry_run=True, verified=outcome.verified)

    season = await session.scalar(select(Season).where(Season.fpl_season_code == season_code))
    assert season is not None  # plan_replacement has already checked

    # The schedule is built from the roster, so it cannot outlive it. It also
    # holds the foreign keys that would otherwise block the deletes below.
    schedule_ids = list(
        await session.scalars(select(H2HSchedule.id).where(H2HSchedule.season_id == season.id))
    )
    if schedule_ids:
        await session.execute(delete(H2HMatch).where(H2HMatch.schedule_id.in_(schedule_ids)))
        await session.execute(delete(H2HSchedule).where(H2HSchedule.id.in_(schedule_ids)))

    cup_ids = list(
        await session.scalars(
            select(CupCompetition.id).where(CupCompetition.season_id == season.id)
        )
    )
    if cup_ids:
        round_ids = list(
            await session.scalars(
                select(CupRound.id).where(CupRound.cup_competition_id.in_(cup_ids))
            )
        )
        if round_ids:
            await session.execute(delete(CupMatch).where(CupMatch.cup_round_id.in_(round_ids)))
            await session.execute(delete(CupRound).where(CupRound.id.in_(round_ids)))
        await session.execute(delete(CupCompetition).where(CupCompetition.id.in_(cup_ids)))

    removed_ids = [manager_id for manager_id, _, _ in plan.remove]
    if removed_ids:
        for model in (
            ManagerGameweekScore,
            ViolationThresholdAction,
            Violation,
            H2HPenalty,
            DivisionMembership,
            ManagerExternalProfile,
        ):
            await session.execute(delete(model).where(model.manager_id.in_(removed_ids)))
        await session.execute(delete(Manager).where(Manager.id.in_(removed_ids)))
    await session.flush()

    outcome = await import_roster(
        session,
        entries,
        season_code=season_code,
        client=client,
        dry_run=False,
    )
    return ReplacementResult(
        plan=plan,
        managers_deleted=len(removed_ids),
        managers_created=outcome.created,
        memberships_created=outcome.memberships_created,
        verified=outcome.verified,
        warnings=outcome.warnings,
        dry_run=False,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replace a placeholder roster with the real one. Reports what would "
            "change unless --apply is given, and refuses to delete a manager who "
            "has already played."
        )
    )
    parser.add_argument("--file", required=True, type=Path, help="Path to the roster CSV.")
    parser.add_argument("--season-code", required=True, help='For example "2026/27".')
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the change. Without this the command only reports.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip the FPL check on each entry id. Offline testing only.",
    )
    return parser


async def _run(
    *,
    path: Path,
    season_code: str,
    apply: bool,
    verify: bool,
) -> ReplacementResult:
    entries, errors = parse_roster(read_csv(path))
    if errors:
        raise RosterError(f"{path} has invalid rows:\n  " + "\n  ".join(errors))

    problems = check_roster_shape(entries)
    if problems:
        raise RosterError(
            "the roster does not match the rulebook structure:\n  " + "\n  ".join(problems)
        )

    settings = get_settings()
    engine = get_engine()
    client: HttpFPLClient | None = None
    try:
        if verify and apply:
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
                result = await replace_roster(
                    session,
                    entries,
                    season_code=season_code,
                    client=client,
                    dry_run=not apply,
                )
                if apply:
                    await session.commit()
                    result = ReplacementResult(**{**result.__dict__, "committed": True})
                else:
                    await session.rollback()
                return result
            except Exception:
                await session.rollback()
                raise
    finally:
        if client is not None:
            await client.close()
        await engine.dispose()


def _report(result: ReplacementResult) -> None:
    plan = result.plan
    mode = "APPLIED" if result.committed else "DRY RUN, nothing written"
    print(f"Roster replacement: {mode}")
    print(f"  managers kept          {len(plan.keep)}")
    print(f"  managers removed       {len(plan.remove)}")
    print(f"  managers added         {len(plan.add)}")
    print(f"  H2H schedules removed  {plan.schedules_removed} ({plan.matches_removed} matches)")
    print(f"  Cups removed           {plan.cups_removed}")
    if result.committed:
        print(f"  memberships created    {result.memberships_created}")
        print(f"  entries verified       {result.verified}")
    for warning in result.warnings:
        print(f"  warning: {warning}")
    if not result.committed:
        print("\nRe-run with --apply to write it.")
    else:
        print("\nNext: regenerate the H2H schedule for the new roster.")


def main(argv: Sequence[str] | None = None) -> int:
    configure_console()
    args = build_parser().parse_args(argv)
    try:
        result = run_async(
            _run(
                path=args.file,
                season_code=args.season_code,
                apply=args.apply,
                verify=not args.no_verify,
            )
        )
    except (RosterError, ValueError) as error:
        print(f"Replacement aborted: {error}", file=sys.stderr)
        return 2

    _report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
