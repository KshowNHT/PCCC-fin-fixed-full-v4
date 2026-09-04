# Báo cáo Rà soát Bảo mật (Security Audit) — PCCC Compliance AI v2

> ⚠️ **Cập nhật:** các đề cập "`docker-compose.yml`" trong tài liệu này giờ
> tương ứng với **`compose.yaml`** (file thật đang dùng qua các script
> `run-docker.bat`/`stop-docker.bat`) — xem `Bao_Cao_Fix_QA_Lan_2.md` mục 12.

**Vai trò thực hiện:** rà soát dạng "20 năm kinh nghiệm security", ưu tiên
lỗ hổng có thể khai thác thực tế trên môi trường mạng công khai, không chỉ
liệt kê lý thuyết. Mọi lỗ hổng "Nghiêm trọng/Cao" dưới đây đều đã được
**tấn công thử nghiệm thật** để xác nhận tồn tại trước khi vá, và **test lại
sau khi vá** để xác nhận đã đóng — không chỉ đọc code suy đoán.

---

## 1. Tóm tắt điều hành

| Mức độ | Số lượng | Đã vá |
|---|---|---|
| 🔴 Nghiêm trọng (Critical) | 3 | 3/3 |
| 🟠 Cao (High) | 4 | 4/4 |
| 🟡 Trung bình (Medium) | 5 | 5/5 |
| 🟢 Thấp (Low) | 2 | 2/2 |
| ⚪ Khuyến nghị (không bắt buộc vá ngay) | 9 | 0/9 — xem mục 4 |

**Tất cả lỗ hổng Nghiêm trọng/Cao/Trung bình/Thấp đã được vá và test lại
thành công trong phiên này.** Mục 4 liệt kê các cải tiến bảo mật *nên làm*
nhưng không bắt buộc trước khi go-live, kèm hướng dẫn sửa nhanh không cần
đổi kiến trúc.

---

## 2. Lỗ hổng đã phát hiện, vá và test (chi tiết kỹ thuật)

### 🔴 CRITICAL-1: Path Traversal → Arbitrary File Write (CWE-22)

**Vị trí:** `app/main.py` — `upload_documents()`, `ocr_extract_drawing()`

**Mô tả:** Tên file lưu trên đĩa được sinh bằng cách nội suy trực tiếp
`upload.filename` (client-controlled, hoàn toàn không đáng tin) vào đường
dẫn: `stored_name = f"{timestamp}_{original_name}"`. Nếu `original_name`
chứa `../`, kẻ tấn công có thể ghi file ra ngoài thư mục dự định.

**Chứng minh khai thác (đã test thật):**
```bash
curl -X POST /api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@evil.txt;filename=../../../../tmp/pwned_by_traversal.txt"
```
Trước khi vá: file sẽ được ghi ra `/tmp/pwned_by_traversal.txt` — tuỳ quyền
hệ thống của tiến trình backend, kẻ tấn công có thể ghi đè cronjob, SSH
`authorized_keys`, hoặc file cấu hình khác → dẫn tới RCE.

**Vá:** Hàm `_generate_safe_storage_path()` mới — chỉ giữ lại phần mở rộng
(đã qua whitelist), tên file sinh bằng `uuid4().hex`, hoàn toàn không phụ
thuộc input người dùng. `original_name` giờ chỉ dùng làm text hiển thị
(`doc.title`), không bao giờ chạm vào filesystem path.

**Test sau vá:** file traversal ở trên nay được lưu an toàn tại
`data/legal_db/21662bbaa40e4d71adb33b04bce1dad7.txt` — verify bằng `find`,
không có file nào bị ghi ra `/tmp`.

---

### 🔴 CRITICAL-2: Lộ dữ liệu qua Static Mount không xác thực (CWE-284)

**Vị trí:** `app/main.py` — 3 dòng `app.mount("/data/...", StaticFiles(...))`

