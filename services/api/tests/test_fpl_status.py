from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from vmf_api.api.deps import get_fpl_client
from vmf_api.integrations.fpl import FPLClientError
from vmf_api.main import app
from vmf_api.schemas.fpl import FPLGameweekState
from vmf_api.services.fpl import FPLStatusPayloadError, derive_fpl_status

OBSERVED_AT = datetime(2026, 8, 15, 12, tzinfo=UTC)


def _event(
    event_id: int,
    *,
    current: bool = False,
    next_: bool = False,
    previous: bool = False,
    finished: bool = False,
) -> dict[str, Any]:
    deadline = datetime(2026, 8, 10, 10, tzinfo=UTC) + timedelta(days=event_id)
    return {
        "id": event_id,
        "name": f"Gameweek {event_id}",
        "deadline_time": deadline.isoformat().replace("+00:00", "Z"),
        "is_current": current,
        "is_next": next_,
        "is_previous": previous,
        "finished": finished,
    }


def test_status_uses_current_event_and_counts_only_its_fixtures() -> None:
    response = derive_fpl_status(
        bootstrap={
            "events": [
                _event(1, previous=True, finished=True),
                _event(2, current=True),
                _event(3, next_=True),
            ]
        },
        fixtures=[
            {"event": 1, "started": True, "finished": True},
            {"event": 2, "started": True, "finished": True},
            {"event": 2, "started": True, "finished": False},
            {"event": 3, "started": False, "finished": False},
            {"event": None, "started": False, "finished": False},
        ],
        observed_at=OBSERVED_AT,
    )

    assert response.gameweek_number == 2
    assert response.gameweek_name == "Gameweek 2"
    assert response.state is FPLGameweekState.LIVE
    assert response.deadline == datetime(2026, 8, 12, 10, tzinfo=UTC)
    assert response.completed_fixtures == 1
    assert response.total_fixtures == 2
    assert response.observed_at == OBSERVED_AT


@pytest.mark.parametrize(
    ("event", "fixtures", "expected_state"),
    [
        (
            _event(1, next_=True),
            [{"event": 1, "started": False, "finished": False}],
            FPLGameweekState.PRESEASON,
        ),
        (
            _event(2, next_=True),
            [{"event": 2, "started": False, "finished": False}],
            FPLGameweekState.UPCOMING,
        ),
        (
            _event(2, current=True),
            [
                {
                    "event": 2,
                    "started": True,
                    "finished": True,
                    "finished_provisional": True,
                },
                {
                    "event": 2,
                    "started": True,
                    "finished": False,
                    "finished_provisional": True,
                },
            ],
            FPLGameweekState.PROVISIONAL,
        ),
        (
            _event(38, finished=True),
            [{"event": 38, "started": True, "finished": True}],
            FPLGameweekState.FINAL,
        ),
    ],
)
def test_status_derives_each_official_gameweek_state(
    event: dict[str, Any],
    fixtures: list[dict[str, Any]],
    expected_state: FPLGameweekState,
) -> None:
    previous = (
        [_event(1, previous=True, finished=True)]
        if event["id"] > 1 and expected_state is not FPLGameweekState.FINAL
        else []
    )
    response = derive_fpl_status(
        bootstrap={"events": [*previous, event]},
        fixtures=fixtures,
        observed_at=OBSERVED_AT,
    )

    assert response.state is expected_state
    if expected_state is FPLGameweekState.PROVISIONAL:
        assert response.completed_fixtures == response.total_fixtures == 2


def test_status_handles_empty_preseason_payload() -> None:
    response = derive_fpl_status(
        bootstrap={"events": []},
        fixtures=[],
        observed_at=OBSERVED_AT,
    )

    assert response.model_dump() == {
        "gameweek_number": None,
        "gameweek_name": None,
        "state": FPLGameweekState.PRESEASON,
        "deadline": None,
        "completed_fixtures": 0,
        "total_fixtures": 0,
        "observed_at": OBSERVED_AT,
    }


def test_status_rejects_ambiguous_current_event() -> None:
    with pytest.raises(FPLStatusPayloadError, match="multiple events"):
        derive_fpl_status(
            bootstrap={"events": [_event(1, current=True), _event(2, current=True)]},
            fixtures=[],
            observed_at=OBSERVED_AT,
        )


class _FakeFPLClient:
    def __init__(
        self,
        *,
        bootstrap: object,
        fixtures: object,
        error: FPLClientError | None = None,
    ) -> None:
        self._bootstrap = bootstrap
        self._fixtures = fixtures
        self._error = error

    async def bootstrap(self) -> Any:
        if self._error is not None:
            raise self._error
        return self._bootstrap

    async def fixtures(self) -> Any:
        return self._fixtures


def _override_client(client: _FakeFPLClient) -> TestClient:
    async def override() -> AsyncIterator[_FakeFPLClient]:
        yield client

    app.dependency_overrides[get_fpl_client] = override
    return TestClient(app)


def test_public_status_endpoint_and_openapi_contract() -> None:
    fake = _FakeFPLClient(
        bootstrap={"events": [_event(1, current=True)]},
        fixtures=[{"event": 1, "started": True, "finished": False}],
    )
    try:
        with _override_client(fake) as client:
            response = client.get("/api/fpl/status")
            schema = client.get("/openapi.json").json()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "gameweek_number": 1,
        "gameweek_name": "Gameweek 1",
        "state": "live",
        "deadline": "2026-08-11T10:00:00Z",
        "completed_fixtures": 0,
        "total_fixtures": 1,
        "observed_at": response.json()["observed_at"],
    }
    operation = schema["paths"]["/api/fpl/status"]["get"]
    assert operation["tags"] == ["fpl"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/FPLStatusResponse"
    }


@pytest.mark.parametrize(
    "fake",
    [
        _FakeFPLClient(
            bootstrap={},
            fixtures=[],
        ),
        _FakeFPLClient(
            bootstrap={"events": []},
            fixtures=[],
            error=FPLClientError("secret upstream detail", path="bootstrap-static/"),
        ),
    ],
)
def test_public_status_endpoint_returns_generic_bad_gateway(fake: _FakeFPLClient) -> None:
    try:
        with _override_client(fake) as client:
            response = client.get("/api/fpl/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] in {
        "FPL upstream request failed",
        "FPL upstream response has an invalid payload",
    }
    assert "secret upstream detail" not in response.text
