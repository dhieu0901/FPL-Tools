from typing import Annotated

from fastapi import APIRouter, Query

from vmf_api.api.deps import AdminActorDep, SessionDep
from vmf_api.models.enums import Division
from vmf_api.schemas.cups import (
    CupAdvanceRequest,
    CupAdvanceResponse,
    CupBracketGenerateRequest,
    CupBracketGenerateResponse,
    CupBracketResponse,
    CupCompetitionResponse,
    CupMatchResponse,
    CupQualificationEntryResponse,
    CupQualificationResponse,
    CupRoundResponse,
)
from vmf_api.services.cups import CupBracketService, CupQualificationService, CupService

router = APIRouter(prefix="/cups", tags=["cups"])

SeasonHalf = Annotated[int, Query(ge=1, le=2)]


@router.get("", response_model=list[CupCompetitionResponse])
async def list_cups(
    session: SessionDep,
    season_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[CupCompetitionResponse]:
    cups = await CupService(session).list_competitions(season_id)
    return [CupCompetitionResponse.model_validate(cup) for cup in cups]


@router.get("/qualification", response_model=CupQualificationResponse)
async def qualification_table(
    session: SessionDep,
    season_id: Annotated[int, Query(gt=0)],
    season_half: SeasonHalf = 1,
) -> CupQualificationResponse:
    """Who is in line for the Cup, and which round each place enters at."""

    table = await CupQualificationService(session).table(
        season_id=season_id,
        season_half=season_half,
    )

    def rows(division: Division) -> list[CupQualificationEntryResponse]:
        return [
            CupQualificationEntryResponse(
                rank=entry.rank,
                manager_id=entry.manager_id,
                manager_name=entry.manager_name,
                team_name=entry.team_name,
                division=entry.division,
                qualification_points=entry.qualification_points,
                gameweeks_counted=entry.gameweeks_counted,
                gameweeks_excluded=list(entry.gameweeks_excluded),
                totw_count=entry.totw_count,
                captain_points=entry.captain_points,
                enters_at_round=entry.enters_at_round,
            )
            for entry in table.entries.get(division, [])
        ]

    return CupQualificationResponse(
        season_id=table.season_id,
        season_half=table.season_half,
        start_gameweek=table.start_gameweek,
        end_gameweek=table.end_gameweek,
        is_settled=table.is_settled,
        high=rows(Division.HIGH),
        low=rows(Division.LOW),
    )


@router.get("/{cup_id}", response_model=CupBracketResponse)
async def cup_bracket(cup_id: int, session: SessionDep) -> CupBracketResponse:
    """The whole Cup, round by round, including ties nobody has reached yet."""

    service = CupService(session)
    competition = await service.get_competition(cup_id)
    rounds = await service.rounds(cup_id)
    return CupBracketResponse(
        competition=CupCompetitionResponse.model_validate(competition),
        rounds=[
            CupRoundResponse(
                id=round_.id,
                name=round_.name,
                round_order=round_.round_order,
                gameweek_number=round_.gameweek_number,
                has_third_place_match=round_.has_third_place_match,
                matches=[CupMatchResponse.model_validate(match) for match in matches],
            )
            for round_, matches in rounds
        ],
    )


@router.get("/{cup_id}/bracket", response_model=list[CupMatchResponse])
async def cup_bracket_matches(cup_id: int, session: SessionDep) -> list[CupMatchResponse]:
    matches = await CupService(session).bracket(cup_id)
    return [CupMatchResponse.model_validate(match) for match in matches]


@router.post("/draw", response_model=CupBracketGenerateResponse)
async def draw_cup(
    request: CupBracketGenerateRequest,
    session: SessionDep,
    _: AdminActorDep,
) -> CupBracketGenerateResponse:
    """Draw a Cup once its qualification Gameweek is finalized."""

    drawn = await CupBracketService(session).generate(
        season_code=request.season_code,
        season_half=request.season_half,
        allow_provisional=request.allow_provisional,
    )
    await session.commit()
    return CupBracketGenerateResponse(
        cup_id=drawn.cup_id,
        season_half=drawn.season_half,
        rounds_created=drawn.rounds_created,
        matches_created=drawn.matches_created,
        managers_placed=drawn.managers_placed,
    )


@router.post("/{cup_id}/advance", response_model=CupAdvanceResponse)
async def advance_cup(
    cup_id: int,
    request: CupAdvanceRequest,
    session: SessionDep,
    _: AdminActorDep,
) -> CupAdvanceResponse:
    """Settle a played round and move its winners into the next one."""

    advanced = await CupBracketService(session).advance(
        cup_id=cup_id,
        gameweek_number=request.gameweek_number,
    )
    await session.commit()
    return CupAdvanceResponse(
        round_name=advanced.round_name,
        gameweek_number=advanced.gameweek_number,
        ties_resolved=advanced.ties_resolved,
        ties_awaiting_draw=advanced.ties_awaiting_draw,
        managers_promoted=advanced.managers_promoted,
    )
