"""Assemble the live matchup view for one H2H match."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vmf_api.core.errors import NotFoundError
from vmf_api.domain.gameweek_scoring import PickInput as ScoringPick
from vmf_api.domain.gameweek_scoring import effective_captain
from vmf_api.domain.matchup import (
    FixtureProgress,
    MatchupComparison,
    SidePick,
    compare_squads,
)
from vmf_api.models.competition import Gameweek
from vmf_api.models.enums import ScoreState
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.ingestion import (
    FplFixture,
    FplPlayer,
    FplPlayerFixtureStat,
    ManagerPickSnapshot,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore


@dataclass(frozen=True, slots=True)
class SideView:
    manager_id: int
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
        snapshots = await self._snapshots(gameweek_number, list(managers))
        points, progress = await self._player_state(season_id, gameweek_number)

        comparison = compare_squads(
            self._side_picks(snapshots.get(match.home_manager_id)),
            self._side_picks(snapshots.get(match.away_manager_id)),
            points,
            progress,
        )
        names = await self._player_names(
            season_id,
            {line.element_id for line in comparison.lines},
        )

        return MatchupView(
            match_id=match.id,
            gameweek_number=gameweek_number,
            status=match.status.value,
            score_state=self._score_state(scores),
            is_playoff=match.is_playoff,
            bracket_position=match.bracket_position,
            walkover_reason=match.walkover_reason,
            home=self._side(match.home_manager_id, managers, scores, match.home_score),
            away=self._side(match.away_manager_id, managers, scores, match.away_score),
            comparison=comparison,
            player_names=names,
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
    ) -> SideView:
        manager = managers.get(manager_id)
        score = scores.get(manager_id)
        return SideView(
            manager_id=manager_id,
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
        )

    @staticmethod
    def _side_picks(snapshot: ManagerPickSnapshot | None) -> dict[int, SidePick]:
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
            )
            for item in snapshot.items
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
            if fixture is not None and fixture.finished:
                counters[element_id][2] += 1

        progress = {
            element_id: FixtureProgress(total=total, started=started, finished=finished)
            for element_id, (total, started, finished) in counters.items()
        }
        return points, progress

    async def _player_names(self, season_id: int, element_ids: set[int]) -> dict[int, str]:
        if not element_ids:
            return {}
        rows = await self.session.execute(
            select(FplPlayer.element_id, FplPlayer.web_name).where(
                FplPlayer.season_id == season_id,
                FplPlayer.element_id.in_(element_ids),
            )
        )
        return {element_id: web_name for element_id, web_name in rows}
