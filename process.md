# Nhật ký phát triển — Where Did My Money Go?

Trước khi làm việc, đọc file này rồi `tech.md`. Sau mỗi thay đổi đáng kể và mỗi commit, ghi kết quả thực tế; cập nhật bản tóm tắt `proccess.md`.

## Trạng thái

- 2026-09-22: workspace trống ở đầu lượt này; tài liệu lượt trước không còn trên đĩa. Đã khởi tạo Git.
- 2026-09-23: MVP cục bộ đã triển khai và commit. `frontend/` Next.js và `backend/` FastAPI chạy với SQLite cục bộ; PostgreSQL được cấu hình cho triển khai. Chưa triển khai production.
- 2026-09-23: người dùng yêu cầu push lên `minkoi007cs/app_system` và hỗ trợ Vercel. Repo đích đã có ứng dụng `Unified-App-Infra` trên `main` (`a73cde6`), không có lịch sử chung với app tài chính. Đã push app lên nhánh riêng `where-did-my-money-go` thành công, giữ nguyên `main`. Project Vercel cũ `apps-system` tự tạo Preview từ nhánh mới nhưng báo lỗi vì root hiện trỏ vào app khác; production cũ vẫn Ready. Cần project Vercel riêng và PostgreSQL riêng cho app tài chính.
- 2026-09-23: người dùng chỉ định repo `minkoi007cs/Money_Tracker` làm đích push. Repo này chỉ có `README.md` và commit khởi tạo `28c1042`; đang hợp nhất lịch sử cũ với app tài chính để push vào `main` mà không force push.
- Kiểm thử mới nhất: 10 test backend qua; build Next.js qua; migration chạy từ database trống và `alembic check` không phát hiện sai lệch. Trên trình duyệt, tài khoản demo tổng hợp đăng nhập được, import CSV 3 dòng qua preview/mapping và dashboard tăng từ 40 lên 43 giao dịch.

## Thay đổi

| Ngày | Phạm vi và file | Lý do | Kiểm thử | Giới hạn/bước tiếp theo |
| --- | --- | --- | --- | --- |
| 2026-09-22 | `tech.md`, `process.md`, `proccess.md`, `.env.example`, `.gitignore` | Tạo lại kiến trúc và quy trình trước mã ứng dụng | Đã đọc/đối chiếu file | Tiếp tục triển khai MVP |
| 2026-09-23 | `backend/app/`, `backend/alembic/`, `backend/tests/`, `backend/scripts/`, `backend/requirements.txt` | Xây auth, DB/migration, CSV preview/confirm, mapping profile, dedupe, category, analytics, recurring, insight, export/xóa và dữ liệu demo | 10 pytest qua; migration mới + `alembic check` qua | Auth production, rate limit, PostgreSQL integration test còn mở |
| 2026-09-23 | `frontend/app/`, `frontend/components/`, `frontend/lib/`, `frontend/package*.json`, `README.md` | Tạo UX từ đăng nhập đến dashboard/import/giao dịch/recurring/categories/insights/privacy, hướng dẫn chạy | `npm run build` qua; thử luồng demo trên trình duyệt; sửa CORS sau khi thử | Cần kiểm thử e2e tự động và hardening trước public deployment |
| 2026-09-23 | `backend/index.py`, `backend/app/db.py`, `.gitignore`, `README.md`, `tech.md` | Chuẩn bị hai project Vercel riêng, bắt buộc PostgreSQL ở production và ghi hướng dẫn env/migration | Import entrypoint qua; 10 pytest qua; Next.js build qua; `git diff --check` sạch | Cần PostgreSQL riêng và biến môi trường để deploy thực tế |
| 2026-09-23 | `README.md`, `tech.md`, `process.md`, `proccess.md` | Chuyển đích GitHub sang `Money_Tracker/main` theo yêu cầu mới | Đang xác nhận push | Deploy Vercel vẫn cần PostgreSQL riêng và cấu hình env |

## Commit thực tế

| Ngày | Hash | Message | Thay đổi | Kiểm thử |
| --- | --- | --- | --- | --- |
| 2026-09-23 | `b1eadbf` | `Build CSV spending dashboard MVP` | Tạo 50 file: kiến trúc/roadmap/README, backend FastAPI + migration, CSV/category/analytics/recurring/insights/privacy, frontend Next.js và fixture/test | 10 pytest qua; Next.js build qua; migration mới + `alembic check` qua; browser CSV→dashboard qua |
| 2026-09-23 | `8d49a5b` | `Prepare separate Vercel deployment for finance app` | Thêm `backend/index.py`, chặn SQLite production, hướng dẫn deploy hai project và cập nhật nhật ký | Entrypoint import qua; 10 pytest qua; Next.js build qua; `git diff --check` sạch |
| 2026-09-23 | `53ac36e` | `Record GitHub branch push and deployment status` | Ghi kết quả push nhánh riêng và Preview của project Vercel cũ | `git push` thành công; xác nhận `main` không đổi |

Nhật ký này được cập nhật **sau** commit `53ac36e`, nên bản cập nhật nhật ký hiện là thay đổi chưa commit. Hash được lấy từ `git log -1`, không dự đoán trước commit.

## Việc còn lại

- Mốc 1–7 đã chạy ở môi trường cục bộ. Mốc 8 cần bổ sung auth session bằng cookie HttpOnly hoặc tương đương, rate limit đăng nhập, CSRF, backup/retention, PostgreSQL integration test, accessibility và e2e tự động trước khi triển khai public.
- Dedupe exact theo user/ngày/số tiền/mô tả có thể coi hai khoản chi thật giống hệt trong cùng ngày là trùng; cần màn hình xử lý thủ công hoặc near-duplicate review nếu dùng với sao kê nhiều nguồn.
- Với commit tiếp theo, tiếp tục ghi hash và nội dung thực tế vào bảng Commit, đồng bộ `proccess.md` sau khi commit thành công.
