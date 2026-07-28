import pytest
from fastapi import HTTPException

from vmf_api.api.deps import require_admin
from vmf_api.core.config import Settings


@pytest.mark.asyncio
async def test_admin_auth_fails_closed_without_configured_key() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        database_url="sqlite+aiosqlite:///:memory:",
        admin_api_key=None,
    )

    with pytest.raises(HTTPException) as error:
        await require_admin(settings, x_admin_key=None, x_admin_actor="tester")

    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_admin_auth_rejects_wrong_key_and_accepts_exact_key() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        admin_api_key="correct-admin-key-that-is-at-least-32",
    )

    with pytest.raises(HTTPException) as error:
        await require_admin(settings, x_admin_key="wrong", x_admin_actor="tester")
    assert error.value.status_code == 401

    actor = await require_admin(
        settings,
        x_admin_key="correct-admin-key-that-is-at-least-32",
        x_admin_actor="tester",
    )
    assert actor == "tester"
