"""One Gameweek from FPL payloads to a written score.

The unit tests cover each stage on its own. This one covers the wiring: a
cron tick calls the orchestrator, which drives the parsers, the ingestion
service and the scoring service in order, and a score lands in the table the
standings read from.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
from vmf_api.core.config import Settings
from vmf_api.db.base import Base
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus, ScoreState
from vmf_api.models.ingestion import FplPlayerFixtureStat
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.services.sync_orchestrator import run_scheduled_sync

BEFORE_DEADLINE = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
AFTER_GAMEWEEK = datetime(2026, 8, 24, 22, 0, tzinfo=UTC)

#: Two fixtures, and a third that gives team 3 a second match in the same
#: Gameweek so the Double Gameweek path is exercised.
FIXTURE_IDS = (101, 102, 103)

#: element_id -> (element_type, [(fixture_id, minutes, goals, assists, bonus)])
PERFORMANCES: dict[int, tuple[int, list[tuple[int, int, int, int, int]]]] = {
    1: (1, [(101, 90, 0, 0, 0)]),  # keeper, clean sheet not modelled
    2: (2, [(101, 90, 0, 0, 0)]),
    3: (3, [(101, 90, 2, 1, 3)]),  # the captain's haul
    4: (4, [(102, 0, 0, 0, 0)]),  # blanks, so FPL substitutes him out
    5: (3, [(102, 90, 0, 1, 0)]),  # comes on as the automatic substitute
    6: (3, [(103, 90, 1, 0, 1), (102, 90, 1, 1, 2)]),  # plays twice
}

GOAL_POINTS = {1: 10, 2: 6, 3: 5, 4: 4}


def _element_points(element_id: int) -> int:
    element_type, appearances = PERFORMANCES[element_id]
    total = 0
    for _fixture, minutes, goals, assists, bonus in appearances:
        total += 2 if minutes >= 60 else (1 if minutes else 0)
        total += goals * GOAL_POINTS[element_type]
        total += assists * 3
        total += bonus
    return total


def _bootstrap() -> dict[str, Any]:
    return {
        "events": [
            {
                "id": number,
                "name": f"Gameweek {number}",
                "deadline_time": "2026-08-21T17:30:00Z" if number == 1 else None,
                "finished": number == 1,
                "data_checked": False,
                "is_current": number == 1,
                "is_next": number == 2,
                "is_previous": False,
            }
            for number in (1, 2)
        ],
        "teams": [
            {"id": index, "name": f"Team {index}", "short_name": f"T{index}"} for index in (1, 2, 3)
        ],
        "elements": [
            {
                "id": element_id,
                "web_name": f"Player {element_id}",
                "first_name": "Sim",
                "second_name": f"Player {element_id}",
                "team": 1,
                "element_type": element_type,
                "status": "a",
                "now_cost": 50,
            }
            for element_id, (element_type, _) in PERFORMANCES.items()
        ],
    }


def _fixtures() -> list[dict[str, Any]]:
    return [
        {
            "id": fixture_id,
            "event": 1,
            "kickoff_time": "2026-08-22T14:00:00Z",
            "started": True,
            "finished": True,
            "finished_provisional": True,
            "minutes": 90,
            "team_h": 1,
            "team_a": 2,
            "team_h_score": 1,
            "team_a_score": 1,
        }
        for fixture_id in FIXTURE_IDS
    ]


def _live() -> dict[str, Any]:
    elements = []
    for element_id, (element_type, appearances) in PERFORMANCES.items():
        explain = []
        total = 0
        minutes_played = 0
        for fixture_id, minutes, goals, assists, bonus in appearances:
            stats = [
                {
                    "identifier": "minutes",
                    "value": minutes,
                    "points": 2 if minutes >= 60 else (1 if minutes else 0),
                },
                {
                    "identifier": "goals_scored",
                    "value": goals,
                    "points": goals * GOAL_POINTS[element_type],
                },
                {"identifier": "assists", "value": assists, "points": assists * 3},
                {"identifier": "bonus", "value": bonus, "points": bonus},
            ]
            explain.append({"fixture": fixture_id, "stats": stats})
            total += sum(stat["points"] for stat in stats)
            minutes_played += minutes
        elements.append(
            {
                "id": element_id,
                "stats": {"total_points": total, "minutes": minutes_played},
                "explain": explain,
            }
        )
    return {"elements": elements}


def _picks(entry_id: int) -> dict[str, Any]:
    # Both entries field the same six players; only the armband and the
    # transfer cost differ, so the comparison isolates those two rules.
    captain = 3 if entry_id == 2001 else 6
    picks = [
        {
            "element": 1,
            "position": 1,
            "multiplier": 1,
            "is_captain": False,
            "is_vice_captain": False,
        },
        {
            "element": 2,
            "position": 2,
            "multiplier": 1,
            "is_captain": False,
            "is_vice_captain": False,
        },
        {
            "element": 3,
            "position": 3,
            "multiplier": 2 if captain == 3 else 1,
            "is_captain": captain == 3,
            "is_vice_captain": False,
        },
        {
            "element": 4,
            "position": 4,
            "multiplier": 0,
            "is_captain": False,
            "is_vice_captain": True,
        },
        {
            "element": 6,
            "position": 5,
            "multiplier": 2 if captain == 6 else 1,
            "is_captain": captain == 6,
            "is_vice_captain": False,
        },
        {
            "element": 5,
            "position": 12,
            "multiplier": 1,
            "is_captain": False,
            "is_vice_captain": False,
        },
    ]
    gross = sum(pick["multiplier"] * _element_points(pick["element"]) for pick in picks)
    bench = sum(_element_points(pick["element"]) for pick in picks if pick["multiplier"] == 0)
    return {
        "active_chip": None,
        "entry_history": {
            "event": 1,
            "points": gross,
            "points_on_bench": bench,
            "event_transfers": 0 if entry_id == 2001 else 2,
            "event_transfers_cost": 0 if entry_id == 2001 else 4,
        },
        "picks": picks,
        "automatic_subs": [{"element_in": 5, "element_out": 4}],
    }


def _history(entry_id: int) -> dict[str, Any]:
    entry_history = _picks(entry_id)["entry_history"]
    return {
        "current": [
            {
                "event": 1,
                "points": entry_history["points"],
                "total_points": entry_history["points"] - entry_history["event_transfers_cost"],
                "event_transfers": entry_history["event_transfers"],
                "event_transfers_cost": entry_history["event_transfers_cost"],
                "points_on_bench": entry_history["points_on_bench"],
                "value": 1000,
                "bank": 5,
            }
        ]
    }


class SimulatedFPL:
    """Serves a synthetic Gameweek over the real client interface."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def bootstrap(self) -> dict[str, Any]:
        self.calls.append("bootstrap")
        return _bootstrap()

    async def fixtures(self) -> list[dict[str, Any]]:
        self.calls.append("fixtures")
        return _fixtures()

    async def live(self, gameweek: int) -> dict[str, Any]:
        self.calls.append(f"live/{gameweek}")
        return _live()

    async def picks(self, entry_id: int, gameweek: int) -> dict[str, Any]:
        self.calls.append(f"picks/{entry_id}")
        return _picks(entry_id)

    async def entry_history(self, entry_id: int) -> dict[str, Any]:
        self.calls.append(f"history/{entry_id}")
        return _history(entry_id)

    async def entry(self, entry_id: int) -> dict[str, Any]:
        return {"id": entry_id, "name": f"Team {entry_id}"}

    async def element_summary(self, element_id: int) -> dict[str, Any]:
        return {}

    async def transfers(self, entry_id: int) -> list[dict[str, Any]]:
        return []

    async def close(self) -> None:
        return None


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed(session: AsyncSession) -> None:
    season = Season(
        name="VMF Fantasy League 2026/27",
        fpl_season_code="2026/27",
        start_gameweek=1,
        end_gameweek=38,
    )
    session.add(season)
    await session.flush()
    session.add_all([Gameweek(season_id=season.id, number=number) for number in (1, 2)])
    for index, entry_id in enumerate((2001, 2002), start=1):
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


