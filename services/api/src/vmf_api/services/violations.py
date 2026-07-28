"""Detect excessive transfer costs, and apply a threshold's consequences once.

Detection is automatic and repeatable: it reads the transfer cost FPL
published and raises a violation, but it never decides anything. A violation
only becomes a penalty when an administrator confirms or overrides it, which is
what rulebook 9.2 requires, so this module deliberately separates the two.

The consequences in rulebook 9.3 are keyed by action rather than recomputed
from a running total. That is what makes "the same threshold action is never
applied twice" true even if a case is reviewed, reversed and reviewed again.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.domain.violations import (
    THRESHOLD_FOR_ACTION,
    ThresholdAction,
    ViolationStatus,
    due_threshold_actions,
    transfer_hit_violation_count,
)
from vmf_api.models.enums import ManagerStatus, ViolationType
from vmf_api.models.governance import Violation, ViolationThresholdAction
from vmf_api.models.h2h import H2HPenalty
from vmf_api.models.ingestion import ManagerGameweekHistory
from vmf_api.models.manager import Manager

#: Rulebook 9.3, threshold 1: a single deduction from the H2H table.
H2H_TABLE_DEDUCTION = -6

H2H_PENALTY_REASON = "Excessive transfer cost, rulebook 9.3 threshold 1"


@dataclass(frozen=True, slots=True)
class DetectionResult:
    raised: int = 0
    updated: int = 0
    cleared: int = 0
    scanned: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.raised or self.updated or self.cleared)


@dataclass(frozen=True, slots=True)
class AppliedActions:
    manager_id: int
    cumulative_count: int
    applied: tuple[ThresholdAction, ...] = ()
    h2h_points_deducted: int = 0
    removed_from_competition: bool = False
    detail: dict[str, int] = field(default_factory=dict)


async def detect_transfer_violations(
    session: AsyncSession,
    *,
    allowed_cost: int = 8,
) -> DetectionResult:
    """Raise one violation per Gameweek whose transfer cost exceeds the limit.

    Re-running is safe. A row whose detected count no longer matches the
    published cost is corrected, and one that no longer qualifies at all is
    cleared, because FPL occasionally restates a Gameweek. Rows an
    administrator has already acted on are left alone: reversing a decision is
    an administrative act, not a side effect of a synchronisation.
    """

    history = list(
        await session.execute(
            select(
                ManagerGameweekHistory.manager_id,
                ManagerGameweekHistory.gameweek_number,
                ManagerGameweekHistory.transfer_cost,
            )
        )
    )
    existing = {
        (row.manager_id, row.gameweek_number): row
        for row in await session.scalars(
            select(Violation).where(Violation.violation_type == ViolationType.TRANSFER_HIT)
        )
    }

    raised = 0
    updated = 0
    cleared = 0

    for manager_id, gameweek_number, transfer_cost in history:
        count = transfer_hit_violation_count(transfer_cost or 0, allowed_cost=allowed_cost)
        violation = existing.get((manager_id, gameweek_number))

        if violation is None:
            if count == 0:
                continue
            session.add(
                Violation(
                    manager_id=manager_id,
                    gameweek_number=gameweek_number,
                    violation_type=ViolationType.TRANSFER_HIT,
                    detected_count=count,
                    confirmed_count=0,
                    status=ViolationStatus.DETECTED,
                )
            )
            raised += 1
            continue

        if violation.status is not ViolationStatus.DETECTED:
            continue
        if count == 0:
            await session.delete(violation)
            cleared += 1
        elif violation.detected_count != count:
            violation.detected_count = count
            updated += 1

    await session.flush()
    return DetectionResult(
        raised=raised,
        updated=updated,
        cleared=cleared,
        scanned=len(history),
    )


async def confirmed_violation_count(session: AsyncSession, manager_id: int) -> int:
    """Total confirmed units for one manager across the whole season."""

    total = await session.scalar(
        select(func.coalesce(func.sum(Violation.confirmed_count), 0)).where(
            Violation.manager_id == manager_id
        )
    )
    return int(total or 0)


async def apply_threshold_actions(
    session: AsyncSession,
    manager_id: int,
    *,
    triggering_violation_id: int | None = None,
    decision_id: int | None = None,
) -> AppliedActions:
    """Apply every consequence that has become due and is not already recorded.

    Called after an administrator decision changes a confirmed count. Each
    action writes its own ledger row, and the unique key on
    ``(manager_id, action)`` is what prevents a second ``-6`` from ever
    reaching the H2H table.
    """

    cumulative = await confirmed_violation_count(session, manager_id)
    already = {
        action
        for action in await session.scalars(
            select(ViolationThresholdAction.action).where(
                ViolationThresholdAction.manager_id == manager_id
            )
        )
    }
    outstanding = sorted(
        due_threshold_actions(cumulative) - already,
        key=lambda action: (THRESHOLD_FOR_ACTION[action], action.value),
    )
    if not outstanding:
        return AppliedActions(manager_id=manager_id, cumulative_count=cumulative)

    deducted = 0
    removed = False
    for action in outstanding:
        session.add(
            ViolationThresholdAction(
                manager_id=manager_id,
                action=action,
                threshold=THRESHOLD_FOR_ACTION[action],
                cumulative_count=cumulative,
                triggering_violation_id=triggering_violation_id,
                decision_id=decision_id,
            )
        )
        if action is ThresholdAction.H2H_TABLE_DEDUCTION:
            session.add(
                H2HPenalty(
                    manager_id=manager_id,
                    violation_id=triggering_violation_id,
                    table_point_delta=H2H_TABLE_DEDUCTION,
                    reason=H2H_PENALTY_REASON,
                )
            )
            deducted = H2H_TABLE_DEDUCTION
        elif action is ThresholdAction.REMOVED_FROM_COMPETITION:
            manager = await session.get(Manager, manager_id)
            if manager is not None:
                manager.active_status = ManagerStatus.REMOVED
            removed = True

    await session.flush()
    return AppliedActions(
        manager_id=manager_id,
        cumulative_count=cumulative,
        applied=tuple(outstanding),
        h2h_points_deducted=deducted,
        removed_from_competition=removed,
    )


async def gameweeks_with_confirmed_violations(
    session: AsyncSession,
    manager_ids: Sequence[int] | None = None,
) -> dict[int, set[int]]:
    """Map each manager to the Gameweeks a confirmed violation falls in.

    Rulebook 8.3 zeroes the Cup contribution of every such Gameweek, not only
    the ones in which a Cup tie is played, so the Cup table needs the whole set
    rather than a single flag.
    """

    statement = select(Violation.manager_id, Violation.gameweek_number).where(
        Violation.confirmed_count > 0
    )
    if manager_ids is not None:
        statement = statement.where(Violation.manager_id.in_(manager_ids))

    affected: dict[int, set[int]] = {}
    for manager_id, gameweek_number in await session.execute(statement):
        affected.setdefault(manager_id, set()).add(gameweek_number)
    return affected
