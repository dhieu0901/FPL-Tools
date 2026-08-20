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

    async def rounds_with_matches(self, cup_id: int) -> list[tuple[CupRound, list[CupMatch]]]:
        """Every round of a Cup with its ties, in the order the bracket is drawn."""

        rounds = list(
            (
                await self.session.scalars(
                    select(CupRound)
                    .where(CupRound.cup_competition_id == cup_id)
                    .order_by(CupRound.round_order)
                )
            )
            .unique()
            .all()
        )
        if not rounds:
            return []
        matches = list(
            (
                await self.session.scalars(
                    select(CupMatch)
                    .where(CupMatch.cup_round_id.in_([round_.id for round_ in rounds]))
                    .order_by(CupMatch.is_third_place_match, CupMatch.id)
                )
            )
            .unique()
            .all()
        )
        grouped: dict[int, list[CupMatch]] = {round_.id: [] for round_ in rounds}
        for match in matches:
            grouped[match.cup_round_id].append(match)
        return [(round_, grouped[round_.id]) for round_ in rounds]

    async def bracket(self, cup_id: int) -> list[CupMatch]:
        statement = (
            select(CupMatch)
            .join(CupRound, CupRound.id == CupMatch.cup_round_id)
            .where(CupRound.cup_competition_id == cup_id)
            .order_by(CupRound.round_order, CupMatch.id)
        )
        return list((await self.session.scalars(statement)).all())
