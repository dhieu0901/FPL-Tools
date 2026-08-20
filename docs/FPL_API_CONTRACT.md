# VMF Fantasy League 2026/27 — FPL API Contract

**Document code:** `VMF-FPL-CONTRACT-2026-27`
**Contract version:** `1.0.0-draft`
**Related:** [`RULEBOOK.md`](./RULEBOOK.md), [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## 1. Important statement

FPL does not publish the JSON endpoints below as a third-party API with
versioning, an SLA or a compatibility promise. They are web endpoints observed
on the official Fantasy Premier League host.

Therefore:

- this is **VMF's own contract against an unofficial, undocumented API**, not a
  contract FPL guarantees;
- endpoints, fields, types, data-release timing and access limits can change
  without notice;
- an endpoint returning HTTP `200` today creates no SLA for the season;
- VMF must store raw payloads, version its parsers and detect schema drift;
- an error or a missing response must never be read as a score of `0`;
- a Gameweek must not be finalized while a required source is stale or
  quarantined;
- every request follows the data permission the organisers confirmed, at a
  controlled rate;
- never log in automatically, never use a personal cookie or token, and never
  try to bypass the mechanism that hides squads before a deadline.

## 2. Base URL and transport

Production base URL:

```text
https://fantasy.premierleague.com/api/
```

Canonical example:

```text
https://fantasy.premierleague.com/api/bootstrap-static/
```

Gateway rules:

- HTTPS only, with certificate verification;
- allowlist exactly the host `fantasy.premierleague.com`;
- the path must start with `/api/`;
- ID path parameters must be positive integers;
- send `Accept: application/json`;
- use a stable `User-Agent` that identifies the VMF application;
- never send `Authorization`, an FPL session cookie or a CSRF token to these
  endpoints;
- timeouts, retries, concurrency and a response-size limit are configured
  centrally;
- follow redirects only within the same host; a cross-host redirect is refused
  and alerted;
- keep the trailing `/`, which is the canonical form in use.

Never hard-code the base URL in a domain service. Only the gateway knows the
external URL.

## 3. Endpoint registry

### 3.1 Required endpoints

| Code | Method and path | Purpose |
|---|---|---|
| `FPL_BOOTSTRAP` | `GET bootstrap-static/` | Gameweek, player, club and position catalogue plus season metadata |
| `FPL_FIXTURES` | `GET fixtures/` or `GET fixtures/?event={gw}` | Fixtures, kick-offs, status, Double and Blank Gameweeks, postponements |
| `FPL_EVENT_LIVE` | `GET event/{gw}/live/` | Live points and statistics per player and fixture |
| `FPL_ENTRY` | `GET entry/{entry_id}/` | Validate an entry, its current team name and profile state |
| `FPL_ENTRY_HISTORY` | `GET entry/{entry_id}/history/` | Gameweek points, transfer cost, bench points, chip history |
| `FPL_ENTRY_PICKS` | `GET entry/{entry_id}/event/{gw}/picks/` | Squad, captain, multipliers, automatic substitutions, active chip |
| `FPL_ENTRY_TRANSFERS` | `GET entry/{entry_id}/transfers/` | Player in and out history for checks and highlights |

### 3.2 Supporting endpoint

| Code | Method and path | Purpose |
|---|---|---|
| `FPL_ELEMENT_SUMMARY` | `GET element-summary/{player_id}/` | Backfill or reconcile player-fixture history, upcoming fixtures, debugging |

A supporting endpoint is never polled for every player every minute. Live
scoring still uses `event/{gw}/live/` and `fixtures/` as its primary sources.

### 3.3 Optional league endpoints

| Code | Observed method and path | Limited purpose |
|---|---|---|
| `FPL_CLASSIC_LEAGUE` | `GET leagues-classic/{league_id}/standings/?page_standings={page}&phase={phase}` | Help importing or reconciling Classic membership |
| `FPL_H2H_LEAGUE` | `GET leagues-h2h/{league_id}/standings/?page_standings={page}` | Help reconciling H2H membership if the route and schema still work |

Both league endpoints are **optional adapters**:

- VMF computes Classic and H2H standings itself from the 40 registered
  managers;
- rank, H2H table points and match results from an FPL league are never a VMF
  source;
- the H2H route must be smoke-tested each season because its route and schema
  can change;
- if a league endpoint fails, changes schema or is not public, only import and
  reconciliation degrade; VMF scoring keeps working;
- pagination must run until `has_next = false`; never assume the first page
  contains all 46 managers;
- `phase` must come from verified season data or configuration, never
  permanently defaulted to `1`.

If an official FPL H2H match list is ever needed for reconciliation, it must be
added under a new contract version; domain code never infers a URL.

## 4. Public access and data timing

The required endpoints behave as anonymous reads once the corresponding data is
public. "Public" does not mean "always available".

| Endpoint | Auth VMF sends | Expected timing | Meaning when absent |
|---|---|---|---|
| Bootstrap | None | Year round while the season exists | Source failure; use cache within its lifetime |
| Fixtures | None | Once FPL publishes the schedule; it can change | A fixture without a Gameweek may have `event = null` |
| Event live | None | A payload may exist before a Gameweek; it means something once fixtures start | Empty or zero does not prove a final Gameweek or a blank player |
| Entry profile | None | Once a valid entry exists and is public | A single 404 or 403 does not prove a locked or deleted team |
| Entry history | None | History is public; the current Gameweek follows FPL | A missing current row means "not available", never zero |
| Entry picks | None | Another manager's squad may be used only after the deadline | Before the deadline or while opening slowly: sealed or not ready; retry on schedule |
| Entry transfers | None | Ingest only what FPL made public after the deadline | Never poll for transfers that are not public |
| Element summary | None | Usually public once the player catalogue exists | Optional; a failure does not block live scoring |
| League standings | None | Depends on the league, route, schema and current visibility | Optional; never blocks scoring |

VMF never calls an authenticated endpoint to see squads before a deadline. If
FPL moves a required endpoint behind authentication:

1. the circuit breaker stops requests;
2. the system keeps the latest snapshot and alerts an administrator;
3. the organisers evaluate an option FPL permits;
4. logins are never automated and manager credentials are never used to bypass
   a limit.

## 5. Per-endpoint contract

### 5.1 `bootstrap-static/`

```text
GET https://fantasy.premierleague.com/api/bootstrap-static/
```

Collections VMF relies on:

```text
events[]
teams[]
elements[]
element_types[]
phases[]              # if still present in the schema
game_settings         # metadata, never a VMF rule source
```

Minimum normalized fields:

```text
events:      id, name, deadline_time, finished, data_checked,
             is_previous, is_current, is_next
teams:       id, name, short_name
elements:    id, team, element_type, web_name, first_name, second_name,
             now_cost, status
element_types: id, singular_name, squad_select, squad_min_play, squad_max_play
```

Used for the event and deadline catalogue, player, team and position
dimensions, formation validation, interface metadata, scheduler transitions
around a deadline, and event-state reconciliation.

Never used for `total_players`, ownership or popularity, overall rank, or any
field that would override [`RULEBOOK.md`](./RULEBOOK.md).

New fields may be ignored. Missing `events`, `teams`, `elements`, an identity
field, or a team/position relationship quarantines the payload.

### 5.2 `fixtures/`

```text
GET https://fantasy.premierleague.com/api/fixtures/
GET https://fantasy.premierleague.com/api/fixtures/?event={gw}
```

Minimum normalized fields:

```text
id
event nullable
kickoff_time nullable
team_h
team_a
team_h_score nullable
team_a_score nullable
started
finished
finished_provisional nullable
minutes nullable
stats[] nullable
```

Used for the player-fixture grain, fixture status, players remaining and
effective remaining, Double and Blank Gameweeks, postponed and rescheduled
fixtures, and the live/provisional gate.

`event` and `kickoff_time` must accept `null`. A fixture can move to another
Gameweek; a new revision must update the mapping with provenance and must never
edit a finalized history in place.

Never finalize a Gameweek from the `finished` flag of a single response.
Finalization also requires live data, picks, schema health and the rule or
administrator gate.

### 5.3 `event/{gw}/live/`

```text
GET https://fantasy.premierleague.com/api/event/{gw}/live/
```

Observed shape the adapter must support:

```text
elements[]:
  id
  stats:
    minutes, total_points, goals_scored, yellow_cards, red_cards, bonus, ...
  explain[]:
    fixture
    stats[]:
      identifier, points, value
```

Used for live player scores, player-fixture statistics and explanations,
counted goals and cards, bonus and provisional corrections, live H2H and Cup
scores, and remaining status combined with fixtures.

`stats` may gain identifiers between seasons. The parser must:

- keep unknown fields in the raw payload;
- map the fields it knows;
- not fail merely because a new field exists;
- quarantine when `elements[].id` or `stats.total_points` is missing;
- accept an empty `explain` when a player has no fixture or it has not started;
- never invent a per-fixture allocation when the player-Gameweek total has
  points but `explain` is incomplete.

If `explain` changes shape, the live total may remain provisional, but
player-fixture tie-breaks and matchup detail are marked incomplete and must not
be finalized.

### 5.4 `entry/{entry_id}/`

```text
GET https://fantasy.premierleague.com/api/entry/{entry_id}/
```

Minimum normalized fields:

```text
id
player_first_name
player_last_name
name
started_event
current_event
summary_overall_points nullable
leagues nullable
```

Used to validate `fpl_entry_id`, display the current FPL team name next to the
registered VMF name, detect a team-name change for review, and check entry
availability.

Never overwrite the registered VMF name. Never use
`summary_overall_rank`, `summary_event_rank` or any global rank.

A single 404, 403 or 5xx never moves a manager to locked or deleted. The
gateway raises an availability incident; only retries, cross-source
reconciliation and an administrator decision change a business status.

### 5.5 `entry/{entry_id}/history/`

```text
GET https://fantasy.premierleague.com/api/entry/{entry_id}/history/
```

Observed shape:

```text
current[]:
  event, points, total_points, rank nullable, overall_rank nullable,
  bank, value, event_transfers, event_transfers_cost, points_on_bench

chips[]:
  name, time, event

past[] nullable
```

Used for source event points, transfer cost, total-points reconciliation, bench
points, chip history, team value and highlights.

Never ingest `rank` or `overall_rank` into VMF standings.

The initial adapter maps:

```text
source_gross_points = current[].points
transfer_cost       = current[].event_transfers_cost
official_net_points = source_gross_points - transfer_cost
```

Before finalization, check the semantic invariant on sufficiently settled data:

```text
delta(total_points) ~= points - event_transfers_cost
```

If FPL changes the meaning of `points` or `total_points`, the mismatch is
semantic schema drift; never silently subtract the transfer cost twice.

### 5.6 `entry/{entry_id}/event/{gw}/picks/`

```text
GET https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gw}/picks/
```

Observed shape:

```text
active_chip nullable
automatic_subs[] nullable
entry_history:
  event, points, total_points, event_transfers, event_transfers_cost,
  points_on_bench
picks[]:
  element, position, multiplier, is_captain, is_vice_captain
```

Used for the deadline squad snapshot, starting XI and bench positions, the
original captain and vice, multipliers and counted picks, the active chip,
automatic-substitution reconciliation, and a transfer-cost cross-check.

Timing:

- fetch first after the deadline;
- retry with backoff while the response is not open yet;
- do not fetch all 40 squads on every live tick;
- refresh at phase transitions, especially once fixtures finish, because FPL can
  re-resolve multipliers and automatic substitutions;
- any payload with a different hash creates a new pick snapshot revision.

Never treat `multiplier = 0` in an unsettled payload as the final bench or
auto-sub decision. Keep the original selection facts and the effective
resolution as separate revisions.

The current Gameweek's picks before its deadline are sealed data. VMF must not
try an authenticated endpoint or poll aggressively to see them early.

### 5.7 `entry/{entry_id}/transfers/`

```text
GET https://fantasy.premierleague.com/api/entry/{entry_id}/transfers/
```

Minimum normalized fields:

```text
element_in, element_out, element_in_cost, element_out_cost, entry, event, time
```

Used for the transfer list, best and worst transfer estimates, reconciling the
transfer count, and violation investigation.

`event_transfers_cost` from entry history or the picks entry history remains the
authoritative transfer cost. Never derive a cost from the number of transfer
rows: free transfers, chips and FPL rule changes make that inference wrong.

Ingest only transfers FPL published after the deadline. Never use this endpoint
to observe behaviour before a deadline.

### 5.8 `element-summary/{player_id}/`

```text
GET https://fantasy.premierleague.com/api/element-summary/{player_id}/
```

Observed shape:

```text
fixtures[]:     id, event nullable, kickoff_time nullable, is_home, difficulty
history[]:      element, fixture, round, total_points, minutes, goals_scored,
                yellow_cards, red_cards, bonus, ...
history_past[] nullable
```

Used to backfill or repair player-fixture history, reconcile Double Gameweeks
and postponements, support administrator diagnostics, and power a player detail
page if one exists.

Never use it as the primary live polling source. Fetch it only on demand, when
contract reconciliation finds a missing player-fixture, after finalization for
backfill, or during replay and testing.

If element summary and event live disagree while a Gameweek is unfinalized,
keep both revisions and mark reconciliation pending. After finalization, the
source chosen as authoritative must be recorded by the adapter or rule version;
never update silently.

### 5.9 Optional league standings

Classic URL template:

```text
GET https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/?page_standings={page}&phase={phase}
```

Minimum shape when the adapter is enabled:

```text
league:
  id, name

standings:
  page, has_next
  results[]:
    entry, entry_name, player_name, rank nullable, total nullable
```

The H2H URL template that needs a smoke test:

```text
GET https://fantasy.premierleague.com/api/leagues-h2h/{league_id}/standings/?page_standings={page}
```

The H2H adapter may be enabled only once a runtime contract test confirms that
the route returns JSON, carries league identity, exposes paginated standings
with entry IDs, and matches the parser version.

Both adapters emit only:

```text
league_id
league_name
member_entry_ids
observed_at
source_revision
```

League rank and totals never enter VMF Classic or H2H. If a Season 2 join needs
checking, a membership observation only creates a candidate; the administrative
or rule workflow decides the violation.

## 6. Endpoint to module mapping

| Module | Primary source | Cross-check |
|---|---|---|
| Manager registration | Entry profile | Optional Classic/H2H league |
| Event scheduler | Bootstrap events | Fixtures |
| Player and team catalogue | Bootstrap | Element summary on demand |
| Deadline squad, chip, captain | Entry picks | Entry history and chips |
| Transfer cost | Entry history and picks entry history | Transfer list |
| Live player score | Event live | Fixtures, element summary on demand |
| Double/Blank/postponed | Fixtures and live explain | Element summary |
| Classic score | Derived picks and live plus history cost | History total reconciliation |
| H2H and Cup score | VMF derived effective score | Never an FPL league rank or result |
| Goals and cards tie-break | Counted picks and live player-fixture | Element summary after finalization |
| Locked or deleted detection | Availability incident plus administrator decision | Entry, history and picks responses |
| Season 2 membership | VMF administrative registry | Optional league standings |
| Transfer highlights | Transfers and player-fixture stats | History transfer count |

No endpoint provides a "VMF score". The competition engine always applies
[`RULEBOOK.md`](./RULEBOOK.md) to source facts.

## 7. Caching and cadence

Every value below is a configurable default. The scheduler adds jitter so
requests do not arrive in a burst.

| Endpoint | Outside live | Near a deadline or transition | While fixtures are live | After fixtures until final |
|---|---:|---:|---:|---:|
| Bootstrap | 30 min | 5 min | 5 min | 5–15 min |
| Fixtures for a Gameweek | 15 min | 5 min | 60 s | 2–5 min |
| Event live | Do not poll a future Gameweek | 5 min readiness check | 60 s | 2–5 min, then 15 min |
| Entry profile | 6 h | Validate once | 6 h | Once a day |
| Entry history | 6 h | After the deadline | 10–15 min | 5 min while reconciling |
| Entry picks | Do not fetch a sealed Gameweek | Retry 30–120 s after the deadline | Not every tick; 10–15 min | 2–5 min until auto-subs settle |
| Entry transfers | Do not poll pre-deadline | Once after picks open | 30–60 min | Once to reconcile |
| Element summary | 6 h or on demand | On demand | Only to repair | Backfill or on demand |
| League standings | 30–60 min | 5–15 min while checking a join | Not needed | On demand |

Mandatory optimizations:

- bootstrap, fixtures and event live are a shared cache for all 46 managers;
- each shared URL is fetched once per tick;
- the cache key covers endpoint, path and query;
- the parser output cache key adds the raw payload hash and the parser version;
- a calculation runs only when a source revision or a decision revision
  changes;
- use ETag and `If-None-Match` when the server offers them, without depending
  on their presence.

Never poll element summary as "every player, every minute".

Free-tier note: the schedule that ships in `supabase/cron_fpl_sync.sql` runs
every five minutes rather than every 60 seconds, because each tick costs a
serverless invocation. Raise the frequency for live Gameweeks only after
checking the hosting quota.

## 8. Raw payloads, versions and schema drift

### 8.1 Raw record

Every request attempt stores metadata:

```text
endpoint_code
canonical_url_without_secret
path_params
query_params
requested_at
received_at
http_status
response_headers_allowlist
payload_hash nullable
payload_json nullable
response_size
contract_version
parser_version
correlation_id
error_class nullable
```

Never store cookies, auth headers or unnecessary response headers. For a
non-JSON or error body, store only a size-limited, sanitized excerpt.

A successful raw payload is append-only:

- the same endpoint, request key and hash may deduplicate the body while still
  recording the observation;
- a payload with a different hash creates a new source revision;
- raw data is never edited when a parser or a rule changes;
- keep raw data for the whole 2026/27 season and through whatever audit window
  the organisers require.

### 8.2 Versions

Three independent versions:

```text
contract_version   # endpoint, field and timing contract
parser_version     # JSON -> normalized source facts
ruleset_version    # source facts -> VMF result
```

Every calculation run stores all three. Changing a parser must never be
disguised as changing a rule.

### 8.3 Drift policy

| Type | Example | Handling |
|---|---|---|
| Additive | FPL adds a stats field | Keep raw, map later; do not block |
| Nullable | A required field becomes `null` | Accept only if the contract allows null; otherwise quarantine |
| Missing required | `elements[].id` disappears | Quarantine that endpoint revision |
| Type change | An ID becomes an object | Quarantine and alert |
| Enum expansion | A new status value | Store the unknown value; never map it onto an old one |
| Semantic | `points` starts including the transfer cost | Invariant fails; block finalization and raise the parser or contract version |
| Route/status | 404 or HTML instead of JSON | Circuit breaker, stale mode, alert |

The parser is a tolerant reader for new fields and strict about identity and
invariants. "Catch everything and default to `0`" is never acceptable.

Automated contract tests:

- run against version-controlled raw fixtures;
- smoke-test the production endpoints read-only;
- compare required fields, types and nullability;
- run the semantic invariants;
- report the difference before a new parser is deployed.

## 9. Retries, circuit breaker and staleness

### 9.1 Response classification

| Situation | Retry within the tick | Action |
|---|---|---|
| Network timeout or reset | Yes, up to 3 attempts | Exponential backoff with jitter |
| HTTP 429 | Follow `Retry-After`; never spam | Throttle or open the circuit for that endpoint |
| HTTP 500/502/503/504 | Yes, up to 3 attempts | Then hold stale data and wait for the next tick |
| HTTP 401/403 | No aggressive retry | Alert that the access contract changed |
| HTTP 404 on picks around a deadline | Retry on the readiness schedule | Classify as `sealed_or_not_ready`, never zero |
| HTTP 404 on an entry that used to be valid | Limited retries plus an availability incident | Never lock or delete the manager automatically |
| HTTP 404 on an ID that was never valid | Do not retry repeatedly | Validation error or administrator review |
| HTTP 200 with HTML or non-JSON | Do not parse | Quarantine plus circuit breaker |
| HTTP 200 JSON with the wrong schema | Do not publish a normalized revision | Quarantine and alert |

A reasonable default backoff is `1s, 3s, 9s` plus jitter. After three attempts,
hand control back to the scheduler; never busy-loop.

The circuit breaker is per endpoint code. A failure in an optional league or
element-summary endpoint must not open the circuit for the live endpoint.

### 9.2 Staleness

Every snapshot and public response must carry:

```text
source_observed_at
calculated_at
last_success_at
is_stale
stale_reason
snapshot_revision
```

Default warnings:

- live and fixtures: stale after more than three refresh cycles;
- bootstrap transitions: stale after 15 minutes;
- current-Gameweek picks: missing after the deadline plus a configured grace
  window;
- manager history: stale if not reconciled while preparing provisional or final.

While stale:

- keep showing the last successful snapshot;
- label the interface as slow to update and show the last update time;
- never turn a missing player or manager into `0`;
- never derive a winner, TotW, penalty or next-round bracket from a partial
  revision;
- never finalize the Gameweek;
- show the affected endpoints and managers on the admin dashboard.

### 9.3 Finalization gate

A Gameweek is eligible for finalization only when:

1. its fixtures are resolved in the current revision;
2. the event live payload matches the required schema;
3. picks and history exist for every active manager, or the manager has a valid
   replacement or status decision;
4. transfer costs are reconciled;
5. automatic substitutions and the effective captain have enough data;
6. no required source revision is quarantined or stale;
7. the necessary violation candidates have been reviewed, or the finalization
   policy explicitly allows them to stay pending;
8. the calculation run used one consistent input revision set.

A single `finished` or `data_checked` field is not the whole finalization
contract. Administrator or rule finalization creates the immutable final
snapshot described in the architecture.

## 10. Data quality and reconciliation

Minimum invariants:

```text
the entry response id equals the requested entry_id
pick elements exist in the bootstrap elements
fixture team_h and team_a exist in the bootstrap teams
a live element id exists in the player catalogue
explain.fixture exists in fixtures, or is marked unresolved
the Gameweek is within 1..38
pick positions are unique inside a squad snapshot
there is exactly one original captain and one original vice-captain
a transfer event maps to a Gameweek
history transfer cost equals the picks entry_history transfer cost once both
    have settled
```

A mismatch never picks a source silently:

- keep both raw revisions;
- create a reconciliation issue;
- define source precedence by parser and contract version;
- block the affected results from finalization.

An unrelated optional mismatch may leave the rest of the Gameweek unblocked,
but the reason must be recorded machine-readably.

## 11. Security and privacy

- The gateway never accepts an arbitrary URL from a user request; only an
  endpoint code and typed parameters.
- Validate numeric ranges to prevent path traversal and SSRF.
- A response size limit prevents an abnormal payload from exhausting memory.
- Never proxy a raw FPL payload straight to a public API.
- Public APIs use VMF DTOs and strip every phone number, Facebook URL and
  administrator note.
- Never log a full manager contact record alongside a source payload.
- Never use global rank, even though the payload contains it.
- A league member list is used only inside an administrative workflow the
  organisers allow; nothing beyond the competition scope is published.

## 12. Suggested configuration

```text
FPL_API_BASE_URL=https://fantasy.premierleague.com/api/
FPL_HTTP_CONNECT_TIMEOUT_SECONDS=3
FPL_HTTP_READ_TIMEOUT_SECONDS=10
FPL_HTTP_MAX_ATTEMPTS=3
FPL_HTTP_MAX_CONCURRENCY=4
FPL_LIVE_REFRESH_SECONDS=60
FPL_LIVE_STALE_AFTER_SECONDS=180
FPL_RESPONSE_MAX_BYTES=<benchmarked limit>
FPL_CONTRACT_VERSION=1.0.0-draft
FPL_ENABLE_CLASSIC_LEAGUE_ADAPTER=false
FPL_ENABLE_H2H_LEAGUE_ADAPTER=false
```

Secrets never live in a configuration file in the repository. The two league
adapters are enabled per season after a smoke test; core scoring never depends
on them.

## 13. Gateway acceptance criteria

1. Every required endpoint goes through the same gateway.
2. No request carries an FPL credential or cookie.
3. Picks are never accessed before a deadline.
4. A shared live endpoint is fetched once per tick.
5. The raw payload and its hash are stored before parsing.
6. Rerunning the same raw payload and parser produces the same normalized
   output.
7. A new field does not break the parser while the invariants hold.
8. A missing, type or semantic drift forces quarantine and an alert.
9. A 404 or a timeout never turns a score into `0`.
10. A stale required source blocks finalization.
11. An optional league failure does not block VMF Classic or H2H.
12. VMF standings never use a rank or total from an FPL league endpoint.
13. A Double Gameweek keeps provenance down to `player_id + fixture_id`.
14. Transfer cost is cross-checked between history and picks.
15. Locked or deleted status only ever results from an administrative workflow,
    never from an HTTP error.
16. Contract, parser and ruleset versions appear in the calculation provenance.

## 14. Runbook when an endpoint changes

When a schema, route or access alert appears:

1. stop publishing normalized revisions for the affected endpoint;
2. keep the last known good snapshot and show the stale banner;
3. store the sanitized response or error;
4. run the contract difference on staging;
5. decide whether the drift is additive, breaking or semantic;
6. update the fixture tests and the parser under a new version;
7. replay at least an ordinary Gameweek, a Double Gameweek, a captaincy and
   auto-sub case, and a transfer-cost case;
8. deploy the parser;
9. backfill from raw payloads if needed;
10. reopen finalization only after reconciliation passes.

Never hot-fix by editing a raw row or defaulting a missing field to `0`.
