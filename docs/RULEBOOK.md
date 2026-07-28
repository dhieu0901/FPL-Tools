# VMF Fantasy League 2026/27 — Rulebook

**Mã tài liệu:** `VMF-RULES-2026-27`
**Phiên bản:** `1.0.0-draft`
**Phạm vi:** Mùa Fantasy Premier League 2026/27
**Trạng thái:** Nguồn luật nghiệp vụ chuẩn để triển khai và kiểm thử

## 1. Thẩm quyền và cách đọc tài liệu

Tài liệu này chuẩn hóa:

- luật tuyển quân VMF 2025/26;
- project specification ban đầu;
- các quyết định đã được BTC xác nhận cho mùa 2026/27.

Khi có mâu thuẫn, thứ tự ưu tiên là:

1. quyết định đã được BTC xác nhận cho mùa 2026/27;
2. tài liệu này;
3. luật tuyển quân VMF 2025/26;
4. project specification và các cấu hình kỹ thuật mặc định.

Mọi thay đổi luật sau khi mùa giải bắt đầu phải tạo một `ruleset_version` mới, ghi rõ thời điểm có hiệu lực và được lưu trong audit log. Không sửa ngược một phiên bản luật đã dùng để chốt kết quả.

Các từ khóa:

- **phải**, **không được**: quy tắc bắt buộc;
- **có thể**: lựa chọn vận hành của BTC;
- **BTC/admin**: tài khoản có quyền quản trị VMF;
- **HLV/manager**: người tham dự giải;
- **GW**: Gameweek chính thức của FPL.

## 2. Thành viên và dữ liệu đăng ký

- Giải có 40 HLV, định danh ngoài hệ thống bằng `fpl_entry_id`.
- Tên HLV và tên đội đăng ký không được tự thay đổi trong thời gian giải diễn ra.
- Nếu tên đội trên FPL thay đổi, hệ thống chỉ cảnh báo; không tự ghi đè tên đội VMF.
- Mỗi HLV thuộc đúng một division tại một GW: `HIGH` hoặc `LOW`.
- Số điện thoại và liên kết Facebook là dữ liệu riêng tư, chỉ admin được xem.
- Không có đăng ký công khai trong phiên bản này. Việc thêm, sửa trạng thái hoặc loại HLV là thao tác admin và phải được ghi audit.

Các trạng thái nghiệp vụ tối thiểu:

```text
active
suspended
removed
locked
deleted
pending_review
```

## 3. Khái niệm điểm chuẩn

### 3.1 Điểm GW

```text
official_gross_points = điểm GW do FPL công bố
transfer_cost         = điểm trừ chuyển nhượng do FPL công bố
official_net_points   = official_gross_points - transfer_cost
```

`official_net_points` là điểm cơ sở cho Classic, H2H, Cup, TotW và các tie-break, trừ khi một điều khoản cụ thể quy định điểm thay thế, điểm không hợp lệ hoặc admin override.

Hệ thống phải giữ riêng:

- dữ liệu FPL gốc;
- kết quả tính toán theo luật VMF;
- penalty;
- replacement;
- admin override.

Không được sửa dữ liệu FPL gốc để biểu diễn một quyết định VMF.

### 3.2 Điểm hiệu lực

`effective_net_points` là điểm được giải đấu sử dụng sau khi áp dụng nguồn điểm hợp lệ:

1. admin override đang có hiệu lực;
2. replacement average hợp lệ;
3. `official_net_points`.

Penalty H2H và việc một GW đóng góp `0` vào bảng xét Cup là các ledger riêng, không sửa `official_net_points` hoặc điểm Classic.

### 3.3 Cầu thủ được tính điểm

Cầu thủ được tính gồm:

- cầu thủ thuộc đội hình cuối cùng sau auto-sub;
- cầu thủ dự bị khi Bench Boost có hiệu lực;
- đội trưởng hoặc đội phó thay thế theo kết quả cuối cùng của FPL.

Cầu thủ không được tính gồm:

