from __future__ import annotations

from dataclasses import replace
from typing import Any

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
from vmf_api.cli.import_managers import (
    EXPECTED_PER_DIVISION,
    RosterEntry,
    RosterError,
    check_roster_shape,
    import_roster,
    parse_roster,
)
from vmf_api.db.base import Base
from vmf_api.integrations.fpl import FPLClientError
from vmf_api.models.competition import DivisionMembership
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus
from vmf_api.models.manager import Manager, ManagerExternalProfile

SEASON_CODE = "2026/27"


def _row(entry_id: int, division: str = "HIGH", **overrides: str) -> dict[str, str]:
    row = {
        "fpl_entry_id": str(entry_id),
        "manager_name": f"Manager {entry_id}",
        "team_name": f"Team {entry_id}",
        "division": division,
    }
    row.update(overrides)
    return row


def _entries(count: int) -> list[RosterEntry]:
    # The registered team name matches what FakeFPL reports, so only a test
    # that overrides a name produces a rename warning.
    return [
        RosterEntry(
            line=index + 2,
            fpl_entry_id=1000 + index,
            manager_name=f"Manager {1000 + index}",
            team_name=f"Team {1000 + index}",
            division=(
                Division.HIGH if index < EXPECTED_PER_DIVISION[Division.HIGH] else Division.LOW
            ),
        )
        for index in range(count)
    ]


class FakeFPL:
    """Answers entry lookups; a missing id raises like the real gateway."""

    def __init__(self, *, known: set[int] | None = None, team_names: dict[int, str] | None = None):
        self.known = known
        self.team_names = team_names or {}
        self.requested: list[int] = []

    async def entry(self, entry_id: int) -> dict[str, Any]:
        self.requested.append(entry_id)
        if self.known is not None and entry_id not in self.known:
            raise FPLClientError("404", path=f"entry/{entry_id}/")
        return {
            "id": entry_id,
            "name": self.team_names.get(entry_id, f"Team {entry_id}"),
            "player_first_name": "Sim",
            "player_last_name": f"Manager {entry_id}",
        }


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed_season(session: AsyncSession) -> None:
    await bootstrap_season(
        session,
        season_code=SEASON_CODE,
        season_name="VMF Fantasy League 2026/27",
    )
    await session.flush()


def test_a_well_formed_file_parses_without_errors() -> None:
    entries, errors = parse_roster([_row(101), _row(102, "low")])

    assert errors == []
    assert [entry.fpl_entry_id for entry in entries] == [101, 102]
    # The division is accepted in any case and normalised.
    assert entries[1].division is Division.LOW


def test_every_bad_row_is_reported_in_one_pass() -> None:
    entries, errors = parse_roster(
        [
            _row(101),
            _row(102, "MIDDLE"),
            {"fpl_entry_id": "abc", "manager_name": "A", "team_name": "B", "division": "HIGH"},
            {"fpl_entry_id": "104", "manager_name": "", "team_name": "B", "division": "HIGH"},
            _row(101),
            {"fpl_entry_id": "-1", "manager_name": "A", "team_name": "B", "division": "HIGH"},
        ]
    )

    # Only the first row survives, and each problem is named with its line.
    assert [entry.fpl_entry_id for entry in entries] == [101]
    assert len(errors) == 5
    assert "line 3" in errors[0] and "MIDDLE" in errors[0]
    assert "line 4" in errors[1] and "not a number" in errors[1]
    assert "line 5" in errors[2] and "manager_name" in errors[2]
    assert "line 6" in errors[3] and "already appears on line 2" in errors[3]
    assert "line 7" in errors[4] and "positive" in errors[4]


def test_a_name_longer_than_the_column_is_rejected() -> None:
    _entries_parsed, errors = parse_roster([_row(101, team_name="x" * 121)])

    assert len(errors) == 1
    assert "team_name" in errors[0] and "120" in errors[0]


def test_the_roster_shape_is_checked_against_the_rulebook() -> None:
    assert check_roster_shape(_entries(46)) == []

    problems = check_roster_shape(_entries(45))
    assert any("expected 46 managers, found 45" in problem for problem in problems)
    assert any("division LOW: expected 26, found 25" in problem for problem in problems)

    # The two divisions are different sizes, so a roster that is the right
    # total but the wrong shape has to be caught as well.
    lopsided = _entries(46)
    lopsided[-1] = replace(lopsided[-1], division=Division.HIGH)
    problems = check_roster_shape(lopsided)
    assert any("division HIGH: expected 20, found 21" in problem for problem in problems)
    assert any("division LOW: expected 26, found 25" in problem for problem in problems)


