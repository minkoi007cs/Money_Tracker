# Tóm tắt quá trình thay đổi và commit

Tên file này giữ đúng cách viết trong yêu cầu. Nhật ký chuẩn và chi tiết nằm tại [process.md](./process.md); `tech.md` bắt buộc đọc và ghi vào đó. Sau mỗi commit, cập nhật cả hai file.

| Ngày | Thay đổi | Commit |
| --- | --- | --- |
| 2026-09-22 | Khởi tạo Git, tạo lại kiến trúc, roadmap và nhật ký cho app | `b1eadbf` |
| 2026-09-23 | Xây MVP Next.js + FastAPI: CSV preview/mapping/import, giao dịch, dashboard, recurring, insights, export/xóa; 10 test backend và build frontend qua | `b1eadbf` |
| 2026-09-23 | Chuẩn bị Vercel hai project, chặn SQLite production; push nhánh `where-did-my-money-go` lên `minkoi007cs/app_system` | `8d49a5b` |
| 2026-09-23 | Ghi lại push GitHub và trạng thái Preview Vercel cũ | `53ac36e` |

Commit `b1eadbf` — `Build CSV spending dashboard MVP` (50 file). Chi tiết và giới hạn ở [process.md](./process.md). Bản cập nhật nhật ký sau commit này chưa được commit để hash trong file luôn đúng.

2026-09-23: Push nhánh riêng đã thành công; `main` của `app_system` không đổi. Preview của project Vercel cũ báo lỗi do root ứng dụng khác; cần project riêng và PostgreSQL riêng để deploy app tài chính. Chi tiết ở [process.md](./process.md).

2026-09-23: Người dùng chọn repo `minkoi007cs/Money_Tracker`; chuẩn bị hợp nhất commit khởi tạo vào lịch sử app rồi push lên `main` không force.

| Ngày | Thay đổi | Commit |
| --- | --- | --- |
| 2026-09-23 | Cập nhật tài liệu theo repo Money_Tracker | `d4fbe4a` |
| 2026-09-23 | Hợp nhất lịch sử repo Money_Tracker; push app lên `main` thành công, không force | `f8de7e4` |
| 2026-09-23 | Đồng bộ nhật ký và push lên Money_Tracker/main | `18cd6a7` |