- cầu thủ còn nằm trên ghế dự bị khi không dùng Bench Boost;
- cầu thủ bị auto-sub ra;
- cầu thủ không có trong squad của HLV.

Mỗi pick phải phân biệt tối thiểu:

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

### 3.4 Đội trưởng

Điểm captain dùng trong tie-break là đóng góp cuối cùng sau multiplier:

```text
captain_contribution_points =
    effective_captain_base_points * effective_captain_multiplier
```

- Captain thường có multiplier `2`.
- Triple Captain có multiplier `3`.
- Nếu captain không thi đấu và FPL chuyển băng cho vice-captain, dùng đóng góp đã nhân của vice-captain.
- Nếu cả captain và vice-captain đều không có hiệu lực, captain contribution là `0`.

### 3.5 Bàn thắng và thẻ

- Chỉ cộng bàn thắng/thẻ của cầu thủ được tính điểm.
- Bàn thắng và thẻ là số sự kiện thực, không nhân theo multiplier captain.
- Một bàn của cầu thủ dự bị không dùng Bench Boost đóng góp `0`.
- Một bàn của cầu thủ dự bị có Bench Boost đóng góp `1`.
- Mỗi thẻ vàng hoặc thẻ đỏ được tính là một thẻ:

```text
total_cards = yellow_cards + red_cards
```

Nếu một cầu thủ có nhiều trận trong một DGW, cộng sự kiện của tất cả fixture thuộc GW đó.

## 4. Classic

### 4.1 Cấu trúc

| Giai đoạn | Gameweek | HIGH | LOW |
|---|---:|---:|---:|
| Classic Season 1 | GW1–GW19 | 20 | 20 |
| Classic Season 2 | GW20–GW38 | 20 | 20 |

Điểm Season 2 reset về `0` tại GW20. Điểm toàn mùa vẫn được giữ cho thống kê.

Sau GW19:

- 6 HLV cuối HIGH xuống LOW;
- 6 HLV đầu LOW lên HIGH;
- membership mới có hiệu lực từ GW20.

Sau GW38:

- 6 HLV cuối HIGH xuống LOW cho kỳ tiếp theo;
- 6 HLV đầu LOW lên HIGH;
- 6 HLV cuối LOW phải đăng ký xét tuyển lại nếu muốn tiếp tục.

Membership phải được lưu theo giai đoạn/GW; không được cập nhật một cột division duy nhất làm thay đổi lịch sử.

### 4.2 Xếp hạng

- Điểm Classic là tổng `effective_net_points` thuộc phạm vi Season tương ứng.
- Bảng xếp hạng chỉ so sánh HLV trong cùng division của giai đoạn đó.
- Không dùng overall rank của FPL.
- Bảng hiển thị dùng competition ranking, ví dụ `1, 2, 2, 4`.

Khi cần chọn người qua một ranh giới có ý nghĩa nghiệp vụ, áp dụng mục 7.

## 5. TotW

TotW là HLV có `effective_net_points` cao nhất trong GW khi so với toàn bộ 40 HLV đủ điều kiện.

- Chip và transfer cost đã nằm trong điểm dùng để xét.
- Nếu nhiều HLV đồng điểm cao nhất, tất cả cùng nhận một TotW.
- Mỗi người đồng hạng được cộng `1` vào cumulative TotW.
- Điểm `replacement_average` không đủ điều kiện nhận TotW.
- HLV dùng replacement cũng không đủ điều kiện nhận giải/highlight cá nhân của GW đó.

Cumulative TotW tại một cutoff chỉ tính các TotW từ đầu giai đoạn liên quan đến hết cutoff, không dùng dữ liệu của GW tương lai.

## 6. H2H

### 6.1 Vòng bảng

- 40 HLV thi đấu trong một H2H chung từ GW1 đến GW35.
- Mỗi HLV có đúng một trận mỗi GW.
- Không tự đấu chính mình.
- Lịch được tạo trước mùa, admin được sửa trước khi khóa và bất biến sau khi khóa, trừ một quyết định admin có audit.
- Điểm trận là `effective_net_points`.

