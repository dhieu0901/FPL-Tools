from fastapi import APIRouter, HTTPException, status

from vmf_api.api.deps import FPLClientDep, SessionDep, SettingsDep
from vmf_api.integrations.fpl import FPLClientError
from vmf_api.schemas.fpl import FPLStatusResponse
from vmf_api.services.fpl import (
    FPLStatusPayloadError,
    fetch_fpl_status,
    status_from_ingested_data,
)

router = APIRouter(prefix="/fpl", tags=["fpl"])


@router.get("/status", response_model=FPLStatusResponse)
async def fpl_status(
    session: SessionDep,
    client: FPLClientDep,
    settings: SettingsDep,
) -> FPLStatusResponse:
    """Return the current Gameweek state.

    The dashboard asks for this on every visit, so it is answered from the
    synchronised data first. Calling FPL per request made the whole site fail
    whenever the upstream had a moment of trouble, and put the request volume
    in proportion to traffic rather than to the cron schedule.
    """

    ingested = await status_from_ingested_data(session, settings.active_season_code)
    if ingested is not None:
        return ingested

    # Nothing has been synchronised yet, so a live read is the only answer.
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
