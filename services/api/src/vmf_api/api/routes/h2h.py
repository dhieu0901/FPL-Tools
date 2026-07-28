from typing import Annotated

from fastapi import APIRouter, Query, status

from vmf_api.api.deps import AdminActorDep, SessionDep, SettingsDep
from vmf_api.repositories.h2h import H2HRepository
from vmf_api.schemas.h2h import (
    H2HMatchResponse,
    H2HScheduleGenerateRequest,
    H2HScheduleResponse,
    H2HStandingResponse,
)
from vmf_api.services.h2h import H2HService

router = APIRouter(prefix="/h2h", tags=["h2h"])


@router.get("/fixtures", response_model=list[H2HMatchResponse])
async def fixtures(
    session: SessionDep,
    schedule_id: Annotated[int | None, Query(gt=0)] = None,
    gameweek: Annotated[int | None, Query(ge=1, le=38)] = None,
) -> list[H2HMatchResponse]:
    matches = await H2HRepository(session).list_matches(
        schedule_id=schedule_id,
        gameweek_number=gameweek,
    )
    return [H2HMatchResponse.model_validate(match) for match in matches]


@router.get("/standings", response_model=list[H2HStandingResponse])
async def standings(
    schedule_id: Annotated[int, Query(gt=0)],
    session: SessionDep,
    settings: SettingsDep,
) -> list[H2HStandingResponse]:
    return await H2HService(
        session,
        expected_manager_count=settings.number_of_managers,
    ).standings(schedule_id)


@router.post(
    "/schedule/generate",
    response_model=H2HScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_schedule(
    request: H2HScheduleGenerateRequest,
    session: SessionDep,
    settings: SettingsDep,
    _: AdminActorDep,
) -> H2HScheduleResponse:
    return await H2HService(
        session,
        expected_manager_count=settings.number_of_managers,
    ).generate_schedule(request)
