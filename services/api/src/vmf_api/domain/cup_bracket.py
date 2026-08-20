"""The two Cup brackets of 2026/27, exactly as the organisers drew them.

Both Cups take the same shape - 40 entrants, two qualifying rounds, then a
round of 16 that runs to a final and a third-place match - but the seeding
differs between the two halves of the season, so neither is derived from the
other. The pairings below are transcribed from the published bracket rather
than generated, because a generated bracket that disagreed with the published
one by a single tie would put the wrong managers out.

A slot is one of two things: a place in the qualification table (``Seed``), or
the winner of an earlier tie (``Winner``). Nothing here touches the database,
so the whole structure can be checked against the published sheet in a test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

DivisionName: TypeAlias = Literal["HIGH", "LOW"]


@dataclass(frozen=True, slots=True)
class Seed:
    """A place in a division's Cup qualification table, for example HIGH 11."""

    division: DivisionName
    rank: int

    def __str__(self) -> str:
        return f"{self.division[0]}{self.rank}"


@dataclass(frozen=True, slots=True)
class Winner:
    """The manager who won an earlier tie in this Cup."""

    tie: str

    def __str__(self) -> str:
        return f"W({self.tie})"


Slot: TypeAlias = Seed | Winner


@dataclass(frozen=True, slots=True)
class Tie:
    tie_id: str
    first: Slot
    second: Slot


@dataclass(frozen=True, slots=True)
class Round:
    name: str
    round_order: int
    gameweek_number: int
    ties: tuple[Tie, ...]
    has_third_place_match: bool = False


@dataclass(frozen=True, slots=True)
class Bracket:
    season_half: Literal[1, 2]
    name: str
    #: The last Gameweek counted by the qualification table.
    qualification_end_gameweek: int
    rounds: tuple[Round, ...]

    @property
    def qualification_start_gameweek(self) -> int:
        return 1 if self.season_half == 1 else 20

    @property
    def final_round(self) -> Round:
        return self.rounds[-1]

    def round_for_gameweek(self, gameweek_number: int) -> Round | None:
        for round_ in self.rounds:
            if round_.gameweek_number == gameweek_number:
                return round_
        return None

    def entry_seeds(self) -> tuple[Seed, ...]:
        """Every qualification place the bracket consumes, in bracket order."""

        return tuple(
            slot
            for round_ in self.rounds
            for tie in round_.ties
            for slot in (tie.first, tie.second)
            if isinstance(slot, Seed)
        )


def _h(rank: int) -> Seed:
    return Seed("HIGH", rank)


def _l(rank: int) -> Seed:
    return Seed("LOW", rank)


def _ties(prefix: str, pairs: tuple[tuple[Slot, Slot], ...]) -> tuple[Tie, ...]:
    return tuple(
        Tie(f"{prefix}{index}", first, second)
        for index, (first, second) in enumerate(pairs, start=1)
    )


# Season 1 --------------------------------------------------------------------
# Ranks are read after GW13; the first ties are played in GW14.

_S1_QUALIFYING_1 = _ties(
    "Q1-",
    (
        (_h(11), _l(22)),
        (_h(12), _l(21)),
        (_l(7), _l(20)),
        (_l(8), _l(19)),
        (_h(13), _l(18)),
        (_h(14), _l(17)),
        (_l(9), _l(16)),
        (_l(10), _l(15)),
        (_h(15), _l(14)),
        (_h(16), _l(13)),
        (_l(11), _h(18)),
        (_l(12), _h(17)),
    ),
)

_S1_QUALIFYING_2 = _ties(
    "Q2-",
    (
        (Winner("Q1-1"), _l(6)),
        (Winner("Q1-2"), _l(5)),
        (Winner("Q1-3"), _l(4)),
        (Winner("Q1-4"), _l(3)),
        (Winner("Q1-5"), _l(2)),
        (Winner("Q1-6"), _h(10)),
        (Winner("Q1-7"), _h(9)),
        (Winner("Q1-8"), _h(8)),
        (Winner("Q1-9"), _h(7)),
        (Winner("Q1-10"), _h(6)),
        (Winner("Q1-11"), _h(5)),
        (Winner("Q1-12"), _h(4)),
    ),
)

_S1_ROUND_OF_16 = _ties(
    "R16-",
    (
        (Winner("Q2-1"), Winner("Q2-9")),
        (Winner("Q2-2"), Winner("Q2-10")),
        (Winner("Q2-3"), Winner("Q2-11")),
        (Winner("Q2-4"), Winner("Q2-12")),
        (Winner("Q2-5"), _l(1)),
        (Winner("Q2-6"), _h(3)),
        (Winner("Q2-7"), _h(2)),
        (Winner("Q2-8"), _h(1)),
    ),
)

# Season 2 --------------------------------------------------------------------
# Same shape, ranks read after GW32, first ties in GW33. The seeding swaps
# which division takes the top places, so the pairings are not a copy.

