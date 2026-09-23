# Where Did My Money Go? — kiến trúc và roadmap

## Quy tắc bắt buộc

Trước **mỗi** phiên làm việc phải đọc `process.md` để biết trạng thái, commit gần nhất và việc còn lại. Sau mỗi thay đổi đáng kể phải ghi vào `process.md` ngày, phạm vi, file, lý do, kiểm thử, giới hạn, bước tiếp theo. Sau mỗi commit của ứng dụng hoặc tài liệu triển khai phải ghi hash và message thực tế; đồng bộ tóm tắt ở `proccess.md`. Commit chỉ cập nhật nhật ký xem trực tiếp bằng `git log`, vì không thể ghi hash của chính commit vào nội dung commit đó. Cập nhật file này khi kiến trúc hoặc roadmap đổi. Không đánh dấu hoàn thành khi chưa kiểm thử.

## Mục tiêu và phạm vi

Dashboard riêng tư để nhập sao kê CSV, chuẩn hóa số tiền, tránh bản ghi trùng, phân loại, xem dòng tiền, so sánh theo kỳ, phát hiện khoản lặp, tìm/lọc/sửa/xóa/xuất giao dịch. Không kết nối ngân hàng, tư vấn tài chính, gắn nhãn gian lận, hoặc dùng AI tính toán. Số tiền lấy từ giao dịch và `Decimal`; ngày dự kiến và phân loại suy đoán có nhãn ước tính.

## Kiến trúc

```text
Browser → Next.js App Router / TypeScript / Tailwind
        → FastAPI REST + JWT ownership checks
        → Services: CSV, normalization, categorization, recurring, analytics
        → SQLAlchemy → PostgreSQL production / SQLite local
```

Backend là modular monolith. Route xử lý HTTP; service xử lý nghiệp vụ. Tất cả truy vấn tài chính dùng `user_id` từ token, không lấy từ body. Local auth dùng email/password và JWT để chạy độc lập; có thể chuyển sang Supabase Auth khi có credential bằng auth adapter riêng. Không triển khai fake bank integration. Frontend gọi API, không truy vấn DB trực tiếp.

Triển khai Vercel dùng hai project từ repo `minkoi007cs/Money_Tracker`, nhánh `main`: `frontend/` Next.js và `backend/` FastAPI (`index.py` entrypoint). Backend cần PostgreSQL riêng đã chạy Alembic migration, `APP_ENV=production`, `JWT_SECRET` và CORS origin chính xác. Frontend cần `NEXT_PUBLIC_API_URL` trỏ tới backend. Repo `app_system` đang chứa ứng dụng khác, không đổi cấu hình project Vercel của ứng dụng đó. Quy trình chi tiết ở `README.md` và tiến độ thực tế ở `process.md`.

### Dữ liệu

`users`: id, email, password hash, created_at. `import_batches`: id, user_id, filename, file_hash, counts, created_at. `import_profiles`: user_id + hash của headers → tên và mapping đã xác nhận. `transactions`: id, user_id, import_id, date, raw/normalized description, merchant, signed `NUMERIC(18,2)` amount, currency, category, category_source, confidence, fingerprint, transfer/refund/subscription flags, notes, created_at. `merchant_category_preferences`: user_id + merchant key → category. `recurring_overrides`: user_id + merchant key → loại user chọn. `user_settings`: currency/timezone. Khóa ngoại xóa theo chủ sở hữu; index `(user_id,date)`, `(user_id,merchant)`, `(user_id,fingerprint)`. Alembic migration quản lý schema.

### CSV → dashboard

Upload tối đa 10 MiB, chỉ CSV UTF-8/UTF-8 BOM, kiểm tra binary và số dòng. Preview phát hiện delimiter/cột, trả 10 dòng; ngày hoặc dấu tiền mơ hồ buộc người dùng xác nhận mapping. Confirm đọc từng dòng độc lập, dùng `Decimal`, signed amount dương thu/âm chi, giữ raw description. Fingerprint theo user + ngày + amount + currency + merchant/mô tả để bỏ trùng giữa import. Quy tắc category: sửa của user → preference merchant → rule merchant/keyword → Other. Sau commit DB, xóa file tạm; chỉ lưu metadata import. Dashboard tính thu, chi, net, category, merchant, timeline, so sánh tháng trên server; transfer không tính vào thu/chi.

