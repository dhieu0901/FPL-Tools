from typing import Annotated, Literal

from fastapi import APIRouter, Query

from vmf_api.api.deps import SessionDep
from vmf_api.models.enums import Division
from vmf_api.schemas.stats import CaptainPickResponse, ChipUseResponse, LeagueStatsResponse
from vmf_api.services.stats import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=LeagueStatsResponse)
async def league_stats(
    session: SessionDep,
    season_id: Annotated[int, Query(gt=0)],
    gameweek: Annotated[int | None, Query(ge=1, le=38)] = None,
    division: Literal["ALL", "HIGH", "LOW"] = "ALL",
) -> LeagueStatsResponse:
    """What the whole league, or one division of it, did with a Gameweek."""

    chosen = None if division == "ALL" else Division(division)
    stats = await StatsService(session, season_id=season_id).league(
        gameweek_number=gameweek, division=chosen
    )
    return LeagueStatsResponse(
        gameweek_number=stats.gameweek_number,
        division=stats.division,
        managers=stats.managers,
        squads_known=stats.squads_known,
        captains=[
            CaptainPickResponse(
                element_id=pick.element_id,
                web_name=pick.web_name,
                club=pick.club,
                count=pick.count,
            )
            for pick in stats.captains
        ],
        chips=[
            ChipUseResponse(
                chip=chip.chip,
                this_gameweek=chip.this_gameweek,
                this_season=chip.this_season,
            )
            for chip in stats.chips
        ],
    )
