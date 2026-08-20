# VMF Fantasy League 2026/27 - Rulebook

**Document code:** `VMF-RULES-2026-27`
**Version:** `1.0.0-draft`
**Scope:** Fantasy Premier League season 2026/27
**Status:** Normative source of competition rules for implementation and testing

## 1. Authority and how to read this document

This document consolidates:

- the VMF 2025/26 recruitment rules;
- the original project specification;
- the decisions the organisers confirmed for the 2026/27 season.

Where they conflict, the order of precedence is:

1. decisions confirmed by the organisers for 2026/27;
2. this document;
3. the VMF 2025/26 recruitment rules;
4. the project specification and default technical configuration.

Any rule change made after the season starts must create a new
`ruleset_version`, state when it takes effect, and be recorded in the audit log.
A ruleset version already used to settle a result is never edited retroactively.

Keywords:

- **must**, **must not**: mandatory;
- **may**: an operational choice for the organisers;
- **organiser/admin**: an account with VMF administrative rights;
- **manager**: a competitor;
- **GW**: an official FPL Gameweek.

## 2. Membership and registration data

- The league has 46 managers, identified externally by `fpl_entry_id`.
- Registered manager and team names must not change while the season runs.
- If the FPL team name changes, the system only raises a warning; it never
  overwrites the registered VMF team name.
- A manager belongs to exactly one division in any given Gameweek: `HIGH` or
  `LOW`.
- Phone numbers and Facebook links are private and visible to administrators
  only.
- There is no public registration in this version. Adding a manager, changing a
  status or removing a manager is an administrative action and must be audited.

Minimum business statuses:

```text
active
suspended
removed
locked
deleted
pending_review
```

## 3. Scoring definitions

### 3.1 Gameweek points

```text
official_gross_points = the Gameweek points published by FPL
transfer_cost         = the transfer penalty published by FPL
official_net_points   = official_gross_points - transfer_cost
```

`official_net_points` is the base score for Classic, H2H, Cup, TotW and every
tie-break, unless a specific clause defines a replacement score, invalidates
the score, or an administrator override applies.

The system must keep these separate:

- raw FPL data;
- results derived under VMF rules;
- penalties;
- replacements;
- administrator overrides.

Raw FPL data must never be edited to express a VMF decision.

### 3.2 Effective points

`effective_net_points` is the value the competition uses, after resolving the
valid source of the score:

1. an active administrator override;
2. a valid replacement average;
3. `official_net_points`.

H2H penalties, and the rule that a Gameweek contributes `0` to a Cup
qualification table, are separate ledgers. They never modify
`official_net_points` or Classic points.

### 3.3 Counted players

Counted players are:

- players in the final XI after automatic substitutions;
- bench players while Bench Boost is active;
- the captain, or the vice-captain if FPL transferred the armband.

Players that do not count:

- bench players when Bench Boost is not active;
- players substituted out automatically;
- players not in the manager's squad.

Every pick must distinguish at least:

```text
selected_in_squad
selected_in_starting_xi
counted_in_final_score
counted_due_to_bench_boost
auto_subbed_in
auto_subbed_out
original_multiplier
effective_multiplier
```

### 3.4 Captain

The captain points used in tie-breaks are the final contribution after the
multiplier:

```text
captain_contribution_points =
    effective_captain_base_points * effective_captain_multiplier
```

- A normal captain has multiplier `2`.
- Triple Captain has multiplier `3`.
- If the captain does not play and FPL passes the armband to the vice-captain,
  use the vice-captain's multiplied contribution.
- If neither captain nor vice-captain is effective, the captain contribution is
  `0`.

### 3.5 Goals and cards

- Only counted players contribute goals and cards.
- Goals and cards are real event counts; they are never multiplied by the
  captain multiplier.
- A goal by a bench player without Bench Boost contributes `0`.
- A goal by a bench player with Bench Boost contributes `1`.
- Each yellow or red card counts as one card:

```text
total_cards = yellow_cards + red_cards
```

If a player has several fixtures in a Double Gameweek, sum the events of every
fixture attached to that Gameweek.

## 4. Classic

### 4.1 Structure

The league is 46 managers, in two divisions of different sizes.

| Phase | Gameweeks | HIGH | LOW |
|---|---:|---:|---:|
| Classic Season 1 | GW1-GW19 | 20 | 26 |
| Classic Season 2 | GW20-GW38 | 20 | 26 |