### API `/api/v1`

`POST /auth/register`, `/auth/login`, `GET/DELETE /me`; `POST /imports/preview`, `/imports/confirm`, `GET /imports`, `DELETE /imports/{id}`, `GET/DELETE /import-profiles`; `GET/PATCH/DELETE /transactions/{id}`, `GET /transactions`; `GET /categories`; `GET /analytics/summary`, `/analytics/comparison`, `/analytics/timeline`; `GET /recurring`, `GET /subscriptions`, `PATCH /recurring/{merchant_key}`; `GET /insights`; `GET /export/transactions`; `DELETE /data`; `GET/PATCH /settings`. Lỗi có `error.code` và `error.message`, không lộ stack trace. List phân trang và lọc server-side.

### UI

Landing, login, signup; dashboard, import, transactions, recurring/subscriptions, insights, settings/privacy. Sidebar và bộ lọc kỳ, empty/loading/error states, bảng số liệu song song biểu đồ, keyboard labels và responsive. Từ ngữ trung tính; không gọi phát hiện bất thường là fraud.

### Bảo mật và vận hành

Hash mật khẩu, JWT secret ở env; production bắt buộc secret mạnh và HTTPS. CORS allowlist. CSV không được thực thi hoặc lưu lâu. Export escape ô dạng formula. Không log dữ liệu giao dịch hoặc token. Xóa import xóa giao dịch thuộc batch; xóa tất cả dữ liệu hoặc account sau xác nhận UI. Multi-currency không cộng chung. Health endpoint, migration, env example và README. Trước production cần review auth, backup retention, giới hạn upload và cross-user tests.

## Roadmap và tiêu chí nghiệm thu

**Trạng thái 2026-09-23:** mốc 0–7 có triển khai chạy được ở local và đã thử luồng CSV → dashboard trên trình duyệt. Mốc 8 mới đạt kiểm thử backend, build frontend và smoke test thủ công; các điều kiện production hardening còn ghi ở `process.md` và README.

| Mốc | Deliverable | Đạt khi |
| --- | --- | --- |
| 0. Thiết kế | Tài liệu, Git, cấu trúc | Roadmap và nhật ký rõ trạng thái thật |
| 1. Foundation | Frontend/backend, DB, auth, shell | Chạy local, migration và user isolation test |
| 2. Import | Preview, mapping, validation, normalize, dedupe | CSV signed/debit-credit chạy xuyên suốt; lỗi một dòng không hủy batch |
| 3. Transactions | List/search/filter/edit/delete/category preference | Sửa category tồn tại; không trộn dữ liệu user |
| 4. Analytics | Tổng, category/merchant, timeline, tháng trước | Phép tính Decimal khớp fixture, transfer loại trừ |
| 5. Recurring | Nhận diện chu kỳ, subscription/bill/income, override | Có confidence và ngày ước tính, user override được giữ |
| 6. Insights | Insight factual, unusual purchase | Có evidence số liệu; không phán xét |
| 7. Privacy | Export, xóa import/data/account, retention | Chỉ export/xóa dữ liệu chủ sở hữu |
| 8. Release | E2E, accessibility, security, deploy | Luồng signup→CSV→dashboard→sửa→export→xóa chạy ổn định |
| 9. Sau MVP | Supabase Auth, ML, bank connect, budget | Chỉ triển khai khi MVP đạt mốc 8 |

## Quyết định cần theo dõi

Local auth là adapter hiện tại vì không có Supabase credential. PostgreSQL là database production, SQLite là mặc định local. CSV gốc xóa ngay sau request; preview và confirm upload cùng file. Mapping được lưu theo bộ headers khi người dùng chọn. Detector recurring mặc định chỉ đề xuất income hoặc các nhóm bill/subscription, tránh gắn nhãn chi mua sắm thông thường. Các giới hạn hoặc thay đổi thiết kế phải ghi vào `process.md`.
