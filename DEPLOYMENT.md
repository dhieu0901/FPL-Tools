# Free deployment: Vercel Hobby + Supabase Free

Updated: 28 July 2026.

The recommended production stack for 46 managers is:

```text
Browser
  -> Vercel project vmf-web (Next.js, root apps/web)
  -> Vercel project vmf-api (FastAPI Function, root services/api)
  -> Supabase Free (PostgreSQL + Vault + Cron)
  -> the public FPL API
```

Docker is not needed in production. `compose.yaml` exists for local development
and testing only.

## Conditions for keeping the cost at zero

- Vercel Hobby is for personal, non-commercial projects under
  [Fair Use](https://vercel.com/docs/plans/hobby). If the league becomes a paid
  or for-profit service, re-read the terms before going live.
- The repository belongs to a personal GitHub account. Vercel Hobby cannot
  connect a private repository owned by a GitHub Organization.
- Do not add a card or upgrade the Supabase plan; watch Usage to stay inside
  the quota.
- Accept that there is no SLA, that Supabase may pause an inactive project, and
  that Vercel Hobby keeps logs only briefly.
- Back the database up yourself, outside Supabase. The Free plan has no
  automatic backups recoverable from the dashboard.

Limits change. Read [Quotas to watch](#quotas-to-watch) and re-check both
dashboards before the season starts.

## 1. Create the Supabase Free project

1. Create a project in the
   [Supabase dashboard](https://supabase.com/dashboard), pick the region
   closest to your users and store the database password in a password
   manager. For users in Vietnam, Singapore is usually the nearest region on
   offer.
2. In **Connect**, take two connection strings:
   - the **transaction pooler**, port `6543`: for the serverless API on Vercel
     only;
   - the **session pooler**, port `5432`: for Alembic migrations and `pg_dump`
     when the machine running them has no IPv6.
3. Produce two variants of the session-pooler URL:
   - the SQLAlchemy/Alembic variant uses the `postgresql+psycopg://` scheme;
   - the Supabase CLI and `pg_dump` variant keeps the standard
     `postgresql://` scheme, because libpq tools do not understand
     `postgresql+psycopg://`.
   The API's transaction-pooler URL also uses `postgresql+psycopg://`. Keep the
   username, host, port and database exactly as the dashboard supplies them. If
   you assemble a URL by hand, URL-encode the password.

Structural example, not a real credential:

```text
# Runtime, transaction pooler
postgresql+psycopg://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require

# Migrations through SQLAlchemy/Alembic, session pooler
postgresql+psycopg://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require

# Backups through the Supabase CLI or pg_dump, same pooler, libpq scheme
postgresql://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```

The transaction pooler is built for serverless workloads but does not support
prepared statements. The API therefore uses psycopg 3 with `NullPool` and
`prepare_threshold=None`. See
[Supabase: connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)
and [SQLAlchemy on Supabase](https://supabase.com/docs/guides/troubleshooting/using-sqlalchemy-with-supabase-FUqebT).

In **Database Settings → SSL Configuration**, enable **Enforce SSL on incoming
connections**. `sslmode=require` is the minimum for Vercel; before the opening
weekend, move to `verify-full` with the CA certificate from the dashboard once
your certificate handling has been tested.

## 2. Safe migrations

Never run migrations from the Vercel build command or at FastAPI startup. Two
Vercel projects can build in parallel and serverless functions can run
concurrently, which would apply the schema more than once.

### First run against an empty database

1. Create the GitHub Actions secret `SUPABASE_MIGRATION_DATABASE_URL` from the
   **session pooler URL on port 5432**, not the runtime URL on 6543.
2. Open **Actions → Apply database migrations → Run workflow** on `main`.
3. Confirm that a backup was checked, or that this is a genuinely empty new
   database, and type `MIGRATE` exactly.
4. On the first run, also supply:
   - `season_code`: `2026/27`
   - `season_name`: `VMF Fantasy League 2026/27`

   Leave both blank on later migrations.
5. `.github/workflows/migrate.yml` runs `alembic upgrade head`, confirms the
   current revision, then calls the idempotent bootstrap when both season
   inputs are present. The bootstrap creates a DRAFT season, 38 Gameweeks and
   the six Classic/H2H/Cup phases; it stops safely if existing data disagrees
   with the rules instead of overwriting it.
6. Open **Security Advisor** and confirm that every VMF table has row-level
   security enabled. The hardening migration creates no policy for `anon` or
   `authenticated` and revokes Data API privileges; the frontend reaches data
   only through FastAPI. In **API Settings**, remove `public` from the exposed
   schemas if the project does not use the Supabase Data API.

### Later schema upgrades

1. Pause the `vmf-fpl-sync` job in Supabase Cron if the migration affects
   writes.
2. Take a logical backup using the **libpq `postgresql://` URL**, not the
   SQLAlchemy `postgresql+psycopg://` one. The Docker-free option is to install
   the PostgreSQL client (`pg_dump`/`pg_restore`) on the administrator's
   machine; the schema is rebuilt by Alembic, so the dump carries application
   data only:

   ```bash
   pg_dump "$SUPABASE_BACKUP_URL" \
     --schema=public \
     --data-only \
     --exclude-table=public.alembic_version \
     --format=custom \
     --file vmf-data.dump
   pg_restore --list vmf-data.dump
   ```

   Store the dump next to the Git commit it came from, together with the row
   counts. If you prefer the Supabase CLI, it needs Docker **on the backup
   machine** (production still does not), and you must produce `roles.sql`,
   `schema.sql` and `data.sql` using `--role-only`, the default, and then
   `--data-only --use-copy`; the default command alone contains no data. See
   [Supabase CLI `db dump`](https://supabase.com/docs/reference/cli/supabase-db-dump).
3. Deploy code compatible with both the old and the new schema where possible.
4. Run the migration workflow manually.
5. Check `/health/ready` and the main pages before re-enabling cron.

Never store a database URL in the repository, a workflow log, a screenshot or a
`NEXT_PUBLIC_*` variable.

## 3. Deploy FastAPI to Vercel

Import `dhieu0901/FPL-Tools` into a Vercel Hobby project:

- Project name: `vmf-api`, or an equivalent free name.
- Root directory: `services/api`.
- Production branch: `main`.
- Framework preset: **Other**. The project ships its own
  `services/api/vercel.json`, which rewrites every path to the ASGI
  application exported from `services/api/api/index.py` and raises the function
  limit to 60 seconds for the synchronization job.
- Leave the install command at its default. Vercel installs from
  `services/api/requirements.txt`, which is generated from `uv.lock`:

  ```bash
  uv export --format requirements-txt --no-dev --no-emit-project \
    --no-hashes -o requirements.txt
  ```

  CI fails if that file drifts from the lock file, so regenerate it whenever a
  dependency changes.
- In **Settings → Functions → Function Region**, choose the same region as
  Supabase, for example Singapore. Vercel defaults to `iad1` (Washington,
  D.C.); leaving that default while the database is in Asia adds latency. Hobby
  allows one region, per
  [Vercel Function regions](https://vercel.com/docs/functions/configuring-functions/region).

Add the following **Production** variables. Preview may use a second Supabase
project; never let Preview write to the production database.

| Name | Value |
| --- | --- |
| `VMF_ENVIRONMENT` | `production` |
| `VMF_DATABASE_URL` | Transaction pooler URL, port `6543` |
| `VMF_DATABASE_USE_NULL_POOL` | `true` |
| `VMF_DATABASE_DISABLE_PREPARED_STATEMENTS` | `true` |
| `VMF_ADMIN_API_KEY` | A dedicated random string, at least 32 bytes |
| `CRON_SECRET` | A different random string, at least 32 bytes |
| `VMF_CORS_ORIGINS` | `["https://<web-project>.vercel.app"]` |
| `VMF_FPL_BASE_URL` | `https://fantasy.premierleague.com/api` |
| `VMF_ACTIVE_SEASON_CODE` | `2026/27` |
| `VMF_SYNC_MANAGER_BATCH_SIZE` | `10`, raise only after measuring the run time |

Do not set `VMF_MIGRATION_DATABASE_URL` on Vercel. After the first deployment,
check:

```text
https://<api-project>.vercel.app/health/live
https://<api-project>.vercel.app/health/ready
https://<api-project>.vercel.app/api/fpl/status
```

`live` confirms the function runs. `ready` returns `200` only when the database
is reachable and the Alembic revision matches the head of the deployed code.
`fpl/status` must return a Gameweek state observed directly from FPL rather
than inferred from the H2H schedule. `/docs` is deliberately disabled in
production.

## 4. Deploy Next.js to Vercel

Import the same repository a second time:

- Project name: `vmf-web`, or an equivalent free name.
- Root directory: `apps/web`.
- Production branch: `main`.
- Framework preset: Next.js.

Production environment variables:

| Name | Value |
| --- | --- |
| `VMF_API_URL` | `https://<api-project>.vercel.app/api` |
| `VMF_USE_MOCK_DATA` | `false` |
| `VMF_SEASON_ID` | The season ID after the data is initialized, for example `1` |
| `VMF_H2H_SCHEDULE_ID` | The H2H schedule ID after an administrator creates it, for example `1` |
| `VMF_SEASON_LABEL` | `2026/27` |
| `VMF_ADMIN_API_KEY` | The same value as in the API project |
| `VMF_ADMIN_ACTOR` | `vmf-web` |
| `VMF_ADMIN_UI_USER` | A dedicated username for `/admin` |
| `VMF_ADMIN_UI_PASSWORD` | A long password, different from every other secret |

The frontend reads these at server runtime. Never rename a secret to the
`NEXT_PUBLIC_` prefix, which would place its value in the browser bundle. Once
the real web URL is known, set the API's `VMF_CORS_ORIGINS` to that exact
origin and redeploy the API. Never use `*` for production CORS.

Every push to `main` creates a deployment for both projects. Vercel Hobby
allows one concurrent build, so the two may queue; that is not an error.

## 5. Complete the initial data

Migrations and the season bootstrap never invent a roster. Before going public:

1. Take `season_id` from the **Bootstrap season metadata** step's log and put
   it in the web project's `VMF_SEASON_ID`.
2. Import the 46 managers with `vmf-import-managers`, run locally against the
   session pooler. Prepare a CSV with the columns `fpl_entry_id`,
   `manager_name`, `team_name`, `division`:

   ```csv
   fpl_entry_id,manager_name,team_name,division
   123456,Manager name,FPL team name,HIGH
   ```

   Validate before writing. The dry run performs every check, including the
   FPL lookup, and writes nothing:

   ```bash
   cd services/api
   export VMF_DATABASE_URL='postgresql+psycopg://...:5432/postgres?sslmode=require'
   .venv/bin/vmf-import-managers --file roster.csv --season-code 2026/27 --dry-run
   ```

   Drop `--dry-run` to apply it. The command creates each manager as active and
   confirmed, adds the Classic Season 1 division membership, and stores the
   manager and team names FPL currently shows so a later rename is visible.

   Each `fpl_entry_id` is confirmed against FPL first, and a single unreadable
   entry aborts the whole import rather than leaving a half-filled roster. This
   is the check that matters: a mistyped entry id produces a manager who looks
   present everywhere while their squad never synchronises.

   The command refuses a roster that is not 46 managers split HIGH 20 / LOW 26 unless
   `--allow-imbalance` is passed, and re-running it creates nothing. A row whose
   division disagrees with an already imported manager is reported instead of
   applied, so promotion and relegation stay an explicit decision.

   Keep `roster.csv` out of the repository, and out of it entirely if it holds
   phone numbers or Facebook URLs.

   For one-off corrections, `POST /api/managers` with `X-Admin-Key` still
   creates a single record.
3. Only once the public API returns exactly 20 HIGH and 20 LOW managers,
   generate the H2H schedule exactly once:

   ```bash
   curl --fail-with-body \
     -X POST "https://<api-project>.vercel.app/api/h2h/schedule/generate" \
     -H "Content-Type: application/json" \
     -H "X-Admin-Key: <admin-key>" \
     -H "X-Admin-Actor: preseason-schedule" \
     -d '{
       "season_id": 1,
       "name": "VMF H2H Group Stage 2026/27",
       "rounds": 35,
       "start_gameweek": 1
     }'
   ```

   Replace `season_id` with the real ID. The endpoint uses only managers that
   are both **active** and **confirmed**, requires exactly 40 of them, creates
   35 × 20 = 700 matches and returns a `schedule_id`.
4. Set the web project's `VMF_H2H_SCHEDULE_ID` to that `schedule_id`, redeploy
   the web project, then check GW1 and GW35. Never call the generate endpoint a
   second time for the same season.

The Cup needs no bracket before the season: competitions, rounds and matches
are created only after qualification is settled at the rule cutoffs.

## 6. Enable Supabase Cron

Do not use Vercel Cron for frequent work: Hobby allows one run per job per day
and the firing time can drift by up to 59 minutes. Supabase Cron uses `pg_cron`
and calls the API through `pg_net`.

1. In Supabase, open **Integrations → Vault** and create exactly two secrets:
   - `vmf_api_base_url`: `https://<api-project>.vercel.app`, without `/api` and
     without a trailing `/`;
   - `vmf_cron_secret`: the same value as `CRON_SECRET` in the Vercel API
     project.
2. Open the SQL Editor and run
   [`supabase/cron_fpl_sync.sql`](supabase/cron_fpl_sync.sql).
3. In **Integrations → Cron**, confirm two active jobs:
   - `vmf-fpl-sync`: every five minutes, in UTC;
   - `vmf-cron-history-cleanup`: deletes run history older than seven days.
4. Check the job history and the `vmf-api` runtime logs.

The script is safe to re-run: a job of the same name is updated rather than
duplicated, and the script stops immediately if a Vault secret is missing or
duplicated. Secrets are decrypted only while the job runs and never appear in
the stored cron statement.

`POST /api/cron/sync` requires `Authorization: Bearer <CRON_SECRET>`, holds a
PostgreSQL advisory lock so overlapping calls are skipped, and runs only the
jobs whose preconditions currently hold:

- bootstrap and fixtures on every tick;
- picks once the Gameweek deadline has passed, in batches of
  `VMF_SYNC_MANAGER_BATCH_SIZE` managers;
- live player statistics once a fixture of that Gameweek has started;
- entry history once a fixture has settled, or while a manager still has no
  history row for the Gameweek.

The response lists each job with its status and the number of records written.
`skipped` with `sealed_until_deadline` is correct behaviour before a deadline,
not a failure.

[`supabase/cron_fpl_probe.sql`](supabase/cron_fpl_probe.sql) remains available
as a read-only connectivity check. Its `persisted=false` result proves only
that FPL is reachable; it is never evidence that league data was written.

To stop the schedule without touching other jobs, run
[`supabase/cron_disable.sql`](supabase/cron_disable.sql). When rotating the
secret, update both the Vercel `CRON_SECRET` and the Vault `vmf_cron_secret`,
redeploy the API, then verify one successful call.

## 7. Checks before going public

- GitHub Actions `CI` is green and the migration workflow ended at revision
  `head`.
- `/health/live` and `/health/ready` return `200`.
- `/api/fpl/status` returns a Gameweek, state and deadline consistent with the
  official FPL site.
- A cron call without a token, or with the wrong token, returns `401`; the
  correct token returns `200`.
- The web project runs with `VMF_USE_MOCK_DATA=false` and shows no sample data
  when the API fails.
- The public managers endpoint returns exactly 40 confirmed profiles, 20 HIGH
  and 20 LOW; pending and rejected profiles do not appear.
- H2H contains exactly 700 group-stage matches, and `VMF_SEASON_ID` and
  `VMF_H2H_SCHEDULE_ID` point at the records just created.
- The web project's production origin appears exactly in `VMF_CORS_ORIGINS`.
- Admin endpoints reject a request with a missing or wrong `X-Admin-Key`.
- Supabase Cron shows successful history with no long-running overlapping
  requests.
- Vercel and Supabase usage are far from their limits, and the Supabase
  database report stays under `400 MB` for headroom.
- `vmf-data.dump` exists, `pg_restore --list` reads it, and a restore has been
  rehearsed into a separate project. If you use the Supabase CLI, all three
  role, schema and data files exist.

## Quotas to watch

Per the official documentation on the update date:

| Service | Free quota and notable risk |
| --- | --- |
| Vercel Hobby | Personal, non-commercial use only; 1,000,000 function invocations, 4 CPU-hours, 360 GB-hours of memory, 100 GB of data transfer; runtime logs kept about an hour; exceeding the quota can pause the project |
| Vercel Cron Hobby | At most one run per job per day, accurate only to the hour (`±59 minutes`); this project does not use it for the five-minute sync |
| Supabase Free | At most 2 active projects; 500 MB database, 5 GB egress, 1 GB storage, 500,000 Edge Function invocations, 50,000 MAU |
| Supabase pausing | A project with little database activity for about seven days may be paused, and can be resumed within 90 days. Watch the warning emails; never treat cron as an SLA |
| Supabase backups | The Free plan has no automatic backups; export a logical backup yourself and keep it outside the project |

Sources: [Vercel Hobby](https://vercel.com/docs/plans/hobby),
[Vercel Cron](https://vercel.com/docs/cron-jobs/usage-and-pricing),
[Supabase pricing](https://supabase.com/pricing),
[Supabase billing](https://supabase.com/docs/guides/platform/billing-on-supabase),
[Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
and [Supabase backups](https://supabase.com/docs/guides/platform/backups).

With 46 managers the request quota is comfortable as long as the API serves
data already aggregated in the database. Do not store the whole
`bootstrap-static` payload again on every tick: shared payloads are recorded by
hash only, while manager-scoped evidence is kept in full. Watch the database
report from `400 MB` and agree a retention policy for old raw rows before the
season.

## Rollback and recovery

### Code

In each Vercel project, open **Deployments**, pick the most recent tested
production deployment and promote or roll back to it. Roll back both the API
and the web project when the contract between them changed. Revert the faulty
commit on `main` so the next deployment does not reintroduce it.

### Cron

Run `supabase/cron_disable.sql`, then confirm the two VMF jobs are gone from
`cron.job`. Never `drop extension pg_cron`: that removes every cron job in the
project.

### Database

- Prefer a forward-fixing migration (`upgrade`) so data is preserved.
- Run `alembic downgrade -1` only when the migration has a tested downgrade and
  the running code is compatible with the older schema.
- Rehearse a Docker-free restore on a second Supabase Free project: first run
  the migration workflow or Alembic to `head`, then use the target project's
  `postgresql://` URL:

  ```bash
  pg_restore \
    --dbname "$RESTORE_DATABASE_URL" \
    --data-only \
    --single-transaction \
    --disable-triggers \
    vmf-data.dump
  ```

  Compare row counts between source and restore for at least `managers`,
  `manager_gameweek_scores`, `manager_gameweek_history`, `h2h_matches`,
  `cup_matches` and `violations`, and confirm `alembic current` reaches `head`
  before treating the backup as usable.
- A logical dump neither decrypts nor moves Vault secrets. Recreate
  `vmf_api_base_url` and `vmf_cron_secret`, then re-run
  `supabase/cron_fpl_sync.sql` on the new project.
- After switching databases, redeploy the API, check readiness, data and admin
  authentication, and only then re-enable cron.

The free plan has no SLA and no point-in-time recovery. An off-platform backup
and a rehearsed restore are mandatory before the opening weekend, not optional.
