import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from vmf_api.api.deps import get_fpl_client
from vmf_api.core.config import Settings, get_settings
from vmf_api.db.session import get_session
from vmf_api.main import app
from vmf_api.services.cron import fpl_probe_lock


class _Dialect:
    def __init__(self, name: str) -> None:
        self.name = name


class _Bind:
    def __init__(self, dialect_name: str) -> None:
        self.dialect = _Dialect(dialect_name)


class _FakeSession:
    def __init__(self, dialect_name: str = "sqlite", *, lock_acquired: bool = True) -> None:
        self._bind = _Bind(dialect_name)
        self._lock_acquired = lock_acquired
        self.rollback_count = 0

    def get_bind(self) -> _Bind:
        return self._bind

    async def scalar(self, *_: object, **__: object) -> bool:
        return self._lock_acquired

    def in_transaction(self) -> bool:
        return self._bind.dialect.name == "postgresql"

    async def rollback(self) -> None:
        self.rollback_count += 1


class _FakeFPLClient:
    async def bootstrap(self) -> dict[str, Any]:
        return {
            "events": [
                {"id": 1, "is_current": False, "is_next": False},
                {"id": 2, "is_current": True, "is_next": False},
            ],
            "teams": [{"id": 1}, {"id": 2}],
            "elements": [{"id": 10}, {"id": 11}, {"id": 12}],
        }

    async def fixtures(self) -> list[dict[str, Any]]:
        return [{"id": 100}]


TEST_CRON_SECRET = "test-cron-secret-that-is-at-least-32"


def _settings(secret: str | None = TEST_CRON_SECRET) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cron_secret=secret,
    )


async def _session_override() -> AsyncIterator[_FakeSession]:
    yield _FakeSession()


async def _client_override() -> AsyncIterator[_FakeFPLClient]:
    yield _FakeFPLClient()


def _test_client(settings: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_fpl_client] = _client_override
    return TestClient(app)


def test_cron_probe_requires_bearer_secret() -> None:
    with _test_client(_settings()) as client:
        response = client.post("/api/cron/fpl-probe")

    app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_cron_probe_fails_closed_when_secret_is_missing() -> None:
    with _test_client(_settings(None)) as client:
        response = client.post(
            "/api/cron/fpl-probe",
            headers={"Authorization": "Bearer anything"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 503


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_cron_probe_observes_metadata_without_persisting(method: str) -> None:
    with _test_client(_settings()) as client:
        response = client.request(
            method,
            "/api/cron/fpl-probe",
            headers={"Authorization": f"Bearer {TEST_CRON_SECRET}"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "status": "observed",
        "persisted": False,
        "observed_at": response.json()["observed_at"],
        "reason": None,
        "current_gameweek": 2,
        "event_count": 2,
        "team_count": 2,
        "player_count": 3,
        "fixture_count": 1,
    }


def test_local_probe_lock_skips_an_overlapping_invocation() -> None:
    async def exercise() -> tuple[bool, bool]:
        session = _FakeSession()
        async with fpl_probe_lock(session) as first:
            async with fpl_probe_lock(session) as second:
                return first, second

    assert asyncio.run(exercise()) == (True, False)


def test_postgres_probe_lock_is_transaction_scoped_and_rolled_back() -> None:
    async def exercise() -> tuple[bool, int]:
        session = _FakeSession("postgresql", lock_acquired=False)
        async with fpl_probe_lock(session) as acquired:
            assert not acquired
        return acquired, session.rollback_count

    assert asyncio.run(exercise()) == (False, 1)
