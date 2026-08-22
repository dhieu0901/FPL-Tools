"""What the league as a whole did with a Gameweek.

Every other view answers a question about one manager or one tie. This one
answers questions about the forty-six: who they trusted with the armband and
what they have spent their chips on. Both are decisions rather than outcomes,
which is why they are worth showing separately from any score.

The division filter is the point. A HIGH manager comparing himself to the
whole league is comparing himself to two different competitions at once, and
the answer he wants is usually "what did my own division do".
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.errors import NotFoundError
from vmf_api.domain.chips import CHIPS_PER_HALF
from vmf_api.models.competition import Gameweek, Season
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus
from vmf_api.models.ingestion import (
    FplPlayer,
    FplTeam,
    ManagerPickItem,
    ManagerPickSnapshot,
)
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore


@dataclass(frozen=True, slots=True)
class CaptainPick:
    element_id: int
    web_name: str | None
    club: str | None
    #: How many managers gave this player the armband.
    count: int


@dataclass(frozen=True, slots=True)
class ChipUse:
    chip: str
    #: Managers who played it in the Gameweek being reported.
    this_gameweek: int
    #: Managers who have played it at any point this season.
    this_season: int


@dataclass(frozen=True, slots=True)
class LeagueStats:
    gameweek_number: int
    division: str
    #: The pool every share on this page is out of.
    managers: int
    #: Managers whose squad has been published, which is what the captain
    #: figures are actually drawn from.
    squads_known: int
    captains: tuple[CaptainPick, ...]
    chips: tuple[ChipUse, ...]


class StatsService:
    def __init__(self, session: AsyncSession, *, season_id: int) -> None:
        self.session = session
        self.season_id = season_id

    async def league(
        self,
        *,
        gameweek_number: int | None = None,
        division: Division | None = None,
    ) -> LeagueStats:
        gameweek = await self._gameweek(gameweek_number)
        managers = await self._managers(division)
        if not managers:
            return LeagueStats(
                gameweek_number=gameweek,
                division=division.value if division else "ALL",
                managers=0,
                squads_known=0,
                captains=(),
                chips=(),
            )

        captains, squads_known = await self._captains(gameweek, list(managers))
        chips = await self._chips(gameweek, list(managers))
        return LeagueStats(
            gameweek_number=gameweek,
            division=division.value if division else "ALL",
            managers=len(managers),
            squads_known=squads_known,
            captains=captains,
            chips=chips,
        )

    async def _gameweek(self, requested: int | None) -> int:
        if requested is not None:
            return requested
        # Whatever has been scored most recently is what a reader means by
        # "this Gameweek"; before anything is scored, the season's first.
        latest = await self.session.scalar(
            select(func.max(Gameweek.number))
            .select_from(ManagerGameweekScore)
            .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
            .where(Gameweek.season_id == self.season_id)
        )
        if latest is not None:
            return int(latest)
        first = await self.session.scalar(
            select(func.min(Gameweek.number)).where(Gameweek.season_id == self.season_id)
        )
        if first is None:
            raise NotFoundError(f"season {self.season_id} has no gameweeks")
        return int(first)

    async def _managers(self, division: Division | None) -> set[int]:
        query = select(Manager.id).where(
            Manager.registration_status == RegistrationStatus.CONFIRMED,
            Manager.active_status.not_in([ManagerStatus.DELETED, ManagerStatus.REMOVED]),
        )
        if division is not None:
            query = query.where(Manager.division == division)
        return set(await self.session.scalars(query))

    async def _captains(
        self,
        gameweek_number: int,
        manager_ids: list[int],
    ) -> tuple[tuple[CaptainPick, ...], int]:
        """Who wore the armband, counted over the newest squad of each manager.

        This is the armband as chosen, not as it ended up. If a captain does
        not appear the vice takes over for scoring, but the decision a reader
        is looking at here is the one the manager made before the deadline.
        """

        latest = (
            select(
                ManagerPickSnapshot.manager_id.label("manager_id"),
                func.max(ManagerPickSnapshot.revision).label("revision"),
            )
            .where(
                ManagerPickSnapshot.gameweek_number == gameweek_number,
                ManagerPickSnapshot.manager_id.in_(manager_ids),
            )
            .group_by(ManagerPickSnapshot.manager_id)
            .subquery()
        )
        rows = await self.session.execute(
            select(
                ManagerPickItem.element_id,
                FplPlayer.web_name,
                FplTeam.short_name,
                func.count().label("picks"),
            )
            .select_from(ManagerPickSnapshot)
            .join(
                latest,
                (ManagerPickSnapshot.manager_id == latest.c.manager_id)
                & (ManagerPickSnapshot.revision == latest.c.revision),
            )
            .join(ManagerPickItem, ManagerPickItem.snapshot_id == ManagerPickSnapshot.id)
            .outerjoin(
                FplPlayer,
                (FplPlayer.element_id == ManagerPickItem.element_id)
                & (FplPlayer.season_id == self.season_id),
            )
            .outerjoin(
                FplTeam,
                (FplTeam.team_fpl_id == FplPlayer.team_fpl_id)
                & (FplTeam.season_id == FplPlayer.season_id),
            )
            .where(ManagerPickItem.is_captain.is_(True))
            .group_by(ManagerPickItem.element_id, FplPlayer.web_name, FplTeam.short_name)
            .order_by(func.count().desc(), ManagerPickItem.element_id)
        )
        picks = tuple(
            CaptainPick(element_id=element_id, web_name=name, club=club, count=count)
            for element_id, name, club, count in rows
        )
        return picks, sum(pick.count for pick in picks)

    async def _chips(self, gameweek_number: int, manager_ids: list[int]) -> tuple[ChipUse, ...]:
        this_week = dict(
            (
                await self.session.execute(
                    select(ManagerGameweekScore.chip_used, func.count())
                    .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                    .where(
                        Gameweek.season_id == self.season_id,
                        Gameweek.number == gameweek_number,
                        ManagerGameweekScore.chip_used.is_not(None),
                        ManagerGameweekScore.manager_id.in_(manager_ids),
                    )
                    .group_by(ManagerGameweekScore.chip_used)
                )
            ).all()
        )
        this_season = dict(
            (
                await self.session.execute(
                    select(ManagerGameweekScore.chip_used, func.count())
                    .join(Gameweek, Gameweek.id == ManagerGameweekScore.gameweek_id)
                    .where(
                        Gameweek.season_id == self.season_id,
                        ManagerGameweekScore.chip_used.is_not(None),
                        ManagerGameweekScore.manager_id.in_(manager_ids),
                    )
                    .group_by(ManagerGameweekScore.chip_used)
                )
            ).all()
        )

        # Every chip is listed, played or not: "nobody has burned a Wildcard
        # yet" is as much a fact about the league as the ones that have gone.
        known = list(CHIPS_PER_HALF)
        for chip in (*this_week, *this_season):
            if chip not in known:
                known.append(chip)
        return tuple(
            ChipUse(
                chip=chip,
                this_gameweek=int(this_week.get(chip, 0)),
                this_season=int(this_season.get(chip, 0)),
            )
            for chip in known
        )


async def season_id_for(session: AsyncSession, season_code: str) -> int:
    season = await session.scalar(select(Season).where(Season.fpl_season_code == season_code))
    if season is None:
        raise NotFoundError(f"season {season_code!r} not found")
    return season.id
