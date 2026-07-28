from vmf_api.domain.locked_scores import (
    DivisionScore,
    ScoreSource,
    calculate_division_replacement_average,
)


def test_replacement_average_uses_only_same_division_real_active_scores() -> None:
    scores = [
        DivisionScore(1, "HIGH", 67),
        DivisionScore(2, "HIGH", 68),
        DivisionScore(3, "LOW", 100),
        DivisionScore(4, "HIGH", 100, active=False),
        DivisionScore(5, "HIGH", 99, locked_or_deleted=True),
        DivisionScore(6, "HIGH", 90, score_source=ScoreSource.REPLACEMENT_AVERAGE),
    ]
    result = calculate_division_replacement_average(
        scores,
        "HIGH",
        excluded_manager_ids={7},
    )
    assert result.sample_size == 2
    assert str(result.raw) == "67.5"
    assert result.rounded == 68


def test_each_division_has_its_own_average() -> None:
    scores = [
        DivisionScore(1, "HIGH", 60),
        DivisionScore(2, "HIGH", 70),
        DivisionScore(3, "LOW", 40),
        DivisionScore(4, "LOW", 50),
    ]
    assert calculate_division_replacement_average(scores, "HIGH").rounded == 65
    assert calculate_division_replacement_average(scores, "LOW").rounded == 45


def test_target_manager_can_be_explicitly_excluded() -> None:
    scores = [
        DivisionScore(1, "HIGH", 10),
        DivisionScore(2, "HIGH", 21),
        DivisionScore(3, "HIGH", 22),
    ]
    result = calculate_division_replacement_average(
        scores,
        "HIGH",
        excluded_manager_ids={1},
    )
    assert str(result.raw) == "21.5"
    assert result.rounded == 22
