from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import vmf_api.models  # noqa: F401  (registers every table on the metadata)
from vmf_api.core.errors import ConflictError, NotFoundError
from vmf_api.db.base import Base
from vmf_api.domain.violations import (
    ReviewAction,
    ThresholdAction,
    ViolationStatus,
    due_threshold_actions,
)
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus, ViolationType
from vmf_api.models.governance import AdminDecision, Violation, ViolationThresholdAction
from vmf_api.models.h2h import H2HPenalty
from vmf_api.models.ingestion import ManagerGameweekHistory
from vmf_api.models.manager import Manager
from vmf_api.schemas.admin import ViolationReviewRequest
from vmf_api.services.admin import AdminService
from vmf_api.services.violations import (
    apply_threshold_actions,
    confirmed_violation_count,
    detect_transfer_violations,
    gameweeks_with_confirmed_violations,
)

SEASON_CODE = "2026/27"


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed(session: AsyncSession, *, manager_count: int = 1) -> list[Manager]:
    season = Season(
        name="VMF Fantasy League 2026/27",
        fpl_season_code=SEASON_CODE,
        start_gameweek=1,
        end_gameweek=38,
    )
    session.add(season)
    await session.flush()
    session.add_all([Gameweek(season_id=season.id, number=number) for number in range(1, 39)])

    managers = []
    for index in range(1, manager_count + 1):
        manager = Manager(
            fpl_entry_id=1000 + index,
            manager_name=f"Manager {index}",
            team_name=f"Team {index}",
            division=Division.HIGH,
            active_status=ManagerStatus.ACTIVE,
            registration_status=RegistrationStatus.CONFIRMED,
            season_joined=SEASON_CODE,
        )
        session.add(manager)
        managers.append(manager)
    await session.flush()
    return managers


def _history(manager_id: int, gameweek: int, cost: int) -> ManagerGameweekHistory:
    return ManagerGameweekHistory(
        manager_id=manager_id,
        gameweek_number=gameweek,
        gross_points=50,
        transfer_cost=cost,
    )


# --------------------------------------------------------------------------
# Domain
# --------------------------------------------------------------------------


def test_no_action_is_due_below_the_first_threshold() -> None:
    assert due_threshold_actions(0) == set()


def test_the_first_threshold_forfeits_the_deposit_and_deducts_from_h2h() -> None:
    assert due_threshold_actions(1) == {
        ThresholdAction.DEPOSIT_FORFEITED,
        ThresholdAction.H2H_TABLE_DEDUCTION,
    }


def test_one_gameweek_can_make_two_thresholds_due_at_once() -> None:
    # A transfer cost of 20 raises two units, so the manager is past both.
    assert due_threshold_actions(2) == {
        ThresholdAction.DEPOSIT_FORFEITED,
        ThresholdAction.H2H_TABLE_DEDUCTION,
        ThresholdAction.PRIZE_CAPPED,
        ThresholdAction.REMOVED_FROM_H2H,
        ThresholdAction.REMOVED_FROM_CUP,
    }


def test_the_third_threshold_removes_the_manager() -> None:
    assert ThresholdAction.REMOVED_FROM_COMPETITION in due_threshold_actions(3)


def test_a_negative_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        due_threshold_actions(-1)


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------


@pytest.mark.anyio
async def test_detection_follows_the_published_transfer_cost() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            manager_id = managers[0].id
            session.add_all(
                [
                    _history(manager_id, 1, 8),  # at the limit, not a violation
                    _history(manager_id, 2, 12),  # one unit
                    _history(manager_id, 3, 20),  # two units
                    _history(manager_id, 4, 28),  # three units
                ]
            )
            await session.flush()

            result = await detect_transfer_violations(session)

            assert result.scanned == 4
            assert result.raised == 3
            rows = {row.gameweek_number: row for row in await session.scalars(select(Violation))}
            assert sorted(rows) == [2, 3, 4]
            assert [rows[gw].detected_count for gw in (2, 3, 4)] == [1, 2, 3]
            # Detection never decides anything.
            assert all(row.status is ViolationStatus.DETECTED for row in rows.values())
            assert all(row.confirmed_count == 0 for row in rows.values())
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_detection_is_idempotent_across_ticks() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            session.add(_history(managers[0].id, 2, 12))
            await session.flush()

            first = await detect_transfer_violations(session)
            second = await detect_transfer_violations(session)

            assert first.raised == 1
            assert second.raised == 0
            assert not second.changed
            assert len(list(await session.scalars(select(Violation)))) == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_restated_gameweek_corrects_or_clears_an_untouched_case() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            entry = _history(managers[0].id, 2, 20)
            session.add(entry)
            await session.flush()
            await detect_transfer_violations(session)

            entry.transfer_cost = 12
            await session.flush()
            corrected = await detect_transfer_violations(session)
            assert corrected.updated == 1
            violation = await session.scalar(select(Violation))
            assert violation is not None
            assert violation.detected_count == 1

            entry.transfer_cost = 4
            await session.flush()
            cleared = await detect_transfer_violations(session)
            assert cleared.cleared == 1
            assert await session.scalar(select(Violation)) is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_reviewed_case_is_never_rewritten_by_a_later_tick() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            entry = _history(managers[0].id, 2, 20)
            session.add(entry)
            await session.flush()
            await detect_transfer_violations(session)

            violation = await session.scalar(select(Violation))
            assert violation is not None
            violation.status = ViolationStatus.CONFIRMED
            violation.confirmed_count = 2
            await session.flush()

            # FPL restates the Gameweek after the decision was taken.
            entry.transfer_cost = 0
            await session.flush()
            result = await detect_transfer_violations(session)

            # Reversing a decision is an administrative act, not a side effect.
            assert not result.changed
            await session.refresh(violation)
            assert violation.confirmed_count == 2
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# Threshold actions
# --------------------------------------------------------------------------


