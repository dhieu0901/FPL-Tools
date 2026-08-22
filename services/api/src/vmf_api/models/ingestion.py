from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    or_,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import ColumnElement

from vmf_api.db.base import Base, TimestampMixin
from vmf_api.models.enums import SyncJobType, SyncStatus


class RawFplResponse(TimestampMixin, Base):
    """Evidence of what FPL returned, keyed by request and payload hash.

    Large shared payloads are recorded by hash only. ``payload_json`` is
    reserved for small manager-scoped evidence so the free-tier database is
    not filled by repeated multi-megabyte bootstrap and live snapshots.
    """

    __tablename__ = "raw_fpl_responses"
    __table_args__ = (UniqueConstraint("request_key", "payload_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint_name: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    request_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    season_code: Mapped[str | None] = mapped_column(String(16))
    gameweek_number: Mapped[int | None] = mapped_column(Integer)
    fpl_entry_id: Mapped[int | None] = mapped_column(BigInteger)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[Any | None] = mapped_column(JSON)
    contract_version: Mapped[str] = mapped_column(String(16), nullable=False)
    parser_version: Mapped[int] = mapped_column(Integer, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    first_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    seen_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class FplTeam(TimestampMixin, Base):
    __tablename__ = "fpl_teams"
    __table_args__ = (UniqueConstraint("season_id", "team_fpl_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_fpl_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    short_name: Mapped[str] = mapped_column(String(8), nullable=False)


class FplPlayer(TimestampMixin, Base):
    __tablename__ = "fpl_players"
    __table_args__ = (UniqueConstraint("season_id", "element_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    element_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    web_name: Mapped[str] = mapped_column(String(120), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    team_fpl_id: Mapped[int] = mapped_column(Integer, nullable=False)
    element_type: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str | None] = mapped_column(String(8))
    now_cost: Mapped[int | None] = mapped_column(Integer)


class FplFixture(TimestampMixin, Base):
    __tablename__ = "fpl_fixtures"
    __table_args__ = (UniqueConstraint("season_id", "fixture_fpl_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    fixture_fpl_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # FPL leaves ``event`` null while a postponed fixture is unscheduled.
    gameweek_number: Mapped[int | None] = mapped_column(Integer, index=True)
    kickoff_time: Mapped[datetime | None]
    started: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finished: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finished_provisional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    team_h_fpl_id: Mapped[int | None] = mapped_column(Integer)
    team_a_fpl_id: Mapped[int | None] = mapped_column(Integer)
    team_h_score: Mapped[int | None] = mapped_column(Integer)
    team_a_score: Mapped[int | None] = mapped_column(Integer)

    @hybrid_property
    def is_played_out(self) -> bool:
        """Whether the football is over, whatever FPL has confirmed since.

        FPL raises two flags and they mean different things. ``finished_
        provisional`` goes up at the final whistle; ``finished`` waits until
        bonus points are settled and the data is checked, which can be hours
        later. Reading only ``finished`` leaves a match that ended at 90
        minutes reporting as still in progress for the rest of the evening.

        Anything asking "is this player still on the pitch" wants this. Only
        something asking "can these points still change" wants ``finished``,
        because bonus does still land between the two.
        """

        return bool(self.finished or self.finished_provisional)

    @is_played_out.inplace.expression
    @classmethod
    def _is_played_out(cls) -> ColumnElement[bool]:
        return or_(cls.finished.is_(True), cls.finished_provisional.is_(True))


class FplPlayerFixtureStat(TimestampMixin, Base):
    """Player statistics at the source grain: one row per fixture.

    Keeping the fixture grain is what makes a Double Gameweek additive instead
    of overwritten, and lets a fixture that moves to another event be removed
    from the old aggregate.
    """

    __tablename__ = "fpl_player_fixture_stats"
    __table_args__ = (
        UniqueConstraint("season_id", "gameweek_number", "element_id", "fixture_fpl_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    gameweek_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    element_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fixture_fpl_id: Mapped[int] = mapped_column(Integer, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    goals_scored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    red_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_raw_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_fpl_responses.id", ondelete="SET NULL")
    )


class ManagerPickSnapshot(TimestampMixin, Base):
    """Immutable record of one manager's squad for one Gameweek revision."""

    __tablename__ = "manager_pick_snapshots"
    __table_args__ = (
        UniqueConstraint("manager_id", "gameweek_number", "revision"),
        UniqueConstraint("manager_id", "gameweek_number", "payload_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gameweek_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    active_chip: Mapped[str | None] = mapped_column(String(32))
    event_transfers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transfer_cost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gross_points: Mapped[int | None] = mapped_column(Integer)
    points_on_bench: Mapped[int | None] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(nullable=False)
    source_raw_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_fpl_responses.id", ondelete="SET NULL")
    )

    items: Mapped[list[ManagerPickItem]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )


class ManagerPickItem(TimestampMixin, Base):
    __tablename__ = "manager_pick_items"
    __table_args__ = (UniqueConstraint("snapshot_id", "element_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("manager_pick_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    element_id: Mapped[int] = mapped_column(Integer, nullable=False)
    squad_position: Mapped[int] = mapped_column(Integer, nullable=False)
    # The multiplier exactly as published in this revision. Revision 1 is the
    # deadline selection; later revisions carry FPL's auto-sub resolution.
    multiplier: Mapped[int] = mapped_column(Integer, nullable=False)
    is_captain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_vice_captain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_subbed_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_subbed_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    snapshot: Mapped[ManagerPickSnapshot] = relationship(back_populates="items")


class ManagerGameweekHistory(TimestampMixin, Base):
    """Official per-Gameweek entry history published by FPL.

    This is the authority for gross points and transfer cost; VMF never edits
    it, and derives ``official_net_points`` from it.
    """

    __tablename__ = "manager_gameweek_history"
    __table_args__ = (UniqueConstraint("manager_id", "gameweek_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gameweek_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    gross_points: Mapped[int] = mapped_column(Integer, nullable=False)
    total_points: Mapped[int | None] = mapped_column(Integer)
    event_transfers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transfer_cost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    points_on_bench: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    squad_value: Mapped[int | None] = mapped_column(Integer)
    bank: Mapped[int | None] = mapped_column(Integer)
    source_raw_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_fpl_responses.id", ondelete="SET NULL")
    )


class SyncRun(TimestampMixin, Base):
    """One attempt of one synchronization job, successful or not."""

    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[SyncJobType] = mapped_column(
        Enum(SyncJobType, name="sync_job_type", native_enum=False, length=24),
        nullable=False,
        index=True,
    )
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status", native_enum=False, length=16),
        nullable=False,
    )
    season_id: Mapped[int | None] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"))
    gameweek_number: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None]
    records_written: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detail: Mapped[Any | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(64))
