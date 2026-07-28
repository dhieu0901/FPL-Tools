"""Append-only storage of what FPL actually returned.

Every request attempt is recorded by ``(request_key, payload_hash)``. Receiving
the same payload again updates the observation counters instead of creating a
second logical revision, which is what makes a retried job idempotent.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vmf_api.integrations.fpl_parsers import CONTRACT_VERSION, PARSER_VERSION
from vmf_api.models.ingestion import RawFplResponse


@dataclass(frozen=True, slots=True)
class RawRecord:
    row: RawFplResponse
    payload_changed: bool


def payload_digest(payload: object) -> tuple[str, int]:
    """Return the canonical sha256 digest and byte size of a JSON payload."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), len(encoded)


def naive_utc(value: datetime) -> datetime:
    """Normalize to UTC and drop the offset to match the schema's columns."""

    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


async def record_raw_response(
    session: AsyncSession,
    *,
    endpoint_name: str,
    request_key: str,
    payload: object,
    observed_at: datetime,
    http_status: int = 200,
    season_code: str | None = None,
    gameweek_number: int | None = None,
    fpl_entry_id: int | None = None,
    correlation_id: str | None = None,
    persist_payload: bool = False,
) -> RawRecord:
    """Store or re-observe one FPL response.

    ``persist_payload`` is reserved for small manager-scoped evidence. Shared
    multi-megabyte payloads are kept by hash only so the database stays inside
    the free-tier storage quota while still proving what was received.
    """

    payload_hash, payload_bytes = payload_digest(payload)
    seen_at = naive_utc(observed_at)
    existing = await session.scalar(
        select(RawFplResponse).where(
            RawFplResponse.request_key == request_key,
            RawFplResponse.payload_hash == payload_hash,
        )
    )
    if existing is not None:
        existing.last_seen_at = seen_at
        existing.seen_count += 1
        if persist_payload and existing.payload_json is None:
            existing.payload_json = payload
        return RawRecord(row=existing, payload_changed=False)

    row = RawFplResponse(
        endpoint_name=endpoint_name,
        request_key=request_key,
        season_code=season_code,
        gameweek_number=gameweek_number,
        fpl_entry_id=fpl_entry_id,
        http_status=http_status,
        payload_hash=payload_hash,
        payload_bytes=payload_bytes,
        payload_json=payload if persist_payload else None,
        contract_version=CONTRACT_VERSION,
        parser_version=PARSER_VERSION,
        correlation_id=correlation_id,
        first_seen_at=seen_at,
        last_seen_at=seen_at,
        seen_count=1,
    )
    session.add(row)
    await session.flush()
    return RawRecord(row=row, payload_changed=True)
