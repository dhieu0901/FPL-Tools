"""Initial VMF competition schema.

Revision ID: 20260728_0001
Revises:
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("fpl_season_code", sa.String(16), nullable=False),
        sa.Column("start_gameweek", sa.Integer(), nullable=False),
        sa.Column("end_gameweek", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("fpl_season_code", name="uq_seasons_fpl_season_code"),
    )
    op.create_table(
        "managers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fpl_entry_id", sa.BigInteger(), nullable=False),
        sa.Column("manager_name", sa.String(120), nullable=False),
        sa.Column("team_name", sa.String(120), nullable=False),
        sa.Column("phone_number", sa.String(32)),
        sa.Column("facebook_url", sa.Text()),
        sa.Column("division", sa.String(8), nullable=False),
        sa.Column("active_status", sa.String(24), nullable=False),
        sa.Column("registration_status", sa.String(16), nullable=False),
        sa.Column("season_joined", sa.String(16), nullable=False),
        sa.Column("locked_from_gameweek", sa.Integer()),
        sa.Column("season_2_league_joined", sa.Boolean(), nullable=False),
        sa.Column("season_2_join_gameweek", sa.Integer()),
        sa.Column("join_violation_applied", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("fpl_entry_id", name="uq_managers_fpl_entry_id"),
    )
    op.create_index("ix_managers_fpl_entry_id", "managers", ["fpl_entry_id"])
    op.create_index("ix_managers_division", "managers", ["division"])
    op.create_table(
        "manager_external_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("current_manager_name", sa.String(120)),
        sa.Column("current_team_name", sa.String(120)),
        sa.Column("team_name_changed", sa.Boolean(), nullable=False),
        sa.Column("raw_payload", sa.JSON()),
        *timestamps(),
        sa.UniqueConstraint("manager_id", name="uq_manager_external_profiles_manager_id"),
    )
    op.create_table(
        "gameweeks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("is_finalized", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("season_id", "number", name="uq_gameweeks_season_id"),
    )
    op.create_index("ix_gameweeks_number", "gameweeks", ["number"])
    op.create_table(
        "competition_phases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("phase_type", sa.String(24), nullable=False),
        sa.Column("start_gameweek", sa.Integer(), nullable=False),
        sa.Column("end_gameweek", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "division_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "competition_phase_id",
            sa.Integer(),
            sa.ForeignKey("competition_phases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("division", sa.String(8), nullable=False),
        sa.Column("start_gameweek", sa.Integer(), nullable=False),
        sa.Column("end_gameweek", sa.Integer(), nullable=False),
        sa.Column("promotion_source", sa.String(120)),
        sa.Column("relegation_source", sa.String(120)),
        *timestamps(),
        sa.UniqueConstraint(
            "manager_id",
            "competition_phase_id",
            name="uq_division_memberships_manager_id",
        ),
    )
    op.create_table(
        "manager_gameweek_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "gameweek_id",
            sa.Integer(),
            sa.ForeignKey("gameweeks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("gross_points", sa.Integer(), nullable=False),
        sa.Column("transfer_cost", sa.Integer(), nullable=False),
        sa.Column("net_points", sa.Integer(), nullable=False),
        sa.Column("official_points", sa.Integer()),
        sa.Column("replacement_points", sa.Integer()),
        sa.Column("score_source", sa.String(24), nullable=False),
        sa.Column("replacement_average_raw", sa.Numeric(10, 4)),
        sa.Column("chip_used", sa.String(32)),
        sa.Column("captain_points", sa.Integer(), nullable=False),
        sa.Column("goals_counted", sa.Integer(), nullable=False),
        sa.Column("yellow_cards_counted", sa.Integer(), nullable=False),
        sa.Column("red_cards_counted", sa.Integer(), nullable=False),
        sa.Column("bench_points", sa.Integer(), nullable=False),
        sa.Column("is_totw", sa.Boolean(), nullable=False),
        sa.Column("score_status", sa.String(16), nullable=False),
        *timestamps(),
        sa.UniqueConstraint(
            "manager_id",
            "gameweek_id",
            name="uq_manager_gameweek_scores_manager_id",
        ),
    )
    op.create_index(
        "ix_manager_gameweek_scores_manager_id",
        "manager_gameweek_scores",
        ["manager_id"],
    )
    op.create_index(
        "ix_manager_gameweek_scores_gameweek_id",
        "manager_gameweek_scores",
        ["gameweek_id"],
    )
    op.create_table(
        "violations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("gameweek_number", sa.Integer(), nullable=False),
        sa.Column("violation_type", sa.String(24), nullable=False),
        sa.Column("detected_count", sa.Integer(), nullable=False),
        sa.Column("confirmed_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("admin_note", sa.Text()),
        sa.Column("reviewed_by", sa.String(120)),
        sa.Column("reviewed_at", sa.DateTime()),
        *timestamps(),
    )
    op.create_index("ix_violations_manager_id", "violations", ["manager_id"])
    op.create_index("ix_violations_gameweek_number", "violations", ["gameweek_number"])
    op.create_table(
        "admin_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_type", sa.String(24), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(80), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("before_state", sa.JSON()),
        sa.Column("after_state", sa.JSON()),
        *timestamps(),
    )
    op.create_table(
        "h2h_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "h2h_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "schedule_id",
            sa.Integer(),
            sa.ForeignKey("h2h_schedules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("gameweek_number", sa.Integer(), nullable=False),
        sa.Column(
            "home_manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "away_manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("home_score", sa.Integer()),
        sa.Column("away_score", sa.Integer()),
        sa.Column("winner_manager_id", sa.Integer(), sa.ForeignKey("managers.id")),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("walkover_reason", sa.String(240)),
        sa.Column("is_playoff", sa.Boolean(), nullable=False),
        sa.Column("bracket_position", sa.String(32)),
        *timestamps(),
        sa.UniqueConstraint(
            "schedule_id",
            "gameweek_number",
            "home_manager_id",
            name="uq_h2h_matches_schedule_id",
        ),
        sa.UniqueConstraint(
            "schedule_id",
            "gameweek_number",
            "away_manager_id",
            name="uq_h2h_matches_schedule_id_2",
        ),
    )
    op.create_index("ix_h2h_matches_gameweek_number", "h2h_matches", ["gameweek_number"])
    op.create_table(
        "h2h_penalties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("violation_id", sa.Integer(), sa.ForeignKey("violations.id")),
        sa.Column("table_point_delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(240), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_h2h_penalties_manager_id", "h2h_penalties", ["manager_id"])
    op.create_table(
        "cup_competitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("season_half", sa.Integer(), nullable=False),
        sa.Column("qualification_end_gameweek", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint(
            "season_id",
            "season_half",
            name="uq_cup_competitions_season_id",
        ),
    )
    op.create_table(
        "cup_rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "cup_competition_id",
            sa.Integer(),
            sa.ForeignKey("cup_competitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(48), nullable=False),
        sa.Column("round_order", sa.Integer(), nullable=False),
        sa.Column("gameweek_number", sa.Integer(), nullable=False),
        sa.Column("has_third_place_match", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint(
            "cup_competition_id",
            "round_order",
            name="uq_cup_rounds_cup_competition_id",
        ),
    )
    op.create_table(
        "cup_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "cup_round_id",
            sa.Integer(),
            sa.ForeignKey("cup_rounds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("manager_a_id", sa.Integer(), sa.ForeignKey("managers.id")),
        sa.Column("manager_b_id", sa.Integer(), sa.ForeignKey("managers.id")),
        sa.Column("manager_a_score", sa.Integer()),
        sa.Column("manager_b_score", sa.Integer()),
        sa.Column("winner_manager_id", sa.Integer(), sa.ForeignKey("managers.id")),
        sa.Column("tie_break_step_used", sa.String(24)),
        sa.Column("random_draw_result", sa.String(240)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("is_third_place_match", sa.Boolean(), nullable=False),
        *timestamps(),
    )


def downgrade() -> None:
    op.drop_table("cup_matches")
    op.drop_table("cup_rounds")
    op.drop_table("cup_competitions")
    op.drop_index("ix_h2h_penalties_manager_id", table_name="h2h_penalties")
    op.drop_table("h2h_penalties")
    op.drop_index("ix_h2h_matches_gameweek_number", table_name="h2h_matches")
    op.drop_table("h2h_matches")
    op.drop_table("h2h_schedules")
    op.drop_table("admin_decisions")
    op.drop_index("ix_violations_gameweek_number", table_name="violations")
    op.drop_index("ix_violations_manager_id", table_name="violations")
    op.drop_table("violations")
    op.drop_index(
        "ix_manager_gameweek_scores_gameweek_id",
        table_name="manager_gameweek_scores",
    )
    op.drop_index(
        "ix_manager_gameweek_scores_manager_id",
        table_name="manager_gameweek_scores",
    )
    op.drop_table("manager_gameweek_scores")
    op.drop_table("division_memberships")
    op.drop_table("competition_phases")
    op.drop_index("ix_gameweeks_number", table_name="gameweeks")
    op.drop_table("gameweeks")
    op.drop_table("manager_external_profiles")
    op.drop_index("ix_managers_division", table_name="managers")
    op.drop_index("ix_managers_fpl_entry_id", table_name="managers")
    op.drop_table("managers")
    op.drop_table("seasons")