Promotion and relegation move six managers in each direction, so both
divisions keep their size across the swap.

Season 2 points reset to `0` at GW20. Full-season points are still kept for
statistics.

After GW19:

- the bottom 6 of HIGH are relegated to LOW;
- the top 6 of LOW are promoted to HIGH;
- the new membership takes effect from GW20.

After GW38:

- the bottom 6 of HIGH are relegated for the next period;
- the top 6 of LOW are promoted;
- the bottom 6 of LOW must reapply if they wish to continue.

Membership must be stored per phase and Gameweek range. Updating a single
division column, which would rewrite history, is not allowed.

### 4.2 Ranking

- A Classic score is the sum of `effective_net_points` inside the relevant
  Season.
- A table compares only the managers in the same division for that phase.
- FPL overall rank is never used.
- Displayed tables use competition ranking, for example `1, 2, 2, 4`.

Managers level on Classic points are separated by the chain in section 7, which
is the same chain the Cup and the H2H table use.

## 5. TotW

TotW is the manager with the highest `effective_net_points` in a Gameweek among
all 46 eligible managers, across both divisions.

- Chips and transfer costs are already inside the score being compared.
- If several managers tie for the highest score, they all receive a TotW.
- Each tied manager's cumulative TotW count increases by `1`.
- A `replacement_average` score is not eligible for TotW.
- A manager on a replacement score is not eligible for that Gameweek's
  individual awards or highlights either.

Cumulative TotW at a cutoff counts only the TotW awards from the start of the
relevant phase up to that cutoff; future Gameweeks are never used.

## 6. Head to head

### 6.1 Group stage

- All 46 managers play one common H2H competition from GW1 to GW35.
- 46 is even, so every manager is paired in every round: 23 matches a
  Gameweek, 805 across the group stage.
- Every manager plays exactly one match per Gameweek.
- No manager faces themselves.
- The schedule is generated before the season. Administrators may edit it
  before it is locked; afterwards it is immutable except through an audited
  administrative decision.
- The match score is `effective_net_points`.

Table points:

```text
win  = 3
draw = 1
loss = 0
```

Metrics that must be kept:

```text
played
wins
draws
losses
points_for
points_against
point_difference
h2h_table_points_before_penalty
h2h_penalty_points
h2h_table_points
```

`h2h_table_points` may be negative.

### 6.2 Selecting the top 8

After GW35 is finalized, the eight highest-placed eligible managers enter the
play-offs. The boundary is decided with section 7 using:

```text
primary_points = h2h_table_points
period = GW1-GW35
```

Point difference, points for and number of wins are still displayed, but they
do not take precedence over the boundary chain fixed in section 7.

### 6.3 Play-offs

| GW | Round |
|---:|---|
| 36 | Quarter-finals |
| 37 | Semi-finals |
| 38 | Final |

Quarter-final seeding:

```text
1 vs 8
4 vs 5
2 vs 7
3 vs 6
```

The semi-final bracket is fixed by the quarter-final bracket.

**H2H has no third-place match.** The two losing semi-finalists share third
place. GW38 contains the final only.

A tied play-off match uses the Cup tie-break chain in section 8.4.

## 7. Tie-break chain

Every table in the competition sorts by its own primary measure first, then
hands whatever is still level to the one chain below. Keeping a single chain is
what stops Classic, H2H and the Cup from disagreeing about who finished ahead.

The primary measure is:

- Classic: Classic Season points;
- H2H: `h2h_table_points`, then point difference, points for and wins;
- Cup: the match score, or `cup_qualification_points` in a qualification table.

Then, in order:

1. **More cumulative TotW**, counted to the Gameweek being decided.
2. **Higher captain points.**
3. **More goals** by counted players.
4. **Fewer cards** by counted players.
5. **Higher Classic points** up to that Gameweek.
6. **An administrator draw** if still tied.

Steps 1-5 are automatic and every one of them records what it compared. Only
step 6 needs a person.

The highest single Gameweek score is still reported, and it decides a separate
special award, but it is no longer a tie-break step.

A draw must record the list of eligible managers, who performed it, when, by
what method, and the result. Silent randomness inside a background job is not
allowed.

This rule breaks a tie only to decide which side of a boundary a manager falls
on. Displayed tables may still show shared ranks when no qualifying decision is
required.

## 8. VMF Cup

