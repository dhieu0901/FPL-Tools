from vmf_api.domain.cup import CupTieBreakStep
from vmf_api.models.enums import MatchStatus
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
    manager_a_id: int | None
    manager_b_id: int | None
    manager_a_score: int | None
    manager_b_score: int | None
    winner_manager_id: int | None
    status: MatchStatus
    tie_break_step_used: CupTieBreakStep | None
    random_draw_result: str | None
    is_third_place_match: bool
