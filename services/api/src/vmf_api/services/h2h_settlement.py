"""Write H2H results from the Gameweek scores, and keep them in step.

The schedule and the standings both existed, but nothing joined them: matches
stayed ``scheduled`` for ever, so the table could only ever read zero. This is
that join, and it runs on every tick so a live Gameweek shows a live result.

A finalized Gameweek is left alone. Rulebook 11 makes a final revision
immutable, so once the organisers lock a Gameweek its matches stop tracking
later corrections and a reopen is required to change them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.domain.h2h_result import MatchResult, Settlement, settle_match
from vmf_api.domain.violations import ThresholdAction
from vmf_api.models.competition import Gameweek
from vmf_api.models.enums import MatchStatus, ScoreState
from vmf_api.models.governance import ViolationThresholdAction
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.scoring import ManagerGameweekScore

#: How a Gameweek's score state presents an H2H match.
STATUS_FOR_SCORE_STATE = {
    ScoreState.LIVE: MatchStatus.LIVE,
    ScoreState.PROVISIONAL: MatchStatus.PROVISIONAL,
    ScoreState.FINAL: MatchStatus.FINAL,
}


@dataclass(frozen=True, slots=True)
class SettlementOutcome:
    gameweek_number: int
    settled: int = 0
    walkovers: int = 0
    needs_review: tuple[int, ...] = ()
    untouched_final: int = 0
    skipped_reason: str | None = None
    detail: dict[str, int] = field(default_factory=dict)


class H2HSettlementService:
    def __init__(self, session: AsyncSession, *, season_id: int) -> None:
        self.session = session
        self.season_id = season_id

    async def settle_gameweek(self, gameweek_number: int) -> SettlementOutcome:
        gameweek = await self.session.scalar(
            select(Gameweek).where(
                Gameweek.season_id == self.season_id,
                Gameweek.number == gameweek_number,
            )
        )
        if gameweek is None:
            return SettlementOutcome(
                gameweek_number=gameweek_number,
                skipped_reason="gameweek_not_found",
            )

        schedule_ids = list(
            await self.session.scalars(
                select(H2HSchedule.id).where(H2HSchedule.season_id == self.season_id)
            )
        )
        if not schedule_ids:
            return SettlementOutcome(
                gameweek_number=gameweek_number,
                skipped_reason="no_schedule",
            )

        matches = list(
            await self.session.scalars(
                select(H2HMatch).where(
                    H2HMatch.schedule_id.in_(schedule_ids),
                    H2HMatch.gameweek_number == gameweek_number,
                )
            )
        )
        if not matches:
            return SettlementOutcome(
                gameweek_number=gameweek_number,
                skipped_reason="no_matches",
            )

        scores = {
            row.manager_id: row
            for row in await self.session.scalars(
                select(ManagerGameweekScore).where(ManagerGameweekScore.gameweek_id == gameweek.id)
            )
        }
        forfeiting = await self._managers_removed_from_h2h()

        settled = 0
        walkovers = 0
        needs_review: list[int] = []
        untouched_final = 0

        for match in matches:
            # A locked Gameweek keeps the result it was settled with.
            if match.status is MatchStatus.FINAL and gameweek.is_finalized:
                untouched_final += 1
                continue

            home = scores.get(match.home_manager_id)
            away = scores.get(match.away_manager_id)
            result = settle_match(
                home_points=home.net_points if home is not None else None,
                away_points=away.net_points if away is not None else None,
                home_forfeits=match.home_manager_id in forfeiting,
                away_forfeits=match.away_manager_id in forfeiting,
            )

            if result.settlement is Settlement.NEEDS_REVIEW:
                needs_review.append(match.id)
                match.walkover_reason = result.walkover_reason
                continue
            if result.settlement is Settlement.NOT_PLAYED:
                continue

            self._apply(match, result, home=home, away=away)
            settled += 1
            if result.settlement is Settlement.WALKOVER:
                walkovers += 1

        await self.session.flush()
        return SettlementOutcome(
            gameweek_number=gameweek_number,
            settled=settled,
            walkovers=walkovers,
            needs_review=tuple(needs_review),
            untouched_final=untouched_final,
            detail={"matches": len(matches), "scored_managers": len(scores)},
        )

    def _apply(
        self,
        match: H2HMatch,
        result: MatchResult,
        *,
        home: ManagerGameweekScore | None,
        away: ManagerGameweekScore | None,
    ) -> None:
        match.home_score = result.home_score
        match.away_score = result.away_score
        if result.winner == "home":
            match.winner_manager_id = match.home_manager_id
        elif result.winner == "away":
            match.winner_manager_id = match.away_manager_id
        else:
            match.winner_manager_id = None

        if result.settlement is Settlement.WALKOVER:
            match.status = MatchStatus.WALKOVER
            match.walkover_reason = result.walkover_reason
            return

        match.walkover_reason = None
        # The match is only as settled as the least settled side's score.
        states = [score.score_status for score in (home, away) if score is not None]
        state = min(states, key=_settledness) if states else ScoreState.LIVE
        match.status = STATUS_FOR_SCORE_STATE.get(state, MatchStatus.LIVE)

    async def _managers_removed_from_h2h(self) -> set[int]:
        return set(
            await self.session.scalars(
                select(ViolationThresholdAction.manager_id).where(
                    ViolationThresholdAction.action == ThresholdAction.REMOVED_FROM_H2H
                )
            )
        )


def _settledness(state: ScoreState) -> int:
    order = {
        ScoreState.UPCOMING: 0,
        ScoreState.LIVE: 1,
        ScoreState.PROVISIONAL: 2,
        ScoreState.FINAL: 3,
    }
    return order.get(state, 0)
