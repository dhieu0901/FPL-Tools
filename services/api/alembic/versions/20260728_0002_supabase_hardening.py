"""Harden VMF tables against direct Supabase Data API access.

Revision ID: 20260728_0002
Revises: 20260728_0001
Create Date: 2026-07-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260728_0002"
down_revision: str | None = "20260728_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VMF_TABLES = (
    "seasons",
    "managers",
    "manager_external_profiles",
    "gameweeks",
    "competition_phases",
    "division_memberships",
    "manager_gameweek_scores",
    "violations",
    "admin_decisions",
    "h2h_schedules",
    "h2h_matches",
    "h2h_penalties",
    "cup_competitions",
    "cup_rounds",
    "cup_matches",
)


def upgrade() -> None:
    # FastAPI connects with the database owner and therefore bypasses RLS.
    # No anon/authenticated policies are created: browser clients must use the
    # audited FastAPI surface instead of Supabase's generated Data API.
    for table_name in VMF_TABLES:
        op.execute(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY')

    op.execute(
        """
        DO $hardening$
        DECLARE
          target_role text;
        BEGIN
          FOREACH target_role IN ARRAY ARRAY['anon', 'authenticated']
          LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = target_role) THEN
              EXECUTE format(
                'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM %I',
                target_role
              );
              EXECUTE format(
                'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM %I',
                target_role
              );
              EXECUTE format(
                'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                'REVOKE ALL ON TABLES FROM %I',
                target_role
              );
              EXECUTE format(
                'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                'REVOKE ALL ON SEQUENCES FROM %I',
                target_role
              );
            END IF;
          END LOOP;

          IF to_regclass('public.alembic_version') IS NOT NULL THEN
            ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;
          END IF;
        END
        $hardening$;
        """
    )


def downgrade() -> None:
    for table_name in reversed(VMF_TABLES):
        op.execute(f'ALTER TABLE public."{table_name}" DISABLE ROW LEVEL SECURITY')

    # Deliberately do not restore anon/authenticated grants on downgrade.
    # Restoring broad Data API access would be an unsafe rollback behavior.
