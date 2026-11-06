# Hệ Thống Chatbot AI & Thẩm Định Phòng Cháy Chữa Cháy (PCCC AI System)

Hệ thống phần mềm ứng dụng Trí tuệ Nhân tạo hỗ trợ **tư vấn pháp lý quy chuẩn**, **bóc tách bản vẽ kỹ thuật (Vision OCR)**, **tự động rà soát thẩm duyệt 16 hạng mục QCVN 06**, và **xuất báo cáo kết quả thẩm định (Word, PDF, JSON)** theo quy định pháp luật Việt Nam mới nhất.

---

## 1. Căn Cứ Pháp Lý & Quy Chuẩn Kỹ Thuật

Hệ thống được thiết kế, mã hóa và cập nhật tuân thủ đầy đủ các văn bản pháp luật hiện hành:
- **Nghị định số 105/2025/NĐ-CP** (Ban hành ngày 15/05/2025) quy định chi tiết thi hành Luật PCCC & CNCH (kèm Phụ lục I đến VIII).
- **Nghị định số 347/2026/NĐ-CP** (Hiệu lực 15/09/2026) phân cấp thẩm duyệt PCCC và phân quyền cho cơ quan quản lý chuyên ngành & UBND các cấp.
- **QCVN 06:2022/BXD** & **Sửa đổi 1:2023 QCVN 06:2022/BXD** — Quy chuẩn kỹ thuật quốc gia về An toàn cháy cho nhà và công trình.
- **TCVN 3890:2023** — Phòng cháy chữa cháy — Phương tiện phòng cháy và chữa cháy cho nhà và công trình — Trang bị, bố trí.
- **TCVN 13456:2022** — Phòng cháy chữa cháy — Phương tiện chiếu sáng sự cố và chỉ dẫn thoát nạn — Yêu cầu thiết kế, lắp đặt.
- **TCVN 7336:2021** — Phòng cháy chữa cháy — Hệ thống chữa cháy tự động bằng nước, bọt — Yêu cầu thiết kế và lắp đặt.
- **TCVN 5687:2024** — Thông gió, điều hòa không khí và hút khói sự cố cho hành lang & tầng hầm.
- **TCVN 2622:1995** — Phòng cháy, chống cháy cho nhà và công trình — Yêu cầu thiết kế.
- **QCVN 10:2025/BCA** — Quy chuẩn kỹ thuật quốc gia về trang bị phương tiện PCCC.

---

## 2. Kiến Trúc Hệ Thống (Modular MVC Architecture)

Hệ thống tuân thủ nghiêm ngặt nguyên tắc phân tách trách nhiệm (Separation of Concerns):

