"""FPL ingestion layer: raw evidence, source facts and sync runs.

Revision ID: 20260728_0003
Revises: 20260728_0002
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0003"
down_revision: str | None = "20260728_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INGESTION_TABLES = (
    "raw_fpl_responses",
    "fpl_teams",
    "fpl_players",
    "fpl_fixtures",
    "fpl_player_fixture_stats",
    "manager_pick_snapshots",
    "manager_pick_items",
    "manager_gameweek_history",
    "sync_runs",
)


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
    op.add_column("gameweeks", sa.Column("deadline_time", sa.DateTime()))
    op.add_column(
        "gameweeks",
        sa.Column("fpl_finished", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "gameweeks",
        sa.Column("fpl_data_checked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "raw_fpl_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("endpoint_name", sa.String(48), nullable=False),
        sa.Column("request_key", sa.String(160), nullable=False),
        sa.Column("season_code", sa.String(16)),
        sa.Column("gameweek_number", sa.Integer()),
        sa.Column("fpl_entry_id", sa.BigInteger()),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_bytes", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON()),
        sa.Column("contract_version", sa.String(16), nullable=False),
        sa.Column("parser_version", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(64)),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("seen_count", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint(
            "request_key",
            "payload_hash",
            name="uq_raw_fpl_responses_request_key",
        ),
    )
    op.create_index(
        "ix_raw_fpl_responses_endpoint_name",
        "raw_fpl_responses",
        ["endpoint_name"],
    )
    op.create_index(
        "ix_raw_fpl_responses_request_key",
        "raw_fpl_responses",
        ["request_key"],
    )

    op.create_table(
        "fpl_teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("team_fpl_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("short_name", sa.String(8), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("season_id", "team_fpl_id", name="uq_fpl_teams_season_id"),
    )

    op.create_table(
        "fpl_players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("element_id", sa.Integer(), nullable=False),
        sa.Column("web_name", sa.String(120), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("team_fpl_id", sa.Integer(), nullable=False),
        sa.Column("element_type", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(8)),
        sa.Column("now_cost", sa.Integer()),
        *timestamps(),
        sa.UniqueConstraint("season_id", "element_id", name="uq_fpl_players_season_id"),
    )
    op.create_index("ix_fpl_players_element_id", "fpl_players", ["element_id"])

    op.create_table(
        "fpl_fixtures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fixture_fpl_id", sa.Integer(), nullable=False),
        sa.Column("gameweek_number", sa.Integer()),
        sa.Column("kickoff_time", sa.DateTime()),
        sa.Column("started", sa.Boolean(), nullable=False),
        sa.Column("finished", sa.Boolean(), nullable=False),
        sa.Column("finished_provisional", sa.Boolean(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("team_h_fpl_id", sa.Integer()),
        sa.Column("team_a_fpl_id", sa.Integer()),
        sa.Column("team_h_score", sa.Integer()),
        sa.Column("team_a_score", sa.Integer()),
        *timestamps(),
        sa.UniqueConstraint("season_id", "fixture_fpl_id", name="uq_fpl_fixtures_season_id"),
    )
    op.create_index("ix_fpl_fixtures_gameweek_number", "fpl_fixtures", ["gameweek_number"])

    op.create_table(
        "fpl_player_fixture_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("gameweek_number", sa.Integer(), nullable=False),
        sa.Column("element_id", sa.Integer(), nullable=False),
        sa.Column("fixture_fpl_id", sa.Integer(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("total_points", sa.Integer(), nullable=False),
        sa.Column("goals_scored", sa.Integer(), nullable=False),
        sa.Column("assists", sa.Integer(), nullable=False),
        sa.Column("yellow_cards", sa.Integer(), nullable=False),
        sa.Column("red_cards", sa.Integer(), nullable=False),
        sa.Column("bonus", sa.Integer(), nullable=False),
        sa.Column(
            "source_raw_id",
            sa.Integer(),
            sa.ForeignKey("raw_fpl_responses.id", ondelete="SET NULL"),
        ),
        *timestamps(),
        sa.UniqueConstraint(
            "season_id",
            "gameweek_number",
            "element_id",
            "fixture_fpl_id",
            name="uq_fpl_player_fixture_stats_season_id",
        ),
    )
    op.create_index(
        "ix_fpl_player_fixture_stats_gameweek_number",
        "fpl_player_fixture_stats",
        ["gameweek_number"],
    )
    op.create_index(
        "ix_fpl_player_fixture_stats_element_id",
        "fpl_player_fixture_stats",
        ["element_id"],
    )

    op.create_table(
        "manager_pick_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("gameweek_number", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("active_chip", sa.String(32)),
        sa.Column("event_transfers", sa.Integer(), nullable=False),
        sa.Column("transfer_cost", sa.Integer(), nullable=False),
        sa.Column("gross_points", sa.Integer()),
        sa.Column("points_on_bench", sa.Integer()),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column(
            "source_raw_id",
            sa.Integer(),
            sa.ForeignKey("raw_fpl_responses.id", ondelete="SET NULL"),
        ),
        *timestamps(),
        sa.UniqueConstraint(
            "manager_id",
            "gameweek_number",
            "revision",
            name="uq_manager_pick_snapshots_manager_id",
        ),
        sa.UniqueConstraint(
            "manager_id",
            "gameweek_number",
            "payload_hash",
            name="uq_manager_pick_snapshots_payload",
        ),
    )
    op.create_index(
        "ix_manager_pick_snapshots_manager_id",
        "manager_pick_snapshots",
        ["manager_id"],
    )
    op.create_index(
        "ix_manager_pick_snapshots_gameweek_number",
        "manager_pick_snapshots",
        ["gameweek_number"],
    )

    op.create_table(
        "manager_pick_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.Integer(),
            sa.ForeignKey("manager_pick_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("element_id", sa.Integer(), nullable=False),
        sa.Column("squad_position", sa.Integer(), nullable=False),
        sa.Column("multiplier", sa.Integer(), nullable=False),
        sa.Column("is_captain", sa.Boolean(), nullable=False),
        sa.Column("is_vice_captain", sa.Boolean(), nullable=False),
        sa.Column("auto_subbed_in", sa.Boolean(), nullable=False),
        sa.Column("auto_subbed_out", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("snapshot_id", "element_id", name="uq_manager_pick_items_snapshot_id"),
    )
    op.create_index("ix_manager_pick_items_snapshot_id", "manager_pick_items", ["snapshot_id"])

    op.create_table(
        "manager_gameweek_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "manager_id",
            sa.Integer(),
            sa.ForeignKey("managers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("gameweek_number", sa.Integer(), nullable=False),
        sa.Column("gross_points", sa.Integer(), nullable=False),
        sa.Column("total_points", sa.Integer()),
        sa.Column("event_transfers", sa.Integer(), nullable=False),
        sa.Column("transfer_cost", sa.Integer(), nullable=False),
        sa.Column("points_on_bench", sa.Integer(), nullable=False),
        sa.Column("squad_value", sa.Integer()),
        sa.Column("bank", sa.Integer()),
        sa.Column(
            "source_raw_id",
            sa.Integer(),
            sa.ForeignKey("raw_fpl_responses.id", ondelete="SET NULL"),
        ),
        *timestamps(),
        sa.UniqueConstraint(
            "manager_id",
            "gameweek_number",
            name="uq_manager_gameweek_history_manager_id",
        ),
    )
    op.create_index(
        "ix_manager_gameweek_history_manager_id",
        "manager_gameweek_history",
        ["manager_id"],
    )
    op.create_index(
        "ix_manager_gameweek_history_gameweek_number",
        "manager_gameweek_history",
        ["gameweek_number"],
    )

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_type", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="SET NULL"),
        ),
        sa.Column("gameweek_number", sa.Integer()),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("records_written", sa.Integer(), nullable=False),
        sa.Column("payload_changed", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("correlation_id", sa.String(64)),
        *timestamps(),
    )
    op.create_index("ix_sync_runs_job_type", "sync_runs", ["job_type"])

    # Ingestion tables hold source evidence, not public content. They follow the
    # same rule as revision 0002: reachable only through the audited API role.
    if op.get_bind().dialect.name == "postgresql":
        for table_name in INGESTION_TABLES:
            op.execute(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("ix_sync_runs_job_type", table_name="sync_runs")
    op.drop_table("sync_runs")
    op.drop_index(
        "ix_manager_gameweek_history_gameweek_number",
        table_name="manager_gameweek_history",
    )
    op.drop_index(
        "ix_manager_gameweek_history_manager_id",
        table_name="manager_gameweek_history",
    )
    op.drop_table("manager_gameweek_history")
    op.drop_index("ix_manager_pick_items_snapshot_id", table_name="manager_pick_items")
    op.drop_table("manager_pick_items")
    op.drop_index(
        "ix_manager_pick_snapshots_gameweek_number",
        table_name="manager_pick_snapshots",
    )
    op.drop_index(
        "ix_manager_pick_snapshots_manager_id",
        table_name="manager_pick_snapshots",
    )
    op.drop_table("manager_pick_snapshots")
    op.drop_index(
        "ix_fpl_player_fixture_stats_element_id",
        table_name="fpl_player_fixture_stats",
    )
    op.drop_index(
        "ix_fpl_player_fixture_stats_gameweek_number",
        table_name="fpl_player_fixture_stats",
    )
    op.drop_table("fpl_player_fixture_stats")
    op.drop_index("ix_fpl_fixtures_gameweek_number", table_name="fpl_fixtures")
    op.drop_table("fpl_fixtures")
    op.drop_index("ix_fpl_players_element_id", table_name="fpl_players")
    op.drop_table("fpl_players")
    op.drop_table("fpl_teams")
    op.drop_index("ix_raw_fpl_responses_request_key", table_name="raw_fpl_responses")
    op.drop_index("ix_raw_fpl_responses_endpoint_name", table_name="raw_fpl_responses")
    op.drop_table("raw_fpl_responses")
    op.drop_column("gameweeks", "fpl_data_checked")
    op.drop_column("gameweeks", "fpl_finished")
    op.drop_column("gameweeks", "deadline_time")
