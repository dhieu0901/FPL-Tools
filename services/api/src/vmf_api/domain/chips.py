"""Which chips a manager has played, and which are left.

FPL issues one set of chips for each half of the season: a manager who spent
their Wildcard in GW6 gets another at GW20. The halves line up with the two VMF
Seasons, so "remaining" always means remaining *in this half* — a chip used in
Season 1 is not held against anyone in Season 2.

Nothing here is inferred from a squad. A chip is known only because FPL
reported it on a Gameweek, which is why an unsynchronised Gameweek shows no
chip rather than guessing that none was played.
"""

from __future__ import annotations

from dataclasses import dataclass

#: FPL's own codes, and how they are written for a reader.
CHIP_NAMES: dict[str, str] = {
    "wildcard": "Wildcard",
    "freehit": "Free Hit",
    "bboost": "Bench Boost",
    "3xc": "Triple Captain",
}

#: One of each per half of the season.
CHIPS_PER_HALF: tuple[str, ...] = ("wildcard", "freehit", "bboost", "3xc")

#: Season 2 starts here, and so does the second set of chips.
SECOND_HALF_START = 20


def season_half(gameweek_number: int) -> int:
    """1 for GW1-GW19, 2 from GW20."""

    if gameweek_number < 1:
        raise ValueError("gameweek_number must be at least 1")
    return 1 if gameweek_number < SECOND_HALF_START else 2


def half_range(half: int) -> range:
    if half == 1:
        return range(1, SECOND_HALF_START)
    if half == 2:
        return range(SECOND_HALF_START, 39)
    raise ValueError(f"season half must be 1 or 2, got {half}")


def display_name(code: str | None) -> str | None:
    """The reader-facing name, or the raw code if FPL introduces a new chip."""

    if not code:
        return None
    return CHIP_NAMES.get(code, code)


@dataclass(frozen=True, slots=True)
class ChipStatus:
    """What a manager has spent and what they still hold, this half."""

    #: The chip played in the Gameweek being viewed, if any.
    played_this_gameweek: str | None
    #: Every chip already spent in this half, in the order FPL issues them.
    used: tuple[str, ...]
    remaining: tuple[str, ...]


def chip_status(
    *,
    gameweek_number: int,
    used_by_gameweek: dict[int, str | None],
) -> ChipStatus:
    """Work out a manager's chip position from the Gameweeks FPL has reported.

    ``used_by_gameweek`` maps a Gameweek to the chip played in it. Gameweeks
    outside the current half are ignored, and a chip FPL reports twice in one
    half is still only one chip spent.
    """

    half = season_half(gameweek_number)
    window = half_range(half)
    spent = {
        chip
        for number, chip in used_by_gameweek.items()
        if chip and number in window and number <= gameweek_number
    }

    return ChipStatus(
        played_this_gameweek=used_by_gameweek.get(gameweek_number) or None,
        used=tuple(chip for chip in CHIPS_PER_HALF if chip in spent),
        remaining=tuple(chip for chip in CHIPS_PER_HALF if chip not in spent),
    )
