"""Notable facts from the season so far.

This returns structured facts rather than sentences: a kind, the manager it
concerns and the numbers behind it. The interface writes the prose, so a card
can be reworded without touching the API, and the words can never disagree
with the figures because both come from the same payload.

Most kinds describe the Gameweek just scored. A few stand for the whole
season, and the page keeps the two apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.models.competition import Gameweek
from vmf_api.models.enums import ManagerStatus, RegistrationStatus, ScoreState
from vmf_api.models.h2h import H2HMatch, H2HSchedule
from vmf_api.models.ingestion import (
    FplPlayer,
    FplPlayerFixtureStat,
    ManagerPickItem,
    ManagerPickSnapshot,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore

#: Enough for one of every kind, plus a Gameweek where several managers tie
#: for Team of the Week. The page groups them; it does not show a flat six.
DEFAULT_LIMIT = 14

#: Below this a lone pick is not a brave call, just a player nobody wanted.
LONE_WOLF_MINIMUM = 8

#: Chips whose return is a single number worth judging. A Wildcard or a Free
#: Hit has no equivalent figure, so neither is second-guessed here.
CHIPS_WITH_A_RETURN = ("3xc", "bboost")

#: At or below this, the chip was wasted. Triple Captain is measured on the
#: armband and already multiplied, so 12 means a return of four before the
#: chip; Bench Boost is measured on what the bench actually delivered.
CHIP_MISFIRE_CEILING = {"3xc": 12, "bboost": 6}

#: Captain points are already multiplied, so this is a two-point return on a
#: doubled armband: the player turned up and did nothing.
CAPTAIN_BLANK_CEILING = 4


class HighlightKind(StrEnum):
    TEAM_OF_THE_WEEK = "team_of_the_week"
    SEASON_HIGH = "season_high"
    CAPTAIN_HAUL = "captain_haul"
    TOTW_LEADER = "totw_leader"
    BENCH_REGRET = "bench_regret"
    #: A player nobody else in the league owned, who then delivered.
    LONE_WOLF = "lone_wolf"
    #: The highest score in the Gameweek that still lost its tie.
    UNLUCKY_LOSER = "unlucky_loser"
    #: The lowest score in the Gameweek that still won its tie.
    LUCKY_WINNER = "lucky_winner"
    #: A chip spent for almost nothing. There are only four a half.
    CHIP_MISFIRE = "chip_misfire"
    #: The armband on someone who did not turn up.
    CAPTAIN_BLANK = "captain_blank"


#: Order the cards are offered in. The dashboard shows only the first few, so
#: the ones that carry a story lead and the season records follow.
KIND_ORDER: tuple[HighlightKind, ...] = (
    HighlightKind.TEAM_OF_THE_WEEK,
    HighlightKind.LONE_WOLF,
    HighlightKind.UNLUCKY_LOSER,
    HighlightKind.LUCKY_WINNER,
    HighlightKind.CHIP_MISFIRE,
    HighlightKind.CAPTAIN_HAUL,
    HighlightKind.CAPTAIN_BLANK,
    HighlightKind.BENCH_REGRET,
    HighlightKind.SEASON_HIGH,
    HighlightKind.TOTW_LEADER,
)


@dataclass(frozen=True, slots=True)
class Highlight:
    kind: HighlightKind
    gameweek_number: int | None
    manager_id: int
    manager_name: str
    team_name: str
    value: int
    is_provisional: bool = False
    #: A player's name, where the story is about one: "Semenyo", "Haaland".
    subject: str | None = None
    #: A second number the sentence needs, such as how many of the 46 owned
    #: the player, or which chip was spent.
    detail: str | None = None


class HighlightsService:
    def __init__(self, session: AsyncSession, *, season_id: int) -> None:
        self.session = session
        self.season_id = season_id

    async def latest(self, *, limit: int = DEFAULT_LIMIT) -> list[Highlight]:
        latest_gameweek = await self._latest_scored_gameweek()
        if latest_gameweek is None:
            return []

        highlights: list[Highlight] = []
        highlights.extend(await self._team_of_the_week(latest_gameweek))
        highlights.extend(await self._lone_wolf(latest_gameweek))
        highlights.extend(await self._h2h_luck(latest_gameweek))
        highlights.extend(await self._chip_misfire(latest_gameweek))
        highlights.extend(await self._captain_haul(latest_gameweek))
        highlights.extend(await self._captain_blank(latest_gameweek))
        highlights.extend(await self._bench_regret(latest_gameweek))
        highlights.extend(await self._season_high())
        highlights.extend(await self._totw_leader())

        # Team of the Week can be several managers at once, so a flat cut
        # would let one week's tie push every other story off the page.
        position = {kind: index for index, kind in enumerate(KIND_ORDER)}
        highlights.sort(key=lambda item: position.get(item.kind, len(KIND_ORDER)))
        return highlights[:limit]

    async def _latest_scored_gameweek(self) -> int | None:
        return await self.session.scalar(
            select(func.max(Gameweek.number))
            .select_from(ManagerGameweekScore)
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(Gameweek.season_id == self.season_id)
        )

    def _eligible(self) -> object:
        """Managers whose results are shown publicly."""

        return (
            Manager.registration_status == RegistrationStatus.CONFIRMED,
            Manager.active_status.notin_([ManagerStatus.DELETED, ManagerStatus.REMOVED]),
        )

    async def _team_of_the_week(self, gameweek_number: int) -> list[Highlight]:
        rows = await self.session.execute(
            select(
                Manager.id,
                Manager.manager_name,
                Manager.team_name,
                ManagerGameweekScore.net_points,
                ManagerGameweekScore.score_status,
            )
            .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(
                Gameweek.season_id == self.season_id,
                Gameweek.number == gameweek_number,
                ManagerGameweekScore.is_totw.is_(True),
                *self._eligible(),
            )
            .order_by(Manager.id)
        )
        return [
            Highlight(
                kind=HighlightKind.TEAM_OF_THE_WEEK,
                gameweek_number=gameweek_number,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=net_points,
                is_provisional=status is not ScoreState.FINAL,
            )
            for manager_id, manager_name, team_name, net_points, status in rows
        ]

    async def _top_by(
        self,
        column: object,
        *,
        kind: HighlightKind,
        gameweek_number: int,
        minimum: int = 1,
    ) -> list[Highlight]:
        row = (
            await self.session.execute(
                select(
                    Manager.id,
                    Manager.manager_name,
                    Manager.team_name,
                    column,
                    ManagerGameweekScore.score_status,
                )
                .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
                .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                .where(
                    Gameweek.season_id == self.season_id,
                    Gameweek.number == gameweek_number,
                    *self._eligible(),
                )
                .order_by(column.desc(), Manager.id)  # type: ignore[union-attr]
                .limit(1)
            )
        ).first()
        if row is None or row[3] is None or row[3] < minimum:
            return []
        manager_id, manager_name, team_name, value, status = row
        return [
            Highlight(
                kind=kind,
                gameweek_number=gameweek_number,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=value,
                is_provisional=status is not ScoreState.FINAL,
            )
        ]

    async def _captain_haul(self, gameweek_number: int) -> list[Highlight]:
        return await self._top_by(
            ManagerGameweekScore.captain_points,
            kind=HighlightKind.CAPTAIN_HAUL,
            gameweek_number=gameweek_number,
            minimum=1,
        )

    async def _bench_regret(self, gameweek_number: int) -> list[Highlight]:
        return await self._top_by(
            ManagerGameweekScore.bench_points,
            kind=HighlightKind.BENCH_REGRET,
            gameweek_number=gameweek_number,
            # Below this it is not worth a card on the page.
            minimum=10,
        )

    async def _eligible_managers(self) -> dict[int, tuple[str, str]]:
        rows = await self.session.execute(
            select(Manager.id, Manager.manager_name, Manager.team_name).where(*self._eligible())
        )
        return {row[0]: (row[1], row[2]) for row in rows}

    async def _lone_wolf(self, gameweek_number: int) -> list[Highlight]:
        """The best return from a player nobody else in the league owned.

        This is the one story a public FPL site cannot tell. Global ownership
        is a percentage of millions; here it is a count out of forty-six, and
        being the only person brave enough to own someone who then delivers is
        worth more bragging than any points total.

        Only counted players qualify, so a lone pick sitting on the bench does
        not count as having backed him.
        """

        managers = await self._eligible_managers()
        if not managers:
            return []

        latest = (
            select(
                ManagerPickSnapshot.manager_id.label("manager_id"),
                func.max(ManagerPickSnapshot.revision).label("revision"),
            )
            .where(
                ManagerPickSnapshot.gameweek_number == gameweek_number,
                ManagerPickSnapshot.manager_id.in_(managers),
            )
            .group_by(ManagerPickSnapshot.manager_id)
            .subquery()
        )
        picks = await self.session.execute(
            select(ManagerPickSnapshot.manager_id, ManagerPickItem.element_id)
            .join(ManagerPickItem, ManagerPickItem.snapshot_id == ManagerPickSnapshot.id)
            .join(
                latest,
                (ManagerPickSnapshot.manager_id == latest.c.manager_id)
                & (ManagerPickSnapshot.revision == latest.c.revision),
            )
            .where(ManagerPickItem.multiplier > 0)
        )

        owners: dict[int, set[int]] = {}
        for manager_id, element_id in picks:
            owners.setdefault(element_id, set()).add(manager_id)
        alone = {element: next(iter(who)) for element, who in owners.items() if len(who) == 1}
        if not alone:
            return []

        # A Double Gameweek is two fixtures for one player, so the player's
        # return for the week is the sum of them.
        scored = await self.session.execute(
            select(
                FplPlayerFixtureStat.element_id,
                func.sum(FplPlayerFixtureStat.total_points).label("points"),
            )
            .where(
                FplPlayerFixtureStat.season_id == self.season_id,
                FplPlayerFixtureStat.gameweek_number == gameweek_number,
                FplPlayerFixtureStat.element_id.in_(alone),
            )
            .group_by(FplPlayerFixtureStat.element_id)
        )
        best_element, best_points = None, LONE_WOLF_MINIMUM - 1
        for element_id, points in scored:
            if points is not None and points > best_points:
                best_element, best_points = element_id, points
        if best_element is None:
            return []

        manager_id = alone[best_element]
        manager_name, team_name = managers[manager_id]
        player = await self.session.scalar(
            select(FplPlayer.web_name).where(
                FplPlayer.season_id == self.season_id,
                FplPlayer.element_id == best_element,
            )
        )
        return [
            Highlight(
                kind=HighlightKind.LONE_WOLF,
                gameweek_number=gameweek_number,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=int(best_points),
                subject=player or f"#{best_element}",
                detail=str(len(managers)),
            )
        ]

    async def _h2h_luck(self, gameweek_number: int) -> list[Highlight]:
        """The best score that lost, and the worst score that won.

        Two halves of the same joke, and the reason head to head is played at
        all: in a Classic table 78 points is a good week, and here it can be
        nothing. They are returned together so the page never shows the pain
        without the gloating.
        """

        managers = await self._eligible_managers()
        matches = await self.session.execute(
            select(
                H2HMatch.home_manager_id,
                H2HMatch.away_manager_id,
                H2HMatch.home_score,
                H2HMatch.away_score,
                H2HMatch.winner_manager_id,
            )
            .join(H2HSchedule, H2HSchedule.id == H2HMatch.schedule_id)
            .where(
                H2HSchedule.season_id == self.season_id,
                H2HMatch.gameweek_number == gameweek_number,
                H2HMatch.winner_manager_id.is_not(None),
            )
        )

        loser: tuple[int, int] | None = None
        winner: tuple[int, int] | None = None
        for home_id, away_id, home_score, away_score, winner_id in matches:
            if home_score is None or away_score is None:
                continue
            won_id, won_score = (
                (home_id, home_score) if winner_id == home_id else (away_id, away_score)
            )
            lost_id, lost_score = (
                (away_id, away_score) if winner_id == home_id else (home_id, home_score)
            )
            if loser is None or lost_score > loser[1]:
                loser = (lost_id, lost_score)
            if winner is None or won_score < winner[1]:
                winner = (won_id, won_score)

        found: list[Highlight] = []
        for kind, entry in (
            (HighlightKind.UNLUCKY_LOSER, loser),
            (HighlightKind.LUCKY_WINNER, winner),
        ):
            if entry is None or entry[0] not in managers:
                continue
            manager_name, team_name = managers[entry[0]]
            found.append(
                Highlight(
                    kind=kind,
                    gameweek_number=gameweek_number,
                    manager_id=entry[0],
                    manager_name=manager_name,
                    team_name=team_name,
                    value=entry[1],
                )
            )
        return found

    async def _chip_misfire(self, gameweek_number: int) -> list[Highlight]:
        """A chip spent for almost nothing.

        Four chips a half is the whole budget, so burning one on a blank is
        the kind of thing a league still brings up in May. Only the two chips
        with a number attached qualify: a Triple Captain is judged on what the
        armband returned, a Bench Boost on what the bench did. A Wildcard has
        no comparable figure, so it is left alone rather than guessed at.
        """

        rows = await self.session.execute(
            select(
                Manager.id,
                Manager.manager_name,
                Manager.team_name,
                ManagerGameweekScore.chip_used,
                ManagerGameweekScore.captain_points,
                ManagerGameweekScore.bench_points,
                ManagerGameweekScore.score_status,
            )
            .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(
                Gameweek.season_id == self.season_id,
                Gameweek.number == gameweek_number,
                ManagerGameweekScore.chip_used.in_(CHIPS_WITH_A_RETURN),
                *self._eligible(),
            )
        )

        worst: Highlight | None = None
        for manager_id, manager_name, team_name, chip, captain, bench, status in rows:
            returned = captain if chip == "3xc" else bench
            if returned is None or returned > CHIP_MISFIRE_CEILING[chip]:
                continue
            if worst is not None and returned >= worst.value:
                continue
            worst = Highlight(
                kind=HighlightKind.CHIP_MISFIRE,
                gameweek_number=gameweek_number,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=returned,
                is_provisional=status is not ScoreState.FINAL,
                detail=chip,
            )
        return [worst] if worst else []

    async def _captain_blank(self, gameweek_number: int) -> list[Highlight]:
        """The armband on someone who did not turn up.

        The page already celebrates the best captain of the week; without its
        opposite the story is only half told, and the half nobody relates to.
        """

        row = (
            await self.session.execute(
                select(
                    Manager.id,
                    Manager.manager_name,
                    Manager.team_name,
                    ManagerGameweekScore.captain_points,
                    ManagerGameweekScore.score_status,
                )
                .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
                .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                .where(
                    Gameweek.season_id == self.season_id,
                    Gameweek.number == gameweek_number,
                    ManagerGameweekScore.captain_points <= CAPTAIN_BLANK_CEILING,
                    *self._eligible(),
                )
                .order_by(ManagerGameweekScore.captain_points, Manager.id)
                .limit(1)
            )
        ).first()
        if row is None:
            return []
        manager_id, manager_name, team_name, points, status = row
        return [
            Highlight(
                kind=HighlightKind.CAPTAIN_BLANK,
                gameweek_number=gameweek_number,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=points,
                is_provisional=status is not ScoreState.FINAL,
            )
        ]

    async def _season_high(self) -> list[Highlight]:
        row = (
            await self.session.execute(
                select(
                    Manager.id,
                    Manager.manager_name,
                    Manager.team_name,
                    ManagerGameweekScore.net_points,
                    Gameweek.number,
                    ManagerGameweekScore.score_status,
                )
                .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
                .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                .where(Gameweek.season_id == self.season_id, *self._eligible())
                .order_by(ManagerGameweekScore.net_points.desc(), Gameweek.number, Manager.id)
                .limit(1)
            )
        ).first()
        if row is None:
            return []
        manager_id, manager_name, team_name, net_points, gameweek_number, status = row
        return [
            Highlight(
                kind=HighlightKind.SEASON_HIGH,
                gameweek_number=gameweek_number,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=net_points,
                is_provisional=status is not ScoreState.FINAL,
            )
        ]

    async def _totw_leader(self) -> list[Highlight]:
        awards = func.count(ManagerGameweekScore.id).label("awards")
        row = (
            await self.session.execute(
                select(Manager.id, Manager.manager_name, Manager.team_name, awards)
                .join(ManagerGameweekScore, ManagerGameweekScore.manager_id == Manager.id)
                .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                .where(
                    Gameweek.season_id == self.season_id,
                    ManagerGameweekScore.is_totw.is_(True),
                    *self._eligible(),
                )
                .group_by(Manager.id, Manager.manager_name, Manager.team_name)
                .order_by(awards.desc(), Manager.id)
                .limit(1)
            )
        ).first()
        # One award is simply this week's winner, already on the page above.
        if row is None or row[3] < 2:
            return []
        manager_id, manager_name, team_name, count = row
        return [
            Highlight(
                kind=HighlightKind.TOTW_LEADER,
                gameweek_number=None,
                manager_id=manager_id,
                manager_name=manager_name,
                team_name=team_name,
                value=count,
            )
        ]
