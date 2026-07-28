from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import vmf_api.models  # noqa: F401  (registers every table on the metadata)
from vmf_api.db.base import Base
from vmf_api.integrations.fpl import FPLClientError
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus, SyncStatus
from vmf_api.models.ingestion import (
    FplFixture,
    FplPlayer,
    FplPlayerFixtureStat,
    FplTeam,
    ManagerGameweekHistory,
    ManagerPickItem,
    ManagerPickSnapshot,
    RawFplResponse,
    SyncRun,
)
from vmf_api.models.manager import Manager
from vmf_api.services.ingestion import FplIngestionService

DEADLINE = datetime(2026, 8, 21, 17, 30)
AFTER_DEADLINE = datetime(2026, 8, 21, 19, 0, tzinfo=UTC)
BEFORE_DEADLINE = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)


class FakeFPLClient:
    """Programmable stand-in for the FPL gateway."""

    def __init__(
        self,
        *,
        bootstrap: Any = None,
        fixtures: Any = None,
        live: Any = None,
        picks: dict[int, Any] | None = None,
        history: dict[int, Any] | None = None,
    ) -> None:
        self.bootstrap_payload = bootstrap
        self.fixtures_payload = fixtures
        self.live_payload = live
        self.picks_payloads = picks or {}
        self.history_payloads = history or {}
        self.calls: list[str] = []

    async def bootstrap(self) -> Any:
        self.calls.append("bootstrap")
        return _payload_or_raise(self.bootstrap_payload, "bootstrap-static/")

    async def fixtures(self) -> Any:
        self.calls.append("fixtures")
        return _payload_or_raise(self.fixtures_payload, "fixtures/")

    async def live(self, gameweek: int) -> Any:
        self.calls.append(f"live:{gameweek}")
        return _payload_or_raise(self.live_payload, f"event/{gameweek}/live/")

    async def picks(self, entry_id: int, gameweek: int) -> Any:
        self.calls.append(f"picks:{entry_id}:{gameweek}")
        return _payload_or_raise(
            self.picks_payloads.get(entry_id),
            f"entry/{entry_id}/event/{gameweek}/picks/",
        )

    async def entry_history(self, entry_id: int) -> Any:
        self.calls.append(f"history:{entry_id}")
        return _payload_or_raise(
            self.history_payloads.get(entry_id),
            f"entry/{entry_id}/history/",
        )


def _payload_or_raise(payload: Any, path: str) -> Any:
    if payload is None:
        raise FPLClientError("FPL returned HTTP 404", path=path, status_code=404)
    if isinstance(payload, FPLClientError):
        raise payload
    return payload


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed(session: AsyncSession, *, manager_entry_ids: tuple[int, ...] = ()) -> Season:
    season = Season(
        name="VMF Fantasy League 2026/27",
        fpl_season_code="2026/27",
        start_gameweek=1,
        end_gameweek=38,
    )
    session.add(season)
    await session.flush()
    session.add_all(
        [
            Gameweek(season_id=season.id, number=1, deadline_time=DEADLINE),
            Gameweek(season_id=season.id, number=2),
        ]
    )
    for index, entry_id in enumerate(manager_entry_ids, start=1):
        session.add(
            Manager(
                fpl_entry_id=entry_id,
                manager_name=f"Manager {index}",
                team_name=f"Team {index}",
                division=Division.HIGH,
                active_status=ManagerStatus.ACTIVE,
                registration_status=RegistrationStatus.CONFIRMED,
                season_joined="2026/27",
            )
        )
    await session.flush()
    return season


def _service(
    session: AsyncSession,
    client: FakeFPLClient,
    season: Season,
    *,
    now: datetime = AFTER_DEADLINE,
) -> FplIngestionService:
    return FplIngestionService(session, client, season=season, clock=lambda: now)


