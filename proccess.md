# Đường dẫn tương thích

Nhật ký phát triển được duy trì tại [process.md](./process.md). File này giữ cách viết cũ của tên nhật ký để các tham chiếu trước đây tiếp tục hoạt động.

Bản PWA và theo dõi tài khoản ngân hàng đã được commit cục bộ tại `f8eea58` ngày 2026-09-26. Trạng thái triển khai và các bước còn lại được cập nhật trong `process.md`.

Ngày 2026-10-14, mã tích hợp App System authentication và database tenant đã qua kiểm thử cục bộ và được commit tại `32e806b`. Child app và Neon PostgreSQL tenant riêng đã được tạo, migration đã chạy; triển khai Vercel và kiểm thử HTTPS đang được thực hiện. Xem `process.md`.


Ngày 2026-10-19 đã thêm Plaid read-only vào mã local để hiển thị số dư/giao dịch Chase và PNC, kèm account filter và thống kê posted transactions. 24 pytest, Next build, migration SQLite/check và browser demo mobile qua. Chưa có credential/quyền Plaid Production được xác minh; chưa deploy hoặc kết nối ngân hàng thật. Xem `process.md` và `docs/bank-setup.md`. Các thay đổi lần này chưa commit.

Thiết lập tiếp 2026-10-19: Plaid Personal use đang chờ người dùng tạo/xác minh tài khoản và chấp nhận điều khoản; hướng đi là Trial miễn phí. 25 pytest qua, gồm chặn account injection qua CSV mapping.

Mã đã push tại `08c4a7e`, draft PR #1; Vercel Preview check qua. API project riêng đã tạo và cấu hình cơ bản. Sandbox API exchange/sync ban đầu thành công (chưa tải lịch sử); đang chờ người dùng hoàn tất Plaid Trial và MFA App System trước production.
