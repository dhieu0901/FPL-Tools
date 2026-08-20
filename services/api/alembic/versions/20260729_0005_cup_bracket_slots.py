"""Give every Cup tie an identity of its own, so a bracket can be drawn empty.

The published bracket exists months before anyone qualifies for it. Storing the
tie's position and the label printed in each side lets the site show the whole
Cup from the start and fill managers in as rounds are played, rather than
appearing out of nothing once the first round is drawn.

Revision ID: 20260729_0005
Revises: 20260729_0004
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0005"
down_revision: str | None = "20260729_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIE_UNIQUE = "uq_cup_matches_round_tie"


def upgrade() -> None:
    # Existing rows carry no bracket position; the two Cups have never been
    # drawn, so a placeholder is enough to make the columns NOT NULL.
    for column, length in (("tie_id", 12), ("slot_a_label", 16), ("slot_b_label", 16)):
        op.add_column(
            "cup_matches",
            sa.Column(column, sa.String(length), nullable=False, server_default=""),
        )
        op.alter_column("cup_matches", column, server_default=None)

    op.create_unique_constraint(TIE_UNIQUE, "cup_matches", ["cup_round_id", "tie_id"])


def downgrade() -> None:
    op.drop_constraint(TIE_UNIQUE, "cup_matches", type_="unique")
    for column in ("slot_b_label", "slot_a_label", "tie_id"):
        op.drop_column("cup_matches", column)
