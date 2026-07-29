"""Notable facts from the season so far.

The interface is bilingual, so this returns structured facts rather than
sentences: a kind, the manager it concerns and the number behind it. Writing
the prose here would hard-code one language into the API and leave the other
half of the league reading the wrong one.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.models.competition import Gameweek
from vmf_api.models.enums import ManagerStatus, RegistrationStatus, ScoreState
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore

DEFAULT_LIMIT = 6


class HighlightKind(StrEnum):
    TEAM_OF_THE_WEEK = "team_of_the_week"
    SEASON_HIGH = "season_high"
    CAPTAIN_HAUL = "captain_haul"
    TOTW_LEADER = "totw_leader"
    BENCH_REGRET = "bench_regret"


@dataclass(frozen=True, slots=True)
class Highlight:
    kind: HighlightKind
    gameweek_number: int | None
    manager_id: int
    manager_name: str
    team_name: str
    value: int
    is_provisional: bool = False


class HighlightsService:
    def __init__(self, session: AsyncSession, *, season_id: int) -> None:
        self.session = session
        self.season_id = season_id

    async def latest(self, *, limit: int = DEFAULT_LIMIT) -> list[Highlight]:
        latest_gameweek = await self._latest_scored_gameweek()
        if latest_gameweek is None:
            return []

        highlights: list[Highlight] = []
        highlights.extend(await self._team_of_the_week(latest_gameweek))
        highlights.extend(await self._captain_haul(latest_gameweek))
        highlights.extend(await self._bench_regret(latest_gameweek))
        highlights.extend(await self._season_high())
        highlights.extend(await self._totw_leader())
        return highlights[:limit]

    async def _latest_scored_gameweek(self) -> int | None:
        return await self.session.scalar(
            select(func.max(Gameweek.number))
            .select_from(ManagerGameweekScore)
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(Gameweek.season_id == self.season_id)
        )

    def _eligible(self) -> object:
        """Managers whose results are shown publicly."""

        return (
            Manager.registration_status == RegistrationStatus.CONFIRMED,
            Manager.active_status.notin_([ManagerStatus.DELETED, ManagerStatus.REMOVED]),
        )

    async def _team_of_the_week(self, gameweek_number: int) -> list[Highlight]:
        rows = await self.session.execute(
            select(
                Manager.id,
                Manager.manager_name,
                Manager.team_name,
                ManagerGameweekScore.net_points,
                ManagerGameweekScore.score_status,
            )
            .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(
                Gameweek.season_id == self.season_id,
                Gameweek.number == gameweek_number,
                ManagerGameweekScore.is_totw.is_(True),
                *self._eligible(),
            )
            .order_by(Manager.id)
        )
        return [
            Highlight(
                kind=HighlightKind.TEAM_OF_THE_WEEK,
                gameweek_number=gameweek_number,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=net_points,
                is_provisional=status is not ScoreState.FINAL,
            )
            for manager_id, manager_name, team_name, net_points, status in rows
        ]

    async def _top_by(
        self,
        column: object,
        *,
        kind: HighlightKind,
        gameweek_number: int,
        minimum: int = 1,
    ) -> list[Highlight]:
        row = (
            await self.session.execute(
                select(
                    Manager.id,
                    Manager.manager_name,
                    Manager.team_name,
                    column,
                    ManagerGameweekScore.score_status,
                )
                .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
                .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                .where(
                    Gameweek.season_id == self.season_id,
                    Gameweek.number == gameweek_number,
                    *self._eligible(),
                )
                .order_by(column.desc(), Manager.id)  # type: ignore[union-attr]
                .limit(1)
            )
        ).first()
        if row is None or row[3] is None or row[3] < minimum:
            return []
        manager_id, manager_name, team_name, value, status = row
        return [
            Highlight(
                kind=kind,
                gameweek_number=gameweek_number,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=value,
                is_provisional=status is not ScoreState.FINAL,
            )
        ]

    async def _captain_haul(self, gameweek_number: int) -> list[Highlight]:
        return await self._top_by(
            ManagerGameweekScore.captain_points,
            kind=HighlightKind.CAPTAIN_HAUL,
            gameweek_number=gameweek_number,
            minimum=1,
        )

    async def _bench_regret(self, gameweek_number: int) -> list[Highlight]:
        return await self._top_by(
            ManagerGameweekScore.bench_points,
            kind=HighlightKind.BENCH_REGRET,
            gameweek_number=gameweek_number,
            # Below this it is not worth a card on the page.
            minimum=10,
        )

    async def _season_high(self) -> list[Highlight]:
        row = (
            await self.session.execute(
                select(
                    Manager.id,
                    Manager.manager_name,
                    Manager.team_name,
                    ManagerGameweekScore.net_points,
                    Gameweek.number,
                    ManagerGameweekScore.score_status,
                )
                .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
                .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                .where(Gameweek.season_id == self.season_id, *self._eligible())
                .order_by(ManagerGameweekScore.net_points.desc(), Gameweek.number, Manager.id)
                .limit(1)
            )
        ).first()
        if row is None:
            return []
        manager_id, manager_name, team_name, net_points, gameweek_number, status = row
        return [
            Highlight(
                kind=HighlightKind.SEASON_HIGH,
                gameweek_number=gameweek_number,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=net_points,
                is_provisional=status is not ScoreState.FINAL,
            )
        ]

    async def _totw_leader(self) -> list[Highlight]:
        awards = func.count(ManagerGameweekScore.id).label("awards")
        row = (
            await self.session.execute(
                select(Manager.id, Manager.manager_name, Manager.team_name, awards)
                .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
                .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                .where(
                    Gameweek.season_id == self.season_id,
                    ManagerGameweekScore.is_totw.is_(True),
                    *self._eligible(),
                )
                .group_by(Manager.id, Manager.manager_name, Manager.team_name)
                .order_by(awards.desc(), Manager.id)
                .limit(1)
            )
        ).first()
        # One award is simply this week's winner, already on the page above.
        if row is None or row[3] < 2:
            return []
        manager_id, manager_name, team_name, count = row
        return [
            Highlight(
                kind=HighlightKind.TOTW_LEADER,
                gameweek_number=None,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=count,
            )
        ]
