# VMF League Web

Frontend public dashboard và khu vực điều hành cho Văn Minh Fantasy League
2026/27. Ứng dụng dùng Next.js App Router, TypeScript strict và Tailwind CSS.

## Chạy local

```bash
npm install
copy .env.example .env.local
npm run dev
```

Mặc định, khi `NEXT_PUBLIC_API_URL` chưa được cấu hình hoặc API không phản hồi,
mọi route dùng dữ liệu minh hoạ typed trong `src/lib/mock-data.ts`. Badge trên
giao diện luôn cho biết đang dùng dữ liệu trực tiếp hay minh hoạ.

## Scripts

- `npm run dev`: development server
- `npm run typecheck`: kiểm tra TypeScript strict
- `npm run lint`: ESLint và Next.js Core Web Vitals
- `npm test`: unit tests
- `npm run build`: production standalone build

## API contract

Client tập trung tại `src/lib/api.ts`. Base URL lấy từ
`NEXT_PUBLIC_API_URL`; các endpoint đang sử dụng:

- `/public/dashboard`
- `/public/classic/standings`
- `/public/h2h/standings`
- `/public/h2h/fixtures`
- `/public/h2h/matches/:id`
- `/public/cups/:season`
- `/public/highlights`
- `/public/managers`
- `/admin/overview`
- `/admin/violations`

API có thể trả trực tiếp payload hoặc `{ data, updatedAt }`.

## Docker

```bash
docker build -t vmf-web .
docker run --rm -p 3000:3000 vmf-web
```

Image chạy output `standalone` với user không đặc quyền.
