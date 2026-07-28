from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import ceil


class ViolationStatus(StrEnum):
    DETECTED = "detected"
    PENDING_REVIEW = "pending_review"
    APPROVED_EXCEPTION = "approved_exception"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"


class ReviewAction(StrEnum):
    REQUEST_FORGOTTEN_CHIP_REVIEW = "request_forgotten_chip_review"
    APPROVE_EXCEPTION = "approve_exception"
    REJECT_EXCEPTION = "reject_exception"
    CONFIRM = "confirm"
    OVERRIDE = "override"


class ThresholdAction(StrEnum):
    """A consequence that applies once, when its threshold is first reached."""

    DEPOSIT_FORFEITED = "deposit_forfeited"
    H2H_TABLE_DEDUCTION = "h2h_table_deduction"
    PRIZE_CAPPED = "prize_capped"
    REMOVED_FROM_H2H = "removed_from_h2h"
    REMOVED_FROM_CUP = "removed_from_cup"
    REMOVED_FROM_COMPETITION = "removed_from_competition"


#: The threshold at which each consequence becomes due, from rulebook 9.3.
THRESHOLD_FOR_ACTION: dict[ThresholdAction, int] = {
    ThresholdAction.DEPOSIT_FORFEITED: 1,
    ThresholdAction.H2H_TABLE_DEDUCTION: 1,
    ThresholdAction.PRIZE_CAPPED: 2,
    ThresholdAction.REMOVED_FROM_H2H: 2,
    ThresholdAction.REMOVED_FROM_CUP: 2,
    ThresholdAction.REMOVED_FROM_COMPETITION: 3,
}


def due_threshold_actions(cumulative_confirmed_count: int) -> set[ThresholdAction]:
    """Every consequence a manager's cumulative count has become due for.

    This is a function of the total alone, not of the change that produced it.
    A single Gameweek that raises two units therefore makes both the first and
    the second threshold due at once, which is what rulebook 9.3 requires, and
    an already applied action is filtered out by its ledger row rather than by
    inspecting the previous total.
    """

    if cumulative_confirmed_count < 0:
        raise ValueError("cumulative_confirmed_count must be non-negative")
    return {
        action
        for action, threshold in THRESHOLD_FOR_ACTION.items()
        if cumulative_confirmed_count >= threshold
    }


@dataclass(frozen=True, slots=True)
class ViolationEvent:
    detected_count: int
    status: ViolationStatus = ViolationStatus.DETECTED
    overridden_count: int | None = None

    @property
    def effective_confirmed_count(self) -> int:
        if self.status in {ViolationStatus.CONFIRMED, ViolationStatus.REJECTED}:
            return self.detected_count
        if self.status == ViolationStatus.OVERRIDDEN:
            return self.overridden_count or 0
        return 0


@dataclass(frozen=True, slots=True)
class DisciplinaryState:
    cumulative_count: int
    deposit_forfeited: bool
    h2h_table_deduction: int
    cup_score_invalid_this_gameweek: bool
    prize_fraction: float
    removed_from_h2h: bool
    removed_from_cup: bool
    removed_from_competition: bool


def transfer_hit_violation_count(transfer_cost: int, *, allowed_cost: int = 8) -> int:
    if transfer_cost < 0:
        raise ValueError("transfer_cost must be non-negative")
    if allowed_cost < 0:
        raise ValueError("allowed_cost must be non-negative")
    if transfer_cost <= allowed_cost:
        return 0
    return ceil((transfer_cost - allowed_cost) / 8)


def transition_violation(
    event: ViolationEvent,
    action: ReviewAction,
    *,
    overridden_count: int | None = None,
) -> ViolationEvent:
    transitions: dict[tuple[ViolationStatus, ReviewAction], ViolationStatus] = {
        (
            ViolationStatus.DETECTED,
            ReviewAction.REQUEST_FORGOTTEN_CHIP_REVIEW,
        ): ViolationStatus.PENDING_REVIEW,
        (ViolationStatus.DETECTED, ReviewAction.CONFIRM): ViolationStatus.CONFIRMED,
        (ViolationStatus.DETECTED, ReviewAction.OVERRIDE): ViolationStatus.OVERRIDDEN,
        (
            ViolationStatus.PENDING_REVIEW,
            ReviewAction.APPROVE_EXCEPTION,
        ): ViolationStatus.APPROVED_EXCEPTION,
        (
            ViolationStatus.PENDING_REVIEW,
            ReviewAction.REJECT_EXCEPTION,
        ): ViolationStatus.REJECTED,
        (ViolationStatus.PENDING_REVIEW, ReviewAction.OVERRIDE): ViolationStatus.OVERRIDDEN,
        (ViolationStatus.CONFIRMED, ReviewAction.OVERRIDE): ViolationStatus.OVERRIDDEN,
        (ViolationStatus.REJECTED, ReviewAction.OVERRIDE): ViolationStatus.OVERRIDDEN,
    }
    try:
        next_status = transitions[(event.status, action)]
    except KeyError as error:
        raise ValueError(f"invalid transition: {event.status} -> {action}") from error

    if next_status == ViolationStatus.OVERRIDDEN:
        if overridden_count is None or overridden_count < 0:
            raise ValueError("override requires a non-negative overridden_count")
        return ViolationEvent(event.detected_count, next_status, overridden_count)
    return ViolationEvent(event.detected_count, next_status)


def disciplinary_state(
    previous_confirmed_count: int,
    event: ViolationEvent,
    *,
    h2h_deduction_per_first_level: int = 6,
) -> DisciplinaryState:
    if previous_confirmed_count < 0:
        raise ValueError("previous_confirmed_count must be non-negative")
    added = event.effective_confirmed_count
    cumulative = previous_confirmed_count + added
    first_level_crossed = previous_confirmed_count < 1 <= cumulative

    return DisciplinaryState(
        cumulative_count=cumulative,
        deposit_forfeited=cumulative >= 1,
        # The -6 applies once when the first confirmed level is crossed.
        h2h_table_deduction=h2h_deduction_per_first_level if first_level_crossed else 0,
        cup_score_invalid_this_gameweek=added > 0,
        prize_fraction=0.5 if cumulative >= 2 else 1.0,
        removed_from_h2h=cumulative >= 2,
        removed_from_cup=cumulative >= 2,
        removed_from_competition=cumulative >= 3,
    )
