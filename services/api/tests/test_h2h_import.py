"""Adopting the head-to-head draw FPL made for the league.

Before the first deadline VMF runs a round robin of its own, because FPL has
not drawn one yet. The moment the league closes the two disagree, and only
FPL's version decides who a manager actually plays. These pin the reading of
that payload and the replacement it drives.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import vmf_api.models  # noqa: F401  (registers every table on the metadata)
from vmf_api.cli.import_h2h_schedule import import_h2h_schedule
from vmf_api.core.errors import NotFoundError, RuleValidationError
from vmf_api.db.base import Base
from vmf_api.integrations.fpl_parsers import SchemaQuarantineError, parse_h2h_matches
from vmf_api.models.competition import Season
from vmf_api.models.enums import Division, ManagerStatus, MatchStatus, RegistrationStatus
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.manager import Manager

LEAGUE = 880869


def tie(match_id: int, event: int, one: int, two: int, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": match_id,
        "event": event,
        "entry_1_entry": one,
        "entry_2_entry": two,
        "entry_1_points": 0,
        "entry_2_points": 0,
        "is_knockout": False,
        "is_bye": False,
        "league": LEAGUE,
        "winner": None,
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def test_a_page_yields_its_ties_and_says_whether_another_follows() -> None:
    matches, has_next = parse_h2h_matches(
        {"has_next": True, "page": 1, "results": [tie(1, 1, 100, 200), tie(2, 1, 300, 400)]}
    )

    assert has_next is True
    assert [(m.gameweek_number, m.home_entry_id, m.away_entry_id) for m in matches] == [
        (1, 100, 200),
        (1, 300, 400),
    ]


def test_the_running_score_is_never_read() -> None:
    """FPL scores a tie its own way; this league scores it to its rulebook."""

    matches, _ = parse_h2h_matches(
        {
            "has_next": False,
            "results": [tie(1, 1, 100, 200, entry_1_points=88, entry_2_points=12, winner=100)],
        }
    )

    assert not hasattr(matches[0], "home_score")
    assert not hasattr(matches[0], "winner")


def test_a_bye_is_dropped_rather_than_quarantined() -> None:
    """An odd league is a thing FPL may legitimately produce."""

    matches, _ = parse_h2h_matches(
        {
            "has_next": False,
            "results": [
                tie(1, 1, 100, 200),
                tie(2, 1, 300, 0, is_bye=True, entry_2_entry=None),
            ],
        }
    )

    assert len(matches) == 1


def test_a_knockout_seat_nobody_has_reached_yet_is_skipped() -> None:
    matches, _ = parse_h2h_matches(
        {
            "has_next": False,
            "results": [tie(1, 36, 100, 0, entry_2_entry=None, is_knockout=True)],
        }
    )

    assert matches == ()


def test_a_knockout_tie_is_carried_through_as_one() -> None:
    matches, _ = parse_h2h_matches(
        {"has_next": False, "results": [tie(1, 36, 100, 200, is_knockout=True)]}
    )

    assert matches[0].is_knockout is True


def test_an_entry_drawn_against_itself_is_quarantined() -> None:
    with pytest.raises(SchemaQuarantineError, match="itself"):
        parse_h2h_matches({"has_next": False, "results": [tie(1, 1, 100, 100)]})


@pytest.mark.parametrize(
    "payload",
    [
        {"has_next": False},
        {"has_next": False, "results": {}},
        {"has_next": False, "results": [tie(1, 0, 100, 200)]},
    ],
)
def test_a_payload_that_cannot_be_trusted_is_quarantined(payload: dict[str, Any]) -> None:
    with pytest.raises(SchemaQuarantineError):
        parse_h2h_matches(payload)


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------


class FakeFPL:
    """Serves a draw one page at a time, the way FPL does."""

    def __init__(self, pages: list[list[dict[str, Any]]]) -> None:
        self.pages = pages
        self.requested: list[int] = []

    async def h2h_matches(self, league_id: int, *, page: int = 1) -> dict[str, Any]:
        self.requested.append(page)
        index = page - 1
        results = self.pages[index] if index < len(self.pages) else []
        return {"has_next": index < len(self.pages) - 1, "page": page, "results": results}

    async def close(self) -> None:  # pragma: no cover - never called here
        return None


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed(session: AsyncSession, *, entries: list[int]) -> tuple[H2HSchedule, list[Manager]]:
    season = Season(fpl_season_code="2026/27", name="VMF 2026/27")
    session.add(season)
    await session.flush()

    schedule = H2HSchedule(season_id=season.id, name="H2H Group Stage")
    session.add(schedule)
    await session.flush()

    managers = []
    for index, entry in enumerate(entries):
        manager = Manager(
            fpl_entry_id=entry,
            manager_name=f"Manager {index + 1}",
            team_name=f"Team {index + 1}",
            division=Division.HIGH,
            active_status=ManagerStatus.ACTIVE,
            registration_status=RegistrationStatus.CONFIRMED,
            season_joined="2026/27",
        )
        session.add(manager)
        managers.append(manager)
    await session.flush()
    return schedule, managers


@pytest.mark.anyio
async def test_the_generated_draw_is_replaced_by_the_one_fpl_made() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            schedule, managers = await _seed(session, entries=[100, 200, 300, 400])
            # What VMF generated before the league closed: 1v2 and 3v4.
            session.add_all(
                [
                    H2HMatch(
                        schedule_id=schedule.id,
                        gameweek_number=1,
                        home_manager_id=managers[0].id,
                        away_manager_id=managers[1].id,
                        status=MatchStatus.SCHEDULED,
                    ),
                    H2HMatch(
                        schedule_id=schedule.id,
                        gameweek_number=1,
                        home_manager_id=managers[2].id,
                        away_manager_id=managers[3].id,
                        status=MatchStatus.SCHEDULED,
                    ),
                ]
            )
            await session.flush()

            # What FPL actually drew: 1v3 and 2v4.
            client = FakeFPL([[tie(1, 1, 100, 300), tie(2, 1, 200, 400)]])
            result = await import_h2h_schedule(
                session, client, league_id=LEAGUE, schedule_id=schedule.id, dry_run=False
            )

            assert result.written == 2
            assert result.removed == 2
            assert len(result.changed_pairings) == 2

            rows = list(
                await session.scalars(select(H2HMatch).where(H2HMatch.schedule_id == schedule.id))
            )
            pairs = {frozenset((row.home_manager_id, row.away_manager_id)) for row in rows}
            assert pairs == {
                frozenset((managers[0].id, managers[2].id)),
                frozenset((managers[1].id, managers[3].id)),
            }
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_report_writes_nothing() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            schedule, _ = await _seed(session, entries=[100, 200])
            client = FakeFPL([[tie(1, 1, 100, 200)]])

            result = await import_h2h_schedule(
                session, client, league_id=LEAGUE, schedule_id=schedule.id
            )

            assert result.dry_run is True
            assert result.written == 0
            assert (await session.scalars(select(H2HMatch))).all() == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_tie_already_in_the_schedule_is_not_reported_as_a_change() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            schedule, managers = await _seed(session, entries=[100, 200])
            session.add(
                H2HMatch(
                    schedule_id=schedule.id,
                    gameweek_number=1,
                    # The same tie, listed the other way round.
                    home_manager_id=managers[1].id,
                    away_manager_id=managers[0].id,
                    status=MatchStatus.SCHEDULED,
                )
            )
            await session.flush()

            result = await import_h2h_schedule(
                session, FakeFPL([[tie(1, 1, 100, 200)]]), league_id=LEAGUE, schedule_id=schedule.id
            )

            assert result.changed_pairings == ()
            assert result.unchanged == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_entry_that_is_not_on_the_roster_stops_the_import() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            schedule, _ = await _seed(session, entries=[100, 200])

            with pytest.raises(RuleValidationError, match="not on the roster"):
                await import_h2h_schedule(
                    session,
                    FakeFPL([[tie(1, 1, 100, 999)]]),
                    league_id=LEAGUE,
                    schedule_id=schedule.id,
                )
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_league_with_no_draw_yet_is_reported_rather_than_emptying_the_schedule() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            schedule, managers = await _seed(session, entries=[100, 200])
            session.add(
                H2HMatch(
                    schedule_id=schedule.id,
                    gameweek_number=1,
                    home_manager_id=managers[0].id,
                    away_manager_id=managers[1].id,
                    status=MatchStatus.SCHEDULED,
                )
            )
            await session.flush()

            with pytest.raises(RuleValidationError, match="no fixtures yet"):
                await import_h2h_schedule(
                    session, FakeFPL([[]]), league_id=LEAGUE, schedule_id=schedule.id
                )

            assert len((await session.scalars(select(H2HMatch))).all()) == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_settled_results_are_not_discarded_without_being_asked() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            schedule, managers = await _seed(session, entries=[100, 200, 300, 400])
            session.add(
                H2HMatch(
                    schedule_id=schedule.id,
                    gameweek_number=1,
                    home_manager_id=managers[0].id,
                    away_manager_id=managers[1].id,
                    home_score=60,
                    away_score=44,
                    winner_manager_id=managers[0].id,
                    status=MatchStatus.FINAL,
                )
            )
            await session.flush()
            client = FakeFPL([[tie(1, 1, 100, 300)]])

            with pytest.raises(RuleValidationError, match="already final"):
                await import_h2h_schedule(
                    session, client, league_id=LEAGUE, schedule_id=schedule.id, dry_run=False
                )

            # And with the organiser decision behind it, it goes through.
            result = await import_h2h_schedule(
                session,
                client,
                league_id=LEAGUE,
                schedule_id=schedule.id,
                dry_run=False,
                allow_settled=True,
            )
            assert result.written == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_every_page_of_the_draw_is_read() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            schedule, _ = await _seed(session, entries=[100, 200, 300, 400])
            client = FakeFPL([[tie(1, 1, 100, 200)], [tie(2, 2, 300, 400)]])

            result = await import_h2h_schedule(
                session, client, league_id=LEAGUE, schedule_id=schedule.id, dry_run=False
            )

            assert client.requested == [1, 2]
            assert result.fetched == 2
            assert result.gameweeks == (1, 2)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_an_unknown_schedule_is_reported() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed(session, entries=[100, 200])

            with pytest.raises(NotFoundError):
                await import_h2h_schedule(
                    session, FakeFPL([[tie(1, 1, 100, 200)]]), league_id=LEAGUE, schedule_id=999
                )
    finally:
        await engine.dispose()
