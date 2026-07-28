from typing import Annotated

from fastapi import APIRouter, Query

from vmf_api.api.deps import AdminActorDep, SessionDep
from vmf_api.domain.violations import ViolationStatus
from vmf_api.schemas.admin import (
    ViolationResponse,
    ViolationReviewRequest,
    ViolationReviewResponse,
)
from vmf_api.schemas.common import AuditInfo
from vmf_api.services.admin import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/violations", response_model=list[ViolationResponse])
async def violations(
    session: SessionDep,
    _: AdminActorDep,
    violation_status: Annotated[ViolationStatus | None, Query(alias="status")] = None,
) -> list[ViolationResponse]:
    rows = await AdminService(session).list_violations(status=violation_status)
    return [ViolationResponse.model_validate(row) for row in rows]


@router.post(
    "/violations/{violation_id}/review",
    response_model=ViolationReviewResponse,
)
async def review_violation(
    violation_id: int,
    request: ViolationReviewRequest,
    session: SessionDep,
    actor: AdminActorDep,
) -> ViolationReviewResponse:
    violation, decision = await AdminService(session).review_violation(
        violation_id,
        request,
        actor=actor,
    )
    return ViolationReviewResponse(
        violation=ViolationResponse.model_validate(violation),
        audit=AuditInfo(
            decision_id=decision.id,
            actor=decision.actor,
            before=decision.before_state,
            after=decision.after_state,
        ),
    )
