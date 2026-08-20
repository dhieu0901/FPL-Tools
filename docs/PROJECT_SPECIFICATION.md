# VMF Fantasy Premier League Management Tool
## Project Specification for AI Coding Agents

**Project name:** VMF Fantasy League Management Tool
**Target competition:** Văn Minh Fantasy League
**Primary platform:** Fantasy Premier League
**Initial scale:** 40 managers
**Main objective:** Build a web-based league management system that reads Fantasy Premier League data, calculates internal live standings, manages custom H2H and Cup competitions, and supports administrative rules specific to VMF.

> **Authority note.** This document is the original brief. Where it disagrees
> with [`docs/RULEBOOK.md`](docs/RULEBOOK.md), the rulebook wins: it records the
> decisions the organisers confirmed for the 2026/27 season. The clauses that
> changed have been updated in place and are marked **Amended**.

---

# 1. Project Overview

The system manages a private Fantasy Premier League competition with 40 managers.

It must not rely on the global FPL overall rank. Instead, it must calculate rankings only among managers registered in the VMF system.

The 40 managers participate in several parallel competitions:

1. Classic competition divided into HIGH League and LOW League.
2. One common H2H competition for all 40 managers.
3. Two knockout Cup competitions, one in each half-season.
4. Monthly and season awards.
5. Manager highlights and administrative monitoring.

The application should use FPL team IDs as the main external identifier for each manager.

---

# 2. Main Project Goals

The system must:

- Import and manage 40 FPL managers.
- Retrieve manager, squad, transfer, chip, player, fixture, and live-score data from FPL.
- Calculate live Gameweek points for each manager.
- Calculate internal live rank in HIGH League and LOW League.
- Manage two Classic seasons:
  - Season 1: GW1-GW19.
  - Season 2: GW20-GW38.
- Promote and relegate managers between HIGH and LOW after GW19.
- Manage a 40-manager H2H league.
- Generate and store H2H schedules.
- Track live H2H results.
- Manage H2H play-offs in GW36-GW38.
- Manage two VMF Cup competitions.
- Apply VMF-specific tie-break rules.
- Detect excessive transfer-hit violations.
- Allow administrators to override scores and penalties.
- Show detailed matchup comparisons such as same players, differentials, captains, players remaining, and live status.

---

# 3. Explicit Non-Goals

The first version does not need to:

- Calculate or display global FPL overall rank.
- Crawl all FPL managers.
- Reproduce every feature of the official FPL website.
- Support public user registration.
- Support multiple unrelated communities.
- Calculate advanced win probability.
- Build a mobile application.
- Automatically make irreversible disciplinary decisions without administrator confirmation.

---

# 4. Manager Registration Data

Each manager record must contain:

```text
manager_id
fpl_entry_id
manager_name
team_name
phone_number
facebook_url
division
active_status
registration_status
season_joined
locked_or_deleted_status
created_at
updated_at
```

Important rules:

- Manager name cannot be changed during the competition.
- Team name cannot be changed during the competition.
- `fpl_entry_id` is the unique identifier used to retrieve FPL data.
- The system should detect changes in team name but should not automatically overwrite the registered VMF team name without an admin action.
- A manager can be active, suspended, removed, locked, deleted, or pending review.

---

# 5. Competition Structure

## 5.1 Classic Competition

There are two Classic divisions:

```text
HIGH League: 20 managers
LOW League: 20 managers
```

There are two independent Classic seasons.

### Season 1

```text
Gameweeks: GW1-GW19
HIGH: 20 managers
LOW: 20 managers
```

At the end of GW19:

- Bottom 6 of HIGH are relegated to LOW.
- Top 6 of LOW are promoted to HIGH.
- New HIGH and LOW memberships apply from GW20.
- Season 2 points reset to zero.
- Full-season points remain available for statistics.

### Season 2

```text
Gameweeks: GW20-GW38
HIGH: 20 managers
LOW: 20 managers
```

At the end of Season 2:

- Bottom 6 of HIGH are relegated for the next competition period.
- Top 6 of LOW are promoted.
- Bottom 6 of LOW must reapply if they want to continue in the next season.

### Required Classic score types

The system must keep these separately:

```text
season_1_points
season_2_points
full_season_points
current_gameweek_points
current_gameweek_net_points
transfer_cost
```

