# PCCC Compliance AI v2 — Đầy đủ theo Kế hoạch 33 ngày (Self-hosted)

> ⚠️ **Cập nhật quan trọng:** file Docker Compose thật đang được dùng là
> **`compose.yaml`** ở thư mục gốc (chạy qua `run-docker.bat`/
> `stop-docker.bat`/`logs-docker.bat`) — KHÔNG PHẢI `docker-compose.yml`
> được nhắc tới trong tài liệu bên dưới (file đó đã lỗi thời, gây lệch cấu
> hình bảo mật, và đã bị xoá). Xem `Bao_Cao_Fix_QA_Lan_2.md` mục 12 để biết
> chi tiết. Toàn bộ nội dung README này giữ nguyên cho mục đích tham khảo
> kiến trúc/gap-analysis, nhưng khi làm theo hướng dẫn Docker, luôn dùng
> `compose.yaml`.

Bản dựng lại toàn diện sau khi đối chiếu 2 file kế hoạch
(`Ke_hoach_Models_Chatbot_PCCC.md`, `_ChiTiet.md`) với thiết kế migration
Python trước đó. Mục tiêu: đáp ứng **đầy đủ** các "Model" và tính năng cam
kết trong hợp đồng, không chỉ port 1:1 code Node.js cũ.

## 1. Gap Analysis — Trước khi sửa

| # | Yêu cầu kế hoạch | Trạng thái trước | Trạng thái sau (bản này) |
|---|---|---|---|
| 1 | PostgreSQL + FastAPI (Ngày 1) | ❌ JSON file | ✅ PostgreSQL thật qua SQLAlchemy async, đã cài đặt + test bằng psql thật |
| 2 | User Model + JWT Auth (Ngày 1) | ❌ `admin/admin` hardcode phía client | ✅ Bcrypt hash + JWT, bootstrap admin đầu tiên, giới hạn `MAX_STAFF_ACCOUNTS` |
| 3 | Document Model (Ngày 2) | ⚠️ JSON file | ✅ Bảng `documents` PostgreSQL, dùng chung toàn tổ chức |
| 4 | ChatSession & ChatMessage Model (Ngày 3) | ⚠️ JSON lồng nhau | ✅ 2 bảng quan hệ riêng, cascade delete |
| 5 | RAG Legal QA (Ngày 5-8) | ✅ Có (keyword-based) | ✅ Giữ nguyên, đã verify logic không đổi |
| 6 | ProjectData Model (Ngày 9-10) | ❌ Không có, chỉ nhúng trong session | ✅ Bảng `project_data` riêng, quan hệ 1-1 với session |
| 7 | InspectionLog / Nhật ký kiểm tra (Ngày 9-11) | ❌ Không có | ✅ Bảng `inspection_logs`, tự ghi mỗi lần chạy thẩm định (chat/manual/OCR), có UI xem |
| 8 | Vision/OCR đọc bản vẽ (Ngày 12-17) | ❌ Không có | ✅ `ocr_vision.py` — PDF/PNG → Gemini Vision → tự điền form (xem ghi chú §4) |
| 9 | Rules Engine / Decision Tree (Ngày 18-21) | ⚠️ Có nhưng lẫn trong `appraisal.py` | ✅ Tách riêng `rules_engine.py`, giữ nguyên 100% logic đã test |
| 10 | Xuất báo cáo PDF/Word/JSON (Ngày 22-25) | ⚠️ Thiếu JSON | ✅ Thêm `/api/report/export-json` |
| 11 | Docker Compose Postgres+Backend (Ngày 29) | ❌ Chỉ có backend | ✅ 3 service: postgres, backend, frontend |
| 12 | Dockerfile Frontend Nginx (Ngày 29) | ❌ Không có | ✅ Multi-stage build + Nginx |
| 13 | Reverse Proxy Nginx (Ngày 30) | ❌ Không có | ✅ `nginx.conf` proxy `/api`, `/data` sang backend + SPA fallback |

## 2. Kiến trúc

