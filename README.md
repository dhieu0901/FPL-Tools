# VMF Fantasy League Management Tool

Competition platform for Văn Minh Fantasy League 2026/27 and its 40 managers.
The application uses Fantasy Premier League as its scoring source and applies
the VMF rulebook on top of it: two Classic divisions, a head-to-head league and
play-offs, two Cups, violations and organiser decisions.

## Layout

```text
apps/web       Next.js public dashboard and admin UI
services/api   FastAPI, rule engine, FPL synchronization and PostgreSQL
docs           Rulebook, architecture, FPL contract and test matrix
supabase       SQL that configures scheduled jobs on Supabase
```

## Non-negotiable principles

- Raw FPL data, VMF-derived results and administrator overrides are stored
  separately; a decision never rewrites the source.
- Deadline squads and finalized results are versioned snapshots.
- Every disciplinary decision, random draw and Gameweek reopen is audited.
- FPL global rank is never used.
- A live score is provisional until the Gameweek is finalized.
- A failed or missing source is recorded as such, never as a score of zero.

## Running locally

Copy `.env.example` to `.env`, replace the placeholder secrets, then start the
database:

```powershell
docker compose up -d postgres
docker compose run --rm migrate
docker compose up --build api web
```

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`

Docker is for local development only. Production runs at no cost on two Vercel
projects (`apps/web` and `services/api`) against one Supabase Free project. The
full procedure, environment variables, migrations, scheduling, quotas and
rollback steps are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Language

The interface ships in Vietnamese and English. Readers switch with the two
flags in the header; the choice is stored in a cookie and pages keep rendering
on the server in the chosen language. Documentation and code are English.
