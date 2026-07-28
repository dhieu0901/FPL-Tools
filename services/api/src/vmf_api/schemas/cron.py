from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from vmf_api.models.enums import SyncJobType, SyncStatus


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


class SyncJobResult(BaseModel):
    job_type: SyncJobType
    status: SyncStatus
    records_written: int
    payload_changed: bool
    gameweek_number: int | None = None
    detail: dict[str, Any] | None = None
    error: str | None = None


class SyncPlanResponse(BaseModel):
    season_code: str
    gameweek_number: int | None
    run_picks: bool
    run_live: bool
    run_entry_history: bool
    reason: str


class CronSyncResponse(BaseModel):
    status: Literal["executed", "skipped"]
    started_at: datetime
    finished_at: datetime
    reason: Literal["already_running", "season_not_bootstrapped"] | None = None
    plan: SyncPlanResponse | None = None
    jobs: list[SyncJobResult] = []
