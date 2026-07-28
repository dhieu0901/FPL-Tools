from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vmf_api.cli.bootstrap_season import (
    PHASE_DEFINITIONS,
    BootstrapConflictError,
    bootstrap_season,
)
from vmf_api.db.base import Base
from vmf_api.models import CompetitionPhase, Gameweek, Season
from vmf_api.models.enums import PhaseType, SeasonStatus


async def _session_factory() -> tuple[
    async_sessionmaker[AsyncSession],
    AsyncEngine,
]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [
        Season.__table__,
        Gameweek.__table__,
        CompetitionPhase.__table__,
    ]
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=tables,
            )
        )
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def test_bootstrap_creates_canonical_season_gameweeks_and_phases() -> None:
    session_factory, engine = await _session_factory()
    async with session_factory() as session:
        result = await bootstrap_season(
            session,
            season_code="2026/27",
            season_name="VMF Fantasy League 2026/27",
        )
        await session.commit()

        season = await session.scalar(select(Season))
        gameweek_numbers = list(
            await session.scalars(select(Gameweek.number).order_by(Gameweek.number))
        )
        phases = list(
            await session.scalars(select(CompetitionPhase).order_by(CompetitionPhase.phase_type))
        )

    assert result.season_created is True
    assert result.gameweeks_created == 38
    assert result.phases_created == 6
    assert season is not None
    assert season.status is SeasonStatus.DRAFT
    assert (season.start_gameweek, season.end_gameweek) == (1, 38)
    assert gameweek_numbers == list(range(1, 39))
    assert {
        (phase.phase_type, phase.name, phase.start_gameweek, phase.end_gameweek) for phase in phases
    } == {
        (
            definition.phase_type,
            definition.name,
            definition.start_gameweek,
            definition.end_gameweek,
        )
        for definition in PHASE_DEFINITIONS
    }
    await engine.dispose()


async def test_bootstrap_is_idempotent_and_preserves_existing_state() -> None:
    session_factory, engine = await _session_factory()
    async with session_factory() as session:
        await bootstrap_season(
            session,
            season_code="2026/27",
            season_name="VMF Fantasy League 2026/27",
        )
        await session.commit()

        gameweek = await session.scalar(select(Gameweek).where(Gameweek.number == 1))
        assert gameweek is not None
        gameweek.is_finalized = True
        await session.commit()

        result = await bootstrap_season(
            session,
            season_code="2026/27",
            season_name="VMF Fantasy League 2026/27",
        )
        await session.commit()

        gameweek_count = await session.scalar(select(func.count()).select_from(Gameweek))
        phase_count = await session.scalar(select(func.count()).select_from(CompetitionPhase))
        finalized = await session.scalar(select(Gameweek.is_finalized).where(Gameweek.number == 1))

    assert result.season_created is False
    assert result.gameweeks_created == 0
    assert result.phases_created == 0
    assert gameweek_count == 38
    assert phase_count == 6
    assert finalized is True
    await engine.dispose()


async def test_bootstrap_rejects_conflicting_existing_phase_without_overwriting() -> None:
    session_factory, engine = await _session_factory()
    async with session_factory() as session:
        season = Season(
            name="VMF Fantasy League 2026/27",
            fpl_season_code="2026/27",
            start_gameweek=1,
            end_gameweek=38,
            status=SeasonStatus.DRAFT,
        )
        session.add(season)
        await session.flush()
        session.add(
            CompetitionPhase(
                season_id=season.id,
                name="Wrong range",
                phase_type=PhaseType.CLASSIC_SEASON_1,
                start_gameweek=2,
                end_gameweek=19,
            )
        )
        await session.commit()

        try:
            await bootstrap_season(
                session,
                season_code="2026/27",
                season_name="VMF Fantasy League 2026/27",
            )
        except BootstrapConflictError as exc:
            assert "classic_season_1" in str(exc)
        else:
            raise AssertionError("expected a bootstrap conflict")
        await session.rollback()

        phase = await session.scalar(
            select(CompetitionPhase).where(
                CompetitionPhase.phase_type == PhaseType.CLASSIC_SEASON_1
            )
        )

    assert phase is not None
    assert (phase.name, phase.start_gameweek, phase.end_gameweek) == (
        "Wrong range",
        2,
        19,
    )
    await engine.dispose()
