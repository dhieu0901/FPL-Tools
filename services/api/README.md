# VMF Fantasy API

FastAPI backend and deterministic rule engine for the VMF Fantasy League.

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn vmf_api.main:app --reload
```

Production uses psycopg 3 asynchronously through `postgresql+psycopg`. Tests override the database URL with
`sqlite+aiosqlite`.

Important environment variables:

```text
VMF_DATABASE_URL
VMF_MIGRATION_DATABASE_URL
VMF_DATABASE_USE_NULL_POOL
VMF_DATABASE_DISABLE_PREPARED_STATEMENTS
VMF_ADMIN_API_KEY
CRON_SECRET (or VMF_CRON_SECRET)
VMF_CORS_ORIGINS
VMF_FPL_BASE_URL
```

The application never creates production tables at startup. Apply Alembic
migrations before starting the service.

After migrating a new database, create the idempotent season shell:

```powershell
vmf-bootstrap-season --season-code "2026/27" --season-name "VMF Fantasy League 2026/27"
```

This creates the season, GW1-GW38 and the six rulebook phases. It deliberately
does not invent managers, scores, H2H schedules or Cup brackets.

## Vercel Hobby + Supabase Free

Create a Vercel project with `services/api` as its Root Directory. Vercel
discovers the FastAPI application through `app.py`; Docker is not used in
production.

Use the Supabase **transaction pooler** URL on port `6543` for application
traffic:

```text
VMF_ENVIRONMENT=production
VMF_DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:PASSWORD@REGION.pooler.supabase.com:6543/postgres
VMF_DATABASE_USE_NULL_POOL=true
VMF_DATABASE_DISABLE_PREPARED_STATEMENTS=true
CRON_SECRET=a-random-secret-with-at-least-32-characters
```

Generic Supabase `postgres://` and `postgresql://` URLs are normalized to
`postgresql+psycopg://`. `NullPool` leaves connection pooling to Supavisor.
Setting `VMF_DATABASE_DISABLE_PREPARED_STATEMENTS=true` passes
`prepare_threshold=None` to psycopg 3, as required by the transaction pooler.

Do not run Alembic during a Vercel build or function startup. Run migrations
from a trusted machine or CI job using the Supabase **session pooler** on port
`5432` (or the direct connection when IPv6 is available):

```powershell
$env:VMF_MIGRATION_DATABASE_URL = "postgresql+psycopg://postgres.PROJECT_REF:PASSWORD@REGION.pooler.supabase.com:5432/postgres"
alembic upgrade head
```

`VMF_MIGRATION_DATABASE_URL` is used only by Alembic. It stays separate from
the serverless runtime URL.

### Scheduled probe

The public `GET /api/fpl/status` route observes the official current FPL
gameweek, deadline and fixture progress without writing to the database. The
web dashboard uses this endpoint instead of inferring the current gameweek
from the pre-generated H2H schedule.

Supabase Cron can invoke:

```http
POST /api/cron/fpl-probe
Authorization: Bearer <CRON_SECRET>
```

The endpoint is fail-closed when no secret is configured and uses a
transaction-scoped PostgreSQL advisory lock to skip overlapping calls. It
only fetches and validates public FPL bootstrap/fixture metadata. The response
explicitly contains `"persisted": false`; this endpoint is deployment
plumbing, not the future competition-state synchronization pipeline.

A `GET` variant exists for Vercel Cron compatibility, although Vercel Hobby
only supports daily schedules. Supabase Cron should use `POST` for any more
frequent free schedule.
