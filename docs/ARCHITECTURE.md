# VMF Fantasy League 2026/27 — Architecture

**Document code:** `VMF-ARCH-2026-27`
**Status:** Production architecture
**Rule source:** [`RULEBOOK.md`](./RULEBOOK.md)

## 1. Architectural goals

The system is a competition engine sitting on top of FPL data. The design must:

- synchronize changing FPL data without losing the trail back to the source;
- compute live results fast enough for 46 managers;
- reproduce an old result exactly;
- keep penalties, replacements and overrides separate from official points;
- handle Double and Blank Gameweeks, postponements, automatic substitutions and
  late point corrections;
- lock results while still allowing an audited administrator reopen;
- never leak phone numbers or Facebook URLs through a public API or a log;
- keep showing the most recent snapshot while the FPL API is failing.

## 2. Deployment shape

A **modular monolith** is recommended for the first season:

```text
Browser
  |
  +-- Next.js web (public + admin UI)
  |
  +-- FastAPI application
        +-- public/admin API
        +-- competition engine
        +-- FPL gateway
        +-- scheduler/worker
        +-- PostgreSQL
        +-- object storage or PostgreSQL JSONB for raw payloads
```

Stack:

```text
Frontend: Next.js + TypeScript + Tailwind
Backend:  Python + FastAPI + Pydantic + SQLAlchemy + Alembic
Database: PostgreSQL
Jobs:     an external scheduler calling an authenticated endpoint
Cache:    PostgreSQL and shared HTTP caching; add Redis only when needed
```

Do not run a scheduler inside every web replica. Exactly one worker holds the
distributed lock, and every job must still be idempotent.

Business modules:

```text
identity
fpl_ingestion
scoring
classic
h2h
cup
discipline
awards
snapshots
admin
audit
```

Modules do not reach into each other's tables at will. Every calculation runs
through a service command with an explicit input revision and ruleset.

## 3. The three mandatory data layers

### 3.1 Raw source layer

The raw layer is append-only evidence of what FPL returned.

`raw_fpl_responses`:

```text
id
endpoint_name
request_key
season_code
gameweek_number
fpl_entry_id nullable
http_status
payload_hash
payload_bytes
payload_json nullable
contract_version
parser_version
correlation_id
first_seen_at
last_seen_at
seen_count
```

Rules:

- the same `request_key + payload_hash` does not create a second logical
  payload; it updates the observation counters;
- a payload with a different hash creates a new revision;
- a parse failure never deletes the payload: store the error and raise a schema
  drift alert;
- raw payloads never contain VMF penalties or overrides;
- secrets, cookies and authorization headers are never stored;
- large shared payloads may be kept by hash only, while small manager-scoped
  evidence is kept in full.

### 3.2 Normalized and derived layers

Normalized source facts are parsed FPL data before any VMF rule applies:

```text
fpl_teams
fpl_players
fpl_fixtures
fpl_player_fixture_stats
manager_pick_snapshots
manager_pick_items
manager_gameweek_history
manager_transfers
manager_chip_events
```

The derived layer is produced by calculation runs:

```text
calculation_runs
manager_player_gameweek_contributions
manager_gameweek_score_calculations
cup_qualification_ledger
h2h_match_calculations
h2h_penalty_ledger
cup_match_calculations
totw_calculations
standing_snapshot_rows
replacement_average_calculations
highlight_calculations
```

Every derived row must be traceable to:

```text
calculation_run_id
ruleset_version
algorithm_version
input_revision_set/hash
calculated_at
```

A finalized derived row is never updated in place. A live materialization may
be upserted for the interface, but the source snapshot and revision must be
kept for debugging.

### 3.3 Decision and override layer

VMF decisions live on their own:

```text
violations
violation_reviews
threshold_actions
admin_score_overrides
admin_penalty_overrides
manager_status_events
league_join_events
random_draws
gameweek_finalization_events
audit_events
```

An override is an overlay; it never edits the raw or derived base:

```text
effective_value =
    active_override
    ?? replacement_value
    ?? calculated_official_value
```

Every override carries `reason`, `actor`, `created_at`, `supersedes_id`, a scope
and the revision from which it takes effect. Cancelling an override means
adding a new event, never deleting the old record.

## 4. Core data model

