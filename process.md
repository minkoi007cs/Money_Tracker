# Nhật ký phát triển — Where Did My Money Go?

Trước khi làm việc, đọc file này rồi `tech.md`. Sau mỗi thay đổi đáng kể và mỗi commit, ghi kết quả thực tế; cập nhật bản tóm tắt `proccess.md`.

## Trạng thái

- 2026-10-14: đã đăng ký child app `money-tracker` trên App System, cấp hai khóa theo phạm vi và Neon project riêng `noisy-bar-91210093`, lưu bí mật ngoài Git. Origin đã đăng ký: `http://localhost:3000` và `https://money-tracker-rho-bay.vercel.app`. Dashboard App System báo database `healthy` và `Online · 16 ms`. Đã chạy migration 001→004 trên PostgreSQL thật. Đang chuẩn bị hai project Vercel và chờ xác nhận ngay trước khi lưu khóa/DSN vào biến môi trường production.
- Kiểm thử mới nhất 2026-10-14: 14 pytest qua (gồm token đúng/sai audience và cô lập hai người dùng), Next.js build chế độ hub qua, bài thử giả lập PKCE/callback/refresh/proxy/logout qua, PostgreSQL `alembic check` không thấy sai lệch; FastAPI `/health` với database production trả 200. Smoke test PostgreSQL thật nhập CSV giả 3 dòng, thêm giao dịch thủ công, tính số dư và cô lập hai người dùng qua; toàn bộ dữ liệu thử được rollback và bảng vẫn trống. Luồng đăng nhập thật qua HTTPS chưa kiểm thử.
- 2026-09-26: đã lấy `Money_Tracker/main` tại `189f82f` vào workspace trước đó chỉ có tài liệu, triển khai PWA cài được ở iPhone/Android sau khi có HTTPS + API, bổ sung tài khoản ngân hàng/số dư, nhập giao dịch thủ công, gán CSV/giao dịch vào tài khoản, export tài khoản, cookie HttpOnly và proxy cùng domain. Chưa triển khai các thay đổi lên production.
- Kiểm thử mới nhất 2026-09-26: 13 test backend qua, migration 001→004 và `alembic check` qua trên SQLite, Next.js build/TypeScript qua bằng webpack, smoke test qua proxy cục bộ cho đăng ký/đăng nhập, cookie HttpOnly, CSRF Origin, nhập CSV, giao dịch thủ công, số dư và export; giao diện mobile 390×844 đã xem bằng Chrome.
- Vercel đã có frontend `money-tracker-rho-bay.vercel.app` ở commit `189f82f`, nhưng project chưa có biến môi trường. Đang chuẩn bị project `money-tracker-api` trỏ `apps/api`. Lượt trước auto-review từng từ chối tạo Neon database; yêu cầu mới của người dùng cho phép hoàn thiện database/auth, và project tenant riêng đã được tạo ở lượt này.

- 2026-09-22: workspace trống ở đầu lượt này; tài liệu lượt trước không còn trên đĩa. Đã khởi tạo Git.
- 2026-09-23: MVP cục bộ đã triển khai và commit. `frontend/` Next.js và `backend/` FastAPI chạy với SQLite cục bộ; PostgreSQL được cấu hình cho triển khai. Chưa triển khai production.
- 2026-09-23: người dùng yêu cầu push lên `minkoi007cs/app_system` và hỗ trợ Vercel. Repo đích đã có ứng dụng `Unified-App-Infra` trên `main` (`a73cde6`), không có lịch sử chung với app tài chính. Đã push app lên nhánh riêng `where-did-my-money-go` thành công, giữ nguyên `main`. Project Vercel cũ `apps-system` tự tạo Preview từ nhánh mới nhưng báo lỗi vì root hiện trỏ vào app khác; production cũ vẫn Ready. Cần project Vercel riêng và PostgreSQL riêng cho app tài chính.
- 2026-09-23: người dùng chỉ định repo `minkoi007cs/Money_Tracker` làm đích push. Repo này ban đầu chỉ có `README.md` và commit `28c1042`. Đã merge lịch sử app với commit khởi tạo thành `f8de7e4` rồi push lên `Money_Tracker/main` thành công, không force push.
- Kiểm thử mới nhất: 10 test backend qua; build Next.js qua; migration chạy từ database trống và `alembic check` không phát hiện sai lệch. Trên trình duyệt, tài khoản demo tổng hợp đăng nhập được, import CSV 3 dòng qua preview/mapping và dashboard tăng từ 40 lên 43 giao dịch.

