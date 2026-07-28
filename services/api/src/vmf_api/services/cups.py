from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.errors import NotFoundError
from vmf_api.models.cup import CupCompetition, CupMatch
from vmf_api.repositories.cups import CupRepository


class CupService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = CupRepository(session)

    async def list_competitions(self, season_id: int | None = None) -> list[CupCompetition]:
        return await self.repository.list_competitions(season_id)

    async def bracket(self, cup_id: int) -> list[CupMatch]:
        if await self.repository.get_competition(cup_id) is None:
            raise NotFoundError(f"cup {cup_id} not found")
        return await self.repository.bracket(cup_id)