def _settings() -> Settings:
    return Settings(active_season_code="2026/27", sync_manager_batch_size=10)


@pytest.mark.anyio
async def test_a_tick_before_the_deadline_ingests_metadata_and_scores_nothing() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)
            client = SimulatedFPL()

            result = await run_scheduled_sync(
                session,
                client,
                _settings(),
                clock=lambda: BEFORE_DEADLINE,
            )

            assert result.plan is not None
            assert result.plan.reason == "before_first_deadline"
            assert result.plan.gameweek_number is None
            assert result.scoring is None
            assert [outcome.job_type.value for outcome in result.outcomes] == [
                "bootstrap",
                "fixtures",
            ]
            # No squad was requested, so no manager-scoped call was made.
            assert not any(call.startswith("picks/") for call in client.calls)
            assert await session.scalar(select(ManagerGameweekScore)) is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_finished_gameweek_is_ingested_parsed_and_scored_in_one_tick() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)
            client = SimulatedFPL()

            result = await run_scheduled_sync(
                session,
                client,
                _settings(),
                clock=lambda: AFTER_GAMEWEEK,
            )

            assert result.plan is not None
            assert result.plan.gameweek_number == 1
            assert all(outcome.status.value == "succeeded" for outcome in result.outcomes)

            scoring = result.scoring
            assert scoring is not None
            assert scoring.state is ScoreState.PROVISIONAL
            assert scoring.managers_scored == 2
            # The derived total agreeing with the published one is the strongest
            # available check that the parse and the arithmetic are both right.
            assert scoring.unreconciled_manager_ids == ()

            rows = {
                manager.fpl_entry_id: score
                for manager, score in await session.execute(
                    select(Manager, ManagerGameweekScore).join(
                        ManagerGameweekScore,
                        ManagerGameweekScore.manager_id == Manager.id,
                    )
                )
            }
            assert set(rows) == {2001, 2002}

            # Player 3: 2 minutes points + 2 goals x 5 + 1 assist x 3 + 3 bonus.
            assert _element_points(3) == 18
            # Player 6 plays twice: (2 + 5 + 1) + (2 + 5 + 3 + 2).
            assert _element_points(6) == 20

            # Both squads field the same players: 2 + 2 + 18 + 20 + 5 counted
            # once, plus whichever of the two hauls carries the armband twice.
            captain_of_three = rows[2001]
            assert captain_of_three.captain_points == 36
            assert captain_of_three.gross_points == 65
            assert captain_of_three.transfer_cost == 0
            assert captain_of_three.net_points == 65

            captain_of_six = rows[2002]
            assert captain_of_six.captain_points == 40
            assert captain_of_six.gross_points == 67
            assert captain_of_six.transfer_cost == 4
            assert captain_of_six.net_points == 63

            # The better armband is worth 2, so a hit of 4 more than cancels it.
            assert captain_of_six.gross_points > captain_of_three.gross_points
            assert captain_of_six.net_points < captain_of_three.net_points

            # The substituted player contributes nothing, and scores nothing to
            # leave on the bench either.
            assert _element_points(4) == 0
            assert captain_of_three.bench_points == 0

            # Four goals are counted: two from player 3 and two from player 6.
            assert captain_of_three.goals_counted == 4

            # TotW compares net points, so the transfer hit decides it.
            assert scoring.totw_manager_ids == (captain_of_three.manager_id,)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_the_double_gameweek_is_stored_as_two_fixture_rows() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)

            await run_scheduled_sync(
                session,
                SimulatedFPL(),
                _settings(),
                clock=lambda: AFTER_GAMEWEEK,
            )

            rows = list(
                await session.scalars(
                    select(FplPlayerFixtureStat)
                    .where(FplPlayerFixtureStat.element_id == 6)
                    .order_by(FplPlayerFixtureStat.fixture_fpl_id)
                )
            )

            # Two rows, not one overwritten row: this is what keeps a Double
            # Gameweek additive and lets a rescheduled fixture be detached.
            assert [row.fixture_fpl_id for row in rows] == [102, 103]
            assert [row.total_points for row in rows] == [12, 8]
            assert sum(row.goals_scored for row in rows) == 2
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_a_repeated_tick_neither_duplicates_rows_nor_changes_the_score() -> None:
    sessionmaker, engine = await _database()
    try:
        async with sessionmaker() as session:
            await _seed(session)
            client = SimulatedFPL()

            first = await run_scheduled_sync(
                session, client, _settings(), clock=lambda: AFTER_GAMEWEEK
            )
            before = {
                score.manager_id: score.net_points
                for score in await session.scalars(select(ManagerGameweekScore))
            }

            second = await run_scheduled_sync(
                session, client, _settings(), clock=lambda: AFTER_GAMEWEEK
            )
            after = {
                score.manager_id: score.net_points
                for score in await session.scalars(select(ManagerGameweekScore))
            }

            assert before == after
            assert len(after) == 2
            assert first.scoring is not None and second.scoring is not None
            assert first.scoring.managers_scored == second.scoring.managers_scored
            # The payloads did not change, so no job wrote a second time.
            assert all(not outcome.payload_changed for outcome in second.outcomes)
    finally:
        await engine.dispose()
