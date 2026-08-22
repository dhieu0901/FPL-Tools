"""Adopt the head-to-head draw FPL made, in place of the generated one.

A schedule has to exist before the season starts so the site has fixtures to
show, and before the first deadline FPL has not drawn one: the league is still
open and the field is not final. So VMF generates a round robin of its own to
run on.

The moment the league closes, FPL publishes the real draw, and the two
disagree. Only FPL's version decides who a manager actually plays, because
that is the fixture list every manager sees inside the game. Running on the
generated one past that point means the site quietly shows the wrong opponent
for the rest of the season.

Only the pairings are taken. Scores stay this league's own: FPL does not know
about transfer-cost violations, penalties or walkovers, and letting its
figures land here would overwrite results computed to the rulebook.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.cli.runner import configure_console
from vmf_api.cli.runner import run as run_async
from vmf_api.core.config import get_settings
from vmf_api.core.errors import NotFoundError, RuleValidationError
from vmf_api.db.session import get_engine, get_session_factory
from vmf_api.integrations.fpl import FPLClient, FPLClientError, HttpFPLClient
from vmf_api.integrations.fpl_parsers import (
    ParsedH2HMatch,
    SchemaQuarantineError,
    parse_h2h_matches,
)
from vmf_api.models.enums import ManagerStatus, MatchStatus
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.manager import Manager

#: FPL paginates the draw. This is a stop rather than an expectation; a
#: 46-manager season is eight pages, and the guard is for a loop that never
#: reports the last page.
MAX_PAGES = 60


@dataclass(frozen=True, slots=True)
class ImportResult:
    schedule_id: int
    league_id: int
    fetched: int
    gameweeks: tuple[int, ...]
    written: int
    removed: int
    unchanged: int
    changed_pairings: tuple[str, ...]
    unknown_entries: tuple[int, ...]
    dry_run: bool


async def _fetch_draw(client: FPLClient, league_id: int) -> tuple[ParsedH2HMatch, ...]:
    drawn: list[ParsedH2HMatch] = []
    page = 1
    while page <= MAX_PAGES:
        payload = await client.h2h_matches(league_id, page=page)
        matches, has_next = parse_h2h_matches(payload)
        drawn.extend(matches)
        if not has_next:
            return tuple(drawn)
        page += 1
    raise RuleValidationError(
        f"league {league_id} reported more than {MAX_PAGES} pages of fixtures"
    )


async def import_h2h_schedule(
    session: AsyncSession,
    client: FPLClient,
    *,
    league_id: int,
    schedule_id: int,
    dry_run: bool = True,
    allow_settled: bool = False,
) -> ImportResult:
    schedule = await session.get(H2HSchedule, schedule_id)
    if schedule is None:
        raise NotFoundError(f"h2h schedule {schedule_id} not found")

    drawn = await _fetch_draw(client, league_id)
    if not drawn:
        raise RuleValidationError(
            f"league {league_id} has no fixtures yet. FPL draws them when the league "
            "closes at the first deadline, not before"
        )

    managers = {
        manager.fpl_entry_id: manager
        for manager in (
            await session.scalars(
                select(Manager).where(Manager.active_status.not_in([ManagerStatus.DELETED]))
            )
        )
        .unique()
        .all()
    }
    unknown = sorted(
        {
            entry
            for match in drawn
            for entry in (match.home_entry_id, match.away_entry_id)
            if entry not in managers
        }
    )
    if unknown:
        raise RuleValidationError(
            "the draw contains FPL entries that are not on the roster: "
            + ", ".join(str(entry) for entry in unknown)
            + ". Import the roster before the schedule"
        )

    existing = list(
        await session.scalars(select(H2HMatch).where(H2HMatch.schedule_id == schedule_id))
    )
    settled = [match for match in existing if match.status is MatchStatus.FINAL]
    if settled and not allow_settled:
        raise RuleValidationError(
            f"{len(settled)} match(es) in this schedule are already final. Replacing the "
            "draw would discard settled results; pass --allow-settled only with an "
            "organiser decision behind it"
        )

    # A tie is the same tie whichever way round FPL happens to list it, so the
    # comparison is order-insensitive; only a genuinely different opponent
    # counts as a change.
    def pairing(home_id: int, away_id: int) -> frozenset[int]:
        return frozenset((home_id, away_id))

    before = {
        (match.gameweek_number, pairing(match.home_manager_id, match.away_manager_id))
        for match in existing
    }
    planned = [
        (
            match.gameweek_number,
            managers[match.home_entry_id].id,
            managers[match.away_entry_id].id,
            match.is_knockout,
        )
        for match in drawn
    ]
    after = {(gameweek, pairing(home, away)) for gameweek, home, away, _ in planned}

    by_id = {manager.id: manager for manager in managers.values()}
    changed = sorted(
        f"GW{gameweek}: "
        + " v ".join(sorted(by_id[manager_id].team_name for manager_id in sorted(pair)))
        for gameweek, pair in (after - before)
    )

    if not dry_run:
        await session.execute(delete(H2HMatch).where(H2HMatch.schedule_id == schedule_id))
        for gameweek, home_id, away_id, is_knockout in planned:
            session.add(
                H2HMatch(
                    schedule_id=schedule_id,
                    gameweek_number=gameweek,
                    home_manager_id=home_id,
                    away_manager_id=away_id,
                    status=MatchStatus.SCHEDULED,
                    is_playoff=is_knockout,
                )
            )
        await session.flush()

    return ImportResult(
        schedule_id=schedule_id,
        league_id=league_id,
        fetched=len(drawn),
        gameweeks=tuple(sorted({match.gameweek_number for match in drawn})),
        written=0 if dry_run else len(planned),
        removed=0 if dry_run else len(existing),
        unchanged=len(after & before),
        changed_pairings=tuple(changed),
        unknown_entries=(),
        dry_run=dry_run,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replace a schedule's fixtures with the draw FPL made for the league. "
            "Reports what would change unless --apply is given."
        )
    )
    parser.add_argument("--league-id", type=int, required=True, help="The FPL H2H league id.")
    parser.add_argument("--schedule-id", type=int, required=True, help="The VMF schedule to fill.")
    parser.add_argument("--apply", action="store_true", help="Write the fixtures.")
    parser.add_argument(
        "--allow-settled",
        action="store_true",
        help="Replace even though some matches are final. Discards settled results.",
    )
    return parser


async def _run(
    *, league_id: int, schedule_id: int, apply: bool, allow_settled: bool
) -> ImportResult:
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
                result = await import_h2h_schedule(
                    session,
                    client,
                    league_id=league_id,
                    schedule_id=schedule_id,
                    dry_run=not apply,
                    allow_settled=allow_settled,
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


def _report(result: ImportResult) -> None:
    mode = "DRY RUN, nothing written" if result.dry_run else "APPLIED"
    print(f"H2H draw from FPL league {result.league_id}: {mode}")
    print(f"  fixtures on FPL     {result.fetched}")
    if result.gameweeks:
        print(f"  gameweeks           GW{result.gameweeks[0]}-GW{result.gameweeks[-1]}")
    print(f"  already correct     {result.unchanged}")
    print(f"  different opponent  {len(result.changed_pairings)}")

    for line in result.changed_pairings[:12]:
        print(f"    {line}")
    if len(result.changed_pairings) > 12:
        print(f"    ... and {len(result.changed_pairings) - 12} more")

    if result.dry_run:
        print("\nRe-run with --apply to adopt FPL's draw.")
    else:
        print(f"\n  removed {result.removed}, wrote {result.written}")


def main(argv: Sequence[str] | None = None) -> int:
    configure_console()
    args = build_parser().parse_args(argv)

    try:
        result = run_async(
            _run(
                league_id=args.league_id,
                schedule_id=args.schedule_id,
                apply=args.apply,
                allow_settled=args.allow_settled,
            )
        )
    except (RuleValidationError, NotFoundError, FPLClientError, SchemaQuarantineError) as error:
        print(f"Import aborted: {error}", file=sys.stderr)
        return 2

    _report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
