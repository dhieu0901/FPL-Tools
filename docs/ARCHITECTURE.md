# VMF Fantasy League 2026/27 — Architecture

**Mã tài liệu:** `VMF-ARCH-2026-27`
**Trạng thái:** Kiến trúc triển khai production
**Nguồn luật:** [`RULEBOOK.md`](./RULEBOOK.md)

## 1. Mục tiêu kiến trúc

Hệ thống là một competition engine đặt trên dữ liệu FPL. Thiết kế phải:

- đồng bộ dữ liệu FPL có thể thay đổi mà không làm mất dấu dữ liệu nguồn;
- tính live đủ nhanh cho 40 manager;
- tái hiện chính xác một kết quả cũ;
- giữ penalty, replacement và override tách khỏi điểm chính thức;
- hỗ trợ DGW, BGW, trận hoãn, auto-sub và sửa điểm muộn;
- khóa được kết quả nhưng vẫn cho admin reopen có audit;
- không làm lộ phone/Facebook qua public API hoặc log;
- tiếp tục hiển thị snapshot gần nhất khi FPL API tạm lỗi.

## 2. Kiểu triển khai

Khuyến nghị dùng **modular monolith** cho mùa đầu:

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
        +-- object storage hoặc PostgreSQL JSONB cho raw payload
```

Stack:

```text
Frontend: Next.js + TypeScript + Tailwind + TanStack Query
Backend:  Python + FastAPI + Pydantic + SQLAlchemy + Alembic
Database: PostgreSQL
Jobs:     APScheduler trong process worker riêng ở quy mô ban đầu
Cache:    PostgreSQL/shared HTTP cache; Redis chỉ thêm khi có nhu cầu
```

Không chạy scheduler trong từng web replica. Chỉ một worker giữ distributed lock; mọi job vẫn phải idempotent.

Các module nghiệp vụ:

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

Module không gọi chéo table tùy tiện. Mỗi calculation chạy qua service/application command có input revision và ruleset rõ ràng.

## 3. Ba lớp dữ liệu bắt buộc

### 3.1 Raw/source layer

Raw layer là bằng chứng dữ liệu đã nhận từ FPL, append-only.

`raw_fpl_responses`:

```text
id
endpoint_name
request_key
season_code
gameweek
fpl_entry_id nullable
fixture_id nullable
fetched_at
http_status
etag nullable
payload_hash
payload_json
schema_version
parser_version
correlation_id
```

Quy tắc:

- cùng `request_key + payload_hash` không tạo nhiều bản payload logic;
- payload mới khác hash tạo revision mới;
- lỗi parse không xóa payload; lưu lỗi và cảnh báo schema drift;
- raw payload không chứa VMF penalty/override;
- secret, cookie hoặc authorization header không được lưu.

### 3.2 Normalized và derived layer

Normalized source facts là dữ liệu FPL đã parse nhưng chưa áp luật VMF:

```text
fpl_players
fpl_fixtures
fpl_player_fixture_stats
manager_deadline_pick_snapshots
manager_pick_items
manager_gameweek_history
manager_transfers
manager_chip_events
```

Derived layer được tạo bởi calculation run:

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

Mỗi derived row phải truy được:

```text
calculation_run_id
ruleset_version
algorithm_version
input_revision_set/hash
calculated_at
```

Không cập nhật derived final row tại chỗ. Live materialization có thể được upsert để phục vụ UI, nhưng snapshot/revision nguồn phải giữ lại để debug.

### 3.3 Decision/override layer

Quyết định VMF nằm riêng:

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

Override là overlay, không sửa raw hoặc derived base:

```text
effective_value =
    active_override
    ?? replacement_value
    ?? calculated_official_value
