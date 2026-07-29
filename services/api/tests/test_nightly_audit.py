from __future__ import annotations

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
from vmf_api.db.base import Base
from vmf_api.integrations.fpl import FPLClientError
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus
from vmf_api.models.manager import Manager, ManagerExternalProfile
from vmf_api.services.nightly_audit import NightlyAuditService


class FakeFPL:
    def __init__(
        self,
        *,
        team_names: dict[int, str] | None = None,
        unreadable: set[int] | None = None,
    ) -> None:
        self.team_names = team_names or {}
        self.unreadable = unreadable or set()
        self.requested: list[int] = []

    async def entry(self, entry_id: int) -> dict[str, Any]:
        self.requested.append(entry_id)
        if entry_id in self.unreadable:
            raise FPLClientError("503", path=f"entry/{entry_id}/")
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


async def _seed(
    session: AsyncSession,
    *,
    count: int = 3,
    statuses: dict[int, ManagerStatus] | None = None,
) -> list[Manager]:
    managers = []
    for index in range(count):
        entry_id = 9000 + index
        manager = Manager(
            fpl_entry_id=entry_id,
            manager_name=f"Manager {entry_id}",
            team_name=f"Team {entry_id}",
            division=Division.HIGH,
            active_status=(statuses or {}).get(index, ManagerStatus.ACTIVE),
            registration_status=RegistrationStatus.CONFIRMED,
            season_joined="2026/27",
        )
        session.add(manager)
        managers.append(manager)
    await session.flush()
    return managers


@pytest.mark.anyio
async def test_a_clean_league_reports_no_renames() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            client = FakeFPL()

            outcome = await NightlyAuditService(session, client).run()

            assert outcome.checked == 3
            assert outcome.rename_count == 0
            assert sorted(client.requested) == [m.fpl_entry_id for m in managers]
            profiles = list(await session.scalars(select(ManagerExternalProfile)))
            assert len(profiles) == 3
            assert all(not profile.team_name_changed for profile in profiles)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_team_renamed_mid_season_is_reported_without_being_accepted() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            offender = managers[1]

            outcome = await NightlyAuditService(
                session,
                FakeFPL(team_names={offender.fpl_entry_id: "Renamed FC"}),
            ).run()

            assert outcome.rename_count == 1
            report = outcome.renamed[0]
            assert report.manager_id == offender.id
            assert report.registered_team_name == f"Team {offender.fpl_entry_id}"
            assert report.current_team_name == "Renamed FC"

            # The league record is untouched; only the observation moves.
            await session.refresh(offender)
            assert offender.team_name == f"Team {offender.fpl_entry_id}"
            profile = await session.scalar(
                select(ManagerExternalProfile).where(
                    ManagerExternalProfile.manager_id == offender.id
                )
            )
            assert profile is not None
            assert profile.team_name_changed
            assert profile.current_team_name == "Renamed FC"
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_rename_reverted_before_the_next_audit_clears_the_flag() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            offender = managers[0]

            await NightlyAuditService(
                session,
                FakeFPL(team_names={offender.fpl_entry_id: "Renamed FC"}),
            ).run()
            second = await NightlyAuditService(session, FakeFPL()).run()

            assert second.rename_count == 0
            assert second.profiles_updated == 1
            profile = await session.scalar(
                select(ManagerExternalProfile).where(
                    ManagerExternalProfile.manager_id == offender.id
                )
            )
            assert profile is not None
            assert not profile.team_name_changed
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_repeating_the_audit_writes_nothing_when_nothing_changed() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)

            first = await NightlyAuditService(session, FakeFPL()).run()
            second = await NightlyAuditService(session, FakeFPL()).run()

            assert first.profiles_created == 3
            assert second.profiles_created == 0
            assert second.profiles_updated == 0
            assert len(list(await session.scalars(select(ManagerExternalProfile)))) == 3
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_one_unreadable_entry_does_not_abandon_the_rest() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            broken = managers[2]

            outcome = await NightlyAuditService(
                session,
                FakeFPL(unreadable={broken.fpl_entry_id}),
            ).run()

            assert outcome.checked == 2
            assert outcome.unreachable == (broken.id,)
            # The other two were still audited.
            assert len(list(await session.scalars(select(ManagerExternalProfile)))) == 2
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_removed_manager_is_not_audited() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session, statuses={1: ManagerStatus.REMOVED})
            client = FakeFPL()

            outcome = await NightlyAuditService(session, client).run()

            assert outcome.checked == 2
            assert len(client.requested) == 2
    finally:
        await engine.dispose()
