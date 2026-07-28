import asyncio
from typing import Any

from sqlalchemy import text
from sqlalchemy.pool import NullPool

from vmf_api.core.config import Settings
from vmf_api.db import session as session_module


def test_serverless_engine_uses_null_pool_and_disables_prepared_statements(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}
    sentinel = object()

    def fake_create_async_engine(url: str, **options: object) -> object:
        captured["url"] = url
        captured.update(options)
        return sentinel

    monkeypatch.setattr(session_module, "create_async_engine", fake_create_async_engine)
    settings = Settings(
        _env_file=None,
        database_url="postgresql://runtime:secret@pooler.example:6543/postgres",
        database_use_null_pool=True,
        database_disable_prepared_statements=True,
    )

    engine = session_module.create_engine(settings)

    assert engine is sentinel
    assert captured["poolclass"] is NullPool
    assert captured["connect_args"] == {"prepare_threshold": None}


def test_sqlite_engine_keeps_local_driver_options_valid() -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite+aiosqlite:///:memory:",
    )

    engine = session_module.create_engine(settings)

    async def exercise() -> int:
        async with engine.connect() as connection:
            result = await connection.scalar(text("SELECT 1"))
        await engine.dispose()
        return int(result)

    assert asyncio.run(exercise()) == 1