```
pccc/
├── backend/
│   ├── app/
│   │   ├── main.py              # Application Entrypoint (< 150 dòng): Lifespan, Middleware, Routers
│   │   ├── config.py            # Quản lý biến môi trường, định dạng file, giới hạn dung lượng
│   │   ├── db.py                # Async Database Connection & SQLAlchemy Engine
│   │   ├── db_models.py         # ORM Models (User, ChatSession, InspectionLog, LegalDocument)
│   │   ├── limiter.py           # SlowAPI Limiter chống brute force / rate limit
│   │   ├── rules_engine.py      # Bộ máy tính toán thẩm định 16 hạng mục kỹ thuật QCVN 06
│   │   ├── gemini_client.py     # Tích hợp Google Gemini AI đa tầng, tự động failover & zero-latency
│   │   ├── doc_extract.py       # Bộ bóc tách tài liệu PDF, DOCX và nhị phân .DOC (Word 97-2003 OLE2)
│   │   ├── ocr_vision.py        # Pipeline Gemini Vision AI bóc tách thông số bản vẽ kỹ thuật
│   │   ├── routers/             # [Controller Layer] - Phân rã RESTful API
│   │   │   ├── auth.py          # /api/auth/* (Đăng nhập, Silent Refresh JWT, Giới hạn 10 Staff)
│   │   │   ├── documents.py     # /api/documents/* (Nạp tài liệu, tìm kiếm, xem trước, xóa)
│   │   │   ├── sessions.py      # /api/sessions/* (Quản lý phiên thẩm định, Optimistic Locking)
│   │   │   ├── chat.py          # /api/chat (Tư vấn pháp lý AI, Bộ phân loại ý định RAG)
│   │   │   ├── ocr.py           # /api/ocr/* (Bóc tách bản vẽ kỹ thuật đa trang Vision)
│   │   │   ├── reports.py       # /api/report/* (Xuất báo cáo Word, PDF, JSON)
│   │   │   ├── inspection_logs.py # /api/sessions/{id}/inspection-logs (Lịch sử kiểm tra)
│   │   │   └── health.py        # /api/health/* (Health check cơ sở dữ liệu & AI status)
│   │   └── services/            # [Business Logic Layer]
│   │       ├── rag_service.py   # Hybrid RAG, Intent Classifier, Rich Context 2.500 ký tự
│   │       └── session_service.py # Xử lý nghiệp vụ thẩm định, kiểm duyệt bản nháp
│   └── tests/                   # Bộ test tự động (103 unit tests, 3.000 fuzz scenarios)
├── frontend/
│   ├── src/
│   │   ├── features/            # Mô đun hóa theo tính năng (Mỗi file .tsx < 400 dòng)
│   │   │   ├── auth/            # Màn hình đăng nhập, quản lý phiên làm việc
│   │   │   ├── chat/            # Giao diện Chatbot AI, hỗ trợ onPaste tức thì
│   │   │   ├── compliance/      # Checklist thẩm duyệt 16 hạng mục, bộ lọc 4 tab
│   │   │   ├── documents/       # Thư viện văn bản pháp lý, form tải tài liệu
│   │   │   └── project/         # Form nhập liệu công trình & bóc tách bản vẽ OCR
│   │   ├── layouts/             # Header, Navigation, Menu Mobile đa điểm chạm
│   │   └── lib/                 # apiFetch tự động cấp mới JWT Token
│   └── package.json             # React 18, Vite, TailwindCSS, Lucide Icons
├── compose.yaml                 # Docker Compose cho máy chủ Production VPS
├── compose.local.yaml           # Docker Compose cho môi trường phát triển cục bộ
└── run-docker.bat               # Khởi chạy Docker 1-Click trên Windows
```

---

## 3. Các Tính Năng Nổi Bật

### 3.1. Phân quyền & Bảo mật (RBAC & OWASP)
- **Phân tách vai trò rõ ràng:**
  - `admin` (Quản trị viên): Toàn quyền quản lý tài khoản người dùng, nạp/xóa văn bản pháp quy, xem trạng thái AI Health và nhật ký kiểm tra toàn hệ thống.
  - `staff` (Nhân viên thẩm định): Nhập liệu hồ sơ, tải bản vẽ OCR, tra cứu chatbot pháp lý, xuất báo cáo và xem nhật ký của chính mình (cô lập dữ liệu).
- **Giới hạn cứng 10 tài khoản nhân viên (`MAX_STAFF_ACCOUNTS = 10`):** Kiểm soát nghiêm ngặt bằng khóa giao dịch cấp cơ sở dữ liệu (`pg_advisory_xact_lock`), không tính tài khoản admin.
- **Bảo mật phiên làm việc:** Cơ chế **Silent Refresh JWT** tự động gia hạn phiên làm việc ngầm, thu hồi token khi đăng xuất hoặc đổi mật khẩu, chống tấn công dò quét bằng **SlowAPI Rate Limiter**.

### 3.2. Quản lý Thư viện Pháp lý & RAG Knowledge Base
- **Hỗ trợ đa định dạng tài liệu:** Tải lên và bóc tách tự động file **PDF có lớp text**, file **Word hiện đại (.docx)** và **file Word cũ (.doc - Word 97-2003 OLE2 Binary)** bằng bộ parser nhị phân nội bộ thuần Python với tốc độ xử lý $< 0.05$ giây, giải mã chính xác bảng mã TCVN3 và Unicode.
- **Khử trùng lặp thông minh (Deduplication by Code):** Khi tải tài liệu đầy đủ lên hệ thống, các bản ghi placeholder mặc định cùng mã số tự động được thay thế, không làm loãng tri thức AI.
- **Trích xuất Ngữ cảnh Chuyên sâu (Rich Context):** Tự động bóc tách đoạn ngữ cảnh lên tới 2.500 ký tự xung quanh điều khoản kỹ thuật cốt lõi, tránh bị kẹt ở trang bìa.