**Mô tả:** `/data/uploads`, `/data/legal_db`, `/data/drawings` được mount
công khai, **không qua bất kỳ lớp xác thực nào** — trong khi mọi endpoint
API khác đều yêu cầu JWT. Bất kỳ ai trên Internet biết/đoán được tên file
(dạng `<timestamp>_<tên_gốc>`, có thể vét cạn theo mốc thời gian upload) đều
tải được toàn bộ tài liệu pháp lý nội bộ và **bản vẽ kiến trúc công trình
khách hàng** (chứa địa chỉ, tên chủ đầu tư, mặt bằng chi tiết — dữ liệu
nhạy cảm kinh doanh).

**Xác nhận trước khi xoá:** đã `grep` toàn bộ frontend, xác nhận
`doc.link`/`data/legal_db`/`data/drawings` **không được tham chiếu ở bất kỳ
đâu** — mọi tải file thực tế đều đi qua `/api/documents/{id}/download` (có
JWT). Static mount là bề mặt tấn công thuần tuý, không phục vụ tính năng nào.

**Vá:** Xoá thẳng 3 dòng `app.mount()`.

**Test sau vá:** `curl /data/legal_db/x.pdf` → `404` (trước đây nếu đúng
tên file sẽ trả `200` + nội dung file).

---

### 🔴 CRITICAL-3: Secret mặc định không an toàn, không cảnh báo khi deploy (CWE-798)

**Vị trí:** `app/config.py`

**Mô tả:** `JWT_SECRET` mặc định là chuỗi cố định
`"CHANGE_ME_IN_PRODUCTION_pccc_secret_key"` viết thẳng trong source code
công khai. Nếu người vận hành quên đặt biến môi trường, **bất kỳ ai đọc
được source code này** (kể cả từ chính file zip đã giao) đều tự ký được JWT
hợp lệ cho bất kỳ user nào, kể cả admin — chiếm toàn quyền hệ thống mà
không cần biết mật khẩu.

**Vá:** `assert_production_secrets_are_safe()` — chạy khi khởi động app,
nếu `NODE_ENV=production` mà `JWT_SECRET` còn là giá trị mặc định (hoặc
<32 ký tự) hoặc `PCCC_ADMIN_PASSWORD` còn là `"admin123"`/quá ngắn →
**từ chối khởi động** (`SystemExit(1)`), in rõ lý do ra stderr.

**Test sau vá (thật, không suy đoán):**
```
[SECURITY] Từ chối khởi động ở môi trường production do cấu hình không an toàn:
  - JWT_SECRET đang để giá trị mặc định hoặc quá ngắn (<32 ký tự)...
  - PCCC_ADMIN_PASSWORD đang để giá trị mặc định 'admin123'...
exit code: 1
```
Sau khi set secret hợp lệ: app khởi động bình thường, verify bằng
`curl /api/health` → `200`.

---

### 🟠 HIGH-1: Không giới hạn brute-force đăng nhập (CWE-307)

**Vị trí:** `/api/auth/login`, `/api/auth/login-json`, `/api/auth/register`,
`/api/chat`, `/api/ocr/extract-drawing`

**Mô tả:** Không có giới hạn số lần thử — kẻ tấn công dò mật khẩu bằng
brute-force/dictionary attack không bị chặn. `/api/chat` và
`/api/ocr/extract-drawing` gọi Gemini API tốn phí, không giới hạn = có thể
bị lạm dụng gây thiệt hại tài chính.

**Vá:** Tích hợp `slowapi` (Limiter theo IP):
- Login/login-json: 10 lần/phút
- Register: 5 lần/phút
- Đổi mật khẩu: 5 lần/phút
- Chat: 30 lần/phút
- OCR: 15 lần/phút
- Thêm lớp `limit_req` thứ 2 độc lập ở tầng Nginx (`nginx.conf`) — defense
  in depth, nếu 1 lớp bị bypass thì lớp còn lại vẫn chặn.

**Test sau vá:** gửi 12 request login sai liên tiếp → 10 request đầu trả
`401`, request thứ 11-12 trả `429 Too Many Requests`.

---

### 🟠 HIGH-2: Chấp nhận mọi loại file upload (CWE-434)

**Vị trí:** `upload_documents()` — nhánh `else` cũ chấp nhận bất kỳ đuôi file

