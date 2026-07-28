from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vmf_api.db.base import Base, TimestampMixin
from vmf_api.models.enums import Division, PhaseType, SeasonStatus

if TYPE_CHECKING:
    from vmf_api.models.manager import Manager
    from vmf_api.models.scoring import ManagerGameweekScore


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    fpl_season_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    start_gameweek: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    end_gameweek: Mapped[int] = mapped_column(Integer, default=38, nullable=False)
    status: Mapped[SeasonStatus] = mapped_column(
        Enum(SeasonStatus, name="season_status", native_enum=False, length=16),
        default=SeasonStatus.DRAFT,
        nullable=False,
    )

    gameweeks: Mapped[list[Gameweek]] = relationship(back_populates="season")
    phases: Mapped[list[CompetitionPhase]] = relationship(back_populates="season")


class Gameweek(TimestampMixin, Base):
    __tablename__ = "gameweeks"
    __table_args__ = (UniqueConstraint("season_id", "number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    season: Mapped[Season] = relationship(back_populates="gameweeks")
    scores: Mapped[list[ManagerGameweekScore]] = relationship(back_populates="gameweek")


class CompetitionPhase(TimestampMixin, Base):
    __tablename__ = "competition_phases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    phase_type: Mapped[PhaseType] = mapped_column(
        Enum(PhaseType, name="phase_type", native_enum=False, length=24),
        nullable=False,
    )
    start_gameweek: Mapped[int] = mapped_column(Integer, nullable=False)
    end_gameweek: Mapped[int] = mapped_column(Integer, nullable=False)

    season: Mapped[Season] = relationship(back_populates="phases")
    memberships: Mapped[list[DivisionMembership]] = relationship(back_populates="phase")


class DivisionMembership(TimestampMixin, Base):
    __tablename__ = "division_memberships"
    __table_args__ = (UniqueConstraint("manager_id", "competition_phase_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="CASCADE"),
        nullable=False,
    )
    competition_phase_id: Mapped[int] = mapped_column(
        ForeignKey("competition_phases.id", ondelete="CASCADE"),
        nullable=False,
    )
    division: Mapped[Division] = mapped_column(
        Enum(Division, name="membership_division", native_enum=False, length=8),
        nullable=False,
    )
    start_gameweek: Mapped[int] = mapped_column(Integer, nullable=False)
    end_gameweek: Mapped[int] = mapped_column(Integer, nullable=False)
    promotion_source: Mapped[str | None] = mapped_column(String(120))
    relegation_source: Mapped[str | None] = mapped_column(String(120))

    manager: Mapped[Manager] = relationship(back_populates="memberships")
    phase: Mapped[CompetitionPhase] = relationship(back_populates="memberships")