### Classic ranking

Rank must only be calculated inside the manager's current division.

Ranking order:

```text
1. Season net FPL points, descending
2. Configurable secondary rule if required
```

Do not use FPL global rank.

The system should support tied ranks using competition ranking:

```text
1, 2, 2, 4
```

SQL equivalent:

```sql
RANK() OVER (
    PARTITION BY season_id, division_id
    ORDER BY season_points DESC
)
```

---

## 5.2 H2H Competition

All 40 managers join one common H2H competition.

### Group stage

```text
GW1-GW35
40 managers
35 matches per manager
```

Managers do not need to face all 39 other managers.

The full schedule should be generated before the season and locked.

Recommended conditions:

- Each manager plays once per Gameweek.
- No manager faces themselves.
- Avoid duplicate matchups where possible.
- Home and away status is cosmetic unless later rules use it.
- The schedule must be editable by an administrator before being locked.

### H2H scoring

```text
Win: 3 points
Draw: 1 point
Loss: 0 points
```

The match score is based on net Gameweek points after transfer hits.

Example:

```text
Manager A gross GW points: 72
Transfer cost: 4
Manager A net GW points: 68
```

The net score of 68 is used for the H2H result.

### H2H standings fields

```text
rank
played
wins
draws
losses
points_for
points_against
point_difference
h2h_table_points
net_fpl_points
```

Recommended ranking order:

```text
1. H2H table points
2. Point difference
3. Points for
4. Number of wins
5. Full net FPL points
6. Administrator draw if still tied
```

This ranking order should be configurable.

### H2H play-offs

**Amended.** Top 8 managers after GW35 qualify.

```text
GW36: Quarter-finals
GW37: Semi-finals
GW38: Final only
```

There is **no third-place match in H2H**. The two losing semi-finalists share
third place. Only the Cup plays a third-place match, because its prize
structure separates third from fourth.

The boundary between 8th and 9th is resolved by the boundary rule in
[`docs/RULEBOOK.md`](docs/RULEBOOK.md) §7 - H2H table points, then cumulative
TotW, then highest single Gameweek score, then an audited administrator draw -
rather than by the display ranking order below.

Recommended seeding:

```text
Quarter-final 1: 1st vs 8th
Quarter-final 2: 4th vs 5th
Quarter-final 3: 2nd vs 7th
Quarter-final 4: 3rd vs 6th
```

Semi-final pairing should follow a fixed bracket.

If a play-off match is tied, use the same tie-break rules as the Cup.

---

## 5.3 VMF Cup

There are two Cup competitions.

## Cup Season 1

Qualification ranking is taken after GW14.

```text
Rank 1-2 in HIGH: direct entry to Round of 16
Rank 1-2 in LOW: direct entry to Round of 16
Rank 3-14 in HIGH: preliminary round
Rank 3-14 in LOW: preliminary round
```

Schedule:

```text
GW15: Preliminary round
GW16: Round of 16
GW17: Quarter-finals
GW18: Semi-finals
GW19: Final and third-place match
```

Numbers:

```text
4 direct qualifiers
24 preliminary participants
12 preliminary winners
16 total teams in Round of 16
```

## Cup Season 2

**Amended.** Cup Season 2 uses exactly the same structure as Cup Season 1.
Qualification ranking is taken after GW33 and is computed over GW20-GW33.

```text
Rank 1-2 in HIGH: direct entry to Round of 16
Rank 1-2 in LOW: direct entry to Round of 16
Rank 3-14 in HIGH: preliminary round
Rank 3-14 in LOW: preliminary round
```

```text
GW34: Preliminary round
GW35: Round of 16
GW36: Quarter-finals
GW37: Semi-finals
GW38: Final and third-place match
```

### Cup qualification table

**Amended.** Each Cup has its own qualification ledger, independent of the
Classic table:

```text
cup_qualification_points = sum(contribution per Gameweek)

confirmed excessive-transfer violation in that Gameweek -> contribution = 0
not yet eligible because the Season 2 league was not joined -> contribution = 0
otherwise -> contribution = effective net points
```

Every Gameweek carrying a confirmed violation inside GW1-GW14 or GW20-GW33 is
zeroed in that ledger, not only the Gameweek in which a Cup tie is played. The
zero affects the Cup qualification table alone: it never changes Classic
points, raw FPL data, or a played H2H group result.