**Mô tả:** Kết hợp với CRITICAL-2 (static mount công khai): kẻ tấn công có
thể upload file `.html` chứa `<script>` độc hại. Nếu một nhân viên khác mở
link tài liệu đó trên trình duyệt (cùng origin với ứng dụng), script sẽ
chạy trong ngữ cảnh ứng dụng → đánh cắp JWT token đang lưu trong
`localStorage` (stored XSS → chiếm tài khoản).

**Vá:** Whitelist nghiêm ngặt `{".txt", ".docx", ".pdf"}` — file khác bị từ
chối thẳng với `400`, không còn nhánh "chấp nhận mọi loại".

**Test sau vá:** upload `.html` → `400 Định dạng file '.html' không được hỗ trợ`.

---

### 🟠 HIGH-3: Nhân viên thường (staff) quản lý được thư viện pháp lý dùng chung (CWE-863)

**Vị trí:** `upload_documents()`, `delete_document()` — trước đây chỉ yêu
cầu `get_current_user` (bất kỳ ai đăng nhập)

**Mô tả:** Kế hoạch gốc (Ngày 2) ghi rõ đây là thao tác của **admin**
("Admin có thể upload tài liệu pháp luật lên hệ thống"), nhưng code cũ cho
phép mọi tài khoản staff upload/xoá tài liệu RAG dùng chung. Một tài khoản
staff bị chiếm (ví dụ qua phishing) có thể xoá sạch hoặc đầu độc (upload
tài liệu sai lệch) cơ sở dữ liệu pháp lý mà toàn bộ hệ thống AI dựa vào để
tư vấn — hậu quả có thể là **tư vấn PCCC sai cho khách hàng thật**.

**Vá:** Đổi `Depends(get_current_user)` → `Depends(require_admin)` cho cả
2 endpoint.

**Test sau vá:** tài khoản staff gọi upload → `403 Yêu cầu quyền quản trị viên`.

---

### 🟠 HIGH-4: Không có cách tự đổi mật khẩu (CWE-620 liên quan)

**Vị trí:** thiếu hoàn toàn endpoint đổi mật khẩu

**Mô tả:** Admin mặc định được seed với mật khẩu từ `.env`
(`PCCC_ADMIN_PASSWORD`) nhưng không có cách nào tự đổi mật khẩu sau đó —
nghĩa là không thể ép buộc xoay vòng thông tin đăng nhập định kỳ, và nếu
mật khẩu ban đầu bị lộ (ví dụ trong log CI/CD) thì không có lối thoát.

**Vá:** Thêm `PUT /api/auth/me/password` — bắt buộc xác nhận đúng mật khẩu
cũ trước khi đổi (chống kẻ tấn công cướp JWT tạm thời tự ý đổi mật khẩu để
khoá chủ tài khoản ra vĩnh viễn).

**Test sau vá:** đổi mật khẩu sai mật khẩu cũ → `400`; đúng mật khẩu cũ →
`200` + login lại bằng mật khẩu mới thành công.

---

### 🟡 MEDIUM-1: Chính sách mật khẩu yếu (CWE-521)

**Trước:** `min_length=6`, không yêu cầu độ phức tạp.
**Vá:** `MIN_PASSWORD_LENGTH=10` + bắt buộc có cả chữ và số (Pydantic
`field_validator`), áp dụng cho cả đăng ký, tạo tài khoản nhân viên, và
đổi mật khẩu.
**Test:** `"123456"` → `422 String should have at least 10 characters`;
`"aaaaaaaaaa"` → `422 Mật khẩu phải chứa cả chữ cái và chữ số`.

### 🟡 MEDIUM-2: Rò rỉ chi tiết exception nội bộ cho client (CWE-209)

**Trước:** nhiều endpoint trả `detail=f"Lỗi ...: {e}"` — có thể lộ đường
dẫn file nội bộ, tên bảng DB, hoặc chi tiết stack trace giúp kẻ tấn công
trinh sát hệ thống.
**Vá:** Tất cả exception handler giờ log đầy đủ chi tiết (`exc_info=True`)
ở server, chỉ trả thông điệp chung chung, không kỹ thuật cho client.

