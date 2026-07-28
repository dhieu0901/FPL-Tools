from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.db.session import get_engine, get_session_factory
from vmf_api.models import CompetitionPhase, Gameweek, Season
from vmf_api.models.enums import PhaseType, SeasonStatus

FIRST_GAMEWEEK = 1
LAST_GAMEWEEK = 38


@dataclass(frozen=True, slots=True)
class PhaseDefinition:
    phase_type: PhaseType
    name: str
    start_gameweek: int
    end_gameweek: int


# These ranges are fixed by docs/RULEBOOK.md for 2026/27. A Cup phase covers
# both its qualification ledger and its explicitly scheduled knockout rounds.
PHASE_DEFINITIONS: tuple[PhaseDefinition, ...] = (
    PhaseDefinition(PhaseType.CLASSIC_SEASON_1, "Classic Season 1", 1, 19),
    PhaseDefinition(PhaseType.CLASSIC_SEASON_2, "Classic Season 2", 20, 38),
    PhaseDefinition(PhaseType.H2H_GROUP, "H2H Group Stage", 1, 35),
    PhaseDefinition(PhaseType.H2H_PLAYOFF, "H2H Play-offs", 36, 38),
    PhaseDefinition(PhaseType.CUP_SEASON_1, "Cup Season 1", 1, 19),
    PhaseDefinition(PhaseType.CUP_SEASON_2, "Cup Season 2", 20, 38),
)


class BootstrapConflictError(ValueError):
    """Raised when existing configuration disagrees with the canonical rules."""


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    season_id: int
    season_created: bool
    gameweeks_created: int
    phases_created: int

    @property
    def gameweeks_existing(self) -> int:
        return LAST_GAMEWEEK - self.gameweeks_created

    @property
    def phases_existing(self) -> int:
        return len(PHASE_DEFINITIONS) - self.phases_created


def _clean_required(value: str, *, field: str, maximum_length: int) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field} must not be empty")
    if len(cleaned) > maximum_length:
        raise ValueError(f"{field} must be at most {maximum_length} characters")
    return cleaned


def _validate_existing_season(season: Season, *, name: str) -> None:
    mismatches: list[str] = []
    if season.name != name:
        mismatches.append(f"name is {season.name!r}, expected {name!r}")
    if season.start_gameweek != FIRST_GAMEWEEK:
        mismatches.append(f"start_gameweek is {season.start_gameweek}, expected {FIRST_GAMEWEEK}")
    if season.end_gameweek != LAST_GAMEWEEK:
        mismatches.append(f"end_gameweek is {season.end_gameweek}, expected {LAST_GAMEWEEK}")
    if mismatches:
        raise BootstrapConflictError(
            f"season {season.fpl_season_code!r} conflicts with the rulebook: "
            + "; ".join(mismatches)
        )


def _validate_existing_phase(
    phase: CompetitionPhase,
    definition: PhaseDefinition,
) -> None:
    actual = (phase.name, phase.start_gameweek, phase.end_gameweek)
    expected = (
        definition.name,
        definition.start_gameweek,
        definition.end_gameweek,
    )
    if actual != expected:
        raise BootstrapConflictError(
            f"phase {definition.phase_type.value!r} conflicts with the rulebook: "
            f"found {actual!r}, expected {expected!r}"
        )


