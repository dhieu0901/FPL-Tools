"""Decide one H2H match from the two Gameweek scores behind it.

Rulebook 6.1 makes the match score ``effective_net_points`` and nothing else,
so this module never reads a squad. What it does carry is the walkover rule
from 9.4: a manager past the second violation threshold forfeits the rest of
their matches, and the technical result must not distort the table it feeds.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

#: A walkover is recorded 0-0 so that it adds nothing to points for or against
#: and creates no artificial point difference.
WALKOVER_SCORE = 0


class Settlement(StrEnum):
    """Why a match holds the result it holds."""

    NOT_PLAYED = "not_played"
    ON_POINTS = "on_points"
    WALKOVER = "walkover"
    #: Both sides forfeited, which the system must never resolve on its own.
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True, slots=True)
class MatchResult:
    settlement: Settlement
    home_score: int | None = None
    away_score: int | None = None
    #: ``None`` with a played settlement means a draw.
    winner: str | None = None
    walkover_reason: str | None = None

    @property
    def is_settled(self) -> bool:
        return self.settlement in {Settlement.ON_POINTS, Settlement.WALKOVER}


def settle_match(
    *,
    home_points: int | None,
    away_points: int | None,
    home_forfeits: bool = False,
    away_forfeits: bool = False,
) -> MatchResult:
    """Resolve a match from both sides' net points.

    A forfeit is decided before the scores are compared: rulebook 9.4 gives the
    opponent the three points regardless of what either manager scored that
    Gameweek, and stores the technical result as ``0-0``.
    """

    if home_forfeits and away_forfeits:
        # Two ineligible sides is an administrative question. Picking a winner
        # here would invent a result nobody decided.
        return MatchResult(
            settlement=Settlement.NEEDS_REVIEW,
            walkover_reason="both managers are ineligible",
        )

    if home_forfeits or away_forfeits:
        winner = "away" if home_forfeits else "home"
        forfeiting = "home" if home_forfeits else "away"
        return MatchResult(
            settlement=Settlement.WALKOVER,
            home_score=WALKOVER_SCORE,
            away_score=WALKOVER_SCORE,
            winner=winner,
            walkover_reason=f"{forfeiting} manager removed from H2H under rulebook 9.3",
        )

    if home_points is None or away_points is None:
        return MatchResult(settlement=Settlement.NOT_PLAYED)

    if home_points > away_points:
        winner = "home"
    elif away_points > home_points:
        winner = "away"
    else:
        winner = None

    return MatchResult(
        settlement=Settlement.ON_POINTS,
        home_score=home_points,
        away_score=away_points,
        winner=winner,
    )