### 4.1 Configuration and membership

```text
seasons
rulesets
competition_phases
gameweeks
divisions
division_memberships
managers
manager_external_profiles
```

`division_memberships` uses Gameweek ranges:

```text
manager_id
division_id
phase_id
start_gameweek
end_gameweek
source_decision_id
```

A database constraint must prevent two overlapping memberships for the same
manager in the same competition scope.

Personal data belongs outside the public row:

```text
managers                  # registered name, team, public-safe status
manager_private_contacts  # phone, Facebook URL, encrypted at rest
```

### 4.2 Schedules and brackets

```text
h2h_schedule_versions
h2h_matches
cup_competitions
cup_qualification_snapshots
cup_rounds
cup_bracket_versions
cup_matches
```

A schedule or bracket has a state:

```text
draft -> locked -> superseded
```

Editing a locked schedule requires a new version and an administrative
decision, never a silent update.

### 4.3 Ledgers instead of mutable totals

Important totals are built from ledgers:

```text
h2h_table_points =
    sum(h2h_result_ledger.points)
    + sum(h2h_penalty_ledger.points_delta)

cup_qualification_points =
    sum(cup_qualification_ledger.contribution)
```

A threshold action has a unique key:

```text
(manager_id, season_id, threshold_number)
```

so a retried job cannot deduct the same `-6` twice or apply a removal again.

## 5. The player–fixture model for Double Gameweeks

Never store a single player score and overwrite it per fixture. The source
grain must be:

```text
(season_id, gameweek_number, element_id, fixture_fpl_id)
```

`fpl_player_fixture_stats`:

```text
element_id
fixture_fpl_id
gameweek_number
minutes
total_points
goals_scored
assists
yellow_cards
red_cards
bonus
source_raw_id
```

Aggregating to player-Gameweek:

```text
player_gw_base_points = sum(total_points across every fixture in that GW)
player_gw_goals       = sum(goals_scored across every fixture in that GW)
player_gw_cards       = sum(yellow_cards + red_cards across those fixtures)
```

The multiplier belongs to the manager's pick, not to the fixture:

```text
manager_player_contribution = player_gw_base_points * effective_multiplier
```

This avoids multiplying the captain per fixture row and then summing wrongly
when fixture data arrives piecemeal.

Player status inside a matchup:

- `yet_to_play`: a fixture has not started;
- `playing`: at least one fixture is in progress;
- `finished`: every fixture in the Gameweek has ended;
- `postponed`: a fixture is unscheduled or marked postponed by FPL;
- `blank`: no fixture in that Gameweek;
- `unknown`: insufficient data.

In a Double Gameweek a player may have finished the first match yet still count
as remaining because of the second. Store as well:

```text
fixtures_total
fixtures_finished
fixtures_remaining
```

`players_remaining` counts distinct players with an unresolved fixture;
`effective_players_remaining` adds each such player's multiplier once. The
interface displays the fixture count separately.

Never treat a postponed fixture as a finished Gameweek. Fixture-to-event
mapping comes from the FPL revision; if a fixture moves to another Gameweek, a
new calculation run must remove it from the previous aggregate.

## 6. Deadline picks, automatic substitutions and chips

After the deadline, fetch each manager's picks and create an immutable
snapshot:

```text
manager_id
gameweek_number
revision
payload_hash
captured_at
source_raw_id
active_chip
transfer_cost
pick_items
```

Keep both:

```text
original_captain_player_id
original_vice_captain_player_id
original_multiplier
effective_captain_player_id
effective_multiplier
auto_sub_resolution_source
```

While live:

- use the snapshot picks; do not refetch all 40 squads every 60 seconds;
- compute live contributions from player-fixture facts;
- mark automatic substitution and captain resolution as provisional;
- when FPL publishes the final resolution, compare and create a new revision if
  it differs.

Bench Boost gives every bench pick multiplier `1`. Triple Captain changes only
the effective captain's multiplier to `3`. Wildcard and Free Hit affect
transfers and the squad source but never erase the transfer cost published by
FPL.

## 7. Calculation pipeline

A calculation run proceeds in this order:

```text
1. Select the input raw/normalized revisions and the ruleset
2. Aggregate player-fixture -> player-Gameweek
3. Resolve counted picks, automatic substitutions, captain and chip
4. Compute official gross/net and matchup exposure
5. Detect violation candidates
6. Apply the decision, override and replacement overlay
7. Write Classic contributions
8. Write the Cup qualification ledger
9. Compute H2H and Cup matches
10. Compute TotW and highlights
11. Compute standings
12. Publish a snapshot revision
```

Each step must be deterministic given the same input revision, rule version and
override set. A run records `input_hash` and `output_hash`; rerunning the same
input must produce the same output.

Replacement averages are computed before competition scores are resolved but
after the sample's net scores are known. Every locked manager in the same
division and Gameweek uses the same sample snapshot, so no recursion occurs.

## 8. Snapshots and versioning

### 8.1 Snapshot model

`snapshot_sets`:

```text
id
season_id
gameweek_id
revision_number
state
ruleset_version
calculation_run_id
parent_snapshot_id nullable
supersedes_snapshot_id nullable
input_cutoff_at
published_at
finalized_by nullable
finalized_at nullable
snapshot_hash
```

One snapshot set ties together:

- manager scores;
- Classic standings;
- H2H results and standings;
- Cup qualification and matches;
- TotW and highlights;
- matchup details.

An API response must never mix rows from two snapshot revisions.

### 8.2 State machine

```text
upcoming -> live -> provisional -> final
final --admin reopen--> provisional (new revision) -> final (new revision)
```

- A live revision may be published repeatedly.
- Moving to final uses a transaction and an advisory lock per Gameweek.
- A final snapshot is never updated or deleted.
- A late source revision after finalization creates a `source_diff_alert`.
- Only an administrator command with a reason creates a reopen revision.
- A next-round bracket stores `source_final_snapshot_id`; if a re-finalization
  changes a winner, the system raises an impact warning and asks the
  administrator to confirm the bracket migration.

### 8.3 Audit and reproducibility

Every public final result must be able to return:

```text
snapshot_id
revision
ruleset_version
calculated_at
finalized_at
```

Audit payloads use before/after JSON with personal data and secrets redacted.
The audit log is append-only, and the application's database role has no
hard-delete permission on it.

## 9. FPL synchronization

### 9.1 Gateway

Every HTTP call goes through the FPL gateway:

- configurable base URL and endpoint mapping;
- short timeouts, retries with exponential backoff and jitter;
- a concurrency limit;
- schema validation;
- conditional requests and caching where the endpoint supports them;
- a circuit breaker;
- latency, status and schema-error metrics;
- an identifiable user agent, used within the data permission the organisers
  confirmed.

No domain service depends directly on FPL's JSON shape. The parser and adapter
carry their own version.

### 9.2 Job schedule

Before the season:

```text
- sync bootstrap, players, teams and fixtures
- validate the 40 entry IDs
- import managers and division memberships
- generate and lock the H2H schedule
- create the Cup configuration
```

After each Gameweek deadline:

```text
- fetch picks, entry history, chips and transfers for all 46 managers
- retry manager endpoints that are not open yet, with backoff
- persist immutable deadline snapshots
- detect transfer-cost candidates
```

While live:

```text
- on the configured interval: sync shared live player data and fixtures
- fetch each shared payload once per tick
- recalculate when the payload hash or revision changes
- publish a live snapshot
```

Do not refetch 40 squads every minute while the deadline snapshot is unchanged.

After fixtures:

```text
- move to provisional
- reconcile automatic substitutions and the effective captain
- compute tie-breaks, TotW and standings
- wait for the finalization gate or an administrator
```

### 9.3 Idempotency and concurrency

- Job key: `(job_type, season, gameweek, logical_tick/input_hash)`.
- A distributed advisory lock prevents two workers running the same Gameweek.
- Raw and decision inserts rely on unique constraints.
- Publishing a calculation uses compare-and-swap on the current revision.
- A retry must never duplicate a violation, a threshold action, a match result
  or an audit event.

### 9.4 Degraded mode

When FPL fails:

- keep the last successful snapshot;
- show `last_updated_at` and a stale warning;
- do not move a snapshot to final;
- do not replace missing data with `0`;
- queue a retry and alert an administrator past the configured threshold.

## 10. API boundary

Separate routers and schemas:

```text
/api/public/*
/api/admin/*
/api/internal/jobs/*
```

