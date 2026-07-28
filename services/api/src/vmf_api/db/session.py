from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from vmf_api.core.config import Settings, get_settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create an engine suitable for either local or serverless execution."""

    engine_options: dict[str, object] = {
        "echo": settings.sql_echo,
        "pool_pre_ping": True,
    }
    if settings.database_use_null_pool:
        # Supavisor already owns the shared pool. Keeping another process-local
        # pool in an autoscaling function wastes scarce database connections.
        engine_options["poolclass"] = NullPool

    if (
        settings.database_url.startswith("postgresql+psycopg")
        and settings.database_disable_prepared_statements
    ):
        # Supavisor transaction mode cannot retain session-scoped prepared
        # statements. Psycopg 3 can disable automatic preparation completely.
        engine_options["connect_args"] = {"prepare_threshold": None}

    return create_async_engine(settings.database_url, **engine_options)


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    return create_engine(get_settings())


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session
