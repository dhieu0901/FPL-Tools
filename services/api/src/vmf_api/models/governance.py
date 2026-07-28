from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from vmf_api.db.base import Base, TimestampMixin
from vmf_api.domain.violations import ThresholdAction, ViolationStatus
from vmf_api.models.enums import DecisionType, ViolationType


class Violation(TimestampMixin, Base):
    __tablename__ = "violations"
    # Detection re-runs on every tick, so one Gameweek can raise one violation
    # of a given type and no more; a corrected FPL figure updates that row.
    __table_args__ = (UniqueConstraint("manager_id", "gameweek_number", "violation_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gameweek_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    violation_type: Mapped[ViolationType] = mapped_column(
        Enum(ViolationType, name="violation_type", native_enum=False, length=24),
        nullable=False,
    )
    detected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[ViolationStatus] = mapped_column(
        Enum(ViolationStatus, name="violation_status", native_enum=False, length=24),
        default=ViolationStatus.DETECTED,
        nullable=False,
    )
    admin_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None]


class ViolationThresholdAction(TimestampMixin, Base):
    """One consequence applied once to one manager.

    The unique key is the mechanism behind "the same threshold action is never
    applied twice": re-running the disciplinary pass cannot add a second ``-6``
    to the H2H table, however many times a violation is reviewed.
    """

    __tablename__ = "violation_threshold_actions"
    __table_args__ = (UniqueConstraint("manager_id", "action"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[ThresholdAction] = mapped_column(
        Enum(ThresholdAction, name="threshold_action", native_enum=False, length=32),
        nullable=False,
    )
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    cumulative_count: Mapped[int] = mapped_column(Integer, nullable=False)
    triggering_violation_id: Mapped[int | None] = mapped_column(
        ForeignKey("violations.id", ondelete="SET NULL")
    )
    decision_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_decisions.id", ondelete="SET NULL")
    )


class AdminDecision(TimestampMixin, Base):
    __tablename__ = "admin_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_type: Mapped[DecisionType] = mapped_column(
        Enum(DecisionType, name="decision_type", native_enum=False, length=24),
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
