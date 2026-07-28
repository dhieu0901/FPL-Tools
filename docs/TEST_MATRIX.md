# VMF Fantasy League 2026/27 — Test Matrix

**Mã tài liệu:** `VMF-TEST-2026-27`
**Nguồn luật:** [`RULEBOOK.md`](./RULEBOOK.md)
**Kiến trúc:** [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## 1. Chiến lược kiểm thử

Các mức:

- **U — Unit:** hàm luật thuần, deterministic, không network/database thật.
- **I — Integration:** PostgreSQL, parser, transaction, ledger và API.
- **E — End-to-end:** frontend/API/worker với dữ liệu replay.
- **S — Security/operational:** quyền, tải, backup, failure mode.

Mỗi scenario final phải khẳng định cả giá trị và provenance:

```text
snapshot_id
revision
ruleset_version
input_hash
score_source
```

Không mock domain rule bằng chính hàm production khi xây expected result. Expected fixture phải khai báo độc lập.

## 2. Bộ fixture chuẩn

Tạo các dataset tái sử dụng:

| Fixture | Nội dung |
|---|---|
| `GW_NORMAL` | Một GW đủ 10 fixture, captain/vice bình thường |
| `GW_AUTOSUB` | Starter không chơi, bench thay hợp lệ theo formation |
| `GW_CHIPS` | Bench Boost, Triple Captain, Wildcard, Free Hit |
| `GW_DGW` | Một player có hai fixture, một fixture update trước |
| `GW_BGW` | Player/team không có fixture |
| `GW_POSTPONED` | Fixture hoãn rồi chuyển event |
| `GW_NEGATIVE` | Counted player và captain có điểm âm |
| `LEAGUE_40` | 20 HIGH, 20 LOW với score có tie boundary |
| `LOCKED_BOTH_DIVS` | Nhiều locked teams ở cả HIGH và LOW |
| `VIOLATION_SEASON` | Cost 8/12/20/28, exception và join trễ |
| `LATE_CORRECTION` | FPL payload đổi sau provisional/final |

## 3. Đồng bộ và provenance

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| SYNC-001 | I | Nhận lại cùng request key và payload hash | Không tạo source revision logic mới; job thành công idempotent |
| SYNC-002 | I | Cùng request key, payload khác hash | Tạo raw revision mới, giữ revision cũ |
| SYNC-003 | I | Payload không đúng schema | Raw vẫn được lưu; parser báo schema drift; không publish score sai |
| SYNC-004 | I | FPL timeout rồi hồi phục | Retry có backoff; không duplicate snapshot/violation |
| SYNC-005 | E | Live endpoint lỗi trong ba tick | Giữ snapshot cuối, hiển thị stale/last update, không điền điểm `0` |
| SYNC-006 | I | Hai worker chạy cùng một GW | Advisory lock/CAS chỉ publish một revision hợp lệ |
| SYNC-007 | I | Fetch live shared data cho 40 manager | Mỗi tick chỉ gọi shared player/fixture endpoint một lần |
| SYNC-008 | I | Deadline picks đã snapshot, live tick tiếp theo | Không refetch 40 picks nếu source không đổi |
| SYNC-009 | I | Parser version mới chạy lại raw cũ | Derived row mang parser/algorithm version mới; raw không đổi |
| SYNC-010 | S | Log request thất bại có contact payload | Phone, Facebook URL, auth header/cookie bị redact |

## 4. Điểm, picks, captain và chip

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| SCORE-001 | U | Gross 72, transfer cost 4 | Official net = 68 |
| SCORE-002 | U | Counted player điểm âm | Điểm âm được cộng đúng, không clamp về 0 |
| SCORE-003 | U | Captain base 8 | Contribution = 16 |
| SCORE-004 | U | Triple Captain base 8 | Contribution = 24 |
| SCORE-005 | U | Captain 0 phút, vice base 7 | Effective captain là vice; contribution = 14 |
| SCORE-006 | U | Captain và vice đều không có hiệu lực | Captain contribution = 0 |
| SCORE-007 | U | Starter không chơi, bench thay đúng formation | Auto-sub in/out và effective multiplier đúng |
| SCORE-008 | U | Bench có điểm, không Bench Boost | Không vào gross; được tính wasted bench points |
| SCORE-009 | U | Bench Boost active | Bench multiplier = 1; điểm vào gross; không tính wasted bench |
| SCORE-010 | U | Wildcard/Free Hit active và FPL cost = 0 | Dùng cost FPL = 0, không tự suy diễn cost |
| SCORE-011 | U | Chip claim nhưng FPL cost vẫn 12 | Net vẫn trừ 12 trừ khi có score override riêng |
| SCORE-012 | U | Captain ghi 2 bàn | Goals tie-break = 2, không nhân thành 4 |
| SCORE-013 | U | Bench không counted ghi bàn/thẻ | Goals/cards đóng góp 0 |
| SCORE-014 | U | Bench Boost player ghi 1 bàn, 1 vàng | Goals = 1, cards = 1 |
| SCORE-015 | U | Player nhận 1 vàng + 1 đỏ | Total cards = 2 |
| SCORE-016 | I | Score override active | Raw/official/derived base không đổi; effective score lấy override và có audit provenance |

## 5. DGW, BGW và fixture

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| FIX-001 | U | Player DGW có 5 và 8 điểm | Player-GW base = 13 |
| FIX-002 | U | Player DGW là captain multiplier 2 | Contribution = 26, không mất/double count fixture |
| FIX-003 | U | Player DGW ghi 1 và 2 bàn | Goals tie-break = 3 |
| FIX-004 | U | Trận một xong, trận hai chưa đá | Player vẫn remaining; fixtures remaining = 1 |
| FIX-005 | U | Captain DGW còn trận hai | Players remaining +1, effective remaining +2, không +4 |
| FIX-006 | U | Player BGW | Fixture status blank; contribution = 0 nếu không được auto-sub thay |
| FIX-007 | I | Fixture postponed chưa gán lại | Không đánh dấu finished/final do thiếu dữ liệu; status postponed |
| FIX-008 | I | Fixture chuyển từ GW25 sang GW26 | Revision mới gỡ stats khỏi aggregate GW25 và đưa đúng GW26 |
| FIX-009 | I | Live fixture revision sửa bonus | Snapshot mới phản ánh diff, không duplicate stats row grain |
| FIX-010 | E | DGW update từng fixture qua nhiều tick | Live score tăng đúng theo từng revision và final aggregate đúng |

## 6. Classic, membership và boundary

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| CLA-001 | U | 20 HIGH + 20 LOW | Rank chỉ partition theo division |
| CLA-002 | U | Hai HLV bằng điểm | Hiển thị rank dạng `1,2,2,4` |
| CLA-003 | U | FPL overall rank khác VMF score | Overall rank không ảnh hưởng VMF rank |
| CLA-004 | I | Final GW19 | Bottom 6 HIGH/Top 6 LOW được xác định; membership mới bắt đầu GW20 |
| CLA-005 | I | Truy vấn lại GW19 sau promotion | Vẫn thấy membership cũ, lịch sử không bị đổi |
| CLA-006 | U | Bắt đầu GW20 | Season 2 points = 0; full-season points giữ nguyên |
| CLA-007 | U | Tie tại top 6, khác cumulative TotW | Người nhiều TotW thắng boundary |
| CLA-008 | U | Tie điểm và TotW, khác highest GW | Người có highest eligible single-GW score thắng |
| CLA-009 | I | Tie mọi bước | Không tự random; tạo pending admin draw |
| CLA-010 | I | Hai membership overlap cùng manager/GW | Database từ chối |
| CLA-011 | U | Không tie tại boundary | Không chạy/admin draw dù các vị trí ngoài boundary đồng điểm |

## 7. TotW và highlights

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| TOTW-001 | U | Một score cao nhất | Một winner, cumulative +1 |
| TOTW-002 | U | Ba score đồng cao nhất | Cả ba nhận TotW và mỗi người +1 |
| TOTW-003 | U | Bench Boost gross 96, cost 4; đối thủ net 90 | Net 92 thắng TotW |
| TOTW-004 | U | Replacement score cao nhất | Manager replacement không nhận TotW |
| TOTW-005 | U | Manager vi phạm chuyển nhượng nhưng có net cao nhất | Vẫn xét TotW theo điểm net; Cup qualification là ledger riêng |
| TOTW-006 | I | Rerun cùng snapshot | Không cộng cumulative TotW lần hai |
| TOTW-007 | U | Bench Boost active | Counted bench không được ghi là wasted bench |
| TOTW-008 | U | Replacement score | Không nhận individual GW highlight/award |

## 8. H2H vòng bảng và play-off

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| H2H-001 | I | Generate 35 rounds cho 40 HLV | Mỗi GW có 20 trận; mỗi manager đúng một trận; không self-match |
| H2H-002 | I | Lock schedule rồi sửa trực tiếp | Bị từ chối; chỉ version/admin action mới được phép |
| H2H-003 | U | Net 68 vs 67 | Bên 68 nhận 3, bên 67 nhận 0 |
| H2H-004 | U | Net 68 vs 68 | Mỗi bên nhận 1 |
| H2H-005 | U | Kết quả nhiều trận | Played/W/D/L/PF/PA/PD/table points đúng |
| H2H-006 | U | Penalty làm table points dưới 0 | Giữ giá trị âm |
| H2H-007 | U | Tie top 8 table points, khác TotW | TotW phân định boundary; PD không đứng trước rule đã chốt |
| H2H-008 | U | Tie table points/TotW, khác highest GW1–35 | Highest GW phân định |
| H2H-009 | I | Tie hết top 8 | Pending audited admin draw, không random nền |
| H2H-010 | I | Seed top 8 | Cặp 1–8, 4–5, 2–7, 3–6 đúng |
| H2H-011 | E | GW36–38 | Tứ kết, bán kết, chung kết; không tạo third-place match |
| H2H-012 | I | Hai đội thua bán kết | Cùng trạng thái đồng hạng ba |
| H2H-013 | U | Play-off hòa | Chạy đúng Cup tie-break chain |
| H2H-014 | I | Manager bị loại trước cutoff | Không nằm trong eligible top 8; suất đi xuống manager kế tiếp theo boundary rule |

## 9. Cup qualification và bracket

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| CUPQ-001 | U | Cup 1 không vi phạm | Qualification total = sum GW1–14 effective net |
| CUPQ-002 | U | Cup 2 không vi phạm | Qualification total = sum GW20–33 effective net |
| CUPQ-003 | U | Vi phạm xác nhận GW5 | GW5 contribution = 0; các GW khác không đổi |
| CUPQ-004 | U | Vi phạm xác nhận GW25 | Cup 2 GW25 contribution = 0 |
| CUPQ-005 | U | GW vi phạm có net âm | Contribution vẫn = 0, không giữ số âm |
| CUPQ-006 | U | Approved forgotten-chip exception | GW không bị zero vì violation; official net vẫn giữ transfer cost |
| CUPQ-007 | U | Vi phạm Cup qualification | Classic score và H2H match score không tự đổi |
| CUPQ-008 | U | Season 2 join ở GW23 | GW20–22 contribution = 0; GW23 bắt đầu tính |
| CUPQ-009 | I | Mỗi division rank 1–2 | Bốn direct qualifiers |
| CUPQ-010 | I | Mỗi division rank 3–14 | Hai mươi bốn preliminary participants |
| CUPQ-011 | I | 12 preliminary winners | Tổng 16 đội vòng 16 |
| CUPQ-012 | U | Tie boundary rank 2/3 | Points → TotW → highest eligible GW → admin draw |
| CUPQ-013 | U | Tie boundary rank 14/15 | Cùng chain, chọn đúng người dự sơ loại |
| CUPQ-014 | I | Cup 1 schedule | GW15 prelim, 16 R16, 17 QF, 18 SF, 19 final + third |
| CUPQ-015 | I | Cup 2 schedule | GW34 prelim, 35 R16, 36 QF, 37 SF, 38 final + third |
| CUPQ-016 | U | Manager HIGH ở Season 1, LOW ở Season 2 | Qualification partition theo membership đúng Season |
| CUPQ-017 | I | Manager threshold 2 trước bracket lock | Không nằm trong eligible draw |

## 10. Cup/H2H knockout tie-break

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| TB-001 | U | Hòa score, TotW khác | Nhiều TotW thắng; dừng ở step 1 |
| TB-002 | U | TotW hòa, captain contribution khác | Captain cao hơn thắng; step 2 |
| TB-003 | U | Captain thường vs Triple Captain cùng base | So contribution sau multiplier |
| TB-004 | U | Captain không chơi, vice thay | Dùng effective vice contribution |
| TB-005 | U | TotW/captain hòa, goals khác | Counted goals cao hơn thắng; step 3 |
| TB-006 | U | Captain ghi bàn | Bàn không nhân multiplier |
| TB-007 | U | Goals hòa, cards khác | Ít `yellow + red` hơn thắng; step 4 |
| TB-008 | U | Các bước 1–4 hòa, Classic points khác | Classic Season points đến GW đó phân định; step 5 |
| TB-009 | I | Mọi automatic step hòa | Pending admin draw; lưu toàn bộ compared inputs |
| TB-010 | I | Admin draw | Lưu eligible list, actor, time, method, result |
| TB-011 | U | Điểm hòa; một bên replacement | Bên dùng điểm thật/valid override đi tiếp trước tie-break |
| TB-012 | I | Cả hai replacement và hòa | Pending admin decision, không random |
| TB-013 | I | Rerun tie-break | Kết quả và `step_used` deterministic, không tạo draw mới |

## 11. Vi phạm và kỷ luật

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| VIO-001 | U | Cost 0/4/8 | Detected count = 0 |
| VIO-002 | U | Cost 12/16 | Detected count = 1 |
| VIO-003 | U | Cost 20/24 | Detected count = 2 |
| VIO-004 | U | Cost 28 | Detected count = 3 |
| VIO-005 | I | Cost 20 được confirm khi counter 0 | Kích hoạt threshold 1 + 2 ngay; chỉ một ledger H2H `-6` |
| VIO-006 | I | Cost 28 được confirm khi counter 0 | Kích hoạt threshold 1 + 2 + 3 ngay |
| VIO-007 | I | Violation GW10 rồi GW22 | Counter cộng dồn, không reset ở GW20 |
| VIO-008 | I | Retry detection/decision cùng event | Không duplicate violation unit/threshold action/penalty |
| VIO-009 | I | Forgotten chip claim | Status pending_review; chưa áp irreversible penalty |
| VIO-010 | I | Admin approve exception | Confirmed count = 0; lưu actor/reason; official net không hoàn transfer cost |
| VIO-011 | I | Admin reject exception | Confirm theo formula và áp threshold idempotent |
| VIO-012 | U | Violation đầu trong H2H group | Kết quả net vẫn cho 3/1/0, sau đó ledger riêng `-6` |
| VIO-013 | I | Threshold 2 sau các trận đã final | Kết quả lịch sử giữ nguyên |
| VIO-014 | U | Trận H2H tương lai sau removal | Opponent +3; technical 0–0; PF/PA/PD không đổi |
| VIO-015 | U | Violation trong H2H play-off | Opponent đi tiếp walkover |
| VIO-016 | U | Violation trong Cup knockout | Score invalid; opponent đi tiếp walkover |
| VIO-017 | I | Threshold 2 | Removed khỏi H2H/Cup; prize eligibility = 50% |
| VIO-018 | I | Threshold 3 | Removed khỏi toàn giải |
| VIO-019 | I | Cả hai bên knockout không đủ điều kiện | Pending admin review; không tự chọn winner |
| VIO-020 | I | Join league Season 2 trễ | Thêm 1 violation unit; Classic/Cup zero trước join; H2H bình thường |
| VIO-021 | U | GW join có score hợp lệ | Tính Classic/Cup từ chính GW join; join violation không tự zero GW join |
| VIO-022 | I | Threshold action chạy lại sau refinal | Unique threshold key ngăn áp lại |

## 12. Locked/deleted replacement

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| AVG-001 | U | HIGH average 67.42 | Rounded = 67 |
| AVG-002 | U | HIGH average 67.50 | Rounded = 68 |
| AVG-003 | U | HIGH average 67.81 | Rounded = 68 |
| AVG-004 | U | Average 68.5 | Half-up = 69, không bankers' rounding |
| AVG-005 | U | HIGH avg 60, LOW avg 80 | Locked HIGH nhận 60; locked LOW nhận 80 |
| AVG-006 | U | Hai locked HIGH | Cả hai bị loại khỏi sample và nhận cùng average từ active non-replacement sample |
| AVG-007 | U | Sample chứa previous replacement row | Replacement row bị loại |
| AVG-008 | U | Manager removed/deleted/locked | Không nằm trong sample |
| AVG-009 | U | Active manager có valid override | Dùng effective non-replacement value và lưu provenance |
| AVG-010 | I | Tập mẫu rỗng | Score pending_review; không dùng division khác/không chia 0 |
| AVG-011 | I | Manager đổi HIGH→LOW tại GW20, locked GW20 | Dùng LOW membership ở GW20 |
| AVG-012 | U | Replacement score | Dùng cho Classic, H2H và Cup |
| AVG-013 | U | Replacement cao nhất GW | Không nhận TotW/highlight cá nhân |
| AVG-014 | I | Calculation record | Lưu raw average, rounded, sample IDs, division, snapshot revision |

## 13. Matchup comparison

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| MAT-001 | U | Cùng player multiplier 1 vs 1 | Net multiplier 0, neutralized |
| MAT-002 | U | Captain 2 vs normal 1 | Differential +1 cho captain side |
| MAT-003 | U | Player chỉ có ở A | Differential cho A với multiplier tương ứng |
| MAT-004 | U | Player đã xong | Nằm trong finished, không remaining |
| MAT-005 | U | Player đang đá | Nằm trong playing |
| MAT-006 | U | Hai player chưa đá, một captain | Players remaining = 2; effective remaining = 3 |
| MAT-007 | U | DGW player còn một fixture | Đếm một player remaining và hiển thị một fixture remaining |
| MAT-008 | E | Match live | Hiển thị score state, chip, transfer cost, bench, tie-break inputs cùng snapshot revision |
| MAT-009 | I | Hai API component fetch cạnh lúc publish | Response vẫn dùng cùng snapshot set, không trộn revision |

## 14. Snapshot, finalization và audit

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| FIN-001 | I | Fixture bắt đầu/kết thúc | State đi upcoming → live → provisional |
| FIN-002 | I | FPL outage khi provisional | Không tự final |
| FIN-003 | I | Admin finalize | Snapshot/score/matches/standings khóa atomically và có audit |
| FIN-004 | I | Cố update final row | Database/service từ chối |
| FIN-005 | I | FPL late correction sau final | Final không đổi; tạo source diff alert |
| FIN-006 | I | Non-admin reopen | 403, không mutation |
| FIN-007 | I | Admin reopen không reason | Validation fail |
| FIN-008 | E | Admin reopen + recalc + refinal | Revision mới supersedes cũ; revision cũ vẫn truy vết được |
| FIN-009 | I | Reopen làm đổi Cup winner đã sinh vòng sau | Cảnh báo impact; không âm thầm sửa bracket |
| FIN-010 | U | Cùng input/rules/overrides | Output hash giống nhau |
| FIN-011 | I | Audit insert thất bại trong admin command | Toàn transaction rollback |
| FIN-012 | I | Random draw/override/status change | Audit có actor/action/before/after/reason/time/request ID |
| FIN-013 | I | Final response | Có snapshot ID, revision, ruleset, calculated/finalized time |

## 15. Authentication, authorization và PII

| ID | Mức | Tình huống | Kết quả mong đợi |
|---|---|---|---|
| SEC-001 | S | Anonymous gọi public standings | 200, không phone/Facebook/admin note |
| SEC-002 | S | Anonymous gọi admin API | 401 |
| SEC-003 | S | Admin viewer gọi mutation | 403 |
| SEC-004 | S | Competition admin finalize | Được phép, audit đầy đủ |
| SEC-005 | S | Role không có quyền PII gọi contact/export | 403 |
| SEC-006 | S | Public serializer nhận ORM manager có private relation | DTO vẫn không xuất private fields |
| SEC-007 | S | Public cache/CDN | Cache entry không chứa admin/PII response |
| SEC-008 | S | Cookie mutation thiếu/sai CSRF | 403 |
| SEC-009 | S | CORS từ origin không allowlist | Bị chặn |
| SEC-010 | S | Login brute force | Rate limit/lockout hoạt động |
| SEC-011 | S | Session cookie | Có HttpOnly, Secure, SameSite |
| SEC-012 | S | Audit xem/xuất PII | Ghi actor, scope, time; log vẫn redact value nhạy cảm |
| SEC-013 | S | Backup/staging refresh | Backup mã hóa; staging không có contact production thật |
| SEC-014 | S | IDOR thử đọc admin target khác | Authorization theo resource/action, không chỉ che UI |

## 16. Acceptance E2E trước production

| ID | Kịch bản | Điều kiện đạt |
|---|---|---|
| ACC-001 | Import 40 manager bằng FPL entry ID | Unique validation, 20 HIGH/20 LOW, private contact không public |
| ACC-002 | Replay một GW bình thường | Gross/net/captain/auto-sub/standings khớp expected fixture |
| ACC-003 | Replay live DGW | Score và remaining cập nhật đúng từng fixture |
| ACC-004 | Chạy toàn Classic Season 1 giả lập | Rank division, tie boundary, top/bottom 6 và membership GW20 đúng |
| ACC-005 | Chạy H2H GW1–35 | Schedule hợp lệ, 3/1/0, penalty, top 8 đúng |
| ACC-006 | Chạy H2H GW36–38 | Bracket đúng, chỉ final ở GW38, hai semifinal losers đồng hạng ba |
| ACC-007 | Chạy Cup 1 | Qualification GW1–14, violation zero, GW15–19 bracket và tie-break đúng |
| ACC-008 | Chạy Cup 2 | Cùng cấu trúc Cup 1 trên GW20–38 |
| ACC-009 | Violation cost 20/28 | Multi-threshold deterministic, không duplicate khi retry |
| ACC-010 | Locked teams ở cả hai division | Hai average độc lập, half-up, không recursion |
| ACC-011 | Final rồi late correction | Final bất biến; reopen tạo revision/audit mới |
| ACC-012 | Public/admin security pass | PII isolation, RBAC, CSRF, log redaction đạt |
| ACC-013 | FPL API outage drill | UI giữ last snapshot/stale banner; không zero/final sai |
| ACC-014 | Backup restore drill | Khôi phục được snapshot final, raw provenance, override và audit |

## 17. Điều kiện chặn phát hành

Không phát hành production nếu còn bất kỳ lỗi nào sau:

- score, violation, Cup/H2H winner hoặc boundary sai;
- replacement average lẫn division hoặc dùng replacement làm mẫu;
- final snapshot có thể bị sửa/xóa tại chỗ;
- retry tạo penalty/threshold action trùng;
- DGW bị double count/mất điểm;
- public API/log/cache lộ phone hoặc Facebook URL;
- admin mutation không có audit hoặc không rollback khi audit fail;
- không khôi phục được database từ backup gần nhất.