```
final_v2/
├── docker-compose.yml       # postgres + backend + frontend, 1 lệnh chạy toàn bộ
├── .env.example             # biến môi trường bắt buộc (JWT_SECRET, mật khẩu...)
├── backend/                 # FastAPI + PostgreSQL + JWT + OCR + Rules Engine
│   ├── app/
│   │   ├── main.py            # toàn bộ route, đã bảo vệ bằng JWT
│   │   ├── db.py, db_models.py # SQLAlchemy async: User/Document/ChatSession/
│   │   │                        # ChatMessage/ProjectData/InspectionLog
│   │   ├── auth.py, schemas_auth.py  # bcrypt + JWT + dependency get_current_user
│   │   ├── rules_engine.py    # Decision Tree 17 mục checklist (đổi tên từ appraisal.py)
│   │   ├── ocr_vision.py      # Vision/OCR đọc bản vẽ (MỚI)
│   │   ├── gemini_client.py   # gọi Gemini, retry/failover
│   │   ├── docx_report.py, pdf_report.py  # xuất báo cáo
│   │   ├── seed.py            # khởi tạo admin mặc định + 18 tài liệu pháp lý
│   │   └── ...
│   ├── requirements.txt
│   ├── Dockerfile             # + poppler-utils cho OCR
│   └── .env.example
└── frontend/                 # React — UI mới: đăng nhập thật, OCR upload, nhật ký kiểm tra
    ├── src/
    │   ├── lib/api.ts           # MỚI — JWT client, thay hoàn toàn fetch() trần
    │   ├── components/Login.tsx        # Viết lại — gọi API thật
    │   ├── components/BlueprintUpload.tsx   # MỚI — OCR upload UI
    │   ├── components/InspectionLogPanel.tsx # MỚI — bảng nhật ký kiểm tra
    │   └── App.tsx               # Viết lại — auth thật, apiFetch, 2 modal mới
    ├── Dockerfile              # MỚI — Nginx multi-stage
    ├── nginx.conf              # MỚI — reverse proxy + SPA fallback
    └── package.json
```

## 3. Bảng Model ↔ Bảng dữ liệu (đối chiếu kế hoạch)

| Tên Model trong kế hoạch | Bảng PostgreSQL | File |
|---|---|---|
| User Model | `users` | `db_models.py::User` |
| Document Model | `documents` | `db_models.py::Document` |
| ChatSession Model | `chat_sessions` | `db_models.py::ChatSession` |
| ChatMessage Model | `chat_messages` | `db_models.py::ChatMessage` |
| ProjectData Model | `project_data` | `db_models.py::ProjectData` |
| InspectionLog Model | `inspection_logs` | `db_models.py::InspectionLog` |

## 4. Ghi chú kỹ thuật quan trọng: OCR dùng Gemini, không dùng GPT-4o

Kế hoạch gốc ghi "Vision/OCR Extraction Model (GPT-4o)". Toàn bộ phần còn
lại của hệ thống (chatbot, RAG, appraisal) đã dùng **Gemini** làm nhà cung
cấp AI duy nhất kể từ code gốc `server.ts`. `ocr_vision.py` dùng Gemini
multimodal (cùng SDK, cùng API key, cùng chi phí vận hành đã có) để tránh
phải tích hợp thêm nhà cung cấp AI thứ hai chỉ cho một tính năng. Về chức
năng (đọc ảnh bản vẽ kỹ thuật → JSON có cấu trúc) hai model tương đương.

Nếu khách hàng yêu cầu bám đúng GPT-4o Vision theo văn bản hợp đồng, chỉ
cần sửa hàm `_call_vision_model()` trong `ocr_vision.py` để gọi
`openai.chat.completions.create(model="gpt-4o", ...)` — toàn bộ phần
rasterize PDF (`pdf2image`) và pipeline autofill giữ nguyên không đổi.

## 5. Testing đã thực hiện (không phải chỉ viết code suông)

Đã cài **PostgreSQL 16 thật** trong môi trường sandbox (không mock), chạy
`uvicorn` thật, và test bằng `curl` + `psql`:

| Test | Kết quả |
|---|---|
| Đăng ký user đầu tiên → tự thành admin | ✅ |
| Đăng ký user thứ 2 qua endpoint mở → bị chặn 403 | ✅ |
| Login sai mật khẩu → 401 | ✅ |
| Login đúng → nhận JWT hợp lệ | ✅ |
| Gọi `/api/documents` không token → 401 | ✅ |
| Admin tạo tài khoản nhân viên → 201 | ✅ |
| Staff xem `/api/sessions` → chỉ thấy hồ sơ của mình (0 hồ sơ của admin) | ✅ |
| Staff xoá session của admin → 403 | ✅ |
| Staff reset tài liệu pháp lý (admin-only) → 403 | ✅ |
| Tạo session → lưu đúng PostgreSQL, `evaluate_appraisal` đúng logic gốc | ✅ |
| Chat 2 lượt liên tiếp → đúng số tin nhắn tích luỹ (1→3→5) | ✅ (phát hiện & sửa 1 bug SQLAlchemy cache) |
| Cập nhật project, xoá session → cascade delete xoá sạch messages/project_data/logs | ✅ (verify bằng `psql COUNT(*)`) |
| Export DOCX / PDF / JSON | ✅ cả 3 định dạng |
| OCR endpoint không token → 401; có token nhưng thiếu `GEMINI_API_KEY` → lỗi 500 sạch (không crash) | ✅ |
| **Frontend**: `tsc --noEmit` | ✅ 0 lỗi (phát hiện & sửa thiếu `vite-env.d.ts` — lỗi có sẵn từ bản gốc) |
| **Frontend**: `npm run build` | ✅ build thành công, 654KB JS (gzip 190KB) |
| **Full-stack**: backend v2 phục vụ `frontend/dist` cùng origin, login qua đúng luồng browser thật | ✅ |

