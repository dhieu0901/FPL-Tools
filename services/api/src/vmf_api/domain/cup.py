from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class CupTieBreakStep(StrEnum):
    MATCH_SCORE = "match_score"
    WALKOVER = "walkover"
    TOTW_COUNT = "totw_count"
    CAPTAIN_POINTS = "captain_points"
    GOALS = "goals"
    FEWER_CARDS = "fewer_cards"
    CLASSIC_POINTS = "classic_points"
    ADMIN_DRAW = "admin_draw"


@dataclass(frozen=True, slots=True)
class CupEntry:
    manager_id: int
    match_score: int
    cumulative_totw_count: int
    captain_points: int
    counted_goals: int
    counted_cards: int
    classic_season_points: int
    disqualified: bool = False


@dataclass(frozen=True, slots=True)
class CupResolution:
    winner_manager_id: int | None
    step: CupTieBreakStep
    requires_admin_draw: bool = False


@dataclass(frozen=True, slots=True)
class CupQualificationGameweek:
    gameweek: int
    net_points: int
    confirmed_violation: bool = False


def cup_qualification_points(scores: Iterable[CupQualificationGameweek]) -> int:
    """Violation Gameweeks contribute zero only to the Cup qualification table."""

    return sum(score.net_points for score in scores if not score.confirmed_violation)


def resolve_cup_match(
    first: CupEntry,
    second: CupEntry,
    *,
    admin_draw_winner_id: int | None = None,
) -> CupResolution:
    if first.manager_id == second.manager_id:
        raise ValueError("a manager cannot play themselves")
    if first.disqualified and second.disqualified:
        return CupResolution(None, CupTieBreakStep.ADMIN_DRAW, requires_admin_draw=True)
    if first.disqualified:
        return CupResolution(second.manager_id, CupTieBreakStep.WALKOVER)
    if second.disqualified:
        return CupResolution(first.manager_id, CupTieBreakStep.WALKOVER)

    comparisons = (
        (CupTieBreakStep.MATCH_SCORE, first.match_score, second.match_score, True),
        (
            CupTieBreakStep.TOTW_COUNT,
            first.cumulative_totw_count,
            second.cumulative_totw_count,
            True,
        ),
        (CupTieBreakStep.CAPTAIN_POINTS, first.captain_points, second.captain_points, True),
        (CupTieBreakStep.GOALS, first.counted_goals, second.counted_goals, True),
        (CupTieBreakStep.FEWER_CARDS, first.counted_cards, second.counted_cards, False),
        (
            CupTieBreakStep.CLASSIC_POINTS,
            first.classic_season_points,
            second.classic_season_points,
            True,
        ),
    )
    for step, first_value, second_value, higher_is_better in comparisons:
        if first_value == second_value:
            continue
        first_wins = first_value > second_value if higher_is_better else first_value < second_value
        return CupResolution(first.manager_id if first_wins else second.manager_id, step)

    valid_ids = {first.manager_id, second.manager_id}
    if admin_draw_winner_id is None:
        return CupResolution(None, CupTieBreakStep.ADMIN_DRAW, requires_admin_draw=True)
    if admin_draw_winner_id not in valid_ids:
        raise ValueError("admin draw winner must be one of the two managers")
    return CupResolution(admin_draw_winner_id, CupTieBreakStep.ADMIN_DRAW)