Điểm bảng:

```text
thắng = 3
hòa   = 1
thua  = 0
```

Các chỉ số phải giữ:

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

`h2h_table_points` được phép âm.

### 6.2 Chọn top 8

Sau khi GW35 được final, tám HLV còn đủ điều kiện có thứ tự cao nhất vào play-off. Việc phân định ranh giới top 8 dùng mục 7 với:

```text
primary_points = h2h_table_points
period = GW1–GW35
```

Các chỉ số point difference, points for và số trận thắng vẫn được hiển thị nhưng không đứng trước chuỗi phân định ranh giới đã chốt tại mục 7.

### 6.3 Play-off

| GW | Vòng |
|---:|---|
| 36 | Tứ kết |
| 37 | Bán kết |
| 38 | Chung kết |

Seeding tứ kết:

```text
1 vs 8
4 vs 5
2 vs 7
3 vs 6
```

Bracket bán kết được cố định từ bracket tứ kết.

**H2H không có trận tranh hạng ba.** Hai HLV thua bán kết đồng hạng ba. GW38 chỉ có trận chung kết.

Trận play-off hòa điểm dùng chuỗi tie-break của Cup tại mục 8.4.

## 7. Quy tắc phân định ranh giới

Quy tắc này áp dụng khi một nhóm đồng điểm nằm vắt qua:

- ranh giới top 6 thăng hạng/xuống hạng;
- ranh giới top 8 H2H;
- ranh giới hạng 2/3 hoặc 14/15 của mỗi bảng xét Cup;
- một ranh giới chọn suất khác nếu cấu hình giải dẫn chiếu đến quy tắc này.

Áp dụng lần lượt:

1. **Điểm giai đoạn liên quan**, cao hơn đứng trước:
   - Classic: điểm Classic Season;
   - H2H: `h2h_table_points`;
   - Cup: `cup_qualification_points`.
2. **Cumulative TotW** đến hết cutoff của giai đoạn, nhiều hơn đứng trước.
3. **Điểm GW cao nhất** trong giai đoạn liên quan, cao hơn đứng trước. Với Cup, chỉ xét điểm đóng góp đủ điều kiện vào bảng xét Cup; GW vi phạm đã bị đưa về `0`.
4. **Admin bốc thăm** nếu vẫn hòa.

Việc bốc thăm phải lưu danh sách HLV đủ điều kiện, người thực hiện, thời gian, phương thức và kết quả. Không dùng random âm thầm trong job nền.

Quy tắc này chỉ phá hòa để chọn phía nào của ranh giới. Bảng hiển thị vẫn có thể giữ đồng hạng nếu không cần một quyết định chọn suất.

## 8. VMF Cup

### 8.1 Cup Season 1

Cutoff xét suất là sau khi GW14 final. Bảng xét Cup tính GW1–GW14.

| Thứ hạng trong mỗi division | Kết quả |
|---|---|
| 1–2 | Vào thẳng vòng 16 đội |
| 3–14 | Đá sơ loại |
| Còn lại | Không dự Cup |

Lịch:

| GW | Vòng |
|---:|---|
| 15 | Sơ loại |
| 16 | Vòng 16 đội |
| 17 | Tứ kết |
| 18 | Bán kết |
| 19 | Chung kết và tranh hạng ba |

### 8.2 Cup Season 2

Cup Season 2 có **cùng cơ cấu** với Cup Season 1. Cutoff xét suất là sau khi GW33 final. Bảng xét Cup tính GW20–GW33.

| Thứ hạng trong mỗi division | Kết quả |
|---|---|
| 1–2 | Vào thẳng vòng 16 đội |
| 3–14 | Đá sơ loại |
| Còn lại | Không dự Cup |

Lịch:

| GW | Vòng |
|---:|---|
| 34 | Sơ loại |
| 35 | Vòng 16 đội |
| 36 | Tứ kết |
| 37 | Bán kết |
| 38 | Chung kết và tranh hạng ba |

