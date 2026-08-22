from __future__ import annotations

import asyncio
import random
from typing import Any, Protocol

import httpx

#: Statuses worth another attempt inside the same tick. Everything else is a
#: contract or availability signal that retrying cannot fix.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


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

    async def h2h_matches(self, league_id: int, *, page: int = 1) -> dict[str, Any]: ...

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
        max_attempts: int = 3,
        retry_base_delay_seconds: float = 1.0,
        response_max_bytes: int = 16 * 1024 * 1024,
        sleep: Any = asyncio.sleep,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout_seconds,
            headers={"Accept": "application/json", "User-Agent": user_agent},
            transport=transport,
            # Redirects would let a changed route move the request off the
            # allowlisted host; a redirect is a contract change, not a success.
            follow_redirects=False,
        )
        self._max_attempts = max(1, max_attempts)
        self._retry_base_delay_seconds = max(0.0, retry_base_delay_seconds)
        self._response_max_bytes = response_max_bytes
        self._sleep = sleep

    async def _get(self, path: str) -> Any:
        for attempt in range(1, self._max_attempts + 1):
            try:
                return await self._attempt(path)
            except FPLClientError as error:
                retryable = error.status_code is None or error.status_code in RETRYABLE_STATUS_CODES
                if not retryable or attempt == self._max_attempts:
                    raise
            # Exponential backoff with jitter keeps a shared outage from turning
            # into a synchronized burst across managers.
            delay = self._retry_base_delay_seconds * (3 ** (attempt - 1))
            await self._sleep(delay + random.uniform(0, self._retry_base_delay_seconds))
        raise AssertionError("unreachable")  # pragma: no cover

    async def _attempt(self, path: str) -> Any:
        try:
            response = await self._client.get(path.lstrip("/"))
        except httpx.HTTPError as error:
            raise FPLClientError("FPL request failed", path=path) from error

        if response.status_code != httpx.codes.OK:
            raise FPLClientError(
                f"FPL returned HTTP {response.status_code}",
                path=path,
                status_code=response.status_code,
            )
        if len(response.content) > self._response_max_bytes:
            raise FPLClientError(
                f"FPL response exceeded {self._response_max_bytes} bytes",
                path=path,
                status_code=response.status_code,
            )
        try:
            return response.json()
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
            f"entry/{_positive_id(entry_id, 'entry_id')}/event/{_gameweek(gameweek)}/picks/"
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

    async def h2h_matches(self, league_id: int, *, page: int = 1) -> dict[str, Any]:
        """One page of the fixture list FPL drew for a head-to-head league.

        The draw does not exist until the league closes at the first deadline,
        so before then this answers with an empty page rather than an error.
        """

        if page < 1:
            raise ValueError("page must be positive")
        return await self._get(
            f"leagues-h2h-matches/league/{_positive_id(league_id, 'league_id')}/?page={page}"
        )

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
