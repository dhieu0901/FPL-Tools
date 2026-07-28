from typing import Annotated

from fastapi import APIRouter, Query, status

from vmf_api.api.deps import AdminActorDep, SessionDep
from vmf_api.models.enums import Division, ManagerStatus
from vmf_api.schemas.managers import (
    ManagerAdmin,
    ManagerCreate,
    ManagerPublic,
    ManagerUpdate,
)
from vmf_api.services.managers import ManagerService

router = APIRouter(prefix="/managers", tags=["managers"])


@router.get("", response_model=list[ManagerPublic])
async def list_managers(
    session: SessionDep,
    division: Annotated[Division | None, Query()] = None,
    manager_status: Annotated[ManagerStatus | None, Query(alias="status")] = None,
) -> list[ManagerPublic]:
    managers = await ManagerService(session).list(division=division, status=manager_status)
    return [ManagerPublic.model_validate(manager) for manager in managers]


@router.get("/{manager_id}", response_model=ManagerPublic)
async def get_manager(manager_id: int, session: SessionDep) -> ManagerPublic:
    manager = await ManagerService(session).get(manager_id)
    return ManagerPublic.model_validate(manager)


@router.post("", response_model=ManagerAdmin, status_code=status.HTTP_201_CREATED)
async def create_manager(
    request: ManagerCreate,
    session: SessionDep,
    _: AdminActorDep,
) -> ManagerAdmin:
    manager = await ManagerService(session).create(request)
    return ManagerAdmin.model_validate(manager)


@router.patch("/{manager_id}", response_model=ManagerAdmin)
async def update_manager(
    manager_id: int,
    request: ManagerUpdate,
    session: SessionDep,
    _: AdminActorDep,
) -> ManagerAdmin:
    manager = await ManagerService(session).update(manager_id, request)
    return ManagerAdmin.model_validate(manager)