### 8.3 Bảng xét suất Cup

Mỗi Cup có một ledger độc lập:

```text
cup_qualification_points =
    sum(cup_qualification_contribution_by_gw)
```

Trong đó:

```text
confirmed excessive-transfer violation ở GW đó -> contribution = 0
không đủ điều kiện vì chưa join league Season 2 -> contribution = 0
trường hợp còn lại -> contribution = effective_net_points
```

Quy tắc `0` chỉ tác động bảng xét suất Cup:

- không sửa điểm Classic;
- không sửa điểm FPL gốc;
- không tự sửa kết quả H2H vòng bảng.

**Toàn bộ GW vi phạm** trong GW1–GW14 hoặc GW20–GW33 bị loại khỏi tổng điểm xét Cup, không chỉ GW đang đá một trận Cup.

Xếp suất được thực hiện riêng trong HIGH và LOW theo membership của Season tương ứng. Hòa tại ranh giới dùng mục 7.

### 8.4 Điểm trận và tie-break

Điểm trận Cup là `effective_net_points`, trừ walkover hoặc điểm đã bị vô hiệu theo mục 9.

Nếu hai bên hòa điểm và cả hai đều có điểm thật/override hợp lệ, xét lần lượt:

1. cumulative TotW nhiều hơn, tính đến hết GW đang đấu;
2. captain contribution trong GW cao hơn;
3. tổng số bàn của counted players trong GW nhiều hơn;
4. tổng số thẻ của counted players trong GW ít hơn;
5. điểm Classic Season hiện tại tính đến hết GW đó cao hơn;
6. admin bốc thăm.

Mỗi bước phải lưu input, kết quả so sánh và bước đã quyết định người thắng.

Quy tắc ưu tiên nguồn điểm:

- nếu hòa và chỉ một bên dùng `replacement_average`, bên có điểm thật/override hợp lệ đi tiếp trước khi chạy tie-break trên;
- nếu cả hai bên dùng `replacement_average`, không tự chọn; chuyển admin quyết định có audit.

Cup có trận tranh hạng ba ở GW19 và GW38.

## 9. Vi phạm

### 9.1 Vi phạm chuyển nhượng

HLV được phép chịu transfer cost tối đa `8` trong một GW.

```text
transfer_cost <= 8:
    detected_count = 0

transfer_cost > 8:
    detected_count = ceil((transfer_cost - 8) / 8)
```

Ví dụ chuẩn:

| Transfer cost | Số lần vi phạm phát sinh |
|---:|---:|
| 0, 4, 8 | 0 |
| 12, 16 | 1 |
| 20, 24 | 2 |
| 28 | 3 |

Số lần vi phạm được cộng dồn xuyên suốt GW1–GW38, không reset ở GW20. Một GW có thể làm vượt nhiều cấp ngay lập tức:

- cost `20` kích hoạt cấp 1 và cấp 2;
- cost `28` kích hoạt cấp 1, cấp 2 và cấp 3.

### 9.2 Quy trình xác nhận

Trạng thái tối thiểu:

```text
detected
pending_review
approved_exception
confirmed
rejected
overridden
```

- Detection là tự động và idempotent.
- Penalty không thể đảo ngược chỉ có hiệu lực từ một quyết định admin `confirmed` hoặc `overridden`.
- Trường hợp báo quên bật chip chuyển `pending_review`.
- Nếu admin duyệt ngoại lệ, số vi phạm xác nhận của event là `0`.
- Dù ngoại lệ được duyệt, transfer cost chính thức của FPL vẫn nằm trong `official_net_points`. Chỉ một score override riêng, có lý do và audit, mới thay đổi điểm hiệu lực.
- Nếu admin bác ngoại lệ, event được xác nhận theo công thức.

### 9.3 Hệ quả theo ngưỡng cộng dồn

Hệ quả được áp dụng khi tổng số lần vi phạm xác nhận **lần đầu chạm hoặc vượt** ngưỡng:

