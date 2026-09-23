# Tóm tắt quá trình thay đổi và commit

Tên file này giữ đúng cách viết trong yêu cầu. Nhật ký chuẩn và chi tiết nằm tại [process.md](./process.md); `tech.md` bắt buộc đọc và ghi vào đó. Sau mỗi commit, cập nhật cả hai file.

| Ngày | Thay đổi | Commit |
| --- | --- | --- |
| 2026-09-22 | Khởi tạo Git, tạo lại kiến trúc, roadmap và nhật ký cho app | `b1eadbf` |
| 2026-09-23 | Xây MVP Next.js + FastAPI: CSV preview/mapping/import, giao dịch, dashboard, recurring, insights, export/xóa; 10 test backend và build frontend qua | `b1eadbf` |

Commit `b1eadbf` — `Build CSV spending dashboard MVP` (50 file). Chi tiết và giới hạn ở [process.md](./process.md). Bản cập nhật nhật ký sau commit này chưa được commit để hash trong file luôn đúng.

2026-09-23: Chuẩn bị push nhánh riêng lên `minkoi007cs/app_system` vì `main` đang chứa ứng dụng khác. Thêm entrypoint FastAPI cho Vercel, kiểm tra PostgreSQL production và hướng dẫn deploy hai project; kết quả push/deploy sẽ ghi sau khi thực hiện.
