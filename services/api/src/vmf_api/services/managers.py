from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.errors import ConflictError, NotFoundError
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus
from vmf_api.models.manager import Manager
from vmf_api.repositories.managers import ManagerRepository
from vmf_api.schemas.managers import ManagerCreate, ManagerUpdate


class ManagerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ManagerRepository(session)

    async def list(
        self,
        *,
        division: Division | None = None,
        status: ManagerStatus | None = None,
        registration_status: RegistrationStatus | None = None,
    ) -> list[Manager]:
        return await self.repository.list(
            division=division,
            status=status,
            registration_status=registration_status,
        )

    async def get(self, manager_id: int) -> Manager:
        manager = await self.repository.get(manager_id)
        if manager is None:
            raise NotFoundError(f"manager {manager_id} not found")
        return manager

    async def create(self, request: ManagerCreate) -> Manager:
        if await self.repository.get_by_fpl_entry_id(request.fpl_entry_id):
            raise ConflictError(f"FPL entry {request.fpl_entry_id} is already registered")
        payload = request.model_dump(mode="json")
        manager = Manager(**payload)
        try:
            await self.repository.add(manager)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise ConflictError("manager conflicts with an existing record") from error
        return manager

    async def update(self, manager_id: int, request: ManagerUpdate) -> Manager:
        manager = await self.get(manager_id)
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(manager, field, value)
        await self.session.commit()
        await self.session.refresh(manager)
        return manager