| Ngưỡng | Hệ quả |
|---:|---|
| 1 | Thu tiền tư cách; trừ một lần `6` điểm bảng H2H; áp dụng luật Cup đối với GW vi phạm |
| 2 | Chỉ được nhận 50% giá trị giải thưởng nếu có; loại khỏi H2H và Cup |
| 3 | Loại khỏi toàn bộ giải |

Không áp lại cùng một threshold action lần thứ hai. Ví dụ cost `20` trong một GW tạo hai violation unit nhưng chỉ tạo một ledger `-6` khi vượt ngưỡng 1, đồng thời áp dụng ngay ngưỡng 2.

### 9.4 Tác động lên H2H

Ở vòng bảng, với violation đầu tiên:

1. trận vẫn được xét thắng/hòa/thua bằng điểm net;
2. điểm trận `3/1/0` được ghi bình thường;
3. ledger penalty `-6` được trừ riêng khỏi bảng H2H.

Điểm bảng sau penalty được phép âm.

Khi HLV chạm ngưỡng 2:

- các kết quả H2H lịch sử đã final được giữ nguyên;
- các trận tương lai của HLV bị xử walkover;
- đối thủ nhận `3` điểm;
- tỷ số kỹ thuật lưu `0–0`;
- trận walkover kỹ thuật không cộng points for/against và không tạo point difference giả.

Nếu HLV vi phạm trong trận play-off, đối thủ đi tiếp bằng walkover. Nếu cả hai phía đồng thời không đủ điều kiện, trận chuyển admin review; hệ thống không tự chọn ngẫu nhiên.

### 9.5 Tác động lên Cup

- Mỗi excessive-transfer violation đã xác nhận làm contribution của **GW vi phạm** trong bảng xét Cup bằng `0`.
- Nếu violation xảy ra ở một trận loại trực tiếp, điểm trận của HLV vi phạm không hợp lệ và đối thủ đi tiếp bằng walkover.
- Khi chạm ngưỡng 2, HLV bị loại khỏi Cup. Kết quả lịch sử đã final được giữ nguyên; trận tương lai xử walkover.
- Nếu bị loại trước khi bracket được khóa, HLV không nằm trong danh sách eligible để xếp suất/draw.
- Nếu cả hai phía cùng không đủ điều kiện, trận chuyển admin review.

### 9.6 Không tham gia league mới

Không tham gia FPL league mới của Season 2 đúng hạn được tính là một violation unit trong cùng bộ đếm GW1–GW38.

- Classic và Cup từ GW20 đến trước GW HLV join đóng góp `0`.
- Điểm Classic và Cup bắt đầu tính lại từ chính GW join.
- H2H vẫn thi đấu và tính điểm bình thường.
- Sự kiện phải được admin review và ghi rõ `season_2_join_gameweek`.

Violation do join trễ không biến GW join thành một excessive-transfer violation; từ GW join, điểm được tính bình thường nếu không có vi phạm khác.

## 10. Team FPL bị khóa hoặc xóa

Từ `locked_from_gameweek` trở đi, điểm của HLV được thay bằng average của **division mà HLV thuộc ở GW đó**.

Vì vậy mỗi GW có thể có hai average độc lập:

```text
HIGH replacement average
LOW replacement average
```

Tập mẫu gồm HLV:

- thuộc cùng division tại GW;
- đang active;
- không locked, deleted hoặc removed;
- có điểm net hiệu lực không phải `replacement_average`.

Không lấy manager của division còn lại. Không đưa bất kỳ replacement score nào vào mẫu; nhiều team bị khóa trong cùng division phải dùng cùng một tập mẫu gốc, không tính vòng lặp.

```text
replacement_average_raw =
    sum(eligible_sample_net_points) / eligible_sample_count

replacement_average_rounded =
    ROUND_HALF_UP(replacement_average_raw)
```

Ví dụ:

```text
67.42 -> 67
67.50 -> 68
67.81 -> 68
```

Không dùng bankers' rounding. Nếu tập mẫu rỗng, hệ thống không lấy average của division khác; score chuyển `pending_review` để admin xử lý.

