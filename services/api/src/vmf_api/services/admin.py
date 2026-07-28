from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.errors import ConflictError, NotFoundError
from vmf_api.domain.violations import (
    ViolationEvent,
    ViolationStatus,
    transition_violation,
)
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import DecisionType
from vmf_api.models.governance import AdminDecision, Violation
from vmf_api.repositories.admin import AdminRepository
from vmf_api.schemas.admin import ViolationReviewRequest
from vmf_api.services.violations import AppliedActions, apply_threshold_actions


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
    ) -> tuple[Violation, AdminDecision, AppliedActions]:
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
        # A decision is the only thing that turns a detected violation into a
        # consequence, so the threshold pass runs here and nowhere else.
        applied = await apply_threshold_actions(
            self.session,
            violation.manager_id,
            triggering_violation_id=violation.id,
            decision_id=decision.id,
        )
        await self.session.commit()
        await self.session.refresh(violation)
        await self.session.refresh(decision)
        return violation, decision, applied

    async def set_gameweek_finalized(
        self,
        season_code: str,
        gameweek_number: int,
        *,
        finalized: bool,
        reason: str,
        actor: str,
    ) -> tuple[Gameweek, AdminDecision]:
        """Lock a Gameweek's results, or reopen them for recalculation.

        Finalizing is what stops a settled result from drifting: from that
        point the scoring pass reports the Gameweek as final and a later FPL
        correction raises a difference for review rather than silently
        rewriting a published table. Reopening is deliberately the same
        operation in reverse, so both carry a reason, an actor and an audit
        entry, and neither can happen without one.
        """

        season = await self.session.scalar(
            select(Season).where(Season.fpl_season_code == season_code)
        )
        if season is None:
            raise NotFoundError(f"season {season_code!r} not found")

        gameweek = await self.session.scalar(
            select(Gameweek).where(
                Gameweek.season_id == season.id,
                Gameweek.number == gameweek_number,
            )
        )
        if gameweek is None:
            raise NotFoundError(f"gameweek {gameweek_number} not found in season {season_code!r}")

        if gameweek.is_finalized == finalized:
            state = "finalized" if finalized else "open"
            raise ConflictError(f"gameweek {gameweek_number} is already {state}")

        before = {"is_finalized": gameweek.is_finalized}
        gameweek.is_finalized = finalized
        after = {"is_finalized": gameweek.is_finalized}

        decision = await self.repository.add_decision(
            AdminDecision(
                decision_type=(
                    DecisionType.GAMEWEEK_FINALIZE if finalized else DecisionType.GAMEWEEK_REOPEN
                ),
                actor=actor,
                target_type="gameweek",
                target_id=f"{season_code}:{gameweek_number}",
                reason=reason,
                before_state=before,
                after_state=after,
            )
        )
        await self.session.commit()
        await self.session.refresh(gameweek)
        await self.session.refresh(decision)
        return gameweek, decision
