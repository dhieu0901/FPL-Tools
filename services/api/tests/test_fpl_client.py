import asyncio

import httpx
import pytest

from vmf_api.integrations.fpl import FPLClientError, HttpFPLClient


def test_fpl_client_uses_expected_public_json_paths() -> None:
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(str(request.url))
        return httpx.Response(200, json={"ok": True})

    async def exercise_client() -> None:
        async with HttpFPLClient(
            base_url="https://fantasy.premierleague.com/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            await client.bootstrap()
            await client.fixtures()
            await client.element_summary(7)
            await client.entry(123)
            await client.entry_history(123)
            await client.picks(123, 4)
            await client.transfers(123)
            await client.live(4)
            await client.league_standings(456, page=2)

    asyncio.run(exercise_client())

    expected_suffixes = [
        "/api/bootstrap-static/",
        "/api/fixtures/",
        "/api/element-summary/7/",
        "/api/entry/123/",
        "/api/entry/123/history/",
        "/api/entry/123/event/4/picks/",
        "/api/entry/123/transfers/",
        "/api/event/4/live/",
        "/api/leagues-classic/456/standings/?page_standings=2",
    ]
    assert all(
        url.endswith(suffix) for url, suffix in zip(seen_paths, expected_suffixes, strict=True)
    )


def test_fpl_client_wraps_status_errors_without_leaking_response_body() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(503, text="upstream secret"))

    async def exercise_client() -> FPLClientError:
        async with HttpFPLClient(
            base_url="https://example.test/api",
            transport=transport,
        ) as client:
            with pytest.raises(FPLClientError) as captured:
                await client.bootstrap()
        return captured.value

    error = asyncio.run(exercise_client())
    assert error.status_code == 503
    assert error.path == "bootstrap-static/"
    assert "upstream secret" not in str(error)