## Thay đổi

| Ngày | Phạm vi và file | Lý do | Kiểm thử | Giới hạn/bước tiếp theo |
| --- | --- | --- | --- | --- |
| 2026-10-14 | App System child app và Neon tenant; `apps/api/.python-version`, `app/main.py`, `auth.py`, `db.py`, README | Cấp database thật, kiểm tra sức khỏe, bảo đảm Vercel Preview thiếu cấu hình không rơi về auth/SQLite local | PostgreSQL migration 001→004, `alembic check`, FastAPI health 200, 14 pytest, Next build | Cấu hình biến bí mật trên Vercel, push GitHub, kiểm thử đăng nhập/CSV trên HTTPS |
| 2026-10-14 | `apps/api/app/auth.py`, `main.py`, `db.py`, `alembic/env.py`, `apps/web/lib/hub.ts`, `app/auth/*`, proxy, AuthForm, settings, tests, README/tech | Nối Money Tracker với App System để dùng hosted authentication và PostgreSQL tenant riêng | 14 pytest; Next build chế độ hub; synthetic PKCE→callback→refresh→API→logout; migration SQLite + `alembic check` | Cần đăng nhập App System, đăng ký child app, cấp database/keys, migrate PostgreSQL, cấu hình Vercel và thử HTTPS bằng dữ liệu giả. |
| 2026-09-26 | `apps/web/app/manifest.ts`, `apps/web/public/`, `apps/web/components/`, `apps/web/app/api/v1/[...path]/route.ts`, `apps/api/app/`, migrations 003–004, tests, README/tech | Cài PWA trên điện thoại; nhập tay; theo dõi số dư từng bank; chuyển JWT ra cookie HttpOnly và proxy cùng domain | 13 pytest; migration 001→004 + `alembic check`; Next.js build; smoke test cục bộ và Chrome mobile | Đã commit cục bộ `f8eea58`; chưa production do cần DB PostgreSQL riêng, API deployment, env/secrets, backup/retention và kiểm thử PostgreSQL. |
| 2026-09-22 | `tech.md`, `process.md`, `proccess.md`, `.env.example`, `.gitignore` | Tạo lại kiến trúc và quy trình trước mã ứng dụng | Đã đọc/đối chiếu file | Tiếp tục triển khai MVP |
| 2026-09-23 | `backend/app/`, `backend/alembic/`, `backend/tests/`, `backend/scripts/`, `backend/requirements.txt` | Xây auth, DB/migration, CSV preview/confirm, mapping profile, dedupe, category, analytics, recurring, insight, export/xóa và dữ liệu demo | 10 pytest qua; migration mới + `alembic check` qua | Auth production, rate limit, PostgreSQL integration test còn mở |
| 2026-09-23 | `frontend/app/`, `frontend/components/`, `frontend/lib/`, `frontend/package*.json`, `README.md` | Tạo UX từ đăng nhập đến dashboard/import/giao dịch/recurring/categories/insights/privacy, hướng dẫn chạy | `npm run build` qua; thử luồng demo trên trình duyệt; sửa CORS sau khi thử | Cần kiểm thử e2e tự động và hardening trước public deployment |
| 2026-09-23 | `backend/index.py`, `backend/app/db.py`, `.gitignore`, `README.md`, `tech.md` | Chuẩn bị hai project Vercel riêng, bắt buộc PostgreSQL ở production và ghi hướng dẫn env/migration | Import entrypoint qua; 10 pytest qua; Next.js build qua; `git diff --check` sạch | Cần PostgreSQL riêng và biến môi trường để deploy thực tế |
| 2026-09-23 | `README.md`, `tech.md`, `process.md`, `proccess.md` | Chuyển đích GitHub sang `Money_Tracker/main` theo yêu cầu mới | `git push -u origin HEAD:main` thành công; remote giữ commit khởi tạo; `git diff --check` sạch | Deploy Vercel vẫn cần PostgreSQL riêng và cấu hình env |

## Commit thực tế

