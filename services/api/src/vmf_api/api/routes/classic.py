from typing import Annotated, Literal

from fastapi import APIRouter, Query

from vmf_api.api.deps import SessionDep
from vmf_api.models.enums import Division
from vmf_api.schemas.classic import ClassicStandingsEnvelope
from vmf_api.services.classic import ClassicService

router = APIRouter(prefix="/classic", tags=["classic"])


@router.get("/standings", response_model=ClassicStandingsEnvelope)
async def standings(
    session: SessionDep,
    season_id: Annotated[int, Query(gt=0)],
    division: Annotated[Division, Query()],
    period: Annotated[Literal["season_1", "season_2", "full"], Query()] = "season_1",
) -> ClassicStandingsEnvelope:
    return await ClassicService(session).standings(
        season_id=season_id,
        division=division,
        period=period,
    )
