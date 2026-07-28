from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from vmf_api.api.deps import CronAuthorizationDep, FPLClientDep, SessionDep, SettingsDep
from vmf_api.integrations.fpl import FPLClientError
from vmf_api.schemas.cron import (
    CronSyncResponse,
    FPLProbeResponse,
    SyncJobResult,
    SyncPlanResponse,
)
from vmf_api.services.cron import fpl_probe_lock, fpl_sync_lock
from vmf_api.services.sync_orchestrator import run_scheduled_sync

router = APIRouter(prefix="/cron", tags=["cron"])


async def _run_fpl_probe(
    session: SessionDep,
    client: FPLClientDep,
) -> FPLProbeResponse:
    observed_at = datetime.now(UTC)
    async with fpl_probe_lock(session) as acquired:
        if not acquired:
            return FPLProbeResponse(
                status="skipped",
                reason="already_running",
                observed_at=observed_at,
            )

        try:
            bootstrap, fixtures = await asyncio.gather(
                client.bootstrap(),
                client.fixtures(),
            )
        except FPLClientError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="FPL upstream request failed",
            ) from error

        if not isinstance(bootstrap, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="FPL upstream response has an invalid bootstrap payload",
            )
        events = _list_field(bootstrap, "events")
        teams = _list_field(bootstrap, "teams")
        players = _list_field(bootstrap, "elements")
        if not isinstance(fixtures, list):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="FPL upstream response has an invalid fixtures payload",
            )

        current_gameweek = _event_id(events, "is_current")
        if current_gameweek is None:
            current_gameweek = _event_id(events, "is_next")

        return FPLProbeResponse(
            status="observed",
            observed_at=observed_at,
            current_gameweek=current_gameweek,
            event_count=len(events),
            team_count=len(teams),
            player_count=len(players),
            fixture_count=len(fixtures),
        )


@router.post("/fpl-probe", response_model=FPLProbeResponse)
async def probe_fpl(
    _: CronAuthorizationDep,
    session: SessionDep,
    client: FPLClientDep,
) -> FPLProbeResponse:
    """Read FPL metadata without mutating competition state."""

    return await _run_fpl_probe(session, client)


@router.get("/fpl-probe", response_model=FPLProbeResponse)
async def probe_fpl_from_vercel_cron(
    _: CronAuthorizationDep,
    session: SessionDep,
    client: FPLClientDep,
) -> FPLProbeResponse:
    """GET variant for Vercel Cron; Supabase Cron should use POST."""

    return await _run_fpl_probe(session, client)


async def _run_sync(
    session: SessionDep,
    client: FPLClientDep,
    settings: SettingsDep,
) -> CronSyncResponse:
    started_at = datetime.now(UTC)
    async with fpl_sync_lock(session) as acquired:
        if not acquired:
            return CronSyncResponse(
                status="skipped",
                reason="already_running",
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )

        result = await run_scheduled_sync(session, client, settings)
        # The advisory lock is transaction-scoped, so committing both persists
        # the source facts and releases it for the next tick.
        await session.commit()

        if result.plan is None:
            return CronSyncResponse(
                status="skipped",
                reason="season_not_bootstrapped",
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )
        return CronSyncResponse(
            status="executed",
            started_at=started_at,
            finished_at=datetime.now(UTC),
            plan=SyncPlanResponse(
                season_code=result.plan.season_code,
                gameweek_number=result.plan.gameweek_number,
                run_picks=result.plan.run_picks,
                run_live=result.plan.run_live,
                run_entry_history=result.plan.run_entry_history,
                reason=result.plan.reason,
            ),
            jobs=[
                SyncJobResult(
                    job_type=outcome.job_type,
                    status=outcome.status,
                    records_written=outcome.records_written,
                    payload_changed=outcome.payload_changed,
                    gameweek_number=outcome.gameweek_number,
                    detail=outcome.detail or None,
                    error=outcome.error,
                )
                for outcome in result.outcomes
            ],
        )


@router.post("/sync", response_model=CronSyncResponse)
async def sync_fpl(
    _: CronAuthorizationDep,
    session: SessionDep,
    client: FPLClientDep,
    settings: SettingsDep,
) -> CronSyncResponse:
    """Run the synchronization jobs whose preconditions currently hold."""

    return await _run_sync(session, client, settings)


@router.get("/sync", response_model=CronSyncResponse)
async def sync_fpl_from_vercel_cron(
    _: CronAuthorizationDep,
    session: SessionDep,
    client: FPLClientDep,
    settings: SettingsDep,
) -> CronSyncResponse:
    """GET variant for Vercel Cron; Supabase Cron should use POST."""

    return await _run_sync(session, client, settings)


def _list_field(payload: dict[str, Any], field: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"FPL upstream response has an invalid {field} payload",
        )
    return value


def _event_id(events: list[Any], flag: str) -> int | None:
    for event in events:
        if not isinstance(event, dict) or not event.get(flag):
            continue
        event_id = event.get("id")
        if isinstance(event_id, int):
            return event_id
    return None