```

Mỗi override có `reason`, `actor`, `created_at`, `supersedes_id`, phạm vi và revision bắt đầu có hiệu lực. Hủy override bằng một event mới; không xóa record cũ.

## 4. Mô hình dữ liệu cốt lõi

### 4.1 Cấu hình và membership

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

`division_memberships` dùng khoảng GW:

```text
manager_id
division_id
phase_id
start_gameweek
end_gameweek
source_decision_id
```

Database constraint phải ngăn hai membership chồng lấn của cùng manager trong cùng competition scope.

PII nên tách khỏi row public:

```text
managers                  # tên đăng ký, team, trạng thái public-safe
manager_private_contacts  # phone, Facebook URL, encrypted at rest
```

### 4.2 Schedule và bracket

```text
h2h_schedule_versions
h2h_matches
cup_competitions
cup_qualification_snapshots
cup_rounds
cup_bracket_versions
cup_matches
```

Schedule/bracket có trạng thái:

```text
draft -> locked -> superseded
```

Chỉnh schedule đã locked phải tạo version mới và admin decision, không update im lặng.

### 4.3 Ledger thay vì sửa tổng

Các tổng quan trọng phải dựng từ ledger:

```text
h2h_table_points =
    sum(h2h_result_ledger.points)
    + sum(h2h_penalty_ledger.points_delta)

cup_qualification_points =
    sum(cup_qualification_ledger.contribution)
```

Threshold action có unique key:

```text
(manager_id, season_id, threshold_number)
```

Nhờ đó retry job không trừ H2H `-6` hai lần hoặc áp lại removal.

## 5. Mô hình player–fixture cho DGW

Không lưu một điểm player duy nhất rồi ghi đè theo fixture. Grain nguồn phải là:

```text
(season_id, gameweek_id, player_id, fixture_id)
```

`fpl_player_fixture_stats`:

```text
player_id
fixture_id
gameweek_id
fixture_revision
minutes
total_points
goals_scored
yellow_cards
red_cards
bonus
fixture_status
source_raw_id
```

Aggregate player-GW:

```text
player_gw_base_points =
    sum(total_points của mọi fixture gắn với GW)

player_gw_goals =
    sum(goals_scored của mọi fixture gắn với GW)

player_gw_cards =
    sum(yellow_cards + red_cards của mọi fixture gắn với GW)
```

Multiplier thuộc pick của manager, không thuộc fixture:

```text
manager_player_contribution =
    player_gw_base_points * effective_multiplier
