from datetime import datetime

from pydantic import BaseModel, Field

from vmf_api.domain.violations import ReviewAction, ThresholdAction, ViolationStatus
from vmf_api.models.enums import ViolationType
from vmf_api.schemas.common import AuditInfo, ORMModel


class ViolationResponse(ORMModel):
    id: int
    manager_id: int
    gameweek_number: int
    violation_type: ViolationType
    detected_count: int
    confirmed_count: int
    status: ViolationStatus
    admin_note: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None


class ViolationReviewRequest(BaseModel):
    action: ReviewAction
    note: str = Field(min_length=1, max_length=2000)
    overridden_count: int | None = Field(default=None, ge=0)


class AppliedActionsResponse(BaseModel):
    """Consequences this decision made due, from rulebook 9.3."""

    cumulative_count: int
    applied: list[ThresholdAction] = []
    h2h_points_deducted: int = 0
    removed_from_competition: bool = False


class ViolationReviewResponse(BaseModel):
    violation: ViolationResponse
    audit: AuditInfo
    consequences: AppliedActionsResponse


class GameweekStateRequest(BaseModel):
    season_code: str = Field(min_length=4, max_length=16)
    #: Rulebook 11 requires a reason on the record for both directions.
    reason: str = Field(min_length=1, max_length=2000)


class GameweekStateResponse(BaseModel):
    gameweek_number: int
    is_finalized: bool
    audit: AuditInfo
