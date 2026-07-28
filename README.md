# VMF Fantasy League Management Tool

Nền tảng quản lý giải Văn Minh Fantasy League 2026/27 dành cho 40 HLV.
Ứng dụng dùng dữ liệu FPL làm nguồn điểm và áp dụng bộ luật VMF cho hai
division Classic, H2H, play-off, hai Cup, vi phạm và các quyết định của BTC.

## Kiến trúc

```text
apps/web       Next.js public dashboard và admin UI
services/api   FastAPI, rule engine, đồng bộ FPL và PostgreSQL
docs           Rulebook, kiến trúc, test matrix và runbook
supabase       SQL cấu hình cron cho môi trường Supabase
```

Các nguyên tắc bắt buộc:

- Dữ liệu FPL thô, dữ liệu VMF suy ra và admin override được lưu tách biệt.
- Deadline picks và kết quả đã finalize là snapshot có version.
- Mọi quyết định kỷ luật, bốc thăm và reopen Gameweek đều có audit log.
- Không dùng overall rank của FPL.
- Điểm live luôn provisional cho tới khi Gameweek được finalize.

## Chạy local

Sao chép `.env.example` thành `.env`, thay các secret mẫu, rồi khởi tạo database:

```powershell
docker compose up -d postgres
docker compose run --rm migrate
docker compose up --build api web
```

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`

Docker chỉ phục vụ môi trường local. Production miễn phí dùng hai Vercel Project
(`apps/web` và `services/api`) cùng một Supabase Free project. Xem toàn bộ quy
trình, biến môi trường, migration, cron, quota và rollback tại
[DEPLOYMENT.md](DEPLOYMENT.md).
