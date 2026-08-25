from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from vmf_api.models.enums import ScoreState, SyncJobType, SyncStatus


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


class ScoringResult(BaseModel):
    """What the scoring pass wrote for the Gameweek this tick worked on."""

    gameweek_number: int
    state: ScoreState | None = None
    managers_scored: int = 0
    totw_manager_ids: list[int] = []
    #: Managers whose derived total disagrees with the total FPL published.
    #: A non-empty list means the pick or live data for them is incomplete.
    unreconciled_manager_ids: list[int] = []
    skipped_reason: str | None = None
    detail: dict[str, int] | None = None


class DetectionResultResponse(BaseModel):
    """Violations raised by this tick. Detection never applies a penalty."""

    scanned: int = 0
    raised: int = 0
    updated: int = 0
    cleared: int = 0


class SettlementResultResponse(BaseModel):
    """H2H matches this tick resolved from the Gameweek scores."""

    gameweek_number: int
    settled: int = 0
    walkovers: int = 0
    #: Matches where both sides forfeited; an administrator decides these.
    needs_review: list[int] = []
    untouched_final: int = 0
    skipped_reason: str | None = None


class RenamedTeamResponse(BaseModel):
    """A manager whose FPL team name no longer matches the registered one."""

    manager_id: int
    fpl_entry_id: int
    registered_team_name: str
    current_team_name: str


class NightlyAuditResponse(BaseModel):
    status: Literal["completed", "skipped"]
    started_at: datetime
    finished_at: datetime
    reason: Literal["already_running"] | None = None
    checked: int = 0
    profiles_created: int = 0
    profiles_updated: int = 0
    #: Managers FPL could not be read for; the rest of the audit still ran.
    unreachable_manager_ids: list[int] = []
    renamed: list[RenamedTeamResponse] = []


class FinalizationResult(BaseModel):
    """Whether the Gameweek closed on this tick, and what stopped it if not."""

    gameweek_number: int
    finalized: bool
    already_final: bool
    blocked_by: str | None = None
    detail: dict[str, int] | None = None


class CronSyncResponse(BaseModel):
    status: Literal["executed", "skipped"]
    started_at: datetime
    finished_at: datetime
    reason: Literal["already_running", "season_not_bootstrapped"] | None = None
    plan: SyncPlanResponse | None = None
    jobs: list[SyncJobResult] = []
    scoring: ScoringResult | None = None
    finalization: FinalizationResult | None = None
    detection: DetectionResultResponse | None = None
    settlement: SettlementResultResponse | None = None