**Chưa test được** (giới hạn môi trường sandbox):
- Docker/`docker-compose up` thật (không có Docker daemon trong sandbox) —
  đã verify từng thành phần tương đương thủ công (Postgres service, uvicorn,
  Nginx static+proxy pattern là chuẩn phổ biến, rủi ro thấp)
- Gọi Gemini Vision thật cho OCR (không có `GEMINI_API_KEY`) — đã verify
  code path và graceful error handling, chưa verify độ chính xác đọc bản vẽ
  thật ngoài đời

## 6. Cách chạy

### Docker (khuyến nghị, đúng kế hoạch Ngày 29-30)
```bash
cp .env.example .env
# Điền GEMINI_API_KEY, JWT_SECRET (openssl rand -hex 32), mật khẩu Postgres/admin
docker compose up -d --build
```
- Frontend: `http://localhost` (Nginx, reverse-proxy `/api` → backend)
- Backend API trực tiếp: `http://localhost:3000`
- Đăng nhập lần đầu bằng `PCCC_ADMIN_USERNAME` / `PCCC_ADMIN_PASSWORD` đã đặt
  trong `.env` — **đổi mật khẩu ngay** (chưa có endpoint đổi mật khẩu tự
  phục vụ, xem "Next Recommendation").

### Chạy dev thủ công (không Docker)
```bash
# 1. PostgreSQL
sudo apt-get install postgresql
sudo -u postgres createuser pccc_app -P
sudo -u postgres createdb pccc_db -O pccc_app

# 2. Backend
cd backend
cp .env.example .env   # điền DATABASE_URL, JWT_SECRET, GEMINI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 3000

# 3. Frontend
cd frontend
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:3000
npm install && npm run dev
```

## 7. Remaining Risks / Next Recommendation

1. **Chưa có endpoint đổi mật khẩu** cho user tự phục vụ — nên thêm
   `PUT /api/auth/me/password` trước khi bàn giao thật.
2. **Alembic chưa tích hợp** — hiện dùng `Base.metadata.create_all()` khi
   khởi động (đủ cho MVP/demo). Trước production nên chuyển sang Alembic
   migrations để kiểm soát thay đổi schema an toàn.
3. **Vector Store thật chưa có** — RAG hiện vẫn là keyword-matching
   (`get_rag_context_for_project`), đúng như code gốc. Nếu cần đúng
   "Nhúng văn bản luật (Vector Store)" theo kế hoạch Ngày 5-6, nên thêm
   `pgvector` extension + Gemini embeddings — hạ tầng PostgreSQL đã sẵn sàng
   để mở rộng việc này.
4. **OCR chưa test với bản vẽ thật** — nên chạy thử với ≥10 bản vẽ mẫu thực
   tế trước khi cam kết độ chính xác với khách hàng (kế hoạch Ngày 7-8 cam
   kết >90% độ chính xác trích dẫn/rà soát).
5. **SSL/TLS chưa cấu hình** — `nginx.conf` hiện chỉ HTTP. Khi có domain
   thật, thêm Certbot hoặc đặt Caddy/Nginx TLS-termination phía trước.

## 8. "Khoá chặn" tài khoản test truy cập DevTools (bổ sung mới)

Tính năng mới: ngăn tài khoản `role="staff"` (cấp cho người xem thử/nghiệm
thu bên ngoài) mở DevTools trình duyệt để xem/khai thác mã nguồn phía
client. Tài khoản `admin` luôn được miễn trừ.

**⚠️ Đọc kỹ trước khi bật**: đây là biện pháp răn đe ở tầng trình duyệt,
**không phải** bảo mật tuyệt đối — không có cách nào 100% ngăn người dùng
đủ kỹ thuật đọc mã JS chạy trong trình duyệt của chính họ (giới hạn vật lý
của kiến trúc web). Xem cảnh báo kỹ thuật đầy đủ trong
`frontend/src/lib/codeProtection.ts`. Toàn bộ logic nghiệp vụ nhạy cảm
(thẩm định PCCC, xác thực...) vẫn luôn nằm ở backend, không gửi xuống
client — đây mới là lớp bảo vệ thật sự.

**Cách bật**: đặt trong `.env`:
```
VITE_ENABLE_CODE_PROTECTION=true
```
rồi build lại: `docker compose up -d --build` (biến này là build-arg của
Vite, cần build lại image frontend mới có tác dụng — không phải biến runtime).

**Hành vi khi bật** (chỉ áp dụng cho tài khoản staff):
- Chặn chuột phải (menu ngữ cảnh)
- Chặn phím tắt mở DevTools/xem mã nguồn/lưu trang (F12, Ctrl+Shift+I/J/C,
  Ctrl+U, Ctrl+S và tương đương trên macOS)
- Phát hiện DevTools đang mở (dạng gắn cạnh trình duyệt) → hiện overlay
  cảnh báo che mờ nội dung, tự đóng lại khi người dùng đóng DevTools (không
  xoá dữ liệu, không đăng xuất)
- In cảnh báo chính sách sử dụng trong Console trình duyệt
