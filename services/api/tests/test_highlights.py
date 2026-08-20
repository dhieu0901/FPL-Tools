"""The stories the dashboard tells about a finished Gameweek.

None of these can be checked against the live season until it has played, so
each kind is pinned here with a seeded Gameweek built to trigger exactly one
of them.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import vmf_api.models  # noqa: F401  (registers every table on the metadata)
from vmf_api.db.base import Base
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
    FplPlayer,
    FplPlayerFixtureStat,
    ManagerPickItem,
    ManagerPickSnapshot,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.services.highlights import HighlightKind, HighlightsService

CAPTURED_AT = datetime(2026, 8, 22, 19, 0)
GAMEWEEK = 1


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


class Season1:
    """A one-Gameweek season that each test bends to its own shape."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.managers: list[Manager] = []

    async def build(self, *, managers: int = 4) -> Season1:
        self.season = Season(fpl_season_code="2026/27", name="VMF 2026/27")
        self.session.add(self.season)
        await self.session.flush()

        self.gameweek = Gameweek(season_id=self.season.id, number=GAMEWEEK, is_finalized=True)
        self.session.add(self.gameweek)

        self.schedule = H2HSchedule(season_id=self.season.id, name="Group")
        self.session.add(self.schedule)
        await self.session.flush()

        for index in range(managers):
            manager = Manager(
                fpl_entry_id=1000 + index,
                manager_name=f"Manager {index + 1}",
                team_name=f"Team {index + 1}",
                division=Division.HIGH,
                active_status=ManagerStatus.ACTIVE,
                registration_status=RegistrationStatus.CONFIRMED,
                season_joined="2026/27",
            )
            self.session.add(manager)
            self.managers.append(manager)
        await self.session.flush()
        return self

    async def score(
        self,
        manager: Manager,
        *,
        net: int = 50,
        captain: int = 10,
        bench: int = 2,
        chip: str | None = None,
        is_totw: bool = False,
    ) -> None:
        self.session.add(
            ManagerGameweekScore(
                manager_id=manager.id,
                gameweek_id=self.gameweek.id,
                gross_points=net,
                transfer_cost=0,
                net_points=net,
                captain_points=captain,
                bench_points=bench,
                chip_used=chip,
                is_totw=is_totw,
                score_status=ScoreState.FINAL,
            )
        )
        await self.session.flush()

    async def squad(self, manager: Manager, elements: list[int], *, benched: int = 0) -> None:
        """Give a manager a squad. ``benched`` elements sit at multiplier 0."""

        snapshot = ManagerPickSnapshot(
            manager_id=manager.id,
            gameweek_number=GAMEWEEK,
            revision=1,
            payload_hash=f"hash-{manager.id}",
            captured_at=CAPTURED_AT,
        )
        self.session.add(snapshot)
        await self.session.flush()
        for position, element_id in enumerate(elements, start=1):
            self.session.add(
                ManagerPickItem(
                    snapshot_id=snapshot.id,
                    element_id=element_id,
                    squad_position=position,
                    multiplier=0 if position > len(elements) - benched else 1,
                )
            )
        await self.session.flush()

    async def player(self, element_id: int, *, name: str, points: int) -> None:
        self.session.add(
            FplPlayer(
                season_id=self.season.id,
                element_id=element_id,
                web_name=name,
                full_name=name,
                team_fpl_id=1,
                element_type=3,
            )
        )
        self.session.add(
            FplPlayerFixtureStat(
                season_id=self.season.id,
                gameweek_number=GAMEWEEK,
                element_id=element_id,
                fixture_fpl_id=100 + element_id,
                total_points=points,
            )
        )
        await self.session.flush()

    async def tie(self, home: Manager, away: Manager, home_score: int, away_score: int) -> None:
        self.session.add(
            H2HMatch(
                schedule_id=self.schedule.id,
                gameweek_number=GAMEWEEK,
                home_manager_id=home.id,
                away_manager_id=away.id,
                home_score=home_score,
                away_score=away_score,
                winner_manager_id=home.id if home_score > away_score else away.id,
                status=MatchStatus.FINAL,
            )
        )
        await self.session.flush()

    def service(self) -> HighlightsService:
        return HighlightsService(self.session, season_id=self.season.id)


def _of(highlights: list, kind: HighlightKind) -> list:
    return [item for item in highlights if item.kind is kind]


