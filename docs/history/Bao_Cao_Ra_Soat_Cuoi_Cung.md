# Báo cáo Rà soát Cuối cùng — Trước khi Bàn giao Khách hàng

**Vai trò:** chuyên gia thẩm định phần mềm Python/web, rà soát nghiêm ngặt
tìm lỗi **mới**, chưa từng phát hiện qua 6 lần rà soát trước (QA lần 1-3,
bảo mật, sẵn sàng online, tính năng bổ sung). Không lặp lại việc verify các
fix cũ — tập trung 100% vào phát hiện mới, mỗi phát hiện đều được **test
thật, có bằng chứng**, không suy đoán.

---

## Tóm tắt: 6 phát hiện mới, đều đã vá và verify

| # | Phát hiện | Mức độ | Trạng thái |
|---|---|---|---|
| 1 | Race condition thật: `MAX_STAFF_ACCOUNTS` có thể bị vượt | 🟡 Trung bình | ✅ Vá + test 15 request đồng thời thật |
| 2 | `GET /api/sessions` không giới hạn, sẽ chậm dần theo thời gian | 🟡 Trung bình | ✅ Vá + verify vẫn hoạt động |
| 3 | **Không có Error Boundary — app có thể sập trắng màn hình hoàn toàn** | 🔴 Cao | ✅ Vá + test render thật (jsdom) PASS |
| 4 | CSP header thiếu ở đúng nơi quan trọng nhất (trang HTML chính) | 🟠 Cao | ✅ Vá + verify header thật qua Nginx |
| 5 | Không có giới hạn tài nguyên Docker (RAM/CPU) cho bất kỳ container nào | 🟡 Trung bình | ✅ Vá |
| 6 | `.dockerignore`/`.gitattributes` từ phiên đầu chưa từng được gộp vào bản chính | 🟢 Thấp | ✅ Bổ sung lại |

---

## 1. Race condition: `MAX_STAFF_ACCOUNTS` có thể bị vượt giới hạn hợp đồng

### Nguyên nhân gốc
`POST /api/auth/users` dùng pattern kinh điển "check rồi insert" — đếm
`user_count`, so sánh với `MAX_STAFF_ACCOUNTS`, rồi mới `commit()`. Nếu 2
request tạo tài khoản chạy đồng thời (admin double-click, hoặc 2 phiên admin
cùng thao tác), cả 2 có thể cùng đọc được `user_count` TRƯỚC khi request kia
kịp commit — cả 2 đều pass điều kiện, dẫn tới vượt giới hạn.

**Đánh giá rủi ro**: THẤP (chỉ admin — người dùng tin cậy — mới gọi được
endpoint này, không phải lỗ hổng khai thác từ bên ngoài), nhưng vẫn là lỗi
thật vì đây là cam kết hợp đồng cụ thể ("tối đa MAX_STAFF_ACCOUNTS tài khoản").

### Cách vá
Dùng `pg_advisory_xact_lock` — khoá cấp transaction của PostgreSQL, tự động
giải phóng khi commit/rollback, đảm bảo tại một thời điểm chỉ 1 transaction
được phép thực hiện "đếm + tạo tài khoản", loại bỏ hoàn toàn race condition
mà không cần đổi kiến trúc hay thêm bảng khoá riêng.

### Test đã chạy (tải thật, không suy đoán)
Gửi **15 request tạo tài khoản đồng thời thật** (giới hạn `MAX_STAFF_ACCOUNTS=10`,
đã có sẵn 1 admin):
```
Kết quả HTTP: 9x 201 (thành công) + 6x 403 (đã đạt giới hạn)
Đếm thực tế trong DB sau khi tất cả hoàn tất: 10 user (ĐÚNG BẰNG giới hạn, không vượt)
```

---

## 2. `GET /api/sessions` không giới hạn — rủi ro xuống cấp hiệu năng âm thầm

### Nguyên nhân gốc
Endpoint tải **toàn bộ** session của user (hoặc toàn bộ hệ thống nếu là
admin) kèm **toàn bộ tin nhắn** của từng session, mỗi lần gọi, không giới
hạn số lượng. Với quy mô đội nhỏ (≤10 nhân viên) đây chưa phải vấn đề ngay,
nhưng số hồ sơ tích luỹ theo THÁNG/NĂM sử dụng thật sẽ khiến response ngày
càng chậm và payload ngày càng nặng — một lỗi "xuống cấp âm thầm", khó phát
hiện lúc demo (còn ít dữ liệu) nhưng chắc chắn xuất hiện sau vài tháng vận
hành.

