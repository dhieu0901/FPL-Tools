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
from vmf_api.db.base import Base
from vmf_api.domain.h2h_result import Settlement, settle_match
from vmf_api.domain.violations import ThresholdAction
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import (
    Division,
    ManagerStatus,
    MatchStatus,
    RegistrationStatus,
    ScoreState,
)
from vmf_api.models.governance import ViolationThresholdAction
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.services.h2h_settlement import H2HSettlementService

# --------------------------------------------------------------------------
# Domain
# --------------------------------------------------------------------------


def test_the_higher_net_score_wins() -> None:
    result = settle_match(home_points=72, away_points=68)

    assert result.settlement is Settlement.ON_POINTS
    assert result.winner == "home"
    assert (result.home_score, result.away_score) == (72, 68)


def test_equal_scores_are_a_draw_rather_than_a_win() -> None:
    result = settle_match(home_points=68, away_points=68)

    assert result.settlement is Settlement.ON_POINTS
    assert result.winner is None
    assert result.is_settled


def test_a_negative_score_still_decides_the_match() -> None:
    # A heavy transfer hit can put a manager below zero.
    result = settle_match(home_points=-3, away_points=-8)

    assert result.winner == "home"


def test_a_match_without_both_scores_is_not_played() -> None:
    assert settle_match(home_points=70, away_points=None).settlement is Settlement.NOT_PLAYED
    assert settle_match(home_points=None, away_points=None).settlement is Settlement.NOT_PLAYED


def test_a_forfeit_hands_the_opponent_the_match_whatever_the_scores() -> None:
    result = settle_match(home_points=99, away_points=1, home_forfeits=True)

    assert result.settlement is Settlement.WALKOVER
    assert result.winner == "away"
    # Stored 0-0 so the table gains no artificial point difference.
    assert (result.home_score, result.away_score) == (0, 0)
    assert result.walkover_reason is not None


def test_two_forfeits_go_to_review_rather_than_a_coin_toss() -> None:
    result = settle_match(
        home_points=50,
        away_points=50,
        home_forfeits=True,
        away_forfeits=True,
    )

    assert result.settlement is Settlement.NEEDS_REVIEW
    assert result.winner is None
    assert not result.is_settled


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed(
    session: AsyncSession,
    *,
    scores: dict[int, tuple[int, ScoreState]] | None = None,
) -> tuple[Season, Gameweek, list[Manager], list[H2HMatch]]:
    season = Season(
        name="VMF Fantasy League 2026/27",
        fpl_season_code="2026/27",
        start_gameweek=1,
        end_gameweek=38,
    )
    session.add(season)
    await session.flush()

    gameweek = Gameweek(season_id=season.id, number=1)
    session.add(gameweek)

    managers = []
    for index in range(1, 5):
        manager = Manager(
            fpl_entry_id=1000 + index,
            manager_name=f"Manager {index}",
            team_name=f"Team {index}",
            division=Division.HIGH,
            active_status=ManagerStatus.ACTIVE,
            registration_status=RegistrationStatus.CONFIRMED,
            season_joined="2026/27",
        )
        session.add(manager)
        managers.append(manager)

    schedule = H2HSchedule(season_id=season.id, name="Group")
    session.add(schedule)
    await session.flush()

    matches = [
        H2HMatch(
            schedule_id=schedule.id,
            gameweek_number=1,
            home_manager_id=managers[0].id,
            away_manager_id=managers[1].id,
        ),
        H2HMatch(
            schedule_id=schedule.id,
            gameweek_number=1,
            home_manager_id=managers[2].id,
            away_manager_id=managers[3].id,
        ),
    ]
    session.add_all(matches)

    for position, (points, state) in (scores or {}).items():
        session.add(
            ManagerGameweekScore(
                manager_id=managers[position].id,
                gameweek_id=gameweek.id,
                gross_points=points,
                transfer_cost=0,
                net_points=points,
                score_status=state,
            )
        )
    await session.flush()
    return season, gameweek, managers, matches