```

Điều này tránh nhân captain riêng từng row rồi cộng sai khi dữ liệu fixture được cập nhật từng phần.

Trạng thái một player trong matchup:

- `yet_to_play`: còn fixture chưa bắt đầu;
- `playing`: ít nhất một fixture đang đá;
- `finished`: toàn bộ fixture trong GW đã kết thúc;
- `postponed`: fixture chưa được gán lại/được FPL đánh dấu hoãn;
- `blank`: không có fixture trong GW;
- `unknown`: dữ liệu không đủ.

Trong DGW, player có thể đã xong trận một nhưng vẫn `remaining` vì còn trận hai. Lưu thêm:

```text
fixtures_total
fixtures_finished
fixtures_remaining
```

`players_remaining` đếm player duy nhất còn fixture unresolved; `effective_players_remaining` cộng multiplier một lần cho mỗi player đó. UI hiển thị fixture count riêng.

Không tự coi trận hoãn là đã kết thúc GW. Mapping fixture sang event/GW phải lấy từ revision FPL; nếu fixture chuyển GW, calculation run mới phải gỡ nó khỏi aggregate GW cũ.

## 6. Deadline picks, auto-sub và chip

Sau deadline, lấy picks cho từng manager và tạo snapshot bất biến:

```text
manager_id
gameweek_id
snapshot_revision
deadline_time
raw_response_id
active_chip
entry_history_transfer_cost
pick_items
```

Giữ cả:

```text
original_captain_player_id
original_vice_captain_player_id
original_multiplier
effective_captain_player_id
effective_multiplier
auto_sub_resolution_source
```

Trong live:

- dùng snapshot picks, không fetch lại toàn bộ 40 squad mỗi 60 giây;
- tính live contribution từ player-fixture facts;
- auto-sub/captain resolution được đánh dấu provisional;
- khi FPL công bố resolution cuối, đối chiếu và tạo revision nếu khác.

Bench Boost làm toàn bộ bench picks có multiplier `1`. Triple Captain chỉ đổi multiplier của effective captain thành `3`. Wildcard/Free Hit ảnh hưởng transfers/squad source nhưng không được tự xóa transfer cost do FPL công bố.

## 7. Calculation pipeline

Một calculation run đi theo thứ tự:

```text
1. Chọn input raw/normalized revisions và ruleset
2. Aggregate player-fixture -> player-GW
3. Resolve counted picks, auto-subs, captain, chip
4. Tính official gross/net và matchup exposure
5. Detect violation candidates
6. Áp decision/override/replacement overlay
7. Ghi Classic contribution
8. Ghi Cup qualification ledger
9. Tính H2H/Cup match
10. Tính TotW và highlights
11. Tính standings
12. Publish snapshot revision
```

Các bước phải deterministic với cùng input revision, rule version và override set. Run ghi `input_hash` và `output_hash`; rerun cùng input phải cho cùng output.

Replacement average được tính trước khi resolve competition scores nhưng sau khi biết điểm net của sample. Mọi locked manager cùng division/GW dùng cùng một sample snapshot để không có vòng lặp.

## 8. Snapshot và versioning

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

Một snapshot set liên kết đồng bộ:

- manager scores;
- Classic standings;
- H2H results/standings;
- Cup qualification/matches;
- TotW/highlights;
- matchup details.

API không được trộn rows từ hai snapshot revisions khác nhau trong một response.

### 8.2 State machine

```text
upcoming -> live -> provisional -> final
final --admin reopen--> provisional (revision mới) -> final (revision mới)
```

- Live revision có thể publish nhiều lần.
- Chuyển final phải dùng transaction và advisory lock theo GW.
- Final snapshot không update/delete.
- Late source revision sau final tạo `source_diff_alert`.
- Chỉ admin command có lý do mới tạo reopen revision.
- Bracket vòng sau lưu `source_final_snapshot_id`; nếu refinal thay đổi winner, hệ thống cảnh báo impact và yêu cầu admin xác nhận migration bracket.

### 8.3 Audit và reproducibility

Mỗi public kết quả final phải trả được:

```text
snapshot_id
revision
ruleset_version
calculated_at
finalized_at
```

Audit payload dùng before/after JSON đã redact PII/secret. Audit append-only; database role của application không có quyền hard-delete audit row.

## 9. Đồng bộ FPL

### 9.1 Gateway

Mọi HTTP call đi qua `FplGateway`:

- base URL và endpoint mapping cấu hình được;
- timeout ngắn, retry exponential backoff + jitter;
- giới hạn concurrency;
- schema validation;
- conditional request/cache khi endpoint hỗ trợ;
- circuit breaker;
- metric latency/status/schema error;
- user agent rõ ràng theo quyền sử dụng đã được BTC xác nhận.

Không để domain service phụ thuộc trực tiếp JSON shape của FPL. Parser/adapter có version riêng.

### 9.2 Lịch job

Trước mùa:

```text
- sync bootstrap/player/teams/fixtures
- validate 40 entry IDs
- import manager và division membership
- generate + lock H2H schedule
- create Cup config
```

Sau deadline mỗi GW:

```text
- fetch picks/entry history/chip/transfer data cho 40 manager
- retry manager endpoint chưa mở với backoff
- persist immutable deadline snapshots
- detect transfer-cost candidates
```

Trong live:

```text
- mỗi 60 giây theo cấu hình: sync shared live-player data + fixtures
- chỉ fetch payload shared một lần mỗi tick
- recalculate khi payload hash/revision thay đổi
- publish live snapshot
```

Không refetch 40 picks mỗi phút nếu deadline snapshot không đổi.

Sau fixtures:

```text
- chuyển provisional
- đối chiếu auto-sub/effective captain
- tính tie-break, TotW, standings
- chờ finalization gate/admin
```

### 9.3 Idempotency và concurrency

- Job key: `(job_type, season, gameweek, logical_tick/input_hash)`.
- Distributed advisory lock ngăn hai worker chạy cùng GW.
- Insert raw/decision dùng unique constraints.
- Calculation publish theo compare-and-swap current revision.
- Retry không được tạo duplicate violation, threshold action, match result hoặc audit event.

### 9.4 Degraded mode

Khi FPL lỗi:

- giữ snapshot thành công gần nhất;
- hiển thị `last_updated_at` và cảnh báo stale;
- không đổi snapshot sang final;
- không thay missing data bằng `0`;
- queue retry và cảnh báo admin sau ngưỡng cấu hình.

## 10. API boundary

Tách router/schema:

```text
/api/public/*
/api/admin/*
/api/internal/jobs/*
```

Public response dùng DTO allowlist, không serialize ORM manager trực tiếp.

Ví dụ:

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

Mutation yêu cầu:

- authentication;
- authorization;
- CSRF protection nếu dùng cookie;
- `Idempotency-Key`;
- reason cho action nhạy cảm;
- optimistic concurrency (`expected_revision`);
- audit trong cùng transaction.

## 11. Authentication và security

### 11.1 Quyền

RBAC tối thiểu:

```text
public          # chỉ public read
admin_viewer    # xem admin, bao gồm PII nếu được cấp
competition_admin # rule decisions, finalize, bracket
super_admin     # quản lý account/quyền, export PII
```

Không suy ra quyền PII chỉ từ quyền xem standings.

### 11.2 Session

- Dùng identity provider/OIDC đáng tin cậy hoặc auth library production-ready.
- Bắt buộc MFA cho competition admin/super admin nếu provider hỗ trợ.
- Session cookie: `HttpOnly`, `Secure`, `SameSite=Lax/Strict`.
- Session ngắn hạn; revoke được.
- Password tự triển khai, nếu buộc phải dùng, phải hash bằng Argon2id/bcrypt và có rate limit/lockout.

### 11.3 App security

- TLS toàn tuyến.
- CORS allowlist chính xác.
- CSRF token cho cookie-authenticated mutations.
- Rate limit login, admin mutation và public endpoint tốn tài nguyên.
- Validate ID/enum/range bằng schema; parameterized SQL qua ORM.
- Security headers: CSP, HSTS, frame-ancestors, nosniff.
- Secret lấy từ secret manager/environment; không commit.
- PII mã hóa at rest ở application/KMS hoặc database encryption phù hợp.
- Backup mã hóa; export PII có watermark/audit và thời hạn.
- Log redact phone, Facebook URL, token, cookie và raw contact payload.

Public cache key và CDN response không bao giờ chứa admin DTO/PII.

## 12. Observability và vận hành

Structured log:

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

Metric/alert tối thiểu:

- FPL sync success/error và payload age;
- schema drift;
- calculation duration/failure;
- snapshot publish/finalization;
- stale live data;
- worker lock contention;
- pending violation/admin review;
- audit write failure;
- backup success và restore drill.

Audit write hoặc final snapshot transaction thất bại phải làm toàn bộ admin command rollback.

Backup PostgreSQL tự động; kiểm thử restore trước mùa và định kỳ. Tạo runbook cho:

- FPL outage;
- sai parser/schema;
- final nhầm GW;
- late point correction;
- admin account compromise;
- database restore.

## 13. Biên triển khai và migration

Mỗi release gồm:

```text
frontend image/version
backend image/version
database migration version
ruleset/algorithm version
```

Migration production theo nguyên tắc expand/contract; không drop cột/dữ liệu cùng release đang còn code đọc. Seed cấu hình 2026/27 bằng migration/command idempotent, không chỉnh tay database.

Các environment:

```text
local
staging (dữ liệu giả lập/replay đã ẩn PII)
production
```

Không copy phone/Facebook production sang staging. Trước GW1 phải replay ít nhất một mùa/GW fixture có captain, auto-sub, chip, DGW, violation, Cup/H2H và finalization.

## 14. Quyết định kiến trúc không được phá

1. Raw, derived và override là ba lớp riêng.
2. Final là revision bất biến, không phải boolean trên một row mutable.
3. Player-fixture là grain nguồn cho live/DGW.
4. Deadline picks là snapshot, không phải dữ liệu fetch lại mỗi tick.
5. Penalty và Cup qualification là ledger.
6. Public API dùng DTO allowlist và không chạm bảng private contact.
7. Job nền idempotent và có distributed lock.
8. Một response standings/matchup dùng một snapshot revision nhất quán.
