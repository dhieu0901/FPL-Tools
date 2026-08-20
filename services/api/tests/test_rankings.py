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


def test_classic_ties_break_on_totw_first() -> None:
    values = [
        ClassicStanding(1, 100, totw_count=1),
        ClassicStanding(2, 100, totw_count=2),
        ClassicStanding(3, 100, totw_count=3),
    ]
    assert [item.value.manager_id for item in rank_classic(values)] == [3, 2, 1]


def test_classic_ties_walk_the_rulebook_chain_in_order() -> None:
    """TotW, then captain points, then goals, then fewest cards."""

    base = {"season_points": 100, "totw_count": 2}
    values = [
        ClassicStanding(1, **base, captain_points=90, goals=10, cards=1),
        # Same TotW and captain points as 1, but more goals.
        ClassicStanding(2, **base, captain_points=90, goals=12, cards=4),
        # Beaten on captain points despite the most goals of anyone.
        ClassicStanding(3, **base, captain_points=80, goals=20, cards=0),
        # Level with 1 all the way to cards, and carries fewer of them.
        ClassicStanding(4, **base, captain_points=90, goals=10, cards=0),
    ]
    assert [item.value.manager_id for item in rank_classic(values)] == [2, 4, 1, 3]


def test_classic_highest_gameweek_score_is_no_longer_a_tie_break() -> None:
    """It is still reported, and it decides a separate prize, but not a rank."""

    values = [
        ClassicStanding(1, 100, totw_count=2, highest_gameweek_score=60),
        ClassicStanding(2, 100, totw_count=2, highest_gameweek_score=110),
    ]
    assert [item.rank for item in rank_classic(values)] == [1, 1]


def test_h2h_ranking_uses_agreed_chain() -> None:
    values = [
        H2HStanding(1, 60, 100, 90, 18, 1900),
        H2HStanding(2, 60, 110, 100, 17, 2000),
        H2HStanding(3, 60, 110, 100, 18, 1800),
        H2HStanding(4, 59, 200, 0, 20, 2500),
    ]
    assert [item.value.manager_id for item in rank_h2h(values)] == [3, 2, 1, 4]
