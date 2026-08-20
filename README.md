# VMF Fantasy League Management Tool

Competition platform for Văn Minh Fantasy League 2026/27 and its 46 managers.
The application uses Fantasy Premier League as its scoring source and applies
the VMF rulebook on top of it: two Classic divisions, a head-to-head league and
play-offs, two Cups, violations and organiser decisions.

## Layout

```text
apps/web       Next.js public dashboard and admin UI
services/api   FastAPI, rule engine, FPL synchronization and PostgreSQL
assets         Brand source files
docs           Rulebook, specification, architecture, FPL contract, tests
scripts        Local quality and maintenance scripts
supabase       SQL that configures scheduled jobs on Supabase
```

The rules the code implements are in [docs/RULEBOOK.md](docs/RULEBOOK.md);
everything else defers to it.

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

The interface, the documentation and the code are English throughout. The
league is played in Vietnam, but the vocabulary of Fantasy Premier League is
English, and managers read those terms on FPL itself every week.

## Competition at a glance

- 46 managers: HIGH 20, LOW 26. Six go up and six come down after each Season.
- Classic Season 1 is GW1–GW19, Season 2 is GW20–GW38 and restarts from zero.
- Head to head is one competition for all 46: group stage GW1–GW35, then a
  top-eight play-off in GW36–GW38.
- Two Cups, drawn after GW13 and GW32, each running six knockout rounds to a
  final and a third-place match.
