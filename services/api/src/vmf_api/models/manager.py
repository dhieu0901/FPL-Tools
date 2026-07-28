from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, BigInteger, Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vmf_api.db.base import Base, TimestampMixin
from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus

if TYPE_CHECKING:
    from vmf_api.models.competition import DivisionMembership
    from vmf_api.models.scoring import ManagerGameweekScore


class Manager(TimestampMixin, Base):
    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fpl_entry_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    manager_name: Mapped[str] = mapped_column(String(120), nullable=False)
    team_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(32))
    facebook_url: Mapped[str | None] = mapped_column(Text)
    division: Mapped[Division] = mapped_column(
        Enum(Division, name="division", native_enum=False, length=8),
        index=True,
        nullable=False,
    )
    active_status: Mapped[ManagerStatus] = mapped_column(
        Enum(ManagerStatus, name="manager_status", native_enum=False, length=24),
        default=ManagerStatus.ACTIVE,
        nullable=False,
    )
    registration_status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, name="registration_status", native_enum=False, length=16),
        default=RegistrationStatus.PENDING,
        nullable=False,
    )
    season_joined: Mapped[str] = mapped_column(String(16), nullable=False)
    locked_from_gameweek: Mapped[int | None] = mapped_column(Integer)
    season_2_league_joined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    season_2_join_gameweek: Mapped[int | None] = mapped_column(Integer)
    join_violation_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    external_profile: Mapped[ManagerExternalProfile | None] = relationship(
        back_populates="manager",
        cascade="all, delete-orphan",
        uselist=False,
    )
    memberships: Mapped[list[DivisionMembership]] = relationship(back_populates="manager")
    gameweek_scores: Mapped[list[ManagerGameweekScore]] = relationship(back_populates="manager")


class ManagerExternalProfile(TimestampMixin, Base):
    __tablename__ = "manager_external_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    current_manager_name: Mapped[str | None] = mapped_column(String(120))
    current_team_name: Mapped[str | None] = mapped_column(String(120))
    team_name_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    manager: Mapped[Manager] = relationship(back_populates="external_profile")
