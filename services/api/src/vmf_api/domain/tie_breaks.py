"""The one tie-break chain the 2026/27 rulebook applies to every table.

Classic, H2H and the Cup each sort by their own primary measure first — Classic
points, H2H table points, the Cup match score — and then hand any remaining tie
to the chain below. Keeping it in a single place is what stops the three tables
from quietly disagreeing about who finished ahead.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The five automatic steps, in rulebook order. An unbroken tie falls through
#: to ``ADMIN_DRAW``, which no amount of data can decide.
AUTOMATIC_TIE_BREAK_ORDER: tuple[str, ...] = (
    "totw_count",
    "captain_points",
    "goals",
    "fewer_cards",
    "classic_points",
)

ADMIN_DRAW = "admin_draw"


@dataclass(frozen=True, slots=True)
class TieBreakFacts:
    """The five automatic measures, counted up to the Gameweek being decided."""

    totw_count: int = 0
    captain_points: int = 0
    goals: int = 0
    cards: int = 0
    classic_points: int = 0

    def sort_key(self) -> tuple[int, int, int, int, int]:
        """Higher sorts first, so cards are negated: fewer cards is better."""

        return (
            self.totw_count,
            self.captain_points,
            self.goals,
            -self.cards,
            self.classic_points,
        )


def deciding_step(first: TieBreakFacts, second: TieBreakFacts) -> str:
    """Name the step that separates two managers, or ``admin_draw`` if none does.

    The step is recorded alongside every Cup result, so a manager can see which
    rule put them out rather than only that they went out.
    """

    for step, first_value, second_value in zip(
        AUTOMATIC_TIE_BREAK_ORDER, first.sort_key(), second.sort_key(), strict=True
    ):
        if first_value != second_value:
            return step
    return ADMIN_DRAW
