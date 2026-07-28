# Triển khai miễn phí: Vercel Hobby + Supabase Free

Cập nhật: 28/07/2026.

Stack production đề xuất cho 40 HLV là:

```text
Trình duyệt
  -> Vercel Project vmf-web (Next.js, root apps/web)
  -> Vercel Project vmf-api (FastAPI Function, root services/api)
  -> Supabase Free (PostgreSQL + Vault + Cron)
  -> FPL public API
```

Không cần Docker trên production. `compose.yaml` chỉ dùng để phát triển và kiểm
thử local.

## Điều kiện để giữ chi phí 0 đồng

- Dùng Vercel Hobby cho dự án cá nhân, phi thương mại và tuân thủ
  [Fair Use](https://vercel.com/docs/plans/hobby). Nếu vận hành dịch vụ thu phí
  hoặc vì lợi nhuận, cần kiểm tra lại điều khoản trước khi đưa giải lên thật.
- Repository thuộc tài khoản GitHub cá nhân. Vercel Hobby không kết nối private
  repository thuộc GitHub Organization.
- Không thêm thẻ/nâng plan trên Supabase; theo dõi Usage để luôn ở trong quota.
- Chấp nhận không có SLA, Supabase có thể pause khi ít hoạt động và log Vercel
  Hobby chỉ giữ trong thời gian ngắn.
- Tự sao lưu database ra ngoài Supabase. Free plan không bao gồm automatic
  backups có thể phục hồi từ Dashboard.

Các giới hạn có thể thay đổi; xem mục [Quota cần theo dõi](#quota-cần-theo-dõi)
và kiểm tra lại dashboard trước khi mùa giải bắt đầu.

## 1. Tạo Supabase Free project

1. Tạo một project tại [Supabase Dashboard](https://supabase.com/dashboard),
   chọn region gần người dùng và lưu database password trong password manager.
   Với người dùng chủ yếu ở Việt Nam, Singapore thường là lựa chọn gần nhất nếu
   đang được cung cấp.
2. Trong **Connect**, lấy hai connection string:
   - **Transaction pooler**, cổng `6543`: chỉ dùng cho API serverless trên
     Vercel.
   - **Session pooler**, cổng `5432`: chỉ dùng cho Alembic migration và
     `pg_dump` khi máy chạy lệnh không có IPv6.
3. Tạo hai bản của Session pooler URL:
   - URL cho SQLAlchemy/Alembic dùng scheme `postgresql+psycopg://`.
   - URL cho Supabase CLI/`pg_dump` giữ nguyên scheme chuẩn
     `postgresql://`. Các công cụ libpq không hiểu scheme
     `postgresql+psycopg://`.
   Transaction pooler URL của API cũng đổi sang `postgresql+psycopg://`.
   Giữ nguyên username, host, port và database do Dashboard cung cấp. Nếu tự
   ghép URL, database password phải được URL-encode.

Ví dụ cấu trúc, không phải credential thật:

```text
# Runtime, transaction pooler
postgresql+psycopg://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require

# Migration bằng SQLAlchemy/Alembic, session pooler
postgresql+psycopg://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require

# Backup bằng Supabase CLI/pg_dump, cùng session pooler nhưng scheme libpq
postgresql://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```

Transaction pooler dành cho workload serverless nhưng không hỗ trợ prepared
statements. API vì vậy dùng psycopg 3 với `NullPool` và
`prepare_threshold=None`. Xem [Supabase: kết nối Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)
và [SQLAlchemy trên Supabase](https://supabase.com/docs/guides/troubleshooting/using-sqlalchemy-with-supabase-FUqebT).

Trong **Database Settings -> SSL Configuration**, bật **Enforce SSL on incoming
connections**. `sslmode=require` là mức tối thiểu cho Vercel; trước ngày khai
mạc nên chuyển sang `verify-full` với CA certificate tải từ Dashboard nếu quy
trình quản lý certificate đã được kiểm thử.

## 2. Migration an toàn

Không chạy migration trong Vercel Build Command hoặc lúc FastAPI khởi động.
Hai Vercel project có thể build song song và serverless function có thể chạy
đồng thời, khiến schema bị cập nhật lặp.

### Lần đầu trên database rỗng

1. Tạo GitHub Actions secret `SUPABASE_MIGRATION_DATABASE_URL` bằng **Session
   pooler URL cổng 5432**, không phải URL runtime 6543.
2. Vào **Actions -> Apply database migrations -> Run workflow** trên nhánh
   `main`.
3. Đánh dấu đã kiểm tra backup, hoặc xác nhận đây là database mới hoàn toàn
   rỗng; nhập chính xác `MIGRATE`.
4. Ở lần đầu, nhập thêm:
   - `season_code`: `2026/27`
   - `season_name`: `VMF Fantasy League 2026/27`
   Để trống cả hai ở các lần migration sau.
5. Workflow `.github/workflows/migrate.yml` sẽ chạy `alembic upgrade head`, xác
   nhận revision hiện tại, rồi gọi bootstrap idempotent nếu có hai input mùa
   giải. Bootstrap tạo Season DRAFT, 38 Gameweek và sáu phase Classic/H2H/Cup;
   nó dừng an toàn nếu dữ liệu hiện hữu lệch luật thay vì tự ghi đè.
6. Mở **Security Advisor** và xác nhận toàn bộ bảng VMF đã bật RLS. Migration
   hardening không tạo policy cho `anon`/`authenticated` và thu hồi quyền Data
   API; frontend chỉ truy cập dữ liệu qua FastAPI. Trong **API Settings**, bỏ
   `public` khỏi exposed schemas nếu project không dùng Supabase Data API.

### Các lần nâng schema sau

1. Tạm dừng job `vmf-fpl-probe` trong Supabase Cron nếu migration ảnh hưởng ghi
   dữ liệu.
2. Tạo logical backup bằng **URL libpq `postgresql://`**, không dùng URL
   SQLAlchemy `postgresql+psycopg://`. Phương án không cần Docker là cài
   PostgreSQL client (`pg_dump`/`pg_restore`) trên máy quản trị; schema được
   dựng lại từ Alembic, dump chỉ chứa dữ liệu ứng dụng:

   ```bash
   pg_dump "$SUPABASE_BACKUP_URL" \
     --schema=public \
     --data-only \
     --exclude-table=public.alembic_version \
     --format=custom \
     --file vmf-data.dump
   pg_restore --list vmf-data.dump
   ```

   Lưu file dump cùng commit Git đang chạy và kết quả row count. Nếu chọn
   Supabase CLI thay thế thì CLI cần Docker trên **máy backup** (production vẫn
   không cần Docker), và phải tạo đủ `roles.sql`, `schema.sql`, `data.sql` bằng
   `--role-only`, mặc định, rồi `--data-only --use-copy`; lệnh mặc định một mình
   không chứa dữ liệu. Xem
   [Supabase CLI `db dump`](https://supabase.com/docs/reference/cli/supabase-db-dump).
3. Deploy code tương thích cả schema cũ và mới nếu có thể.
4. Chạy workflow migration thủ công.
5. Kiểm tra `/health/ready` và các trang chính trước khi bật lại cron.

Không lưu database URL trong repository, workflow log, ảnh chụp màn hình hay
biến `NEXT_PUBLIC_*`.

## 3. Deploy FastAPI lên Vercel

Import `dhieu0901/FPL-Tools` vào một Vercel Hobby project:

- Project Name: `vmf-api` hoặc tên còn trống tương đương.
- Root Directory: `services/api`.
- Production Branch: `main`.
- Framework: để Vercel nhận diện FastAPI từ entrypoint của project.
- Trong **Settings -> Functions -> Function Region**, chọn cùng khu vực với
  Supabase (ví dụ Singapore). Vercel mặc định chạy function tại `iad1`
  (Washington, D.C.); để mặc định trong khi database ở châu Á sẽ tăng độ trễ.
  Hobby được chọn một region, theo
  [Vercel Function regions](https://vercel.com/docs/functions/configuring-functions/region).

Thêm các biến sau cho **Production**. Preview có thể dùng một Supabase project
thứ hai; không để Preview ghi vào database production.

| Tên | Giá trị |
| --- | --- |
| `VMF_ENVIRONMENT` | `production` |
| `VMF_DATABASE_URL` | Transaction pooler URL cổng `6543` |
| `VMF_DATABASE_USE_NULL_POOL` | `true` |
| `VMF_DATABASE_DISABLE_PREPARED_STATEMENTS` | `true` |
| `VMF_ADMIN_API_KEY` | Chuỗi ngẫu nhiên riêng, tối thiểu 32 byte |
| `CRON_SECRET` | Chuỗi ngẫu nhiên khác, tối thiểu 32 byte |
| `VMF_CORS_ORIGINS` | `["https://<web-project>.vercel.app"]` |
| `VMF_FPL_BASE_URL` | `https://fantasy.premierleague.com/api` |

Không đặt `VMF_MIGRATION_DATABASE_URL` trên Vercel. Sau lần deploy đầu, kiểm tra:

```text
https://<api-project>.vercel.app/health/live
https://<api-project>.vercel.app/health/ready
https://<api-project>.vercel.app/api/fpl/status
```

`live` xác nhận function chạy; `ready` chỉ đạt `200` khi database kết nối được
và revision Alembic đúng bằng `head` của code đang deploy. `fpl/status` phải
trả trạng thái GW quan sát trực tiếp từ FPL thay vì suy đoán theo lịch H2H.
Production cố ý tắt `/docs`.

## 4. Deploy Next.js lên Vercel

Import cùng repository lần thứ hai:

- Project Name: `vmf-web` hoặc tên còn trống tương đương.
- Root Directory: `apps/web`.
- Production Branch: `main`.
- Framework Preset: Next.js.

Biến môi trường Production:

| Tên | Giá trị |
| --- | --- |
| `VMF_API_URL` | `https://<api-project>.vercel.app/api` |
| `VMF_USE_MOCK_DATA` | `false` |
| `VMF_SEASON_ID` | ID season sau khi khởi tạo dữ liệu, ví dụ `1` |
| `VMF_H2H_SCHEDULE_ID` | ID schedule H2H sau khi admin tạo, ví dụ `1` |
| `VMF_SEASON_LABEL` | `2026/27` |
| `VMF_ADMIN_API_KEY` | Cùng giá trị với API project |
| `VMF_ADMIN_ACTOR` | `vmf-web` |
| `VMF_ADMIN_UI_USER` | Username riêng cho khu vực `/admin` |
| `VMF_ADMIN_UI_PASSWORD` | Mật khẩu dài, khác mọi secret còn lại |

Các biến trên được frontend đọc ở server runtime; không đổi tên secret sang
prefix `NEXT_PUBLIC_` vì prefix đó làm giá trị xuất hiện trong browser bundle.
Sau khi biết URL web thật, cập nhật `VMF_CORS_ORIGINS` của API bằng đúng origin
đó và redeploy API. Không dùng `*` cho production CORS.

Mỗi push lên `main` sẽ tạo deployment cho cả hai project. Vercel Hobby chỉ có
một concurrent build nên hai build có thể xếp hàng; đây không phải lỗi.

## 5. Hoàn tất dữ liệu khởi tạo

Migration và bootstrap mùa không tự bịa roster. Trước khi công bố:

1. Lấy `season_id` từ log bước **Bootstrap season metadata**, đặt giá trị đó
   vào `VMF_SEASON_ID` của web.
2. Tạo đủ 40 manager bằng `POST /api/managers` với `X-Admin-Key`. Hồ sơ chỉ
   xuất hiện công khai khi `registration_status=confirmed`. Ví dụ một bản ghi:

   ```bash
   curl --fail-with-body \
     -X POST "https://<api-project>.vercel.app/api/managers" \
     -H "Content-Type: application/json" \
     -H "X-Admin-Key: <admin-key>" \
     -H "X-Admin-Actor: preseason-import" \
     -d '{
       "fpl_entry_id": 123456,
       "manager_name": "Tên HLV",
       "team_name": "Tên đội FPL",
       "division": "HIGH",
       "season_joined": "2026/27",
       "registration_status": "confirmed"
     }'
   ```

   Không commit file roster có số điện thoại/Facebook. Gửi từng record hoặc
   dùng script import cục bộ lấy secret từ environment.
3. Chỉ sau khi API công khai trả đúng 20 manager HIGH + 20 manager LOW, tạo
   lịch H2H đúng một lần:

   ```bash
   curl --fail-with-body \
     -X POST "https://<api-project>.vercel.app/api/h2h/schedule/generate" \
     -H "Content-Type: application/json" \
     -H "X-Admin-Key: <admin-key>" \
     -H "X-Admin-Actor: preseason-schedule" \
     -d '{
       "season_id": 1,
       "name": "VMF H2H Group Stage 2026/27",
       "rounds": 35,
       "start_gameweek": 1
     }'
   ```

   Thay `season_id` bằng ID thật. Endpoint chỉ lấy manager vừa **active** vừa
   **confirmed**, yêu cầu đúng 40 người, tạo 35 GW × 20 trận = 700 trận và trả
   `schedule_id`.
4. Đặt `VMF_H2H_SCHEDULE_ID` của web bằng `schedule_id`, redeploy web, rồi đối
   chiếu GW1 và GW35. Không gọi endpoint generate lần hai cho cùng mùa.

Cup chưa cần bracket trước mùa: competition/round/match chỉ được tạo sau khi có
kết quả xét suất theo các mốc luật. Pipeline persistence đầy đủ vẫn phải được
hoàn thiện trước khi dùng điểm live để vận hành thật; cron ở mục tiếp theo mới
chỉ là probe kết nối.

## 6. Bật Supabase Cron

Không dùng Vercel Cron cho tác vụ 15 phút: Hobby chỉ cho mỗi job chạy tối đa một
lần/ngày và thời điểm có thể lệch tới 59 phút. Supabase Cron dùng `pg_cron` và
gọi API bằng `pg_net`.

1. Trong Supabase, mở **Integrations -> Vault** và tạo đúng hai secret:
   - `vmf_api_base_url`: `https://<api-project>.vercel.app`, không có `/api` và
     không có dấu `/` cuối.
   - `vmf_cron_secret`: cùng giá trị với `CRON_SECRET` trên Vercel API project.
2. Mở SQL Editor, dán và chạy
   [`supabase/cron_fpl_probe.sql`](supabase/cron_fpl_probe.sql).
3. Trong **Integrations -> Cron**, xác nhận hai job active:
   - `vmf-fpl-probe`: mỗi 15 phút, theo UTC.
   - `vmf-cron-history-cleanup`: xóa lịch sử chạy cũ hơn 7 ngày.
4. Kiểm tra History của job và Runtime Logs của `vmf-api`.

Script có thể chạy lại an toàn: job cùng tên được cập nhật thay vì nhân đôi và
script dừng ngay nếu thiếu/nhân đôi Vault secret. Secret chỉ được giải mã lúc
job chạy, không nằm trong câu lệnh cron lưu công khai.

Endpoint `POST /api/cron/fpl-probe` yêu cầu
`Authorization: Bearer <CRON_SECRET>`, dùng PostgreSQL advisory lock để bỏ qua
lần gọi chồng nhau và hiện chỉ kiểm tra kết nối tới FPL
`bootstrap-static`/`fixtures`. Kết quả `persisted=false` nghĩa là chưa phải
pipeline đồng bộ/snapshot hoàn chỉnh; không được coi probe thành bằng chứng dữ
liệu giải đã được ghi.

Để dừng cron mà không ảnh hưởng job khác, chạy
[`supabase/cron_disable.sql`](supabase/cron_disable.sql). Khi đổi secret, cập
nhật cả Vercel `CRON_SECRET` và Vault `vmf_cron_secret`, redeploy API, rồi kiểm
tra một lần gọi thành công.

## 7. Kiểm tra trước khi công bố

- GitHub Actions `CI` xanh và migration workflow kết thúc ở revision `head`.
- `/health/live` và `/health/ready` trả `200`.
- `/api/fpl/status` trả GW/trạng thái/deadline hợp lý với trang FPL chính thức.
- Gọi cron không có token hoặc token sai trả `401`; token đúng trả `200`.
- Web dùng `VMF_USE_MOCK_DATA=false` và không hiển thị dữ liệu mẫu khi
  API lỗi.
- Public managers có đúng 40 hồ sơ confirmed, chia 20 HIGH + 20 LOW; hồ sơ
  pending/rejected không xuất hiện.
- H2H có đúng 700 trận vòng bảng, `VMF_SEASON_ID` và
  `VMF_H2H_SCHEDULE_ID` trỏ đúng record vừa tạo.
- Origin production của web xuất hiện chính xác trong `VMF_CORS_ORIGINS`.
- Admin endpoint từ chối request thiếu/sai `X-Admin-Key`.
- Supabase Cron có history thành công; không có request chồng nhau kéo dài.
- Vercel và Supabase Usage còn xa ngưỡng, Supabase Database Reports dưới
  `400 MB` để có vùng an toàn.
- Đã tạo `vmf-data.dump`, `pg_restore --list` đọc được và đã diễn tập restore
  vào một project tách biệt. Nếu dùng Supabase CLI thì đã tạo đủ ba file role,
  schema và data.

## Quota cần theo dõi

Theo tài liệu chính thức tại ngày cập nhật:

| Dịch vụ | Free quota/rủi ro đáng chú ý |
| --- | --- |
| Vercel Hobby | Chỉ cho mục đích cá nhân, phi thương mại; 1.000.000 function invocation, 4 CPU-hours, 360 GB-hours memory, 100 GB data transfer; runtime log khoảng 1 giờ; vượt quota có thể làm project bị pause |
| Vercel Cron Hobby | Tối thiểu một lần/ngày cho mỗi job, độ chính xác theo giờ (`±59 phút`); dự án này không dùng nó cho probe 15 phút |
| Supabase Free | Tối đa 2 active project; 500 MB database, 5 GB egress, 1 GB Storage, 500.000 Edge Function invocation, 50.000 MAU |
| Supabase pause | Project ít database activity trong khoảng 7 ngày có thể bị pause; có thể resume trong 90 ngày. Theo dõi email cảnh báo, không coi cron là bảo đảm SLA |
| Supabase backup | Không có automatic backup thuộc Free plan; phải tự xuất logical backup và lưu ngoài project |

Nguồn: [Vercel Hobby](https://vercel.com/docs/plans/hobby),
[Vercel Cron](https://vercel.com/docs/cron-jobs/usage-and-pricing),
[Supabase pricing](https://supabase.com/pricing),
[Supabase billing](https://supabase.com/docs/guides/platform/billing-on-supabase),
[Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
và [Supabase backups](https://supabase.com/docs/guides/platform/backups).

Với 40 HLV, quota request thường đủ nếu API trả dữ liệu đã tổng hợp từ database.
Không lưu toàn bộ `bootstrap-static` lặp lại mỗi 15 phút. Khi pipeline persistence
được bổ sung, cần upsert dữ liệu chuẩn hóa, nén/xóa raw payload cũ theo retention
đã thống nhất và cảnh báo từ `400 MB`.

## Rollback và khôi phục

### Code

Trong từng Vercel project, mở **Deployments**, chọn deployment production gần
nhất đã kiểm thử và Promote/Rollback. Rollback cả API và web nếu contract giữa
hai bên thay đổi. Git revert commit lỗi trên `main` để lần deploy tiếp theo không
đưa lỗi quay lại.

### Cron

Chạy `supabase/cron_disable.sql`, sau đó xác nhận không còn hai VMF job trong
`cron.job`. Không `drop extension pg_cron`, vì thao tác đó xóa mọi cron job của
project.

### Database

- Ưu tiên migration sửa tiến (`upgrade`) để giữ dữ liệu.
- Chỉ chạy `alembic downgrade -1` khi migration có downgrade đã kiểm thử và code
  đang chạy tương thích schema cũ.
- Diễn tập restore không-Docker trên project Supabase Free thứ hai: trước hết
  chạy workflow migration/Alembic đến `head`, sau đó dùng URL
  `postgresql://...` của project đích:

  ```bash
  pg_restore \
    --dbname "$RESTORE_DATABASE_URL" \
    --data-only \
    --single-transaction \
    --disable-triggers \
    vmf-data.dump
  ```

  So sánh row count ít nhất cho `managers`, `manager_gameweek_scores`,
  `h2h_matches`, `cup_matches`, `violations` giữa nguồn và bản restore; kiểm tra
  `alembic current` đạt `head` trước khi coi backup là dùng được.
- Vault secret không được giải mã/di chuyển bởi logical dump. Tạo lại
  `vmf_api_base_url`, `vmf_cron_secret`, rồi chạy lại
  `supabase/cron_fpl_probe.sql` trên project mới.
- Sau khi đổi database, redeploy API, kiểm tra readiness, dữ liệu và admin auth,
  rồi mới bật lại cron.

Gói miễn phí không có SLA hay point-in-time recovery. Backup ngoài hệ thống và
diễn tập restore là điều kiện bắt buộc trước ngày khai mạc, không phải bước tùy
chọn.