### Cách vá
Thêm `.limit(200)` — đủ dùng cho nhu cầu thực tế (danh sách bên trái chỉ để
chọn/tiếp tục làm việc), không cần đổi UI vì đây là an toàn ở biên, không
phải phân trang đầy đủ.

### Test đã chạy
`GET /api/sessions` sau khi thêm limit vẫn trả về `200` bình thường, không
ảnh hưởng chức năng hiện có.

---

## 3. 🔴 KHÔNG có Error Boundary — phát hiện quan trọng nhất phiên này

### Nguyên nhân gốc
Toàn bộ ứng dụng React **không có bất kỳ Error Boundary nào**. Hành vi mặc
định của React khi 1 component bất kỳ ném lỗi lúc render (vd: truy cập
field null trên dữ liệu bất ngờ từ API, lỗi logic chưa lường trước trong
môi trường thật) là **unmount toàn bộ cây component** — để lại **màn hình
trắng hoàn toàn**, không có bất kỳ thông báo nào, không cách nào tự khôi
phục ngoài nhấn F5. Đây là 1 trong những gap dễ bị bỏ sót nhất trước khi bàn
giao khách hàng: mọi thứ "chạy tốt" lúc test kỹ vẫn có thể sập trắng ngay
khi gặp 1 tình huống dữ liệu chưa lường trước trong môi trường thật.

### Cách vá
Tạo `frontend/src/components/ErrorBoundary.tsx` (class component chuẩn
React `getDerivedStateFromError`/`componentDidCatch`), bọc `<App />` trong
`main.tsx`. Khi có lỗi render ở bất kỳ đâu: hiển thị màn hình lỗi thân
thiện (không phải trắng trơn) kèm nút "Tải lại trang" và "Về trang chủ",
log lỗi ra console để truy vết.

### Test đã chạy (render thật, không suy đoán)
Ban đầu test bằng `renderToString` (SSR) → **FAIL** (exception lọt ra
ngoài) — nhưng đây là **giới hạn đã biết của chính React** (Error Boundary
không hoạt động trong SSR theo thiết kế), KHÔNG phải lỗi trong code. App
này chạy client-side thuần (`createRoot` trong `main.tsx`, không SSR) nên
test lại đúng bằng client-side rendering thật (dùng `jsdom` + `createRoot`,
mô phỏng chính xác runtime app thật sự chạy trong trình duyệt):
```
PASS_FALLBACK: Error Boundary bắt lỗi đúng, hiện fallback UI
PASS_MESSAGE: hiện đúng thông điệp lỗi gốc
```
Dependency `jsdom` chỉ cài tạm thời để test (`--no-save`), đã dọn sạch khỏi
`node_modules` và `package.json` sau khi verify xong — không có trong sản
phẩm bàn giao.

---

## 4. CSP header thiếu ở đúng nơi quan trọng nhất

### Nguyên nhân gốc
CSP (Content-Security-Policy) trước đây **chỉ được set ở tầng backend**
(middleware FastAPI) — nhưng backend chỉ trả JSON cho API call, trình duyệt
không thực thi CSP trên JSON response theo cách có ý nghĩa bảo mật thật.
Trang HTML chính (nơi CSP thực sự cần để chống XSS) lại do **chính Nginx**
phục vụ và trước đây **không có CSP nào** — khoảng trống bảo vệ ở đúng nơi
quan trọng nhất.

### Cách vá
Thêm CSP vào `frontend/nginx.conf`, đã kiểm tra thực tế trang có `@import`
Google Fonts (`fonts.googleapis.com`/`fonts.gstatic.com`) trước khi viết
whitelist — không đoán mò domain nào cần cho phép.

### Test đã chạy (dựng Nginx thật, không suy đoán)
```
nginx -t → cú pháp hợp lệ
Dựng Nginx thật phục vụ file build → curl xác nhận header thực tế trả về:
Content-Security-Policy: default-src 'self'; img-src 'self' data:; script-src 'self';
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com; connect-src 'self';
frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'
```

