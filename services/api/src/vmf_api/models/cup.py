from __future__ import annotations

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from vmf_api.db.base import Base, TimestampMixin
from vmf_api.domain.cup import CupTieBreakStep
from vmf_api.models.enums import MatchStatus


class CupCompetition(TimestampMixin, Base):
    __tablename__ = "cup_competitions"
    __table_args__ = (UniqueConstraint("season_id", "season_half"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    season_half: Mapped[int] = mapped_column(Integer, nullable=False)
    qualification_end_gameweek: Mapped[int] = mapped_column(Integer, nullable=False)


class CupRound(TimestampMixin, Base):
    __tablename__ = "cup_rounds"
    __table_args__ = (UniqueConstraint("cup_competition_id", "round_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cup_competition_id: Mapped[int] = mapped_column(
        ForeignKey("cup_competitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(48), nullable=False)
    round_order: Mapped[int] = mapped_column(Integer, nullable=False)
    gameweek_number: Mapped[int] = mapped_column(Integer, nullable=False)
    has_third_place_match: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CupMatch(TimestampMixin, Base):
    __tablename__ = "cup_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cup_round_id: Mapped[int] = mapped_column(
        ForeignKey("cup_rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    manager_a_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"))
    manager_b_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"))
    manager_a_score: Mapped[int | None] = mapped_column(Integer)
    manager_b_score: Mapped[int | None] = mapped_column(Integer)
    winner_manager_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"))
    tie_break_step_used: Mapped[CupTieBreakStep | None] = mapped_column(
        Enum(CupTieBreakStep, name="cup_tie_break_step", native_enum=False, length=24)
    )
    random_draw_result: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="cup_match_status", native_enum=False, length=16),
        default=MatchStatus.SCHEDULED,
        nullable=False,
    )
    is_third_place_match: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
