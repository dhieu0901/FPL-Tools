"""Turn one manager's picks and the Gameweek's player statistics into a score.

This module is deliberately free of database and network access: every rule in
sections 3.3 to 3.5 of the rulebook is expressed as a pure function over value
objects, so the arithmetic can be tested against worked examples without a
fixture database.

The multiplier published by FPL is the authority for what counted. FPL resolves
automatic substitutions and the transfer of the armband itself and republishes
the squad with updated multipliers, so VMF reads that resolution rather than
re-deriving it from minutes played, which would disagree with the official
score whenever FPL applies an edge case differently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: FPL chip identifiers. ``bboost`` makes the four bench players count, and
#: ``3xc`` raises the captain multiplier to three.
BENCH_BOOST_CHIP = "bboost"
TRIPLE_CAPTAIN_CHIP = "3xc"

#: Squad positions 1 to 11 are the starting eleven; 12 to 15 are the bench.
STARTING_XI_SIZE = 11


@dataclass(frozen=True, slots=True)
class PickInput:
    """One squad member as published for a Gameweek revision."""

    element_id: int
    squad_position: int
    multiplier: int
    is_captain: bool = False
    is_vice_captain: bool = False
    auto_subbed_in: bool = False
    auto_subbed_out: bool = False


@dataclass(frozen=True, slots=True)
class ElementStats:
    """A player's totals for a Gameweek, summed across every fixture.

    Summing at this grain is what makes a Double Gameweek additive: two
    fixtures attached to the same Gameweek contribute two sets of events.
    """

    total_points: int = 0
    minutes: int = 0
    goals_scored: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    bonus: int = 0
    fixture_count: int = 0


@dataclass(frozen=True, slots=True)
class CountedPick:
    """A pick that contributes to the score, with its resolved flags."""

    element_id: int
    squad_position: int
    effective_multiplier: int
    base_points: int
    contribution_points: int
    counted_due_to_bench_boost: bool
    is_effective_captain: bool
    auto_subbed_in: bool


@dataclass(frozen=True, slots=True)
class GameweekScoreComputation:
    """The result of scoring one manager for one Gameweek."""

    gross_points: int
    transfer_cost: int
    net_points: int
    computed_gross_points: int
    captain_points: int
    captain_element_id: int | None
    goals_counted: int
    yellow_cards_counted: int
    red_cards_counted: int
    bench_points: int
    counted: tuple[CountedPick, ...] = field(default=())
    bench_boost_active: bool = False
    reconciled: bool = True

    @property
    def cards_counted(self) -> int:
        """Total cards, where a yellow and a red each count as one."""

        return self.yellow_cards_counted + self.red_cards_counted


def is_bench_boost(active_chip: str | None) -> bool:
    return (active_chip or "").strip().lower() == BENCH_BOOST_CHIP


def is_triple_captain(active_chip: str | None) -> bool:
    return (active_chip or "").strip().lower() == TRIPLE_CAPTAIN_CHIP


def effective_captain(picks: list[PickInput]) -> PickInput | None:
    """Return the pick that actually carries the armband, if any.

    A multiplier above one is the armband: two normally, three under Triple
    Captain. When FPL passes the armband to the vice-captain it moves the
    multiplier with it, so the highest multiplier identifies the holder
    without inspecting minutes. Ordering by ``is_captain`` and then squad
    position keeps the choice deterministic if a payload ever carries two
    picks at the same raised multiplier.
    """

    candidates = [pick for pick in picks if pick.multiplier > 1]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda pick: (pick.multiplier, pick.is_captain, -pick.squad_position),
    )


def compute_gameweek_score(
    picks: list[PickInput],
    stats: dict[int, ElementStats],
    *,
    active_chip: str | None = None,
    transfer_cost: int = 0,
    official_gross_points: int | None = None,
) -> GameweekScoreComputation:
    """Score one manager for one Gameweek.

    ``official_gross_points`` is the value FPL published for the entry. When it
    is supplied it wins, because rulebook section 3.1 makes the published total
    the authority; the total derived from picks is still computed so that a
    disagreement is visible in ``reconciled`` rather than silently absorbed.
    Before FPL publishes an entry's history — during a live Gameweek — the
    derived total is the only available figure and is used directly.
    """

    if transfer_cost < 0:
        raise ValueError("transfer_cost must be non-negative")

    bench_boost = is_bench_boost(active_chip)
    captain = effective_captain(picks)
    captain_element_id = captain.element_id if captain is not None else None

    counted: list[CountedPick] = []
    computed_gross = 0
    bench_points = 0
    goals = 0
    yellows = 0
    reds = 0

    for pick in picks:
        player = stats.get(pick.element_id, ElementStats())
        if pick.multiplier <= 0:
            # Bench players without Bench Boost, and players FPL substituted
            # out, contribute nothing but are still reported as bench points.
            bench_points += player.total_points
            continue

        contribution = player.total_points * pick.multiplier
        computed_gross += contribution
        goals += player.goals_scored
        yellows += player.yellow_cards
        reds += player.red_cards
        counted.append(
            CountedPick(
                element_id=pick.element_id,
                squad_position=pick.squad_position,
                effective_multiplier=pick.multiplier,
                base_points=player.total_points,
                contribution_points=contribution,
                counted_due_to_bench_boost=bench_boost and pick.squad_position > STARTING_XI_SIZE,
                is_effective_captain=captain is not None and pick.element_id == captain.element_id,
                auto_subbed_in=pick.auto_subbed_in,
            )
        )

    captain_points = 0
    if captain is not None:
        captain_points = stats.get(captain.element_id, ElementStats()).total_points * (
            captain.multiplier
        )

    gross = computed_gross if official_gross_points is None else official_gross_points
    return GameweekScoreComputation(
        gross_points=gross,
        transfer_cost=transfer_cost,
        net_points=gross - transfer_cost,
        computed_gross_points=computed_gross,
        captain_points=captain_points,
        captain_element_id=captain_element_id,
        goals_counted=goals,
        yellow_cards_counted=yellows,
        red_cards_counted=reds,
        bench_points=bench_points,
        counted=tuple(counted),
        bench_boost_active=bench_boost,
        reconciled=official_gross_points is None or official_gross_points == computed_gross,
    )
