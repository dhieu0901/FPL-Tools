"""Assemble the live matchup view for one H2H match."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vmf_api.core.errors import NotFoundError
from vmf_api.domain.chips import (
    CHIPS_PER_HALF,
    ChipStatus,
    chip_status,
    half_range,
    season_half,
)
from vmf_api.domain.gameweek_scoring import PickInput as ScoringPick
from vmf_api.domain.gameweek_scoring import effective_captain
from vmf_api.domain.matchup import (
    FixtureProgress,
    MatchupComparison,
    PlayerFixture,
    SidePick,
    SquadEntry,
    build_squad,
    compare_squads,
)
from vmf_api.models.competition import Gameweek
from vmf_api.models.enums import ScoreState
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.ingestion import (
    FplFixture,
    FplPlayer,
    FplPlayerFixtureStat,
    FplTeam,
    ManagerPickSnapshot,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore


@dataclass(frozen=True, slots=True)
class SideView:
    manager_id: int
    fpl_entry_id: int
    manager_name: str
    team_name: str
    score: int | None
    gross_points: int | None
    transfer_cost: int | None
    bench_points: int | None
    chip_used: str | None
    captain_points: int | None
    goals_counted: int | None
    is_totw: bool
    chips: ChipStatus


@dataclass(frozen=True, slots=True)
class MatchupView:
    match_id: int
    gameweek_number: int
    status: str
    score_state: ScoreState | None
    is_playoff: bool
    bracket_position: str | None
    walkover_reason: str | None
    home: SideView
    away: SideView
    comparison: MatchupComparison
    player_names: dict[int, str]
    #: FPL's own three-letter club code, keyed by element id.
    player_clubs: dict[int, str]
    home_squad: tuple[SquadEntry, ...] = ()
    away_squad: tuple[SquadEntry, ...] = ()


class MatchupService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def h2h_match(self, match_id: int) -> MatchupView:
        match = await self.session.get(H2HMatch, match_id)
        if match is None:
            raise NotFoundError(f"h2h match {match_id} not found")

        schedule = await self.session.get(H2HSchedule, match.schedule_id)
        if schedule is None:
            raise NotFoundError(f"h2h schedule {match.schedule_id} not found")

        gameweek_number = match.gameweek_number
        season_id = schedule.season_id

        managers = {
            manager.id: manager
            for manager in await self.session.scalars(
                select(Manager).where(
                    Manager.id.in_([match.home_manager_id, match.away_manager_id])
                )
            )
        }
        scores = await self._scores(season_id, gameweek_number, list(managers))
        chips = await self._chips(season_id, gameweek_number, list(managers))
        snapshots = await self._snapshots(gameweek_number, list(managers))
        points, progress = await self._player_state(season_id, gameweek_number)
        player_fixtures = await self._player_fixtures(season_id, gameweek_number)

        squad_elements = {
            item.element_id for snapshot in snapshots.values() for item in snapshot.items
        }
        catalog = await self._player_catalog(season_id, squad_elements)
        element_types = {element_id: entry[1] for element_id, entry in catalog.items()}

        home_picks = self._side_picks(snapshots.get(match.home_manager_id), element_types)
        away_picks = self._side_picks(snapshots.get(match.away_manager_id), element_types)
        comparison = compare_squads(home_picks, away_picks, points, progress)
        names = {element_id: entry[0] for element_id, entry in catalog.items()}
        clubs = {
            element_id: entry[2] for element_id, entry in catalog.items() if entry[2] is not None
        }

        return MatchupView(
            match_id=match.id,
            gameweek_number=gameweek_number,
            status=match.status.value,
            score_state=self._score_state(scores),
            is_playoff=match.is_playoff,
            bracket_position=match.bracket_position,
            walkover_reason=match.walkover_reason,
            home=self._side(match.home_manager_id, managers, scores, match.home_score, chips),
            away=self._side(match.away_manager_id, managers, scores, match.away_score, chips),
            comparison=comparison,
            player_names=names,
            player_clubs=clubs,
            home_squad=build_squad(home_picks, points, progress, player_fixtures),
            away_squad=build_squad(away_picks, points, progress, player_fixtures),
        )

    @staticmethod
    def _score_state(scores: dict[int, ManagerGameweekScore]) -> ScoreState | None:
        states = {score.score_status for score in scores.values()}
        if not states:
            return None
        # The less settled of the two is what the page must present.
        for state in (ScoreState.UPCOMING, ScoreState.LIVE, ScoreState.PROVISIONAL):
            if state in states:
                return state
        return ScoreState.FINAL

    @staticmethod
    def _side(
        manager_id: int,
        managers: dict[int, Manager],
        scores: dict[int, ManagerGameweekScore],
        recorded_score: int | None,
        chips: dict[int, ChipStatus],
    ) -> SideView:
        manager = managers.get(manager_id)
        score = scores.get(manager_id)
        return SideView(
            manager_id=manager_id,
            fpl_entry_id=manager.fpl_entry_id if manager is not None else 0,
            manager_name=manager.manager_name if manager is not None else "",
            team_name=manager.team_name if manager is not None else "",
            # A finalized match keeps the score it was settled with; otherwise
            # the live figure is the honest one.
            score=recorded_score
            if recorded_score is not None
            else (score.net_points if score is not None else None),
            gross_points=score.gross_points if score is not None else None,
            transfer_cost=score.transfer_cost if score is not None else None,
            bench_points=score.bench_points if score is not None else None,
            chip_used=score.chip_used if score is not None else None,
            captain_points=score.captain_points if score is not None else None,
            goals_counted=score.goals_counted if score is not None else None,
            is_totw=bool(score.is_totw) if score is not None else False,
            chips=chips.get(manager_id, ChipStatus(None, (), CHIPS_PER_HALF)),
        )

    @staticmethod
    def _side_picks(
        snapshot: ManagerPickSnapshot | None,
        element_types: dict[int, int],
    ) -> dict[int, SidePick]:
        if snapshot is None:
            return {}
        captain = effective_captain(
            [
                ScoringPick(
                    element_id=item.element_id,
                    squad_position=item.squad_position,
                    multiplier=item.multiplier,
                    is_captain=item.is_captain,
                    is_vice_captain=item.is_vice_captain,
                )
                for item in snapshot.items
            ]
        )
        captain_element = captain.element_id if captain is not None else None
        return {
            item.element_id: SidePick(
                element_id=item.element_id,
                multiplier=item.multiplier,
                is_effective_captain=item.element_id == captain_element,
                squad_position=item.squad_position,
                element_type=element_types.get(item.element_id, 0),
                # The armband may have moved, so the vice-captain is reported
                # as published rather than inferred from who is captaining.
                is_vice_captain=item.is_vice_captain,
            )
            for item in snapshot.items
        }

    async def _chips(
        self,
        season_id: int,
        gameweek_number: int,
        manager_ids: list[int],
    ) -> dict[int, ChipStatus]:
        """Every chip each side has played in this half of the season."""

        if not manager_ids:
            return {}
        window = half_range(season_half(gameweek_number))
        rows = (
            await self.session.execute(
                select(
                    ManagerGameweekScore.manager_id,
                    Gameweek.number,
                    ManagerGameweekScore.chip_used,
                )
                .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                .where(
                    Gameweek.season_id == season_id,
                    Gameweek.number.between(window.start, window.stop - 1),
                    ManagerGameweekScore.manager_id.in_(manager_ids),
                )
            )
        ).all()

        played: dict[int, dict[int, str | None]] = {manager_id: {} for manager_id in manager_ids}
        for manager_id, number, chip in rows:
            if manager_id in played:
                played[manager_id][number] = chip
        return {
            manager_id: chip_status(
                gameweek_number=gameweek_number,
                used_by_gameweek=by_gameweek,
            )
            for manager_id, by_gameweek in played.items()
        }

    async def _scores(
        self,
        season_id: int,
        gameweek_number: int,
        manager_ids: list[int],
    ) -> dict[int, ManagerGameweekScore]:
        if not manager_ids:
            return {}
        rows = await self.session.scalars(
            select(ManagerGameweekScore)
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(
                Gameweek.season_id == season_id,
                Gameweek.number == gameweek_number,
                ManagerGameweekScore.manager_id.in_(manager_ids),
            )
        )
        return {row.manager_id: row for row in rows}

    async def _snapshots(
        self,
        gameweek_number: int,
        manager_ids: list[int],
    ) -> dict[int, ManagerPickSnapshot]:
        if not manager_ids:
            return {}
        latest = (
            select(
                ManagerPickSnapshot.manager_id.label("manager_id"),
                func.max(ManagerPickSnapshot.revision).label("revision"),
            )
            .where(
                ManagerPickSnapshot.gameweek_number == gameweek_number,
                ManagerPickSnapshot.manager_id.in_(manager_ids),
            )
            .group_by(ManagerPickSnapshot.manager_id)
            .subquery()
        )
        rows = await self.session.scalars(
            select(ManagerPickSnapshot)
            .join(
                latest,
                (ManagerPickSnapshot.manager_id == latest.c.manager_id)
                & (ManagerPickSnapshot.revision == latest.c.revision),
            )
            .options(selectinload(ManagerPickSnapshot.items))
        )
        return {row.manager_id: row for row in rows}

    async def _player_state(
        self,
        season_id: int,
        gameweek_number: int,
    ) -> tuple[dict[int, int], dict[int, FixtureProgress]]:
        """Points per player, and how far through the Gameweek each one is."""

        fixtures = {
            row.fixture_fpl_id: row
            for row in await self.session.scalars(
                select(FplFixture).where(
                    FplFixture.season_id == season_id,
                    FplFixture.gameweek_number == gameweek_number,
                )
            )
        }

        points: dict[int, int] = {}
        counters: dict[int, list[int]] = {}
        for element_id, fixture_id, total_points in await self.session.execute(
            select(
                FplPlayerFixtureStat.element_id,
                FplPlayerFixtureStat.fixture_fpl_id,
                FplPlayerFixtureStat.total_points,
            ).where(
                FplPlayerFixtureStat.season_id == season_id,
                FplPlayerFixtureStat.gameweek_number == gameweek_number,
            )
        ):
            points[element_id] = points.get(element_id, 0) + (total_points or 0)
            counters.setdefault(element_id, [0, 0, 0])
            fixture = fixtures.get(fixture_id)
            counters[element_id][0] += 1
            if fixture is not None and fixture.started:
                counters[element_id][1] += 1
            # The final whistle, not the bonus-point confirmation that comes
            # hours after it. A player whose match has ended is not "playing".
            if fixture is not None and fixture.is_played_out:
                counters[element_id][2] += 1

        progress = {
            element_id: FixtureProgress(total=total, started=started, finished=finished)
            for element_id, (total, started, finished) in counters.items()
        }
        return points, progress

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        """Say out loud that a stored timestamp is UTC.

        Kick-offs arrive from FPL with a ``Z`` and land in a column that has
        no timezone, so the offset is dropped on the way in and the value
        that comes back is a naive UTC datetime. Serialised as-is it reaches
        a browser with nothing to anchor it, and JavaScript reads a naive
        string as *local* time - which showed every kick-off seven hours out
        for a league played in Vietnam.
        """

        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)

    async def _player_fixtures(
        self,
        season_id: int,
        gameweek_number: int,
    ) -> dict[int, tuple[PlayerFixture, ...]]:
        """Who each player faces this Gameweek, and where it has got to.

        "Yet to play" on its own leaves a reader guessing at the two things
        they came for: against whom, and when. A Double Gameweek gives a
        player two entries here rather than a summary that hides one.
        """

        clubs = {
            row.team_fpl_id: row.short_name
            for row in await self.session.scalars(
                select(FplTeam).where(FplTeam.season_id == season_id)
            )
        }
        teams = {
            row.element_id: row.team_fpl_id
            for row in await self.session.scalars(
                select(FplPlayer).where(FplPlayer.season_id == season_id)
            )
        }

        clock = await self._match_clock(season_id, gameweek_number)

        schedule: dict[int, list[PlayerFixture]] = {}
        for fixture in await self.session.scalars(
            select(FplFixture).where(
                FplFixture.season_id == season_id,
                FplFixture.gameweek_number == gameweek_number,
            )
        ):
            for side, other in (
                (fixture.team_h_fpl_id, fixture.team_a_fpl_id),
                (fixture.team_a_fpl_id, fixture.team_h_fpl_id),
            ):
                if side is None:
                    continue
                entry = PlayerFixture(
                    opponent=clubs.get(other) if other is not None else None,
                    is_home=side == fixture.team_h_fpl_id,
                    kickoff_time=self._as_utc(fixture.kickoff_time),
                    minutes=max(fixture.minutes, clock.get(fixture.fixture_fpl_id, 0)),
                    started=fixture.started,
                    played_out=fixture.is_played_out,
                )
                for element_id, team_id in teams.items():
                    if team_id == side:
                        schedule.setdefault(element_id, []).append(entry)

        # Earliest first, so a Double reads in the order it will be played.
        return {
            element_id: tuple(
                sorted(items, key=lambda item: (item.kickoff_time is None, item.kickoff_time))
            )
            for element_id, items in schedule.items()
        }

    async def _match_clock(self, season_id: int, gameweek_number: int) -> dict[int, int]:
        """How far into each match we are, read from the live feed.

        The fixture list carries a ``minutes`` field of its own, but FPL serves
        that endpoint from a cache that has been observed five minutes behind
        and, once, twenty. The live feed is served fresh - under a minute -
        because it is what FPL's own pages are built from, and any player who
        has been on since kick-off carries the match clock in his own minutes.
        Taking the highest is therefore the clock, and it is only ever read
        alongside the fixture's own figure, never instead of it: a clock runs
        forward, so whichever source is further along is the current one.
        """

        rows = await self.session.execute(
            select(
                FplPlayerFixtureStat.fixture_fpl_id,
                func.max(FplPlayerFixtureStat.minutes),
            )
            .where(
                FplPlayerFixtureStat.season_id == season_id,
                FplPlayerFixtureStat.gameweek_number == gameweek_number,
            )
            .group_by(FplPlayerFixtureStat.fixture_fpl_id)
        )
        return {fixture_id: minutes or 0 for fixture_id, minutes in rows}

    async def _player_catalog(
        self,
        season_id: int,
        element_ids: set[int],
    ) -> dict[int, tuple[str, int, str | None]]:
        """Name, position and club for each squad member, in one query.

        The club is FPL's own ``short_name`` - the three letters shown in the
        game itself - rather than an abbreviation of our own. It is read
        through the player's current ``team_fpl_id``, so a January transfer
        moves a player's club here the moment the catalogue is re-ingested.

        The join is outer: a player whose club has not been ingested yet is
        still a player, and is worth listing without one.
        """

        if not element_ids:
            return {}
        rows = await self.session.execute(
            select(
                FplPlayer.element_id,
                FplPlayer.web_name,
                FplPlayer.element_type,
                FplTeam.short_name,
            )
            .outerjoin(
                FplTeam,
                (FplTeam.team_fpl_id == FplPlayer.team_fpl_id)
                & (FplTeam.season_id == FplPlayer.season_id),
            )
            .where(
                FplPlayer.season_id == season_id,
                FplPlayer.element_id.in_(element_ids),
            )
        )
        return {
            element_id: (web_name, element_type, short_name)
            for element_id, web_name, element_type, short_name in rows
        }
