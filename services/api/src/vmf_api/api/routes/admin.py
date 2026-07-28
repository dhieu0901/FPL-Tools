from typing import Annotated

from fastapi import APIRouter, Query

from vmf_api.api.deps import AdminActorDep, SessionDep
from vmf_api.domain.violations import ViolationStatus
from vmf_api.schemas.admin import (
    AppliedActionsResponse,
    GameweekStateRequest,
    GameweekStateResponse,
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
    violation, decision, applied = await AdminService(session).review_violation(
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
        consequences=AppliedActionsResponse(
            cumulative_count=applied.cumulative_count,
            applied=list(applied.applied),
            h2h_points_deducted=applied.h2h_points_deducted,
            removed_from_competition=applied.removed_from_competition,
        ),
    )


@router.post(
    "/gameweeks/{gameweek_number}/finalize",
    response_model=GameweekStateResponse,
)
async def finalize_gameweek(
    gameweek_number: int,
    request: GameweekStateRequest,
    session: SessionDep,
    actor: AdminActorDep,
) -> GameweekStateResponse:
    """Lock a Gameweek so later corrections cannot rewrite a published result."""

    return await _set_finalized(
        gameweek_number,
        request,
        session=session,
        actor=actor,
        finalized=True,
    )


@router.post(
    "/gameweeks/{gameweek_number}/reopen",
    response_model=GameweekStateResponse,
)
async def reopen_gameweek(
    gameweek_number: int,
    request: GameweekStateRequest,
    session: SessionDep,
    actor: AdminActorDep,
) -> GameweekStateResponse:
    """Reopen a finalized Gameweek so the next scoring pass can recalculate it."""

    return await _set_finalized(
        gameweek_number,
        request,
        session=session,
        actor=actor,
        finalized=False,
    )


async def _set_finalized(
    gameweek_number: int,
    request: GameweekStateRequest,
    *,
    session: SessionDep,
    actor: str,
    finalized: bool,
) -> GameweekStateResponse:
    gameweek, decision = await AdminService(session).set_gameweek_finalized(
        request.season_code,
        gameweek_number,
        finalized=finalized,
        reason=request.reason,
        actor=actor,
    )
    return GameweekStateResponse(
        gameweek_number=gameweek.number,
        is_finalized=gameweek.is_finalized,
        audit=AuditInfo(
            decision_id=decision.id,
            actor=decision.actor,
            before=decision.before_state,
            after=decision.after_state,
        ),
    )