_S2_QUALIFYING_1 = _ties(
    "Q1-",
    (
        (_l(7), _l(22)),
        (_l(8), _l(21)),
        (_h(11), _l(20)),
        (_h(12), _l(19)),
        (_l(9), _l(18)),
        (_l(10), _l(17)),
        (_h(13), _l(16)),
        (_h(14), _l(15)),
        (_l(11), _h(18)),
        (_l(12), _h(17)),
        (_h(15), _l(14)),
        (_h(16), _l(13)),
    ),
)

_S2_QUALIFYING_2 = _ties(
    "Q2-",
    (
        (Winner("Q1-1"), _h(10)),
        (Winner("Q1-2"), _l(6)),
        (Winner("Q1-3"), _h(9)),
        (Winner("Q1-4"), _h(8)),
        (Winner("Q1-5"), _l(5)),
        (Winner("Q1-6"), _l(4)),
        (Winner("Q1-7"), _h(7)),
        (Winner("Q1-8"), _h(6)),
        (Winner("Q1-9"), _l(3)),
        (Winner("Q1-10"), _l(2)),
        (Winner("Q1-11"), _h(5)),
        (Winner("Q1-12"), _h(4)),
    ),
)

_S2_ROUND_OF_16 = _ties(
    "R16-",
    (
        (Winner("Q2-1"), Winner("Q2-9")),
        (Winner("Q2-2"), Winner("Q2-10")),
        (Winner("Q2-3"), Winner("Q2-11")),
        (Winner("Q2-4"), Winner("Q2-12")),
        (Winner("Q2-5"), _h(3)),
        (Winner("Q2-6"), _l(1)),
        (Winner("Q2-7"), _h(2)),
        (Winner("Q2-8"), _h(1)),
    ),
)

# Both halves share the knockout stage from the quarter-finals onwards.
_QUARTER_FINALS = _ties(
    "QF-",
    (
        (Winner("R16-1"), Winner("R16-5")),
        (Winner("R16-2"), Winner("R16-6")),
        (Winner("R16-3"), Winner("R16-7")),
        (Winner("R16-4"), Winner("R16-8")),
    ),
)

_SEMI_FINALS = _ties(
    "SF-",
    ((Winner("QF-1"), Winner("QF-3")), (Winner("QF-2"), Winner("QF-4"))),
)

_FINAL = (Tie("F", Winner("SF-1"), Winner("SF-2")),)


def _build(
    *,
    season_half: Literal[1, 2],
    qualifying_1: tuple[Tie, ...],
    qualifying_2: tuple[Tie, ...],
    round_of_16: tuple[Tie, ...],
    first_gameweek: int,
) -> Bracket:
    """Lay the six rounds onto consecutive Gameweeks from ``first_gameweek``."""

    return Bracket(
        season_half=season_half,
        name=f"VMF Cup · Season {season_half}",
        qualification_end_gameweek=first_gameweek - 1,
        rounds=(
            Round("Qualifying Round 1", 1, first_gameweek, qualifying_1),
            Round("Qualifying Round 2", 2, first_gameweek + 1, qualifying_2),
            Round("Round of 16", 3, first_gameweek + 2, round_of_16),
            Round("Quarter-finals", 4, first_gameweek + 3, _QUARTER_FINALS),
            Round("Semi-finals", 5, first_gameweek + 4, _SEMI_FINALS),
            Round("Final", 6, first_gameweek + 5, _FINAL, has_third_place_match=True),
        ),
    )


CUP_SEASON_1 = _build(
    season_half=1,
    qualifying_1=_S1_QUALIFYING_1,
    qualifying_2=_S1_QUALIFYING_2,
    round_of_16=_S1_ROUND_OF_16,
    first_gameweek=14,
)

CUP_SEASON_2 = _build(
    season_half=2,
    qualifying_1=_S2_QUALIFYING_1,
    qualifying_2=_S2_QUALIFYING_2,
    round_of_16=_S2_ROUND_OF_16,
    first_gameweek=33,
)

BRACKETS: dict[int, Bracket] = {1: CUP_SEASON_1, 2: CUP_SEASON_2}

#: Ranks below these miss the Cup entirely: HIGH 19-20 and LOW 23-26.
QUALIFYING_RANK_LIMIT: dict[DivisionName, int] = {"HIGH": 18, "LOW": 22}


def bracket_for_half(season_half: int) -> Bracket:
    try:
        return BRACKETS[season_half]
    except KeyError as error:
        raise ValueError(f"season half must be 1 or 2, got {season_half}") from error


def eliminated_ranks(division: DivisionName, division_size: int) -> range:
    """The ranks in a division that do not enter the Cup at all."""

    return range(QUALIFYING_RANK_LIMIT[division] + 1, division_size + 1)
