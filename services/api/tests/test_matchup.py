from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import vmf_api.models  # noqa: F401  (registers every table on the metadata)
from vmf_api.core.errors import NotFoundError
from vmf_api.db.base import Base
from vmf_api.domain.matchup import (
    FixtureProgress,
    PlayerState,
    SidePick,
    build_squad,
    compare_squads,
)
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import (
    Division,
    ManagerStatus,
    MatchStatus,
    RegistrationStatus,
    ScoreState,
)
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.ingestion import (
    FplFixture,
    FplPlayer,
    FplPlayerFixtureStat,
    ManagerPickItem,
    ManagerPickSnapshot,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.services.matchup import MatchupService

CAPTURED_AT = __import__("datetime").datetime(2026, 8, 21, 19, 0)


# --------------------------------------------------------------------------
# Domain
# --------------------------------------------------------------------------


def test_a_player_both_sides_field_identically_is_shared() -> None:
    comparison = compare_squads(
        {1: SidePick(1, 1)},
        {1: SidePick(1, 1)},
        {1: 12},
        {1: FixtureProgress(total=1, started=1, finished=1)},
    )

    line = comparison.lines[0]
    assert line.is_shared
    assert line.net_multiplier == 0
    # However well he scores, he cannot move the margin.
    assert line.swing_points == 0
    assert comparison.differentials == ()


def test_the_same_player_captained_by_one_side_is_a_differential() -> None:
    comparison = compare_squads(
        {1: SidePick(1, 2, is_effective_captain=True)},
        {1: SidePick(1, 1)},
        {1: 12},
        {},
    )

    line = comparison.lines[0]
    assert not line.is_shared
    assert line.net_multiplier == 1
    assert line.swing_points == 12
    assert comparison.captain_differential == (line,)


def test_the_sign_of_the_net_multiplier_says_whose_differential_it_is() -> None:
    comparison = compare_squads(
        {1: SidePick(1, 1)},
        {2: SidePick(2, 2, is_effective_captain=True)},
        {1: 8, 2: 5},
        {},
    )

    lines = {line.element_id: line for line in comparison.lines}
    assert lines[1].net_multiplier == 1
    assert lines[1].swing_points == 8
    assert lines[2].net_multiplier == -2
    assert lines[2].swing_points == -10
    # The bigger swing is listed first.
    assert [line.element_id for line in comparison.differentials] == [2, 1]


def test_a_player_benched_by_both_sides_is_left_out() -> None:
    comparison = compare_squads(
        {1: SidePick(1, 0)},
        {1: SidePick(1, 0)},
        {1: 9},
        {},
    )

    assert comparison.lines == ()


def test_remaining_counts_players_and_fixtures_separately() -> None:
    comparison = compare_squads(
        # Element 3 plays twice; element 2 has already finished.
        {1: SidePick(1, 1), 2: SidePick(2, 1), 3: SidePick(3, 2)},
        {},
        {},
        {
            1: FixtureProgress(total=1, started=0, finished=0),
            2: FixtureProgress(total=1, started=1, finished=1),
            3: FixtureProgress(total=2, started=1, finished=1),
        },
    )

    remaining = comparison.home_remaining
    assert remaining.players_remaining == 2
    # One at x1 and the captain at x2.
    assert remaining.effective_players_remaining == 3
    # A Double Gameweek player must not read as two players.
    assert remaining.fixtures_remaining == 2


def test_a_benched_player_is_not_counted_as_still_to_play() -> None:
    comparison = compare_squads(
        {1: SidePick(1, 0)},
        {1: SidePick(1, 1)},
        {},
        {1: FixtureProgress(total=1, started=0, finished=0)},
    )

    assert comparison.home_remaining.players_remaining == 0
    assert comparison.away_remaining.players_remaining == 1


def test_player_state_follows_the_fixtures() -> None:
    assert FixtureProgress(total=1).state is PlayerState.UPCOMING
    assert FixtureProgress(total=1, started=1).state is PlayerState.PLAYING
    assert FixtureProgress(total=1, started=1, finished=1).state is PlayerState.FINISHED
    # One of two fixtures played is still in progress overall.
    assert FixtureProgress(total=2, started=1, finished=1).state is PlayerState.PLAYING


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed(session: AsyncSession) -> H2HMatch:
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
    await session.flush()

    managers = []
    for index in (1, 2):
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
    await session.flush()

    schedule = H2HSchedule(season_id=season.id, name="Group")
    session.add(schedule)
    await session.flush()

    match = H2HMatch(
        schedule_id=schedule.id,
        gameweek_number=1,
        home_manager_id=managers[0].id,
        away_manager_id=managers[1].id,
        status=MatchStatus.LIVE,
    )
    session.add(match)

    # Element 1 is shared, 2 is the home differential, 3 the away captain.
    session.add_all(
        [
            FplPlayer(
                season_id=season.id,
                element_id=element_id,
                web_name=f"Player {element_id}",
                full_name=f"Player {element_id}",
                team_fpl_id=1,
                element_type=3,
            )
            for element_id in (1, 2, 3)
        ]
    )
    session.add_all(
        [
            FplFixture(
                season_id=season.id,
                fixture_fpl_id=101,
                gameweek_number=1,
                started=True,
                finished=True,
            ),
            FplFixture(
                season_id=season.id,
                fixture_fpl_id=102,
                gameweek_number=1,
                started=True,
                finished=False,
            ),
        ]
    )
    session.add_all(
        [
            FplPlayerFixtureStat(
                season_id=season.id,
                gameweek_number=1,
                element_id=1,
                fixture_fpl_id=101,
                total_points=6,
            ),
            FplPlayerFixtureStat(
                season_id=season.id,
                gameweek_number=1,
                element_id=2,
                fixture_fpl_id=101,
                total_points=9,
            ),
            FplPlayerFixtureStat(
                season_id=season.id,
                gameweek_number=1,
                element_id=3,
                fixture_fpl_id=102,
                total_points=2,
            ),
        ]
    )

    home_snapshot = ManagerPickSnapshot(
        manager_id=managers[0].id,
        gameweek_number=1,
        revision=1,
        payload_hash="home",
        captured_at=CAPTURED_AT,
    )
    home_snapshot.items = [
        ManagerPickItem(element_id=1, squad_position=1, multiplier=1),
        ManagerPickItem(element_id=2, squad_position=2, multiplier=2, is_captain=True),
    ]
    away_snapshot = ManagerPickSnapshot(
        manager_id=managers[1].id,
        gameweek_number=1,
        revision=1,
        payload_hash="away",
        captured_at=CAPTURED_AT,
    )
    away_snapshot.items = [
        ManagerPickItem(element_id=1, squad_position=1, multiplier=1),
        ManagerPickItem(element_id=3, squad_position=2, multiplier=2, is_captain=True),
    ]
    session.add_all([home_snapshot, away_snapshot])

    session.add_all(
        [
            ManagerGameweekScore(
                manager_id=managers[0].id,
                gameweek_id=gameweek.id,
                gross_points=24,
                transfer_cost=0,
                net_points=24,
                captain_points=18,
                bench_points=3,
                score_status=ScoreState.LIVE,
            ),
            ManagerGameweekScore(
                manager_id=managers[1].id,
                gameweek_id=gameweek.id,
                gross_points=10,
                transfer_cost=4,
                net_points=6,
                captain_points=4,
                bench_points=0,
                score_status=ScoreState.LIVE,
            ),
        ]
    )
    await session.flush()
    return match


@pytest.mark.anyio
async def test_the_matchup_view_separates_shared_players_from_differentials() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            match = await _seed(session)

            view = await MatchupService(session).h2h_match(match.id)

            assert view.gameweek_number == 1
            assert view.score_state is ScoreState.LIVE
            assert view.home.score == 24
            assert view.away.score == 6
            assert view.away.transfer_cost == 4

            shared = [line.element_id for line in view.comparison.shared]
            assert shared == [1]
            differentials = [line.element_id for line in view.comparison.differentials]
            assert sorted(differentials) == [2, 3]
            assert view.player_names[2] == "Player 2"
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_remaining_reflects_which_fixtures_have_finished() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            match = await _seed(session)

            view = await MatchupService(session).h2h_match(match.id)

            # The home squad's players both played in the finished fixture.
            assert view.comparison.home_remaining.players_remaining == 0
            # The away captain's fixture is still in progress.
            assert view.comparison.away_remaining.players_remaining == 1
            assert view.comparison.away_remaining.effective_players_remaining == 2
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_settled_match_keeps_the_score_it_was_recorded_with() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            match = await _seed(session)
            match.home_score = 99
            match.away_score = 1
            await session.flush()

            view = await MatchupService(session).h2h_match(match.id)

            assert view.home.score == 99
            assert view.away.score == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_unknown_match_is_reported_as_missing() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)

            with pytest.raises(NotFoundError):
                await MatchupService(session).h2h_match(9999)
    finally:
        await engine.dispose()


