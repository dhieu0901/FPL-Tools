"""The Gameweek closes itself when FPL has closed it, and refuses when it has not."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import vmf_api.models  # noqa: F401  (registers every table on the metadata)
from vmf_api.db.base import Base
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus, SyncStatus
from vmf_api.models.ingestion import FplFixture, SyncRun
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.services.finalization import finalize_if_settled

KICKOFF = datetime(2026, 8, 22, 11, 30)


async def _database() -> tuple[async_sessionmaker[AsyncSession], object]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _settled_gameweek(
    session: AsyncSession,
    *,
    fpl_finished: bool = True,
    fpl_data_checked: bool = True,
    fixture_finished: bool = True,
    managers: int = 2,
    scored: int | None = None,
) -> tuple[Season, Gameweek]:
    season = Season(
        name="VMF Fantasy League 2026/27",
        fpl_season_code="2026/27",
        start_gameweek=1,
        end_gameweek=38,
    )
    session.add(season)
    await session.flush()

    gameweek = Gameweek(
        season_id=season.id,
        number=1,
        deadline_time=KICKOFF,
        fpl_finished=fpl_finished,
        fpl_data_checked=fpl_data_checked,
    )
    session.add(gameweek)
    session.add(
        FplFixture(
            season_id=season.id,
            fixture_fpl_id=1,
            gameweek_number=1,
            kickoff_time=KICKOFF,
            started=True,
            finished=fixture_finished,
            finished_provisional=fixture_finished,
        )
    )
    await session.flush()

    for index in range(managers):
        session.add(
            Manager(
                fpl_entry_id=100 + index,
                manager_name=f"Manager {index}",
                team_name=f"Team {index}",
                division=Division.HIGH,
                active_status=ManagerStatus.ACTIVE,
                registration_status=RegistrationStatus.CONFIRMED,
                season_joined="2026/27",
            )
        )
    await session.flush()

    ids = list(await session.scalars(select(Manager.id)))
    for manager_id in ids[: managers if scored is None else scored]:
        session.add(
            ManagerGameweekScore(
                manager_id=manager_id,
                gameweek_id=gameweek.id,
                gross_points=60,
                transfer_cost=0,
                net_points=60,
            )
        )
    await session.flush()
    return season, gameweek


async def test_a_gameweek_fpl_has_checked_closes_without_anyone_pressing_anything() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season, gameweek = await _settled_gameweek(session)

        outcome = await finalize_if_settled(session, season_id=season.id, gameweek_number=1)
        await session.commit()

    assert outcome.finalized is True
    assert outcome.blocked_by is None
    assert gameweek.is_finalized is True
    await engine.dispose()


async def test_bonus_points_still_landing_hold_the_gameweek_open() -> None:
    """``finished`` goes up at the final whistle; bonus arrives after it."""

    factory, engine = await _database()
    async with factory() as session:
        season, gameweek = await _settled_gameweek(session, fpl_data_checked=False)

        outcome = await finalize_if_settled(session, season_id=season.id, gameweek_number=1)

    assert outcome.finalized is False
    assert outcome.blocked_by == "fpl_has_not_checked_the_data"
    assert gameweek.is_finalized is False
    await engine.dispose()


async def test_an_unfinished_fixture_holds_the_gameweek_open() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season, gameweek = await _settled_gameweek(session, fixture_finished=False)

        outcome = await finalize_if_settled(session, season_id=season.id, gameweek_number=1)

    assert outcome.blocked_by == "a_fixture_is_still_open"
    assert gameweek.is_finalized is False
    await engine.dispose()


async def test_a_manager_without_a_score_holds_the_gameweek_open() -> None:
    """Closing now would fix his absence as his result."""

    factory, engine = await _database()
    async with factory() as session:
        season, gameweek = await _settled_gameweek(session, managers=3, scored=2)

        outcome = await finalize_if_settled(session, season_id=season.id, gameweek_number=1)

    assert outcome.blocked_by == "a_manager_has_no_score"
    assert outcome.detail == {"managers_missing_a_score": 1}
    assert gameweek.is_finalized is False
    await engine.dispose()


async def test_a_score_that_disagrees_with_fpl_holds_the_gameweek_open() -> None:
    """The guard against locking a score that is merely old."""

    factory, engine = await _database()
    async with factory() as session:
        season, gameweek = await _settled_gameweek(session)

        outcome = await finalize_if_settled(
            session,
            season_id=season.id,
            gameweek_number=1,
            unreconciled_manager_ids=(1,),
        )

    assert outcome.blocked_by == "a_score_disagrees_with_fpl"
    assert gameweek.is_finalized is False
    await engine.dispose()


async def test_a_quarantined_source_holds_the_gameweek_open() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season, gameweek = await _settled_gameweek(session)
        session.add(
            SyncRun(
                job_type="picks",
                status=SyncStatus.QUARANTINED,
                gameweek_number=1,
                started_at=KICKOFF,
            )
        )
        await session.flush()

        outcome = await finalize_if_settled(session, season_id=season.id, gameweek_number=1)

    assert outcome.blocked_by == "a_source_is_quarantined"
    assert gameweek.is_finalized is False
    await engine.dispose()


async def test_an_already_closed_gameweek_is_left_alone() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season, gameweek = await _settled_gameweek(session)
        gameweek.is_finalized = True
        await session.flush()

        outcome = await finalize_if_settled(session, season_id=season.id, gameweek_number=1)

    assert outcome.already_final is True
    assert outcome.finalized is False
    await engine.dispose()
