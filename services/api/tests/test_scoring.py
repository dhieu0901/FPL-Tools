from decimal import Decimal

import pytest

from vmf_api.domain.scoring import calculate_net_points, round_half_up, totw_winners


def test_calculate_net_points_subtracts_transfer_cost_once() -> None:
    assert calculate_net_points(72, 4) == 68
    assert calculate_net_points(5, 8) == -3


def test_calculate_net_points_rejects_negative_cost() -> None:
    with pytest.raises(ValueError):
        calculate_net_points(72, -4)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("67.42", 67),
        ("67.50", 68),
        ("67.81", 68),
        ("-1.50", -2),
        (Decimal("2.5"), 3),
    ],
)
def test_round_half_up(value: object, expected: int) -> None:
    assert round_half_up(value) == expected  # type: ignore[arg-type]


def test_totw_returns_all_tied_eligible_winners() -> None:
    scores = {1: 90, 2: 96, 3: 96, 4: 100}
    assert totw_winners(scores, eligible_manager_ids={1, 2, 3}) == {2, 3}


def test_totw_empty_sample() -> None:
    assert totw_winners({}, eligible_manager_ids=set()) == set()