@pytest.mark.anyio
async def test_a_live_gameweek_produces_a_live_result() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers, matches = await _seed(
                session,
                scores={
                    0: (54, ScoreState.LIVE),
                    1: (41, ScoreState.LIVE),
                    2: (33, ScoreState.LIVE),
                    3: (33, ScoreState.LIVE),
                },
            )

            outcome = await H2HSettlementService(session, season_id=season.id).settle_gameweek(1)

            assert outcome.settled == 2
            await session.refresh(matches[0])
            await session.refresh(matches[1])
            assert matches[0].status is MatchStatus.LIVE
            assert (matches[0].home_score, matches[0].away_score) == (54, 41)
            assert matches[0].winner_manager_id == managers[0].id
            # The level match is a draw, not an unresolved fixture.
            assert matches[1].winner_manager_id is None
            assert matches[1].status is MatchStatus.LIVE
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_the_result_is_only_as_settled_as_the_least_settled_side() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, _, matches = await _seed(
                session,
                scores={
                    0: (54, ScoreState.FINAL),
                    1: (41, ScoreState.LIVE),
                },
            )

            await H2HSettlementService(session, season_id=season.id).settle_gameweek(1)

            await session.refresh(matches[0])
            # One side is still playing, so the match is not presented as final.
            assert matches[0].status is MatchStatus.LIVE
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_match_missing_a_score_is_left_alone() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, _, matches = await _seed(session, scores={0: (54, ScoreState.LIVE)})

            outcome = await H2HSettlementService(session, season_id=season.id).settle_gameweek(1)

            assert outcome.settled == 0
            await session.refresh(matches[0])
            assert matches[0].status is MatchStatus.SCHEDULED
            assert matches[0].home_score is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_removed_manager_forfeits_the_match() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers, matches = await _seed(
                session,
                scores={
                    0: (90, ScoreState.PROVISIONAL),
                    1: (30, ScoreState.PROVISIONAL),
                },
            )
            session.add(
                ViolationThresholdAction(
                    manager_id=managers[0].id,
                    action=ThresholdAction.REMOVED_FROM_H2H,
                    threshold=2,
                    cumulative_count=2,
                )
            )
            await session.flush()

            outcome = await H2HSettlementService(session, season_id=season.id).settle_gameweek(1)

            assert outcome.walkovers == 1
            await session.refresh(matches[0])
            assert matches[0].status is MatchStatus.WALKOVER
            # The opponent takes the match despite scoring far fewer points.
            assert matches[0].winner_manager_id == managers[1].id
            assert (matches[0].home_score, matches[0].away_score) == (0, 0)
            assert matches[0].walkover_reason is not None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_finalized_gameweek_keeps_the_result_it_was_locked_with() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, gameweek, _, matches = await _seed(
                session,
                scores={
                    0: (54, ScoreState.FINAL),
                    1: (41, ScoreState.FINAL),
                    2: (20, ScoreState.FINAL),
                    3: (10, ScoreState.FINAL),
                },
            )
            await H2HSettlementService(session, season_id=season.id).settle_gameweek(1)
            gameweek.is_finalized = True
            await session.flush()

            # FPL restates a score after the Gameweek was locked.
            score = await session.scalar(
                select(ManagerGameweekScore).where(
                    ManagerGameweekScore.manager_id == matches[0].home_manager_id
                )
            )
            assert score is not None
            score.net_points = 5
            await session.flush()

            outcome = await H2HSettlementService(session, season_id=season.id).settle_gameweek(1)

            assert outcome.untouched_final == 2
            assert outcome.settled == 0
            await session.refresh(matches[0])
            # The locked result stands; changing it requires a reopen.
            assert matches[0].home_score == 54
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_rerunning_keeps_the_result_in_step_with_a_corrected_score() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season, _, managers, matches = await _seed(
                session,
                scores={
                    0: (54, ScoreState.LIVE),
                    1: (41, ScoreState.LIVE),
                },
            )
            service = H2HSettlementService(session, season_id=season.id)
            await service.settle_gameweek(1)

            score = await session.scalar(
                select(ManagerGameweekScore).where(
                    ManagerGameweekScore.manager_id == managers[1].id
                )
            )
            assert score is not None
            score.net_points = 80
            await session.flush()

            await service.settle_gameweek(1)

            await session.refresh(matches[0])
            # An unfinalized match follows the live score, including a lead change.
            assert matches[0].away_score == 80
            assert matches[0].winner_manager_id == managers[1].id
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_season_without_a_schedule_is_reported_rather_than_failing() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            season = Season(
                name="VMF Fantasy League 2026/27",
                fpl_season_code="2026/27",
                start_gameweek=1,
                end_gameweek=38,
            )
            session.add(season)
            await session.flush()
            session.add(Gameweek(season_id=season.id, number=1))
            await session.flush()

            outcome = await H2HSettlementService(session, season_id=season.id).settle_gameweek(1)

            assert outcome.skipped_reason == "no_schedule"
    finally:
        await engine.dispose()