### 3.3. Chatbot AI Tư vấn Pháp lý (Hybrid RAG)
- **Bộ phân loại ý định thông minh (Intent Classifier - DEF-01):**
  - Khi người dùng hỏi câu hỏi lý thuyết quy chuẩn chung (ví dụ: *"Nhà cao 75m cần loại thang nào?"*, *"Tiêu chuẩn bình chữa cháy"*), Chatbot **trả lời ngay lập tức** kèm trích dẫn văn bản mà không bắt người dùng phải bấm *"Kiểm duyệt lại hồ sơ"*.
  - Chỉ khi người dùng hỏi về *"Kết luận cấp phép/thẩm định của dự án cụ thể"* trên hồ sơ nháp, Chatbot mới nhắc nhở bấm *"Kiểm duyệt hồ sơ"* để đảm bảo căn cứ pháp lý.
- **Sự kiện dán clipboard tức thì (onPaste - DEF-02):** Khi dán nội dung câu hỏi từ clipboard (`Ctrl + V`), nút *"Gửi câu hỏi"* lập tức sáng lên sẵn sàng gửi ngay mà không cần thêm thao tác gõ phím.
- **Phòng vệ AI:** Chống Prompt Injection, lọc nội dung ngoài phạm vi PCCC, hỗ trợ tiếng Việt có dấu và viết tắt kỹ thuật.

### 3.4. Bóc tách Bản vẽ Kỹ thuật AI OCR Vision
- Tiếp nhận 1 đến 5 bản vẽ kỹ thuật (ảnh PNG/JPG hoặc PDF đa trang).
- Thị giác AI bóc tách tự động: diện tích đất, diện tích xây dựng, số tầng nổi, số tầng hầm, chiều cao PCCC, công năng, bậc chịu lửa, chiều rộng lối thoát nạn... và tự động điền vào Form thông số công trình.

### 3.5. Bộ máy Thẩm duyệt 16 Hạng mục QCVN 06 & Xuất Báo cáo
- **Kiểm tra ngưỡng danh mục:** Tự động kết luận công trình thuộc diện thẩm duyệt thiết kế PCCC theo Nghị định 105/2025/NĐ-CP và phân cấp thẩm duyệt theo Nghị định 347/2026/NĐ-CP.
- **Chấm điểm động 16 hạng mục kỹ thuật:** Chiều cao PCCC, bậc chịu lửa, diện tích khoang cháy, khoảng cách an toàn, đường giao thông bãi đỗ xe chữa cháy, lối thoát nạn, buồng thang N1/N2/N3, hệ thống báo cháy, họng nước vách tường, chữa cháy tự động Sprinkler, thể tích bể nước chữa cháy ($m^3$), hút khói sự cố, tăng áp buồng thang...
- **Bộ lọc Checklist 4 tab:** Lọc trực quan các hạng mục theo trạng thái: Tất cả, Đạt (Pass), Cảnh báo (Warn), Không đạt (Fail).
- **Xuất đa định dạng:** Xuất kết quả thẩm duyệt chính thức ra file **Word (.docx)** định dạng chuẩn văn bản, **PDF (.pdf)** chất lượng in ấn, và **JSON (.json)** dữ liệu cấu trúc phục vụ tích hợp hệ thống.

### 3.6. Tối Ưu Token, Quota & Tốc Độ Trả Lời (Performance)
- **Tốc độ phản hồi cực nhanh (Zero-Latency Thinking):** Cấu hình `ThinkingConfig(thinking_budget=0)` giúp mô hình Flash phản hồi trong **1 - 2 giây**, triệt tiêu độ trễ suy nghĩ ngầm (10 - 20s) và tiết kiệm 100% token reasoning.
- **Chuỗi Fallback Quota 3 tầng:** Tự động chuyển tiếp `gemini-2.5-flash` $\rightarrow$ `gemini-3.5-flash` $\rightarrow$ `gemini-3.1-flash-lite`. Khi model chính chạm hạn mức 429 Free Tier, hệ thống tự động gọi model dự phòng ngay lập tức mà không gián đoạn người dùng.
- **Bộ nhớ đệm (In-memory Cache):** Lưu trữ kết quả tra cứu các câu hỏi lý thuyết phổ biến, giảm thiểu chi phí API quota.

---

## 4. Hướng Dẫn Cài Đặt & Khởi Chạy

