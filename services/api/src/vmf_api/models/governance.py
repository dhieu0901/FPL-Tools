from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vmf_api.db.base import Base, TimestampMixin
from vmf_api.domain.violations import ViolationStatus
from vmf_api.models.enums import DecisionType, ViolationType


class Violation(TimestampMixin, Base):
    __tablename__ = "violations"

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
