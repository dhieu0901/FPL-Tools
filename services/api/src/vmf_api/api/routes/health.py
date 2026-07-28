from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from vmf_api import __version__
from vmf_api.api.deps import SessionDep, SettingsDep
from vmf_api.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthResponse)
async def liveness(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=__version__,
        database="ok",
        timestamp=datetime.now(UTC),
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(
    session: SessionDep,
    settings: SettingsDep,
    response: Response,
) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
        database = "ok"
        health_status = "ok"
    except Exception:  # The response deliberately hides driver/credential details.
        database = "unavailable"
        health_status = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status=health_status,
        service=settings.app_name,
        version=__version__,
        database=database,
        timestamp=datetime.now(UTC),
    )
