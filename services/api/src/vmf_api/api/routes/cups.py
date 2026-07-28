from typing import Annotated

from fastapi import APIRouter, Query

from vmf_api.api.deps import SessionDep
from vmf_api.schemas.cups import CupCompetitionResponse, CupMatchResponse
from vmf_api.services.cups import CupService

router = APIRouter(prefix="/cups", tags=["cups"])


@router.get("", response_model=list[CupCompetitionResponse])
async def list_cups(
    session: SessionDep,
    season_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[CupCompetitionResponse]:
    cups = await CupService(session).list_competitions(season_id)
    return [CupCompetitionResponse.model_validate(cup) for cup in cups]


@router.get("/{cup_id}/bracket", response_model=list[CupMatchResponse])
async def cup_bracket(cup_id: int, session: SessionDep) -> list[CupMatchResponse]:
    matches = await CupService(session).bracket(cup_id)
    return [CupMatchResponse.model_validate(match) for match in matches]