@pytest.mark.anyio
async def test_the_first_threshold_writes_exactly_one_h2h_deduction() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            manager_id = managers[0].id
            session.add(
                Violation(
                    manager_id=manager_id,
                    gameweek_number=2,
                    violation_type=ViolationType.TRANSFER_HIT,
                    detected_count=1,
                    confirmed_count=1,
                    status=ViolationStatus.CONFIRMED,
                )
            )
            await session.flush()

            applied = await apply_threshold_actions(session, manager_id)

            assert applied.cumulative_count == 1
            assert applied.h2h_points_deducted == -6
            penalties = list(await session.scalars(select(H2HPenalty)))
            assert len(penalties) == 1
            assert penalties[0].table_point_delta == -6

            # Re-running must not add a second deduction.
            repeat = await apply_threshold_actions(session, manager_id)
            assert repeat.applied == ()
            assert repeat.h2h_points_deducted == 0
            assert len(list(await session.scalars(select(H2HPenalty)))) == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_two_units_in_one_gameweek_apply_both_thresholds_but_one_deduction() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            manager_id = managers[0].id
            session.add(
                Violation(
                    manager_id=manager_id,
                    gameweek_number=3,
                    violation_type=ViolationType.TRANSFER_HIT,
                    detected_count=2,
                    confirmed_count=2,
                    status=ViolationStatus.CONFIRMED,
                )
            )
            await session.flush()

            applied = await apply_threshold_actions(session, manager_id)

            assert applied.cumulative_count == 2
            assert set(applied.applied) == {
                ThresholdAction.DEPOSIT_FORFEITED,
                ThresholdAction.H2H_TABLE_DEDUCTION,
                ThresholdAction.PRIZE_CAPPED,
                ThresholdAction.REMOVED_FROM_H2H,
                ThresholdAction.REMOVED_FROM_CUP,
            }
            # Both thresholds are crossed, but the -6 is still a single entry.
            assert len(list(await session.scalars(select(H2HPenalty)))) == 1
            assert not applied.removed_from_competition
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_later_violation_adds_only_the_newly_due_actions() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            manager_id = managers[0].id
            first = Violation(
                manager_id=manager_id,
                gameweek_number=2,
                violation_type=ViolationType.TRANSFER_HIT,
                detected_count=1,
                confirmed_count=1,
                status=ViolationStatus.CONFIRMED,
            )
            session.add(first)
            await session.flush()
            await apply_threshold_actions(session, manager_id)

            session.add(
                Violation(
                    manager_id=manager_id,
                    gameweek_number=5,
                    violation_type=ViolationType.TRANSFER_HIT,
                    detected_count=1,
                    confirmed_count=1,
                    status=ViolationStatus.CONFIRMED,
                )
            )
            await session.flush()

            second = await apply_threshold_actions(session, manager_id)

            assert second.cumulative_count == 2
            assert set(second.applied) == {
                ThresholdAction.PRIZE_CAPPED,
                ThresholdAction.REMOVED_FROM_H2H,
                ThresholdAction.REMOVED_FROM_CUP,
            }
            assert second.h2h_points_deducted == 0
            assert len(list(await session.scalars(select(H2HPenalty)))) == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_the_third_threshold_removes_the_manager_from_the_competition() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            manager_id = managers[0].id
            session.add(
                Violation(
                    manager_id=manager_id,
                    gameweek_number=3,
                    violation_type=ViolationType.TRANSFER_HIT,
                    detected_count=3,
                    confirmed_count=3,
                    status=ViolationStatus.CONFIRMED,
                )
            )
            await session.flush()

            applied = await apply_threshold_actions(session, manager_id)

            assert applied.removed_from_competition
            manager = await session.get(Manager, manager_id)
            assert manager is not None
            assert manager.active_status is ManagerStatus.REMOVED
            assert len(list(await session.scalars(select(ViolationThresholdAction)))) == 6
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_approved_exception_confirms_nothing_and_applies_nothing() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            manager_id = managers[0].id
            violation = Violation(
                manager_id=manager_id,
                gameweek_number=2,
                violation_type=ViolationType.TRANSFER_HIT,
                detected_count=1,
                status=ViolationStatus.PENDING_REVIEW,
            )
            session.add(violation)
            await session.flush()

            _row, _decision, applied = await AdminService(session).review_violation(
                violation.id,
                ViolationReviewRequest(
                    action=ReviewAction.APPROVE_EXCEPTION,
                    note="Forgot to activate the chip; evidence accepted.",
                ),
                actor="admin",
            )

            assert await confirmed_violation_count(session, manager_id) == 0
            assert applied.applied == ()
            assert await session.scalar(select(H2HPenalty)) is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_confirming_through_the_service_writes_the_penalty_and_the_audit() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session)
            violation = Violation(
                manager_id=managers[0].id,
                gameweek_number=2,
                violation_type=ViolationType.TRANSFER_HIT,
                detected_count=1,
                status=ViolationStatus.DETECTED,
            )
            session.add(violation)
            await session.flush()

            row, decision, applied = await AdminService(session).review_violation(
                violation.id,
                ViolationReviewRequest(
                    action=ReviewAction.CONFIRM,
                    note="Took a 12 point hit in GW2.",
                ),
                actor="admin",
            )

            assert row.status is ViolationStatus.CONFIRMED
            assert row.confirmed_count == 1
            assert decision.actor == "admin"
            assert applied.h2h_points_deducted == -6
            penalty = await session.scalar(select(H2HPenalty))
            assert penalty is not None
            assert penalty.violation_id == violation.id
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_the_cup_zeroes_every_gameweek_carrying_a_confirmed_violation() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            managers = await _seed(session, manager_count=2)
            session.add_all(
                [
                    Violation(
                        manager_id=managers[0].id,
                        gameweek_number=4,
                        violation_type=ViolationType.TRANSFER_HIT,
                        detected_count=1,
                        confirmed_count=1,
                        status=ViolationStatus.CONFIRMED,
                    ),
                    Violation(
                        manager_id=managers[0].id,
                        gameweek_number=25,
                        violation_type=ViolationType.TRANSFER_HIT,
                        detected_count=1,
                        confirmed_count=1,
                        status=ViolationStatus.CONFIRMED,
                    ),
                    # Detected but not yet reviewed, so it changes nothing.
                    Violation(
                        manager_id=managers[1].id,
                        gameweek_number=7,
                        violation_type=ViolationType.TRANSFER_HIT,
                        detected_count=1,
                        confirmed_count=0,
                        status=ViolationStatus.DETECTED,
                    ),
                ]
            )
            await session.flush()

            affected = await gameweeks_with_confirmed_violations(session)

            assert affected == {managers[0].id: {4, 25}}
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# Finalize and reopen
# --------------------------------------------------------------------------


