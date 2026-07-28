from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from vmf_api.integrations.fpl import FPLClient
from vmf_api.schemas.fpl import FPLGameweekState, FPLStatusResponse


class FPLStatusPayloadError(ValueError):
    """Raised when FPL metadata cannot be interpreted safely."""


async def fetch_fpl_status(client: FPLClient) -> FPLStatusResponse:
    """Read and interpret official FPL state without persisting it."""

    observed_at = datetime.now(UTC)
    bootstrap, fixtures = await asyncio.gather(
        client.bootstrap(),
        client.fixtures(),
    )
    return derive_fpl_status(
        bootstrap=bootstrap,
        fixtures=fixtures,
        observed_at=observed_at,
    )


def derive_fpl_status(
    *,
    bootstrap: object,
    fixtures: object,
    observed_at: datetime,
) -> FPLStatusResponse:
    if not isinstance(bootstrap, dict):
        raise FPLStatusPayloadError("bootstrap payload must be an object")

    events = bootstrap.get("events")
    if not isinstance(events, list):
        raise FPLStatusPayloadError("bootstrap events must be a list")
    if not isinstance(fixtures, list):
        raise FPLStatusPayloadError("fixtures payload must be a list")

    if not events:
        return FPLStatusResponse(
            gameweek_number=None,
            gameweek_name=None,
            state=FPLGameweekState.PRESEASON,
            deadline=None,
            completed_fixtures=0,
            total_fixtures=0,
            observed_at=observed_at,
        )

    normalized_events = [_event(item) for item in events]
    selected = _select_event(normalized_events)
    event_id = selected["id"]
    event_fixtures = [_fixture(item) for item in fixtures if _fixture_event(item) == event_id]

    total_fixtures = len(event_fixtures)
    completed_fixtures = sum(
        item.get("finished") is True or item.get("finished_provisional") is True
        for item in event_fixtures
    )
    state = _state(
        event=selected,
        all_events=normalized_events,
        fixtures=event_fixtures,
    )

    return FPLStatusResponse(
        gameweek_number=event_id,
        gameweek_name=_optional_string(selected.get("name"), field="event name"),
        state=state,
        deadline=_optional_datetime(selected.get("deadline_time")),
        completed_fixtures=completed_fixtures,
        total_fixtures=total_fixtures,
        observed_at=observed_at,
    )


def _event(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FPLStatusPayloadError("event entries must be objects")
    event_id = value.get("id")
    if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id <= 0:
        raise FPLStatusPayloadError("event id must be a positive integer")
    return value


def _fixture_event(value: object) -> int | None:
    if not isinstance(value, dict):
        raise FPLStatusPayloadError("fixture entries must be objects")
    event_id = value.get("event")
    if event_id is None:
        return None
    if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id <= 0:
        raise FPLStatusPayloadError("fixture event must be a positive integer or null")
    return event_id


def _fixture(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FPLStatusPayloadError("fixture entries must be objects")
    return value


def _select_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    current = [event for event in events if event.get("is_current") is True]
    if len(current) > 1:
        raise FPLStatusPayloadError("multiple events are marked current")
    if current:
        return current[0]

    upcoming = [event for event in events if event.get("is_next") is True]
    if len(upcoming) > 1:
        raise FPLStatusPayloadError("multiple events are marked next")
    if upcoming:
        return upcoming[0]

    # FPL clears current/next after the season. Selecting the latest event
    # keeps the endpoint useful while its official ``finished`` flag remains
    # the only authority for whether that event is final.
    return max(events, key=lambda event: event["id"])


def _state(
    *,
    event: dict[str, Any],
    all_events: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
) -> FPLGameweekState:
    if event.get("finished") is True:
        return FPLGameweekState.FINAL

    all_finished_provisionally = bool(fixtures) and all(
        fixture.get("finished") is True or fixture.get("finished_provisional") is True
        for fixture in fixtures
    )
    if all_finished_provisionally:
        return FPLGameweekState.PROVISIONAL

    if any(fixture.get("started") is True for fixture in fixtures):
        return FPLGameweekState.LIVE

    has_previous_event = any(
        other["id"] < event["id"]
        and (other.get("finished") is True or other.get("is_previous") is True)
        for other in all_events
    )
    if event["id"] == 1 and not has_previous_event:
        return FPLGameweekState.PRESEASON
    return FPLGameweekState.UPCOMING


def _optional_string(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FPLStatusPayloadError(f"{field} must be a string or null")
    return value


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FPLStatusPayloadError("event deadline_time must be an ISO timestamp or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise FPLStatusPayloadError(
            "event deadline_time must be an ISO timestamp or null"
        ) from error
    if parsed.tzinfo is None:
        raise FPLStatusPayloadError("event deadline_time must include a timezone")
    return parsed
