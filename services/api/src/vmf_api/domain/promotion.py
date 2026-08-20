"""Who swaps divisions at the end of a Season.

The bottom six of HIGH and the top six of LOW change places, which keeps both
divisions the size they started at. The swap is expressed here as a pure
decision over two ranked tables so it can be reviewed before it is written:
moving a manager between divisions rewrites which table their whole next Season
is judged in, and that is not something to discover after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class DivisionPlace:
    manager_id: int
    rank: int


@dataclass(frozen=True, slots=True)
class Movement:
    manager_id: int
    from_rank: int
    reason: str


@dataclass(frozen=True, slots=True)
class DivisionSwap:
    promoted: tuple[Movement, ...]
    relegated: tuple[Movement, ...]
    #: Ranks that could not be separated, so the swap cannot be written yet.
    contested_ranks: tuple[int, ...]

    @property
    def is_decided(self) -> bool:
        return not self.contested_ranks


def _contested(places: Sequence[DivisionPlace], boundary_ranks: set[int]) -> set[int]:
    """Ranks shared by more than one manager at a boundary that matters."""

    counts: dict[int, int] = {}
    for place in places:
        counts[place.rank] = counts.get(place.rank, 0) + 1
    return {rank for rank in boundary_ranks if counts.get(rank, 0) > 1}


def plan_division_swap(
    *,
    high: Sequence[DivisionPlace],
    low: Sequence[DivisionPlace],
    count: int = 6,
) -> DivisionSwap:
    """The six who go up and the six who come down, or why nobody can.

    A tie on either side of a boundary stops the whole swap rather than half of
    it: promoting five managers and leaving the sixth place open would leave
    the two divisions the wrong size for the Season that follows.
    """

    if count <= 0:
        raise ValueError("count must be positive")
    if len(high) < count or len(low) < count:
        raise ValueError("each division must hold at least as many managers as the swap moves")

    high_ranked = sorted(high, key=lambda place: place.rank)
    low_ranked = sorted(low, key=lambda place: place.rank)

    relegation_zone = high_ranked[-count:]
    promotion_zone = low_ranked[:count]

    # A tie matters only where it straddles a boundary: the last relegated
    # rank in HIGH and the last promoted rank in LOW.
    contested = _contested(high, {place.rank for place in relegation_zone})
    contested |= _contested(low, {place.rank for place in promotion_zone})

    return DivisionSwap(
        promoted=tuple(
            Movement(place.manager_id, place.rank, "top_of_low") for place in promotion_zone
        ),
        relegated=tuple(
            Movement(place.manager_id, place.rank, "bottom_of_high") for place in relegation_zone
        ),
        contested_ranks=tuple(sorted(contested)),
    )
