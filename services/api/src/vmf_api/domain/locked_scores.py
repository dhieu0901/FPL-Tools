from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Iterable

from vmf_api.domain.scoring import round_half_up


class ScoreSource(StrEnum):
    OFFICIAL = "official"
    REPLACEMENT_AVERAGE = "replacement_average"
    ADMIN_OVERRIDE = "admin_override"


@dataclass(frozen=True, slots=True)
class DivisionScore:
    manager_id: int
    division: str
    net_points: int
    active: bool = True
    locked_or_deleted: bool = False
    score_source: ScoreSource = ScoreSource.OFFICIAL


@dataclass(frozen=True, slots=True)
class ReplacementAverage:
    division: str
    sample_size: int
    raw: Decimal
    rounded: int


def calculate_division_replacement_average(
    scores: Iterable[DivisionScore],
    division: str,
    *,
    excluded_manager_ids: Iterable[int] = (),
) -> ReplacementAverage:
    """Average only eligible, non-replacement scores from the same division."""

    excluded = set(excluded_manager_ids)
    sample = [
        score.net_points
        for score in scores
        if score.division == division
        and score.manager_id not in excluded
        and score.active
        and not score.locked_or_deleted
        and score.score_source != ScoreSource.REPLACEMENT_AVERAGE
    ]
    if not sample:
        raise ValueError(f"no eligible scores for division {division}")
    raw = sum((Decimal(value) for value in sample), start=Decimal(0)) / Decimal(len(sample))
    return ReplacementAverage(
        division=division,
        sample_size=len(sample),
        raw=raw,
        rounded=round_half_up(raw),
    )
