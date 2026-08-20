"""Qualification, the draw, and moving winners through the bracket."""

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
from vmf_api.core.errors import ConflictError, NotFoundError, RuleValidationError
from vmf_api.db.base import Base
from vmf_api.domain.cup_bracket import CUP_SEASON_1
from vmf_api.domain.violations import ViolationStatus
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.cup import CupMatch, CupRound
from vmf_api.models.enums import (
    Division,
    ManagerStatus,
    MatchStatus,
    RegistrationStatus,
    ScoreState,
    ViolationType,
)
from vmf_api.models.governance import Violation
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.services.cups import (
    CupBracketService,
    CupQualificationService,
    CupService,
)

HIGH_SIZE = 20
LOW_SIZE = 26


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed_league(
    session: AsyncSession,
    *,
    through_gameweek: int = 13,
    finalize_cutoff: bool = True,
) -> tuple[Season, list[Manager]]:
    """A full 46-manager league with a strict, gap-free points order.

    Manager points descend with the roster index, so HIGH rank 1 is the first
    HIGH manager created and every rank is unambiguous. That makes the seeding
    assertions below read as "who should be here", not "who happened to sort
    first".
    """

    season = Season(
        name="VMF Fantasy League 2026/27",
        fpl_season_code="2026/27",
        start_gameweek=1,
        end_gameweek=38,
    )
    session.add(season)
    await session.flush()

    gameweeks: dict[int, Gameweek] = {}
    for number in range(1, 39):
        gameweek = Gameweek(
            season_id=season.id,
            number=number,
            is_finalized=finalize_cutoff and number <= through_gameweek,
        )
        session.add(gameweek)
        gameweeks[number] = gameweek
    await session.flush()

    managers: list[Manager] = []
    points_per_gameweek: dict[int, int] = {}
    for division, size in ((Division.HIGH, HIGH_SIZE), (Division.LOW, LOW_SIZE)):
        for index in range(size):
            manager = Manager(
                fpl_entry_id=(1_000_000 if division is Division.HIGH else 2_000_000) + index,
                manager_name=f"{division.value} Manager {index + 1}",
                team_name=f"{division.value} Team {index + 1}",
                division=division,
                active_status=ManagerStatus.ACTIVE,
                registration_status=RegistrationStatus.CONFIRMED,
                season_joined="2026/27",
            )
            session.add(manager)
            managers.append(manager)
            await session.flush()
            # Descending within each division, so roster order is rank order.
            points_per_gameweek[manager.id] = 100 - index

    for manager in managers:
        per_gameweek = points_per_gameweek[manager.id]
        for number in range(1, through_gameweek + 1):
            session.add(
                ManagerGameweekScore(
                    manager_id=manager.id,
                    gameweek_id=gameweeks[number].id,
                    gross_points=per_gameweek,
                    transfer_cost=0,
                    net_points=per_gameweek,
                    captain_points=10,
                    goals_counted=2,
                    score_status=ScoreState.FINAL,
                )
            )
    await session.flush()
    return season, managers


def _high(managers: list[Manager], rank: int) -> Manager:
    return managers[rank - 1]


def _low(managers: list[Manager], rank: int) -> Manager:
    return managers[HIGH_SIZE + rank - 1]


