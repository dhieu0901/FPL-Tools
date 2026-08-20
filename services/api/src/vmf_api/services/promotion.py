"""Move six managers up and six down at the end of a Season.

The swap rewrites which table a manager is judged in for the whole of the
Season that follows, so it is written once, from the finalized Classic tables,
and recorded as membership of the next phase rather than by editing history.
The previous phase's memberships are left exactly as they were: a manager who
finished 18th in HIGH still finished 18th in HIGH.

Nothing here decides an order. The ranking is the same one the Classic page
shows, so the swap cannot disagree with the table managers were reading.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.errors import ConflictError, NotFoundError, RuleValidationError
from vmf_api.domain.promotion import (
    DivisionPlace,
    DivisionSwap,
    Movement,
    plan_division_swap,
)
from vmf_api.domain.rankings import ClassicStanding, rank_classic
from vmf_api.models.competition import CompetitionPhase, DivisionMembership, Gameweek, Season
from vmf_api.models.enums import Division, PhaseType
from vmf_api.models.manager import Manager
from vmf_api.repositories.classic import ClassicRepository

#: The Season boundary the swap is made at, and the phase it takes effect in.
SWAP_AFTER_GAMEWEEK = 19
NEXT_PHASE = PhaseType.CLASSIC_SEASON_2


@dataclass(frozen=True, slots=True)
class Move:
    manager_id: int
    manager_name: str
    team_name: str
    from_division: Division
    to_division: Division
    finished_rank: int


@dataclass(frozen=True, slots=True)
class SwapResult:
    promoted: tuple[Move, ...]
    relegated: tuple[Move, ...]
    contested_ranks: tuple[int, ...]
    memberships_written: int
    dry_run: bool

    @property
    def is_decided(self) -> bool:
        return not self.contested_ranks


class DivisionSwapService:
    """Plan and apply the end-of-Season exchange between HIGH and LOW."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.classic = ClassicRepository(session)

    async def plan(
        self,
        *,
        season_code: str,
        count: int = 6,
    ) -> tuple[SwapResult, dict[int, Manager]]:
        season = await self.session.scalar(
            select(Season).where(Season.fpl_season_code == season_code)
        )
        if season is None:
            raise NotFoundError(f"season {season_code!r} not found")

        cutoff = await self.session.scalar(
            select(Gameweek).where(
                Gameweek.season_id == season.id,
                Gameweek.number == SWAP_AFTER_GAMEWEEK,
            )
        )
        if cutoff is None or not cutoff.is_finalized:
            raise RuleValidationError(
                f"GW{SWAP_AFTER_GAMEWEEK} is not finalized, so the Season 1 tables can still change"
            )

        managers: dict[int, Manager] = {}
        places: dict[Division, list[DivisionPlace]] = {}
        for division in (Division.HIGH, Division.LOW):
            aggregates = await self.classic.standings(
                season_id=season.id,
                division=division,
                start_gameweek=1,
                end_gameweek=SWAP_AFTER_GAMEWEEK,
            )
            for row in aggregates:
                managers[row.manager_id] = await self._manager(row.manager_id)
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
            places[division] = [
                DivisionPlace(manager_id=item.value.manager_id, rank=item.rank) for item in ranked
            ]

        swap: DivisionSwap = plan_division_swap(
            high=places[Division.HIGH],
            low=places[Division.LOW],
            count=count,
        )

        return (
            SwapResult(
                promoted=tuple(
                    self._move(move, managers, Division.LOW, Division.HIGH)
                    for move in swap.promoted
                ),
                relegated=tuple(
                    self._move(move, managers, Division.HIGH, Division.LOW)
                    for move in swap.relegated
                ),
                contested_ranks=swap.contested_ranks,
                memberships_written=0,
                dry_run=True,
            ),
            managers,
        )

    async def apply(self, *, season_code: str, count: int = 6) -> SwapResult:
        planned, managers = await self.plan(season_code=season_code, count=count)
        if not planned.is_decided:
            raise RuleValidationError(
                "the swap cannot be written while these ranks are shared: "
                + ", ".join(str(rank) for rank in planned.contested_ranks)
                + "; the boundary is an audited administrator decision"
            )

        season = await self.session.scalar(
            select(Season).where(Season.fpl_season_code == season_code)
        )
        assert season is not None  # plan() has already checked
        phase = await self.session.scalar(
            select(CompetitionPhase).where(
                CompetitionPhase.season_id == season.id,
                CompetitionPhase.phase_type == NEXT_PHASE,
            )
        )
        if phase is None:
            raise NotFoundError(f"season {season_code!r} has no {NEXT_PHASE.value} phase")

        existing = {
            membership.manager_id
            for membership in await self.session.scalars(
                select(DivisionMembership).where(
                    DivisionMembership.competition_phase_id == phase.id
                )
            )
        }
        if existing:
            raise ConflictError(
                f"{len(existing)} manager(s) already hold a {NEXT_PHASE.value} membership; "
                "the swap has been made"
            )

        moving = {move.manager_id: move for move in (*planned.promoted, *planned.relegated)}
        written = 0
        for manager_id, manager in managers.items():
            move = moving.get(manager_id)
            division = move.to_division if move else manager.division
            self.session.add(
                DivisionMembership(
                    manager_id=manager_id,
                    competition_phase_id=phase.id,
                    division=division,
                    start_gameweek=phase.start_gameweek,
                    end_gameweek=phase.end_gameweek,
                    promotion_source=(
                        f"top {count} of LOW after GW{SWAP_AFTER_GAMEWEEK}"
                        if move and move.to_division is Division.HIGH
                        else None
                    ),
                    relegation_source=(
                        f"bottom {count} of HIGH after GW{SWAP_AFTER_GAMEWEEK}"
                        if move and move.to_division is Division.LOW
                        else None
                    ),
                )
            )
            # The column on the manager is the "where are they now" pointer;
            # the membership rows remain the record of where they have been.
            manager.division = division
            written += 1

        await self.session.flush()
        return SwapResult(
            promoted=planned.promoted,
            relegated=planned.relegated,
            contested_ranks=(),
            memberships_written=written,
            dry_run=False,
        )

    async def _manager(self, manager_id: int) -> Manager:
        manager = await self.session.get(Manager, manager_id)
        if manager is None:
            raise NotFoundError(f"manager {manager_id} not found")
        return manager

    @staticmethod
    def _move(
        move: Movement,
        managers: dict[int, Manager],
        from_division: Division,
        to_division: Division,
    ) -> Move:
        manager = managers[move.manager_id]
        return Move(
            manager_id=move.manager_id,
            manager_name=manager.manager_name,
            team_name=manager.team_name,
            from_division=from_division,
            to_division=to_division,
            finished_rank=move.from_rank,
        )
