from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.models.competition import Gameweek
from vmf_api.models.enums import Division
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore


@dataclass(frozen=True, slots=True)
class ClassicAggregate:
    manager_id: int
    manager_name: str
    team_name: str
    division: Division
    gameweeks_scored: int
    season_points: int
    full_season_points: int
    totw_count: int
    highest_gameweek_score: int


class ClassicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def standings(
        self,
        *,
        season_id: int,
        division: Division,
        start_gameweek: int,
        end_gameweek: int,
    ) -> list[ClassicAggregate]:
        period = (
            select(
                ManagerGameweekScore.manager_id.label("manager_id"),
                func.count(ManagerGameweekScore.id).label("gameweeks_scored"),
                func.coalesce(func.sum(ManagerGameweekScore.net_points), 0).label("season_points"),
                func.coalesce(
                    func.sum(case((ManagerGameweekScore.is_totw.is_(True), 1), else_=0)),
                    0,
                ).label("totw_count"),
                func.coalesce(func.max(ManagerGameweekScore.net_points), 0).label(
                    "highest_gameweek_score"
                ),
            )
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(
                Gameweek.season_id == season_id,
                Gameweek.number.between(start_gameweek, end_gameweek),
            )
            .group_by(ManagerGameweekScore.manager_id)
            .subquery()
        )
        full = (
            select(
                ManagerGameweekScore.manager_id.label("manager_id"),
                func.coalesce(func.sum(ManagerGameweekScore.net_points), 0).label(
                    "full_season_points"
                ),
            )
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(Gameweek.season_id == season_id)
            .group_by(ManagerGameweekScore.manager_id)
            .subquery()
        )
        statement = (
            select(
                Manager.id,
                Manager.manager_name,
                Manager.team_name,
                Manager.division,
                func.coalesce(period.c.gameweeks_scored, 0),
                func.coalesce(period.c.season_points, 0),
                func.coalesce(full.c.full_season_points, 0),
                func.coalesce(period.c.totw_count, 0),
                func.coalesce(period.c.highest_gameweek_score, 0),
            )
            .outerjoin(period, period.c.manager_id == Manager.id)
            .outerjoin(full, full.c.manager_id == Manager.id)
            .where(Manager.division == division)
            .order_by(Manager.id)
        )
        rows = (await self.session.execute(statement)).all()
        return [
            ClassicAggregate(
                manager_id=row[0],
                manager_name=row[1],
                team_name=row[2],
                division=row[3],
                gameweeks_scored=row[4],
                season_points=row[5],
                full_season_points=row[6],
                totw_count=row[7],
                highest_gameweek_score=row[8],
            )
            for row in rows
        ]
