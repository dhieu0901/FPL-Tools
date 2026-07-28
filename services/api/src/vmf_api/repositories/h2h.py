from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.domain.h2h_schedule import ScheduledMatch
from vmf_api.models.competition import Gameweek
from vmf_api.models.h2h import H2HMatch, H2HPenalty, H2HSchedule
from vmf_api.models.scoring import ManagerGameweekScore


class H2HRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_schedule(
        self,
        *,
        season_id: int,
        name: str,
        rounds: list[list[ScheduledMatch]],
    ) -> H2HSchedule:
        schedule = H2HSchedule(season_id=season_id, name=name, is_locked=False)
        self.session.add(schedule)
        await self.session.flush()
        self.session.add_all(
            [
                H2HMatch(
                    schedule_id=schedule.id,
                    gameweek_number=match.round_number,
                    home_manager_id=match.home_manager_id,
                    away_manager_id=match.away_manager_id,
                )
                for round_matches in rounds
                for match in round_matches
            ]
        )
        await self.session.flush()
        return schedule

    async def get_schedule(self, schedule_id: int) -> H2HSchedule | None:
        return await self.session.get(H2HSchedule, schedule_id)

    async def list_matches(
        self,
        *,
        schedule_id: int | None = None,
        gameweek_number: int | None = None,
    ) -> list[H2HMatch]:
        statement = select(H2HMatch).order_by(H2HMatch.gameweek_number, H2HMatch.id)
        if schedule_id is not None:
            statement = statement.where(H2HMatch.schedule_id == schedule_id)
        if gameweek_number is not None:
            statement = statement.where(H2HMatch.gameweek_number == gameweek_number)
        return list((await self.session.scalars(statement)).all())

    async def list_penalty_totals(self) -> dict[int, int]:
        rows = (
            await self.session.execute(
                select(
                    H2HPenalty.manager_id,
                    func.coalesce(func.sum(H2HPenalty.table_point_delta), 0),
                ).group_by(H2HPenalty.manager_id)
            )
        ).all()
        return {manager_id: total for manager_id, total in rows}

    async def full_net_points(self, season_id: int) -> dict[int, int]:
        rows = (
            await self.session.execute(
                select(
                    ManagerGameweekScore.manager_id,
                    func.coalesce(func.sum(ManagerGameweekScore.net_points), 0),
                )
                .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                .where(Gameweek.season_id == season_id)
                .group_by(ManagerGameweekScore.manager_id)
            )
        ).all()
        return {manager_id: points for manager_id, points in rows}
