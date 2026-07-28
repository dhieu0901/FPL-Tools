from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus
from vmf_api.models.manager import Manager


class ManagerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        division: Division | None = None,
        status: ManagerStatus | None = None,
        registration_status: RegistrationStatus | None = None,
    ) -> list[Manager]:
        statement = select(Manager).order_by(Manager.division, Manager.team_name, Manager.id)
        if division is not None:
            statement = statement.where(Manager.division == division)
        if status is not None:
            statement = statement.where(Manager.active_status == status)
        if registration_status is not None:
            statement = statement.where(Manager.registration_status == registration_status)
        return list((await self.session.scalars(statement)).all())

    async def get(self, manager_id: int) -> Manager | None:
        return await self.session.get(Manager, manager_id)

    async def get_by_fpl_entry_id(self, fpl_entry_id: int) -> Manager | None:
        return await self.session.scalar(
            select(Manager).where(Manager.fpl_entry_id == fpl_entry_id)
        )

    async def add(self, manager: Manager) -> Manager:
        self.session.add(manager)
        await self.session.flush()
        await self.session.refresh(manager)
        return manager
