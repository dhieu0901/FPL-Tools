from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class FPLGameweekState(StrEnum):
    PRESEASON = "preseason"
    UPCOMING = "upcoming"
    LIVE = "live"
    PROVISIONAL = "provisional"
    FINAL = "final"


class FPLStatusResponse(BaseModel):
    gameweek_number: int | None
    gameweek_name: str | None
    state: FPLGameweekState
    deadline: datetime | None
    completed_fixtures: int
    total_fixtures: int
    observed_at: datetime
