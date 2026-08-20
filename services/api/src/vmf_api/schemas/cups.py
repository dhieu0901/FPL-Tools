from pydantic import BaseModel

from vmf_api.domain.cup import CupTieBreakStep
from vmf_api.models.enums import Division, MatchStatus
from vmf_api.schemas.common import ORMModel


class CupCompetitionResponse(ORMModel):
    id: int
    season_id: int
    name: str
    season_half: int
    qualification_end_gameweek: int


class CupMatchResponse(ORMModel):
    id: int
    cup_round_id: int
    tie_id: str
    slot_a_label: str
    slot_b_label: str
    manager_a_id: int | None
    manager_b_id: int | None
    manager_a_score: int | None
    manager_b_score: int | None
    winner_manager_id: int | None
    status: MatchStatus
    tie_break_step_used: CupTieBreakStep | None
    random_draw_result: str | None
    is_third_place_match: bool


class CupRoundResponse(ORMModel):
    id: int
    name: str
    round_order: int
    gameweek_number: int
    has_third_place_match: bool
    matches: list[CupMatchResponse]


class CupBracketResponse(BaseModel):
    """A whole Cup: its identity and every round, drawn or not yet played."""

    competition: CupCompetitionResponse
    rounds: list[CupRoundResponse]


class CupQualificationEntryResponse(BaseModel):
    rank: int
    manager_id: int
    manager_name: str
    team_name: str
    division: Division
    qualification_points: int
    gameweeks_counted: int
    gameweeks_excluded: list[int]
    totw_count: int
    captain_points: int
    enters_at_round: int | None


class CupQualificationResponse(BaseModel):
    season_id: int
    season_half: int
    start_gameweek: int
    end_gameweek: int
    is_settled: bool
    high: list[CupQualificationEntryResponse]
    low: list[CupQualificationEntryResponse]


class CupBracketGenerateRequest(BaseModel):
    season_code: str
    season_half: int
    #: Draw before the cutoff Gameweek is finalized. For rehearsal only: the
    #: table it draws from can still change.
    allow_provisional: bool = False


class CupBracketGenerateResponse(BaseModel):
    cup_id: int
    season_half: int
    rounds_created: int
    matches_created: int
    managers_placed: int


class CupAdvanceRequest(BaseModel):
    gameweek_number: int


class CupAdvanceResponse(BaseModel):
    round_name: str
    gameweek_number: int
    ties_resolved: int
    ties_awaiting_draw: int
    managers_promoted: int