### Cup match score

Cup match score is the manager's net Gameweek score after transfer hits, unless the manager violated a rule that invalidates the score.

### Cup tie-break rules

When two managers have the same Cup match score, apply these rules in order:

```text
1. Higher cumulative TotW count up to and including the current Gameweek
2. Higher captain points in the current Gameweek
3. More goals scored by counted players in the current Gameweek
4. Fewer cards received by counted players in the current Gameweek
5. Higher current Classic season points up to that Gameweek
6. Random draw performed by the administrator
```

---

# 6. Definition of TotW

`TotW` means the manager with the highest net Gameweek score among all 40 VMF managers.

It includes chip effects.

It uses net Gameweek points after transfer hits.

Example:

```text
Manager A: 96 gross points, Bench Boost, transfer cost 4
Net score: 92

Manager B: 90 gross points, no chip, transfer cost 0
Net score: 90

TotW: Manager A
```

If multiple managers have the same highest net Gameweek score:

- All tied managers receive one TotW.
- Each tied manager's cumulative TotW count increases by one.

Required fields:

```text
is_totw
totw_rank
cumulative_totw_count
```

---

# 7. Counted Squad Definition

Many statistics are based only on players whose points count toward the manager's final Gameweek score.

Counted players include:

- Starting XI players who remain in the final XI.
- Automatic substitutes who replace non-playing starters.
- Captain or vice-captain as resolved by FPL rules.
- Bench players when Bench Boost is active.

Counted players exclude:

- Bench players whose points do not count.
- Players removed by auto-sub resolution.
- Non-playing players who are not replaced.
- Players not selected in the manager's FPL squad.

The system should distinguish:

```text
selected_in_squad
selected_in_starting_xi
counted_in_final_xi
counted_due_to_bench_boost
auto_subbed_in
auto_subbed_out
```

---

# 8. Captain Points

Captain points used in Cup and H2H tie-breaks are the captain's final contribution after multiplier.

Examples:

```text
Captain base points: 8
Normal captain contribution: 16

Triple Captain base points: 8
Triple Captain contribution: 24
```

If the captain does not play and vice-captain takes over:

- Use the vice-captain's multiplied contribution.

Required fields:

```text
original_captain_player_id
effective_captain_player_id
captain_multiplier
captain_base_points
captain_contribution_points
```

---

# 9. Goals and Cards for Tie-Breaks

## Goals

Count the actual number of goals scored by counted players.

Examples:

```text
A counted player scores 2 goals: count 2
A captain scores 2 goals: count 2, not 4
A benched player scores 1 goal without Bench Boost: count 0
A benched player scores 1 goal with Bench Boost: count 1
```

Do not count goals scored by the player's Premier League club unless the selected player personally scored.

## Cards

Count cards received by counted players.

Recommended storage:

```text
yellow_cards
red_cards
total_cards
```

Default tie-break value:

```text
total_cards = yellow_cards + red_cards
```

A lower total is better.

The system may later introduce weighted card values, but the initial version should count each yellow or red card as one card.

---

# 10. Transfer-Hit Rules and Violations

A manager may take a maximum transfer cost of 8 points in one Gameweek without violating VMF rules.

Examples:

```text
Transfer cost 0: no violation
Transfer cost 4: no violation
Transfer cost 8: no violation
Transfer cost 12: one violation
Transfer cost 20: two violations
Transfer cost 28: three violations
```

Violation formula:

```python
if transfer_cost <= 8:
    violation_count = 0
else:
    violation_count = ceil((transfer_cost - 8) / 8)
```

Equivalent examples:

```text
-12 = 1 violation
-16 = 1 violation
-20 = 2 violations
-24 = 2 violations
-28 = 3 violations
```

### Cumulative counting

**Amended.** The violation counter accumulates across GW1-GW38 and does not
reset at GW20. A single Gameweek can cross several thresholds at once:

```text
transfer cost 20 -> triggers threshold 1 and threshold 2 immediately
transfer cost 28 -> triggers thresholds 1, 2 and 3 immediately
```

Each threshold action is applied at most once per manager per season, keyed by
`(manager_id, season_id, threshold_number)`, so a retried job cannot deduct the
same 6 H2H points twice.