| Ngày | Hash | Message | Thay đổi | Kiểm thử |
| --- | --- | --- | --- | --- |
| 2026-09-23 | `b1eadbf` | `Build CSV spending dashboard MVP` | Tạo 50 file: kiến trúc/roadmap/README, backend FastAPI + migration, CSV/category/analytics/recurring/insights/privacy, frontend Next.js và fixture/test | 10 pytest qua; Next.js build qua; migration mới + `alembic check` qua; browser CSV→dashboard qua |
| 2026-09-23 | `8d49a5b` | `Prepare separate Vercel deployment for finance app` | Thêm `backend/index.py`, chặn SQLite production, hướng dẫn deploy hai project và cập nhật nhật ký | Entrypoint import qua; 10 pytest qua; Next.js build qua; `git diff --check` sạch |
| 2026-09-23 | `53ac36e` | `Record GitHub branch push and deployment status` | Ghi kết quả push nhánh riêng và Preview của project Vercel cũ | `git push` thành công; xác nhận `main` không đổi |
| 2026-09-23 | `d4fbe4a` | `Target Money_Tracker repository for deployment` | Cập nhật README, roadmap và nhật ký cho repo đích mới | `git diff --check` sạch |
| 2026-09-23 | `f8de7e4` | `Merge Money_Tracker initialization with finance app` | Hợp nhất commit README khởi tạo vào lịch sử app; giữ README đầy đủ của app | `git merge-base --is-ancestor origin/main HEAD` qua trước push; push fast-forward thành công |
| 2026-09-23 | `18cd6a7` | `Record Money_Tracker migration and push` | Đồng bộ nhật ký chuyển repo và kết quả push `Money_Tracker/main` | `git push origin HEAD:main` thành công |
| 2026-09-26 | `f8eea58` | `Build installable mobile finance tracker with bank balances` | Bổ sung PWA, nhập tiền thủ công, tài khoản ngân hàng và số dư, proxy cùng domain và cookie HttpOnly, migration/test và tài liệu | 13 pytest; migration 001→004 + `alembic check`; Next.js build; smoke test cục bộ và Chrome mobile |
| 2026-10-14 | `32e806b` | `Integrate App System authentication and tenant database configuration` | Thêm hosted PKCE, xác minh token App System trong FastAPI, cookie/refresh, cấu hình PostgreSQL tenant và tài liệu | 14 pytest; Next build chế độ hub; synthetic PKCE/callback/refresh/proxy/logout; migration SQLite + `alembic check` |
| 2026-10-14 | `27f7077` | `Preserve hub session during auth service outages` | Giữ cookie khi App System trả lỗi máy chủ hoặc dữ liệu phiên không hợp lệ tạm thời | Next build chế độ hub và synthetic auth smoke test qua |
| 2026-10-14 | `2300373` | `Prepare production Money Tracker API and document tenant database` | Chốt Python 3.12, health kiểm tra PostgreSQL, chặn fallback local trên Vercel, cập nhật trạng thái App System tenant | 14 pytest; Next build hub; PostgreSQL migration/check; health 200; Vercel thiếu cấu hình từ chối khởi động |

Hash trong bảng được lấy từ Git sau khi commit. Các commit chỉ ghi nhật ký có thể xem trong `git log` để tránh vòng lặp tự tham chiếu.

## Việc còn lại

- Mốc 1–7 đã chạy ở môi trường cục bộ. Cookie HttpOnly và kiểm tra Origin đã bổ sung; App System cung cấp rate limit đăng nhập khi chế độ hub hoạt động. Mốc 8 còn backup/retention, PostgreSQL integration test, accessibility và e2e tự động trước khi dùng sao kê thật.
- App System child app, khóa và PostgreSQL tenant riêng đã sẵn sàng. Còn cấu hình Vercel production, push GitHub và thử bằng dữ liệu giả trên HTTPS; chỉ dùng sao kê thật sau khi xác nhận luồng này và chính sách backup/retention.
- Dedupe exact theo user/ngày/số tiền/mô tả có thể coi hai khoản chi thật giống hệt trong cùng ngày là trùng; cần màn hình xử lý thủ công hoặc near-duplicate review nếu dùng với sao kê nhiều nguồn.
- Với commit tiếp theo, tiếp tục ghi hash và nội dung thực tế vào bảng Commit, đồng bộ `proccess.md` sau khi commit thành công.
