from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import Lock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ASCII "VMFPROBE" represented as a signed-safe PostgreSQL bigint.
FPL_PROBE_LOCK_ID = 0x564D4650524F4245
# ASCII "VMFSYNC0" for the job that writes source facts.
FPL_SYNC_LOCK_ID = 0x564D4653594E4330
# ASCII "VMFAUDIT" for the nightly pass over manager entries.
NIGHTLY_AUDIT_LOCK_ID = 0x564D4641554449

_local_locks: dict[int, Lock] = {
    FPL_PROBE_LOCK_ID: Lock(),
    FPL_SYNC_LOCK_ID: Lock(),
    NIGHTLY_AUDIT_LOCK_ID: Lock(),
}


@asynccontextmanager
async def advisory_lock(
    session: AsyncSession,
    lock_id: int,
    *,
    release_with_rollback: bool,
) -> AsyncIterator[bool]:
    """Prevent overlapping cron work without introducing a lock table.

    PostgreSQL uses a transaction-scoped advisory lock, which works across
    concurrent Vercel instances and is released when the caller commits or
    rolls back. SQLite uses an in-process lock for local development and tests.

    ``release_with_rollback`` suits read-only jobs, whose transaction can be
    discarded. A writing job must keep its transaction so its own commit both
    persists the work and releases the lock.
    """

    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        acquired = bool(
            await session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": lock_id},
            )
        )
        try:
            yield acquired
        finally:
            if release_with_rollback and session.in_transaction():
                await session.rollback()
        return

    local_lock = _local_locks.setdefault(lock_id, Lock())
    acquired = local_lock.acquire(blocking=False)
    if not acquired:
        yield False
        return

    try:
        yield True
    finally:
        local_lock.release()


@asynccontextmanager
async def fpl_probe_lock(session: AsyncSession) -> AsyncIterator[bool]:
    """Guard the read-only FPL probe endpoint."""

    async with advisory_lock(
        session,
        FPL_PROBE_LOCK_ID,
        release_with_rollback=True,
    ) as acquired:
        yield acquired


@asynccontextmanager
async def fpl_sync_lock(session: AsyncSession) -> AsyncIterator[bool]:
    """Guard the synchronization job, which writes source facts."""

    async with advisory_lock(
        session,
        FPL_SYNC_LOCK_ID,
        release_with_rollback=False,
    ) as acquired:
        yield acquired


@asynccontextmanager
async def nightly_audit_lock(session: AsyncSession) -> AsyncIterator[bool]:
    """Guard the nightly audit, which writes observed manager profiles."""

    async with advisory_lock(
        session,
        NIGHTLY_AUDIT_LOCK_ID,
        release_with_rollback=False,
    ) as acquired:
        yield acquired
