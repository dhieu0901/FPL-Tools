from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


def calculate_net_points(gross_points: int, transfer_cost: int) -> int:
    """Return VMF net Gameweek points.

    Gross points include FPL chip and captain effects; transfer cost is kept
    separately and subtracted exactly once by VMF.
    """

    if transfer_cost < 0:
        raise ValueError("transfer_cost must be non-negative")
    return gross_points - transfer_cost


def round_half_up(value: Decimal | float | int | str) -> int:
    """Round to an integer with VMF's explicit half-up rule."""

    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def totw_winners(net_scores: dict[int, int], eligible_manager_ids: Iterable[int] | None = None) -> set[int]:
    """Return every eligible manager tied for the highest real net score."""

    eligible = set(eligible_manager_ids) if eligible_manager_ids is not None else set(net_scores)
    candidates = {manager_id: score for manager_id, score in net_scores.items() if manager_id in eligible}
    if not candidates:
        return set()
    best = max(candidates.values())
    return {manager_id for manager_id, score in candidates.items() if score == best}
