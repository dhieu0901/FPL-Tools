from pydantic import BaseModel, Field

from vmf_api.domain.matchup import PlayerState
from vmf_api.models.enums import MatchStatus, ScoreState
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


class MatchupPlayerLine(BaseModel):
    """One player as he appears across both squads."""

    element_id: int
    web_name: str | None = None
    home_multiplier: int
    away_multiplier: int
    #: Zero cancels out; the sign says which side the differential favours.
    net_multiplier: int
    points: int
    #: Points this player has already moved the margin by.
    swing_points: int
    state: PlayerState
    fixtures_total: int
    fixtures_unresolved: int
    is_home_captain: bool
    is_away_captain: bool


class MatchupSideRemaining(BaseModel):
    players_remaining: int
    effective_players_remaining: int
    #: Reported separately so a Double Gameweek player is not read as two.
    fixtures_remaining: int


class MatchupSide(BaseModel):
    manager_id: int
    manager_name: str
    team_name: str
    score: int | None
    gross_points: int | None
    transfer_cost: int | None
    bench_points: int | None
    chip_used: str | None
    captain_points: int | None
    goals_counted: int | None
    is_totw: bool
    remaining: MatchupSideRemaining


class H2HMatchDetailResponse(BaseModel):
    match_id: int
    gameweek_number: int
    status: MatchStatus
    score_state: ScoreState | None
    is_playoff: bool
    bracket_position: str | None
    walkover_reason: str | None
    home: MatchupSide
    away: MatchupSide
    shared: list[MatchupPlayerLine] = []
    differentials: list[MatchupPlayerLine] = []
    captain_differential: list[MatchupPlayerLine] = []


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
