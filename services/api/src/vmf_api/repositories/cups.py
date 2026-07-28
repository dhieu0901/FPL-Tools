from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.models.cup import CupCompetition, CupMatch, CupRound


class CupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_competitions(self, season_id: int | None = None) -> list[CupCompetition]:
        statement = select(CupCompetition).order_by(
            CupCompetition.season_id,
            CupCompetition.season_half,
        )
        if season_id is not None:
            statement = statement.where(CupCompetition.season_id == season_id)
        return list((await self.session.scalars(statement)).all())

    async def get_competition(self, cup_id: int) -> CupCompetition | None:
        return await self.session.get(CupCompetition, cup_id)

    async def bracket(self, cup_id: int) -> list[CupMatch]:
        statement = (
            select(CupMatch)
            .join(CupRound, CupRound.id == CupMatch.cup_round_id)
            .where(CupRound.cup_competition_id == cup_id)
            .order_by(CupRound.round_order, CupMatch.id)
        )
        return list((await self.session.scalars(statement)).all())
