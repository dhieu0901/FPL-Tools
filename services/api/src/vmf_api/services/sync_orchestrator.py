"""Decide which synchronization jobs a cron tick should run.

The scheduler is stateless: it reads the Gameweek catalog and the fixture
table, then runs only the jobs whose preconditions hold. That keeps request
volume inside the free-tier budget and makes every tick safe to repeat.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.config import Settings
from vmf_api.integrations.fpl import FPLClient
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import ManagerStatus, RegistrationStatus
from vmf_api.models.ingestion import FplFixture, ManagerGameweekHistory
from vmf_api.models.manager import Manager
from vmf_api.services.h2h_settlement import H2HSettlementService, SettlementOutcome
from vmf_api.services.ingestion import FplIngestionService, SyncOutcome
from vmf_api.services.raw_store import naive_utc
from vmf_api.services.scoring import GameweekScoringService, ScoringOutcome
from vmf_api.services.violations import DetectionResult, detect_transfer_violations


@dataclass(frozen=True, slots=True)
class SyncPlan:
    season_code: str
    gameweek_number: int | None
    run_picks: bool
    run_live: bool
    run_entry_history: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ScheduledSyncResult:
    plan: SyncPlan | None
    outcomes: list[SyncOutcome] = field(default_factory=list)
    scoring: ScoringOutcome | None = None
    detection: DetectionResult | None = None
    settlement: SettlementOutcome | None = None
    skipped_reason: str | None = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def run_scheduled_sync(
    session: AsyncSession,
    client: FPLClient,
    settings: Settings,
    *,
    correlation_id: str | None = None,
    clock: Callable[[], datetime] = _utcnow,
) -> ScheduledSyncResult:
    season = await session.scalar(
        select(Season).where(Season.fpl_season_code == settings.active_season_code)
    )
    if season is None:
        return ScheduledSyncResult(plan=None, skipped_reason="season_not_bootstrapped")

    service = FplIngestionService(
        session,
        client,
        season=season,
        correlation_id=correlation_id,
        max_concurrency=settings.fpl_max_concurrency,
        clock=clock,
    )

    outcomes = [await service.sync_bootstrap(), await service.sync_fixtures()]

    plan = await _build_plan(session, season, clock=clock)
    scoring: ScoringOutcome | None = None
    detection: DetectionResult | None = None
    settlement: SettlementOutcome | None = None
    if plan.gameweek_number is not None:
        if plan.run_picks:
            outcomes.append(
                await service.sync_picks(
                    plan.gameweek_number,
                    manager_limit=settings.sync_manager_batch_size,
                )
            )
        if plan.run_live:
            outcomes.append(await service.sync_live(plan.gameweek_number))
        if plan.run_entry_history:
            outcomes.append(
                await service.sync_entry_history(manager_limit=settings.sync_manager_batch_size)
            )
        # Scoring reads only what the jobs above just wrote, so it runs on the
        # same transaction and reflects this tick's data rather than the last.
        scoring = await GameweekScoringService(
            session,
            season_id=season.id,
            clock=clock,
        ).score_gameweek(plan.gameweek_number)
        # Detection only raises cases for review; no penalty follows from a
        # synchronisation, so this is safe to repeat on every tick.
        detection = await detect_transfer_violations(session)
        # Results follow the scores that were just written, so a live Gameweek
        # shows a live H2H result rather than a fixture that never resolves.
        settlement = await H2HSettlementService(
            session,
            season_id=season.id,
        ).settle_gameweek(plan.gameweek_number)
    return ScheduledSyncResult(
        plan=plan,
        outcomes=outcomes,
        scoring=scoring,
        detection=detection,
        settlement=settlement,
    )


async def _build_plan(
    session: AsyncSession,
    season: Season,
    *,
    clock: Callable[[], datetime],
) -> SyncPlan:
    now = naive_utc(clock())
    current = await session.scalar(
        select(Gameweek.number)
        .where(
            Gameweek.season_id == season.id,
            Gameweek.deadline_time.is_not(None),
            Gameweek.deadline_time <= now,
        )
        .order_by(Gameweek.number.desc())
        .limit(1)
    )
    if current is None:
        return SyncPlan(
            season_code=season.fpl_season_code,
            gameweek_number=None,
            run_picks=False,
            run_live=False,
            run_entry_history=False,
            reason="before_first_deadline",
        )

    started, settled = await _fixture_progress(session, season, current)
    managers_missing_history = await _managers_missing_history(session, current)

    return SyncPlan(
        season_code=season.fpl_season_code,
        gameweek_number=current,
        # Squads open after the deadline and keep changing until FPL resolves
        # automatic substitutions, so picks are refreshed for the whole window.
        run_picks=True,
        run_live=started,
        run_entry_history=settled or managers_missing_history,
        reason="deadline_passed",
    )


async def _fixture_progress(
    session: AsyncSession,
    season: Season,
    gameweek_number: int,
) -> tuple[bool, bool]:
    rows = list(
        await session.execute(
            select(FplFixture.started, FplFixture.finished, FplFixture.finished_provisional).where(
                FplFixture.season_id == season.id,
                FplFixture.gameweek_number == gameweek_number,
            )
        )
    )
    started = any(row.started for row in rows)
    settled = any(row.finished or row.finished_provisional for row in rows)
    return started, settled


async def _managers_missing_history(session: AsyncSession, gameweek_number: int) -> bool:
    active = await session.scalar(
        select(func.count())
        .select_from(Manager)
        .where(
            Manager.registration_status == RegistrationStatus.CONFIRMED,
            Manager.active_status == ManagerStatus.ACTIVE,
        )
    )
    if not active:
        return False
    recorded = await session.scalar(
        select(func.count())
        .select_from(ManagerGameweekHistory)
        .where(ManagerGameweekHistory.gameweek_number == gameweek_number)
    )
    return (recorded or 0) < active
