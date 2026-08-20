"""Swapping a placeholder roster for the real one, and refusing to when it is late.

The command deletes managers, so the tests that matter most are the ones that
prove it will not: a manager with a Gameweek score, a played match, a violation
or a Cup tie has to survive any run of this.
"""

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
from vmf_api.cli.import_managers import RosterEntry, RosterError
from vmf_api.cli.replace_roster import plan_replacement, replace_roster
from vmf_api.db.base import Base
from vmf_api.domain.violations import ViolationStatus
from vmf_api.models.competition import DivisionMembership, Gameweek, Season
from vmf_api.models.enums import (
    Division,
    ManagerStatus,
    RegistrationStatus,
    ScoreState,
    ViolationType,
)
from vmf_api.models.governance import Violation
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore

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


def _real_roster() -> list[RosterEntry]:
    """46 managers with entry ids that do not overlap the placeholders."""

    entries: list[RosterEntry] = []
    line = 2
    for division, size, base in (
        (Division.HIGH, HIGH_SIZE, 100_000),
        (Division.LOW, LOW_SIZE, 200_000),
    ):
        for index in range(size):
            entries.append(
                RosterEntry(
                    line=line,
                    fpl_entry_id=base + index,
                    manager_name=f"Real {division.value} {index + 1}",
                    team_name=f"Real Team {division.value} {index + 1}",
                    division=division,
                )
            )
            line += 1
    return entries


async def _seed_placeholders(session: AsyncSession, count: int = 40) -> list[Manager]:
    await bootstrap_season(
        session,
        season_code=SEASON_CODE,
        season_name="VMF Fantasy League 2026/27",
    )
    managers: list[Manager] = []
    for index in range(count):
        manager = Manager(
            fpl_entry_id=9000 + index,
            manager_name=f"HLV {index + 1:02d}",
            team_name=f"Doi {index + 1:02d}",
            division=Division.HIGH if index < count // 2 else Division.LOW,
            active_status=ManagerStatus.ACTIVE,
            registration_status=RegistrationStatus.CONFIRMED,
            season_joined=SEASON_CODE,
        )
        session.add(manager)
        managers.append(manager)
    await session.flush()
    return managers


async def _seed_schedule(session: AsyncSession, managers: list[Manager]) -> H2HSchedule:
    season = await session.scalar(select(Season).where(Season.fpl_season_code == SEASON_CODE))
    assert season is not None
    schedule = H2HSchedule(season_id=season.id, name="Group stage")
    session.add(schedule)
    await session.flush()
    for gameweek in range(1, 4):
        for index in range(0, len(managers), 2):
            session.add(
                H2HMatch(
                    schedule_id=schedule.id,
                    gameweek_number=gameweek,
                    home_manager_id=managers[index].id,
                    away_manager_id=managers[index + 1].id,
                )
            )
    await session.flush()
    return schedule


# --------------------------------------------------------------------------
# Planning
# --------------------------------------------------------------------------


@pytest.mark.anyio
async def test_the_plan_names_everything_that_would_change() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            managers = await _seed_placeholders(session)
            await _seed_schedule(session, managers)

            plan = await plan_replacement(session, _real_roster(), season_code=SEASON_CODE)

            assert len(plan.remove) == 40
            assert len(plan.add) == 46
            assert plan.keep == ()
            assert plan.schedules_removed == 1
            assert plan.matches_removed == 60
            assert plan.blocked == ()
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_manager_present_in_both_rosters_is_kept() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            managers = await _seed_placeholders(session)
            # One placeholder turns out to be a real entrant after all.
            managers[0].fpl_entry_id = 100_000
            await session.flush()

            plan = await plan_replacement(session, _real_roster(), season_code=SEASON_CODE)

            assert plan.keep == (managers[0].id,)
            assert len(plan.remove) == 39
            assert len(plan.add) == 45
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_season_that_was_never_bootstrapped_is_rejected() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            with pytest.raises(RosterError, match="has not been bootstrapped"):
                await plan_replacement(session, _real_roster(), season_code=SEASON_CODE)
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# Refusing to delete evidence
# --------------------------------------------------------------------------


