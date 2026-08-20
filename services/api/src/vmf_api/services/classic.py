from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.domain.rankings import ClassicStanding, rank_classic
from vmf_api.models.enums import Division
from vmf_api.repositories.classic import ClassicRepository
from vmf_api.schemas.classic import ClassicStandingResponse, ClassicStandingsEnvelope


class ClassicService:
    PERIODS = {
        "season_1": (1, 19),
        "season_2": (20, 38),
        "full": (1, 38),
    }

    def __init__(self, session: AsyncSession) -> None:
        self.repository = ClassicRepository(session)

    async def standings(
        self,
        *,
        season_id: int,
        division: Division,
        period: str,
    ) -> ClassicStandingsEnvelope:
        try:
            start_gameweek, end_gameweek = self.PERIODS[period]
        except KeyError as error:
            raise ValueError(f"unsupported classic period: {period}") from error

        aggregates = await self.repository.standings(
            season_id=season_id,
            division=division,
            start_gameweek=start_gameweek,
            end_gameweek=end_gameweek,
        )
        by_id = {row.manager_id: row for row in aggregates}
        ranked = rank_classic(
            ClassicStanding(
                manager_id=row.manager_id,
                season_points=row.season_points,
                totw_count=row.totw_count,
                highest_gameweek_score=row.highest_gameweek_score,
                captain_points=row.captain_points,
                goals=row.goals,
                cards=row.cards,
            )
            for row in aggregates
        )
        responses = [
            ClassicStandingResponse(
                rank=item.rank,
                manager_id=item.value.manager_id,
                fpl_entry_id=by_id[item.value.manager_id].fpl_entry_id,
                manager_name=by_id[item.value.manager_id].manager_name,
                team_name=by_id[item.value.manager_id].team_name,
                division=by_id[item.value.manager_id].division,
                gameweeks_scored=by_id[item.value.manager_id].gameweeks_scored,
                season_points=item.value.season_points,
                full_season_points=by_id[item.value.manager_id].full_season_points,
                totw_count=item.value.totw_count,
                highest_gameweek_score=item.value.highest_gameweek_score,
            )
            for item in ranked
        ]
        return ClassicStandingsEnvelope(
            season_id=season_id,
            period=period,  # type: ignore[arg-type]
            division=division,
            start_gameweek=start_gameweek,
            end_gameweek=end_gameweek,
            standings=responses,
        )
