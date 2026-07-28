"""Make the disciplinary rules enforceable: unique violations and applied actions.

Revision ID: 20260729_0004
Revises: 20260728_0003
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0004"
down_revision: str | None = "20260728_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIOLATION_UNIQUE = "uq_violations_manager_gameweek_type"
THRESHOLD_UNIQUE = "uq_violation_threshold_actions_manager_action"


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    ]


def upgrade() -> None:
    # Detection runs on every cron tick. Without this key a retried tick would
    # raise the same Gameweek's violation again and inflate the count that
    # drives the thresholds.
    op.create_unique_constraint(
        VIOLATION_UNIQUE,
        "violations",
        ["manager_id", "gameweek_number", "violation_type"],
    )

    op.create_table(
        "violation_threshold_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("cumulative_count", sa.Integer(), nullable=False),
        sa.Column(
            "triggering_violation_id",
            sa.Integer(),
            sa.ForeignKey("violations.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "decision_id",
            sa.Integer(),
            sa.ForeignKey("admin_decisions.id", ondelete="SET NULL"),
        ),
        *timestamps(),
        sa.UniqueConstraint("manager_id", "action", name=THRESHOLD_UNIQUE),
    )
    op.create_index(
        "ix_violation_threshold_actions_manager_id",
        "violation_threshold_actions",
        ["manager_id"],
    )

    # Disciplinary records are administrative, not public content, so they
    # follow revision 0002: reachable only through the audited API role.
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE public."violation_threshold_actions" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index(
        "ix_violation_threshold_actions_manager_id",
        table_name="violation_threshold_actions",
    )
    op.drop_table("violation_threshold_actions")
    op.drop_constraint(VIOLATION_UNIQUE, "violations", type_="unique")
