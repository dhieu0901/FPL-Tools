from datetime import datetime

from pydantic import BaseModel, Field

from vmf_api.domain.violations import ReviewAction, ViolationStatus
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


class ViolationReviewResponse(BaseModel):
    violation: ViolationResponse
    audit: AuditInfo