# --------------------------------------------------------------------------
# Qualification
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_qualification_ranks_each_division_separately() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, managers = await _seed_league(session)
            table = await CupQualificationService(session).table(season_id=season.id, season_half=1)

            assert table.start_gameweek == 1
            assert table.end_gameweek == 13
            assert table.is_settled is True
            assert len(table.entries[Division.HIGH]) == HIGH_SIZE
            assert len(table.entries[Division.LOW]) == LOW_SIZE

            high = table.entries[Division.HIGH]
            assert [entry.rank for entry in high] == list(range(1, HIGH_SIZE + 1))
            assert high[0].manager_id == _high(managers, 1).id
            assert high[0].qualification_points == 100 * 13
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_violation_gameweek_contributes_zero_to_the_cup_only() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, managers = await _seed_league(session)
            leader = _high(managers, 1)
            session.add(
                Violation(
                    manager_id=leader.id,
                    gameweek_number=5,
                    violation_type=ViolationType.TRANSFER_HIT,
                    status=ViolationStatus.CONFIRMED,
                    detected_count=1,
                    confirmed_count=1,
                )
            )
            await session.flush()

            table = await CupQualificationService(session).table(season_id=season.id, season_half=1)
            entry = next(
                item for item in table.entries[Division.HIGH] if item.manager_id == leader.id
            )

            assert entry.gameweeks_excluded == (5,)
            assert entry.gameweeks_counted == 12
            assert entry.qualification_points == 100 * 12

            # Losing one Gameweek costs the leader far more than one place:
            # 1200 sits between the 93-point manager (1209) and the 92-point
            # manager (1196), so HIGH's best falls from first to eighth and
            # enters the Cup a round earlier than they otherwise would.
            assert entry.rank == 8
            assert entry.enters_at_round == 2

            # Classic is untouched: the same Gameweek still counts there.
            others = [item for item in table.entries[Division.HIGH] if item.manager_id != leader.id]
            assert others[0].qualification_points == 99 * 13
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_entry_round_marks_who_starts_where_and_who_misses_out() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, _ = await _seed_league(session)
            table = await CupQualificationService(session).table(season_id=season.id, season_half=1)
            high = {entry.rank: entry.enters_at_round for entry in table.entries[Division.HIGH]}
            low = {entry.rank: entry.enters_at_round for entry in table.entries[Division.LOW]}

            assert [high[rank] for rank in (1, 2, 3)] == [3, 3, 3], "HIGH 1-3 wait for the R16"
            assert [high[rank] for rank in range(4, 11)] == [2] * 7
            assert [high[rank] for rank in range(11, 19)] == [1] * 8
            assert high[19] is None and high[20] is None, "HIGH 19-20 miss the Cup"

            assert low[1] == 3
            assert [low[rank] for rank in range(2, 7)] == [2] * 5
            assert [low[rank] for rank in range(7, 23)] == [1] * 16
            assert [low[rank] for rank in range(23, 27)] == [None] * 4
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# Drawing the bracket
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_draw_writes_every_round_at_once() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, managers = await _seed_league(session)
            drawn = await CupBracketService(session).generate(season_code="2026/27", season_half=1)

            assert drawn.rounds_created == 6
            # 12 + 12 + 8 + 4 + 2 + 1, plus the third-place match.
            assert drawn.matches_created == 40
            assert drawn.managers_placed == 40

            rounds = await CupService(session).rounds(drawn.cup_id)
            assert [round_.name for round_, _ in rounds] == [
                "Qualifying Round 1",
                "Qualifying Round 2",
                "Round of 16",
                "Quarter-finals",
                "Semi-finals",
                "Final",
            ]
            assert [round_.gameweek_number for round_, _ in rounds] == [14, 15, 16, 17, 18, 19]

            first_round = rounds[0][1]
            assert [match.tie_id for match in first_round] == [
                f"Q1-{index}" for index in range(1, 13)
            ]
            # The published sheet opens with HIGH 11 against LOW 22.
            assert first_round[0].slot_a_label == "H11"
            assert first_round[0].slot_b_label == "L22"
            assert first_round[0].manager_a_id == _high(managers, 11).id
            assert first_round[0].manager_b_id == _low(managers, 22).id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_later_rounds_are_drawn_empty_but_labelled() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed_league(session)
            drawn = await CupBracketService(session).generate(season_code="2026/27", season_half=1)
            rounds = dict(
                (round_.name, matches)
                for round_, matches in await CupService(session).rounds(drawn.cup_id)
            )

            final = rounds["Final"]
            assert len(final) == 2, "the final and the third-place match"
            tie, third = final[0], final[1]
            assert tie.tie_id == "F"
            assert (tie.slot_a_label, tie.slot_b_label) == ("W(SF-1)", "W(SF-2)")
            assert tie.manager_a_id is None and tie.manager_b_id is None
            assert third.is_third_place_match is True
            assert (third.slot_a_label, third.slot_b_label) == ("L(SF-1)", "L(SF-2)")

            # The round of 16 carries its four byes from the start.
            seeded = [m for m in rounds["Round of 16"] if m.manager_b_id is not None]
            assert [m.slot_b_label for m in seeded] == ["L1", "H3", "H2", "H1"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_cup_is_only_drawn_once() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed_league(session)
            service = CupBracketService(session)
            await service.generate(season_code="2026/27", season_half=1)
            with pytest.raises(ConflictError, match="already drawn"):
                await service.generate(season_code="2026/27", season_half=1)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_the_draw_waits_for_the_cutoff_gameweek_to_be_finalized() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed_league(session, finalize_cutoff=False)
            service = CupBracketService(session)
            with pytest.raises(RuleValidationError, match="GW13 is not finalized"):
                await service.generate(season_code="2026/27", season_half=1)

            # A rehearsal draw is still possible, but only when asked for.
            drawn = await service.generate(
                season_code="2026/27", season_half=1, allow_provisional=True
            )
            assert drawn.managers_placed == 40
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_shared_rank_stops_the_draw_rather_than_guessing() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, managers = await _seed_league(session)
            # Give HIGH 12 exactly HIGH 11's record, so both hold rank 11.
            eleventh, twelfth = _high(managers, 11), _high(managers, 12)
            scores = (
                await session.scalars(
                    select(ManagerGameweekScore).where(
                        ManagerGameweekScore.manager_id == twelfth.id
                    )
                )
            ).all()
            reference = (
                await session.scalars(
                    select(ManagerGameweekScore).where(
                        ManagerGameweekScore.manager_id == eleventh.id
                    )
                )
            ).all()
            for score, model in zip(scores, reference, strict=True):
                score.net_points = model.net_points
                score.gross_points = model.gross_points
            await session.flush()

            table = await CupQualificationService(session).table(season_id=season.id, season_half=1)
            shared = [e.rank for e in table.entries[Division.HIGH]]
            assert shared.count(11) == 2, "both managers hold rank 11"

            with pytest.raises(RuleValidationError, match="does not fill every bracket place"):
                await CupBracketService(session).generate(season_code="2026/27", season_half=1)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_an_unknown_season_is_reported_as_missing() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed_league(session)
            with pytest.raises(NotFoundError, match="season '2027/28' not found"):
                await CupBracketService(session).generate(season_code="2027/28", season_half=1)
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# Advancing
# --------------------------------------------------------------------------


async def _score_gameweek(
    session: AsyncSession,
    *,
    season_id: int,
    number: int,
    points: dict[int, int],
) -> None:
    gameweek = await session.scalar(
        select(Gameweek).where(Gameweek.season_id == season_id, Gameweek.number == number)
    )
    assert gameweek is not None
    gameweek.is_finalized = True
    for manager_id, value in points.items():
        session.add(
            ManagerGameweekScore(
                manager_id=manager_id,
                gameweek_id=gameweek.id,
                gross_points=value,
                transfer_cost=0,
                net_points=value,
                score_status=ScoreState.FINAL,
            )
        )
    await session.flush()


@pytest.mark.asyncio
async def test_advancing_settles_ties_and_fills_the_next_round() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, _ = await _seed_league(session)
            drawn = await CupBracketService(session).generate(season_code="2026/27", season_half=1)
            first_round = (await CupService(session).rounds(drawn.cup_id))[0][1]

            # Side A wins every tie of the first round.
            points: dict[int, int] = {}
            for match in first_round:
                assert match.manager_a_id and match.manager_b_id
                points[match.manager_a_id] = 80
                points[match.manager_b_id] = 60
            await _score_gameweek(session, season_id=season.id, number=14, points=points)

            advanced = await CupBracketService(session).advance(
                cup_id=drawn.cup_id, gameweek_number=14
            )
            assert advanced.round_name == "Qualifying Round 1"
            assert advanced.ties_resolved == 12
            assert advanced.ties_awaiting_draw == 0
            assert advanced.managers_promoted == 12

            rounds = await CupService(session).rounds(drawn.cup_id)
            settled = rounds[0][1]
            assert all(match.status is MatchStatus.FINAL for match in settled)
            assert [match.manager_a_score for match in settled] == [80] * 12
            assert [match.winner_manager_id for match in settled] == [
                match.manager_a_id for match in settled
            ]

            second_round = rounds[1][1]
            assert [match.manager_a_id for match in second_round] == [
                match.winner_manager_id for match in settled
            ]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_level_tie_is_decided_by_the_rulebook_chain() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, _ = await _seed_league(session)
            drawn = await CupBracketService(session).generate(season_code="2026/27", season_half=1)
            first_round = (await CupService(session).rounds(drawn.cup_id))[0][1]
            tie = first_round[0]
            assert tie.manager_a_id and tie.manager_b_id

            points = {match.manager_a_id: 70 for match in first_round if match.manager_a_id}
            points.update({match.manager_b_id: 50 for match in first_round if match.manager_b_id})
            points[tie.manager_b_id] = 70  # dead level with side A
            await _score_gameweek(session, season_id=season.id, number=14, points=points)

            await CupBracketService(session).advance(cup_id=drawn.cup_id, gameweek_number=14)
            await session.refresh(tie)

            assert tie.status is MatchStatus.FINAL
            assert tie.tie_break_step_used is not None
            assert tie.tie_break_step_used.value != "match_score"
            assert tie.winner_manager_id in {tie.manager_a_id, tie.manager_b_id}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_gameweek_that_plays_no_round_is_rejected() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed_league(session)
            drawn = await CupBracketService(session).generate(season_code="2026/27", season_half=1)
            with pytest.raises(RuleValidationError, match="GW20 plays no round"):
                await CupBracketService(session).advance(cup_id=drawn.cup_id, gameweek_number=20)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_live_gameweek_cannot_settle_its_cup_ties() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed_league(session)
            drawn = await CupBracketService(session).generate(season_code="2026/27", season_half=1)
            with pytest.raises(RuleValidationError, match="GW14 is not finalized"):
                await CupBracketService(session).advance(cup_id=drawn.cup_id, gameweek_number=14)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semi_final_losers_meet_in_the_third_place_match() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, _ = await _seed_league(session)
            service = CupBracketService(session)
            drawn = await service.generate(season_code="2026/27", season_half=1)

            # Walk the whole Cup: side A wins every tie in every round.
            for round_definition in CUP_SEASON_1.rounds[:-1]:
                rounds = await CupService(session).rounds(drawn.cup_id)
                matches = rounds[round_definition.round_order - 1][1]
                points = {}
                for match in matches:
                    if match.manager_a_id and match.manager_b_id:
                        points[match.manager_a_id] = 80
                        points[match.manager_b_id] = 60
                await _score_gameweek(
                    session,
                    season_id=season.id,
                    number=round_definition.gameweek_number,
                    points=points,
                )
                await service.advance(
                    cup_id=drawn.cup_id, gameweek_number=round_definition.gameweek_number
                )

            final_round = (await CupService(session).rounds(drawn.cup_id))[5][1]
            final, third = final_round[0], final_round[1]
            semi_finals = (await CupService(session).rounds(drawn.cup_id))[4][1]

            assert final.manager_a_id == semi_finals[0].winner_manager_id
            assert final.manager_b_id == semi_finals[1].winner_manager_id
            assert third.manager_a_id == semi_finals[0].manager_b_id
            assert third.manager_b_id == semi_finals[1].manager_b_id
            assert third.manager_a_id != final.manager_a_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_advancing_twice_changes_nothing() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            season, _ = await _seed_league(session)
            drawn = await CupBracketService(session).generate(season_code="2026/27", season_half=1)
            first_round = (await CupService(session).rounds(drawn.cup_id))[0][1]
            points: dict[int, int] = {}
            for match in first_round:
                assert match.manager_a_id and match.manager_b_id
                points[match.manager_a_id] = 80
                points[match.manager_b_id] = 60
            await _score_gameweek(session, season_id=season.id, number=14, points=points)

            service = CupBracketService(session)
            first = await service.advance(cup_id=drawn.cup_id, gameweek_number=14)
            winners = [match.winner_manager_id for match in first_round]

            second = await service.advance(cup_id=drawn.cup_id, gameweek_number=14)
            assert second.ties_resolved == 0, "settled ties are not re-decided"
            assert second.managers_promoted == 0
            assert [match.winner_manager_id for match in first_round] == winners
            assert first.ties_resolved == 12
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_an_unknown_cup_is_reported_as_missing() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed_league(session)
            with pytest.raises(NotFoundError, match="cup 999 not found"):
                await CupBracketService(session).advance(cup_id=999, gameweek_number=14)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_rounds_and_matches_are_persisted_in_bracket_order() -> None:
    factory, engine = await _database()
    try:
        async with factory() as session:
            await _seed_league(session)
            drawn = await CupBracketService(session).generate(season_code="2026/27", season_half=1)
            stored = (
                await session.scalars(
                    select(CupRound)
                    .where(CupRound.cup_competition_id == drawn.cup_id)
                    .order_by(CupRound.round_order)
                )
            ).all()
            assert [round_.round_order for round_ in stored] == [1, 2, 3, 4, 5, 6]

            counts = []
            for round_ in stored:
                matches = (
                    await session.scalars(
                        select(CupMatch).where(CupMatch.cup_round_id == round_.id)
                    )
                ).all()
                counts.append(len(matches))
            assert counts == [12, 12, 8, 4, 2, 2]
    finally:
        await engine.dispose()