### Disciplinary effects

#### First violation

- The manager's conduct deposit is confiscated into the common fund.
- In Cup:
  - The violating Gameweek score is invalid.
  - In a knockout match, the opponent receives a walkover.
- In H2H:
  - Deduct 6 points from H2H table points.
  - In a knockout match, the opponent receives a walkover.
- The administrator may need to adjust the play-off schedule.

#### Second violation

- The manager may receive only 50% of any prize.
- The manager is removed from H2H.
- The manager is removed from Cup.

#### Third violation

- The manager is removed from the competition.

### Forgotten chip exception

If a manager made many transfers but claims they forgot to activate a chip:

- The system flags the case.
- No irreversible penalty is applied automatically.
- An administrator reviews the case.
- The administrator's decision is final.

Required violation statuses:

```text
detected
pending_review
approved_exception
confirmed
rejected
overridden
```

Required admin actions:

```text
approve exception
reject exception
change violation count
apply H2H deduction
invalidate Cup score
remove manager from competition
restore manager
add admin note
```

---

# 11. Failure to Join New League

After GW19, managers must join the new FPL league announced by the organizer before GW20.

Failure to join is counted as one violation.

Consequences:

- Classic and Cup scoring begins again only from the Gameweek in which the manager joins.
- H2H continues as normal.
- The event must be manually reviewable by an administrator.

Required fields:

```text
season_2_league_joined
season_2_join_gameweek
join_violation_applied
```

---

# 12. Locked or Deleted FPL Team

**Amended.** If a manager's FPL team is locked or deleted:

- From the affected Gameweek onward, replace that manager's Gameweek score with
  the average net Gameweek score of the **division that manager belongs to in
  that Gameweek**. Each Gameweek therefore has two independent averages, one
  for HIGH and one for LOW; the other division is never used.
- Do not include the locked or deleted manager in the average.
- Exclude every replacement score from the sample, so several locked teams in
  one division all use the same original sample and no recursion occurs.
- If the sample is empty, do not borrow the other division's average: move the
  score to `pending_review` for an administrator.
- Use standard half-up rounding.

Rounding rule:

```text
Decimal part below 0.5: round down
Decimal part 0.5 or above: round up
```

Examples:

```text
67.42 -> 67
67.50 -> 68
67.81 -> 68
```

Python implementation:

```python
from decimal import Decimal, ROUND_HALF_UP

rounded_score = int(
    Decimal(str(average_score)).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP
    )
)
```

Required fields:

```text
score_source = official | replacement_average | admin_override
replacement_average_raw
replacement_average_rounded
locked_from_gameweek
```

---

# 13. Live Scoring

The application should support four score states:

```text
upcoming
live
provisional
final
```

Definitions:

- `upcoming`: No relevant fixture has started.
- `live`: At least one counted or selected player is currently playing.
- `provisional`: All fixtures have ended, but FPL may still revise points.
- `final`: The Gameweek is considered finalized by the system or administrator.

The application should show live scores but clearly mark them as provisional until finalization.

The system must not calculate global overall rank.

It only needs to:

```text
1. Calculate live score for each registered manager
2. Calculate live rank inside HIGH or LOW
3. Calculate H2H live score
4. Calculate Cup live score
5. Show live matchup details
```

---

# 14. Live Matchup Comparison

Each H2H or Cup matchup should have a detailed comparison page.

Header example:

```text
HIEU FC                     DATA UNITED
58              LIVE              52

Division rank: 3            Division rank: 7
Players remaining: 2        Players remaining: 3
Effective remaining: 3      Effective remaining: 4
```

Required sections:

```text
Same players
Manager A differentials
Manager B differentials
Captain differences
Players finished
Players currently playing
Players yet to play
Bench points
Chip used
Transfer cost
Current tie-break status
```

## Same-player logic

For each player:

```python
net_multiplier = multiplier_manager_a - multiplier_manager_b
```

Interpretation:

```text
net_multiplier = 0:
Player is fully neutralized.

net_multiplier > 0:
Player is a differential for Manager A.

net_multiplier < 0:
Player is a differential for Manager B.
```

Example:

```text
Manager A has Salah as captain: multiplier 2
Manager B has Salah normally: multiplier 1

Net multiplier for Manager A: 1
```

