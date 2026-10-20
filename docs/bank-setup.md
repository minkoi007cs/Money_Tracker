# Kết nối Chase và PNC với Money Tracker

Tính năng đã có trong mã local, chưa được xác minh với ngân hàng thật hoặc triển khai production. Không cần cung cấp mật khẩu ngân hàng cho Money Tracker hay vào chat. Người dùng đăng nhập và cấp quyền ở giao diện ngân hàng qua Plaid Link.

## Cấu hình phía server

1. Tạo tài khoản tại [Plaid Dashboard](https://dashboard.plaid.com/), chọn sản phẩm **Transactions**. Bắt đầu bằng Sandbox với dữ liệu giả. Để đọc tài khoản Chase và PNC thật cần Production access (gói trả phí hoặc Trial phù hợp) và quyền OAuth của từng ngân hàng. Xem [OAuth requirements](https://plaid.com/docs/link/oauth/); PNC yêu cầu MSA hiện hành ngoài Trial. Quyền truy cập thực tế, tài khoản hỗ trợ và chi phí phải kiểm tra trong Dashboard của chính bạn. Với người dùng cá nhân tại Mỹ/Canada tạo team mới, ưu tiên [Trial plan](https://support.plaid.com/hc/en-us/articles/39994173227159-What-is-the-Plaid-Trial-plan): miễn phí, tối đa 10 Production Items, có OAuth Chase/PNC. Xóa Item không hoàn lại slot. Sau khi xác minh email, vào `https://dashboard.plaid.com/trial-plan`. Trial vẫn cần người dùng tự đọc/chấp nhận MSA và xác nhận các cam kết bảo mật đúng sự thật. Không nộp đơn trả phí/full Production khi chỉ cần Trial; việc nộp đơn Production có thể khiến không quay lại Trial được. Không khai có công ty hoặc chứng nhận bảo mật nếu không có.
2. Tại API server, đặt `PLAID_ENV=sandbox`, `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_REDIRECT_URI`, `BANK_TOKEN_ENCRYPTION_KEYS`. Ví dụ redirect local: `http://localhost:3000/banks/callback`. Chỉ localhost HTTP được dùng trong Sandbox. Frontend có thể gọi API qua proxy như trước; không đặt bí mật trong biến `NEXT_PUBLIC_`.
3. Tạo khóa mã hóa trên máy: `.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. Lưu kết quả trong secret manager ở `BANK_TOKEN_ENCRYPTION_KEYS`, không đưa vào Git/chat. Giữ khóa trong các lần restart/deploy. Khi xoay khóa: khóa mới đầu tiên, các khóa cũ tiếp theo, phân cách bằng dấu phẩy; giữ khóa cũ đến khi mọi credential cũ được mã hóa lại hoặc kết nối lại.
4. Đăng ký chính xác redirect URI trong Plaid Dashboard. Production phải là `https://<frontend-domain>/banks/callback`. Để OAuth trên mobile/PWA hoạt động, mở lại cùng trình duyệt đã bắt đầu Link; token phiên Link tạm giữ trong sessionStorage tối đa 30 phút. Access token ngân hàng chỉ lưu mã hóa phía server.
5. Chạy migration `005_bank_connections` trước khi bật app mới. Local: từ `apps/api`, chạy `../../.venv/bin/alembic upgrade head`. Production: dùng DSN PostgreSQL tenant hiện có trong môi trường tiến trình, không đặt DSN thật trong tài liệu hoặc lịch sử shell.
6. Deploy cả API và web mới, giữ cấu hình App System/tenant database của README. Frontend cần cho phép gọi Plaid CDN. Cấu hình thời gian chạy serverless và reverse proxy ít nhất 100 giây cho request đồng bộ; proxy web đã dùng timeout 100 giây cho bank endpoints. Giữ Preview và Production tách biệt về database, khóa và môi trường Plaid.
7. Vào Overview → **Connect bank** → Chase, chọn tài khoản → hoàn tất cấp quyền. Lặp lại cho PNC. Trong Sandbox đây là tài khoản giả; không nhập mật khẩu ngân hàng thật vào flow giả. Sau khi được cấp quyền Production, đổi `PLAID_ENV=production` và secret tương ứng, dùng database production sạch cho các kết nối thật.

## Cách dữ liệu được hiển thị

- Mỗi tài khoản hiển thị current balance, available balance khi có và thời điểm app lấy snapshot. Các số này lấy từ `/accounts/get`; có thể là dữ liệu cached của Plaid. Chưa triển khai `/accounts/balance/get` để ép lấy số dư trực tiếp tại ngân hàng. Với thẻ tín dụng, current balance được ghi là **Amount owed**, không cộng thành tiền mặt.
- Overview kiểm tra cập nhật khi mở, lấy lại focus và mỗi phút trong lúc trang đang hiển thị. Server giới hạn fetch từng ngân hàng mỗi 5 phút khi lịch sử đã tải xong, mỗi 10 giây trong lúc tải lần đầu. Chưa có webhook/cron để cập nhật khi app đóng. Plaid thường kiểm tra giao dịch ngân hàng 1–4 lần/ngày; nút Check for updates lấy dữ liệu Plaid đã có, không ép ngân hàng refresh.
- Lịch sử yêu cầu tối đa 365 ngày; dữ liệu thật trả về tùy ngân hàng/quyền tài khoản. Đợt đầu có thể cần vài phút. Cursor và giao dịch commit cùng một transaction; phân trang bị mutation sẽ bắt đầu lại từ cursor ban đầu. Lease trong database tránh nhiều worker đồng bộ cùng lúc.
- Pending được hiển thị trong giao dịch, loại khỏi thống kê. Khi posted thay thế pending, xóa pending cũ và dùng mã transaction mới. Added/modified/removed được xử lý theo mã Plaid, tránh nhân đôi khi replay.
- Thống kê: thu, chi, dòng tiền ròng, danh mục, merchant, theo ngày và so sánh tháng. Có thể lọc từng tài khoản hoặc tất cả. Chuyển khoản/thanh toán thẻ được nhận diện từ category Plaid và loại khỏi thu/chi; vẫn nên kiểm tra phân loại. Mỗi currency giữ riêng.
- Không cho nhập CSV/ghi tay vào tài khoản đã link ngân hàng để tránh đếm lịch sử hai lần. CSV cũ ở tài khoản riêng vẫn nằm trong thống kê All accounts; chọn tài khoản ngân hàng cụ thể nếu dữ liệu cũ trùng giai đoạn.
- Mỗi người dùng kết nối một Item cho mỗi ngân hàng trong từng môi trường. Chọn tất cả checking/savings/credit card cần dùng trong một flow. Không dùng Connect bank để sửa phiên cũ; dùng Reconnect khi cần đăng nhập lại.
- Disconnect thu hồi Item tại Plaid rồi xóa tài khoản/giao dịch đã sync của kết nối đó. Nút xác nhận nói rõ việc xóa. Delete data/Delete profile cũng ngắt kết nối trước. Nếu thu hồi provider thất bại thì giữ credential để thử lại; nếu nhiều bank, thao tác có thể hoàn thành một phần trước khi lỗi ở bank tiếp theo.

## Trước khi dùng dữ liệu thật

Phải kiểm tra luồng HTTPS App System → dashboard → Plaid OAuth → Chase/PNC → số dư/giao dịch, mở lại PWA, refresh session, quyền người dùng thứ hai, disconnect/revoke và backup/retention. Hiện các bài test provider dùng dữ liệu giả; không chứng minh quyền Production hoặc kết nối thật thành công. Không đưa Sandbox Items vào database dùng cho tài chính thật.

Nguồn: [Transactions integration](https://plaid.com/docs/transactions/), [Accounts and balance semantics](https://plaid.com/docs/api/accounts/), [Web Link and OAuth callback](https://plaid.com/docs/link/web/).


## Vercel frontend → API

API production giữ Vercel Authentication. Frontend production dùng `API_USE_VERCEL_OIDC=true` và `@vercel/oidc` để gửi token ngắn hạn bằng header `x-vercel-trusted-oidc-idp-token`; JWT người dùng vẫn được FastAPI xác minh riêng. Trusted Sources của API chỉ cho project frontend Money Tracker production → API production, không cấp Preview/Development quyền vào dữ liệu production. Proxy không theo redirect ngoài ý muốn. `API_BASE_URL` trỏ domain production của API sau khi deploy và kiểm tra health. Trong monorepo, API cần override install command `pip install -r requirements.txt` và build command `python -m compileall -q app index.py` để Turbo không chọn lệnh build frontend.