@pytest.mark.anyio
async def test_the_import_creates_managers_memberships_and_profiles() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed_season(session)
            client = FakeFPL()

            result = await import_roster(
                session,
                _entries(40),
                season_code=SEASON_CODE,
                client=client,
            )

            assert result.created == 40
            assert result.memberships_created == 40
            assert result.verified == 40
            assert len(client.requested) == 40

            managers = list(await session.scalars(select(Manager)))
            assert len(managers) == 40
            assert all(
                manager.registration_status is RegistrationStatus.CONFIRMED for manager in managers
            )
            assert all(manager.active_status is ManagerStatus.ACTIVE for manager in managers)
            assert all(manager.season_joined == SEASON_CODE for manager in managers)
            assert sum(manager.division is Division.HIGH for manager in managers) == 20

            memberships = list(await session.scalars(select(DivisionMembership)))
            assert len(memberships) == 40
            # The opening membership covers Classic Season 1 only; Season 2 is
            # decided by promotion and relegation at GW19.
            assert {(row.start_gameweek, row.end_gameweek) for row in memberships} == {(1, 19)}

            profiles = list(await session.scalars(select(ManagerExternalProfile)))
            assert len(profiles) == 40
            assert all(not profile.team_name_changed for profile in profiles)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_entry_fpl_cannot_confirm_aborts_the_whole_import() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed_season(session)
            entries = _entries(40)
            # One mistyped entry id out of forty-six.
            known = {entry.fpl_entry_id for entry in entries} - {entries[7].fpl_entry_id}

            with pytest.raises(RosterError) as error:
                await import_roster(
                    session,
                    entries,
                    season_code=SEASON_CODE,
                    client=FakeFPL(known=known),
                )

            assert str(entries[7].fpl_entry_id) in str(error.value)
            assert "line 9" in str(error.value)
            # Nothing is written, so the roster is never half imported.
            assert await session.scalar(select(Manager)) is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_team_renamed_on_fpl_is_recorded_rather_than_rejected() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed_season(session)
            entries = _entries(40)
            renamed = entries[3]

            result = await import_roster(
                session,
                entries,
                season_code=SEASON_CODE,
                client=FakeFPL(team_names={renamed.fpl_entry_id: "Renamed FC"}),
            )

            assert result.created == 40
            assert len(result.warnings) == 1
            assert "Renamed FC" in result.warnings[0]

            manager = await session.scalar(
                select(Manager).where(Manager.fpl_entry_id == renamed.fpl_entry_id)
            )
            assert manager is not None
            profile = await session.scalar(
                select(ManagerExternalProfile).where(
                    ManagerExternalProfile.manager_id == manager.id
                )
            )
            assert profile is not None
            assert profile.team_name_changed
            assert profile.current_team_name == "Renamed FC"
            # The registered name is what the league competes under.
            assert manager.team_name == renamed.team_name
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_running_the_import_twice_creates_nothing_the_second_time() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed_season(session)
            entries = _entries(40)

            await import_roster(session, entries, season_code=SEASON_CODE, client=FakeFPL())
            second = await import_roster(
                session, entries, season_code=SEASON_CODE, client=FakeFPL()
            )

            assert second.created == 0
            assert second.already_present == 40
            assert second.memberships_created == 0
            assert len(list(await session.scalars(select(Manager)))) == 40
            assert len(list(await session.scalars(select(DivisionMembership)))) == 40
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_changed_division_is_reported_instead_of_silently_applied() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed_season(session)
            entries = _entries(40)
            await import_roster(session, entries, season_code=SEASON_CODE, client=FakeFPL())

            moved = [
                RosterEntry(
                    line=entry.line,
                    fpl_entry_id=entry.fpl_entry_id,
                    manager_name=entry.manager_name,
                    team_name=entry.team_name,
                    division=Division.LOW if entry is entries[0] else entry.division,
                )
                for entry in entries
            ]

            with pytest.raises(RosterError) as error:
                await import_roster(session, moved, season_code=SEASON_CODE, client=FakeFPL())

            assert "already in HIGH" in str(error.value)
            assert "the file says LOW" in str(error.value)

            manager = await session.scalar(
                select(Manager).where(Manager.fpl_entry_id == entries[0].fpl_entry_id)
            )
            assert manager is not None
            assert manager.division is Division.HIGH
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_dry_run_reports_the_same_counts_and_writes_nothing() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed_season(session)

            result = await import_roster(
                session,
                _entries(40),
                season_code=SEASON_CODE,
                client=FakeFPL(),
                dry_run=True,
            )

            assert result.dry_run
            assert result.created == 40
            assert result.memberships_created == 40
            assert result.verified == 40
            assert await session.scalar(select(Manager)) is None
            assert await session.scalar(select(DivisionMembership)) is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_importing_before_the_season_is_bootstrapped_is_refused() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            with pytest.raises(RosterError) as error:
                await import_roster(session, _entries(40), season_code=SEASON_CODE)

            assert "has not been bootstrapped" in str(error.value)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_verification_can_be_skipped_for_offline_use() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed_season(session)

            result = await import_roster(session, _entries(40), season_code=SEASON_CODE)

            assert result.created == 40
            assert result.verified == 0
            # Without the FPL call there is nothing to record a profile from.
            assert await session.scalar(select(ManagerExternalProfile)) is None
    finally:
        await engine.dispose()