@pytest.mark.anyio
async def test_nothing_is_claimed_before_a_gameweek_has_been_scored() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build()

            assert await world.service().latest() == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_player_only_one_manager_owned_is_the_lone_wolf() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=3)
            for manager in world.managers:
                await world.score(manager)

            # Element 10 is owned by everyone, element 11 by one manager only.
            await world.player(10, name="Crowd", points=14)
            await world.player(11, name="Semenyo", points=16)
            await world.squad(world.managers[0], [10, 11])
            await world.squad(world.managers[1], [10])
            await world.squad(world.managers[2], [10])

            found = _of(await world.service().latest(), HighlightKind.LONE_WOLF)

            assert len(found) == 1
            assert found[0].subject == "Semenyo"
            assert found[0].value == 16
            assert found[0].manager_id == world.managers[0].id
            # How many managers he was alone among, for the sentence.
            assert found[0].detail == "3"
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_lone_pick_left_on_the_bench_is_not_a_brave_call() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=2)
            for manager in world.managers:
                await world.score(manager)
            await world.player(10, name="Crowd", points=4)
            await world.player(11, name="Benched", points=20)
            # Element 11 is last, and one element is benched.
            await world.squad(world.managers[0], [10, 11], benched=1)
            await world.squad(world.managers[1], [10])

            assert _of(await world.service().latest(), HighlightKind.LONE_WOLF) == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_quiet_lone_pick_is_not_a_story() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=2)
            for manager in world.managers:
                await world.score(manager)
            await world.player(11, name="Anonymous", points=2)
            await world.squad(world.managers[0], [11])
            await world.squad(world.managers[1], [10])
            await world.player(10, name="Crowd", points=3)

            assert _of(await world.service().latest(), HighlightKind.LONE_WOLF) == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_the_best_score_that_lost_and_the_worst_that_won() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=4)
            for manager in world.managers:
                await world.score(manager)

            # 78 is the highest score of the week and it still loses.
            await world.tie(world.managers[0], world.managers[1], 80, 78)
            # 41 is the lowest score of the week and it still wins.
            await world.tie(world.managers[2], world.managers[3], 41, 30)

            highlights = await world.service().latest()
            unlucky = _of(highlights, HighlightKind.UNLUCKY_LOSER)
            lucky = _of(highlights, HighlightKind.LUCKY_WINNER)

            assert len(unlucky) == 1
            assert unlucky[0].manager_id == world.managers[1].id
            assert unlucky[0].value == 78

            assert len(lucky) == 1
            assert lucky[0].manager_id == world.managers[2].id
            assert lucky[0].value == 41
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_tie_still_being_played_decides_nothing() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=2)
            for manager in world.managers:
                await world.score(manager)
            session.add(
                H2HMatch(
                    schedule_id=world.schedule.id,
                    gameweek_number=GAMEWEEK,
                    home_manager_id=world.managers[0].id,
                    away_manager_id=world.managers[1].id,
                    home_score=60,
                    away_score=59,
                    winner_manager_id=None,
                    status=MatchStatus.LIVE,
                )
            )
            await session.flush()

            highlights = await world.service().latest()

            assert _of(highlights, HighlightKind.UNLUCKY_LOSER) == []
            assert _of(highlights, HighlightKind.LUCKY_WINNER) == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_triple_captain_on_a_blank_is_a_misfire() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=2)
            await world.score(world.managers[0], captain=6, chip="3xc")
            await world.score(world.managers[1], captain=24, chip="3xc")

            found = _of(await world.service().latest(), HighlightKind.CHIP_MISFIRE)

            assert len(found) == 1
            assert found[0].manager_id == world.managers[0].id
            assert found[0].value == 6
            assert found[0].detail == "3xc"
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_wildcard_is_never_second_guessed() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=1)
            await world.score(world.managers[0], captain=2, bench=0, chip="wildcard")

            assert _of(await world.service().latest(), HighlightKind.CHIP_MISFIRE) == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_the_armband_that_did_not_turn_up() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=3)
            await world.score(world.managers[0], captain=30)
            await world.score(world.managers[1], captain=2)
            await world.score(world.managers[2], captain=18)

            highlights = await world.service().latest()
            blank = _of(highlights, HighlightKind.CAPTAIN_BLANK)
            haul = _of(highlights, HighlightKind.CAPTAIN_HAUL)

            assert len(blank) == 1
            assert blank[0].manager_id == world.managers[1].id
            assert blank[0].value == 2
            # The best captain is still celebrated alongside the worst.
            assert haul[0].manager_id == world.managers[0].id
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_captain_who_delivered_is_not_called_a_blank() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=2)
            await world.score(world.managers[0], captain=12)
            await world.score(world.managers[1], captain=8)

            assert _of(await world.service().latest(), HighlightKind.CAPTAIN_BLANK) == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_gameweek_of_ties_for_team_of_the_week_cannot_crowd_out_the_rest() -> None:
    """The old flat cut let one shared award push every other story off."""

    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await Season1(session).build(managers=8)
            for manager in world.managers:
                await world.score(manager, net=90, captain=2, is_totw=True)

            highlights = await world.service().latest()
            kinds = {item.kind for item in highlights}

            assert len(_of(highlights, HighlightKind.TEAM_OF_THE_WEEK)) == 8
            assert HighlightKind.CAPTAIN_BLANK in kinds
            assert HighlightKind.SEASON_HIGH in kinds
    finally:
        await engine.dispose()
