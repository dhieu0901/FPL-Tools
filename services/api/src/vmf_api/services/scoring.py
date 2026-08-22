"""Derive ``manager_gameweek_scores`` from the ingested source facts.

The ingestion layer records what FPL published; this layer applies the VMF
rulebook to it. The two are kept apart on purpose: a re-run of this service can
never change raw evidence, and a correction from FPL flows through by
recomputing rather than by editing a stored result.

Every run rewrites the whole Gameweek, so the service is idempotent and safe to
call from each cron tick while a Gameweek is live.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vmf_api.domain.gameweek_scoring import (
    ElementStats,
    PickInput,
    compute_gameweek_score,
)
from vmf_api.domain.locked_scores import ScoreSource
from vmf_api.domain.scoring import totw_winners
from vmf_api.models.competition import Gameweek
from vmf_api.models.enums import ManagerStatus, ScoreState
from vmf_api.models.ingestion import (
    FplFixture,
    FplPlayerFixtureStat,
    ManagerGameweekHistory,
    ManagerPickSnapshot,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore

#: A manager in one of these states does not hold an eligible score, so the
#: score must not win TotW even when it is numerically the highest.
INELIGIBLE_STATUSES = frozenset({ManagerStatus.LOCKED, ManagerStatus.DELETED})


@dataclass(frozen=True, slots=True)
class ScoringOutcome:
    gameweek_number: int
    state: ScoreState | None = None
    managers_scored: int = 0
    totw_manager_ids: tuple[int, ...] = ()
    unreconciled_manager_ids: tuple[int, ...] = ()
    skipped_reason: str | None = None
    detail: dict[str, int] = field(default_factory=dict)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class GameweekScoringService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        season_id: int,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.session = session
        self.season_id = season_id
        self.clock = clock

    async def score_gameweek(self, gameweek_number: int) -> ScoringOutcome:
        gameweek = await self.session.scalar(
            select(Gameweek).where(
                Gameweek.season_id == self.season_id,
                Gameweek.number == gameweek_number,
            )
        )
        if gameweek is None:
            return ScoringOutcome(
                gameweek_number=gameweek_number,
                skipped_reason="gameweek_not_found",
            )

        state = await self._score_state(gameweek)
        if state is ScoreState.UPCOMING:
            # Writing zeroes before kick-off would present an absent score as a
            # real one, which section 11 of the rulebook forbids.
            return ScoringOutcome(
                gameweek_number=gameweek_number,
                state=state,
                skipped_reason="no_fixture_started",
            )

        stats = await self._element_stats(gameweek_number)
        snapshots = await self._latest_snapshots(gameweek_number)
        history = await self._history(gameweek_number)
        managers = await self._managers(set(snapshots) | set(history))
        existing = await self._existing_scores(gameweek.id)

        scored: dict[int, int] = {}
        unreconciled: list[int] = []

        for manager_id in sorted(managers):
            snapshot = snapshots.get(manager_id)
            entry = history.get(manager_id)
            if snapshot is None and entry is None:
                continue

            picks = (
                [
                    PickInput(
                        element_id=item.element_id,
                        squad_position=item.squad_position,
                        multiplier=item.multiplier,
                        is_captain=item.is_captain,
                        is_vice_captain=item.is_vice_captain,
                        auto_subbed_in=item.auto_subbed_in,
                        auto_subbed_out=item.auto_subbed_out,
                    )
                    for item in snapshot.items
                ]
                if snapshot is not None
                else []
            )
            # FPL's entry history carries the published total and the
            # transfer penalty. The penalty is fixed at the deadline, so it is
            # taken whenever the row exists. The total is not: FPL opens an
            # entry's history row when the Gameweek opens and lets it trail the
            # live element feed, so a goal reaches a player's page minutes
            # before it reaches the totals of the managers who own him. While
            # the football is still going the derived total is the fresher of
            # the two; the published figure becomes the authority - rulebook
            # 3.1 - once the Gameweek has stopped moving.
            if entry is not None:
                transfer_cost = entry.transfer_cost
                official_gross: int | None = (
                    None if state is ScoreState.LIVE else entry.gross_points
                )
            else:
                transfer_cost = snapshot.transfer_cost if snapshot is not None else 0
                official_gross = None

            computation = compute_gameweek_score(
                picks,
                stats,
                active_chip=snapshot.active_chip if snapshot is not None else None,
                transfer_cost=transfer_cost,
                official_gross_points=official_gross,
            )
            if not computation.reconciled:
                unreconciled.append(manager_id)

            row = existing.get(manager_id)
            if row is None:
                row = ManagerGameweekScore(
                    manager_id=manager_id,
                    gameweek_id=gameweek.id,
                )
                self.session.add(row)
                existing[manager_id] = row

            row.gross_points = computation.gross_points
            row.transfer_cost = computation.transfer_cost
            row.net_points = computation.net_points
            row.official_points = (
                entry.gross_points - entry.transfer_cost if entry is not None else None
            )
            row.captain_points = computation.captain_points
            row.goals_counted = computation.goals_counted
            row.yellow_cards_counted = computation.yellow_cards_counted
            row.red_cards_counted = computation.red_cards_counted
            row.bench_points = computation.bench_points
            row.chip_used = snapshot.active_chip if snapshot is not None else None
            row.score_status = state
            scored[manager_id] = computation.net_points

        winners = self._award_totw(scored, managers, existing)
        await self.session.flush()

        return ScoringOutcome(
            gameweek_number=gameweek_number,
            state=state,
            managers_scored=len(scored),
            totw_manager_ids=tuple(sorted(winners)),
            unreconciled_manager_ids=tuple(unreconciled),
            detail={
                "snapshots": len(snapshots),
                "history_rows": len(history),
                "elements_with_stats": len(stats),
            },
        )

    def _award_totw(
        self,
        scored: dict[int, int],
        managers: dict[int, ManagerStatus],
        rows: dict[int, ManagerGameweekScore],
    ) -> set[int]:
        """Mark the highest eligible net score, or every score tied with it."""

        eligible = {
            manager_id
            for manager_id in scored
            if managers.get(manager_id) not in INELIGIBLE_STATUSES
            and rows[manager_id].score_source != ScoreSource.REPLACEMENT_AVERAGE
        }
        winners = totw_winners(scored, eligible_manager_ids=eligible)
        for manager_id in scored:
            rows[manager_id].is_totw = manager_id in winners
        return winners

    async def _score_state(self, gameweek: Gameweek) -> ScoreState:
        if gameweek.is_finalized:
            return ScoreState.FINAL

        rows = list(
            await self.session.execute(
                select(FplFixture.started, FplFixture.is_played_out.label("played_out")).where(
                    FplFixture.season_id == self.season_id,
                    FplFixture.gameweek_number == gameweek.number,
                )
            )
        )
        if not rows or not any(row.started for row in rows):
            return ScoreState.UPCOMING
        # Once the last whistle has gone nothing is live, even though bonus
        # points can still land. That is exactly what "provisional" means, and
        # waiting for FPL to confirm would leave the Gameweek reading as in
        # progress for hours after the football stopped.
        if all(row.played_out for row in rows):
            return ScoreState.PROVISIONAL
        return ScoreState.LIVE

    async def _element_stats(self, gameweek_number: int) -> dict[int, ElementStats]:
        """Sum every fixture attached to the Gameweek, so a Double is additive."""

        rows = await self.session.execute(
            select(
                FplPlayerFixtureStat.element_id,
                func.sum(FplPlayerFixtureStat.total_points),
                func.sum(FplPlayerFixtureStat.minutes),
                func.sum(FplPlayerFixtureStat.goals_scored),
                func.sum(FplPlayerFixtureStat.assists),
                func.sum(FplPlayerFixtureStat.yellow_cards),
                func.sum(FplPlayerFixtureStat.red_cards),
                func.sum(FplPlayerFixtureStat.bonus),
                func.count(FplPlayerFixtureStat.id),
            )
            .where(
                FplPlayerFixtureStat.season_id == self.season_id,
                FplPlayerFixtureStat.gameweek_number == gameweek_number,
            )
            .group_by(FplPlayerFixtureStat.element_id)
        )
        return {
            element_id: ElementStats(
                total_points=points or 0,
                minutes=minutes or 0,
                goals_scored=goals or 0,
                assists=assists or 0,
                yellow_cards=yellows or 0,
                red_cards=reds or 0,
                bonus=bonus or 0,
                fixture_count=fixtures or 0,
            )
            for (
                element_id,
                points,
                minutes,
                goals,
                assists,
                yellows,
                reds,
                bonus,
                fixtures,
            ) in rows
        }

    async def _latest_snapshots(self, gameweek_number: int) -> dict[int, ManagerPickSnapshot]:
        """Return the newest revision per manager.

        Later revisions carry FPL's automatic substitutions, so scoring an older
        revision would count a player FPL has already substituted out.
        """

        latest = (
            select(
                ManagerPickSnapshot.manager_id.label("manager_id"),
                func.max(ManagerPickSnapshot.revision).label("revision"),
            )
            .where(ManagerPickSnapshot.gameweek_number == gameweek_number)
            .group_by(ManagerPickSnapshot.manager_id)
            .subquery()
        )
        snapshots = await self.session.scalars(
            select(ManagerPickSnapshot)
            .join(
                latest,
                (ManagerPickSnapshot.manager_id == latest.c.manager_id)
                & (ManagerPickSnapshot.revision == latest.c.revision),
            )
            .where(ManagerPickSnapshot.gameweek_number == gameweek_number)
            .options(selectinload(ManagerPickSnapshot.items))
        )
        return {snapshot.manager_id: snapshot for snapshot in snapshots}

    async def _history(self, gameweek_number: int) -> dict[int, ManagerGameweekHistory]:
        rows = await self.session.scalars(
            select(ManagerGameweekHistory).where(
                ManagerGameweekHistory.gameweek_number == gameweek_number
            )
        )
        return {row.manager_id: row for row in rows}

    async def _managers(self, manager_ids: set[int]) -> dict[int, ManagerStatus]:
        if not manager_ids:
            return {}
        rows = await self.session.execute(
            select(Manager.id, Manager.active_status).where(Manager.id.in_(manager_ids))
        )
        return {manager_id: status for manager_id, status in rows}

    async def _existing_scores(self, gameweek_id: int) -> dict[int, ManagerGameweekScore]:
        rows = await self.session.scalars(
            select(ManagerGameweekScore).where(ManagerGameweekScore.gameweek_id == gameweek_id)
        )
        return {row.manager_id: row for row in rows}