### 4.1. Yêu cầu Hệ thống
- **Hệ điều hành:** Linux (Ubuntu 22.04+ khuyến nghị) hoặc Windows 10/11.
- **Phần mềm:** Docker & Docker Compose v2 (hoặc Python 3.12 + Node.js 20+ nếu chạy local).
- **Cấu hình tối thiểu:** 2 vCPU, 4 GB RAM, 20 GB dung lượng ổ đĩa.

---

### 4.2. Khởi chạy 1-Click bằng Docker (Khuyến nghị)

#### Trên Windows (Môi trường Local Development):
Chạy file script tự động:
```bat
run-docker.bat
```
Script sẽ tự động kiểm tra Docker, tạo môi trường `.env`, khởi tạo PostgreSQL, Backend FastAPI và Frontend React. Truy cập: `http://localhost:5173`.

#### Trên Linux VPS (Môi trường Production):
1. Clone mã nguồn về máy chủ:
   ```bash
   git clone https://github.com/KshowNHT/PCCC-fin-fixed-full-v4.git
   cd PCCC-fin-fixed-full-v4
   ```
2. Cấu hình biến môi trường production:
   ```bash
   cp .env.example .env
   # Mở file .env để điền GEMINI_API_KEY, PCCC_ADMIN_PASSWORD và SECRET_KEY
   nano .env
   ```
3. Khởi chạy toàn bộ hệ thống bằng Docker Compose:
   ```bash
   docker compose -f compose.yaml up -d --build
   ```
4. Kiểm tra trạng thái các container:
   ```bash
   docker compose ps
   curl -f http://localhost:8000/api/health
   ```

---

### 4.3. Khởi chạy Môi trường Phát triển (Local Dev không dùng Docker)

#### Bước 1: Khởi tạo Backend (Python 3.12)
```bash
# Tạo môi trường ảo và cài đặt dependencies
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r backend/requirements-test.txt

# Cấu hình biến môi trường
copy backend\.env.example backend\.env

# Khởi chạy server FastAPI Backend
python -m uvicorn app.main:app --app-dir backend --reload --port 3000
```

#### Bước 2: Khởi tạo Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Giao diện ứng dụng sẽ chạy tại địa chỉ: `http://localhost:5173`.

---

## 5. Tài Khoản Đăng Nhập Mặc Định

Khi hệ thống khởi tạo lần đầu, cơ sở dữ liệu tự động tạo sẵn tài khoản quản trị:
- **Tên đăng nhập:** `admin`
- **Mật khẩu:** Được cấu hình trong biến môi trường `PCCC_ADMIN_PASSWORD` (mặc định trong `.env.example`: `admin123`).
- **Đổi mật khẩu:** Ngay sau lần đăng nhập đầu tiên, vui lòng đổi mật khẩu tại menu góc trên bên phải hoặc gọi `PUT /api/auth/me/password`.

---

## 6. Kiểm Thử Hệ Thống (Quality Assurance & CI/CD)

Hệ thống được trang bị bộ kiểm thử tự động toàn diện, tích hợp trực tiếp vào **GitHub Actions CI/CD Pipeline**:

```bash
# 1. Chạy bộ 103 Unit Tests Backend (xác thực toàn bộ API, RAG, Auth, QCVN):
python -m unittest discover -s backend/tests -p "test_*.py"

# 2. Chạy kiểm thử Fuzzing 3.000 kịch bản ngẫu nhiên:
python backend/tests/test_rules_fuzz.py

# 3. Chạy kiểm tra tĩnh mã nguồn Frontend (TypeScript Linting - 0 errors):
npm --prefix frontend run lint

# 4. Đóng gói kiểm tra bản build Frontend Production:
npm --prefix frontend run build
```

---

## 7. Giấy Phép & Tuyên Bố Miễn Trừ Trách Nhiệm

- Phần mềm được phát triển bởi PDTech cung cấp giải pháp công nghệ **HopDong_Chatbot_PCCC_1A**.
- **Tuyên bố pháp lý:** Hệ thống là công cụ hỗ trợ rà soát, tra cứu quy chuẩn kỹ thuật và kiểm tra sơ bộ hồ sơ thiết kế phòng cháy chữa cháy. Kết quả do hệ thống cung cấp mang tính chất tư vấn kỹ thuật hỗ trợ chuyên gia; kết luận cấp phép chính thức phải do cơ quan có thẩm quyền về PCCC theo Nghị định 105/2025/NĐ-CP và Nghị định 347/2026/NĐ-CP phê duyệt và ban hành bằng văn bản.
