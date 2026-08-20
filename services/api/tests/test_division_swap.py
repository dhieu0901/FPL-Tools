"""Writing the end-of-Season swap between HIGH and LOW."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import vmf_api.models  # noqa: F401  (registers every table on the metadata)
from vmf_api.cli.bootstrap_season import bootstrap_season
from vmf_api.core.errors import ConflictError, RuleValidationError
from vmf_api.db.base import Base
from vmf_api.models.competition import CompetitionPhase, DivisionMembership, Gameweek, Season
from vmf_api.models.enums import (
    Division,
    ManagerStatus,
    PhaseType,
    RegistrationStatus,
    ScoreState,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.services.promotion import SWAP_AFTER_GAMEWEEK, DivisionSwapService

SEASON_CODE = "2026/27"
HIGH_SIZE = 20
LOW_SIZE = 26


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed(
    session: AsyncSession,
    *,
    finalize: bool = True,
    tie: tuple[Division, int] | None = None,
) -> tuple[Season, list[Manager]]:
    """A finished Season 1 where roster order is rank order.

    ``tie`` gives the manager at that zero-based index the same points as the
    one before them, which is how a boundary becomes contested.
    """

    await bootstrap_season(
        session, season_code=SEASON_CODE, season_name="VMF Fantasy League 2026/27"
    )
    season = await session.scalar(select(Season).where(Season.fpl_season_code == SEASON_CODE))
    assert season is not None

    if finalize:
        for gameweek in await session.scalars(
            select(Gameweek).where(
                Gameweek.season_id == season.id,
                Gameweek.number <= SWAP_AFTER_GAMEWEEK,
            )
        ):
            gameweek.is_finalized = True
    await session.flush()

    gameweeks = {
        gameweek.number: gameweek
        for gameweek in await session.scalars(
            select(Gameweek).where(Gameweek.season_id == season.id)
        )
    }

    managers: list[Manager] = []
    for division, size, base in ((Division.HIGH, HIGH_SIZE, 1000), (Division.LOW, LOW_SIZE, 2000)):
        for index in range(size):
            manager = Manager(
                fpl_entry_id=base + index,
                manager_name=f"{division.value} Manager {index + 1}",
                team_name=f"{division.value} Team {index + 1}",
                division=division,
                active_status=ManagerStatus.ACTIVE,
                registration_status=RegistrationStatus.CONFIRMED,
                season_joined=SEASON_CODE,
            )
            session.add(manager)
            await session.flush()
            managers.append(manager)

            points = 100 - index
            if tie is not None and tie[0] is division and index == tie[1]:
                points = 100 - (index - 1)
            for number in range(1, SWAP_AFTER_GAMEWEEK + 1):
                session.add(
                    ManagerGameweekScore(
                        manager_id=manager.id,
                        gameweek_id=gameweeks[number].id,
                        gross_points=points,
                        transfer_cost=0,
                        net_points=points,
                        score_status=ScoreState.FINAL,
                    )
                )
    await session.flush()
    return season, managers


def _high(managers: list[Manager], rank: int) -> Manager:
    return managers[rank - 1]


def _low(managers: list[Manager], rank: int) -> Manager:
    return managers[HIGH_SIZE + rank - 1]


@pytest.mark.anyio
async def test_the_plan_names_the_twelve_who_move() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            _, managers = await _seed(session)

            planned, _ = await DivisionSwapService(session).plan(season_code=SEASON_CODE)

            assert planned.is_decided
            assert [move.finished_rank for move in planned.promoted] == [1, 2, 3, 4, 5, 6]
            assert [move.manager_id for move in planned.promoted] == [
                _low(managers, rank).id for rank in range(1, 7)
            ]
            assert [move.finished_rank for move in planned.relegated] == [15, 16, 17, 18, 19, 20]
            assert [move.manager_id for move in planned.relegated] == [
                _high(managers, rank).id for rank in range(15, 21)
            ]
            assert planned.dry_run is True
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_plan_writes_nothing() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed(session)
            await DivisionSwapService(session).plan(season_code=SEASON_CODE)

            assert (await session.scalars(select(DivisionMembership))).all() == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_applying_moves_twelve_and_keeps_both_divisions_the_same_size() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, managers = await _seed(session)

            result = await DivisionSwapService(session).apply(season_code=SEASON_CODE)

            assert result.memberships_written == HIGH_SIZE + LOW_SIZE
            assert len(result.promoted) == len(result.relegated) == 6

            phase = await session.scalar(
                select(CompetitionPhase).where(
                    CompetitionPhase.season_id == season.id,
                    CompetitionPhase.phase_type == PhaseType.CLASSIC_SEASON_2,
                )
            )
            assert phase is not None
            memberships = list(
                await session.scalars(
                    select(DivisionMembership).where(
                        DivisionMembership.competition_phase_id == phase.id
                    )
                )
            )
            counts = {Division.HIGH: 0, Division.LOW: 0}
            for membership in memberships:
                counts[membership.division] += 1
            assert counts == {Division.HIGH: HIGH_SIZE, Division.LOW: LOW_SIZE}

            # The pointer on each manager follows them to the new division.
            await session.refresh(_low(managers, 1))
            await session.refresh(_high(managers, 20))
            assert _low(managers, 1).division is Division.HIGH
            assert _high(managers, 20).division is Division.LOW
            assert _high(managers, 1).division is Division.HIGH
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_the_reason_a_manager_moved_is_recorded() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            _, managers = await _seed(session)
            await DivisionSwapService(session).apply(season_code=SEASON_CODE)

            promoted = await session.scalar(
                select(DivisionMembership).where(
                    DivisionMembership.manager_id == _low(managers, 1).id
                )
            )
            relegated = await session.scalar(
                select(DivisionMembership).where(
                    DivisionMembership.manager_id == _high(managers, 20).id
                )
            )
            stayed = await session.scalar(
                select(DivisionMembership).where(
                    DivisionMembership.manager_id == _high(managers, 1).id
                )
            )
            assert promoted is not None and "top 6 of LOW" in (promoted.promotion_source or "")
            assert relegated is not None and "bottom 6 of HIGH" in (
                relegated.relegation_source or ""
            )
            assert stayed is not None
            assert stayed.promotion_source is None and stayed.relegation_source is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_season_1_membership_is_left_exactly_as_it_was() -> None:
    """A manager who finished 18th in HIGH still finished 18th in HIGH."""

    factory, engine = await _database()
    try:
        async with factory() as session:
            season, managers = await _seed(session)
            first_phase = await session.scalar(
                select(CompetitionPhase).where(
                    CompetitionPhase.season_id == season.id,
                    CompetitionPhase.phase_type == PhaseType.CLASSIC_SEASON_1,
                )
            )
            assert first_phase is not None
            session.add(
                DivisionMembership(
                    manager_id=_high(managers, 20).id,
                    competition_phase_id=first_phase.id,
                    division=Division.HIGH,
                    start_gameweek=1,
                    end_gameweek=19,
                )
            )
            await session.flush()

            await DivisionSwapService(session).apply(season_code=SEASON_CODE)

            history = await session.scalar(
                select(DivisionMembership).where(
                    DivisionMembership.manager_id == _high(managers, 20).id,
                    DivisionMembership.competition_phase_id == first_phase.id,
                )
            )
            assert history is not None
            assert history.division is Division.HIGH
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_tie_at_the_boundary_blocks_the_whole_swap() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            # LOW ranks 6 and 7 share a score, so the last promotion place
            # cannot be decided from the table.
            await _seed(session, tie=(Division.LOW, 6))

            planned, _ = await DivisionSwapService(session).plan(season_code=SEASON_CODE)
            assert not planned.is_decided
            assert planned.contested_ranks == (6,)

            with pytest.raises(RuleValidationError, match="administrator decision"):
                await DivisionSwapService(session).apply(season_code=SEASON_CODE)

            assert (await session.scalars(select(DivisionMembership))).all() == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_unfinalized_gameweek_19_blocks_the_swap() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed(session, finalize=False)

            with pytest.raises(RuleValidationError, match="GW19 is not finalized"):
                await DivisionSwapService(session).plan(season_code=SEASON_CODE)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_the_swap_is_made_once() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed(session)
            service = DivisionSwapService(session)
            await service.apply(season_code=SEASON_CODE)

            with pytest.raises(ConflictError, match="the swap has been made"):
                await service.apply(season_code=SEASON_CODE)
    finally:
        await engine.dispose()