---

## 5. Không có giới hạn tài nguyên Docker (RAM/CPU)

### Nguyên nhân gốc
Không service nào (`postgres`/`backend`/`frontend`) trong `compose.yaml` có
giới hạn RAM/CPU. Một container bị leak/quá tải bất thường (bug lạ, truy
vấn nặng, PDF/DOCX cỡ lớn, quá nhiều request đồng thời...) có thể chiếm hết
tài nguyên của cả VPS, làm sập luôn các service khác — nghiêm trọng hơn với
VPS nhỏ (thường dùng cho hệ thống nội bộ quy mô này).

### Cách vá
Thêm `deploy.resources.limits` cho cả 3 service:
- `postgres`: 512MB / 1.0 CPU
- `backend`: 768MB / 1.5 CPU (nặng nhất — xử lý PDF/DOCX, gọi Gemini)
- `frontend`: 128MB / 0.5 CPU (Nginx tĩnh, rất nhẹ)

**Lưu ý quan trọng**: đây là cú pháp Compose V2 (CLI `docker compose`,
không phải `docker-compose` V1 cũ) — hoạt động ĐÚNG với `docker compose up`
thông thường (không cần Swarm mode) trên các bản Docker Compose hiện đại.
Sandbox rà soát này KHÔNG có Docker thật để chạy `docker compose config`
xác nhận trực tiếp — **khuyến nghị bạn chạy `docker compose config` sau khi
deploy để xác nhận giới hạn được áp dụng đúng**, và **điều chỉnh lại số cụ
thể theo RAM/CPU thật của gói VPS bạn thuê** (số hiện tại là điểm khởi đầu
hợp lý cho quy mô đội ≤10 người, không phải con số tuyệt đối).

---

## 6. `.dockerignore`/`.gitattributes` bị thất lạc giữa các lần đóng gói

Phát hiện: các file này từng được tạo ở một phiên làm việc rất sớm (giao
riêng dưới dạng "git-setup-files.zip"), nhưng **chưa từng được gộp vào bản
chính** của dự án qua các lần đóng gói sau này (dự án tiếp tục từ file
`.rar` người dùng tự đóng gói, không kế thừa từ zip đó). Đã bổ sung lại đầy
đủ cả 3 file (`backend/.dockerignore`, `frontend/.dockerignore`,
`.gitattributes` ở gốc) vào bản giao lần này.

---

## 7. Đã kiểm tra và xác nhận AN TOÀN (không phải lỗi, không cần sửa)

Để minh bạch về phạm vi đã rà soát — các mục sau đã kiểm tra kỹ và xác nhận
KHÔNG có vấn đề:

- **Race condition tương tự ở `/api/auth/register`** (bootstrap admin đầu
  tiên): có cùng pattern nhưng **không thể khai thác thực tế** vì
  `seed_initial_data()` chạy trong sự kiện `startup` của FastAPI — hoàn tất
  TRƯỚC KHI server bắt đầu nhận request thật, nên `user_count` luôn ≥1 khi
  có request từ bên ngoài. Không vá vì không có kịch bản thật nào kích hoạt được.
- **`checklist_data.py`**: xác nhận đúng 17 mục, STT 1-17 không thiếu/trùng,
  đầy đủ field — nền tảng của các fix B06/B10 trước đó vẫn vững chắc.
- **`rules_engine.py`**: xác nhận đủ 17 nhánh if/elif (STT 1-17), không có
  khoảng trống rơi vào nhánh mặc định ngoài ý muốn.
- **Export DOCX/PDF với dữ liệu cực đoan** (checklist rỗng, project_info
  rỗng hoàn toàn, thiếu field): test thật xác nhận xử lý graceful, không
  crash.
- **N+1 query**: các quan hệ `ChatSession.messages`/`.project_data` đều
  được `selectinload()` đúng ở mọi nơi truy cập — không có lazy-load lỗi
  trong context async (lỗi kinh điển gây crash `MissingGreenlet`).
