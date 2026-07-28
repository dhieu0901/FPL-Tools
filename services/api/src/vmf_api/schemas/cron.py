from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FPLProbeResponse(BaseModel):
    status: Literal["observed", "skipped"]
    persisted: Literal[False] = False
    observed_at: datetime
    reason: Literal["already_running"] | None = None
    current_gameweek: int | None = None
    event_count: int | None = None
    team_count: int | None = None
    player_count: int | None = None
    fixture_count: int | None = None
