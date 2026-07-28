# VMF League Web

Frontend public dashboard và khu vực điều hành cho Văn Minh Fantasy League 2026/27.
Ứng dụng dùng Next.js App Router, React Server Components và TypeScript strict.

## Chạy local

```bash
npm install
copy .env.example .env.local
npm run dev
```

Client mặc định chỉ dùng API thật. Nếu API lỗi, route hiển thị error state và tuyệt đối
không âm thầm chuyển sang dữ liệu minh họa. Muốn chạy bản demo, phải chủ động đặt:

```dotenv
VMF_USE_MOCK_DATA=true
```

Badge trên giao diện luôn phân biệt `live`, `mock`, hoặc tính năng chưa có nguồn dữ liệu.

## Biến môi trường

- `VMF_API_URL`: URL FastAPI phía server, gồm prefix `/api`, ví dụ
  `https://vmf-api.example.com/api`.
- `VMF_USE_MOCK_DATA`: chỉ nhận `true` khi muốn chạy demo rõ ràng.
- `VMF_SEASON_ID`: ID season trong database; bắt buộc ở production.
- `VMF_H2H_SCHEDULE_ID`: ID schedule H2H; bắt buộc ở production.
- `VMF_SEASON_LABEL`: nhãn mùa giải, mặc định `2026/27`.
- `VMF_ADMIN_API_KEY`: khóa gọi route admin.
- `VMF_ADMIN_ACTOR`: tên actor ghi audit log, mặc định `vmf-web`.
- `VMF_ADMIN_UI_USER` và `VMF_ADMIN_UI_PASSWORD`: HTTP Basic Auth bảo vệ toàn bộ
  `/admin`; nếu thiếu một trong hai, khu vực admin trả `503` và không để lộ dữ liệu.

`VMF_ADMIN_API_KEY` là bí mật server-side, không bao giờ đặt tên với prefix
`NEXT_PUBLIC_`. Hai biến `NEXT_PUBLIC_API_URL` và `NEXT_PUBLIC_USE_MOCK_DATA` chỉ được
giữ để tương thích cấu hình Docker hiện tại; cấu hình Vercel nên dùng biến `VMF_*`.

## Deploy Vercel miễn phí

Tạo một Vercel project với **Root Directory** là `apps/web`; Vercel tự nhận diện
Next.js nên không cần Docker hay `vercel.json`. Khai báo các biến `VMF_*` ở trên trong
Project Settings. Các trang dữ liệu được render động tại request-time, vì vậy
`next build` không gọi API production và không phụ thuộc API đang hoạt động.

## API contract

Client tại `src/lib/api.ts` gọi đúng các route FastAPI hiện có:

- `GET /managers`
- `GET /fpl/status`
- `GET /classic/standings?season_id=&division=&period=`
- `GET /h2h/standings?schedule_id=`
- `GET /h2h/fixtures?schedule_id=&gameweek=`
- `GET /cups?season_id=` rồi `GET /cups/:cup_id/bracket`
- `GET /admin/violations` với `X-Admin-Key` và `X-Admin-Actor`
- `POST /admin/violations/:id/review` từ Server Action được bảo vệ

Dashboard lấy GW/deadline chính thức từ `/fpl/status`, không suy đoán từ lịch
H2H đã tạo sẵn. Backend chưa có endpoint highlights,
telemetry worker, division average và job log nên giao diện hiển thị trạng thái
“chưa có nguồn dữ liệu”, không dựng dữ liệu giả.

## Scripts

- `npm run dev`: development server
- `npm run lint`: kiểm tra Biome
- `npm run format:check`: kiểm tra định dạng
- `npm run typecheck`: kiểm tra TypeScript strict
- `npm test`: unit tests
- `npm run build`: production build
- `npm run quality`: chạy toàn bộ kiểm tra trên

## Docker local

```bash
docker build -t vmf-web .
docker run --rm -p 3000:3000 vmf-web
```

Docker chỉ phục vụ local/self-host; deploy Vercel không cần Docker.
