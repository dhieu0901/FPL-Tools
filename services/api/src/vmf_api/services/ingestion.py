"""Synchronization jobs that turn FPL responses into VMF source facts.

Every job is idempotent: it stores raw evidence by payload hash, upserts
normalized rows, and records a :class:`SyncRun`. A failed or quarantined source
never becomes a zero score; it becomes a recorded run that blocks finalization
later in the pipeline.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.integrations.fpl import FPLClient, FPLClientError
from vmf_api.integrations.fpl_parsers import (
    ParsedFixture,
    ParsedPicks,
    SchemaQuarantineError,
    parse_bootstrap,
    parse_entry_history,
    parse_fixtures,
    parse_live,
    parse_picks,
)
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import ManagerStatus, RegistrationStatus, SyncJobType, SyncStatus
from vmf_api.models.ingestion import (
    FplFixture,
    FplPlayer,
    FplPlayerFixtureStat,
    FplTeam,
    ManagerGameweekHistory,
    ManagerPickItem,
    ManagerPickSnapshot,
    SyncRun,
)
from vmf_api.models.manager import Manager
from vmf_api.services.raw_store import naive_utc, payload_digest, record_raw_response

#: Manager-scoped payloads are small and are the evidence behind a score, so
#: they are stored in full. Shared payloads are kept by hash only.
PERSISTED_PAYLOAD_ENDPOINTS = frozenset({"entry_picks", "entry_history"})


@dataclass(frozen=True, slots=True)
class SyncOutcome:
    job_type: SyncJobType
    status: SyncStatus
    records_written: int = 0
    payload_changed: bool = False
    gameweek_number: int | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


class FplIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        client: FPLClient,
        *,
        season: Season,
        correlation_id: str | None = None,
        max_concurrency: int = 4,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.session = session
        self.client = client
        # Plain values, not the ORM instance: a job that rolls back its
        # savepoint would otherwise expire the row and trigger lazy IO.
        self.season_id = season.id
        self.season_code = season.fpl_season_code
        self.correlation_id = correlation_id
        self.clock = clock
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))

    async def sync_bootstrap(self) -> SyncOutcome:
        return await self._run(SyncJobType.BOOTSTRAP, None, self._sync_bootstrap)

    async def sync_fixtures(self) -> SyncOutcome:
        return await self._run(SyncJobType.FIXTURES, None, self._sync_fixtures)

    async def sync_live(self, gameweek_number: int) -> SyncOutcome:
        return await self._run(
            SyncJobType.LIVE,
            gameweek_number,
            lambda: self._sync_live(gameweek_number),
        )

    async def sync_picks(
        self,
        gameweek_number: int,
        *,
        manager_limit: int | None = None,
    ) -> SyncOutcome:
        return await self._run(
            SyncJobType.PICKS,
            gameweek_number,
            lambda: self._sync_picks(gameweek_number, manager_limit=manager_limit),
        )

    async def sync_entry_history(self, *, manager_limit: int | None = None) -> SyncOutcome:
        return await self._run(
            SyncJobType.ENTRY_HISTORY,
            None,
            lambda: self._sync_entry_history(manager_limit=manager_limit),
        )

    async def _sync_bootstrap(self) -> SyncOutcome:
        observed_at = self.clock()
        payload = await self.client.bootstrap()
        record = await self._record_raw(
            endpoint_name="bootstrap",
            request_key="bootstrap-static/",
            payload=payload,
            observed_at=observed_at,
        )
        parsed = parse_bootstrap(payload)

        written = 0
        existing_teams = await self._by_key(FplTeam, FplTeam.team_fpl_id)
        for team in parsed.teams:
            row = existing_teams.get(team.team_fpl_id)
            if row is None:
                self.session.add(
                    FplTeam(
                        season_id=self.season_id,
                        team_fpl_id=team.team_fpl_id,
                        name=team.name,
                        short_name=team.short_name,
                    )
                )
                written += 1
            elif (row.name, row.short_name) != (team.name, team.short_name):
                row.name = team.name
                row.short_name = team.short_name
                written += 1

        existing_players = await self._by_key(FplPlayer, FplPlayer.element_id)
        for player in parsed.players:
            row = existing_players.get(player.element_id)
            if row is None:
                self.session.add(
                    FplPlayer(
                        season_id=self.season_id,
                        element_id=player.element_id,
                        web_name=player.web_name,
                        full_name=player.full_name,
                        team_fpl_id=player.team_fpl_id,
                        element_type=player.element_type,
                        status=player.status,
                        now_cost=player.now_cost,
                    )
                )
                written += 1
                continue
            changed = (
                row.web_name != player.web_name
                or row.full_name != player.full_name
                or row.team_fpl_id != player.team_fpl_id
                or row.element_type != player.element_type
                or row.status != player.status
                or row.now_cost != player.now_cost
            )
            if changed:
                row.web_name = player.web_name
                row.full_name = player.full_name
                row.team_fpl_id = player.team_fpl_id
                row.element_type = player.element_type
                row.status = player.status
                row.now_cost = player.now_cost
                written += 1

        gameweeks = await self._gameweeks()
        events_applied = 0
        for event in parsed.events:
            gameweek = gameweeks.get(event.number)
            if gameweek is None:
                # The season catalog is created by the bootstrap-season command;
                # ingestion never invents Gameweek rows for it.
                continue
            deadline = None if event.deadline_time is None else naive_utc(event.deadline_time)
            if (
                gameweek.deadline_time != deadline
                or gameweek.fpl_finished != event.finished
                or gameweek.fpl_data_checked != event.data_checked
            ):
                gameweek.deadline_time = deadline
                gameweek.fpl_finished = event.finished
                gameweek.fpl_data_checked = event.data_checked
                events_applied += 1

        await self.session.flush()
        return SyncOutcome(
            job_type=SyncJobType.BOOTSTRAP,
            status=SyncStatus.SUCCEEDED,
            records_written=written + events_applied,
            payload_changed=record.payload_changed,
            detail={
                "teams": len(parsed.teams),
                "players": len(parsed.players),
                "events": len(parsed.events),
                "gameweeks_updated": events_applied,
            },
        )

    async def _sync_fixtures(self) -> SyncOutcome:
        observed_at = self.clock()
        payload = await self.client.fixtures()
        record = await self._record_raw(
            endpoint_name="fixtures",
            request_key="fixtures/",
            payload=payload,
            observed_at=observed_at,
        )
        parsed = parse_fixtures(payload)

        existing = await self._by_key(FplFixture, FplFixture.fixture_fpl_id)
        written = 0
        rescheduled: list[dict[str, int | None]] = []
        for fixture in parsed:
            row = existing.get(fixture.fixture_fpl_id)
            if row is None:
                self.session.add(self._new_fixture(fixture))
                written += 1
                continue
            previous_gameweek = row.gameweek_number
            if not self._apply_fixture(row, fixture):
                continue
            written += 1
            if previous_gameweek is not None and previous_gameweek != fixture.gameweek_number:
                # A rescheduled fixture must leave its old Gameweek aggregate,
                # otherwise the same minutes would be counted twice.
                await self.session.execute(
                    delete(FplPlayerFixtureStat).where(
                        FplPlayerFixtureStat.season_id == self.season_id,
                        FplPlayerFixtureStat.fixture_fpl_id == fixture.fixture_fpl_id,
                        FplPlayerFixtureStat.gameweek_number == previous_gameweek,
                    )
                )
                rescheduled.append(
                    {
                        "fixture": fixture.fixture_fpl_id,
                        "from_gameweek": previous_gameweek,
                        "to_gameweek": fixture.gameweek_number,
                    }
                )

        await self.session.flush()
        return SyncOutcome(
            job_type=SyncJobType.FIXTURES,
            status=SyncStatus.SUCCEEDED,
            records_written=written,
            payload_changed=record.payload_changed,
            detail={"fixtures": len(parsed), "rescheduled": rescheduled},
        )

    async def _sync_live(self, gameweek_number: int) -> SyncOutcome:
        observed_at = self.clock()
        payload = await self.client.live(gameweek_number)
        record = await self._record_raw(
            endpoint_name="event_live",
            request_key=f"event/{gameweek_number}/live/",
            payload=payload,
            observed_at=observed_at,
            gameweek_number=gameweek_number,
        )
        parsed = parse_live(payload)

        known_fixtures = set(
            await self.session.scalars(
                select(FplFixture.fixture_fpl_id).where(
                    FplFixture.season_id == self.season_id,
                    FplFixture.gameweek_number == gameweek_number,
                )
            )
        )
        existing_rows = list(
            await self.session.scalars(
                select(FplPlayerFixtureStat).where(
                    FplPlayerFixtureStat.season_id == self.season_id,
                    FplPlayerFixtureStat.gameweek_number == gameweek_number,
                )
            )
        )
        existing = {(row.element_id, row.fixture_fpl_id): row for row in existing_rows}

        written = 0
        unknown_fixtures: set[int] = set()
        for stat in parsed.stats:
            if known_fixtures and stat.fixture_fpl_id not in known_fixtures:
                # Either the fixture catalog is behind or the fixture moved.
                # Recording it under this Gameweek would fabricate provenance.
                unknown_fixtures.add(stat.fixture_fpl_id)
                continue
            row = existing.get((stat.element_id, stat.fixture_fpl_id))
            if row is None:
                self.session.add(
                    FplPlayerFixtureStat(
                        season_id=self.season_id,
                        gameweek_number=gameweek_number,
                        element_id=stat.element_id,
                        fixture_fpl_id=stat.fixture_fpl_id,
                        minutes=stat.minutes,
                        total_points=stat.total_points,
                        goals_scored=stat.goals_scored,
                        assists=stat.assists,
                        yellow_cards=stat.yellow_cards,
                        red_cards=stat.red_cards,
                        bonus=stat.bonus,
                        source_raw_id=record.row.id,
                    )
                )
                written += 1
                continue
            changed = (
                row.minutes != stat.minutes
                or row.total_points != stat.total_points
                or row.goals_scored != stat.goals_scored
                or row.assists != stat.assists
                or row.yellow_cards != stat.yellow_cards
                or row.red_cards != stat.red_cards
                or row.bonus != stat.bonus
            )
            if changed:
                row.minutes = stat.minutes
                row.total_points = stat.total_points
                row.goals_scored = stat.goals_scored
                row.assists = stat.assists
                row.yellow_cards = stat.yellow_cards
                row.red_cards = stat.red_cards
                row.bonus = stat.bonus
                row.source_raw_id = record.row.id
                written += 1

        await self.session.flush()
        status = (
            SyncStatus.PARTIAL
            if parsed.unresolved_element_ids or unknown_fixtures
            else SyncStatus.SUCCEEDED
        )
        return SyncOutcome(
            job_type=SyncJobType.LIVE,
            status=status,
            records_written=written,
            payload_changed=record.payload_changed,
            gameweek_number=gameweek_number,
            detail={
                "stat_rows": len(parsed.stats),
                "unresolved_elements": len(parsed.unresolved_element_ids),
                "unknown_fixtures": sorted(unknown_fixtures),
            },
        )

    async def _sync_picks(
        self,
        gameweek_number: int,
        *,
        manager_limit: int | None,
    ) -> SyncOutcome:
        gameweek = (await self._gameweeks()).get(gameweek_number)
        if gameweek is None:
            return SyncOutcome(
                job_type=SyncJobType.PICKS,
                status=SyncStatus.SKIPPED,
                gameweek_number=gameweek_number,
                detail={"reason": "gameweek_not_in_season"},
            )
        if gameweek.deadline_time is None:
            return SyncOutcome(
                job_type=SyncJobType.PICKS,
                status=SyncStatus.SKIPPED,
                gameweek_number=gameweek_number,
                detail={"reason": "deadline_unknown"},
            )
        if naive_utc(self.clock()) < gameweek.deadline_time:
            # Other managers' squads are sealed until the deadline. VMF does not
            # poll for them early.
            return SyncOutcome(
                job_type=SyncJobType.PICKS,
                status=SyncStatus.SKIPPED,
                gameweek_number=gameweek_number,
                detail={"reason": "sealed_until_deadline"},
            )

        managers = await self._managers_for_picks(gameweek_number, manager_limit)
        if not managers:
            return SyncOutcome(
                job_type=SyncJobType.PICKS,
                status=SyncStatus.SKIPPED,
                gameweek_number=gameweek_number,
                detail={"reason": "no_managers_selected"},
            )

        observed_at = self.clock()
        results = await self._gather(
            managers,
            lambda manager: self.client.picks(manager.fpl_entry_id, gameweek_number),
        )

        written = 0
        payload_changed = False
        not_ready: list[int] = []
        quarantined: list[int] = []
        for manager, payload, error in results:
            if error is not None:
                not_ready.append(manager.fpl_entry_id)
                continue
            record = await self._record_raw(
                endpoint_name="entry_picks",
                request_key=f"entry/{manager.fpl_entry_id}/event/{gameweek_number}/picks/",
                payload=payload,
                observed_at=observed_at,
                gameweek_number=gameweek_number,
                fpl_entry_id=manager.fpl_entry_id,
            )
            try:
                parsed = parse_picks(payload)
            except SchemaQuarantineError:
                quarantined.append(manager.fpl_entry_id)
                continue
            created = await self._store_pick_snapshot(
                manager=manager,
                gameweek_number=gameweek_number,
                parsed=parsed,
                payload=payload,
                raw_id=record.row.id,
                captured_at=observed_at,
            )
            if created:
                written += 1
                payload_changed = True

        await self.session.flush()
        status = SyncStatus.SUCCEEDED
        if quarantined:
            status = SyncStatus.QUARANTINED
        elif not_ready:
            status = SyncStatus.PARTIAL
        return SyncOutcome(
            job_type=SyncJobType.PICKS,
            status=status,
            records_written=written,
            payload_changed=payload_changed,
            gameweek_number=gameweek_number,
            detail={
                "requested": len(managers),
                "snapshots_created": written,
                "sealed_or_not_ready": not_ready,
                "quarantined": quarantined,
            },
        )

    async def _sync_entry_history(self, *, manager_limit: int | None) -> SyncOutcome:
        managers = await self._managers_for_history(manager_limit)
        if not managers:
            return SyncOutcome(
                job_type=SyncJobType.ENTRY_HISTORY,
                status=SyncStatus.SKIPPED,
                detail={"reason": "no_managers_selected"},
            )

        observed_at = self.clock()
        results = await self._gather(
            managers,
            lambda manager: self.client.entry_history(manager.fpl_entry_id),
        )

        written = 0
        payload_changed = False
        unavailable: list[int] = []
        quarantined: list[int] = []
        for manager, payload, error in results:
            if error is not None:
                unavailable.append(manager.fpl_entry_id)
                continue
            record = await self._record_raw(
                endpoint_name="entry_history",
                request_key=f"entry/{manager.fpl_entry_id}/history/",
                payload=payload,
                observed_at=observed_at,
                fpl_entry_id=manager.fpl_entry_id,
            )
            try:
                rows = parse_entry_history(payload)
            except SchemaQuarantineError:
                quarantined.append(manager.fpl_entry_id)
                continue
            payload_changed = payload_changed or record.payload_changed
            written += await self._store_history(manager, rows, record.row.id)

        await self.session.flush()
        status = SyncStatus.SUCCEEDED
        if quarantined:
            status = SyncStatus.QUARANTINED
        elif unavailable:
            status = SyncStatus.PARTIAL
        return SyncOutcome(
            job_type=SyncJobType.ENTRY_HISTORY,
            status=status,
            records_written=written,
            payload_changed=payload_changed,
            detail={
                "requested": len(managers),
                "rows_written": written,
                "unavailable": unavailable,
                "quarantined": quarantined,
            },
        )

    async def _store_pick_snapshot(
        self,
        *,
        manager: Manager,
        gameweek_number: int,
        parsed: ParsedPicks,
        payload: object,
        raw_id: int,
        captured_at: datetime,
    ) -> bool:
        payload_hash, _ = payload_digest(payload)
        duplicate = await self.session.scalar(
            select(ManagerPickSnapshot.id).where(
                ManagerPickSnapshot.manager_id == manager.id,
                ManagerPickSnapshot.gameweek_number == gameweek_number,
                ManagerPickSnapshot.payload_hash == payload_hash,
            )
        )
        if duplicate is not None:
            return False

        highest = await self.session.scalar(
            select(ManagerPickSnapshot.revision)
            .where(
                ManagerPickSnapshot.manager_id == manager.id,
                ManagerPickSnapshot.gameweek_number == gameweek_number,
            )
            .order_by(ManagerPickSnapshot.revision.desc())
            .limit(1)
        )
        snapshot = ManagerPickSnapshot(
            manager_id=manager.id,
            gameweek_number=gameweek_number,
            revision=(highest or 0) + 1,
            payload_hash=payload_hash,
            active_chip=parsed.active_chip,
            event_transfers=parsed.event_transfers,
            transfer_cost=parsed.transfer_cost,
            gross_points=parsed.gross_points,
            points_on_bench=parsed.points_on_bench,
            captured_at=naive_utc(captured_at),
            source_raw_id=raw_id,
        )
        snapshot.items = [
            ManagerPickItem(
                element_id=item.element_id,
                squad_position=item.squad_position,
                multiplier=item.multiplier,
                is_captain=item.is_captain,
                is_vice_captain=item.is_vice_captain,
                auto_subbed_in=item.auto_subbed_in,
                auto_subbed_out=item.auto_subbed_out,
            )
            for item in parsed.items
        ]
        self.session.add(snapshot)
        return True

    async def _store_history(
        self,
        manager: Manager,
        rows: Sequence[Any],
        raw_id: int,
    ) -> int:
        existing = {
            row.gameweek_number: row
            for row in await self.session.scalars(
                select(ManagerGameweekHistory).where(
                    ManagerGameweekHistory.manager_id == manager.id
                )
            )
        }
        written = 0
        for parsed in rows:
            row = existing.get(parsed.gameweek_number)
            if row is None:
                self.session.add(
                    ManagerGameweekHistory(
                        manager_id=manager.id,
                        gameweek_number=parsed.gameweek_number,
                        gross_points=parsed.gross_points,
                        total_points=parsed.total_points,
                        event_transfers=parsed.event_transfers,
                        transfer_cost=parsed.transfer_cost,
                        points_on_bench=parsed.points_on_bench,
                        squad_value=parsed.squad_value,
                        bank=parsed.bank,
                        source_raw_id=raw_id,
                    )
                )
                written += 1
                continue
            changed = (
                row.gross_points != parsed.gross_points
                or row.total_points != parsed.total_points
                or row.event_transfers != parsed.event_transfers
                or row.transfer_cost != parsed.transfer_cost
                or row.points_on_bench != parsed.points_on_bench
                or row.squad_value != parsed.squad_value
                or row.bank != parsed.bank
            )
            if changed:
                row.gross_points = parsed.gross_points
                row.total_points = parsed.total_points
                row.event_transfers = parsed.event_transfers
                row.transfer_cost = parsed.transfer_cost
                row.points_on_bench = parsed.points_on_bench
                row.squad_value = parsed.squad_value
                row.bank = parsed.bank
                row.source_raw_id = raw_id
                written += 1
        return written

    async def _managers_for_picks(
        self,
        gameweek_number: int,
        manager_limit: int | None,
    ) -> list[Manager]:
        managers = await self._active_managers()
        captured = {
            manager_id: revision
            for manager_id, revision in await self.session.execute(
                select(
                    ManagerPickSnapshot.manager_id,
                    ManagerPickSnapshot.revision,
                ).where(ManagerPickSnapshot.gameweek_number == gameweek_number)
            )
        }
        # Managers without a snapshot come first: a missing squad blocks scoring,
        # while a stale one only delays auto-sub reconciliation.
        ordered = sorted(managers, key=lambda manager: (captured.get(manager.id, 0), manager.id))
        return ordered if manager_limit is None else ordered[:manager_limit]

    async def _managers_for_history(self, manager_limit: int | None) -> list[Manager]:
        managers = await self._active_managers()
        if manager_limit is None:
            return managers
        counts = {
            manager_id: total
            for manager_id, total in await self.session.execute(
                select(
                    ManagerGameweekHistory.manager_id,
                    func.count(ManagerGameweekHistory.id),
                ).group_by(ManagerGameweekHistory.manager_id)
            )
        }
        # The manager with the least recorded history is the one most likely to
        # be missing the Gameweek a calculation is waiting for.
        ordered = sorted(managers, key=lambda manager: (counts.get(manager.id, 0), manager.id))
        return ordered[:manager_limit]

    async def _active_managers(self) -> list[Manager]:
        statement = (
            select(Manager)
            .where(
                Manager.registration_status == RegistrationStatus.CONFIRMED,
                Manager.active_status.in_(
                    (
                        ManagerStatus.ACTIVE,
                        ManagerStatus.SUSPENDED,
                        ManagerStatus.PENDING_REVIEW,
                    )
                ),
            )
            .order_by(Manager.id)
        )
        return list(await self.session.scalars(statement))

    async def _gather(
        self,
        managers: Sequence[Manager],
        request: Callable[[Manager], Awaitable[Any]],
    ) -> list[tuple[Manager, Any, FPLClientError | None]]:
        async def run(manager: Manager) -> tuple[Manager, Any, FPLClientError | None]:
            async with self._semaphore:
                try:
                    return manager, await request(manager), None
                except FPLClientError as error:
                    # A missing or failing manager endpoint is an availability
                    # incident, never a zero score.
                    return manager, None, error

        return list(await asyncio.gather(*(run(manager) for manager in managers)))

    async def _record_raw(
        self,
        *,
        endpoint_name: str,
        request_key: str,
        payload: object,
        observed_at: datetime,
        gameweek_number: int | None = None,
        fpl_entry_id: int | None = None,
    ) -> Any:
        return await record_raw_response(
            self.session,
            endpoint_name=endpoint_name,
            request_key=request_key,
            payload=payload,
            observed_at=observed_at,
            season_code=self.season_code,
            gameweek_number=gameweek_number,
            fpl_entry_id=fpl_entry_id,
            correlation_id=self.correlation_id,
            persist_payload=endpoint_name in PERSISTED_PAYLOAD_ENDPOINTS,
        )

    async def _by_key(self, model: type[Any], key_column: Any) -> dict[int, Any]:
        rows = await self.session.scalars(select(model).where(model.season_id == self.season_id))
        return {getattr(row, key_column.key): row for row in rows}

    async def _gameweeks(self) -> dict[int, Gameweek]:
        rows = await self.session.scalars(
            select(Gameweek).where(Gameweek.season_id == self.season_id)
        )
        return {row.number: row for row in rows}

    def _new_fixture(self, fixture: ParsedFixture) -> FplFixture:
        row = FplFixture(season_id=self.season_id, fixture_fpl_id=fixture.fixture_fpl_id)
        self._apply_fixture(row, fixture)
        return row

    def _apply_fixture(self, row: FplFixture, fixture: ParsedFixture) -> bool:
        kickoff = None if fixture.kickoff_time is None else naive_utc(fixture.kickoff_time)
        values = {
            "gameweek_number": fixture.gameweek_number,
            "kickoff_time": kickoff,
            "started": fixture.started,
            "finished": fixture.finished,
            "finished_provisional": fixture.finished_provisional,
            "minutes": fixture.minutes,
            "team_h_fpl_id": fixture.team_h_fpl_id,
            "team_a_fpl_id": fixture.team_a_fpl_id,
            "team_h_score": fixture.team_h_score,
            "team_a_score": fixture.team_a_score,
        }
        changed = False
        for attribute, value in values.items():
            if getattr(row, attribute, None) != value:
                setattr(row, attribute, value)
                changed = True
        return changed

    async def _run(
        self,
        job_type: SyncJobType,
        gameweek_number: int | None,
        job: Callable[[], Awaitable[SyncOutcome]],
    ) -> SyncOutcome:
        started_at = self.clock()
        # Each job owns a savepoint so a failing source discards only its own
        # partial writes; work already done in this tick survives.
        savepoint = await self.session.begin_nested()
        try:
            outcome = await job()
        except SchemaQuarantineError as error:
            await savepoint.rollback()
            outcome = SyncOutcome(
                job_type=job_type,
                status=SyncStatus.QUARANTINED,
                gameweek_number=gameweek_number,
                error=str(error),
            )
        except FPLClientError as error:
            await savepoint.rollback()
            outcome = SyncOutcome(
                job_type=job_type,
                status=SyncStatus.FAILED,
                gameweek_number=gameweek_number,
                error=f"{error} ({error.path})",
            )
        else:
            await savepoint.commit()
        await self._record_run(outcome, started_at)
        return outcome

    async def _record_run(self, outcome: SyncOutcome, started_at: datetime) -> None:
        self.session.add(
            SyncRun(
                job_type=outcome.job_type,
                status=outcome.status,
                season_id=self.season_id,
                gameweek_number=outcome.gameweek_number,
                started_at=naive_utc(started_at),
                finished_at=naive_utc(self.clock()),
                records_written=outcome.records_written,
                payload_changed=outcome.payload_changed,
                detail=outcome.detail or None,
                error=outcome.error,
                correlation_id=self.correlation_id,
            )
        )
        await self.session.flush()