def bootstrap_payload(deadline: str = "2026-08-21T17:30:00Z") -> dict[str, Any]:
    return {
        "events": [
            {
                "id": 1,
                "name": "Gameweek 1",
                "deadline_time": deadline,
                "finished": False,
                "data_checked": False,
            }
        ],
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS"}],
        "elements": [
            {
                "id": 10,
                "team": 1,
                "element_type": 3,
                "web_name": "Saka",
                "first_name": "Bukayo",
                "second_name": "Saka",
            }
        ],
    }


def picks_payload(*, captain_multiplier: int = 2, chip: str | None = None) -> dict[str, Any]:
    return {
        "active_chip": chip,
        "entry_history": {
            "event": 1,
            "points": 72,
            "event_transfers": 2,
            "event_transfers_cost": 4,
            "points_on_bench": 6,
        },
        "picks": [
            {"element": 10, "position": 1, "multiplier": captain_multiplier, "is_captain": True},
            {"element": 11, "position": 2, "multiplier": 1, "is_vice_captain": True},
        ],
    }


def history_payload(points: int = 72) -> dict[str, Any]:
    return {
        "current": [
            {
                "event": 1,
                "points": points,
                "total_points": points,
                "event_transfers": 2,
                "event_transfers_cost": 4,
                "points_on_bench": 6,
                "value": 1000,
                "bank": 5,
            }
        ]
    }


async def test_bootstrap_sync_stores_catalog_and_gameweek_deadline() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session)
        client = FakeFPLClient(bootstrap=bootstrap_payload())

        outcome = await _service(session, client, season).sync_bootstrap()
        await session.commit()

        gameweek = await session.scalar(select(Gameweek).where(Gameweek.number == 1))
        teams = await session.scalar(select(func.count()).select_from(FplTeam))
        players = await session.scalar(select(func.count()).select_from(FplPlayer))

    assert outcome.status is SyncStatus.SUCCEEDED
    assert outcome.payload_changed is True
    assert (teams, players) == (1, 1)
    assert gameweek is not None and gameweek.deadline_time == DEADLINE
    await engine.dispose()


async def test_repeating_bootstrap_sync_is_idempotent() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session)
        client = FakeFPLClient(bootstrap=bootstrap_payload())
        service = _service(session, client, season)

        await service.sync_bootstrap()
        second = await service.sync_bootstrap()
        await session.commit()

        raw_rows = list(await session.scalars(select(RawFplResponse)))
        players = await session.scalar(select(func.count()).select_from(FplPlayer))

    assert second.payload_changed is False
    assert second.records_written == 0
    assert len(raw_rows) == 1
    assert raw_rows[0].seen_count == 2
    # Shared payloads are kept by hash only to protect the free-tier quota.
    assert raw_rows[0].payload_json is None
    assert players == 1
    await engine.dispose()


async def test_bootstrap_quarantine_records_the_run_without_writing_facts() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session)
        client = FakeFPLClient(bootstrap={"events": [], "teams": [], "elements": []})

        outcome = await _service(session, client, season).sync_bootstrap()
        await session.commit()

        players = await session.scalar(select(func.count()).select_from(FplPlayer))
        run = await session.scalar(select(SyncRun))

    assert outcome.status is SyncStatus.QUARANTINED
    assert players == 0
    assert run is not None and run.status is SyncStatus.QUARANTINED and run.error
    await engine.dispose()


async def test_rescheduled_fixture_leaves_its_previous_gameweek_aggregate() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session)
        client = FakeFPLClient(fixtures=[{"id": 100, "event": 1, "started": False}])
        service = _service(session, client, season)
        await service.sync_fixtures()
        session.add(
            FplPlayerFixtureStat(
                season_id=season.id,
                gameweek_number=1,
                element_id=10,
                fixture_fpl_id=100,
                minutes=90,
                total_points=6,
                goals_scored=1,
                assists=0,
                yellow_cards=0,
                red_cards=0,
                bonus=0,
            )
        )
        await session.flush()

        client.fixtures_payload = [{"id": 100, "event": 2, "started": False}]
        outcome = await service.sync_fixtures()
        await session.commit()

        remaining = list(await session.scalars(select(FplPlayerFixtureStat)))
        fixture = await session.scalar(select(FplFixture))

    assert fixture is not None and fixture.gameweek_number == 2
    assert remaining == []
    assert outcome.detail["rescheduled"] == [{"fixture": 100, "from_gameweek": 1, "to_gameweek": 2}]
    await engine.dispose()


