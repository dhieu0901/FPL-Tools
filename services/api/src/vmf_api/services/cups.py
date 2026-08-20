from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.errors import ConflictError, NotFoundError, RuleValidationError
from vmf_api.domain.cup import CupEntry, CupResolution, resolve_cup_match
from vmf_api.domain.cup_bracket import (
    Bracket,
    Seed,
    Slot,
    Winner,
    bracket_for_half,
)
from vmf_api.domain.rankings import competition_rank
from vmf_api.domain.tie_breaks import TieBreakFacts
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.cup import CupCompetition, CupMatch, CupRound
from vmf_api.models.enums import Division, ManagerStatus, MatchStatus
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore
from vmf_api.repositories.cups import CupRepository
from vmf_api.services.violations import gameweeks_with_confirmed_violations


@dataclass(frozen=True, slots=True)
class QualificationEntry:
    """One manager's line in a Cup qualification table."""

    rank: int
    manager_id: int
    manager_name: str
    team_name: str
    division: Division
    qualification_points: int
    gameweeks_counted: int
    #: Gameweeks removed from the total by a confirmed violation, per 9.5.
    gameweeks_excluded: tuple[int, ...]
    totw_count: int
    captain_points: int
    #: The round this rank enters at, or ``None`` when the rank misses the Cup.
    enters_at_round: int | None