def test_a_squad_is_listed_in_the_order_fpl_presents_it() -> None:
    picks = {
        # Deliberately out of order to prove the sort, not the input.
        14: SidePick(14, 0, squad_position=14, element_type=3),
        1: SidePick(1, 1, squad_position=1, element_type=1),
        12: SidePick(12, 0, squad_position=12, element_type=1),
        9: SidePick(9, 2, squad_position=9, element_type=4, is_effective_captain=True),
        13: SidePick(13, 0, squad_position=13, element_type=2),
        15: SidePick(15, 0, squad_position=15, element_type=4),
    }

    squad = build_squad(picks, {9: 13, 1: 6}, {})

    assert [entry.squad_position for entry in squad] == [1, 9, 12, 13, 14, 15]
    keeper, captain, sub_keeper, bench_one, bench_two, bench_three = squad

    assert keeper.is_starter
    assert captain.is_starter and captain.is_captain
    # The captain's line shows the multiplied contribution.
    assert captain.contribution_points == 26

    assert not sub_keeper.is_starter
    assert sub_keeper.is_substitute_goalkeeper
    assert sub_keeper.bench_order is None

    assert [entry.bench_order for entry in (bench_one, bench_two, bench_three)] == [1, 2, 3]
    assert not any(entry.is_substitute_goalkeeper for entry in (bench_one, bench_two, bench_three))


def test_the_vice_captain_is_reported_even_when_the_armband_did_not_move() -> None:
    picks = {
        1: SidePick(1, 2, squad_position=1, element_type=3, is_effective_captain=True),
        2: SidePick(2, 1, squad_position=2, element_type=3, is_vice_captain=True),
    }

    squad = build_squad(picks, {}, {})

    assert squad[0].is_captain and not squad[0].is_vice_captain
    assert squad[1].is_vice_captain and not squad[1].is_captain


@pytest.mark.anyio
async def test_the_service_returns_both_squads_with_names_and_positions() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            match = await _seed(session)

            view = await MatchupService(session).h2h_match(match.id)

            assert [slot.squad_position for slot in view.home_squad] == [1, 2]
            assert view.home_squad[1].is_captain
            assert view.player_names[view.home_squad[1].element_id] == "Player 2"
            # Positions come from the player catalog, not from the pick row.
            assert all(slot.element_type == 3 for slot in view.home_squad)
    finally:
        await engine.dispose()
