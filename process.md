# Nhật ký phát triển — Where Did My Money Go?

Trước khi làm việc, đọc file này rồi `tech.md`. Sau mỗi thay đổi đáng kể và mỗi commit, ghi kết quả thực tế; cập nhật bản tóm tắt `proccess.md`.

## Trạng thái

- 2026-09-22: workspace trống ở đầu lượt này; tài liệu lượt trước không còn trên đĩa. Đã khởi tạo Git.
- 2026-09-23: MVP cục bộ đã triển khai. `frontend/` Next.js và `backend/` FastAPI chạy với SQLite cục bộ; PostgreSQL được cấu hình cho triển khai. Chưa triển khai production.
- Kiểm thử mới nhất: 10 test backend qua; build Next.js qua; migration chạy từ database trống và `alembic check` không phát hiện sai lệch. Trên trình duyệt, tài khoản demo tổng hợp đăng nhập được, import CSV 3 dòng qua preview/mapping và dashboard tăng từ 40 lên 43 giao dịch.

## Thay đổi

| Ngày | Phạm vi và file | Lý do | Kiểm thử | Giới hạn/bước tiếp theo |
| --- | --- | --- | --- | --- |
| 2026-09-22 | `tech.md`, `process.md`, `proccess.md`, `.env.example`, `.gitignore` | Tạo lại kiến trúc và quy trình trước mã ứng dụng | Đã đọc/đối chiếu file | Tiếp tục triển khai MVP |
| 2026-09-23 | `backend/app/`, `backend/alembic/`, `backend/tests/`, `backend/scripts/`, `backend/requirements.txt` | Xây auth, DB/migration, CSV preview/confirm, mapping profile, dedupe, category, analytics, recurring, insight, export/xóa và dữ liệu demo | 10 pytest qua; migration mới + `alembic check` qua | Auth production, rate limit, PostgreSQL integration test còn mở |
| 2026-09-23 | `frontend/app/`, `frontend/components/`, `frontend/lib/`, `frontend/package*.json`, `README.md` | Tạo UX từ đăng nhập đến dashboard/import/giao dịch/recurring/categories/insights/privacy, hướng dẫn chạy | `npm run build` qua; thử luồng demo trên trình duyệt; sửa CORS sau khi thử | Cần kiểm thử e2e tự động và hardening trước public deployment |

## Commit thực tế

| Ngày | Hash | Message | Thay đổi | Kiểm thử |
| --- | --- | --- | --- | --- |
| — | — | Chưa có commit | — | — |

## Việc còn lại

- Mốc 1–7 đã chạy ở môi trường cục bộ. Mốc 8 cần bổ sung auth session bằng cookie HttpOnly hoặc tương đương, rate limit đăng nhập, CSRF, backup/retention, PostgreSQL integration test, accessibility và e2e tự động trước khi triển khai public.
- Dedupe exact theo user/ngày/số tiền/mô tả có thể coi hai khoản chi thật giống hệt trong cùng ngày là trùng; cần màn hình xử lý thủ công hoặc near-duplicate review nếu dùng với sao kê nhiều nguồn.
- Khi commit, ghi hash và nội dung thực tế vào bảng Commit và đồng bộ `proccess.md`.
