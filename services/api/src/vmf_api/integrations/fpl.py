from __future__ import annotations

from typing import Any, Protocol

import httpx


class FPLClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        path: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.status_code = status_code


class FPLClient(Protocol):
    async def bootstrap(self) -> dict[str, Any]: ...

    async def fixtures(self) -> list[dict[str, Any]]: ...

    async def element_summary(self, element_id: int) -> dict[str, Any]: ...

    async def entry(self, entry_id: int) -> dict[str, Any]: ...

    async def entry_history(self, entry_id: int) -> dict[str, Any]: ...

    async def picks(self, entry_id: int, gameweek: int) -> dict[str, Any]: ...

    async def transfers(self, entry_id: int) -> list[dict[str, Any]]: ...

    async def league_standings(
        self,
        league_id: int,
        *,
        page: int = 1,
    ) -> dict[str, Any]: ...

    async def live(self, gameweek: int) -> dict[str, Any]: ...

    async def close(self) -> None: ...


class HttpFPLClient:
    """Thin adapter around FPL JSON endpoints.

    Domain and application services depend on ``FPLClient``, so endpoint or
    provider changes remain isolated here.
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 15.0,
        user_agent: str = "VMF-Fantasy-League/0.1",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout_seconds,
            headers={"Accept": "application/json", "User-Agent": user_agent},
            transport=transport,
        )

    async def _get(self, path: str) -> Any:
        try:
            response = await self._client.get(path.lstrip("/"))
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise FPLClientError(
                f"FPL returned HTTP {error.response.status_code}",
                path=path,
                status_code=error.response.status_code,
            ) from error
        except httpx.HTTPError as error:
            raise FPLClientError("FPL request failed", path=path) from error
        except ValueError as error:
            raise FPLClientError("FPL returned invalid JSON", path=path) from error

    async def bootstrap(self) -> dict[str, Any]:
        return await self._get("bootstrap-static/")

    async def fixtures(self) -> list[dict[str, Any]]:
        return await self._get("fixtures/")

    async def element_summary(self, element_id: int) -> dict[str, Any]:
        return await self._get(f"element-summary/{_positive_id(element_id, 'element_id')}/")

    async def entry(self, entry_id: int) -> dict[str, Any]:
        return await self._get(f"entry/{_positive_id(entry_id, 'entry_id')}/")

    async def entry_history(self, entry_id: int) -> dict[str, Any]:
        return await self._get(f"entry/{_positive_id(entry_id, 'entry_id')}/history/")

    async def picks(self, entry_id: int, gameweek: int) -> dict[str, Any]:
        return await self._get(
            f"entry/{_positive_id(entry_id, 'entry_id')}/"
            f"event/{_gameweek(gameweek)}/picks/"
        )

    async def transfers(self, entry_id: int) -> list[dict[str, Any]]:
        return await self._get(f"entry/{_positive_id(entry_id, 'entry_id')}/transfers/")

    async def league_standings(
        self,
        league_id: int,
        *,
        page: int = 1,
    ) -> dict[str, Any]:
        if page < 1:
            raise ValueError("page must be positive")
        return await self._get(
            f"leagues-classic/{_positive_id(league_id, 'league_id')}/standings/?page_standings={page}"
        )

    async def live(self, gameweek: int) -> dict[str, Any]:
        return await self._get(f"event/{_gameweek(gameweek)}/live/")

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> HttpFPLClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()


def _positive_id(value: int, field: str) -> int:
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _gameweek(value: int) -> int:
    if not 1 <= value <= 38:
        raise ValueError("gameweek must be between 1 and 38")
    return value
