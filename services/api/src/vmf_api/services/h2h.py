from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.errors import NotFoundError, RuleValidationError
from vmf_api.domain.h2h_schedule import generate_round_robin_schedule
from vmf_api.domain.rankings import H2HStanding, rank_h2h
from vmf_api.models.enums import ManagerStatus, MatchStatus, RegistrationStatus
from vmf_api.repositories.h2h import H2HRepository
from vmf_api.repositories.managers import ManagerRepository
from vmf_api.schemas.h2h import (
    H2HScheduleGenerateRequest,
    H2HScheduleResponse,
    H2HStandingResponse,
)


@dataclass(slots=True)
class _StandingAccumulator:
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    points_for: int = 0
    points_against: int = 0
    table_points: int = 0


class H2HService:
    def __init__(self, session: AsyncSession, *, expected_manager_count: int = 40) -> None:
        self.session = session
        self.expected_manager_count = expected_manager_count
        self.repository = H2HRepository(session)
        self.manager_repository = ManagerRepository(session)

    async def generate_schedule(
        self,
        request: H2HScheduleGenerateRequest,
    ) -> H2HScheduleResponse:
        managers = await self.manager_repository.list(
            status=ManagerStatus.ACTIVE,
            registration_status=RegistrationStatus.CONFIRMED,
        )
        manager_ids = [manager.id for manager in managers]
        if len(manager_ids) != self.expected_manager_count:
            raise RuleValidationError(
                f"schedule requires exactly {self.expected_manager_count} active managers; "
                f"found {len(manager_ids)}"
            )
        rounds = generate_round_robin_schedule(
            manager_ids,
            rounds=request.rounds,
            start_gameweek=request.start_gameweek,
        )
        schedule = await self.repository.create_schedule(
            season_id=request.season_id,
            name=request.name,
            rounds=rounds,
        )
        await self.session.commit()
        return H2HScheduleResponse(
            schedule_id=schedule.id,
            name=schedule.name,
            rounds=len(rounds),
            matches=sum(len(items) for items in rounds),
            is_locked=schedule.is_locked,
        )

    async def standings(self, schedule_id: int) -> list[H2HStandingResponse]:
        schedule = await self.repository.get_schedule(schedule_id)
        if schedule is None:
            raise NotFoundError(f"H2H schedule {schedule_id} not found")
        matches = await self.repository.list_matches(schedule_id=schedule_id)
        completed = [
            match for match in matches if match.status in {MatchStatus.FINAL, MatchStatus.WALKOVER}
        ]
        manager_ids = {
            manager_id
            for match in matches
            for manager_id in (match.home_manager_id, match.away_manager_id)
        }
        accumulators = {manager_id: _StandingAccumulator() for manager_id in manager_ids}
        for match in completed:
            home = accumulators[match.home_manager_id]
            away = accumulators[match.away_manager_id]
            home_score = match.home_score or 0
            away_score = match.away_score or 0
            home.played += 1
            away.played += 1
            home.points_for += home_score
            home.points_against += away_score
            away.points_for += away_score
            away.points_against += home_score
            if match.winner_manager_id == match.home_manager_id:
                home.wins += 1
                away.losses += 1
                home.table_points += 3
            elif match.winner_manager_id == match.away_manager_id:
                away.wins += 1
                home.losses += 1
                away.table_points += 3
            else:
                home.draws += 1
                away.draws += 1
                home.table_points += 1
                away.table_points += 1

        penalties = await self.repository.list_penalty_totals()
        full_net = await self.repository.full_net_points(schedule.season_id)
        domain_rows = [
            H2HStanding(
                manager_id=manager_id,
                table_points=row.table_points + penalties.get(manager_id, 0),
                points_for=row.points_for,
                points_against=row.points_against,
                wins=row.wins,
                full_net_fpl_points=full_net.get(manager_id, 0),
            )
            for manager_id, row in accumulators.items()
        ]
        ranked = rank_h2h(domain_rows)
        return [
            H2HStandingResponse(
                rank=item.rank,
                manager_id=item.value.manager_id,
                played=accumulators[item.value.manager_id].played,
                wins=accumulators[item.value.manager_id].wins,
                draws=accumulators[item.value.manager_id].draws,
                losses=accumulators[item.value.manager_id].losses,
                points_for=item.value.points_for,
                points_against=item.value.points_against,
                point_difference=item.value.point_difference,
                h2h_table_points=item.value.table_points,
                full_net_fpl_points=item.value.full_net_fpl_points,
            )
            for item in ranked
        ]