@pytest.mark.anyio
async def test_finalizing_locks_the_gameweek_and_records_who_did_it() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)
            service = AdminService(session)

            gameweek, decision = await service.set_gameweek_finalized(
                SEASON_CODE,
                1,
                finalized=True,
                reason="Bonus points confirmed and standings checked.",
                actor="admin",
            )

            assert gameweek.is_finalized
            assert decision.actor == "admin"
            assert decision.before_state == {"is_finalized": False}
            assert decision.after_state == {"is_finalized": True}
            assert decision.target_id == f"{SEASON_CODE}:1"
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_reopening_is_recorded_as_its_own_decision() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)
            service = AdminService(session)
            await service.set_gameweek_finalized(
                SEASON_CODE, 1, finalized=True, reason="Settled.", actor="admin"
            )

            gameweek, decision = await service.set_gameweek_finalized(
                SEASON_CODE,
                1,
                finalized=False,
                reason="FPL restated the bonus for GW1.",
                actor="admin",
            )

            assert not gameweek.is_finalized
            # The previous decision is preserved rather than replaced.
            decisions = list(await session.scalars(select(AdminDecision)))
            assert len(decisions) == 2
            assert decision.reason == "FPL restated the bonus for GW1."
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_finalizing_twice_is_refused_rather_than_silently_repeated() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)
            service = AdminService(session)
            await service.set_gameweek_finalized(
                SEASON_CODE, 1, finalized=True, reason="Settled.", actor="admin"
            )

            with pytest.raises(ConflictError):
                await service.set_gameweek_finalized(
                    SEASON_CODE, 1, finalized=True, reason="Again.", actor="admin"
                )
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_unknown_gameweek_or_season_is_reported() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)
            service = AdminService(session)

            with pytest.raises(NotFoundError):
                await service.set_gameweek_finalized(
                    "2099/00", 1, finalized=True, reason="x", actor="admin"
                )
            with pytest.raises(NotFoundError):
                await service.set_gameweek_finalized(
                    SEASON_CODE, 39, finalized=True, reason="x", actor="admin"
                )
    finally:
        await engine.dispose()
