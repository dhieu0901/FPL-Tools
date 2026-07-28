# Security policy

## Reporting

Không đăng công khai dữ liệu cá nhân, thông tin đăng nhập, FPL session,
database dump hoặc chi tiết lỗ hổng. Báo trực tiếp cho quản trị viên VMF.

## Production requirements

- Thay toàn bộ secret và mật khẩu mẫu trước khi deploy.
- Admin bắt buộc dùng mật khẩu mạnh; hỗ trợ 2FA sẽ được ưu tiên sau MVP.
- Số điện thoại và Facebook URL chỉ xuất hiện trong admin API có xác thực.
- Không ghi access token, session cookie hay raw PII vào application log.
- Backup PostgreSQL phải được mã hóa và kiểm tra khả năng restore.
- Mọi score override, disciplinary action và Gameweek reopen phải có audit log.
