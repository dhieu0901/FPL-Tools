from __future__ import annotations

import pytest

from vmf_api.domain.gameweek_scoring import (
    ElementStats,
    PickInput,
    compute_gameweek_score,
    effective_captain,
    is_bench_boost,
    is_triple_captain,
)


def _squad(
    *,
    captain_element: int = 1,
    captain_multiplier: int = 2,
    bench_multiplier: int = 0,
) -> list[PickInput]:
    """Eleven starters and four bench players, with the armband on one starter."""

    picks = []
    for position in range(1, 12):
        element = position
        picks.append(
            PickInput(
                element_id=element,
                squad_position=position,
                multiplier=(captain_multiplier if element == captain_element else 1),
                is_captain=element == captain_element,
                is_vice_captain=element == 2,
            )
        )
    for position in range(12, 16):
        picks.append(
            PickInput(
                element_id=position,
                squad_position=position,
                multiplier=bench_multiplier,
            )
        )
    return picks


def _flat_stats(points: int = 3) -> dict[int, ElementStats]:
    return {element: ElementStats(total_points=points, minutes=90) for element in range(1, 16)}


def test_chip_helpers_ignore_case_and_absence() -> None:
    assert is_bench_boost("bboost")
    assert is_bench_boost("BBoost")
    assert not is_bench_boost(None)
    assert not is_bench_boost("3xc")
    assert is_triple_captain("3xc")


def test_the_starting_eleven_counts_and_the_bench_does_not() -> None:
    result = compute_gameweek_score(_squad(), _flat_stats(3))

    # Ten starters at 3 points, plus the captain counted twice.
    assert result.computed_gross_points == 10 * 3 + 3 * 2
    assert result.gross_points == 36
    assert result.bench_points == 4 * 3
    assert len(result.counted) == 11
    assert all(not pick.counted_due_to_bench_boost for pick in result.counted)


def test_bench_boost_counts_the_bench_and_records_why() -> None:
    result = compute_gameweek_score(
        _squad(bench_multiplier=1),
        _flat_stats(3),
        active_chip="bboost",
    )

    assert result.bench_boost_active
    assert len(result.counted) == 15
    assert result.bench_points == 0
    assert result.computed_gross_points == 14 * 3 + 3 * 2
    boosted = [pick for pick in result.counted if pick.counted_due_to_bench_boost]
    assert [pick.squad_position for pick in boosted] == [12, 13, 14, 15]


def test_triple_captain_multiplies_the_armband_by_three() -> None:
    picks = _squad(captain_multiplier=3)
    stats = _flat_stats(3) | {1: ElementStats(total_points=12, minutes=90)}

    result = compute_gameweek_score(picks, stats, active_chip="3xc")

    assert result.captain_element_id == 1
    assert result.captain_points == 36
    assert result.computed_gross_points == 10 * 3 + 36


def test_the_armband_follows_the_multiplier_to_the_vice_captain() -> None:
    """FPL republishes the squad with the multiplier moved, so VMF reads it."""

    picks = [
        PickInput(element_id=1, squad_position=1, multiplier=1, is_captain=True),
        PickInput(element_id=2, squad_position=2, multiplier=2, is_vice_captain=True),
    ]
    stats = {1: ElementStats(total_points=0), 2: ElementStats(total_points=9, minutes=90)}

    result = compute_gameweek_score(picks, stats)

    assert result.captain_element_id == 2
    assert result.captain_points == 18


def test_no_effective_armband_gives_zero_captain_points() -> None:
    picks = [
        PickInput(element_id=1, squad_position=1, multiplier=1, is_captain=True),
        PickInput(element_id=2, squad_position=2, multiplier=1, is_vice_captain=True),
    ]

    assert effective_captain(picks) is None
    result = compute_gameweek_score(picks, {1: ElementStats(total_points=5)})
    assert result.captain_points == 0
    assert result.captain_element_id is None


def test_a_captain_who_blanks_still_holds_the_armband() -> None:
    picks = [PickInput(element_id=1, squad_position=1, multiplier=2, is_captain=True)]

    result = compute_gameweek_score(picks, {1: ElementStats(total_points=0, minutes=0)})

    assert result.captain_element_id == 1
    assert result.captain_points == 0


def test_a_player_substituted_out_contributes_nothing() -> None:
    picks = [
        PickInput(element_id=1, squad_position=1, multiplier=0, auto_subbed_out=True),
        PickInput(element_id=12, squad_position=12, multiplier=1, auto_subbed_in=True),
    ]
    stats = {
        1: ElementStats(total_points=0, minutes=0, goals_scored=0),
        12: ElementStats(total_points=6, minutes=90, goals_scored=1),
    }

    result = compute_gameweek_score(picks, stats)

    assert result.computed_gross_points == 6
    assert result.goals_counted == 1
    assert [pick.element_id for pick in result.counted] == [12]
    assert result.counted[0].auto_subbed_in


def test_goals_and_cards_come_only_from_counted_players_and_are_never_multiplied() -> None:
    picks = [
        PickInput(element_id=1, squad_position=1, multiplier=2, is_captain=True),
        PickInput(element_id=2, squad_position=2, multiplier=1),
        PickInput(element_id=12, squad_position=12, multiplier=0),
    ]
    stats = {
        1: ElementStats(total_points=13, goals_scored=2, yellow_cards=1),
        2: ElementStats(total_points=1, goals_scored=0, red_cards=1),
        12: ElementStats(total_points=9, goals_scored=3, yellow_cards=2),
    }

    result = compute_gameweek_score(picks, stats)

    # The captain's two goals are counted once even though his points double.
    assert result.goals_counted == 2
    assert result.yellow_cards_counted == 1
    assert result.red_cards_counted == 1
    assert result.cards_counted == 2
    assert result.bench_points == 9


def test_a_double_gameweek_is_additive_at_the_element_grain() -> None:
    picks = [PickInput(element_id=1, squad_position=1, multiplier=2, is_captain=True)]
    # Two fixtures already summed by the caller: 8 + 5 points, 2 + 1 goals.
    stats = {1: ElementStats(total_points=13, goals_scored=3, fixture_count=2)}

    result = compute_gameweek_score(picks, stats)

    assert result.captain_points == 26
    assert result.goals_counted == 3


def test_the_published_total_wins_over_the_derived_one() -> None:
    result = compute_gameweek_score(
        _squad(),
        _flat_stats(3),
        transfer_cost=4,
        official_gross_points=41,
    )

    assert result.gross_points == 41
    assert result.computed_gross_points == 36
    assert result.net_points == 37
    assert not result.reconciled


def test_agreement_between_the_two_totals_is_reported() -> None:
    result = compute_gameweek_score(_squad(), _flat_stats(3), official_gross_points=36)

    assert result.reconciled
    assert result.net_points == 36


def test_transfer_cost_is_subtracted_exactly_once() -> None:
    result = compute_gameweek_score(_squad(), _flat_stats(3), transfer_cost=8)

    assert result.gross_points == 36
    assert result.net_points == 28


def test_a_negative_transfer_cost_is_rejected() -> None:
    with pytest.raises(ValueError):
        compute_gameweek_score(_squad(), _flat_stats(3), transfer_cost=-4)


def test_a_player_without_statistics_scores_zero_rather_than_failing() -> None:
    picks = [PickInput(element_id=99, squad_position=1, multiplier=1)]

    result = compute_gameweek_score(picks, {})

    assert result.computed_gross_points == 0
    assert result.counted[0].base_points == 0
