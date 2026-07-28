# VMF Fantasy League 2026/27 — FPL API Contract

**Mã tài liệu:** `VMF-FPL-CONTRACT-2026-27`
**Phiên bản contract:** `1.0.0-draft`
**Liên quan:** [`RULEBOOK.md`](./RULEBOOK.md), [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## 1. Tuyên bố quan trọng

FPL không công bố các JSON endpoint dưới đây như một API dành cho bên thứ ba có versioning, SLA hoặc cam kết tương thích. Chúng là các endpoint web đang quan sát được trên host chính thức của Fantasy Premier League.

Vì vậy:

- đây là **unofficial/undocumented API contract của phía VMF**, không phải contract do FPL bảo đảm;
- endpoint, field, kiểu dữ liệu, thời điểm mở dữ liệu và giới hạn truy cập có thể thay đổi không báo trước;
- việc endpoint trả HTTP `200` hôm nay không tạo SLA cho mùa giải;
- VMF phải lưu raw payload, version parser và phát hiện schema drift;
- không được coi một response lỗi/missing là điểm `0`;
- không được final một GW khi nguồn bắt buộc đang stale hoặc bị quarantine;
- mọi request phải tuân theo quyền sử dụng dữ liệu mà BTC đã xác nhận, với tần suất có kiểm soát;
- không tự động đăng nhập, không dùng cookie/token cá nhân và không tìm cách vượt cơ chế che picks trước deadline.

## 2. Base URL và transport

Base URL production:

```text
https://fantasy.premierleague.com/api/
```

Ví dụ canonical:

```text
https://fantasy.premierleague.com/api/bootstrap-static/
```

Quy tắc gateway:

- chỉ dùng HTTPS và verify certificate;
- allowlist host đúng `fantasy.premierleague.com`;
- path phải bắt đầu bằng `/api/`;
- ID path parameter phải là số nguyên dương;
- gửi `Accept: application/json`;
- dùng một `User-Agent` ổn định, nhận diện ứng dụng VMF;
- không gửi `Authorization`, FPL session cookie hoặc CSRF token cho các endpoint trong contract này;
- timeout, retry, concurrency và response-size limit được cấu hình tập trung;
- chỉ follow redirect cùng host; redirect sang host khác bị từ chối và cảnh báo;
- giữ dấu `/` cuối path vì đây là dạng canonical đang dùng.

Không hard-code base URL ở domain service. Chỉ `FplGateway` được biết URL ngoài.

## 3. Registry endpoint

### 3.1 Endpoint bắt buộc

| Mã | Method và path | Mục đích chính |
|---|---|---|
| `FPL_BOOTSTRAP` | `GET bootstrap-static/` | Danh mục GW, player, Premier League team, position và metadata mùa |
| `FPL_FIXTURES` | `GET fixtures/` hoặc `GET fixtures/?event={gw}` | Fixture, kickoff, trạng thái, DGW/BGW, trận hoãn |
| `FPL_EVENT_LIVE` | `GET event/{gw}/live/` | Điểm và stats live theo player/fixture |
| `FPL_ENTRY` | `GET entry/{entry_id}/` | Validate entry, tên team hiện tại và trạng thái profile |
| `FPL_ENTRY_HISTORY` | `GET entry/{entry_id}/history/` | Điểm GW, transfer cost, bench points, chip/history |
| `FPL_ENTRY_PICKS` | `GET entry/{entry_id}/event/{gw}/picks/` | Squad/picks, captain, multiplier, auto-sub, active chip |
| `FPL_ENTRY_TRANSFERS` | `GET entry/{entry_id}/transfers/` | Lịch sử player in/out phục vụ kiểm tra và highlights |

### 3.2 Endpoint hỗ trợ

| Mã | Method và path | Mục đích |
|---|---|---|
| `FPL_ELEMENT_SUMMARY` | `GET element-summary/{player_id}/` | Backfill/đối chiếu lịch sử player-fixture, fixture sắp tới và debug |

Endpoint hỗ trợ không được poll cho toàn bộ player mỗi phút. Live scoring vẫn lấy `event/{gw}/live/` và `fixtures/` làm nguồn chính.

### 3.3 Endpoint league tùy chọn

| Mã | Method và path quan sát được | Mục đích giới hạn |
|---|---|---|
| `FPL_CLASSIC_LEAGUE` | `GET leagues-classic/{league_id}/standings/?page_standings={page}&phase={phase}` | Hỗ trợ import/đối chiếu membership Classic |
| `FPL_H2H_LEAGUE` | `GET leagues-h2h/{league_id}/standings/?page_standings={page}` | Hỗ trợ đối chiếu membership H2H nếu route/schema còn hoạt động |

Hai endpoint league là **optional adapter**:

- VMF tự tính Classic/H2H standings từ 40 manager đã đăng ký;
- không lấy rank, H2H table points hoặc kết quả trận của FPL league làm nguồn VMF;
- route H2H phải được smoke-test theo mùa vì schema/route thực tế có thể thay đổi;
- nếu endpoint league lỗi, thay schema hoặc không public, chỉ tính năng import/đối chiếu bị degraded; scoring VMF vẫn hoạt động;
- pagination phải chạy đến khi `has_next = false`, không giả định page đầu chứa đủ 40 người;
- `phase` phải lấy từ dữ liệu mùa/cấu hình đã kiểm tra, không mặc định vĩnh viễn bằng `1`.

Nếu cần đối chiếu official FPL H2H match list về sau, route đó phải được thêm bằng một contract version mới; không suy ra URL trong domain code.

## 4. Public access và thời điểm dữ liệu

Các endpoint bắt buộc hiện được thiết kế như nguồn đọc anonymous khi dữ liệu tương ứng đã public. “Public” không có nghĩa là luôn sẵn sàng.

| Endpoint | Auth VMF gửi | Thời điểm/điều kiện mong đợi | Cách hiểu khi chưa có |
|---|---|---|---|
| Bootstrap | Không | Quanh năm/mùa đang mở | Lỗi nguồn; dùng cache còn hạn |
| Fixtures | Không | Khi lịch đã được FPL công bố; có thể đổi | Fixture chưa gán GW có thể có `event = null` |
| Event live | Không | Có thể có payload trước GW; có ý nghĩa live khi fixture bắt đầu | Empty/zero không tự chứng minh GW final hoặc player blank |
| Entry profile | Không | Sau khi entry hợp lệ tồn tại và public | 404/403 đơn lẻ không đủ kết luận team locked/deleted |
| Entry history | Không | Lịch sử đã public; current GW cập nhật theo FPL | Missing current row là “not available”, không phải zero |
| Entry picks | Không | Picks của người khác chỉ được dùng sau deadline GW | Trước deadline/đang mở chậm: sealed/not ready; retry theo lịch |
| Entry transfers | Không | Chỉ ingest phần FPL đã public sau deadline | Không poll để tìm transfer chưa public |
| Element summary | Không | Thường public khi player catalog tồn tại | Optional; failure không chặn live nếu nguồn chính đủ |
| League standings | Không | Tùy league/route/schema/quyền public hiện tại | Optional unavailable; không chặn scoring |

VMF không gọi endpoint authenticated để xem picks trước deadline. Nếu FPL đổi endpoint bắt buộc sang yêu cầu authentication:

1. circuit breaker dừng request;
2. hệ thống giữ snapshot gần nhất và báo admin;
3. BTC đánh giá một phương án được FPL cho phép;
4. không tự động hóa login hoặc dùng credential của HLV để lách giới hạn.

## 5. Contract từng endpoint

### 5.1 `bootstrap-static/`

URL:

```text
GET https://fantasy.premierleague.com/api/bootstrap-static/
```

Các collection tối thiểu VMF quan tâm:

```text
events[]
teams[]
elements[]
element_types[]
phases[]              # nếu còn tồn tại trong schema
game_settings         # metadata, không dùng làm nguồn luật VMF
```

Field normalized tối thiểu:

```text
events:
  id
  name
  deadline_time
  finished
  data_checked
  is_previous
  is_current
  is_next

teams:
  id
  name
  short_name

elements:
  id
  team
  element_type
  web_name
  first_name
  second_name
  now_cost
  status

element_types:
  id
  singular_name
  squad_select
  squad_min_play
  squad_max_play
```

Module sử dụng:

- event/deadline catalog;
- player/team/position dimensions;
- formation validation;
- UI metadata;
- scheduler transition quanh deadline;
- reconciliation event state.

Không sử dụng:

- `total_players`;
- player ownership/global popularity để xếp hạng VMF;
- overall/global rank;
- bất kỳ field nào để thay luật trong `RULEBOOK.md`.

Field mới được phép bỏ qua. Thiếu `events`, `teams`, `elements`, ID hoặc quan hệ team/position làm payload bị quarantine.

### 5.2 `fixtures/`

URL:

```text
GET https://fantasy.premierleague.com/api/fixtures/
GET https://fantasy.premierleague.com/api/fixtures/?event={gw}
```

Field normalized tối thiểu:

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

Module sử dụng:

- player-fixture grain;
- fixture status;
- player remaining/effective remaining;
- DGW/BGW;
- postponed/rescheduled fixture;
- live/provisional gate.

`event` và `kickoff_time` phải chấp nhận `null`. Fixture có thể chuyển GW; một revision mới phải cập nhật mapping bằng provenance, không update lịch sử final tại chỗ.

Không chỉ dựa vào `finished` của một response để final GW. Finalization còn cần live data, picks, schema health và rule/admin gate.

### 5.3 `event/{gw}/live/`

URL:

```text
GET https://fantasy.premierleague.com/api/event/{gw}/live/
```

Shape quan sát cần adapter hỗ trợ:

```text
elements[]:
  id
  stats:
    minutes
    total_points
    goals_scored
    yellow_cards
    red_cards
    bonus
    ...
  explain[]:
    fixture
    stats[]:
      identifier
      points
      value
```

Module sử dụng:

- live player score;
- player-fixture stats/explanation;
- counted goals/cards;
- bonus/provisional correction;
- H2H/Cup live score;
- remaining status kết hợp fixture.

`stats` có thể thêm identifier theo mùa. Parser:

- giữ unknown fields trong raw;
- map các field biết;
- không fail chỉ vì có field mới;
- quarantine nếu thiếu `elements[].id` hoặc `stats.total_points`;
- cho phép `explain` rỗng khi player chưa có fixture/fixture chưa bắt đầu;
- không bịa phân bổ theo fixture nếu tổng player-GW có điểm nhưng `explain` chưa đủ.

Nếu `explain` thay shape, live total có thể tiếp tục ở trạng thái provisional nhưng player-fixture tie-break/matchup bị đánh dấu incomplete và không được final.

### 5.4 `entry/{entry_id}/`

URL:

```text
GET https://fantasy.premierleague.com/api/entry/{entry_id}/
```

Field normalized tối thiểu:

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

Module sử dụng:

- validate `fpl_entry_id`;
- hiển thị current FPL team name bên cạnh registered VMF team name;
- phát hiện đổi team name để admin review;
- hỗ trợ kiểm tra entry availability.

Không tự ghi đè tên đăng ký VMF. Không dùng `summary_overall_rank`, `summary_event_rank` hoặc rank global.

Một lỗi 404/403/5xx không tự chuyển manager sang locked/deleted. Gateway tạo availability incident; chỉ sau retry, đối chiếu nguồn và admin decision mới đổi trạng thái nghiệp vụ.

### 5.5 `entry/{entry_id}/history/`

URL:

```text
GET https://fantasy.premierleague.com/api/entry/{entry_id}/history/
```

Shape quan sát:

```text
current[]:
  event
  points
  total_points
  rank nullable
  overall_rank nullable
  bank
  value
  event_transfers
  event_transfers_cost
  points_on_bench

chips[]:
  name
  time
  event

past[] nullable
```

Module sử dụng:

- source event points;
- transfer cost;
- total-points reconciliation;
- bench points;
- chip history;
- team value/highlights.

Không ingest `rank` hoặc `overall_rank` vào VMF standings.

Adapter ban đầu map:

```text
source_gross_points = current[].points
transfer_cost       = current[].event_transfers_cost
official_net_points = source_gross_points - transfer_cost
```

Trước khi final, phải kiểm tra semantic invariant trên dữ liệu đủ ổn định:

```text
delta(total_points) ≈ points - event_transfers_cost
```

Nếu FPL thay đổi ý nghĩa `points` hoặc `total_points`, mismatch tạo semantic schema drift; không âm thầm trừ transfer cost hai lần.

`rank` có thể rất lớn hoặc nullable và không liên quan đến VMF.

### 5.6 `entry/{entry_id}/event/{gw}/picks/`

URL:

```text
GET https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gw}/picks/
```

Shape quan sát:

```text
active_chip nullable
automatic_subs[] nullable
entry_history:
  event
  points
  total_points
  event_transfers
  event_transfers_cost
  points_on_bench
picks[]:
  element
  position
  multiplier
  is_captain
  is_vice_captain
```

Module sử dụng:

- deadline squad snapshot;
- starting XI/bench position;
- original captain/vice;
- multiplier và counted picks;
- active chip;
- auto-sub reconciliation;
- transfer-cost cross-check.

Timing:

- fetch lần đầu sau deadline;
- retry có backoff nếu response chưa mở;
- không fetch toàn bộ 40 picks mỗi live tick;
- refresh ở các phase transition, đặc biệt sau khi fixtures kết thúc, vì multiplier/automatic substitutions có thể được FPL resolve lại;
- mọi payload khác hash tạo pick snapshot revision mới.

Không coi `multiplier = 0` ở payload chưa ổn định là final bench/auto-sub decision. Giữ original selection facts và effective resolution có revision riêng.

Picks của current GW trước deadline là sealed data. VMF không được thử endpoint authenticated hoặc poll dày để truy cập sớm.

### 5.7 `entry/{entry_id}/transfers/`

URL:

```text
GET https://fantasy.premierleague.com/api/entry/{entry_id}/transfers/
```

Field normalized tối thiểu:

```text
element_in
element_out
element_in_cost
element_out_cost
entry
event
time
```

Module sử dụng:

- transfer list;
- best/worst transfer estimate;
- audit/reconciliation số transfer;
- violation investigation.

`event_transfers_cost` trong entry history/picks entry history mới là nguồn transfer cost chính. Không tự tính cost từ số row transfer vì free transfer, chip và thay đổi luật FPL có thể làm suy luận sai.

Chỉ ingest transfer đã được FPL công khai sau deadline. Không dùng endpoint này để theo dõi hành vi trước deadline.

### 5.8 `element-summary/{player_id}/`

URL:

```text
GET https://fantasy.premierleague.com/api/element-summary/{player_id}/
```

Shape quan sát:

```text
fixtures[]:
  id
  event nullable
  kickoff_time nullable
  is_home
  difficulty

history[]:
  element
  fixture
  round
  total_points
  minutes
  goals_scored
  yellow_cards
  red_cards
  bonus
  ...

history_past[] nullable
```

Module sử dụng:

- backfill/repair player-fixture history;
- đối chiếu DGW và trận hoãn;
- admin diagnostics;
- trang player detail nếu có.

Không dùng làm nguồn poll live chính. Chỉ fetch:

- on demand;
- khi contract reconciliation phát hiện player-fixture thiếu;
- sau final để backfill;
- trong replay/testing.

Nếu element summary và event live mâu thuẫn khi GW chưa final, giữ cả hai revisions và đánh dấu reconciliation pending. Sau final, nguồn chọn làm authoritative phải được adapter/rule version ghi rõ; không update im lặng.

### 5.9 League standings optional

Classic URL template:

```text
GET https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/?page_standings={page}&phase={phase}
```

Shape tối thiểu nếu adapter bật:

```text
league:
  id
  name

standings:
  page
  has_next
  results[]:
    entry
    entry_name
    player_name
    rank nullable
    total nullable
```

H2H URL template cần smoke-test:

```text
GET https://fantasy.premierleague.com/api/leagues-h2h/{league_id}/standings/?page_standings={page}
```

H2H adapter chỉ được bật khi runtime contract test xác nhận:

- route trả JSON;
- có league identity;
- có paginated standings/results với entry ID;
- parser version hỗ trợ shape thực tế.

Hai adapter chỉ xuất:

```text
league_id
league_name
member_entry_ids
observed_at
source_revision
```

Rank/total của league nguồn không đi vào Classic/H2H VMF. Nếu cần kiểm tra Season 2 join, membership observation chỉ tạo candidate; admin/rule workflow quyết định violation.

## 6. Mapping endpoint sang module

| Module | Nguồn chính | Nguồn đối chiếu |
|---|---|---|
| Manager registration | Entry profile | Classic/H2H league optional |
| Event scheduler | Bootstrap events | Fixtures |
| Player/team catalog | Bootstrap | Element summary on demand |
| Deadline squad/chip/captain | Entry picks | Entry history/chips |
| Transfer cost | Entry history + picks entry history | Transfer list |
| Live player score | Event live | Fixtures, element summary on demand |
| DGW/BGW/postponed | Fixtures + live explain | Element summary |
| Classic score | Derived picks/live + history cost | History total reconciliation |
| H2H/Cup score | VMF derived effective score | Không dùng FPL league rank/result |
| Goals/cards tie-break | Counted picks + live player-fixture | Element summary after final |
| Locked/deleted detection | Availability incident + admin decision | Entry/history/picks responses |
| Season 2 membership | VMF admin registry | League standings optional |
| Transfer highlights | Transfers + player-fixture stats | History event transfer count |

Không endpoint nào cung cấp “VMF score” trực tiếp. Competition engine luôn áp [`RULEBOOK.md`](./RULEBOOK.md) trên source facts.

## 7. Cache và cadence

Mọi giá trị dưới đây là default có thể cấu hình. Scheduler thêm jitter để không tạo request burst.

| Endpoint | Ngoài live | Gần deadline/transition | Khi fixture live | Sau fixture đến final |
|---|---:|---:|---:|---:|
| Bootstrap | 30 phút | 5 phút | 5 phút | 5–15 phút |
| Fixtures theo GW | 15 phút | 5 phút | 60 giây | 2–5 phút |
| Event live | Không poll future GW | 5 phút để readiness check | 60 giây | 2–5 phút rồi giảm còn 15 phút |
| Entry profile | 6 giờ | 1 lần validate | 6 giờ | 1 lần/ngày |
| Entry history | 6 giờ | Sau deadline | 10–15 phút | 5 phút khi reconcile |
| Entry picks | Không fetch sealed GW | Retry sau deadline 30–120 giây | Không poll mỗi tick; 10–15 phút | 2–5 phút đến khi auto-sub ổn định |
| Entry transfers | Không poll pre-deadline | 1 lần sau picks mở | 30–60 phút | 1 lần reconcile |
| Element summary | 6 giờ/on demand | On demand | Chỉ khi repair | Backfill/on demand |
| League standings | 30–60 phút | 5–15 phút khi kiểm tra join | Không cần | On demand |

Tối ưu bắt buộc:

- bootstrap, fixtures và event live là shared cache cho cả 40 manager;
- một tick chỉ fetch mỗi shared URL một lần;
- cache key gồm endpoint/path/query;
- parser output cache key thêm raw payload hash + parser version;
- calculation chỉ chạy khi source revision hoặc decision revision thay đổi;
- ETag/`If-None-Match` được dùng nếu server cung cấp, nhưng hệ thống không phụ thuộc việc có ETag.

Không poll player element summary theo kiểu `tổng số player × mỗi phút`.

## 8. Raw payload, version và schema drift

### 8.1 Raw record

Mỗi request attempt lưu metadata:

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

Không lưu cookie, auth header hoặc response header không cần thiết. Với non-JSON/error body, chỉ lưu phần body đã giới hạn kích thước và sanitize.

Raw success payload là append-only:

- cùng endpoint/request key/hash có thể deduplicate body nhưng vẫn ghi observation;
- payload khác hash tạo source revision mới;
- không sửa raw khi parser hoặc rule thay đổi;
- giữ raw ít nhất toàn bộ mùa 2026/27 và qua cửa sổ audit/đối soát do BTC quy định.

### 8.2 Version

Ba version độc lập:

```text
contract_version   # endpoint/field/timing contract
parser_version     # JSON -> normalized source facts
ruleset_version    # source facts -> VMF result
```

Mọi calculation run phải lưu cả ba. Thay parser không được ngụy trang thành thay luật.

### 8.3 Drift policy

Drift được phân loại:

| Loại | Ví dụ | Xử lý |
|---|---|---|
| Additive | FPL thêm field stats | Giữ raw, parser bỏ qua/map sau; không chặn |
| Nullable | Field từng bắt buộc thành `null` | Chỉ chấp nhận nếu contract cho nullable; nếu không quarantine |
| Missing required | Mất `elements[].id` | Quarantine endpoint revision |
| Type change | ID từ number thành object | Quarantine và alert |
| Enum expansion | Status mới | Lưu unknown, không map thành status cũ |
| Semantic | `points` đã bao gồm transfer cost | Invariant fail; chặn final và nâng parser/contract |
| Route/status | 404/HTML thay JSON | Circuit breaker, stale mode, alert |

Parser dùng “tolerant reader” với field mới nhưng strict cho invariant/identity. Không được dùng kiểu “catch all rồi mặc định `0`”.

Contract test tự động:

- chạy fixture raw đã version-control;
- smoke-test production endpoint read-only;
- so required field/type/nullability;
- chạy semantic invariants;
- báo diff trước khi deploy parser mới.

## 9. Retry, circuit breaker và stale strategy

### 9.1 Phân loại response

| Tình huống | Retry trong tick | Hành động |
|---|---|---|
| Network timeout/reset | Có, tối đa 3 attempt | Exponential backoff + jitter |
| HTTP 429 | Theo `Retry-After`; không spam | Mở endpoint throttle/circuit |
| HTTP 500/502/503/504 | Có, tối đa 3 attempt | Sau đó giữ stale và chờ tick kế |
| HTTP 401/403 | Không retry dày | Cảnh báo access contract thay đổi |
| HTTP 404 picks quanh deadline | Retry theo readiness schedule | Phân loại `sealed_or_not_ready`, không zero |
| HTTP 404 entry đã từng hợp lệ | Retry có giới hạn + availability incident | Không tự khóa/xóa manager |
| HTTP 404 ID chưa từng hợp lệ | Không retry liên tục | Validation error/admin review |
| HTTP 200 nhưng HTML/non-JSON | Không parse | Quarantine + circuit breaker |
| HTTP 200 JSON sai schema | Không publish normalized revision | Quarantine + alert |

Backoff default cho retry ngắn có thể là `1s, 3s, 9s` cộng jitter. Sau ba attempt, trả quyền điều phối cho scheduler; không busy-loop.

Circuit breaker tách theo endpoint code. Lỗi optional league/element summary không mở circuit cho live endpoint.

### 9.2 Staleness

Snapshot/API response public phải có:

```text
source_observed_at
calculated_at
last_success_at
is_stale
stale_reason
snapshot_revision
```

Default cảnh báo:

- live/fixtures: stale sau hơn 3 chu kỳ 60 giây;
- bootstrap transition: stale sau 15 phút;
- picks của current GW: missing sau deadline + grace window cấu hình;
- manager history: stale nếu chưa reconcile khi chuẩn bị provisional/final.

Khi stale:

- tiếp tục hiển thị snapshot thành công gần nhất;
- UI gắn nhãn “dữ liệu chậm cập nhật” và thời gian cuối;
- không đổi missing player/manager thành `0`;
- không phát sinh winner, TotW, penalty hoặc next-round bracket từ partial revision;
- không final GW;
- admin dashboard hiển thị endpoint/manager bị ảnh hưởng.

### 9.3 Finalization gate

Một GW chỉ eligible để final khi:

1. fixtures thuộc GW đã được resolve theo revision hiện tại;
2. event live payload required schema hợp lệ;
3. picks/history của tất cả manager active đã có, hoặc manager có quyết định replacement/status hợp lệ;
4. transfer cost đã reconcile;
5. auto-sub/effective captain đủ dữ liệu;
6. không có source revision required đang quarantine/stale;
7. violation candidate cần thiết đã được review hoặc được finalization policy cho phép pending rõ ràng;
8. calculation run dùng một input revision set nhất quán.

Không coi một field `finished`/`data_checked` duy nhất là toàn bộ finalization contract. Admin/rule finalization tạo snapshot final bất biến theo kiến trúc.

## 10. Data quality và reconciliation

Các invariant tối thiểu:

```text
entry response id == requested entry_id
pick elements tồn tại trong bootstrap elements
fixture team_h/team_a tồn tại trong bootstrap teams
live element id tồn tại trong player catalog
fixture explain.fixture tồn tại trong fixtures hoặc được đánh dấu unresolved
GW nằm trong 1..38
position của picks là duy nhất trong squad snapshot
chỉ một original captain và một original vice-captain
transfer event map được sang GW
history transfer cost == picks entry_history transfer cost khi cả hai đã ổn định
```

Mismatch không tự chọn nguồn một cách im lặng:

- lưu cả hai raw revisions;
- tạo reconciliation issue;
- quy định source precedence theo parser/contract version;
- chặn phần kết quả bị ảnh hưởng khỏi final.

Một mismatch optional không liên quan có thể không chặn toàn GW, nhưng lý do phải được ghi machine-readable.

## 11. Security và privacy

- Endpoint gateway không nhận URL tùy ý từ request user; chỉ nhận endpoint code + typed params.
- Validate numeric range để tránh path traversal/SSRF.
- Response size limit ngăn payload bất thường làm cạn memory.
- Không proxy raw FPL payload thẳng ra public API.
- Public API dùng DTO VMF và loại mọi phone/Facebook/admin note.
- Không log full manager contact record cùng source payload.
- Không dùng global rank dù payload có field đó.
- League member list chỉ dùng trong admin workflow nếu BTC cho phép; không tự công bố thêm dữ liệu ngoài phạm vi giải.

## 12. Cấu hình đề xuất

```text
FPL_API_BASE_URL=https://fantasy.premierleague.com/api/
FPL_HTTP_CONNECT_TIMEOUT_SECONDS=3
FPL_HTTP_READ_TIMEOUT_SECONDS=10
FPL_HTTP_MAX_ATTEMPTS=3
FPL_HTTP_MAX_CONCURRENCY=4
FPL_LIVE_REFRESH_SECONDS=60
FPL_LIVE_STALE_AFTER_SECONDS=180
FPL_RESPONSE_MAX_BYTES=<giới hạn đã benchmark>
FPL_CONTRACT_VERSION=1.0.0-draft
FPL_ENABLE_CLASSIC_LEAGUE_ADAPTER=false
FPL_ENABLE_H2H_LEAGUE_ADAPTER=false
```

Không lưu secret trong file cấu hình repo. Hai league adapter bật theo season sau smoke-test; core scoring không phụ thuộc chúng.

## 13. Acceptance criteria cho gateway

1. Mọi endpoint bắt buộc đi qua cùng `FplGateway`.
2. Không request nào gửi FPL credential/cookie.
3. Picks không được truy cập trước deadline.
4. Shared live endpoint chỉ fetch một lần mỗi tick.
5. Raw payload và hash được giữ trước khi parse.
6. Rerun cùng raw + parser cho cùng normalized output.
7. Field mới không làm parser hỏng nếu invariant không đổi.
8. Missing/type/semantic drift bắt buộc quarantine và alert.
9. 404/timeout không biến score thành `0`.
10. Stale required source chặn finalization.
11. Optional league endpoint lỗi không chặn Classic/H2H VMF.
12. VMF standings không dùng rank/points từ FPL league endpoint.
13. DGW có provenance đến `player_id + fixture_id`.
14. Transfer cost được cross-check giữa history và picks.
15. Locked/deleted chỉ hình thành sau workflow admin, không từ một HTTP error.
16. Contract/parser/ruleset version xuất hiện trong calculation provenance.

## 14. Runbook khi endpoint thay đổi

Khi alert schema/route/access xuất hiện:

1. dừng publish normalized revision của endpoint bị ảnh hưởng;
2. giữ last-known-good snapshot và bật stale banner;
3. lưu response/error đã sanitize;
4. chạy contract diff trên staging;
5. xác định additive, breaking hay semantic drift;
6. cập nhật fixture test và parser với version mới;
7. replay ít nhất một GW normal, DGW, captain/auto-sub và transfer-cost case;
8. deploy parser;
9. backfill từ raw payload nếu cần;
10. chỉ mở finalization sau khi reconciliation pass.

Không hot-fix bằng cách sửa raw row hoặc đặt missing field về `0`.
