from __future__ import annotations

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from vmf_api.db.base import Base, TimestampMixin
from vmf_api.models.enums import MatchStatus


class H2HSchedule(TimestampMixin, Base):
    __tablename__ = "h2h_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class H2HMatch(TimestampMixin, Base):
    __tablename__ = "h2h_matches"
    __table_args__ = (
        UniqueConstraint("schedule_id", "gameweek_number", "home_manager_id"),
        UniqueConstraint("schedule_id", "gameweek_number", "away_manager_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("h2h_schedules.id", ondelete="CASCADE"),
        nullable=False,
    )
    gameweek_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    home_manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    away_manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    winner_manager_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"))
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="h2h_match_status", native_enum=False, length=16),
        default=MatchStatus.SCHEDULED,
        nullable=False,
    )
    walkover_reason: Mapped[str | None] = mapped_column(String(240))
    is_playoff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bracket_position: Mapped[str | None] = mapped_column(String(32))


class H2HPenalty(TimestampMixin, Base):
    __tablename__ = "h2h_penalties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    violation_id: Mapped[int | None] = mapped_column(ForeignKey("violations.id"))
    table_point_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(240), nullable=False)
