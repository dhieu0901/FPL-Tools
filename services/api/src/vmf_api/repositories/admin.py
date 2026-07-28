from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.domain.violations import ViolationStatus
from vmf_api.models.governance import AdminDecision, Violation


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_violations(
        self,
        *,
        status: ViolationStatus | None = None,
    ) -> list[Violation]:
        statement = select(Violation).order_by(
            Violation.gameweek_number.desc(),
            Violation.id.desc(),
        )
        if status is not None:
            statement = statement.where(Violation.status == status)
        return list((await self.session.scalars(statement)).all())

    async def get_violation(self, violation_id: int) -> Violation | None:
        return await self.session.get(Violation, violation_id)

    async def add_decision(self, decision: AdminDecision) -> AdminDecision:
        self.session.add(decision)
        await self.session.flush()
        return decision
