from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Ranked(Generic[T]):
    rank: int
    value: T


def competition_rank(
    values: Iterable[T],
    *,
    key: Callable[[T], tuple[object, ...]],
) -> list[Ranked[T]]:
    """Sort descending and assign competition ranks (1, 2, 2, 4)."""

    ordered = sorted(values, key=key, reverse=True)
    result: list[Ranked[T]] = []
    previous_key: tuple[object, ...] | None = None
    current_rank = 0
    for position, value in enumerate(ordered, start=1):
        value_key = key(value)
        if previous_key is None or value_key != previous_key:
            current_rank = position
            previous_key = value_key
        result.append(Ranked(rank=current_rank, value=value))
    return result


@dataclass(frozen=True, slots=True)
class ClassicStanding:
    manager_id: int
    season_points: int
    totw_count: int = 0
    highest_gameweek_score: int = 0


def rank_classic(values: Iterable[ClassicStanding]) -> list[Ranked[ClassicStanding]]:
    """Rank by the agreed automatic boundary tie-break chain."""

    return competition_rank(
        values,
        key=lambda row: (row.season_points, row.totw_count, row.highest_gameweek_score),
    )


@dataclass(frozen=True, slots=True)
class H2HStanding:
    manager_id: int
    table_points: int
    points_for: int
    points_against: int
    wins: int
    full_net_fpl_points: int

    @property
    def point_difference(self) -> int:
        return self.points_for - self.points_against


def rank_h2h(values: Iterable[H2HStanding]) -> list[Ranked[H2HStanding]]:
    return competition_rank(
        values,
        key=lambda row: (
            row.table_points,
            row.point_difference,
            row.points_for,
            row.wins,
            row.full_net_fpl_points,
        ),
    )
