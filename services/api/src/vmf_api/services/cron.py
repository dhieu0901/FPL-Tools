from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import Lock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ASCII "VMFPROBE" represented as a signed-safe PostgreSQL bigint.
FPL_PROBE_LOCK_ID = 0x564D4650524F4245
_local_fpl_probe_lock = Lock()


@asynccontextmanager
async def fpl_probe_lock(session: AsyncSession) -> AsyncIterator[bool]:
    """Prevent overlapping probes without introducing a lock table.

    PostgreSQL uses a transaction-scoped advisory lock, which works across
    concurrent Vercel instances. SQLite uses an in-process lock for local
    development and tests only.
    """

    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        acquired = bool(
            await session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": FPL_PROBE_LOCK_ID},
            )
        )
        try:
            yield acquired
        finally:
            # The endpoint is deliberately read-only. Rolling back closes the
            # transaction and releases pg_try_advisory_xact_lock.
            if session.in_transaction():
                await session.rollback()
        return

    acquired = _local_fpl_probe_lock.acquire(blocking=False)
    if not acquired:
        yield False
        return

    try:
        yield True
    finally:
        _local_fpl_probe_lock.release()