async def test_live_sync_keeps_both_fixtures_of_a_double_gameweek() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session)
        client = FakeFPLClient(
            fixtures=[{"id": 100, "event": 1}, {"id": 101, "event": 1}],
            live={
                "elements": [
                    {
                        "id": 10,
                        "stats": {"total_points": 15, "minutes": 180},
                        "explain": [
                            {
                                "fixture": 100,
                                "stats": [
                                    {"identifier": "minutes", "value": 90, "points": 2},
                                    {"identifier": "goals_scored", "value": 1, "points": 4},
                                ],
                            },
                            {
                                "fixture": 101,
                                "stats": [
                                    {"identifier": "minutes", "value": 90, "points": 2},
                                    {"identifier": "goals_scored", "value": 2, "points": 8},
                                    {"identifier": "yellow_cards", "value": 1, "points": -1},
                                ],
                            },
                        ],
                    }
                ]
            },
        )
        service = _service(session, client, season)
        await service.sync_fixtures()

        outcome = await service.sync_live(1)
        await session.commit()

        rows = list(
            await session.scalars(
                select(FplPlayerFixtureStat).order_by(FplPlayerFixtureStat.fixture_fpl_id)
            )
        )

    assert outcome.status is SyncStatus.SUCCEEDED
    assert [row.total_points for row in rows] == [6, 9]
    assert sum(row.goals_scored for row in rows) == 3
    assert rows[1].yellow_cards == 1
    await engine.dispose()


async def test_live_sync_reports_elements_without_a_usable_breakdown() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session)
        client = FakeFPLClient(
            fixtures=[{"id": 100, "event": 1}],
            live={"elements": [{"id": 10, "stats": {"total_points": 6, "minutes": 90}}]},
        )
        service = _service(session, client, season)
        await service.sync_fixtures()

        outcome = await service.sync_live(1)
        await session.commit()

        rows = await session.scalar(select(func.count()).select_from(FplPlayerFixtureStat))

    assert outcome.status is SyncStatus.PARTIAL
    assert outcome.detail["unresolved_elements"] == 1
    # A missing breakdown must never be materialized as a zero-point row.
    assert rows == 0
    await engine.dispose()


async def test_live_sync_refuses_a_fixture_that_is_not_in_this_gameweek() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session)
        client = FakeFPLClient(
            fixtures=[{"id": 100, "event": 1}],
            live={
                "elements": [
                    {
                        "id": 10,
                        "stats": {"total_points": 2, "minutes": 90},
                        "explain": [
                            {
                                "fixture": 999,
                                "stats": [{"identifier": "minutes", "value": 90, "points": 2}],
                            }
                        ],
                    }
                ]
            },
        )
        service = _service(session, client, season)
        await service.sync_fixtures()

        outcome = await service.sync_live(1)
        await session.commit()

        rows = await session.scalar(select(func.count()).select_from(FplPlayerFixtureStat))

    assert outcome.status is SyncStatus.PARTIAL
    assert outcome.detail["unknown_fixtures"] == [999]
    assert rows == 0
    await engine.dispose()


async def test_picks_are_not_requested_before_the_deadline() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session, manager_entry_ids=(111,))
        client = FakeFPLClient(picks={111: picks_payload()})

        outcome = await _service(session, client, season, now=BEFORE_DEADLINE).sync_picks(1)
        await session.commit()

    assert outcome.status is SyncStatus.SKIPPED
    assert outcome.detail["reason"] == "sealed_until_deadline"
    assert client.calls == []
    await engine.dispose()


