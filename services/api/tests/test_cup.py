import pytest

from vmf_api.domain.cup import (
    CupEntry,
    CupQualificationGameweek,
    CupTieBreakStep,
    cup_qualification_points,
    resolve_cup_match,
)


def entry(manager_id: int, **overrides: int | bool) -> CupEntry:
    values: dict[str, int | bool] = {
        "manager_id": manager_id,
        "match_score": 70,
        "cumulative_totw_count": 1,
        "captain_points": 14,
        "counted_goals": 2,
        "counted_cards": 1,
        "classic_season_points": 1000,
        "disqualified": False,
    }
    values.update(overrides)
    return CupEntry(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("first_overrides", "second_overrides", "step", "winner"),
    [
        ({"match_score": 71}, {}, CupTieBreakStep.MATCH_SCORE, 1),
        ({"cumulative_totw_count": 2}, {}, CupTieBreakStep.TOTW_COUNT, 1),
        ({"captain_points": 16}, {}, CupTieBreakStep.CAPTAIN_POINTS, 1),
        ({"counted_goals": 3}, {}, CupTieBreakStep.GOALS, 1),
        ({"counted_cards": 2}, {}, CupTieBreakStep.FEWER_CARDS, 2),
        ({"classic_season_points": 999}, {}, CupTieBreakStep.CLASSIC_POINTS, 2),
    ],
)
def test_cup_tie_break_chain(
    first_overrides: dict[str, int],
    second_overrides: dict[str, int],
    step: CupTieBreakStep,
    winner: int,
) -> None:
    result = resolve_cup_match(entry(1, **first_overrides), entry(2, **second_overrides))
    assert result.step == step
    assert result.winner_manager_id == winner


def test_cup_walkover_for_confirmed_invalid_score() -> None:
    result = resolve_cup_match(entry(1, disqualified=True), entry(2))
    assert result.winner_manager_id == 2
    assert result.step == CupTieBreakStep.WALKOVER


def test_fully_tied_cup_match_waits_for_admin_draw() -> None:
    pending = resolve_cup_match(entry(1), entry(2))
    assert pending.requires_admin_draw
    assert pending.winner_manager_id is None
    resolved = resolve_cup_match(entry(1), entry(2), admin_draw_winner_id=2)
    assert resolved.winner_manager_id == 2
    assert resolved.step == CupTieBreakStep.ADMIN_DRAW


def test_violation_gameweeks_are_zero_only_in_cup_qualification_total() -> None:
    scores = [
        CupQualificationGameweek(1, 70),
        CupQualificationGameweek(2, 95, confirmed_violation=True),
        CupQualificationGameweek(3, 80),
    ]
    assert cup_qualification_points(scores) == 150
    assert sum(score.net_points for score in scores) == 245  # Classic remains unchanged.
