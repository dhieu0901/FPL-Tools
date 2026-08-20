"""The end-of-Season swap between the two divisions."""

from __future__ import annotations

import pytest

from vmf_api.domain.promotion import DivisionPlace, plan_division_swap


def _places(count: int, *, start: int = 1, ranks: list[int] | None = None) -> list[DivisionPlace]:
    given = ranks or list(range(1, count + 1))
    return [DivisionPlace(manager_id=start + index, rank=given[index]) for index in range(count)]


def test_six_go_up_and_six_come_down() -> None:
    swap = plan_division_swap(high=_places(20), low=_places(26, start=100))

    assert swap.is_decided
    assert [move.manager_id for move in swap.relegated] == [15, 16, 17, 18, 19, 20]
    assert [move.from_rank for move in swap.relegated] == [15, 16, 17, 18, 19, 20]
    assert [move.manager_id for move in swap.promoted] == [100, 101, 102, 103, 104, 105]
    assert [move.from_rank for move in swap.promoted] == [1, 2, 3, 4, 5, 6]


def test_both_divisions_keep_their_size() -> None:
    swap = plan_division_swap(high=_places(20), low=_places(26, start=100))

    assert len(swap.promoted) == len(swap.relegated) == 6
    assert 20 - len(swap.relegated) + len(swap.promoted) == 20
    assert 26 - len(swap.promoted) + len(swap.relegated) == 26


def test_a_tie_at_the_promotion_boundary_stops_the_whole_swap() -> None:
    # Two managers share LOW rank 6, so the sixth promotion place is contested.
    low_ranks = [1, 2, 3, 4, 5, 6, 6, *range(8, 27)]
    swap = plan_division_swap(high=_places(20), low=_places(26, start=100, ranks=low_ranks))

    assert not swap.is_decided
    assert swap.contested_ranks == (6,)


def test_a_tie_at_the_relegation_boundary_stops_it_too() -> None:
    high_ranks = [*range(1, 15), 15, 15, 17, 18, 19, 20]
    swap = plan_division_swap(high=_places(20, ranks=high_ranks), low=_places(26, start=100))

    assert not swap.is_decided
    assert swap.contested_ranks == (15,)


def test_a_tie_clear_of_both_boundaries_is_ignored() -> None:
    # Ranks 2 and 3 are shared, but nothing at rank 15 or below is.
    high_ranks = [1, 2, 2, 4, *range(5, 21)]
    swap = plan_division_swap(high=_places(20, ranks=high_ranks), low=_places(26, start=100))

    assert swap.is_decided
    assert swap.contested_ranks == ()


def test_places_do_not_have_to_arrive_sorted() -> None:
    shuffled = list(reversed(_places(20)))
    swap = plan_division_swap(high=shuffled, low=_places(26, start=100))

    assert [move.from_rank for move in swap.relegated] == [15, 16, 17, 18, 19, 20]


def test_a_division_too_small_to_swap_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least as many managers"):
        plan_division_swap(high=_places(4), low=_places(26, start=100))


def test_a_non_positive_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="count must be positive"):
        plan_division_swap(high=_places(20), low=_places(26, start=100), count=0)
