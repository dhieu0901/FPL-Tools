from typing import Annotated

from fastapi import APIRouter, Query, status

from vmf_api.api.deps import AdminActorDep, SessionDep, SettingsDep
from vmf_api.domain.matchup import MatchupComparison, PlayerLine, SquadEntry
from vmf_api.repositories.h2h import H2HRepository
from vmf_api.schemas.h2h import (
    H2HMatchDetailResponse,
    H2HMatchResponse,
    H2HScheduleGenerateRequest,
    H2HScheduleResponse,
    H2HStandingResponse,
    MatchupChips,
    MatchupPlayerLine,
    MatchupSide,
    MatchupSideRemaining,
    SquadSlot,
)
from vmf_api.services.h2h import H2HService
from vmf_api.services.matchup import MatchupService, MatchupView, SideView

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


@router.get("/matches/{match_id}", response_model=H2HMatchDetailResponse)
async def match_detail(match_id: int, session: SessionDep) -> H2HMatchDetailResponse:
    """The live matchup view required by rulebook 12."""

    view = await MatchupService(session).h2h_match(match_id)
    return _match_detail(view)


def _match_detail(view: MatchupView) -> H2HMatchDetailResponse:
    names = view.player_names
    return H2HMatchDetailResponse(
        match_id=view.match_id,
        gameweek_number=view.gameweek_number,
        status=view.status,
        score_state=view.score_state,
        is_playoff=view.is_playoff,
        bracket_position=view.bracket_position,
        walkover_reason=view.walkover_reason,
        home=_side(view.home, view.comparison, view.home_squad, names, home=True),
        away=_side(view.away, view.comparison, view.away_squad, names, home=False),
        shared=[_line(line, names) for line in view.comparison.shared],
        differentials=[_line(line, names) for line in view.comparison.differentials],
        captain_differential=[_line(line, names) for line in view.comparison.captain_differential],
    )


def _side(
    side: SideView,
    comparison: MatchupComparison,
    squad: tuple[SquadEntry, ...],
    names: dict[int, str],
    *,
    home: bool,
) -> MatchupSide:
    remaining = comparison.home_remaining if home else comparison.away_remaining
    return MatchupSide(
        manager_id=side.manager_id,
        fpl_entry_id=side.fpl_entry_id,
        manager_name=side.manager_name,
        team_name=side.team_name,
        score=side.score,
        gross_points=side.gross_points,
        transfer_cost=side.transfer_cost,
        bench_points=side.bench_points,
        chip_used=side.chip_used,
        captain_points=side.captain_points,
        goals_counted=side.goals_counted,
        chips=MatchupChips(
            # Names are resolved in the interface, not here: the API reports
            # the chip FPL played, and the page decides how to write it.
            played_this_gameweek=side.chips.played_this_gameweek,
            used=list(side.chips.used),
            remaining=list(side.chips.remaining),
        ),
        is_totw=side.is_totw,
        remaining=MatchupSideRemaining(
            players_remaining=remaining.players_remaining,
            effective_players_remaining=remaining.effective_players_remaining,
            fixtures_remaining=remaining.fixtures_remaining,
        ),
        squad=[_slot(entry, names) for entry in squad],
    )


def _slot(entry: SquadEntry, names: dict[int, str]) -> SquadSlot:
    return SquadSlot(
        element_id=entry.element_id,
        web_name=names.get(entry.element_id),
        squad_position=entry.squad_position,
        element_type=entry.element_type,
        multiplier=entry.multiplier,
        points=entry.points,
        contribution_points=entry.contribution_points,
        state=entry.state,
        fixtures_total=entry.fixtures_total,
        fixtures_unresolved=entry.fixtures_unresolved,
        is_starter=entry.is_starter,
        is_substitute_goalkeeper=entry.is_substitute_goalkeeper,
        bench_order=entry.bench_order,
        is_captain=entry.is_captain,
        is_vice_captain=entry.is_vice_captain,
    )


def _line(line: PlayerLine, names: dict[int, str]) -> MatchupPlayerLine:
    return MatchupPlayerLine(
        element_id=line.element_id,
        web_name=names.get(line.element_id),
        home_multiplier=line.home_multiplier,
        away_multiplier=line.away_multiplier,
        net_multiplier=line.net_multiplier,
        points=line.points,
        swing_points=line.swing_points,
        state=line.state,
        fixtures_total=line.fixtures_total,
        fixtures_unresolved=line.fixtures_unresolved,
        is_home_captain=line.is_home_captain,
        is_away_captain=line.is_away_captain,
    )


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
