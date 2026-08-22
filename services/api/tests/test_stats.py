"""What the league as a whole did with a Gameweek.

Every figure on the stats page is a share, and a share is only as honest as
the pool it is divided by. These pin who counts, whose squad counts, and
which revision of a squad counts.
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
    RegistrationStatus,
    ScoreState,
)
from vmf_api.models.ingestion import (
    FplPlayer,
    FplTeam,
    ManagerPickItem,
    ManagerPickSnapshot,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.services.stats import StatsService

CAPTURED_AT = datetime(2026, 8, 21, 19, 0)
GAMEWEEK = 1


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


class World:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.next_entry = 1000

    async def build(self) -> World:
        self.season = Season(fpl_season_code="2026/27", name="VMF 2026/27")
        self.session.add(self.season)
        await self.session.flush()

        self.gameweek = Gameweek(season_id=self.season.id, number=GAMEWEEK)
        self.session.add(self.gameweek)

        self.session.add_all(
            [
                FplTeam(season_id=self.season.id, team_fpl_id=1, name="Man City", short_name="MCI"),
                FplTeam(season_id=self.season.id, team_fpl_id=2, name="Man Utd", short_name="MUN"),
            ]
        )
        for element_id, name, team in ((10, "Haaland", 1), (11, "B.Fernandes", 2)):
            self.session.add(
                FplPlayer(
                    season_id=self.season.id,
                    element_id=element_id,
                    web_name=name,
                    full_name=name,
                    team_fpl_id=team,
                    element_type=4,
                )
            )
        await self.session.flush()
        return self

    async def manager(
        self,
        *,
        division: Division = Division.HIGH,
        status: ManagerStatus = ManagerStatus.ACTIVE,
        registration: RegistrationStatus = RegistrationStatus.CONFIRMED,
    ) -> Manager:
        self.next_entry += 1
        manager = Manager(
            fpl_entry_id=self.next_entry,
            manager_name=f"Manager {self.next_entry}",
            team_name=f"Team {self.next_entry}",
            division=division,
            active_status=status,
            registration_status=registration,
            season_joined="2026/27",
        )
        self.session.add(manager)
        await self.session.flush()
        return manager

    async def captain(self, manager: Manager, element_id: int, *, revision: int = 1) -> None:
        snapshot = ManagerPickSnapshot(
            manager_id=manager.id,
            gameweek_number=GAMEWEEK,
            revision=revision,
            payload_hash=f"hash-{manager.id}-{revision}",
            captured_at=CAPTURED_AT,
        )
        self.session.add(snapshot)
        await self.session.flush()
        self.session.add(
            ManagerPickItem(
                snapshot_id=snapshot.id,
                element_id=element_id,
                squad_position=1,
                multiplier=2,
                is_captain=True,
            )
        )
        await self.session.flush()

    async def score(self, manager: Manager, *, chip: str | None = None) -> None:
        self.session.add(
            ManagerGameweekScore(
                manager_id=manager.id,
                gameweek_id=self.gameweek.id,
                gross_points=50,
                transfer_cost=0,
                net_points=50,
                chip_used=chip,
                score_status=ScoreState.FINAL,
            )
        )
        await self.session.flush()

    def service(self) -> StatsService:
        return StatsService(self.session, season_id=self.season.id)


@pytest.mark.anyio
async def test_captains_are_counted_across_the_league() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await World(session).build()
            for element_id in (10, 10, 11):
                manager = await world.manager()
                await world.captain(manager, element_id)

            stats = await world.service().league(gameweek_number=GAMEWEEK)

            assert stats.managers == 3
            assert stats.squads_known == 3
            assert [(p.web_name, p.club, p.count) for p in stats.captains] == [
                ("Haaland", "MCI", 2),
                ("B.Fernandes", "MUN", 1),
            ]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_division_is_counted_against_its_own_managers() -> None:
    """A HIGH manager comparing himself to all 46 is comparing two leagues."""

    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await World(session).build()
            await world.captain(await world.manager(division=Division.HIGH), 10)
            await world.captain(await world.manager(division=Division.LOW), 11)
            await world.captain(await world.manager(division=Division.LOW), 11)

            high = await world.service().league(gameweek_number=GAMEWEEK, division=Division.HIGH)
            low = await world.service().league(gameweek_number=GAMEWEEK, division=Division.LOW)

            assert high.managers == 1
            assert [(p.web_name, p.count) for p in high.captains] == [("Haaland", 1)]
            assert low.managers == 2
            assert [(p.web_name, p.count) for p in low.captains] == [("B.Fernandes", 2)]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_only_the_newest_squad_of_a_manager_counts() -> None:
    """A manager who changed his captain must not be counted twice."""

    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await World(session).build()
            manager = await world.manager()
            await world.captain(manager, 10, revision=1)
            await world.captain(manager, 11, revision=2)

            stats = await world.service().league(gameweek_number=GAMEWEEK)

            assert stats.squads_known == 1
            assert [(p.web_name, p.count) for p in stats.captains] == [("B.Fernandes", 1)]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_manager_whose_squad_is_not_published_is_not_a_missing_choice() -> None:
    """Shares divide by squads seen, not by the roster."""

    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await World(session).build()
            await world.captain(await world.manager(), 10)
            await world.manager()  # no picks published yet

            stats = await world.service().league(gameweek_number=GAMEWEEK)

            assert stats.managers == 2
            assert stats.squads_known == 1
            assert stats.captains[0].count == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_removed_manager_is_left_out_of_every_figure() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await World(session).build()
            await world.captain(await world.manager(), 10)
            await world.captain(await world.manager(status=ManagerStatus.REMOVED), 11)
            await world.captain(await world.manager(registration=RegistrationStatus.PENDING), 11)

            stats = await world.service().league(gameweek_number=GAMEWEEK)

            assert stats.managers == 1
            assert [(p.web_name, p.count) for p in stats.captains] == [("Haaland", 1)]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_every_chip_is_listed_whether_it_has_been_played_or_not() -> None:
    """ "Nobody has burned a Wildcard" is a fact about the league too."""

    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await World(session).build()
            await world.score(await world.manager(), chip="bboost")
            await world.score(await world.manager(), chip="bboost")
            await world.score(await world.manager())

            stats = await world.service().league(gameweek_number=GAMEWEEK)
            chips = {chip.chip: chip for chip in stats.chips}

            assert set(chips) == {"wildcard", "freehit", "bboost", "3xc"}
            assert chips["bboost"].this_gameweek == 2
            assert chips["bboost"].this_season == 2
            assert chips["wildcard"].this_gameweek == 0
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_empty_division_reports_nothing_rather_than_dividing_by_zero() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            world = await World(session).build()
            await world.captain(await world.manager(division=Division.HIGH), 10)

            stats = await world.service().league(gameweek_number=GAMEWEEK, division=Division.LOW)

            assert stats.managers == 0
            assert stats.squads_known == 0
            assert stats.captains == ()
            assert stats.chips == ()
    finally:
        await engine.dispose()
