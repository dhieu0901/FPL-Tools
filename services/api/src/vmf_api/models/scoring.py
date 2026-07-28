from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vmf_api.db.base import Base, TimestampMixin
from vmf_api.domain.locked_scores import ScoreSource
from vmf_api.models.enums import ScoreState

if TYPE_CHECKING:
    from vmf_api.models.competition import Gameweek
    from vmf_api.models.manager import Manager


class ManagerGameweekScore(TimestampMixin, Base):
    __tablename__ = "manager_gameweek_scores"
    __table_args__ = (UniqueConstraint("manager_id", "gameweek_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("managers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gameweek_id: Mapped[int] = mapped_column(
        ForeignKey("gameweeks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gross_points: Mapped[int] = mapped_column(Integer, nullable=False)
    transfer_cost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    net_points: Mapped[int] = mapped_column(Integer, nullable=False)
    official_points: Mapped[int | None] = mapped_column(Integer)
    replacement_points: Mapped[int | None] = mapped_column(Integer)
    score_source: Mapped[ScoreSource] = mapped_column(
        Enum(ScoreSource, name="score_source", native_enum=False, length=24),
        default=ScoreSource.OFFICIAL,
        nullable=False,
    )
    replacement_average_raw: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    chip_used: Mapped[str | None] = mapped_column(String(32))
    captain_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    goals_counted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yellow_cards_counted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    red_cards_counted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bench_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_totw: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    score_status: Mapped[ScoreState] = mapped_column(
        Enum(ScoreState, name="score_state", native_enum=False, length=16),
        default=ScoreState.UPCOMING,
        nullable=False,
    )

    manager: Mapped[Manager] = relationship(back_populates="gameweek_scores")
    gameweek: Mapped[Gameweek] = relationship(back_populates="scores")
