from __future__ import annotations

from collections.abc import AsyncIterator
from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.config import Settings, get_settings
from vmf_api.db.session import get_session
from vmf_api.integrations.fpl import FPLClient, HttpFPLClient

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def require_admin(
    settings: SettingsDep,
    x_admin_key: Annotated[str | None, Header()] = None,
    x_admin_actor: Annotated[str, Header()] = "admin",
) -> str:
    configured = settings.admin_api_key
    if configured is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="admin API key is not configured",
        )
    if x_admin_key is None or not compare_digest(
        x_admin_key.encode(),
        configured.get_secret_value().encode(),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin credentials",
        )
    return x_admin_actor


AdminActorDep = Annotated[str, Depends(require_admin)]


async def require_cron(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Fail closed unless the caller supplies the configured bearer secret."""

    configured = settings.cron_secret
    if configured is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="cron secret is not configured",
        )
    expected = f"Bearer {configured.get_secret_value()}"
    if authorization is None or not compare_digest(
        authorization.encode(),
        expected.encode(),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid cron credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


CronAuthorizationDep = Annotated[None, Depends(require_cron)]


async def get_fpl_client(settings: SettingsDep) -> AsyncIterator[FPLClient]:
    async with HttpFPLClient(
        base_url=settings.fpl_base_url,
        timeout_seconds=settings.fpl_timeout_seconds,
        user_agent=settings.fpl_user_agent,
        max_attempts=settings.fpl_max_attempts,
        retry_base_delay_seconds=settings.fpl_retry_base_delay_seconds,
        response_max_bytes=settings.fpl_response_max_bytes,
    ) as client:
        yield client


FPLClientDep = Annotated[FPLClient, Depends(get_fpl_client)]