## Remaining-player logic

Display both:

```text
players_remaining
effective_players_remaining
```

Example:

```text
Salah captain yet to play: 1 player, 2 effective players
Palmer yet to play: 1 player, 1 effective player

Total: 2 players remaining, 3 effective players remaining
```

Fixture status options:

```text
yet_to_play
playing
finished
postponed
blank
unknown
```

---

# 15. Manager Highlights

The system should calculate highlights for each Gameweek and each Classic season.

Initial highlights:

```text
Manager of the Week
Biggest Rank Rise
Biggest Rank Fall
Best Transfer
Worst Transfer
Most Bench Points
Highest Team Value
Lowest Team Value
Most Transfers
Least Transfers
Highest Gameweek Score
```

## Manager of the Week

Manager with the highest net Gameweek score among all 40 managers.

## Biggest Rank Rise

```text
previous_division_rank - current_division_rank
```

## Biggest Rank Fall

```text
current_division_rank - previous_division_rank
```

## Bench Points

Points earned by players who remain on the bench and do not count.

When Bench Boost is active:

- Bench points counted toward the manager's score should not be treated as wasted bench points.

## Transfer performance

Recommended formula:

```text
transfer_gain =
points_from_players_bought
- points_from_players_sold
- transfer_cost
```

This metric should be labeled as an estimate because exact attribution can be ambiguous when there are multiple transfers.

---

# 16. Monthly and Season Awards

The system should support configurable award periods.

Required award types:

```text
Monthly winner
Season 1 winner
Season 2 winner
Highest single Gameweek score
```

The definition of a month should follow the organizer's configured Gameweek grouping, not necessarily the calendar month.

Recommended table:

```text
award_periods
award_type
start_gameweek
end_gameweek
division_scope
winner_manager_id
winning_score
status
```

---

# 17. Recommended Application Pages

## 17.1 Public Dashboard

Show:

```text
Current Gameweek
Current season
HIGH leader
LOW leader
H2H leader
Live H2H matches
Current Cup round
Recent highlights
Latest warnings or announcements
```

## 17.2 Manager List

Columns:

```text
FPL Team ID
Manager
Registered Team Name
Current FPL Team Name
Division
Status
Season 2 Join Status
Violation Count
```

## 17.3 Classic Standings

Filters:

```text
Season 1
Season 2
Full season

HIGH
LOW
```

Columns:

```text
Rank
Rank change
Team
Manager
GW gross points
Transfer cost
GW net points
Season points
Full-season points
Chip
Status
```

## 17.4 H2H

Tabs:

```text
Standings
Fixtures
Results
Play-off bracket
Match detail
```

## 17.5 Cup

Tabs:

```text
Season 1 Cup
Season 2 Cup
Qualification standings
Preliminary round
Bracket
Match detail
Tie-break explanation
```

## 17.6 Highlights

Filters:

```text
Gameweek
Season
Division
All managers
```

## 17.7 Admin Panel

Functions:

```text
Add or remove manager
Import manager list
Assign division
Promote and relegate
Generate H2H schedule
Lock H2H schedule
Create Cup draw
Change Cup pairing
Review violations
Apply penalties
Override scores
Mark Gameweek final
Manage locked or deleted teams
Manage season league join status
Add administrative notes
Export standings
```

---

# 18. Recommended Technical Architecture

## Frontend

```text
Next.js
TypeScript
Tailwind CSS
React Query or TanStack Query
```

## Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
```

## Database

```text
PostgreSQL
```

SQLite may be used only for early local prototyping.

## Background jobs

**Amended.** The season runs on free hosting, where no long-lived worker
process exists. Scheduled work is therefore driven by an external scheduler
calling an authenticated endpoint:

```text
Supabase Cron (pg_cron + pg_net) -> POST /api/cron/sync
```

Every job is idempotent and guarded by a PostgreSQL transaction-scoped
advisory lock, so overlapping ticks cannot double-write. APScheduler or Celery
remain options if the deployment later moves to a host with a always-on worker.

## Deployment

**Amended.** The 2026/27 season is deployed on free tiers:

```text
Frontend: Vercel Hobby project, root apps/web
Backend:  Vercel Hobby project, root services/api (FastAPI as a Function)
Database: Supabase Free PostgreSQL, transaction pooler for the API and
          session pooler for migrations
