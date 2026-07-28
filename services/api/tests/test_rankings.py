from vmf_api.domain.rankings import (
    ClassicStanding,
    H2HStanding,
    rank_classic,
    rank_h2h,
)


def test_classic_uses_competition_rank_for_exact_ties() -> None:
    values = [
        ClassicStanding(1, 100, 2, 80),
        ClassicStanding(2, 90, 1, 70),
        ClassicStanding(3, 90, 1, 70),
        ClassicStanding(4, 80, 5, 100),
    ]
    ranked = rank_classic(values)
    assert [(item.value.manager_id, item.rank) for item in ranked] == [
        (1, 1),
        (2, 2),
        (3, 2),
        (4, 4),
    ]


def test_classic_boundary_ties_use_totw_then_highest_gameweek() -> None:
    values = [
        ClassicStanding(1, 100, 1, 80),
        ClassicStanding(2, 100, 2, 70),
        ClassicStanding(3, 100, 2, 90),
    ]
    assert [item.value.manager_id for item in rank_classic(values)] == [3, 2, 1]


def test_h2h_ranking_uses_agreed_chain() -> None:
    values = [
        H2HStanding(1, 60, 100, 90, 18, 1900),
        H2HStanding(2, 60, 110, 100, 17, 2000),
        H2HStanding(3, 60, 110, 100, 18, 1800),
        H2HStanding(4, 59, 200, 0, 20, 2500),
    ]
    assert [item.value.manager_id for item in rank_h2h(values)] == [3, 2, 1, 4]
