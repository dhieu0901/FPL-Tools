from typing import Literal

from pydantic import BaseModel

from vmf_api.models.enums import Division


class ClassicStandingResponse(BaseModel):
    rank: int
    manager_id: int
    #: FPL's own id, so a team name can link through to their season there.
    fpl_entry_id: int
    manager_name: str
    team_name: str
    division: Division
    gameweeks_scored: int
    season_points: int
    full_season_points: int
    totw_count: int
    highest_gameweek_score: int


class ClassicStandingsEnvelope(BaseModel):
    season_id: int
    period: Literal["season_1", "season_2", "full"]
    division: Division
    start_gameweek: int
    end_gameweek: int
    standings: list[ClassicStandingResponse]
