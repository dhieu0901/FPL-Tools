from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from test_ingestion import FakeFPLClient, _database, _seed, bootstrap_payload, history_payload

from vmf_api.core.config import Settings
from vmf_api.models.enums import SyncJobType, SyncStatus
from vmf_api.models.ingestion import FplPlayer, ManagerPickSnapshot, SyncRun
from vmf_api.services.sync_orchestrator import run_scheduled_sync

AFTER_DEADLINE = datetime(2026, 8, 21, 19, 0, tzinfo=UTC)
BEFORE_DEADLINE = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)


def _settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        active_season_code="2026/27",
        **overrides,
    )


def picks_payload() -> dict[str, object]:
    return {
        "active_chip": None,
        "entry_history": {
            "event": 1,
            "points": 60,
            "event_transfers": 0,
            "event_transfers_cost": 0,
            "points_on_bench": 3,
        },
        "picks": [
            {"element": 10, "position": 1, "multiplier": 2, "is_captain": True},
            {"element": 11, "position": 2, "multiplier": 1, "is_vice_captain": True},
        ],
    }


def _job_types(result: object) -> list[SyncJobType]:
    return [outcome.job_type for outcome in result.outcomes]  # type: ignore[attr-defined]


async def test_sync_is_skipped_until_the_season_is_bootstrapped() -> None:
    factory, engine = await _database()
    async with factory() as session:
        result = await run_scheduled_sync(session, FakeFPLClient(), _settings())

    assert result.plan is None
    assert result.skipped_reason == "season_not_bootstrapped"
    await engine.dispose()


async def test_before_the_first_deadline_only_shared_catalogs_are_synced() -> None:
    factory, engine = await _database()
    async with factory() as session:
        await _seed(session, manager_entry_ids=(111,))
        client = FakeFPLClient(bootstrap=bootstrap_payload(), fixtures=[])

        result = await run_scheduled_sync(
            session,
            client,
            _settings(),
            clock=lambda: BEFORE_DEADLINE,
        )
        await session.commit()

    assert result.plan is not None
    assert result.plan.gameweek_number is None
    assert result.plan.reason == "before_first_deadline"
    assert _job_types(result) == [SyncJobType.BOOTSTRAP, SyncJobType.FIXTURES]
    await engine.dispose()


async def test_after_the_deadline_picks_and_history_run_but_live_waits_for_kickoff() -> None:
    factory, engine = await _database()
    async with factory() as session:
        await _seed(session, manager_entry_ids=(111,))
        client = FakeFPLClient(
            bootstrap=bootstrap_payload(),
            fixtures=[{"id": 100, "event": 1, "started": False}],
            picks={111: picks_payload()},
            history={111: history_payload()},
        )

        result = await run_scheduled_sync(
            session,
            client,
            _settings(),
            clock=lambda: AFTER_DEADLINE,
        )
        await session.commit()

        snapshots = list(await session.scalars(select(ManagerPickSnapshot)))

    assert result.plan is not None
    assert (result.plan.gameweek_number, result.plan.run_live) == (1, False)
    assert _job_types(result) == [
        SyncJobType.BOOTSTRAP,
        SyncJobType.FIXTURES,
        SyncJobType.PICKS,
        SyncJobType.ENTRY_HISTORY,
    ]
    assert [snapshot.revision for snapshot in snapshots] == [1]
    await engine.dispose()


async def test_live_sync_starts_once_a_fixture_has_kicked_off() -> None:
    factory, engine = await _database()
    async with factory() as session:
        await _seed(session, manager_entry_ids=(111,))
        client = FakeFPLClient(
            bootstrap=bootstrap_payload(),
            fixtures=[{"id": 100, "event": 1, "started": True}],
            live={"elements": []},
            picks={111: picks_payload()},
            history={111: history_payload()},
        )

        result = await run_scheduled_sync(
            session,
            client,
            _settings(),
            clock=lambda: AFTER_DEADLINE,
        )
        await session.commit()

    assert result.plan is not None and result.plan.run_live is True
    assert SyncJobType.LIVE in _job_types(result)
    await engine.dispose()


async def test_a_failing_upstream_is_recorded_without_stopping_the_other_jobs() -> None:
    factory, engine = await _database()
    async with factory() as session:
        await _seed(session, manager_entry_ids=(111,))
        # No fixtures payload: the gateway reports the endpoint as unavailable.
        client = FakeFPLClient(bootstrap=bootstrap_payload(), picks={111: picks_payload()})

        result = await run_scheduled_sync(
            session,
            client,
            _settings(),
            clock=lambda: AFTER_DEADLINE,
        )
        await session.commit()

        players = await session.scalar(select(func.count()).select_from(FplPlayer))
        snapshots = await session.scalar(select(func.count()).select_from(ManagerPickSnapshot))
        runs = {
            job_type: status
            for job_type, status in await session.execute(select(SyncRun.job_type, SyncRun.status))
        }

    outcomes = {outcome.job_type: outcome for outcome in result.outcomes}
    assert outcomes[SyncJobType.FIXTURES].status is SyncStatus.FAILED
    assert outcomes[SyncJobType.BOOTSTRAP].status is SyncStatus.SUCCEEDED
    assert outcomes[SyncJobType.PICKS].status is SyncStatus.SUCCEEDED
    # The failed job rolls back only its own savepoint.
    assert (players, snapshots) == (1, 1)
    assert runs[SyncJobType.FIXTURES] is SyncStatus.FAILED
    await engine.dispose()
