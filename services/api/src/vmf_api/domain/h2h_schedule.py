from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class ScheduledMatch:
    round_number: int
    home_manager_id: int
    away_manager_id: int


def generate_round_robin_schedule(
    manager_ids: Sequence[int],
    *,
    rounds: int = 35,
    start_gameweek: int = 1,
) -> list[list[ScheduledMatch]]:
    """Generate deterministic, non-repeating rounds with the circle method."""

    participants = list(manager_ids)
    if len(participants) < 2 or len(participants) % 2:
        raise ValueError("an even number of at least two managers is required")
    if len(set(participants)) != len(participants):
        raise ValueError("manager IDs must be unique")

    maximum_rounds = len(participants) - 1
    if not 1 <= rounds <= maximum_rounds:
        raise ValueError(f"rounds must be between 1 and {maximum_rounds}")

    rotation = participants[:]
    schedule: list[list[ScheduledMatch]] = []
    for offset in range(rounds):
        round_number = start_gameweek + offset
        matches: list[ScheduledMatch] = []
        for index in range(len(rotation) // 2):
            first = rotation[index]
            second = rotation[-(index + 1)]
            # Alternating the first pairing balances cosmetic home assignment.
            if offset % 2 == 1 and index == 0:
                first, second = second, first
            matches.append(
                ScheduledMatch(
                    round_number=round_number,
                    home_manager_id=first,
                    away_manager_id=second,
                )
            )
        schedule.append(matches)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return schedule
