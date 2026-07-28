from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.errors import NotFoundError
from vmf_api.domain.violations import (
    ViolationEvent,
    ViolationStatus,
    transition_violation,
)
from vmf_api.models.enums import DecisionType
from vmf_api.models.governance import AdminDecision, Violation
from vmf_api.repositories.admin import AdminRepository
from vmf_api.schemas.admin import ViolationReviewRequest


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AdminRepository(session)

    async def list_violations(
        self,
        *,
        status: ViolationStatus | None = None,
    ) -> list[Violation]:
        return await self.repository.list_violations(status=status)

    async def review_violation(
        self,
        violation_id: int,
        request: ViolationReviewRequest,
        *,
        actor: str,
    ) -> tuple[Violation, AdminDecision]:
        violation = await self.repository.get_violation(violation_id)
        if violation is None:
            raise NotFoundError(f"violation {violation_id} not found")
        before = {
            "status": violation.status.value,
            "confirmed_count": violation.confirmed_count,
            "admin_note": violation.admin_note,
        }
        event = transition_violation(
            ViolationEvent(
                detected_count=violation.detected_count,
                status=violation.status,
                overridden_count=(
                    violation.confirmed_count
                    if violation.status == ViolationStatus.OVERRIDDEN
                    else None
                ),
            ),
            request.action,
            overridden_count=request.overridden_count,
        )
        violation.status = event.status
        violation.confirmed_count = event.effective_confirmed_count
        violation.admin_note = request.note
        violation.reviewed_by = actor
        violation.reviewed_at = datetime.now(UTC)
        after = {
            "status": violation.status.value,
            "confirmed_count": violation.confirmed_count,
            "admin_note": violation.admin_note,
        }
        decision = await self.repository.add_decision(
            AdminDecision(
                decision_type=DecisionType.VIOLATION_REVIEW,
                actor=actor,
                target_type="violation",
                target_id=str(violation.id),
                reason=request.note,
                before_state=before,
                after_state=after,
            )
        )
        await self.session.commit()
        await self.session.refresh(violation)
        await self.session.refresh(decision)
        return violation, decision
