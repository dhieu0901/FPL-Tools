from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import vmf_api.models  # noqa: F401  (registers every table on the metadata)
from vmf_api.db.base import Base
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus, ScoreState
from vmf_api.models.ingestion import (
    FplFixture,
    FplPlayerFixtureStat,
    ManagerGameweekHistory,
    ManagerPickItem,
    ManagerPickSnapshot,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.services.scoring import GameweekScoringService

CAPTURED_AT = datetime(2026, 8, 21, 19, 0)


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed(
    session: AsyncSession,
    *,
    manager_count: int = 1,
    statuses: dict[int, ManagerStatus] | None = None,
) -> tuple[Season, Gameweek, list[Manager]]:
    season = Season(
        name="VMF Fantasy League 2026/27",
        fpl_season_code="2026/27",
        start_gameweek=1,
        end_gameweek=38,
    )
    session.add(season)
    await session.flush()

    gameweek = Gameweek(season_id=season.id, number=1, deadline_time=datetime(2026, 8, 21, 17, 30))
    session.add(gameweek)

    managers = []
    for index in range(1, manager_count + 1):
        manager = Manager(
            fpl_entry_id=1000 + index,
            manager_name=f"Manager {index}",
            team_name=f"Team {index}",
            division=Division.HIGH,
            active_status=(statuses or {}).get(index, ManagerStatus.ACTIVE),
            registration_status=RegistrationStatus.CONFIRMED,
            season_joined="2026/27",
        )
        session.add(manager)
        managers.append(manager)
    await session.flush()
    return season, gameweek, managers


def _fixtures(season_id: int, *, started: bool, finished: bool) -> list[FplFixture]:
    return [
        FplFixture(
            season_id=season_id,
            fixture_fpl_id=index,
            gameweek_number=1,
            started=started,
            finished=finished,
        )
        for index in range(1, 3)
    ]


def _stats(
    season_id: int, points: dict[int, int], **events: dict[int, int]
) -> list[FplPlayerFixtureStat]:
    goals = events.get("goals", {})
    yellows = events.get("yellows", {})
    return [
        FplPlayerFixtureStat(
            season_id=season_id,
            gameweek_number=1,
            element_id=element_id,
            fixture_fpl_id=1,
            minutes=90,
            total_points=value,
            goals_scored=goals.get(element_id, 0),
            yellow_cards=yellows.get(element_id, 0),
        )
        for element_id, value in points.items()
    ]


def _snapshot(
    manager_id: int,
    *,
    revision: int = 1,
    captain_element: int = 1,
    captain_multiplier: int = 2,
    bench_multiplier: int = 0,
    active_chip: str | None = None,
    transfer_cost: int = 0,
) -> ManagerPickSnapshot:
    snapshot = ManagerPickSnapshot(
        manager_id=manager_id,
        gameweek_number=1,
        revision=revision,
        payload_hash=f"hash-{manager_id}-{revision}",
        active_chip=active_chip,
        transfer_cost=transfer_cost,
        captured_at=CAPTURED_AT,
    )
    items = []
    for position in range(1, 12):
        items.append(
            ManagerPickItem(
                element_id=position,
                squad_position=position,
                multiplier=(captain_multiplier if position == captain_element else 1),
                is_captain=position == captain_element,
                is_vice_captain=position == 2,
            )
        )
    for position in range(12, 16):
        items.append(
            ManagerPickItem(
                element_id=position,
                squad_position=position,
                multiplier=bench_multiplier,
            )
        )
    snapshot.items = items
    return snapshot


@pytest.mark.anyio
async def test_a_gameweek_with_no_started_fixture_is_not_scored() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers = await _seed(session)
            session.add_all(_fixtures(season.id, started=False, finished=False))
            session.add(_snapshot(managers[0].id))
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            assert outcome.state is ScoreState.UPCOMING
            assert outcome.skipped_reason == "no_fixture_started"
            assert outcome.managers_scored == 0
            assert await session.scalar(select(ManagerGameweekScore)) is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_live_gameweek_is_scored_from_picks_alone() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, gameweek, managers = await _seed(session)
            session.add_all(_fixtures(season.id, started=True, finished=False))
            session.add_all(
                _stats(
                    season.id,
                    {element: 3 for element in range(1, 16)},
                    goals={1: 2, 12: 1},
                )
            )
            session.add(_snapshot(managers[0].id))
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            assert outcome.state is ScoreState.LIVE
            assert outcome.managers_scored == 1
            score = await session.scalar(select(ManagerGameweekScore))
            assert score is not None
            assert score.gameweek_id == gameweek.id
            assert score.gross_points == 36
            assert score.net_points == 36
            assert score.captain_points == 6
            assert score.bench_points == 12
            # The bench goal does not count without Bench Boost.
            assert score.goals_counted == 2
            assert score.official_points is None
            assert score.score_status is ScoreState.LIVE
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_the_published_history_becomes_the_authority_once_it_exists() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers = await _seed(session)
            session.add_all(_fixtures(season.id, started=True, finished=True))
            session.add_all(_stats(season.id, {element: 3 for element in range(1, 16)}))
            session.add(_snapshot(managers[0].id, transfer_cost=0))
            session.add(
                ManagerGameweekHistory(
                    manager_id=managers[0].id,
                    gameweek_number=1,
                    gross_points=41,
                    transfer_cost=4,
                    points_on_bench=12,
                )
            )
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            assert outcome.state is ScoreState.PROVISIONAL
            # 41 disagrees with the 36 derived from picks, so it is flagged.
            assert outcome.unreconciled_manager_ids == (managers[0].id,)
            score = await session.scalar(select(ManagerGameweekScore))
            assert score is not None
            assert score.gross_points == 41
            assert score.transfer_cost == 4
            assert score.net_points == 37
            assert score.official_points == 37
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_only_the_newest_revision_is_scored() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers = await _seed(session)
            session.add_all(_fixtures(season.id, started=True, finished=False))
            session.add_all(_stats(season.id, {element: 3 for element in range(1, 16)}))
            # Revision 1 is the deadline squad; revision 2 carries FPL's
            # automatic substitutions and a Bench Boost that was not visible yet.
            session.add(_snapshot(managers[0].id, revision=1))
            session.add(
                _snapshot(
                    managers[0].id,
                    revision=2,
                    bench_multiplier=1,
                    active_chip="bboost",
                )
            )
            await session.flush()

            await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            score = await session.scalar(select(ManagerGameweekScore))
            assert score is not None
            assert score.chip_used == "bboost"
            assert score.gross_points == 14 * 3 + 3 * 2
            assert score.bench_points == 0
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_totw_goes_to_every_manager_tied_at_the_top() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers = await _seed(session, manager_count=3)
            session.add_all(_fixtures(season.id, started=True, finished=True))
            session.add_all(_stats(season.id, {element: 3 for element in range(1, 16)}))
            for manager in managers:
                session.add(_snapshot(manager.id))
            session.add_all(
                [
                    ManagerGameweekHistory(
                        manager_id=managers[0].id, gameweek_number=1, gross_points=60
                    ),
                    ManagerGameweekHistory(
                        manager_id=managers[1].id, gameweek_number=1, gross_points=60
                    ),
                    ManagerGameweekHistory(
                        manager_id=managers[2].id, gameweek_number=1, gross_points=72
                    ),
                ]
            )
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            assert outcome.managers_scored == 3
            assert outcome.totw_manager_ids == (managers[2].id,)

            # TotW compares net points, so a transfer hit brings the highest
            # gross back level with the other two and all three win.
            entry = await session.scalar(
                select(ManagerGameweekHistory).where(
                    ManagerGameweekHistory.manager_id == managers[2].id
                )
            )
            assert entry is not None
            entry.transfer_cost = 12
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            assert outcome.totw_manager_ids == tuple(manager.id for manager in managers)
            winners = await session.scalars(
                select(ManagerGameweekScore.manager_id).where(
                    ManagerGameweekScore.is_totw.is_(True)
                )
            )
            assert sorted(winners) == [manager.id for manager in managers]

            # A bigger hit drops that manager clear of the tie.
            entry.transfer_cost = 16
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            assert outcome.totw_manager_ids == (managers[0].id, managers[1].id)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_locked_manager_cannot_win_totw() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers = await _seed(
                session,
                manager_count=2,
                statuses={2: ManagerStatus.LOCKED},
            )
            session.add_all(_fixtures(season.id, started=True, finished=True))
            session.add_all(_stats(season.id, {element: 3 for element in range(1, 16)}))
            for manager in managers:
                session.add(_snapshot(manager.id))
            session.add_all(
                [
                    ManagerGameweekHistory(
                        manager_id=managers[0].id, gameweek_number=1, gross_points=50
                    ),
                    ManagerGameweekHistory(
                        manager_id=managers[1].id, gameweek_number=1, gross_points=99
                    ),
                ]
            )
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            assert outcome.totw_manager_ids == (managers[0].id,)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_rescoring_updates_the_existing_row_instead_of_duplicating_it() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers = await _seed(session)
            session.add_all(_fixtures(season.id, started=True, finished=False))
            session.add_all(_stats(season.id, {element: 3 for element in range(1, 16)}))
            session.add(_snapshot(managers[0].id))
            await session.flush()

            service = GameweekScoringService(session, season_id=season.id)
            await service.score_gameweek(1)
            first = await session.scalar(select(ManagerGameweekScore))
            assert first is not None
            row_id = first.id

            # A later tick sees a corrected statistic for one counted player.
            stat = await session.scalar(
                select(FplPlayerFixtureStat).where(FplPlayerFixtureStat.element_id == 1)
            )
            assert stat is not None
            stat.total_points = 13
            await session.flush()

            await service.score_gameweek(1)

            rows = list(await session.scalars(select(ManagerGameweekScore)))
            assert len(rows) == 1
            assert rows[0].id == row_id
            assert rows[0].gross_points == 10 * 3 + 13 * 2
            assert rows[0].captain_points == 26
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_manager_with_history_but_no_picks_still_gets_a_score() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers = await _seed(session)
            session.add_all(_fixtures(season.id, started=True, finished=True))
            session.add(
                ManagerGameweekHistory(
                    manager_id=managers[0].id,
                    gameweek_number=1,
                    gross_points=64,
                    transfer_cost=4,
                )
            )
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            assert outcome.managers_scored == 1
            assert outcome.unreconciled_manager_ids == (managers[0].id,)
            score = await session.scalar(select(ManagerGameweekScore))
            assert score is not None
            assert score.net_points == 60
            # Tie-break figures need the squad, so they stay at zero.
            assert score.captain_points == 0
            assert score.goals_counted == 0
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_finalized_gameweek_reports_the_final_state() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, gameweek, managers = await _seed(session)
            gameweek.is_finalized = True
            session.add_all(_fixtures(season.id, started=True, finished=True))
            session.add_all(_stats(season.id, {element: 3 for element in range(1, 16)}))
            session.add(_snapshot(managers[0].id))
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(1)

            assert outcome.state is ScoreState.FINAL
            score = await session.scalar(select(ManagerGameweekScore))
            assert score is not None
            assert score.score_status is ScoreState.FINAL
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_unknown_gameweek_is_reported_rather_than_raising() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, _ = await _seed(session)
            await session.flush()

            outcome = await GameweekScoringService(session, season_id=season.id).score_gameweek(38)

            assert outcome.skipped_reason == "gameweek_not_found"
            assert outcome.state is None
    finally:
        await engine.dispose()