### 8.1 Structure

Both Cups have the same structure. Classic places are read at the cutoff, the
bottom of each division drops out, and the remaining 40 managers enter the
bracket at one of three points.

| Rank | HIGH | LOW | Enters at |
|---|---|---|---|
| Top | 1-3 | 1 | Round of 16 |
| Middle | 4-10 | 2-6 | Qualifying Round 2 |
| Lower | 11-18 | 7-22 | Qualifying Round 1 |
| Out | 19-20 | 23-26 | Not in the Cup |

That is 24 managers in Qualifying Round 1 playing for 12 places, joined by 12
more in Qualifying Round 2 playing for 12 places, joined by the last 4 in a
round of 16.

| Round | Season 1 | Season 2 |
|---|---:|---:|
| Classic places read after | GW13 | GW32 |
| Qualifying Round 1 | GW14 | GW33 |
| Qualifying Round 2 | GW15 | GW34 |
| Round of 16 | GW16 | GW35 |
| Quarter-finals | GW17 | GW36 |
| Semi-finals | GW18 | GW37 |
| Final and third-place match | GW19 | GW38 |

Every round is a single head-to-head knockout tie.

### 8.2 Seeding

The two Cups are seeded differently: Season 1 gives HIGH the top places in the
qualifying draw, Season 2 gives them to LOW. Neither bracket is derived from
the other, and neither is generated at run time - both are transcribed from the
bracket sheet the organisers published, in `domain/cup_bracket.py`, and checked
against it by test.

A Cup is drawn once, after its cutoff Gameweek is finalized, and the whole
bracket is written at that moment. Later rounds carry their position - "winner
of Q1-7" - until the managers who fill them are known.

Two managers sharing a qualification rank stops the draw. The system does not
choose between them; that is the administrator draw in section 7.

### 8.3 Cup qualification table

Each Cup has an independent ledger:

```text
cup_qualification_points =
    sum(cup_qualification_contribution_by_gw)
```

where:

```text
confirmed excessive-transfer violation in that GW -> contribution = 0
not eligible because the Season 2 league was not joined -> contribution = 0
otherwise -> contribution = effective_net_points
```

The `0` rule affects the Cup qualification table only:

- it does not change Classic points;
- it does not change raw FPL data;
- it does not by itself change a played H2H group result.

**Every Gameweek carrying a violation** inside GW1-GW13 or GW20-GW32 is removed
from the Cup total, not only the Gameweek in which a Cup tie is played.

Qualification is computed separately inside HIGH and LOW according to the
membership of the relevant Season. Ties at a boundary use section 7.

### 8.4 Match score and tie-breaks

A Cup match score is `effective_net_points`, except for a walkover or a score
invalidated under section 9.

If both sides are level and both hold a genuine score or a valid override,
apply the chain in section 7. Every step must record its inputs, the comparison
result, and which step decided the winner.

Score-source precedence:

- if the scores are level and only one side is on a `replacement_average`, the
  side with a genuine score or valid override advances before the chain above
  runs;
- if both sides are on a `replacement_average`, the system decides nothing; the
  tie goes to an audited administrator decision.

The Cup does play a third-place match, in GW19 and GW38.

## 9. Violations

### 9.1 Excessive transfer cost

A manager may take a transfer cost of at most `8` in one Gameweek.

```text
transfer_cost <= 8:
    detected_count = 0

transfer_cost > 8:
    detected_count = ceil((transfer_cost - 8) / 8)
```

Reference examples:

| Transfer cost | Violations raised |
|---:|---:|
| 0, 4, 8 | 0 |
| 12, 16 | 1 |
| 20, 24 | 2 |
| 28 | 3 |

The counter accumulates across GW1-GW38 and does not reset at GW20. A single
Gameweek can cross several thresholds at once:

- a cost of `20` triggers thresholds 1 and 2;
- a cost of `28` triggers thresholds 1, 2 and 3.

### 9.2 Review workflow

Minimum statuses:

```text
detected
pending_review
approved_exception
confirmed
rejected
overridden
```

- Detection is automatic and idempotent.
- An irreversible penalty takes effect only from an administrator decision of
  `confirmed` or `overridden`.
- A claim of having forgotten to activate a chip moves the case to
  `pending_review`.
- If the administrator approves the exception, the confirmed count for that
  event is `0`.