Replacement score:

- được dùng cho Classic, H2H và Cup;
- không đủ điều kiện nhận TotW hoặc giải/highlight thành tích cá nhân;
- lưu cả raw average, rounded value, sample manager IDs và snapshot revision đã dùng.

## 11. Trạng thái điểm và finalization

Một GW đi theo state machine:

```text
upcoming -> live -> provisional -> final
```

- `upcoming`: chưa có fixture liên quan bắt đầu;
- `live`: có fixture đã bắt đầu và chưa kết thúc;
- `provisional`: các fixture đã kết thúc nhưng FPL/BTC còn có thể điều chỉnh;
- `final`: BTC hoặc rule finalization đã khóa một revision.

Quy tắc:

- UI phải hiển thị rõ live/provisional, không trình bày như kết quả cuối.
- Một final snapshot là bất biến.
- Chỉ admin được reopen GW đã final.
- Reopen phải có lý do, actor, timestamp và audit log.
- Recalculation sau reopen tạo revision mới và liên kết `supersedes`; không ghi đè hoặc xóa final revision cũ.
- H2H result, Cup result, TotW, standings và next-round bracket phải tham chiếu đúng final revision đã tạo chúng.
- Late correction từ FPL không tự thay đổi kết quả đã final. Nó tạo cảnh báo diff để admin quyết định reopen.

Admin override cũng là bản ghi append-only:

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

Trang matchup H2H/Cup phải cung cấp:

- điểm live/provisional của hai bên;
- same players và differentials;
- captain differences;
- cầu thủ đã xong, đang đá, chưa đá;
- `players_remaining`;
- `effective_players_remaining`;
- bench points, chip, transfer cost;
- tie-break hiện tại và trạng thái dữ liệu.

Với một player:

```text
net_multiplier =
    effective_multiplier_manager_a
    - effective_multiplier_manager_b
```

- `0`: bị neutralize;
- dương: differential cho A;
- âm: differential cho B.

`players_remaining` đếm player duy nhất còn ít nhất một fixture chưa được giải quyết. `effective_players_remaining` cộng effective multiplier của các player đó. Trong DGW, UI nên hiển thị thêm số fixture còn lại để tránh hiểu nhầm một player còn hai trận là hai player.

## 13. Riêng tư, quyền admin và audit

### 13.1 Dữ liệu public

Public có thể xem:

- tên HLV và tên đội đăng ký;
- FPL Team ID nếu BTC lựa chọn công khai;
- division, trạng thái thi đấu không nhạy cảm;
- điểm, standings, bracket, matchup và quyết định kỷ luật đã công bố.

Public không được nhận:

- số điện thoại;
- Facebook URL hoặc contact URL riêng;
- admin note;
- dữ liệu xác thực;
- raw payload chứa dữ liệu không cần công khai.

### 13.2 Audit bắt buộc

Phải audit tối thiểu:

- thay đổi manager/division/status;
- khóa hoặc mở lịch H2H;
- draw/bracket change;
- violation review và threshold action;
- replacement calculation và manual replacement;
- score/penalty override;
- final, reopen và refinal;
- random draw;
- truy cập/xuất PII của admin.

Audit record là append-only và phải có:

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

Quyết định cuối cùng thuộc BTC, nhưng hệ thống không được biến quyết định đó thành thay đổi không truy vết.

## 14. Các bất biến bắt buộc

1. Không dùng FPL overall rank để xếp VMF.
2. Một manager chỉ có một division membership hiệu lực tại một GW.
3. Raw FPL data không bị penalty hoặc override ghi đè.
4. Violation counter không reset giữa hai Season.
5. Một threshold action chỉ được áp dụng một lần.
6. GW vi phạm Cup có contribution `0`, Classic không đổi.
7. Replacement average chỉ dùng mẫu cùng division và không chứa replacement.
8. H2H không có trận tranh hạng ba.
9. Final revision không bị sửa tại chỗ.
10. PII không xuất hiện trong public API, cache public, log hoặc export public.
