"""Generate the head-to-head group stage from the confirmed roster.

The schedule is normally created through the admin API, but it is needed
exactly once per season and it is needed before the API is serving anything
useful. Doing it from the command line removes that ordering problem, and
means a season can be prepared against the database alone.

Nothing here decides fixtures: the circle method in ``domain/h2h_schedule``
produces them, and this command only checks the roster is the right shape,
writes the rounds, and refuses to touch a schedule that has already been
played.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.cli.runner import configure_console
from vmf_api.cli.runner import run as run_async
from vmf_api.core.config import get_settings
from vmf_api.core.errors import RuleValidationError
from vmf_api.db.session import get_engine, get_session_factory
from vmf_api.domain.h2h_schedule import generate_round_robin_schedule
from vmf_api.models.competition import Season
from vmf_api.models.enums import ManagerStatus, RegistrationStatus
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.manager import Manager

DEFAULT_ROUNDS = 35
DEFAULT_NAME = "H2H Group Stage"


@dataclass(frozen=True, slots=True)
class ScheduleResult:
    schedule_id: int | None
    name: str
    managers: int
    rounds: int
    matches: int
    replaced: int
    dry_run: bool


async def generate_schedule(
    session: AsyncSession,
    *,
    season_code: str,
    name: str = DEFAULT_NAME,
    rounds: int = DEFAULT_ROUNDS,
    start_gameweek: int = 1,
    expected_managers: int | None = None,
    replace: bool = False,
    dry_run: bool = True,
) -> ScheduleResult:
    season = await session.scalar(select(Season).where(Season.fpl_season_code == season_code))
    if season is None:
        raise RuleValidationError(f"season {season_code!r} has not been bootstrapped")

    managers = list(
        (
            await session.scalars(
                select(Manager)
                .where(
                    Manager.active_status == ManagerStatus.ACTIVE,
                    Manager.registration_status == RegistrationStatus.CONFIRMED,
                )
                .order_by(Manager.id)
            )
        )
        .unique()
        .all()
    )
    expected = expected_managers if expected_managers is not None else len(managers)
    if len(managers) != expected:
        raise RuleValidationError(
            f"expected {expected} confirmed active managers, found {len(managers)}"
        )
    if len(managers) < 2 or len(managers) % 2:
        raise RuleValidationError(
            f"an even number of at least two managers is required, found {len(managers)}"
        )

    existing = list(
        (await session.scalars(select(H2HSchedule).where(H2HSchedule.season_id == season.id)))
        .unique()
        .all()
    )
    replaced = 0
    if existing:
        played = (
            await session.scalar(
                select(func.count()).where(
                    H2HMatch.schedule_id.in_([item.id for item in existing]),
                    (H2HMatch.home_score.is_not(None)) | (H2HMatch.away_score.is_not(None)),
                )
            )
        ) or 0
        if played:
            raise RuleValidationError(
                f"{played} match(es) already carry a score; a played schedule is never regenerated"
            )
        if not replace:
            raise RuleValidationError(
                f"season {season_code!r} already has {len(existing)} schedule(s); "
                "pass --replace to discard and regenerate"
            )
        replaced = len(existing)

    plan = generate_round_robin_schedule(
        [manager.id for manager in managers],
        rounds=rounds,
        start_gameweek=start_gameweek,
    )
    match_total = sum(len(round_) for round_ in plan)

    if dry_run:
        return ScheduleResult(
            schedule_id=None,
            name=name,
            managers=len(managers),
            rounds=len(plan),
            matches=match_total,
            replaced=replaced,
            dry_run=True,
        )

    if existing:
        ids = [item.id for item in existing]
        await session.execute(delete(H2HMatch).where(H2HMatch.schedule_id.in_(ids)))
        await session.execute(delete(H2HSchedule).where(H2HSchedule.id.in_(ids)))

    schedule = H2HSchedule(season_id=season.id, name=name)
    session.add(schedule)
    await session.flush()
    for round_ in plan:
        for match in round_:
            session.add(
                H2HMatch(
                    schedule_id=schedule.id,
                    gameweek_number=match.round_number,
                    home_manager_id=match.home_manager_id,
                    away_manager_id=match.away_manager_id,
                )
            )
    await session.flush()

    return ScheduleResult(
        schedule_id=schedule.id,
        name=name,
        managers=len(managers),
        rounds=len(plan),
        matches=match_total,
        replaced=replaced,
        dry_run=False,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the H2H group stage for a season. Reports what it would "
            "write unless --apply is given."
        )
    )
    parser.add_argument("--season-code", required=True, help='For example "2026/27".')
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--start-gameweek", type=int, default=1)
    parser.add_argument(
        "--expect",
        type=int,
        default=None,
        help="Fail unless exactly this many managers are confirmed and active. "
        "Defaults to the configured roster size.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Discard an existing unplayed schedule and regenerate it.",
    )
    parser.add_argument("--apply", action="store_true", help="Write the schedule.")
    return parser


async def _run(
    *,
    season_code: str,
    name: str,
    rounds: int,
    start_gameweek: int,
    expect: int | None,
    replace: bool,
    apply: bool,
) -> ScheduleResult:
    engine = get_engine()
    try:
        async with get_session_factory()() as session:
            try:
                result = await generate_schedule(
                    session,
                    season_code=season_code,
                    name=name,
                    rounds=rounds,
                    start_gameweek=start_gameweek,
                    expected_managers=expect,
                    replace=replace,
                    dry_run=not apply,
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
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    configure_console()
    args = build_parser().parse_args(argv)
    expect = args.expect if args.expect is not None else get_settings().number_of_managers
    try:
        result = run_async(
            _run(
                season_code=args.season_code,
                name=args.name,
                rounds=args.rounds,
                start_gameweek=args.start_gameweek,
                expect=expect,
                replace=args.replace,
                apply=args.apply,
            )
        )
    except (RuleValidationError, ValueError) as error:
        print(f"Schedule aborted: {error}", file=sys.stderr)
        return 2

    mode = (
        "DRY RUN, nothing written" if result.dry_run else f"WRITTEN (schedule {result.schedule_id})"
    )
    print(f"H2H group stage: {mode}")
    print(f"  managers   {result.managers}")
    print(f"  rounds     {result.rounds}")
    print(f"  matches    {result.matches}")
    if result.replaced:
        print(f"  replaced   {result.replaced} previous schedule(s)")
    if result.dry_run:
        print("\nRe-run with --apply to write it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