Schedule: Supabase Cron
```

Docker is used for local development only. See
[`DEPLOYMENT.md`](DEPLOYMENT.md) for the full procedure, environment variables,
quotas and rollback steps.

---

# 19. Recommended Data Model

Core tables:

```text
seasons
competition_phases
gameweeks
managers
manager_external_profiles
divisions
division_memberships
manager_gameweek_scores
manager_gameweek_picks
manager_gameweek_players
manager_transfers
manager_chips
standing_snapshots
h2h_schedules
h2h_matches
h2h_standings
h2h_penalties
cup_competitions
cup_rounds
cup_matches
cup_tiebreak_results
violations
admin_decisions
awards
manager_highlights
sync_logs
system_settings
```

**Amended.** The implemented schema separates three layers instead of one, as
described in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): raw FPL evidence
(`raw_fpl_responses`), normalized source facts at their true grain
(`fpl_player_fixture_stats`, `manager_pick_snapshots`, `manager_pick_items`,
`manager_gameweek_history`), and VMF decisions (`violations`,
`admin_decisions`, ledgers). Penalties and Cup qualification are ledgers rather
than mutable totals, and a finalized result is an immutable revision rather
than a boolean flag on a mutable row.

## Suggested table responsibilities

### `seasons`

```text
id
name
fpl_season_code
start_gameweek
end_gameweek
status
```

### `competition_phases`

```text
id
season_id
name
phase_type
start_gameweek
end_gameweek
```

Examples:

```text
Classic Season 1
Classic Season 2
H2H Group Stage
H2H Play-offs
Cup Season 1
Cup Season 2
```

### `division_memberships`

```text
manager_id
division_id
competition_phase_id
start_gameweek
end_gameweek
promotion_source
relegation_source
```

### `manager_gameweek_scores`

```text
manager_id
gameweek_id
gross_points
transfer_cost
net_points
official_points
replacement_points
score_source
chip_used
captain_points
goals_counted
yellow_cards_counted
red_cards_counted
bench_points
is_totw
score_status
last_synced_at
```

### `manager_gameweek_players`

```text
manager_id
gameweek_id
player_id
squad_position
is_captain
is_vice_captain
original_multiplier
effective_multiplier
base_points
contribution_points
goals
yellow_cards
red_cards
fixture_status
counted_in_final_score
auto_subbed_in
auto_subbed_out
```

### `standing_snapshots`

```text
competition_phase_id
division_id
manager_id
gameweek_id
snapshot_time
rank
previous_rank
rank_change
points
```

### `h2h_matches`

```text
competition_phase_id
gameweek_id
home_manager_id
away_manager_id
home_score
away_score
winner_manager_id
status
walkover_reason
is_playoff
bracket_position
```

### `cup_matches`

```text
cup_competition_id
round_id
gameweek_id
manager_a_id
manager_b_id
manager_a_score
manager_b_score
winner_manager_id
tie_break_step_used
random_draw_result
status
```

### `violations`

```text
manager_id
gameweek_id
violation_type
detected_count
confirmed_count
status
admin_note
reviewed_by
reviewed_at
```

---

# 20. Recommended Internal API

## Managers

```text
GET    /api/managers
POST   /api/managers
GET    /api/managers/{manager_id}
PATCH  /api/managers/{manager_id}
POST   /api/managers/import
POST   /api/managers/{manager_id}/sync
```

## Classic

```text
GET /api/classic/standings
GET /api/classic/standings/live
GET /api/classic/highlights
POST /api/classic/promote-relegate
```

## H2H

```text
GET  /api/h2h/standings
GET  /api/h2h/fixtures
GET  /api/h2h/matches/{match_id}
POST /api/h2h/schedule/generate
POST /api/h2h/schedule/lock
POST /api/h2h/playoffs/generate
```

## Cup

```text
GET  /api/cups
GET  /api/cups/{cup_id}/bracket
GET  /api/cups/matches/{match_id}
POST /api/cups/{cup_id}/draw
POST /api/cups/matches/{match_id}/resolve
```

## Administration

```text
GET  /api/admin/violations
POST /api/admin/violations/{violation_id}/approve
POST /api/admin/violations/{violation_id}/reject
POST /api/admin/scores/override
POST /api/admin/gameweeks/{gw}/finalize
POST /api/admin/locked-team/replacement
```

---

# 21. Data Synchronization Strategy

## Before the season

```text
Import 40 managers
Validate all FPL Team IDs
Assign HIGH and LOW
Generate H2H schedule
Create Cup configuration
Lock competition configuration
```

## After each FPL deadline

For all 40 managers:

```text
Fetch squad picks
Fetch captain and vice-captain
Fetch active chip
Fetch transfers
Fetch transfer cost
Store immutable deadline snapshot
```

## During live fixtures

Recommended refresh:

```text
Every 60 seconds
```

Tasks:

```text
Fetch live player scores
Fetch fixture statuses
Recalculate manager live scores
Recalculate HIGH and LOW live rank
Recalculate H2H live results
Recalculate Cup live results
Update players remaining
Update provisional tie-break status
```

Do not repeatedly refetch all 40 squads if the deadline snapshot has not changed.

## After all fixtures end

```text
Mark scores provisional
Recalculate auto-subs when data is available
Recalculate effective captain
Recalculate goals and cards
Recalculate TotW
Recalculate all standings
```

## Finalization

```text
Administrator or automated rule marks Gameweek final
Freeze final H2H and Cup results
Save final standing snapshot
Apply confirmed penalties
Generate next-round Cup or play-off fixtures
```

---

# 22. Important Edge Cases

The system must handle:

```text
Double Gameweeks
Blank Gameweeks
Postponed fixtures
Multiple fixtures for one player
Captain does not play
Vice-captain does not play
Bench Boost
Triple Captain
Free Hit
Wildcard
Automatic substitutions
Formation constraints
Late point corrections
Provisional bonus changes
Negative player points
Manager transfer cost above 8
Manager removed mid-season
FPL team locked or deleted
Manager joins new league late
Tied TotW
Cup match tied at all automatic tie-break steps
Manual administrative override
```

---

# 23. Configuration Requirements

Competition rules must not be hard-coded where avoidable.

Create configurable settings for:

```text
number_of_managers
division_size
promotion_count
relegation_count
classic_season_1_start_gw
classic_season_1_end_gw
classic_season_2_start_gw
classic_season_2_end_gw
h2h_group_start_gw
h2h_group_end_gw
h2h_playoff_size
h2h_win_points
h2h_draw_points
h2h_loss_points
maximum_allowed_transfer_cost
h2h_violation_deduction
cup_round_gameweeks
locked_team_average_rounding
refresh_interval_seconds
```

Initial values:

```text
number_of_managers = 40
division_size = 20
promotion_count = 6
relegation_count = 6
classic_season_1 = GW1-GW19
classic_season_2 = GW20-GW38
h2h_group_stage = GW1-GW35
h2h_playoff_size = 8
h2h_win_points = 3
h2h_draw_points = 1
h2h_loss_points = 0
maximum_allowed_transfer_cost = 8
h2h_violation_deduction = 6
refresh_interval_seconds = 60
```

---

# 24. MVP Scope

The MVP should contain:

```text
1. Manager import and management
2. HIGH and LOW division assignment
3. FPL data synchronization
4. Live Gameweek scoring
5. Internal Classic live standings
6. Rank movement
7. H2H schedule and standings
8. Live H2H score
9. H2H matchup detail
10. Cup bracket and Cup scoring
11. Cup tie-break calculations
12. Transfer-hit violation detection
13. Admin review and manual override
14. Locked-team average replacement score
15. Basic highlights
```

Not required in MVP:

```text
Win probability
Push notifications
Public authentication
Payment management
Advanced historical analytics
Mobile application
Multi-community support
```

---

# 25. Suggested Development Phases

## Phase 1: Data Prototype

Use 4 test managers.

Deliverables:

```text
Fetch manager profile
Fetch Gameweek picks
Fetch chip
Fetch transfers
Fetch player points
Calculate gross and net GW score
Display a simple ranking
```

## Phase 2: Classic Engine

Deliverables:

```text
40-manager import
HIGH and LOW membership
Season 1 and Season 2 point ranges
Live standings
Rank snapshots
Promotion and relegation
```

## Phase 3: H2H Engine

Deliverables:

```text
Generate 35-round schedule
Calculate live and final match results
H2H standings
Top-8 play-off bracket
Walkover handling
```

## Phase 4: Cup Engine

Deliverables:

```text
Cup qualification
Preliminary round
Knockout bracket
Tie-break calculation
Admin random draw
```

## Phase 5: Matchup Comparison

Deliverables:

```text
Same players
Differentials
Captain differences
Players playing
Players remaining
Effective players remaining
Bench points
Tie-break status
```

## Phase 6: Administration and Edge Cases

Deliverables:

```text
Violation review
Late league join
Locked or deleted team
Manual score override
Gameweek finalization
Audit log
```

## Phase 7: UI Polish and Deployment

Deliverables:

```text
Responsive frontend
Public dashboard
Admin panel
Deployment
Logging
Backups
Monitoring
```

---

# 26. Acceptance Criteria

The MVP is accepted when:

1. Forty managers can be imported using FPL Team IDs.
2. Managers can be assigned to HIGH and LOW.
3. The system calculates GW net points correctly.
4. The system does not use global FPL overall rank.
5. Classic rank is calculated only within the current division.
6. Season 1 and Season 2 scores are separated correctly.
7. Promotion and relegation after GW19 work correctly.
8. H2H schedule contains 35 rounds and one match per manager per round.
9. H2H results use net GW points.
10. H2H standings award 3/1/0 points.
11. Top 8 managers enter the play-offs.
12. Cup brackets are generated using the correct qualification rules.
13. Cup ties are resolved in the correct rule order.
14. TotW uses the highest net score and includes chip effects.
15. Goals and cards are counted only from counted players.
16. Captain points use the effective multiplied contribution.
17. Excessive transfer hits are detected correctly.
18. Admin can approve an exception or confirm a violation.
19. Locked-team replacement scores use the remaining-manager average.
20. Average replacement scores use half-up rounding.
21. Live matchup pages show same players and differentials.
22. Captain multiplier differences are handled correctly.
23. Players remaining and effective players remaining are shown.
24. Scores can move from live to provisional to final.
25. Admin actions are logged.

---

# 27. Implementation Principles for AI Agents

When implementing this project:

- Do not assume external FPL endpoints are permanently stable.
- Put external API calls behind a service layer.
- Store raw external responses where useful for debugging.
- Cache shared player and fixture data.
- Store manager deadline picks as snapshots.
- Do not recalculate historical final results from changing live data without explicit migration logic.
- Separate official external data from VMF-specific derived data.
- Make penalties and overrides auditable.
- Keep all competition rules configurable.
- Use deterministic calculations wherever possible.
- Require admin confirmation for random draws and disciplinary exceptions.
- Write unit tests for every scoring and tie-break rule.
- Use standard half-up rounding for replacement scores.
- Do not use Python's default `round()` for VMF replacement-score rounding.
- Treat live scores as provisional until finalized.
- Never depend on FPL global overall rank.

---

# 28. Priority Unit Tests

At minimum, test:

```text
Normal captain
Triple Captain
Captain does not play
Vice-captain replacement
Bench Boost
Auto-sub
Transfer cost 8
Transfer cost 12
Transfer cost 20
Transfer cost 28
TotW single winner
TotW tied winners
Cup tie resolved by TotW
Cup tie resolved by captain
Cup tie resolved by goals
Cup tie resolved by cards
Cup tie resolved by Classic points
Locked-team average below .5
Locked-team average exactly .5
Locked-team average above .5
Same player same multiplier
Same player captain versus normal
Player in only one manager's squad
Blank Gameweek
Double Gameweek
Postponed fixture
H2H point deduction
Cup walkover
Manager joins Season 2 late
```

---

# 29. Final Project Summary

The VMF Fantasy League Management Tool is a custom competition layer built on top of FPL data.

FPL supplies:

```text
Managers
Squads
Players
Fixtures
Points
Transfers
Chips
```

The VMF system supplies:

```text
HIGH and LOW divisions
Two Classic seasons
Promotion and relegation
Internal live rankings
Custom 40-manager H2H
Top-8 H2H play-offs
Two Cup competitions
VMF tie-break rules
Violation detection
Administrative decisions
Manager highlights
Live matchup comparison
```

The central design principle is:

```text
Use FPL as the scoring data source.
Use the VMF application as the competition rule engine.
```
