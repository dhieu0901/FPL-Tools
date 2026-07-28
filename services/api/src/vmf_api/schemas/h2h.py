from pydantic import BaseModel, Field

from vmf_api.models.enums import MatchStatus
from vmf_api.schemas.common import ORMModel


class H2HMatchResponse(ORMModel):
    id: int
    schedule_id: int
    gameweek_number: int
    home_manager_id: int
    away_manager_id: int
    home_score: int | None
    away_score: int | None
    winner_manager_id: int | None
    status: MatchStatus
    walkover_reason: str | None
    is_playoff: bool
    bracket_position: str | None


class H2HScheduleGenerateRequest(BaseModel):
    season_id: int = Field(gt=0)
    name: str = Field(default="VMF H2H Group Stage", min_length=1, max_length=80)
    rounds: int = Field(default=35, ge=1, le=39)
    start_gameweek: int = Field(default=1, ge=1, le=38)


class H2HScheduleResponse(BaseModel):
    schedule_id: int
    name: str
    rounds: int
    matches: int
    is_locked: bool


class H2HStandingResponse(BaseModel):
    rank: int
    manager_id: int
    played: int
    wins: int
    draws: int
    losses: int
    points_for: int
    points_against: int
    point_difference: int
    h2h_table_points: int
    full_net_fpl_points: int
