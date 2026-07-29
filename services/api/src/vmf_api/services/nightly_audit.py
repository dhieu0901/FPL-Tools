"""A nightly pass over what the five-minute sync deliberately does not touch.

The frequent job compares field by field, so a player moving club or arriving
from another league is already picked up within one tick. What it never
revisits is the manager's own FPL entry, which is read once at import.

That matters because the league forbids changing a team name mid-season. A
rule nobody checks is not a rule, so this reads each entry again and records
what FPL currently shows. It never rewrites the registered name: the name a
manager competes under is a league record, and a mismatch is evidence for an
administrator rather than something to silently accept.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.integrations.fpl import FPLClient, FPLClientError
from vmf_api.integrations.fpl_parsers import SchemaQuarantineError, parse_entry
from vmf_api.models.enums import ManagerStatus, RegistrationStatus
from vmf_api.models.manager import Manager, ManagerExternalProfile


@dataclass(frozen=True, slots=True)
class RenamedTeam:
    manager_id: int
    fpl_entry_id: int
    registered_team_name: str
    current_team_name: str


@dataclass(frozen=True, slots=True)
class AuditOutcome:
    checked: int = 0
    profiles_created: int = 0
    profiles_updated: int = 0
    unreachable: tuple[int, ...] = ()
    renamed: tuple[RenamedTeam, ...] = field(default=())
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def rename_count(self) -> int:
        return len(self.renamed)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class NightlyAuditService:
    def __init__(
        self,
        session: AsyncSession,
        client: FPLClient,
        *,
        max_concurrency: int = 4,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.session = session
        self.client = client
        self.clock = clock
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))

    async def run(self, *, manager_limit: int | None = None) -> AuditOutcome:
        started_at = self.clock()
        managers = await self._managers(limit=manager_limit)
        if not managers:
            return AuditOutcome(started_at=started_at, finished_at=self.clock())

        profiles = {
            profile.manager_id: profile
            for profile in await self.session.scalars(
                select(ManagerExternalProfile).where(
                    ManagerExternalProfile.manager_id.in_([m.id for m in managers])
                )
            )
        }

        results = await asyncio.gather(
            *(self._read_entry(manager) for manager in managers),
            return_exceptions=False,
        )

        created = 0
        updated = 0
        unreachable: list[int] = []
        renamed: list[RenamedTeam] = []

        for manager, parsed in zip(managers, results, strict=True):
            if parsed is None:
                unreachable.append(manager.id)
                continue

            current_team = parsed.team_name
            # The registered name is the league record; only the observation of
            # FPL's current name moves.
            changed = bool(current_team and current_team != manager.team_name)
            if changed and current_team is not None:
                renamed.append(
                    RenamedTeam(
                        manager_id=manager.id,
                        fpl_entry_id=manager.fpl_entry_id,
                        registered_team_name=manager.team_name,
                        current_team_name=current_team,
                    )
                )

            profile = profiles.get(manager.id)
            if profile is None:
                self.session.add(
                    ManagerExternalProfile(
                        manager_id=manager.id,
                        current_manager_name=parsed.manager_name,
                        current_team_name=current_team,
                        team_name_changed=changed,
                    )
                )
                created += 1
                continue

            if (
                profile.current_manager_name != parsed.manager_name
                or profile.current_team_name != current_team
                or profile.team_name_changed != changed
            ):
                profile.current_manager_name = parsed.manager_name
                profile.current_team_name = current_team
                profile.team_name_changed = changed
                updated += 1

        await self.session.flush()
        return AuditOutcome(
            checked=len(managers) - len(unreachable),
            profiles_created=created,
            profiles_updated=updated,
            unreachable=tuple(unreachable),
            renamed=tuple(renamed),
            started_at=started_at,
            finished_at=self.clock(),
        )

    async def _read_entry(self, manager: Manager) -> object | None:
        """Return the parsed entry, or ``None`` when FPL cannot be read.

        One unreadable entry must not abandon the other thirty-nine: this is a
        report, so a partial answer with the gaps named is more useful than no
        answer at all.
        """

        async with self._semaphore:
            try:
                payload = await self.client.entry(manager.fpl_entry_id)
                return parse_entry(payload)
            except (FPLClientError, SchemaQuarantineError):
                return None

    async def _managers(self, *, limit: int | None) -> Sequence[Manager]:
        statement = (
            select(Manager)
            .where(
                Manager.registration_status == RegistrationStatus.CONFIRMED,
                Manager.active_status.notin_([ManagerStatus.DELETED, ManagerStatus.REMOVED]),
            )
            .order_by(Manager.id)
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(await self.session.scalars(statement))
