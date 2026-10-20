# Đường dẫn tương thích

Nhật ký đầy đủ: [process.md](./process.md).

Ngày 2026-10-20: Money Tracker đã chạy production tại https://money-tracker-rho-bay.vercel.app. Đăng nhập HTTPS thật, API có bảo vệ, PostgreSQL migration 005, nhập CSV giả, thống kê và export đã qua kiểm tra. Dữ liệu thử đã xóa chính xác; giữ profile/settings. 25 pytest, Next.js hub build/TypeScript và npm audit root/web (0 vulnerabilities) qua. Commit ghi nhận release: `7398709`; commit code/lockfile trước đó: `cbafa81`.

Có thể mở/cài PWA để thử; chưa kiểm thử cài trên điện thoại thật. Plaid Trial đang chờ review 2–3 business days, Connect bank hiện tắt. Chưa kết nối Chase/PNC thật; cần Production secret/quyền, đăng ký redirect và người dùng tự OAuth sau duyệt. Không có webhook/cron hoặc ép live balance. Xem [bank setup](./docs/bank-setup.md).

PR #1 đã merge vào main tại `8f3ec0e`; cả hai Vercel project đã nối repo. Production HTTPS đã kiểm thử trước khi merge. File khóa auth tạm đã xóa sau khi cấu hình server.