async def test_picks_snapshot_is_created_once_per_distinct_payload() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session, manager_entry_ids=(111,))
        client = FakeFPLClient(picks={111: picks_payload()})
        service = _service(session, client, season)

        first = await service.sync_picks(1)
        unchanged = await service.sync_picks(1)
        client.picks_payloads[111] = picks_payload(captain_multiplier=3, chip="3xc")
        changed = await service.sync_picks(1)
        await session.commit()

        snapshots = list(
            await session.scalars(
                select(ManagerPickSnapshot).order_by(ManagerPickSnapshot.revision)
            )
        )
        items = await session.scalar(select(func.count()).select_from(ManagerPickItem))
        raw = await session.scalar(
            select(RawFplResponse).where(RawFplResponse.endpoint_name == "entry_picks")
        )

    assert first.records_written == 1
    assert unchanged.records_written == 0
    assert changed.records_written == 1
    assert [snapshot.revision for snapshot in snapshots] == [1, 2]
    assert snapshots[0].transfer_cost == 4
    assert snapshots[1].active_chip == "3xc"
    assert items == 4
    # Manager-scoped evidence is small enough to keep in full.
    assert raw is not None and raw.payload_json is not None
    await engine.dispose()


async def test_unavailable_picks_do_not_block_the_other_managers() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session, manager_entry_ids=(111, 222))
        client = FakeFPLClient(picks={111: picks_payload()})

        outcome = await _service(session, client, season).sync_picks(1)
        await session.commit()

        snapshots = await session.scalar(select(func.count()).select_from(ManagerPickSnapshot))

    assert outcome.status is SyncStatus.PARTIAL
    assert outcome.detail["sealed_or_not_ready"] == [222]
    assert snapshots == 1
    await engine.dispose()


async def test_picks_batch_prioritizes_managers_without_a_snapshot() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session, manager_entry_ids=(111, 222))
        client = FakeFPLClient(picks={111: picks_payload(), 222: picks_payload()})
        service = _service(session, client, season)

        await service.sync_picks(1, manager_limit=1)
        client.calls.clear()
        await service.sync_picks(1, manager_limit=1)
        await session.commit()

        captured = sorted(
            entry_id
            for entry_id in await session.scalars(
                select(Manager.fpl_entry_id).join(
                    ManagerPickSnapshot, ManagerPickSnapshot.manager_id == Manager.id
                )
            )
        )

    assert client.calls == ["picks:222:1"]
    assert captured == [111, 222]
    await engine.dispose()


async def test_entry_history_upserts_official_points_and_transfer_cost() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session, manager_entry_ids=(111,))
        client = FakeFPLClient(history={111: history_payload()})
        service = _service(session, client, season)

        await service.sync_entry_history()
        client.history_payloads[111] = history_payload(points=75)
        corrected = await service.sync_entry_history()
        await session.commit()

        rows = list(await session.scalars(select(ManagerGameweekHistory)))

    assert corrected.records_written == 1
    assert len(rows) == 1
    assert (rows[0].gross_points, rows[0].transfer_cost) == (75, 4)
    await engine.dispose()


async def test_entry_history_failure_is_reported_not_zeroed() -> None:
    factory, engine = await _database()
    async with factory() as session:
        season = await _seed(session, manager_entry_ids=(111,))
        client = FakeFPLClient()

        outcome = await _service(session, client, season).sync_entry_history()
        await session.commit()

        rows = await session.scalar(select(func.count()).select_from(ManagerGameweekHistory))
        run = await session.scalar(select(SyncRun))

    assert outcome.status is SyncStatus.PARTIAL
    assert outcome.detail["unavailable"] == [111]
    assert rows == 0
    assert run is not None and run.status is SyncStatus.PARTIAL
    await engine.dispose()