- Even with an approved exception, the official FPL transfer cost remains
  inside `official_net_points`. Only a separate score override, with a reason
  and an audit entry, changes the effective score.
- If the administrator rejects the exception, the event is confirmed by the
  formula.

### 9.3 Consequences by cumulative threshold

A consequence applies when the total confirmed violations **first reach or
exceed** a threshold:

| Threshold | Consequence |
|---:|---|
| 1 | Conduct deposit forfeited; a single `-6` deduction from the H2H table; the Cup rule applies to the offending Gameweek |
| 2 | Entitled to at most 50% of any prize; removed from H2H and from the Cup |
| 3 | Removed from the competition |

The same threshold action is never applied twice. A cost of `20` in one
Gameweek raises two violation units but still creates only one `-6` ledger
entry when threshold 1 is crossed, while also applying threshold 2 immediately.

### 9.4 Effect on H2H

In the group stage, for a first violation:

1. the match is still won, drawn or lost on net points;
2. the `3/1/0` match points are recorded normally;
3. a separate `-6` penalty ledger entry is deducted from the H2H table.

The table total after the penalty may be negative.

When a manager reaches threshold 2:

- historical finalized H2H results are preserved;
- the manager's remaining matches are recorded as walkovers;
- the opponent receives `3` points;
- the technical score is stored as `0-0`;
- a technical walkover adds nothing to points for or points against and creates
  no artificial point difference.

If a manager violates during a play-off match, the opponent advances by
walkover. If both sides are simultaneously ineligible, the tie goes to
administrator review; the system never picks a winner at random.

### 9.5 Effect on the Cup

- Each confirmed excessive-transfer violation sets the contribution of **the
  offending Gameweek** in the Cup qualification table to `0`.
- If the violation falls in a knockout tie, the offending manager's match score
  is invalid and the opponent advances by walkover.
- On reaching threshold 2 the manager is removed from the Cup. Historical
  finalized results stand; remaining ties are walkovers.
- If the removal happens before the bracket is locked, the manager is not in
  the eligible list for seeding or the draw.
- If both sides are ineligible, the tie goes to administrator review.

### 9.6 Failing to join the new league

Not joining the new Season 2 FPL league in time counts as one violation unit in
the same GW1-GW38 counter.

- Classic and Cup contributions from GW20 until the Gameweek the manager joins
  are `0`.
- Classic and Cup scoring resumes from the joining Gameweek itself.
- H2H continues to be played and scored normally.
- The event must be reviewed by an administrator, who records
  `season_2_join_gameweek`.

A late-join violation does not turn the joining Gameweek into an
excessive-transfer violation; from that Gameweek the score counts normally
unless another violation exists.

## 10. Locked or deleted FPL teams

From `locked_from_gameweek` onward, the manager's score is replaced by the
average of the **division that manager belongs to in that Gameweek**.

Each Gameweek can therefore have two independent averages:

```text
HIGH replacement average
LOW replacement average
```

The sample contains managers who:

- belong to the same division in that Gameweek;
- are active;
- are not locked, deleted or removed;
- have an effective net score that is not itself a `replacement_average`.

Never take managers from the other division. Never place a replacement score in
the sample; several locked teams in one division must use the same original
sample, with no recursion.

```text
replacement_average_raw =
    sum(eligible_sample_net_points) / eligible_sample_count

replacement_average_rounded =
    ROUND_HALF_UP(replacement_average_raw)
```

Examples:

```text
67.42 -> 67
67.50 -> 68
67.81 -> 68
```

Do not use bankers' rounding. If the sample is empty, the system does not
borrow the other division's average; the score moves to `pending_review` for an
administrator.

A replacement score:

- is used for Classic, H2H and the Cup;
- is not eligible for TotW or any individual performance award or highlight;
- must store the raw average, the rounded value, the sample manager IDs and the
  snapshot revision used.

## 11. Score states and finalization

A Gameweek follows this state machine:

```text
upcoming -> live -> provisional -> final
```

- `upcoming`: no relevant fixture has started;
- `live`: a fixture has started and has not finished;
- `provisional`: fixtures have finished but FPL or the organisers may still
  adjust;
- `final`: the organisers or a finalization rule have locked a revision.

Rules:

- The interface must mark live and provisional clearly and never present them
  as a settled result.