Public responses use allowlisted DTOs; ORM manager rows are never serialized
directly.

Examples:

```text
GET /api/public/gameweeks/{gw}/snapshot
GET /api/public/classic/standings
GET /api/public/h2h/standings
GET /api/public/h2h/matches/{id}
GET /api/public/cups/{id}/bracket
GET /api/public/cups/matches/{id}

POST /api/admin/gameweeks/{gw}/finalize
POST /api/admin/gameweeks/{gw}/reopen
POST /api/admin/violations/{id}/decide
POST /api/admin/overrides
POST /api/admin/random-draws
POST /api/admin/schedules/{id}/lock
```

A mutation requires:

- authentication;
- authorization;
- CSRF protection when cookies are used;
- an `Idempotency-Key`;
- a reason for sensitive actions;
- optimistic concurrency (`expected_revision`);
- an audit entry inside the same transaction.

## 11. Authentication and security

### 11.1 Roles

Minimum RBAC:

```text
public            # public reads only
admin_viewer      # admin views, including personal data when granted
competition_admin # rule decisions, finalization, brackets
super_admin       # account and permission management, personal data export
```

Permission to view standings never implies permission to view personal data.

### 11.2 Sessions

- Use a trusted identity provider or a production-ready auth library.
- Require multi-factor authentication for competition and super administrators
  where the provider supports it.
- Session cookies: `HttpOnly`, `Secure`, `SameSite=Lax` or stricter.
- Sessions are short-lived and revocable.
- If passwords must be implemented directly, hash with Argon2id or bcrypt and
  apply rate limiting and lockout.

### 11.3 Application security

- TLS end to end.
- An exact CORS allowlist.
- CSRF tokens for cookie-authenticated mutations.
- Rate limits on login, admin mutations and expensive public endpoints.
- Validate IDs, enums and ranges with schemas; parameterized SQL through the
  ORM.
- Security headers: CSP, HSTS, frame-ancestors, nosniff.
- Secrets come from a secret manager or the environment and are never
  committed.
- Personal data encrypted at rest, in the application, a KMS or the database.
- Encrypted backups; personal data exports watermarked, audited and expiring.
- Logs redact phone numbers, Facebook URLs, tokens, cookies and raw contact
  payloads.

Public cache keys and CDN responses must never contain admin DTOs or personal
data.

## 12. Observability and operations

Structured logs:

```text
request_id
job_id
season
gameweek
snapshot_revision
calculation_run_id
endpoint_name
duration_ms
result
```

Minimum metrics and alerts:

- FPL sync success, errors and payload age;
- schema drift;
- calculation duration and failures;
- snapshot publication and finalization;
- stale live data;
- worker lock contention;
- pending violations and admin reviews;
- audit write failures;
- backup success and restore drills.

A failed audit write or a failed final-snapshot transaction must roll back the
entire administrative command.

Back up PostgreSQL automatically and test the restore before the season and
periodically. Write runbooks for:

- an FPL outage;
- a bad parser or schema change;
- finalizing the wrong Gameweek;
- a late point correction;
- a compromised administrator account;
- a database restore.

## 13. Release and migration boundaries

Every release contains:

```text
frontend version
backend version
database migration version
ruleset/algorithm version
```

Production migrations follow expand/contract: never drop a column or data in
the same release whose running code still reads it. Seed the 2026/27
configuration through an idempotent migration or command, never by editing the
database by hand.

Environments:

```text
local
staging (replayed or synthetic data with personal data removed)
production
```

Never copy production phone numbers or Facebook URLs into staging. Before GW1,
replay at least one Gameweek covering captaincy, automatic substitutions,
chips, a Double Gameweek, a violation, Cup and H2H, and finalization.

## 14. Architectural decisions that must not be broken

1. Raw, derived and override are three separate layers.
2. Final is an immutable revision, not a boolean on a mutable row.
3. Player-fixture is the source grain for live scoring and Double Gameweeks.
4. Deadline picks are snapshots, not data refetched every tick.
5. Penalties and Cup qualification are ledgers.
6. Public APIs use allowlisted DTOs and never touch the private contact table.
7. Background jobs are idempotent and hold a distributed lock.
8. One standings or matchup response uses one consistent snapshot revision.