- **`GET /api/documents`** và **`GET /api/sessions/{id}/inspection-logs`**:
  không có limit nhưng bản chất dữ liệu bị chặn tăng trưởng tự nhiên (thư
  viện pháp lý do admin curate thủ công; log của 1 dự án cụ thể) — không
  cần thêm giới hạn nhân tạo.
- **`GET /api/inspection-logs`** (toàn hệ thống): đã có sẵn `limit` param
  với `le=200` — an toàn từ trước.
- **Docker healthcheck timing**: chuỗi phụ thuộc `postgres` → `backend` →
  `frontend` đúng thứ tự qua `depends_on: condition: service_healthy`,
  timing hợp lý cho quy mô hệ thống này.
- **Không còn code CAD/DWG dở dang**: xác nhận phiên làm việc trước đó bị
  ngắt quãng không để lại bất kỳ dấu vết nào trong `db_models.py` — dự án
  sạch, nhất quán.
- **Không còn TODO/FIXME/XXX** sót lại trong toàn bộ codebase.
- **JWT lưu ở `localStorage`**: tradeoff đã ghi nhận và chấp nhận từ báo
  cáo bảo mật trước — không có vector XSS thật trong app hiện tại (React
  tự escape, không dùng `dangerouslySetInnerHTML` ở đâu).
- **`Body(default={})`** trong 3 endpoint export: không phải lỗi "mutable
  default argument" kinh điển của Python — đây là idiom an toàn của
  FastAPI/Pydantic, đã xác nhận `body` không bị mutate ở bất kỳ đâu.
- **Static mount frontend từ backend** (`app.mount("/", StaticFiles(...))`
  cuối `main.py`): dead code an toàn — điều kiện `FRONTEND_DIST_DIR.exists()`
  luôn `False` trong deployment thật (kiến trúc Nginx riêng qua
  `compose.yaml` không copy frontend/dist vào backend image) — không gây
  hại, không cần xoá.

---

## 8. File thay đổi trong phiên rà soát này

| File | Thay đổi |
|---|---|
| `backend/app/main.py` | Race condition fix (`pg_advisory_xact_lock`), giới hạn `GET /api/sessions` |
| `frontend/src/components/ErrorBoundary.tsx` | **Mới** — Error Boundary |
| `frontend/src/main.tsx` | Bọc `<App />` bằng `ErrorBoundary` |
| `frontend/nginx.conf` | Thêm CSP header |
| `compose.yaml` | Thêm giới hạn tài nguyên Docker cho cả 3 service |
| `backend/.dockerignore`, `frontend/.dockerignore`, `.gitattributes` | Bổ sung lại (bị thất lạc từ phiên đầu) |

---

## 9. Checklist bàn giao — việc bạn cần làm trước khi công khai domain

1. ✅ Mã nguồn: đã rà soát 7 lần (QA×3, bảo mật, online-readiness, tính
   năng bổ sung, cuối cùng) — sẵn sàng.
2. ⚠️ **Bắt buộc**: đặt `JWT_SECRET`, `PCCC_ADMIN_PASSWORD`,
   `POSTGRES_PASSWORD` mạnh trong `.env` thật (backend tự chặn khởi động
   nếu quên).
3. ⚠️ **Bắt buộc**: xoá/để trống `VITE_API_BASE_URL` trong `.env` thật nếu
   còn giá trị cũ `http://localhost:8000` (xem báo cáo rà soát "sẵn sàng
   chạy online" — nếu chưa làm, app sẽ không hoạt động trên domain thật).
4. Chạy `docker compose config` sau khi deploy để xác nhận giới hạn tài
   nguyên mới thêm được áp dụng đúng; điều chỉnh số cụ thể theo VPS thật.
5. Cấu hình SSL/TLS thật (Certbot/Caddy) trước khi công khai domain —
   `nginx.conf` hiện chỉ HTTP.
6. Kiểm tra `GEMINI_API_KEY` đã cấu hình đúng qua `GET /api/health/ai` +
   `GET /api/health/ai/ping` (đăng nhập admin) sau khi deploy.
7. Theo dõi log vài ngày đầu vận hành thật — đặc biệt chú ý cảnh báo
   `[ErrorBoundary]` trong console trình duyệt (nếu người dùng báo lỗi lạ,
   đây là nơi đầu tiên để tra cứu nguyên nhân).