### 🟡 MEDIUM-3: Thiếu security headers (CWE-1021 Clickjacking và liên quan)

**Vá:** Middleware thêm `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`,
`Strict-Transport-Security`, `Content-Security-Policy` cho mọi response;
lặp lại ở tầng Nginx (defense in depth, phòng khi backend bị lộ trực tiếp).
**Test:** verify bằng `curl -D -` thấy đủ 6 header.

### 🟡 MEDIUM-4: `/api/chat` không giới hạn độ dài input (CWE-400)

**Vá:** Endpoint giờ dùng Pydantic `ChatRequest` (trước là `dict` thô),
giới hạn `messageText` tối đa 8000 ký tự.
**Test:** gửi 9000 ký tự → `422 String should have at most 8000 characters`.

### 🟡 MEDIUM-5: Không giới hạn dung lượng file upload ở tầng ứng dụng

**Vá:** `MAX_UPLOAD_SIZE_MB=25` (cấu hình được), kiểm tra sau khi đọc file
trong `_read_upload_with_size_limit()`, đồng bộ với `client_max_body_size`
đã có sẵn ở Nginx (25M, trước đó 50M — đã đồng bộ lại 2 tầng cho khớp nhau).

### 🟢 LOW-1: CORS hardcode domain demo không liên quan

**Vá:** `ALLOWED_ORIGINS` giờ đọc từ biến môi trường `PCCC_ALLOWED_ORIGINS`
(phân tách bởi dấu phẩy), mặc định chỉ còn localhost cho dev.

### 🟢 LOW-2: Container Docker chạy bằng root

**Vá:** `backend/Dockerfile` tạo user `pccc` (uid 1001) không có quyền hệ
thống, chạy ứng dụng bằng user này thay vì root — giảm thiệt hại nếu có lỗ
hổng RCE trong dependency Python nào đó trong tương lai.

---

## 3. Kết quả test tổng hợp (tất cả chạy trên PostgreSQL + uvicorn thật)

| Kịch bản test | Kết quả kỳ vọng | Kết quả thực tế |
|---|---|---|
| Fail-fast production với secret yếu | Từ chối khởi động | ✅ `exit code 1` |
| App khởi động với secret hợp lệ | Chạy bình thường | ✅ `200` |
| Security headers | Đủ 6 header | ✅ |
| Static mount `/data/*` | `404` | ✅ |
| Brute-force login 12 lần | 10x `401`, 2x `429` | ✅ |
| Path traversal filename upload | File lưu an toàn (uuid), không ghi ra ngoài | ✅ |
| Upload `.html` giả dạng tài liệu | `400` | ✅ |
| Staff upload tài liệu (giờ admin-only) | `403` | ✅ |
| Đăng ký mật khẩu `"123456"` | `422` | ✅ |
| Đăng ký mật khẩu `"aaaaaaaaaa"` | `422` | ✅ |
| Đổi mật khẩu sai mật khẩu cũ | `400` | ✅ |
| Đổi mật khẩu đúng + login lại | `200` cả 2 | ✅ |
| Chat message 9000 ký tự | `422` | ✅ |
| Chat message hợp lệ (chức năng cũ) | Hoạt động bình thường | ✅ |
| Export DOCX/PDF/JSON (chức năng cũ) | Hoạt động bình thường | ✅ |
| `nginx -t` cú pháp `nginx.conf` mới | Hợp lệ | ✅ (cài nginx thật để test, không suy đoán) |
| `docker-compose.yml` cú pháp YAML | Hợp lệ | ✅ (parse bằng PyYAML) |
| Frontend `tsc --noEmit` | 0 lỗi | ✅ |
| Frontend `npm run build` | Thành công | ✅ |

**Không có tính năng cũ nào bị hỏng sau khi vá** — mọi luồng nghiệp vụ
(session, chat, export báo cáo, RAG) đều test lại và hoạt động đúng như
trước.

---

## 4. Gợi ý sửa nhanh — KHÔNG bắt buộc trước khi go-live, không cần đổi kiến trúc

