from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.core.config import Settings, get_settings
from vmf_api.db.session import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def require_admin(
    settings: SettingsDep,
    x_admin_key: Annotated[str | None, Header()] = None,
    x_admin_actor: Annotated[str, Header()] = "admin",
) -> str:
    configured = settings.admin_api_key
    if configured is not None and x_admin_key != configured.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin credentials",
        )
    if settings.environment == "production" and configured is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="admin API key is not configured",
        )
    return x_admin_actor


AdminActorDep = Annotated[str, Depends(require_admin)]
