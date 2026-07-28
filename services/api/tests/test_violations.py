import pytest

from vmf_api.domain.violations import (
    ReviewAction,
    ViolationEvent,
    ViolationStatus,
    disciplinary_state,
    transfer_hit_violation_count,
    transition_violation,
)


@pytest.mark.parametrize(
    ("cost", "expected"),
    [(0, 0), (8, 0), (12, 1), (16, 1), (20, 2), (24, 2), (28, 3)],
)
def test_transfer_hit_violation_levels(cost: int, expected: int) -> None:
    assert transfer_hit_violation_count(cost) == expected


def test_forgotten_chip_exception_never_adds_a_violation() -> None:
    event = ViolationEvent(detected_count=2)
    pending = transition_violation(event, ReviewAction.REQUEST_FORGOTTEN_CHIP_REVIEW)
    approved = transition_violation(pending, ReviewAction.APPROVE_EXCEPTION)
    assert approved.status == ViolationStatus.APPROVED_EXCEPTION
    assert approved.effective_confirmed_count == 0
    assert disciplinary_state(1, approved).cumulative_count == 1


def test_rejected_exception_confirms_all_detected_levels() -> None:
    pending = transition_violation(
        ViolationEvent(detected_count=2),
        ReviewAction.REQUEST_FORGOTTEN_CHIP_REVIEW,
    )
    rejected = transition_violation(pending, ReviewAction.REJECT_EXCEPTION)
    assert rejected.status == ViolationStatus.REJECTED
    assert rejected.effective_confirmed_count == 2


def test_cost_20_immediately_crosses_first_and_second_levels() -> None:
    confirmed = transition_violation(ViolationEvent(2), ReviewAction.CONFIRM)
    state = disciplinary_state(0, confirmed)
    assert state.cumulative_count == 2
    assert state.deposit_forfeited
    assert state.h2h_table_deduction == 6
    assert state.cup_score_invalid_this_gameweek
    assert state.prize_fraction == 0.5
    assert state.removed_from_h2h
    assert state.removed_from_cup
    assert not state.removed_from_competition


def test_cost_28_immediately_removes_manager_from_competition() -> None:
    confirmed = transition_violation(ViolationEvent(3), ReviewAction.CONFIRM)
    assert disciplinary_state(0, confirmed).removed_from_competition


def test_h2h_deduction_is_not_applied_twice() -> None:
    confirmed = transition_violation(ViolationEvent(1), ReviewAction.CONFIRM)
    state = disciplinary_state(1, confirmed)
    assert state.cumulative_count == 2
    assert state.h2h_table_deduction == 0


def test_override_requires_explicit_count() -> None:
    with pytest.raises(ValueError):
        transition_violation(ViolationEvent(1), ReviewAction.OVERRIDE)
    overridden = transition_violation(
        ViolationEvent(3),
        ReviewAction.OVERRIDE,
        overridden_count=1,
    )
    assert overridden.effective_confirmed_count == 1