Đây là các cải tiến bảo mật hợp lý nên làm dần, xếp theo độ ưu tiên giảm
dần. Mỗi mục đều là thay đổi cục bộ, không đụng vào luồng nghiệp vụ chính.

1. **JWT lưu ở `localStorage`** — dễ bị đánh cắp nếu có XSS (dù CSP đã giảm
   rủi ro này nhiều). Sửa nhanh: không cần đổi ngay vì rủi ro đã giảm đáng
   kể sau khi vá CRITICAL-2/HIGH-2 (nguồn XSS khả dĩ nhất đã bị chặn). Nếu
   muốn chắc chắn hơn nữa: chuyển sang cookie `httpOnly + Secure +
   SameSite=Strict`, nhưng cần thêm cơ chế CSRF token — đổi kiến trúc lớn
   hơn, để dành giai đoạn sau.

2. **Alembic migrations** — hiện dùng `Base.metadata.create_all()`. Sửa
   nhanh: `pip install alembic && alembic init migrations`, generate
   revision đầu tiên từ schema hiện tại. Không đổi code nghiệp vụ.

3. **Dependency vulnerability scanning** — thêm vào CI:
   ```bash
   pip install pip-audit && pip-audit -r backend/requirements.txt
   npm audit --prefix frontend
   ```
   Chạy định kỳ (hàng tuần) hoặc mỗi lần build Docker image.

4. **2FA cho tài khoản admin** — thư viện `pyotp` (TOTP), thêm 1 cột
   `totp_secret` vào bảng `users`, 1 bước xác thực phụ ở `/api/auth/login`.
   Không bắt buộc với hệ thống nội bộ ≤10 người dùng nhưng nên có cho admin.

5. **Audit log riêng cho hành động quản trị** (khác `InspectionLog` — vốn
   chỉ log kết quả thẩm định). Ví dụ: ai xoá tài liệu nào, ai tạo/xoá tài
   khoản nào, khi nào. Thêm 1 bảng `admin_audit_log` đơn giản, ghi log ở
   các endpoint admin-only hiện có — không đổi logic hiện tại.

6. **Backup tự động PostgreSQL** — thêm `pg_dump` cron job hoặc dùng
   image `prodrigestivill/postgres-backup-local` như 1 service phụ trong
   `docker-compose.yml`. Không đụng service hiện có.

7. **RAG bằng Vector Store thật (pgvector)** — hiện vẫn keyword-matching
   (đã ghi rõ trong README trước). Không phải lỗ hổng bảo mật, nhưng liên
   quan tới chất lượng/độ tin cậy của tư vấn AI.

8. **WAF / Fail2ban ở tầng VPS** — với rate-limit đã có ở 2 tầng
   (slowapi + Nginx), đây là lớp phòng thủ thứ 3 tuỳ chọn, hữu ích nếu
   VPS bị quét cổng/tấn công diện rộng thường xuyên.

9. **SSL/TLS thật** — `nginx.conf` hiện chỉ HTTP (đúng cho môi trường
   Docker nội bộ có TLS-termination phía ngoài, hoặc dev). Khi có domain
   thật: chạy Certbot (`certbot --nginx`) hoặc thêm service Caddy đứng
   trước — không đổi cấu hình ứng dụng, chỉ thêm ở tầng hạ tầng.

---

## 5. Kết luận

Hệ thống trước phiên rà soát này có **3 lỗ hổng Nghiêm trọng** đủ để một kẻ
tấn công không cần tài khoản (CRITICAL-2), hoặc chỉ cần đọc source code
công khai (CRITICAL-3), chiếm được dữ liệu nhạy cảm hoặc toàn quyền hệ
thống. Sau khi vá và test lại toàn bộ, hệ thống đã sẵn sàng ở mức bảo mật
phù hợp để triển khai production cho một đội ngũ nội bộ ≤10 người dùng,
với điều kiện: **đặt `JWT_SECRET` và `PCCC_ADMIN_PASSWORD` mạnh trong
`.env` trước khi deploy** (backend sẽ tự từ chối khởi động nếu quên).
