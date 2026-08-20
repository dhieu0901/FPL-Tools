# VMF Fantasy League 2026/27 - Test Matrix

**Document code:** `VMF-TEST-2026-27`
**Rule source:** [`RULEBOOK.md`](./RULEBOOK.md)
**Architecture:** [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## 1. Testing strategy

Levels:

- **U - Unit:** pure rule functions, deterministic, no real network or database.
- **I - Integration:** PostgreSQL, parsers, transactions, ledgers and the API.
- **E - End-to-end:** frontend, API and worker against replayed data.
- **S - Security/operational:** permissions, load, backups, failure modes.

Every finalized scenario must assert both the value and its provenance:

```text
snapshot_id
revision
ruleset_version
input_hash
score_source
```

Never build an expected result by calling the production rule function itself.
Expected fixtures are declared independently.

## 2. Standard fixtures

Build these reusable datasets:

| Fixture | Content |
|---|---|
| `GW_NORMAL` | A full Gameweek of 10 fixtures, ordinary captain and vice |
| `GW_AUTOSUB` | A starter does not play; a bench player replaces them legally |
| `GW_CHIPS` | Bench Boost, Triple Captain, Wildcard, Free Hit |
| `GW_DGW` | A player with two fixtures, one updated first |
| `GW_BGW` | A player or team without a fixture |
| `GW_POSTPONED` | A fixture postponed and later moved to another event |
| `GW_NEGATIVE` | A counted player and a captain on negative points |
| `LEAGUE_40` | 20 HIGH and 20 LOW with scores that tie on a boundary |
| `LOCKED_BOTH_DIVS` | Several locked teams in both HIGH and LOW |
| `VIOLATION_SEASON` | Costs of 8/12/20/28, an exception and a late join |
| `LATE_CORRECTION` | An FPL payload that changes after provisional or final |

## 3. Synchronization and provenance

| ID | Level | Scenario | Expected |
|---|---|---|---|
| SYNC-001 | I | The same request key and payload hash arrive again | No new logical source revision; the job succeeds idempotently |
| SYNC-002 | I | Same request key, different payload hash | A new raw revision is created and the old one kept |
| SYNC-003 | I | A payload that breaks the schema | The raw payload is still stored; the parser reports drift; no wrong score is published |
| SYNC-004 | I | FPL times out and then recovers | Retries with backoff; no duplicate snapshot or violation |
| SYNC-005 | E | The live endpoint fails for three ticks | The last snapshot is kept, staleness and last update are shown, no score becomes `0` |
| SYNC-006 | I | Two workers run the same Gameweek | The advisory lock or CAS publishes only one valid revision |
| SYNC-007 | I | Fetch live shared data for 46 managers | Each shared player/fixture endpoint is called once per tick |
| SYNC-008 | I | Deadline picks already captured, next live tick | The 40 picks are not refetched while the source is unchanged |
| SYNC-009 | I | A new parser version reruns old raw data | Derived rows carry the new parser and algorithm version; raw is unchanged |
| SYNC-010 | S | A failed request log contains a contact payload | Phone, Facebook URL, auth header and cookie are redacted |

## 4. Points, picks, captain and chips

| ID | Level | Scenario | Expected |
|---|---|---|---|
| SCORE-001 | U | Gross 72, transfer cost 4 | Official net = 68 |
| SCORE-002 | U | A counted player on negative points | The negative value is added, never clamped to 0 |
| SCORE-003 | U | Captain base 8 | Contribution = 16 |
| SCORE-004 | U | Triple Captain base 8 | Contribution = 24 |
| SCORE-005 | U | Captain plays 0 minutes, vice base 7 | The vice is the effective captain; contribution = 14 |
| SCORE-006 | U | Neither captain nor vice is effective | Captain contribution = 0 |
| SCORE-007 | U | A starter does not play, a legal bench replacement exists | Auto-sub in/out and the effective multiplier are correct |
| SCORE-008 | U | Bench players score without Bench Boost | Not added to gross; counted as wasted bench points |
| SCORE-009 | U | Bench Boost active | Bench multiplier = 1; points enter gross; no wasted bench |
| SCORE-010 | U | Wildcard or Free Hit active and FPL cost = 0 | Use the FPL cost of 0; never infer a cost |
| SCORE-011 | U | A chip is claimed but FPL cost is still 12 | Net still subtracts 12 unless a separate score override exists |
| SCORE-012 | U | The captain scores 2 goals | Goals tie-break = 2, not multiplied to 4 |
| SCORE-013 | U | An uncounted bench player scores a goal or card | Goals and cards contribute 0 |
| SCORE-014 | U | A Bench Boost player scores 1 goal and 1 yellow | Goals = 1, cards = 1 |
| SCORE-015 | U | A player receives 1 yellow and 1 red | Total cards = 2 |
| SCORE-016 | I | A score override is active | Raw, official and derived bases are unchanged; the effective score uses the override and records provenance |

## 5. Double Gameweeks, Blank Gameweeks and fixtures

| ID | Level | Scenario | Expected |
|---|---|---|---|
| FIX-001 | U | A Double Gameweek player scores 5 and 8 | Player-Gameweek base = 13 |
| FIX-002 | U | That player is the captain, multiplier 2 | Contribution = 26, with no lost or double-counted fixture |
| FIX-003 | U | The player scores 1 and 2 goals | Goals tie-break = 3 |
| FIX-004 | U | The first match is over, the second has not started | The player still counts as remaining; fixtures remaining = 1 |
| FIX-005 | U | A captain still has a second fixture | Players remaining +1, effective remaining +2, never +4 |
| FIX-006 | U | A Blank Gameweek player | Fixture status blank; contribution 0 unless replaced by an auto-sub |
| FIX-007 | I | A postponed fixture is not rescheduled | Not marked finished or final because of missing data; status postponed |
| FIX-008 | I | A fixture moves from GW25 to GW26 | A new revision removes the stats from the GW25 aggregate and adds them to GW26 |
| FIX-009 | I | A live fixture revision changes bonus points | The new snapshot reflects the difference without duplicating a stats row |
| FIX-010 | E | A Double Gameweek updates fixture by fixture over several ticks | The live score grows correctly per revision and the final aggregate is right |

## 6. Classic, membership and boundaries

| ID | Level | Scenario | Expected |
|---|---|---|---|
| CLA-001 | U | 20 HIGH and 20 LOW | Ranking partitions by division only |
| CLA-002 | U | Two managers on equal points | Displayed as `1,2,2,4` |
| CLA-003 | U | FPL overall rank disagrees with the VMF score | Overall rank does not affect the VMF rank |
| CLA-004 | I | GW19 is finalized | The bottom 6 of HIGH and top 6 of LOW are identified; the new membership starts at GW20 |
| CLA-005 | I | Query GW19 again after promotion | The old membership is still visible; history is unchanged |
| CLA-006 | U | GW20 begins | Season 2 points = 0; full-season points unchanged |
| CLA-007 | U | A tie at the top 6 boundary with different cumulative TotW | The manager with more TotW takes the place |
| CLA-008 | U | Points and TotW tie, highest Gameweek differs | The higher eligible single-Gameweek score wins |
| CLA-009 | I | Every step ties | No silent randomness; a pending administrator draw is created |
| CLA-010 | I | Two overlapping memberships for one manager and Gameweek | The database rejects it |
| CLA-011 | U | No tie at the boundary | No draw runs, even if positions outside the boundary are level |

## 7. TotW and highlights

| ID | Level | Scenario | Expected |
|---|---|---|---|
| TOTW-001 | U | One highest score | One winner, cumulative +1 |
| TOTW-002 | U | Three equal highest scores | All three receive TotW and each gains +1 |
| TOTW-003 | U | Bench Boost gross 96 cost 4 against a net of 90 | Net 92 wins TotW |
| TOTW-004 | U | A replacement score is the highest | The manager on a replacement does not receive TotW |
| TOTW-005 | U | A manager with a transfer violation has the highest net | TotW still follows net points; Cup qualification is a separate ledger |
| TOTW-006 | I | Rerun the same snapshot | Cumulative TotW is not incremented twice |
| TOTW-007 | U | Bench Boost active | Counted bench points are not recorded as wasted bench |
| TOTW-008 | U | A replacement score | No individual Gameweek highlight or award |

## 8. H2H group stage and play-offs

| ID | Level | Scenario | Expected |
|---|---|---|---|
| H2H-001 | I | Generate 35 rounds for 46 managers | 23 matches per Gameweek, one per manager, no self-match |
| H2H-002 | I | Edit a locked schedule directly | Rejected; only a new version or an administrative action is allowed |
| H2H-003 | U | Net 68 against 67 | 68 receives 3 points, 67 receives 0 |
| H2H-004 | U | Net 68 against 68 | Each receives 1 |
| H2H-005 | U | A series of results | Played/W/D/L/PF/PA/PD and table points are correct |
| H2H-006 | U | A penalty pushes table points below zero | The negative value is preserved |
| H2H-007 | U | A top-8 tie on table points with different TotW | TotW decides the boundary; point difference does not override the fixed rule |
| H2H-008 | U | Table points and TotW tie, highest GW1-35 differs | The highest Gameweek decides |
| H2H-009 | I | Everything ties at the top-8 boundary | A pending, audited administrator draw; no background randomness |
| H2H-010 | I | Seed the top 8 | Pairs 1-8, 4-5, 2-7, 3-6 |
| H2H-011 | E | GW36-38 | Quarter-finals, semi-finals and final; no third-place match is created |
| H2H-012 | I | Two losing semi-finalists | Both hold shared third place |
| H2H-013 | U | A play-off draw on points | The Cup tie-break chain runs |
| H2H-014 | I | A manager is removed before the cutoff | Not in the eligible top 8; the place passes to the next manager by the boundary rule |

## 9. Cup qualification and brackets

| ID | Level | Scenario | Expected |
|---|---|---|---|
| CUPQ-001 | U | Cup 1 without violations | Qualification total = sum of GW1-14 effective net |
| CUPQ-002 | U | Cup 2 without violations | Qualification total = sum of GW20-33 effective net |
| CUPQ-003 | U | A confirmed violation in GW5 | GW5 contributes 0; other Gameweeks unchanged |
| CUPQ-004 | U | A confirmed violation in GW25 | Cup 2 GW25 contributes 0 |
| CUPQ-005 | U | The violating Gameweek has a negative net | The contribution is still 0, not the negative value |
| CUPQ-006 | U | An approved forgotten-chip exception | The Gameweek is not zeroed for a violation; official net still carries the transfer cost |
| CUPQ-007 | U | A Cup qualification violation | Classic points and H2H match scores do not change |
| CUPQ-008 | U | The Season 2 league is joined at GW23 | GW20-22 contribute 0; GW23 starts counting |
| CUPQ-009 | I | Ranks 1-2 in each division | Four direct qualifiers |
| CUPQ-010 | I | Ranks 3-14 in each division | Twenty-four preliminary participants |
| CUPQ-011 | I | Twelve preliminary winners | Sixteen teams in the round of 16 |
| CUPQ-012 | U | A tie on the rank 2/3 boundary | Points → TotW → highest eligible Gameweek → administrator draw |
| CUPQ-013 | U | A tie on the rank 14/15 boundary | The same chain selects who plays the preliminary round |
| CUPQ-014 | I | The Cup 1 schedule | GW15 preliminary, 16 R16, 17 QF, 18 SF, 19 final plus third place |
| CUPQ-015 | I | The Cup 2 schedule | GW34 preliminary, 35 R16, 36 QF, 37 SF, 38 final plus third place |
| CUPQ-016 | U | A manager is HIGH in Season 1 and LOW in Season 2 | Qualification partitions by the membership of the relevant Season |
| CUPQ-017 | I | A manager reaches threshold 2 before the bracket is locked | Not in the eligible draw |

## 10. Cup and H2H knockout tie-breaks

| ID | Level | Scenario | Expected |
|---|---|---|---|
| TB-001 | U | Scores level, TotW differs | More TotW wins; stops at step 1 |
| TB-002 | U | TotW level, captain contribution differs | The higher contribution wins; step 2 |
| TB-003 | U | Normal captain against Triple Captain on the same base | Compare the contribution after the multiplier |
| TB-004 | U | The captain does not play and the vice takes over | Use the effective vice contribution |
| TB-005 | U | TotW and captain level, goals differ | More counted goals wins; step 3 |
| TB-006 | U | The captain scores | The goal is not multiplied |
| TB-007 | U | Goals level, cards differ | Fewer `yellow + red` wins; step 4 |
| TB-008 | U | Steps 1-4 level, Classic points differ | Classic Season points up to that Gameweek decide; step 5 |
| TB-009 | I | Every automatic step ties | A pending administrator draw storing every compared input |
| TB-010 | I | An administrator draw | Store the eligible list, actor, time, method and result |
| TB-011 | U | Level scores where one side is on a replacement | The side with a genuine score or valid override advances before the chain |
| TB-012 | I | Both sides on a replacement and level | A pending administrator decision; no randomness |
| TB-013 | I | Rerun the tie-break | The result and `step_used` are deterministic; no new draw is created |

## 11. Violations and discipline

| ID | Level | Scenario | Expected |
|---|---|---|---|
| VIO-001 | U | Cost 0/4/8 | Detected count = 0 |
| VIO-002 | U | Cost 12/16 | Detected count = 1 |
| VIO-003 | U | Cost 20/24 | Detected count = 2 |
| VIO-004 | U | Cost 28 | Detected count = 3 |
| VIO-005 | I | Cost 20 confirmed while the counter is 0 | Thresholds 1 and 2 fire immediately; only one `-6` H2H ledger entry |
| VIO-006 | I | Cost 28 confirmed while the counter is 0 | Thresholds 1, 2 and 3 fire immediately |
| VIO-007 | I | A violation in GW10 and another in GW22 | The counter accumulates and does not reset at GW20 |
| VIO-008 | I | Retry detection or the decision for the same event | No duplicate violation unit, threshold action or penalty |
| VIO-009 | I | A forgotten-chip claim | Status pending_review; no irreversible penalty yet |
| VIO-010 | I | An administrator approves the exception | Confirmed count = 0; actor and reason stored; official net keeps the transfer cost |
| VIO-011 | I | An administrator rejects the exception | Confirmed by the formula and the threshold applies idempotently |
| VIO-012 | U | A first violation during the H2H group stage | The result still awards 3/1/0, then a separate `-6` ledger entry |
| VIO-013 | I | Threshold 2 after matches were finalized | Historical results are unchanged |
| VIO-014 | U | A future H2H match after removal | Opponent +3; technical 0-0; PF/PA/PD unchanged |
| VIO-015 | U | A violation during an H2H play-off | The opponent advances by walkover |
| VIO-016 | U | A violation during a Cup knockout tie | The score is invalid; the opponent advances by walkover |
| VIO-017 | I | Threshold 2 | Removed from H2H and the Cup; prize eligibility 50% |
| VIO-018 | I | Threshold 3 | Removed from the whole competition |
| VIO-019 | I | Both knockout sides ineligible | Pending administrator review; no automatic winner |
| VIO-020 | I | The Season 2 league is joined late | One violation unit added; Classic and Cup zeroed before the join; H2H normal |
| VIO-021 | U | The joining Gameweek has a valid score | Classic and Cup count from that Gameweek; the join violation does not zero it |
| VIO-022 | I | A threshold action reruns after a re-finalization | The unique threshold key prevents reapplication |

## 12. Locked and deleted replacements

| ID | Level | Scenario | Expected |
|---|---|---|---|
| AVG-001 | U | HIGH average 67.42 | Rounded = 67 |
| AVG-002 | U | HIGH average 67.50 | Rounded = 68 |
| AVG-003 | U | HIGH average 67.81 | Rounded = 68 |
| AVG-004 | U | Average 68.5 | Half-up = 69, not bankers' rounding |
| AVG-005 | U | HIGH average 60, LOW average 80 | A locked HIGH manager receives 60; a locked LOW manager receives 80 |
| AVG-006 | U | Two locked HIGH managers | Both are excluded from the sample and receive the same average from the active non-replacement sample |
| AVG-007 | U | The sample contains an earlier replacement row | That row is excluded |
| AVG-008 | U | A removed, deleted or locked manager | Not in the sample |
| AVG-009 | U | An active manager with a valid override | Use the effective non-replacement value and record provenance |
| AVG-010 | I | An empty sample | The score becomes pending_review; no other division and no division by zero |
| AVG-011 | I | A manager moves HIGH→LOW at GW20 and is locked at GW20 | The LOW membership applies at GW20 |
| AVG-012 | U | A replacement score | Used for Classic, H2H and the Cup |
| AVG-013 | U | The highest score of the Gameweek is a replacement | No TotW and no individual highlight |
| AVG-014 | I | The calculation record | Stores the raw average, the rounded value, the sample IDs, the division and the snapshot revision |

## 13. Matchup comparison

| ID | Level | Scenario | Expected |
|---|---|---|---|
| MAT-001 | U | The same player at multiplier 1 against 1 | Net multiplier 0, neutralized |
| MAT-002 | U | Captain 2 against normal 1 | Differential +1 for the captaining side |
| MAT-003 | U | A player only in A's squad | A differential for A at the matching multiplier |
| MAT-004 | U | A player has finished | Listed as finished, not remaining |
| MAT-005 | U | A player is playing | Listed as playing |
| MAT-006 | U | Two players yet to play, one captained | Players remaining = 2; effective remaining = 3 |
| MAT-007 | U | A Double Gameweek player with one fixture left | Counted as one player remaining, showing one fixture remaining |
| MAT-008 | E | A live match | Shows the score state, chip, transfer cost, bench and tie-break inputs from one snapshot revision |
| MAT-009 | I | Two API components fetch during a publish | The response still uses one snapshot set, with no mixed revisions |

## 14. Snapshots, finalization and audit

| ID | Level | Scenario | Expected |
|---|---|---|---|
| FIN-001 | I | Fixtures start and end | The state moves upcoming → live → provisional |
| FIN-002 | I | An FPL outage while provisional | No automatic finalization |
| FIN-003 | I | An administrator finalizes | The snapshot, scores, matches and standings lock atomically with an audit entry |
| FIN-004 | I | An attempt to update a finalized row | The database or the service refuses |
| FIN-005 | I | A late FPL correction after finalization | The final result is unchanged; a source difference alert is raised |
| FIN-006 | I | A non-administrator attempts a reopen | 403 with no mutation |
| FIN-007 | I | An administrator reopens without a reason | Validation fails |
| FIN-008 | E | Reopen, recalculate and re-finalize | A new revision supersedes the old one, which stays traceable |
| FIN-009 | I | A reopen changes a Cup winner that already produced a next round | An impact warning; the bracket is not silently rewritten |
| FIN-010 | U | The same inputs, rules and overrides | The output hash matches |
| FIN-011 | I | The audit insert fails inside an administrative command | The whole transaction rolls back |
| FIN-012 | I | A random draw, override or status change | The audit holds actor, action, before, after, reason, time and request ID |
| FIN-013 | I | A finalized response | Contains the snapshot ID, revision, ruleset, calculation and finalization times |

## 15. Authentication, authorization and personal data

| ID | Level | Scenario | Expected |
|---|---|---|---|
| SEC-001 | S | An anonymous call to public standings | 200 with no phone, Facebook URL or admin note |
| SEC-002 | S | An anonymous call to an admin API | 401 |
| SEC-003 | S | An admin viewer attempts a mutation | 403 |
| SEC-004 | S | A competition admin finalizes | Allowed, fully audited |
| SEC-005 | S | A role without personal-data rights calls contact or export | 403 |
| SEC-006 | S | A public serializer receives an ORM manager with a private relation | The DTO still omits private fields |
| SEC-007 | S | Public cache and CDN | No cache entry contains an admin or personal-data response |
| SEC-008 | S | A cookie mutation with a missing or wrong CSRF token | 403 |
| SEC-009 | S | A request from an origin outside the allowlist | Blocked |
| SEC-010 | S | Login brute force | Rate limiting and lockout work |
| SEC-011 | S | Session cookies | Carry HttpOnly, Secure and SameSite |
| SEC-012 | S | Viewing or exporting personal data | Records actor, scope and time; logs still redact the values |
| SEC-013 | S | Backup and staging refresh | Backups encrypted; staging holds no real production contacts |
| SEC-014 | S | An IDOR attempt against another admin target | Authorization is enforced per resource and action, not by hiding the UI |

## 16. Pre-production acceptance

| ID | Scenario | Pass condition |
|---|---|---|
| ACC-001 | Import 46 managers by FPL entry ID | Uniqueness validated, 20 HIGH and 26 LOW, private contacts not public |
| ACC-002 | Replay an ordinary Gameweek | Gross, net, captain, auto-subs and standings match the expected fixture |
| ACC-003 | Replay a live Double Gameweek | Scores and remaining counts update correctly per fixture |
| ACC-004 | Simulate all of Classic Season 1 | Division ranks, boundary ties, top and bottom 6 and the GW20 membership are correct |
| ACC-005 | Run H2H GW1-35 | A valid schedule, 3/1/0 scoring, penalties and the correct top 8 |
| ACC-006 | Run H2H GW36-38 | The bracket is correct, GW38 holds only the final, and both losing semi-finalists share third |
| ACC-007 | Run Cup 1 | Qualification over GW1-14, violations zeroed, GW15-19 bracket and tie-breaks correct |
| ACC-008 | Run Cup 2 | The same structure as Cup 1 over GW20-38 |
| ACC-009 | Violations at cost 20 and 28 | Multi-threshold behaviour is deterministic with no duplicates on retry |
| ACC-010 | Locked teams in both divisions | Two independent averages, half-up rounding, no recursion |
| ACC-011 | Finalize then apply a late correction | The final result is immutable; a reopen creates a new revision and audit entry |
| ACC-012 | Public and admin security pass | Personal-data isolation, RBAC, CSRF and log redaction all hold |
| ACC-013 | FPL API outage drill | The interface keeps the last snapshot with a stale banner; nothing is zeroed or wrongly finalized |
| ACC-014 | Backup restore drill | Final snapshots, raw provenance, overrides and audit entries are recoverable |

## 17. Release blockers

Do not release to production while any of these is true:

- a score, violation, Cup or H2H winner, or boundary decision is wrong;
- a replacement average mixes divisions or uses a replacement in its sample;
- a final snapshot can be edited or deleted in place;
- a retry creates a duplicate penalty or threshold action;
- a Double Gameweek double-counts or loses points;
- a public API, log or cache exposes a phone number or Facebook URL;
- an administrative mutation lacks an audit entry, or does not roll back when
  the audit write fails;
- the database cannot be restored from the most recent backup.
