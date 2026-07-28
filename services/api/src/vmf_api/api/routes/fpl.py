from fastapi import APIRouter, HTTPException, status

from vmf_api.api.deps import FPLClientDep
from vmf_api.integrations.fpl import FPLClientError
from vmf_api.schemas.fpl import FPLStatusResponse
from vmf_api.services.fpl import FPLStatusPayloadError, fetch_fpl_status

router = APIRouter(prefix="/fpl", tags=["fpl"])


@router.get("/status", response_model=FPLStatusResponse)
async def fpl_status(client: FPLClientDep) -> FPLStatusResponse:
    """Return the current official FPL gameweek state without persisting it."""

    try:
        return await fetch_fpl_status(client)
    except FPLClientError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="FPL upstream request failed",
        ) from error
    except FPLStatusPayloadError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="FPL upstream response has an invalid payload",
        ) from error
