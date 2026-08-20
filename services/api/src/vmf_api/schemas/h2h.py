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


class SquadSlot(BaseModel):
    """One squad member, in the order FPL lists them.

    Positions 1 to 11 are the eleven that started, keeper first and then the
    outfield lines; 12 is the substitute goalkeeper and 13 to 15 the outfield
    bench, which is what ``bench_order`` numbers.
    """

    element_id: int
    web_name: str | None = None
    #: FPL's own club code, as shown in the game: "EVE", "ARS", "NFO".
    club: str | None = None
    squad_position: int
    #: FPL element type: 1 keeper, 2 defender, 3 midfielder, 4 forward.
    element_type: int
    multiplier: int
    points: int
    contribution_points: int
    state: PlayerState
    fixtures_total: int
    fixtures_unresolved: int
    is_starter: bool
    is_substitute_goalkeeper: bool
    bench_order: int | None = None
    is_captain: bool
    is_vice_captain: bool


class MatchupChipPlay(BaseModel):
    """A chip and the Gameweek it was played in."""

    chip: str
    gameweek: int
    #: How managers write it: "BB1" is a Bench Boost played in GW1.
    short: str


class MatchupChips(BaseModel):
    """What a manager has spent and what they still hold, this half."""

    #: The chip played in the Gameweek being viewed, or null for none.
    played_this_gameweek: MatchupChipPlay | None
    #: Every chip spent this half, oldest first.
    used: list[MatchupChipPlay]
    #: Codes only: an unplayed chip has no Gameweek yet.
    remaining: list[str]


class MatchupSide(BaseModel):
    manager_id: int
    #: FPL's own entry id, so the site can link a team through to the same
    #: Gameweek on FPL, where every number on this page originates.
    fpl_entry_id: int
    manager_name: str
    team_name: str
    score: int | None
    gross_points: int | None
    transfer_cost: int | None
    bench_points: int | None
    chip_used: str | None
    captain_points: int | None
    goals_counted: int | None
    chips: MatchupChips
    is_totw: bool
    remaining: MatchupSideRemaining
    squad: list[SquadSlot] = []


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
