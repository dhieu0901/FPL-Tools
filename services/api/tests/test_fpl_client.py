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


def test_fpl_client_retries_a_transient_failure_then_succeeds() -> None:
    attempts: list[int] = []
    delays: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def exercise_client() -> object:
        async with HttpFPLClient(
            base_url="https://example.test/api",
            transport=httpx.MockTransport(handler),
            retry_base_delay_seconds=0.5,
            sleep=sleep,
        ) as client:
            return await client.bootstrap()

    assert asyncio.run(exercise_client()) == {"ok": True}
    assert len(attempts) == 3
    # Exponential backoff with jitter: 0.5-1.0 then 1.5-2.0 seconds.
    assert 0.5 <= delays[0] < 1.0 < delays[1] < 2.5


def test_fpl_client_does_not_retry_a_contract_error() -> None:
    attempts: list[int] = []

    def handler(_: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(404)

    async def exercise_client() -> FPLClientError:
        async with HttpFPLClient(
            base_url="https://example.test/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(FPLClientError) as captured:
                await client.picks(123, 4)
        return captured.value

    error = asyncio.run(exercise_client())
    assert error.status_code == 404
    assert len(attempts) == 1


def test_fpl_client_rejects_an_oversized_response() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"padding": "x" * 5_000}))

    async def exercise_client() -> FPLClientError:
        async with HttpFPLClient(
            base_url="https://example.test/api",
            transport=transport,
            response_max_bytes=1_000,
        ) as client:
            with pytest.raises(FPLClientError) as captured:
                await client.bootstrap()
        return captured.value

    assert "exceeded" in str(asyncio.run(exercise_client()))


def test_fpl_client_treats_a_redirect_as_a_contract_change() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(302, headers={"Location": "https://elsewhere.test/"})
    )

    async def exercise_client() -> FPLClientError:
        async with HttpFPLClient(
            base_url="https://example.test/api",
            transport=transport,
        ) as client:
            with pytest.raises(FPLClientError) as captured:
                await client.fixtures()
        return captured.value

    assert asyncio.run(exercise_client()).status_code == 302


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