- A final snapshot is immutable.
- Only an administrator may reopen a finalized Gameweek.
- A reopen requires a reason, an actor, a timestamp and an audit entry.
- Recalculation after a reopen creates a new revision linked by `supersedes`;
  it never overwrites or deletes the previous final revision.
- H2H results, Cup results, TotW, standings and next-round brackets must
  reference the exact final revision that produced them.
- A late correction from FPL never changes a finalized result on its own. It
  raises a difference alert for an administrator to decide whether to reopen.

An administrator override is also an append-only record:

```text
target
old_effective_value
new_effective_value
reason
actor
created_at
effective_from_revision
supersedes_override_id
```

## 12. Live matchup

An H2H or Cup matchup page must provide:

- the live or provisional score of both sides;
- shared players and differentials;
- captain differences;
- players finished, playing and yet to play;
- `players_remaining`;
- `effective_players_remaining`;
- bench points, chip and transfer cost;
- the current tie-break position and the state of the data.

For a single player:

```text
net_multiplier =
    effective_multiplier_manager_a
    - effective_multiplier_manager_b
```

- `0`: neutralized;
- positive: a differential for A;
- negative: a differential for B.

`players_remaining` counts distinct players with at least one unresolved
fixture. `effective_players_remaining` sums the effective multipliers of those
players. In a Double Gameweek the interface should also show the number of
remaining fixtures, so that one player with two matches is not mistaken for two
players.

## 13. Privacy, administrative rights and audit

### 13.1 Public data

The public may see:

- manager names and registered team names;
- the FPL Team ID, if the organisers choose to publish it;
- division and non-sensitive competition status;
- scores, standings, brackets, matchups and published disciplinary decisions.

The public must never receive:

- phone numbers;
- Facebook or other private contact URLs;
- administrator notes;
- authentication data;
- raw payloads containing data that does not need to be public.

### 13.2 Mandatory audit

At minimum, audit:

- manager, division and status changes;
- locking or unlocking an H2H schedule;
- a draw or a bracket change;
- violation reviews and threshold actions;
- replacement calculations and manual replacements;
- score and penalty overrides;
- finalize, reopen and re-finalize;
- random draws;
- administrator access to or export of personal data.

An audit record is append-only and must contain:

```text
actor
action
target_type
target_id
before
after
reason
timestamp
request_id
```

The organisers hold the final decision, but the system must never turn that
decision into an untraceable change.

## 14. Prize fund

The fund is 9,200,000₫. It is fixed before the season and never derived from
play, so it lives beside the interface copy rather than in the database.

| Competition | Total |
|---|---:|
| Classic | 5,600,000₫ |
| Head to head | 1,200,000₫ |
| VMF Cup | 1,700,000₫ |
| Special awards | 700,000₫ |

**Classic**, 2,800,000₫ per Season:

| Place | HIGH | LOW |
|---|---:|---:|
| Champion | 600,000₫ | 550,000₫ |
| Runner-up | 400,000₫ | 350,000₫ |
| Third | 250,000₫ | 200,000₫ |
| Fourth | 200,000₫ | 150,000₫ |
| Fifth and sixth | - | 50,000₫ each |

**Head to head**: champion 500,000₫, runner-up 300,000₫, 150,000₫ to each
losing semi-finalist, 100,000₫ to the group-stage winner.

**VMF Cup**, 850,000₫ per Season: champion 400,000₫, runner-up 200,000₫, third
150,000₫, fourth 100,000₫.

**Special awards**: 50,000₫ for each of ten monthly Classic winners, 100,000₫
for the Classic number one across the full season, and 100,000₫ for the
highest score in a single Gameweek.

A manager past the second violation threshold receives 50% of anything they
would otherwise be paid, per section 9.3.

The **minigame fund** sits outside these figures. Each minigame pays
50,000-100,000₫, and every forfeited entry fee is added to it.

## 15. Invariants that must hold

1. FPL overall rank is never used to rank VMF.
2. A manager has exactly one effective division membership per Gameweek.
3. Raw FPL data is never overwritten by a penalty or an override.
4. The violation counter does not reset between the two Seasons.
5. A threshold action is applied at most once.
6. A Gameweek zeroed for the Cup contributes `0` there and leaves Classic
   unchanged.
7. A replacement average uses only same-division samples and contains no
   replacement score.
8. H2H has no third-place match; the Cup does.
9. A final revision is never edited in place.
10. Personal data never appears in a public API, public cache, log or export.
