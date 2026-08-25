"""Close a Gameweek once FPL has finished with it, without waiting for a human.

Section 5.2 of the FPL contract forbids finalizing on the ``finished`` flag of a
single response: the gate also wants the live data, the squads and a schema in
good health. This module is that gate, and it is the rule half of the "rule or
administrator" wording - the league is not asked to press anything.

The gate never decides a result. It decides only that nothing is left to
arrive, so the figures it locks are the ones scoring has already derived. When
it refuses it says which condition refused, because a Gameweek that quietly
stays open stops the H2H table, the Cup and promotion from ever moving.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.models.competition import Gameweek
from vmf_api.models.enums import ManagerStatus, RegistrationStatus, SyncStatus
from vmf_api.models.ingestion import FplFixture, SyncRun
from vmf_api.models.manager import Manager
from vmf_api.models.scoring import ManagerGameweekScore

#: A manager in one of these states is still expected to hold a score, so a
#: Gameweek must not be closed while one of them is missing from the table.
EXPECTED_STATUSES = (
    ManagerStatus.ACTIVE,
    ManagerStatus.SUSPENDED,
    ManagerStatus.PENDING_REVIEW,
)


@dataclass(frozen=True, slots=True)
class FinalizationOutcome:
    gameweek_number: int
    finalized: bool = False
    already_final: bool = False
    blocked_by: str | None = None
    detail: dict[str, int] = field(default_factory=dict)


async def finalize_if_settled(
    session: AsyncSession,
    *,
    season_id: int,
    gameweek_number: int,
    unreconciled_manager_ids: Sequence[int] = (),
) -> FinalizationOutcome:
    """Close the Gameweek if every source agrees there is nothing left to come."""

    gameweek = await session.scalar(
        select(Gameweek).where(
            Gameweek.season_id == season_id,
            Gameweek.number == gameweek_number,
        )
    )
    if gameweek is None:
        return FinalizationOutcome(gameweek_number=gameweek_number, blocked_by="gameweek_not_found")
    if gameweek.is_finalized:
        return FinalizationOutcome(gameweek_number=gameweek_number, already_final=True)

    # FPL's own two flags, mirrored by every bootstrap sync. ``data_checked`` is
    # the one that matters: ``finished`` goes up when the last match ends, but
    # bonus points are still being applied, and a score locked before them is
    # wrong by up to three points a player.
    if not gameweek.fpl_finished or not gameweek.fpl_data_checked:
        return FinalizationOutcome(
            gameweek_number=gameweek_number,
            blocked_by="fpl_has_not_checked_the_data",
        )

    fixtures = list(
        await session.execute(
            select(FplFixture.is_played_out).where(
                FplFixture.season_id == season_id,
                FplFixture.gameweek_number == gameweek_number,
            )
        )
    )
    if not fixtures:
        return FinalizationOutcome(gameweek_number=gameweek_number, blocked_by="no_fixtures")
    if not all(row.is_played_out for row in fixtures):
        return FinalizationOutcome(
            gameweek_number=gameweek_number,
            blocked_by="a_fixture_is_still_open",
        )

    # A Gameweek closed while a manager is missing would fix his absence as a
    # result. Every manager the league still expects a score from must have one.
    expected = set(
        await session.scalars(
            select(Manager.id).where(
                Manager.registration_status == RegistrationStatus.CONFIRMED,
                Manager.active_status.in_(EXPECTED_STATUSES),
            )
        )
    )
    scored = set(
        await session.scalars(
            select(ManagerGameweekScore.manager_id).where(
                ManagerGameweekScore.gameweek_id == gameweek.id
            )
        )
    )
    missing = expected - scored
    if missing:
        return FinalizationOutcome(
            gameweek_number=gameweek_number,
            blocked_by="a_manager_has_no_score",
            detail={"managers_missing_a_score": len(missing)},
        )

    # The derived total and FPL's published total have to agree. This is the
    # condition that catches a score which is merely old: a stale published
    # figure disagrees with the squad it is supposed to summarize, and a
    # disagreement is never something to lock.
    if unreconciled_manager_ids:
        return FinalizationOutcome(
            gameweek_number=gameweek_number,
            blocked_by="a_score_disagrees_with_fpl",
            detail={"unreconciled_managers": len(unreconciled_manager_ids)},
        )

    quarantined = await session.scalar(
        select(func.count())
        .select_from(SyncRun)
        .where(
            SyncRun.gameweek_number == gameweek_number,
            SyncRun.status == SyncStatus.QUARANTINED,
        )
    )
    if quarantined:
        return FinalizationOutcome(
            gameweek_number=gameweek_number,
            blocked_by="a_source_is_quarantined",
            detail={"quarantined_runs": int(quarantined)},
        )

    gameweek.is_finalized = True
    await session.flush()
    return FinalizationOutcome(
        gameweek_number=gameweek_number,
        finalized=True,
        detail={"managers_scored": len(scored), "fixtures": len(fixtures)},
    )