@dataclass(frozen=True, slots=True)
class QualificationTable:
    season_id: int
    season_half: int
    start_gameweek: int
    end_gameweek: int
    #: True once the cutoff Gameweek is finalized, i.e. the table can be drawn.
    is_settled: bool
    entries: dict[Division, list[QualificationEntry]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GeneratedBracket:
    cup_id: int
    season_half: int
    rounds_created: int
    matches_created: int
    managers_placed: int


@dataclass(frozen=True, slots=True)
class AdvancedRound:
    round_name: str
    gameweek_number: int
    ties_resolved: int
    ties_awaiting_draw: int
    managers_promoted: int


class CupService:
    """Read access to the Cup: competitions, rounds and their ties."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CupRepository(session)

    async def list_competitions(self, season_id: int | None = None) -> list[CupCompetition]:
        return await self.repository.list_competitions(season_id)

    async def get_competition(self, cup_id: int) -> CupCompetition:
        competition = await self.repository.get_competition(cup_id)
        if competition is None:
            raise NotFoundError(f"cup {cup_id} not found")
        return competition

    async def rounds(self, cup_id: int) -> list[tuple[CupRound, list[CupMatch]]]:
        await self.get_competition(cup_id)
        return await self.repository.rounds_with_matches(cup_id)

    async def bracket(self, cup_id: int) -> list[CupMatch]:
        if await self.repository.get_competition(cup_id) is None:
            raise NotFoundError(f"cup {cup_id} not found")
        return await self.repository.bracket(cup_id)


class CupQualificationService:
    """Build the ledger that decides who enters each Cup, and where.

    The table is deliberately separate from Classic: a Gameweek carrying a
    confirmed violation contributes zero here and its full value there, so the
    two totals are expected to disagree for a sanctioned manager.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def table(self, *, season_id: int, season_half: int) -> QualificationTable:
        bracket = bracket_for_half(season_half)
        start = bracket.qualification_start_gameweek
        end = bracket.qualification_end_gameweek

        cutoff = await self.session.scalar(
            select(Gameweek).where(Gameweek.season_id == season_id, Gameweek.number == end)
        )
        managers = list(
            (
                await self.session.scalars(
                    select(Manager).where(
                        Manager.active_status.not_in([ManagerStatus.DELETED, ManagerStatus.REMOVED])
                    )
                )
            )
            .unique()
            .all()
        )
        scores = await self._scores_in_window(season_id=season_id, start=start, end=end)
        excluded = await gameweeks_with_confirmed_violations(
            self.session, [manager.id for manager in managers]
        )
        entry_round = _entry_round_by_seed(bracket)

        by_division: dict[Division, list[QualificationEntry]] = {}
        for division in (Division.HIGH, Division.LOW):
            members = [manager for manager in managers if manager.division == division]
            ranked = competition_rank(
                [self._totals(manager, scores, excluded) for manager in members],
                key=lambda row: (row.qualification_points, *row.tie_break.sort_key()),
            )
            by_division[division] = [
                QualificationEntry(
                    rank=item.rank,
                    manager_id=item.value.manager.id,
                    manager_name=item.value.manager.manager_name,
                    team_name=item.value.manager.team_name,
                    division=division,
                    qualification_points=item.value.qualification_points,
                    gameweeks_counted=item.value.gameweeks_counted,
                    gameweeks_excluded=item.value.gameweeks_excluded,
                    totw_count=item.value.tie_break.totw_count,
                    captain_points=item.value.tie_break.captain_points,
                    enters_at_round=entry_round.get(Seed(division.value, item.rank)),  # type: ignore[arg-type]
                )
                for item in ranked
            ]

        return QualificationTable(
            season_id=season_id,
            season_half=season_half,
            start_gameweek=start,
            end_gameweek=end,
            is_settled=bool(cutoff and cutoff.is_finalized),
            entries=by_division,
        )

    async def _scores_in_window(
        self,
        *,
        season_id: int,
        start: int,
        end: int,
    ) -> dict[int, list[tuple[int, ManagerGameweekScore]]]:
        statement = (
            select(Gameweek.number, ManagerGameweekScore)
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(Gameweek.season_id == season_id, Gameweek.number.between(start, end))
        )
        rows = (await self.session.execute(statement)).all()
        grouped: dict[int, list[tuple[int, ManagerGameweekScore]]] = {}
        for number, score in rows:
            grouped.setdefault(score.manager_id, []).append((number, score))
        return grouped

    def _totals(
        self,
        manager: Manager,
        scores: dict[int, list[tuple[int, ManagerGameweekScore]]],
        excluded: dict[int, set[int]],
    ) -> _QualificationTotals:
        violation_gameweeks = excluded.get(manager.id, set())
        counted = [
            (number, score)
            for number, score in scores.get(manager.id, [])
            if number not in violation_gameweeks
        ]
        dropped = tuple(
            sorted(
                number for number, _ in scores.get(manager.id, []) if number in violation_gameweeks
            )
        )
        return _QualificationTotals(
            manager=manager,
            qualification_points=sum(score.net_points for _, score in counted),
            gameweeks_counted=len(counted),
            gameweeks_excluded=dropped,
            tie_break=TieBreakFacts(
                totw_count=sum(1 for _, score in counted if score.is_totw),
                captain_points=sum(score.captain_points for _, score in counted),
                goals=sum(score.goals_counted for _, score in counted),
                cards=sum(
                    score.yellow_cards_counted + score.red_cards_counted for _, score in counted
                ),
                classic_points=sum(score.net_points for _, score in scores.get(manager.id, [])),
            ),
        )


@dataclass(frozen=True, slots=True)
class _QualificationTotals:
    manager: Manager
    qualification_points: int
    gameweeks_counted: int
    gameweeks_excluded: tuple[int, ...]
    tie_break: TieBreakFacts


def _entry_round_by_seed(bracket: Bracket) -> dict[Seed, int]:
    """Which round each qualification place walks into."""

    return {
        slot: round_.round_order
        for round_ in bracket.rounds
        for tie in round_.ties
        for slot in (tie.first, tie.second)
        if isinstance(slot, Seed)
    }


class CupBracketService:
    """Draw a Cup and move winners through it.

    Drawing is a single decision made once the qualification Gameweek is
    finalized: every tie in all six rounds is written at that moment, with the
    two qualifying rounds carrying real managers and the later rounds carrying
    only their bracket position. Nothing is invented later, so the shape of the
    Cup a manager sees in GW14 is the shape it still has in GW19.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CupRepository(session)
        self.qualification = CupQualificationService(session)

    async def generate(
        self,
        *,
        season_code: str,
        season_half: int,
        allow_provisional: bool = False,
    ) -> GeneratedBracket:
        bracket = bracket_for_half(season_half)
        season = await self.session.scalar(
            select(Season).where(Season.fpl_season_code == season_code)
        )
        if season is None:
            raise NotFoundError(f"season {season_code!r} not found")

        existing = await self.session.scalar(
            select(CupCompetition).where(
                CupCompetition.season_id == season.id,
                CupCompetition.season_half == season_half,
            )
        )
        if existing is not None:
            raise ConflictError(
                f"Cup Season {season_half} is already drawn (cup {existing.id}); "
                "reopening a drawn Cup is an administrator decision"
            )

        table = await self.qualification.table(season_id=season.id, season_half=season_half)
        if not table.is_settled and not allow_provisional:
            raise RuleValidationError(
                f"GW{bracket.qualification_end_gameweek} is not finalized, so the "
                f"Season {season_half} qualification table can still change"
            )

        seeded = _managers_by_seed(table)
        missing = [seed for seed in bracket.entry_seeds() if seed not in seeded]
        if missing:
            raise RuleValidationError(
                "the qualification table does not fill every bracket place; missing "
                + ", ".join(str(seed) for seed in sorted(missing, key=str))
            )

        competition = CupCompetition(
            season_id=season.id,
            name=bracket.name,
            season_half=season_half,
            qualification_end_gameweek=bracket.qualification_end_gameweek,
        )
        self.session.add(competition)
        await self.session.flush()

        matches_created = 0
        managers_placed = 0
        for definition in bracket.rounds:
            round_ = CupRound(
                cup_competition_id=competition.id,
                name=definition.name,
                round_order=definition.round_order,
                gameweek_number=definition.gameweek_number,
                has_third_place_match=definition.has_third_place_match,
            )
            self.session.add(round_)
            await self.session.flush()

            for tie in definition.ties:
                manager_a = seeded.get(tie.first) if isinstance(tie.first, Seed) else None
                manager_b = seeded.get(tie.second) if isinstance(tie.second, Seed) else None
                managers_placed += sum(1 for value in (manager_a, manager_b) if value is not None)
                self.session.add(
                    CupMatch(
                        cup_round_id=round_.id,
                        tie_id=tie.tie_id,
                        slot_a_label=str(tie.first),
                        slot_b_label=str(tie.second),
                        manager_a_id=manager_a,
                        manager_b_id=manager_b,
                        status=MatchStatus.SCHEDULED,
                    )
                )
                matches_created += 1

            if definition.has_third_place_match:
                # Both semi-final losers meet here, so neither side is known
                # until the semi-finals are settled.
                self.session.add(
                    CupMatch(
                        cup_round_id=round_.id,
                        tie_id="3RD",
                        slot_a_label="L(SF-1)",
                        slot_b_label="L(SF-2)",
                        status=MatchStatus.SCHEDULED,
                        is_third_place_match=True,
                    )
                )
                matches_created += 1

        await self.session.flush()
        return GeneratedBracket(
            cup_id=competition.id,
            season_half=season_half,
            rounds_created=len(bracket.rounds),
            matches_created=matches_created,
            managers_placed=managers_placed,
        )

    async def advance(self, *, cup_id: int, gameweek_number: int) -> AdvancedRound:
        """Settle one round's ties and move the winners into their next slot."""

        competition = await self.repository.get_competition(cup_id)
        if competition is None:
            raise NotFoundError(f"cup {cup_id} not found")

        bracket = bracket_for_half(competition.season_half)
        definition = bracket.round_for_gameweek(gameweek_number)
        if definition is None:
            raise RuleValidationError(f"GW{gameweek_number} plays no round of {bracket.name}")

        gameweek = await self.session.scalar(
            select(Gameweek).where(
                Gameweek.season_id == competition.season_id,
                Gameweek.number == gameweek_number,
            )
        )
        if gameweek is None or not gameweek.is_finalized:
            raise RuleValidationError(
                f"GW{gameweek_number} is not finalized, so its Cup ties are still live"
            )

        rounds = await self.repository.rounds_with_matches(cup_id)
        by_order = {round_.round_order: (round_, matches) for round_, matches in rounds}
        current = by_order.get(definition.round_order)
        if current is None:
            raise NotFoundError(f"cup {cup_id} has no round {definition.name!r}")

        facts = await self._tie_break_facts(
            season_id=competition.season_id,
            through_gameweek=gameweek_number,
            season_half=competition.season_half,
        )
        scores = await self._scores_for_gameweek(gameweek_id=gameweek.id)

        resolved = 0
        awaiting_draw = 0
        winners: dict[str, int] = {}
        losers: dict[str, int] = {}
        for match in current[1]:
            if match.winner_manager_id is not None:
                winners[match.tie_id] = match.winner_manager_id
                losers[match.tie_id] = _other_side(match, match.winner_manager_id)
                continue
            if match.manager_a_id is None or match.manager_b_id is None:
                continue

            resolution = self._resolve(match, scores=scores, facts=facts)
            if resolution.requires_admin_draw:
                match.status = MatchStatus.PROVISIONAL
                match.tie_break_step_used = resolution.step
                awaiting_draw += 1
                continue

            match.manager_a_score = scores.get(match.manager_a_id, 0)
            match.manager_b_score = scores.get(match.manager_b_id, 0)
            match.winner_manager_id = resolution.winner_manager_id
            match.tie_break_step_used = resolution.step
            match.status = MatchStatus.FINAL
            resolved += 1
            if resolution.winner_manager_id is not None:
                winners[match.tie_id] = resolution.winner_manager_id
                losers[match.tie_id] = _other_side(match, resolution.winner_manager_id)

        promoted = self._place_winners(
            bracket=bracket,
            after_round=definition.round_order,
            by_order=by_order,
            winners=winners,
            losers=losers,
        )
        await self.session.flush()
        return AdvancedRound(
            round_name=definition.name,
            gameweek_number=gameweek_number,
            ties_resolved=resolved,
            ties_awaiting_draw=awaiting_draw,
            managers_promoted=promoted,
        )

    def _resolve(
        self,
        match: CupMatch,
        *,
        scores: dict[int, int],
        facts: dict[int, TieBreakFacts],
    ) -> CupResolution:
        def entry(manager_id: int) -> CupEntry:
            manager_facts = facts.get(manager_id, TieBreakFacts())
            return CupEntry(
                manager_id=manager_id,
                match_score=scores.get(manager_id, 0),
                cumulative_totw_count=manager_facts.totw_count,
                captain_points=manager_facts.captain_points,
                counted_goals=manager_facts.goals,
                counted_cards=manager_facts.cards,
                classic_season_points=manager_facts.classic_points,
            )

        assert match.manager_a_id is not None and match.manager_b_id is not None
        return resolve_cup_match(entry(match.manager_a_id), entry(match.manager_b_id))

    def _place_winners(
        self,
        *,
        bracket: Bracket,
        after_round: int,
        by_order: dict[int, tuple[CupRound, list[CupMatch]]],
        winners: dict[str, int],
        losers: dict[str, int],
    ) -> int:
        """Write the winners into whichever later ties reference them."""

        placed = 0
        for definition in bracket.rounds:
            if definition.round_order <= after_round:
                continue
            target = by_order.get(definition.round_order)
            if target is None:
                continue
            rows = {match.tie_id: match for match in target[1]}
            for tie in definition.ties:
                match = rows.get(tie.tie_id)
                if match is None:
                    continue
                for slot, attribute in ((tie.first, "manager_a_id"), (tie.second, "manager_b_id")):
                    if not isinstance(slot, Winner) or getattr(match, attribute) is not None:
                        continue
                    winner = winners.get(slot.tie)
                    if winner is not None:
                        setattr(match, attribute, winner)
                        placed += 1

            third_place = rows.get("3RD")
            if third_place is not None and definition.has_third_place_match:
                semi_final_ties = [
                    tie.tie_id
                    for round_ in bracket.rounds
                    if round_.round_order == definition.round_order - 1
                    for tie in round_.ties
                ]
                for tie_id, attribute in zip(
                    semi_final_ties, ("manager_a_id", "manager_b_id"), strict=False
                ):
                    if getattr(third_place, attribute) is None and tie_id in losers:
                        setattr(third_place, attribute, losers[tie_id])
                        placed += 1
        return placed

    async def _scores_for_gameweek(self, *, gameweek_id: int) -> dict[int, int]:
        rows = (
            await self.session.execute(
                select(
                    ManagerGameweekScore.manager_id,
                    ManagerGameweekScore.net_points,
                ).where(ManagerGameweekScore.gameweek_id == gameweek_id)
            )
        ).all()
        return {manager_id: net_points for manager_id, net_points in rows}

    async def _tie_break_facts(
        self,
        *,
        season_id: int,
        through_gameweek: int,
        season_half: int,
    ) -> dict[int, TieBreakFacts]:
        """Cumulative measures up to and including the Gameweek being played."""

        classic_start = 1 if season_half == 1 else 20
        statement = (
            select(Gameweek.number, ManagerGameweekScore)
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(Gameweek.season_id == season_id, Gameweek.number <= through_gameweek)
        )
        rows = (await self.session.execute(statement)).all()
        totals: dict[int, dict[str, int]] = {}
        for number, score in rows:
            bucket = totals.setdefault(
                score.manager_id,
                {"totw": 0, "captain": 0, "goals": 0, "cards": 0, "classic": 0},
            )
            bucket["totw"] += 1 if score.is_totw else 0
            bucket["captain"] += score.captain_points
            bucket["goals"] += score.goals_counted
            bucket["cards"] += score.yellow_cards_counted + score.red_cards_counted
            if number >= classic_start:
                bucket["classic"] += score.net_points
        return {
            manager_id: TieBreakFacts(
                totw_count=bucket["totw"],
                captain_points=bucket["captain"],
                goals=bucket["goals"],
                cards=bucket["cards"],
                classic_points=bucket["classic"],
            )
            for manager_id, bucket in totals.items()
        }


def _managers_by_seed(table: QualificationTable) -> dict[Seed, int]:
    """Map each qualification place to the manager holding it.

    A shared rank leaves the bracket unfillable on purpose: two managers cannot
    both take HIGH 11, and guessing which of them does is exactly the decision
    the rulebook reserves for an audited administrator draw.
    """

    seeded: dict[Seed, int] = {}
    ranks_taken: dict[Seed, int] = {}
    for division, entries in table.entries.items():
        for entry in entries:
            seed = Seed(division.value, entry.rank)  # type: ignore[arg-type]
            ranks_taken[seed] = ranks_taken.get(seed, 0) + 1
            seeded[seed] = entry.manager_id
    return {seed: manager for seed, manager in seeded.items() if ranks_taken[seed] == 1}


def _other_side(match: CupMatch, manager_id: int) -> int:
    if match.manager_a_id == manager_id:
        assert match.manager_b_id is not None
        return match.manager_b_id
    assert match.manager_a_id is not None
    return match.manager_a_id


def slot_label(slot: Slot) -> str:
    return str(slot)
