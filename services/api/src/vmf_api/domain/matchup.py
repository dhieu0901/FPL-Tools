"""Compare two managers' squads for one Gameweek.

Rulebook section 12 defines what a live matchup must show. The interesting
part is not the score, which both sides already have, but what is still to
come: which players are shared and therefore cancel out, which are genuine
differentials, and how much scoring is still live for each side.

``net_multiplier`` is the quantity that carries all of it. A player both
managers field at the same multiplier contributes zero to the difference
however many points he scores, so he is shared; any other value is a
differential, and its sign says whose.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PlayerState(StrEnum):
    """How much of a player's Gameweek is still to be played."""

    UPCOMING = "upcoming"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class FixtureProgress:
    """Whether each of a player's fixtures has started and finished."""

    total: int = 0
    started: int = 0
    finished: int = 0

    @property
    def unresolved(self) -> int:
        return max(0, self.total - self.finished)

    @property
    def state(self) -> PlayerState:
        if self.total == 0 or self.started == 0:
            return PlayerState.UPCOMING
        if self.finished >= self.total:
            return PlayerState.FINISHED
        return PlayerState.PLAYING


@dataclass(frozen=True, slots=True)
class SidePick:
    element_id: int
    multiplier: int
    is_effective_captain: bool = False


@dataclass(frozen=True, slots=True)
class PlayerLine:
    """One player as he appears across both squads."""

    element_id: int
    home_multiplier: int
    away_multiplier: int
    points: int
    state: PlayerState
    fixtures_total: int
    fixtures_unresolved: int
    is_home_captain: bool = False
    is_away_captain: bool = False

    @property
    def net_multiplier(self) -> int:
        """Positive favours the home side, negative the away side, zero cancels."""

        return self.home_multiplier - self.away_multiplier

    @property
    def is_shared(self) -> bool:
        """Both sides field him identically, so he cannot change the margin."""

        return self.home_multiplier == self.away_multiplier and self.home_multiplier > 0

    @property
    def swing_points(self) -> int:
        """The points this player has already moved the margin by."""

        return self.points * self.net_multiplier


@dataclass(frozen=True, slots=True)
class SideRemaining:
    """What a side still has to play for."""

    players_remaining: int = 0
    effective_players_remaining: int = 0
    #: Shown separately so a Double Gameweek player is not read as two players.
    fixtures_remaining: int = 0


@dataclass(frozen=True, slots=True)
class MatchupComparison:
    lines: tuple[PlayerLine, ...]
    home_remaining: SideRemaining
    away_remaining: SideRemaining

    @property
    def shared(self) -> tuple[PlayerLine, ...]:
        return tuple(line for line in self.lines if line.is_shared)

    @property
    def differentials(self) -> tuple[PlayerLine, ...]:
        """Players who can still change the margin, biggest swing first."""

        return tuple(
            sorted(
                (line for line in self.lines if line.net_multiplier != 0),
                key=lambda line: (-abs(line.swing_points), line.element_id),
            )
        )

    @property
    def captain_differential(self) -> tuple[PlayerLine, ...]:
        return tuple(
            line
            for line in self.lines
            if line.is_home_captain != line.is_away_captain
            and (line.is_home_captain or line.is_away_captain)
        )


def _remaining(
    picks: dict[int, SidePick],
    progress: dict[int, FixtureProgress],
) -> SideRemaining:
    players = 0
    effective = 0
    fixtures = 0
    for element_id, pick in picks.items():
        if pick.multiplier <= 0:
            continue
        unresolved = progress.get(element_id, FixtureProgress()).unresolved
        if unresolved <= 0:
            continue
        players += 1
        effective += pick.multiplier
        fixtures += unresolved
    return SideRemaining(
        players_remaining=players,
        effective_players_remaining=effective,
        fixtures_remaining=fixtures,
    )


def compare_squads(
    home_picks: dict[int, SidePick],
    away_picks: dict[int, SidePick],
    points: dict[int, int],
    progress: dict[int, FixtureProgress],
) -> MatchupComparison:
    """Build the player-by-player comparison for one matchup.

    Only players at least one side actually counts appear. A player benched by
    both managers is in neither squad's scoring and would be noise on the page.
    """

    lines: list[PlayerLine] = []
    for element_id in sorted(set(home_picks) | set(away_picks)):
        home = home_picks.get(element_id)
        away = away_picks.get(element_id)
        home_multiplier = home.multiplier if home is not None else 0
        away_multiplier = away.multiplier if away is not None else 0
        if home_multiplier <= 0 and away_multiplier <= 0:
            continue

        fixture = progress.get(element_id, FixtureProgress())
        lines.append(
            PlayerLine(
                element_id=element_id,
                home_multiplier=max(0, home_multiplier),
                away_multiplier=max(0, away_multiplier),
                points=points.get(element_id, 0),
                state=fixture.state,
                fixtures_total=fixture.total,
                fixtures_unresolved=fixture.unresolved,
                is_home_captain=home is not None and home.is_effective_captain,
                is_away_captain=away is not None and away.is_effective_captain,
            )
        )

    return MatchupComparison(
        lines=tuple(lines),
        home_remaining=_remaining(home_picks, progress),
        away_remaining=_remaining(away_picks, progress),
    )