async def bootstrap_season(
    session: AsyncSession,
    *,
    season_code: str,
    season_name: str,
) -> BootstrapResult:
    """Create the canonical season shell without overwriting existing data.

    The caller owns the transaction. Repeating the call with the same inputs
    creates no additional records. Existing configuration that differs from
    the rulebook is reported as a conflict instead of being silently changed.
    """

    code = _clean_required(season_code, field="season_code", maximum_length=16)
    name = _clean_required(season_name, field="season_name", maximum_length=80)

    season = await session.scalar(select(Season).where(Season.fpl_season_code == code))
    season_created = season is None
    if season is None:
        season = Season(
            name=name,
            fpl_season_code=code,
            start_gameweek=FIRST_GAMEWEEK,
            end_gameweek=LAST_GAMEWEEK,
            status=SeasonStatus.DRAFT,
        )
        session.add(season)
        await session.flush()
    else:
        _validate_existing_season(season, name=name)

    existing_gameweeks = (
        (await session.scalars(select(Gameweek).where(Gameweek.season_id == season.id)))
        .unique()
        .all()
    )
    invalid_gameweeks = sorted(
        gameweek.number
        for gameweek in existing_gameweeks
        if not FIRST_GAMEWEEK <= gameweek.number <= LAST_GAMEWEEK
    )
    if invalid_gameweeks:
        raise BootstrapConflictError(
            f"season {code!r} contains out-of-range gameweeks: {invalid_gameweeks}"
        )

    gameweeks_by_number = {gameweek.number: gameweek for gameweek in existing_gameweeks}
    gameweeks_created = 0
    for number in range(FIRST_GAMEWEEK, LAST_GAMEWEEK + 1):
        if number not in gameweeks_by_number:
            session.add(Gameweek(season_id=season.id, number=number, is_finalized=False))
            gameweeks_created += 1

    existing_phases = (
        (
            await session.scalars(
                select(CompetitionPhase).where(CompetitionPhase.season_id == season.id)
            )
        )
        .unique()
        .all()
    )
    phase_counts = Counter(phase.phase_type for phase in existing_phases)
    duplicate_types = sorted(
        phase_type.value for phase_type, count in phase_counts.items() if count > 1
    )
    if duplicate_types:
        raise BootstrapConflictError(
            f"season {code!r} contains duplicate competition phases: {duplicate_types}"
        )

    phases_by_type = {phase.phase_type: phase for phase in existing_phases}
    phases_created = 0
    for definition in PHASE_DEFINITIONS:
        phase = phases_by_type.get(definition.phase_type)
        if phase is not None:
            _validate_existing_phase(phase, definition)
            continue
        session.add(
            CompetitionPhase(
                season_id=season.id,
                name=definition.name,
                phase_type=definition.phase_type,
                start_gameweek=definition.start_gameweek,
                end_gameweek=definition.end_gameweek,
            )
        )
        phases_created += 1

    await session.flush()
    return BootstrapResult(
        season_id=season.id,
        season_created=season_created,
        gameweeks_created=gameweeks_created,
        phases_created=phases_created,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Idempotently seed a VMF season, GW1-GW38, and the six rulebook phases.")
    )
    parser.add_argument(
        "--season-code",
        required=True,
        help='FPL season code, for example "2026/27".',
    )
    parser.add_argument(
        "--season-name",
        required=True,
        help='Display name, for example "VMF Fantasy League 2026/27".',
    )
    return parser


async def _run(*, season_code: str, season_name: str) -> BootstrapResult:
    engine = get_engine()
    try:
        async with get_session_factory()() as session:
            try:
                result = await bootstrap_season(
                    session,
                    season_code=season_code,
                    season_name=season_name,
                )
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()


def _print_result(result: BootstrapResult, *, season_code: str) -> None:
    season_action = "created" if result.season_created else "already existed"
    print(f"Season {season_code!r} (id={result.season_id}): {season_action}.")
    print(
        "Gameweeks GW1-GW38: "
        f"{result.gameweeks_created} created, {result.gameweeks_existing} already existed."
    )
    print(
        "Competition phases: "
        f"{result.phases_created} created, {result.phases_existing} already existed."
    )
    print(
        "Not seeded: managers, division memberships, FPL scores, H2H schedules, "
        "Cup competitions/rounds/matches, or audit records."
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(_run(season_code=args.season_code, season_name=args.season_name))
    except (BootstrapConflictError, ValueError) as exc:
        print(f"Bootstrap aborted: {exc}", file=sys.stderr)
        return 2

    _print_result(result, season_code=args.season_code.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