@pytest.mark.anyio
async def test_a_manager_with_a_gameweek_score_stops_the_whole_replacement() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            managers = await _seed_placeholders(session)
            gameweek = await session.scalar(select(Gameweek).where(Gameweek.number == 1))
            assert gameweek is not None
            session.add(
                ManagerGameweekScore(
                    manager_id=managers[3].id,
                    gameweek_id=gameweek.id,
                    gross_points=64,
                    transfer_cost=0,
                    net_points=64,
                    score_status=ScoreState.FINAL,
                )
            )
            await session.flush()

            with pytest.raises(RosterError, match="HLV 04.*1 Gameweek score"):
                await replace_roster(
                    session, _real_roster(), season_code=SEASON_CODE, dry_run=False
                )

            # Nothing was removed on the way to the refusal.
            assert await session.scalar(select(Manager).where(Manager.id == managers[3].id))
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_played_match_stops_it_but_an_empty_fixture_does_not() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            managers = await _seed_placeholders(session)
            schedule = await _seed_schedule(session, managers)

            # A scheduled fixture nobody has played is not evidence.
            plan = await plan_replacement(session, _real_roster(), season_code=SEASON_CODE)
            assert plan.blocked == ()

            played = await session.scalar(
                select(H2HMatch).where(H2HMatch.schedule_id == schedule.id)
            )
            assert played is not None
            played.home_score = 70
            played.away_score = 61
            await session.flush()

            plan = await plan_replacement(session, _real_roster(), season_code=SEASON_CODE)
            assert len(plan.blocked) == 2, "both sides of the played match are protected"
            assert "played H2H match" in plan.blocked[0]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_violation_stops_it() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            managers = await _seed_placeholders(session)
            session.add(
                Violation(
                    manager_id=managers[7].id,
                    gameweek_number=2,
                    violation_type=ViolationType.TRANSFER_HIT,
                    status=ViolationStatus.CONFIRMED,
                    detected_count=1,
                    confirmed_count=1,
                )
            )
            await session.flush()

            plan = await plan_replacement(session, _real_roster(), season_code=SEASON_CODE)
            assert any("1 violation" in row for row in plan.blocked)
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# Applying
# --------------------------------------------------------------------------


@pytest.mark.anyio
async def test_a_dry_run_writes_nothing() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            managers = await _seed_placeholders(session)
            await _seed_schedule(session, managers)

            result = await replace_roster(
                session, _real_roster(), season_code=SEASON_CODE, dry_run=True
            )

            assert result.dry_run is True
            assert result.managers_deleted == 0
            assert await session.scalar(select(Manager).where(Manager.fpl_entry_id == 9000))
            assert await session.scalar(select(H2HSchedule))
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_applying_swaps_the_roster_and_clears_the_schedule() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            managers = await _seed_placeholders(session)
            await _seed_schedule(session, managers)

            result = await replace_roster(
                session, _real_roster(), season_code=SEASON_CODE, dry_run=False
            )

            assert result.managers_deleted == 40
            assert result.managers_created == 46
            assert result.memberships_created == 46

            remaining = list((await session.scalars(select(Manager))).unique().all())
            assert len(remaining) == 46
            assert {manager.fpl_entry_id for manager in remaining} == {
                entry.fpl_entry_id for entry in _real_roster()
            }
            assert sum(1 for m in remaining if m.division is Division.HIGH) == HIGH_SIZE
            assert sum(1 for m in remaining if m.division is Division.LOW) == LOW_SIZE

            # The schedule was built from the old roster, so it cannot survive.
            assert (await session.scalars(select(H2HSchedule))).all() == []
            assert (await session.scalars(select(H2HMatch))).all() == []

            memberships = list((await session.scalars(select(DivisionMembership))).unique().all())
            assert len(memberships) == 46
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_running_it_twice_changes_nothing_the_second_time() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            managers = await _seed_placeholders(session)
            await _seed_schedule(session, managers)
            roster = _real_roster()

            await replace_roster(session, roster, season_code=SEASON_CODE, dry_run=False)
            second = await replace_roster(session, roster, season_code=SEASON_CODE, dry_run=False)

            assert second.managers_deleted == 0
            assert second.managers_created == 0
            assert len((await session.scalars(select(Manager))).unique().all()) == 46
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_empty_database_simply_imports_the_roster() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await bootstrap_season(
                session,
                season_code=SEASON_CODE,
                season_name="VMF Fantasy League 2026/27",
            )

            result = await replace_roster(
                session, _real_roster(), season_code=SEASON_CODE, dry_run=False
            )

            assert result.managers_deleted == 0
            assert result.managers_created == 46
    finally:
        await engine.dispose()
