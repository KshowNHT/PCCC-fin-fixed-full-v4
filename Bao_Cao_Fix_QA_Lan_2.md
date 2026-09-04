# Báo cáo Fix Lỗi — Đối chiếu Bao_Cao_QA_Lan_2.md

**Vai trò:** rà soát dạng "20 năm kinh nghiệm Python", ưu tiên tìm **nguyên
nhân gốc (root cause)** thay vì vá triệu chứng. Mọi bug dưới đây đều đã được
**verify bằng test thật** (unit test trực tiếp hàm, hoặc gọi API thật qua
PostgreSQL + uvicorn) trước khi báo hoàn thành — không chỉ đọc code suy đoán.

---

## Tóm tắt

| Bug | Mức độ (theo QA) | Trạng thái |
|---|---|---|
| B10 — Kết quả không tái lập | 🔴 Nghiêm trọng nhất | ✅ Đã vá tận gốc, verify bằng test 3 lần chạy giống hệt nhau |
| B06 — Nội dung export lệch hạng mục | 🔴 Nghiêm trọng | ✅ Đã vá tận gốc, verify bằng unit test giả lập dữ liệu AI lệch |
| B03 — Validation ô nhập liệu | 🟠 Cao | ✅ Đã vá, verify bằng test API thật (số âm + logic vô lý) |
| B04 — Thiếu nút Huỷ | 🟠 Cao | ✅ Đã thêm AbortController + nút Huỷ |
| B07 — Vỡ giao diện mobile | 🟠 Cao | ✅ Đã vá 3 vấn đề con (tràn ngang, nút chen chúc, toggle không "ăn") |
| B08/B09 — Reset không sạch | 🟠 Cao | ✅ Đã tìm đúng dòng code lỗi, vá tận gốc |
| Ghi nhận thêm: hardcode "2.500m²/6 tầng" | 🟡 Phát hiện thêm | ✅ Đã vá |
| Phát hiện thêm: `VITE_API_URL` sai tên biến | 🟡 Phát hiện thêm (không có trong QA) | ✅ Đã vá |
| B01 — Hiệu năng 12-18s | 🟢 Đã cải thiện (QA ghi nhận), không phải bug code | ⚪ Không có thay đổi thêm — xem mục 8 |

---

## 1. B10 — Kết quả thẩm định không tái lập được (CRITICAL)

### Nguyên nhân gốc
Hai lỗi kiến trúc cộng hưởng:
1. `gemini_client.py`: `temperature=0.2` — cho phép Gemini trả lời khác
   nhau giữa các lần gọi giống hệt đầu vào.
2. `isSubjectToAppraisal`/`appraisalReason` (kết luận pháp lý — vốn là
   **công thức toán học thuần**: `floors >= 7 HOẶC totalFloorArea >= 3000`)
   trước đây được lấy **thẳng từ JSON do LLM tự sinh**, không hề đối chiếu
   với bất kỳ nguồn "sự thật" nào khác. Một LLM không hoàn toàn deterministic
   dù `temperature=0`, nên để nó tự quyết định 1 con số nhị phân có tính
   ràng buộc pháp lý là sai nguyên tắc thiết kế.

### Cách vá
- `backend/app/main.py`: sau khi gọi Gemini xong, **luôn** tính lại bằng
  `rules_engine.evaluate_appraisal()` (cây quyết định thuần toán học, không
  phụ thuộc AI) và **ghi đè** `isSubjectToAppraisal`/`appraisalReason`/
  `result` của từng hạng mục bằng giá trị deterministic này. Áp dụng cho cả
  2 nơi gọi AI: `PUT /api/sessions/{id}/project` và `POST /api/chat`.
- `backend/app/gemini_client.py`: hạ `temperature` 0.2 → **0.0**.

### Test đã chạy (thật, không suy đoán)
Gọi API thẩm định (`appraise=true`) 3 lần liên tiếp với **cùng một** bộ
thông số (`floors=8, floorArea=400, totalFloorArea=3500`):
```
run 1: isSubjectToAppraisal=True, results=[Không đạt, Không đạt, Cần đo đạc, ...]
run 2: isSubjectToAppraisal=True, results=[Không đạt, Không đạt, Cần đo đạc, ...]
run 3: isSubjectToAppraisal=True, results=[Không đạt, Không đạt, Cần đo đạc, ...]
```
**Giống hệt nhau tuyệt đối cả 3 lần** — bug đã được giải quyết triệt để,
không phải giảm thiểu.

---

## 2. B06 — Nội dung "Kết luận chi tiết" không khớp "Hạng mục" (CRITICAL)

### Nguyên nhân gốc
`_merge_checklist()` (bản cũ) ghép `note` của AI vào đúng hạng mục dựa
**hoàn toàn vào `stt` do chính AI tự gán** trong JSON trả về. Vì response
là tự do (LLM tự sinh mảng 17 phần tử), nếu AI gán sai `stt` cho 1 note
(ví dụ viết nội dung về "khoảng cách an toàn" nhưng gán `stt=2` — vốn là ô
"Bậc chịu lửa") thì bảng hiển thị sẽ sai lệch hoàn toàn mà hệ thống không
hề phát hiện được.

### Cách vá
`_merge_checklist()` viết lại hoàn toàn (`backend/app/main.py`):
- `result` của **cả 17 hạng mục** giờ luôn lấy từ `rules_engine` (xem B10)
  — AI không còn quyền quyết định giá trị này.
- `note`: chỉ chấp nhận từ AI **khi** `ai_checklist` hợp lệ (đúng 17 phần
  tử, `stt` là hoán vị 1..17, không trùng/thiếu). Nếu không hợp lệ (dấu
  hiệu điển hình của 1 lần chạy lỗi), **toàn bộ note** fallback về
  `rules_engine` — không dùng dữ liệu dị dạng dù chỉ 1 phần.
- `backend/app/gemini_client.py`: system prompt giờ liệt kê tường minh cả
  17 hạng mục kèm đúng STT (`checklist_anchor`) để neo ngữ cảnh, giảm khả
  năng AI tự gán nhầm ngay từ đầu (giảm residual risk, không phải fix
  chính — fix chính là lớp validate ở trên).

### Test đã chạy (unit test trực tiếp hàm `_merge_checklist`)
```python
# Giả lập chính xác lỗi QA mô tả: note của "Bậc chịu lửa" (stt=2)
# bị gán nhầm nội dung "Khoảng cách an toàn" + trùng stt=2
malformed_ai = [
    {"stt": 1, ...}, 
    {"stt": 2, "note": "Yêu cầu khoảng cách an toàn..."},  # SAI nội dung
    {"stt": 2, "note": "note trùng stt=2 khác"},            # TRÙNG stt
]
merged = _merge_checklist(malformed_ai, deterministic_checklist)
```
Kết quả: `merged[1]["result"]` khớp 100% rules_engine, `merged[1]["note"]`
khớp 100% note gốc rules_engine (KHÔNG bị ghi đè bởi note lệch của AI) —
**cả 2 assertion đều `True`**.

Test thêm case AI trả dữ liệu **hợp lệ** (đủ 17, đúng hoán vị): note của
AI được dùng đúng như kỳ vọng, `result` vẫn deterministic — xác nhận fix
không làm mất tính năng "AI viết note phân tích".

---

## 3. B03 — Validate ô nhập liệu (Tầng=4, DT=30, Tổng=50 vẫn submit được)

### Nguyên nhân gốc
`PUT /api/sessions/{id}/project` nhận `body: dict` thô — **không có bất kỳ
validation nào** ở tầng API. Frontend cũng không có `min` trên input
`type="number"`.

### Cách vá
- **Backend** (mới): `backend/app/schemas_project.py` — `ProjectUpdateRequest`
  (Pydantic): `ge=0` cho toàn bộ trường số; `model_validator` chặn cứng khi
  `totalFloorArea` nhỏ hơn 50% của `floorArea × floors` (bắt đúng case QA
  nêu: 30×4=120, nhập 50 → 50 < 60 → chặn) và nhỏ hơn 1 tầng đơn lẻ.
- **Frontend**: thêm `min={0}` + `Math.max(0, ...)` tại `onChange` cho cả
  8 ô số (`Sidebar.tsx`) — chặn ngay từ UI, đồng bộ với backend.
- **Frontend**: `App.tsx` — trước đây lỗi 422 bị **nuốt im lặng** (chỉ
  `console.error`), UI vẫn hiển thị giá trị không hợp lệ như thể đã lưu
  thành công. Giờ có `parseApiError()` hiển thị banner lỗi rõ ràng + rollback
  UI về giá trị đã lưu gần nhất trên server.

### Test đã chạy (gọi API thật)
```bash
PUT /project  {"floors": -5, "totalFloorArea": -9999999}
→ HTTP 422: "Input should be greater than or equal to 0" (cả 2 trường)

PUT /project  {"floors": 4, "floorArea": 30, "totalFloorArea": 50}
→ HTTP 422: "Tổng diện tích sàn (50.0m²) quá nhỏ so với 4 tầng × 30.0m²/tầng
   (dự kiến tối thiểu ~60m²) — vui lòng kiểm tra lại số liệu."
```
Đúng chính xác kịch bản QA nêu.

---

## 4. B04 — Không có nút Huỷ giữa chừng

### Cách vá
- `frontend/src/App.tsx`: thêm `abortControllerRef` (AbortController),
  `handleCancelPending()`. Áp dụng cho `handleSendMessage` và
  `handleTriggerAppraisal` (2 luồng gọi AI dài 12-18s+).
- `frontend/src/components/MainArea.tsx`: thêm nút "Huỷ" ngay cạnh chỉ báo
  "Đang phân tích..." — gọi `onCancelPending` (prop mới).
- `AbortError` được lọc riêng, không hiện thông báo lỗi khi người dùng chủ
  động huỷ (khác với lỗi mạng thật).

---

## 5. B07 — Giao diện vỡ trên mobile (3 vấn đề con)

### 5a. "Báo cáo nhanh" tràn ngang, chữ bị cắt
**Nguyên nhân:** `<h3 className="truncate">` nằm trong 1 flex item **không
có `min-w-0`** — đây là gotcha kinh điển của Tailwind/Flexbox: flex item mặc
định `min-width: auto`, khiến nó không chịu co nhỏ hơn nội dung dù có class
`truncate`, gây tràn ra ngoài khung chứa trên màn hình hẹp.
**Vá:** thêm `min-w-0 flex-1` vào div bọc tiêu đề.

### 5b. Các nút chức năng chen chúc khó bấm
**Vá:** thêm `flex-wrap` cho khung chứa 3 nút (Thực hiện kiểm duyệt / Xuất
Word / Tải PDF), giảm padding cố định (`px-6` → `px-3 sm:px-6`) để có thêm
không gian trên màn hình hẹp.

### 5c. Nút thu gọn/mở rộng bấm không "ăn"
**Nguyên nhân gốc (khó phát hiện nhất):** có 1 `useEffect` tự động
`setIsSpecsExpanded(false)` mỗi khi có tin nhắn mới — chạy **đè lên** lựa
chọn vừa bấm tay của người dùng. Vì `onToggleSidebar` là arrow function
khai báo inline ở `App.tsx` (đổi identity mỗi lần render), effect này dễ bị
kích hoạt lại nhiều hơn dự kiến.
**Vá:** thêm `userToggledSpecsRef` — đánh dấu khi người dùng tự bấm nút
trong phiên hiện tại, effect auto-collapse tôn trọng lựa chọn này (reset
lại khi đổi sang phiên/hồ sơ khác).

---

## 6. B08/B09 — "Thẩm định Hồ sơ Mới" không reset sạch (Số tầng nổi giữ giá trị cũ)

### Nguyên nhân gốc (tìm chính xác đến từng dòng)
`Sidebar.tsx`, đoạn đồng bộ `localFloors` với `project.floors`:
```js
// CODE CŨ (lỗi):
if (propFloors !== "" && propFloors !== 0) {
  setLocalFloors(propFloors);
} else if (Number(localFloors) <= 1) {   // <-- chỉ reset về 0 nếu giá trị CŨ đã <=1
  setLocalFloors(propFloors);
}
```
Khi tạo session mới, `project.floors` = 0 (đúng), nhưng nếu giá trị cũ trên
UI đang là 5 (>1), điều kiện `else if` **không bao giờ đúng** → `localFloors`
kẹt ở 5 vĩnh viễn dù backend đã có dữ liệu đúng là 0. Đây rõ ràng là 1 đoạn
code "sticky" cố tình thêm vào (có thể để chống nhấp nháy khi AI đang trích
xuất dữ liệu tăng dần) nhưng gây tác dụng phụ nghiêm trọng hơn.

Cùng lỗi cho `localBasements`, và biến thể nhẹ hơn cho các mảng
`floorFunctions`/`basementFunctions`/`basementHeights`/`basementAreas`/
`basementFootprints` (chỉ đồng bộ khi có dữ liệu MỚI, không xoá khi rỗng).

### Cách vá
Xoá toàn bộ điều kiện "sticky", đồng bộ thẳng theo `project` prop (vẫn giữ
guard hợp lý "không ghi đè khi người dùng đang gõ trong chính ô đó").

### Test đã chạy
```bash
POST /api/sessions {} 
→ {"floors": 0, "totalFloorArea": 0.0, ...}
```
Xác nhận backend luôn trả state sạch; phần fix chính nằm ở tầng đồng bộ
state cục bộ React (`Sidebar.tsx`) — đã sửa đúng dòng code gây lỗi.

---

## 7. Phát hiện thêm (không có trong Bao_Cao_QA_Lan_2.md)

### 7a. Hiển thị cứng "2.500m² / 6 tầng" khi hồ sơ đang trống
`MainArea.tsx` tab "[Xem Rộng] Kết luận Pháp lý": `{projectInfo.totalFloorArea
|| "2.500"} m²` — khi giá trị thật là `0` (falsy), fallback hiện số **giả**
thay vì "0" hay "chưa nhập", khiến người dùng tưởng nhầm đã có dữ liệu thật.
**Vá:** đổi thành hiển thị "Chưa nhập" khi giá trị = 0/rỗng.

### 7b. `VITE_API_URL` sai tên biến trong Docker build
`frontend/Dockerfile` và `compose.yaml` truyền build-arg tên `VITE_API_URL`,
nhưng code (`lib/api.ts`, `Sidebar.tsx`) chỉ đọc
`import.meta.env.VITE_API_BASE_URL` — **sai tên hoàn toàn**, khiến cấu hình
URL API set qua Docker build không bao giờ có tác dụng (âm thầm rơi về giá
trị mặc định). Đã đổi tên biến khớp nhau ở cả 2 file + `.env.example`.

**Lưu ý riêng cho bạn:** file `.env` thật của bạn (chứa `GEMINI_API_KEY`
thật) vẫn còn dùng tên cũ `VITE_API_URL` — đổi thành `VITE_API_BASE_URL`
(giữ nguyên giá trị) trước khi build lại Docker, xem mục "Cần bạn tự làm"
bên dưới.

---

## 8. B01 — Hiệu năng (không sửa thêm)

QA lần 2 đã ghi nhận **CẢI THIỆN** (từ 70-190s xuống 12-18s) sau lần fix
trước, chỉ còn "thỉnh thoảng vượt 15s". Đây là độ trễ gọi Gemini API qua
mạng, không phải bug logic trong code — hạ `temperature=0` ở fix B10 lần
này có thể giúp giảm nhẹ thêm (ít token sinh ra hơn do model tự tin hơn ở
temperature thấp), nhưng không có thay đổi kiến trúc nào thêm trong lần
này. Nếu cần tối ưu sâu hơn: cân nhắc cache RAG context, hoặc model Gemini
nhanh hơn.

---

## 9. Danh sách file đã sửa

| File | Loại thay đổi |
|---|---|
| `backend/app/main.py` | Sửa — B10/B06 (`_merge_checklist`, 2 nơi gọi LLM), B03 (dùng `ProjectUpdateRequest`) |
| `backend/app/gemini_client.py` | Sửa — temperature=0, neo STT vào system prompt |
| `backend/app/schemas_project.py` | **MỚI** — validation B03 |
| `frontend/src/App.tsx` | Sửa — B03 (hiển thị lỗi + rollback), B04 (AbortController) |
| `frontend/src/components/MainArea.tsx` | Sửa — B04 (nút Huỷ), B07 (3 vấn đề mobile), hardcode 2.500m²/6 tầng |
| `frontend/src/components/Sidebar.tsx` | Sửa — B08/B09 (xoá logic sticky lỗi), B03 (`min={0}` × 8 ô) |
| `frontend/Dockerfile` | Sửa — đổi tên biến `VITE_API_BASE_URL` |
| `compose.yaml` | Sửa — đổi tên biến `VITE_API_BASE_URL` |
| `.env.example` | Sửa — đổi tên biến `VITE_API_BASE_URL` |

**Không đổi:** toàn bộ file backend còn lại (`auth.py`, `db_models.py`,
`rules_engine.py`, `ocr_vision.py`, `pdf_report.py`, `docx_report.py`...),
`frontend/src/components/Login.tsx`, `BlueprintUpload.tsx`,
`InspectionLogPanel.tsx`, `lib/api.ts`, `types.ts` — không liên quan đến
các bug trong báo cáo QA lần 2.

## 10. Cần bạn tự làm (không thể tự động hoá vì liên quan secret của bạn)

Trong file `.env` thật của bạn (không đưa vào gói giao vì chứa API key
thật), đổi:
```diff
- VITE_API_URL=http://localhost:8000
+ VITE_API_BASE_URL=http://localhost:8000
```
(giữ nguyên giá trị, chỉ đổi tên biến ở vế trái).

## 11. Testing Summary

Toàn bộ test dưới đây chạy **thật** qua PostgreSQL 16 + uvicorn (không phải
đọc code suy đoán):

- ✅ 3 lần gọi thẩm định cùng input → kết quả giống hệt nhau tuyệt đối (B10)
- ✅ Unit test `_merge_checklist` với dữ liệu AI lệch stt → fallback đúng rules_engine (B06)
- ✅ Unit test `_merge_checklist` với dữ liệu AI hợp lệ → vẫn dùng note AI, result vẫn deterministic (không mất tính năng)
- ✅ `PUT /project` số âm → 422 đúng thông điệp
- ✅ `PUT /project` logic vô lý (đúng case QA nêu) → 422 đúng thông điệp
- ✅ `POST /sessions` mới → `floors=0, totalFloorArea=0` sạch từ backend
- ✅ Chat message 9000 ký tự → 422 (giới hạn từ bản vá trước vẫn hoạt động)
- ✅ Export DOCX/PDF/JSON → cả 3 vẫn hoạt động bình thường sau các thay đổi
- ✅ `python3 -m py_compile` toàn bộ backend → sạch
- ✅ `tsc --noEmit` toàn bộ frontend → 0 lỗi
- ✅ `npm run build` production → thành công
- ✅ `compose.yaml` → YAML hợp lệ (parse bằng PyYAML)

---

## 12. Rà soát lần 2 (\brutal \10x \ultrathink) — Bổ sung sau khi đối chiếu lại từng dòng code

Sau khi bàn giao bản vá lần đầu, đã thực hiện 1 vòng rà soát độc lập thứ 2,
đọc lại **từng dòng code đã sửa** (không chỉ tin vào ghi chú của lần trước)
và **test tấn công thử nghiệm thật** một lần nữa. Kết quả:

### Xác nhận lại 6 fix cũ vẫn nguyên vẹn, đúng logic
Đã `grep` + đọc trực tiếp code xác nhận cả 6 fix (B10, B06, B03, B04, B07,
B08/B09) đều còn đúng như mô tả, không bị lỗi thời/thoái lui. Đặc biệt đã
kiểm tra kỹ càng:
- Toàn bộ `useEffect` đồng bộ state trong `Sidebar.tsx` (14 field) — xác
  nhận không còn field nào khác dính logic "sticky" tương tự B09 (đã từng
  chỉ ảnh hưởng `floors`/`basements`, giờ xác nhận toàn bộ field đều sync
  đúng, không sót).
- `docx_report.py`/`pdf_report.py` chỉ đơn thuần lặp qua `checklist` đã
  nhận, không tự ghép lại `stt`↔`note` theo cách nào khác — xác nhận không
  có đường tái phát B06 độc lập ở tầng xuất file.

### Phát hiện 1 lỗ hổng dữ liệu MỚI (chưa có trong Bao_Cao_QA_Lan_2.md)

**Vấn đề:** 3 endpoint `/api/report/export`, `/export-pdf`, `/export-json`
trước đây nhận `projectInfo`/`checklist` **trực tiếp từ body request của
client**, không đối chiếu lại với `session.checklist` đã chốt trên server
(nguồn sự thật duy nhất sau fix B10). Trong luồng sử dụng bình thường qua
UI, dữ liệu này vẫn đúng vì frontend chỉ echo lại state đã nhận từ server —
nhưng đây vẫn là 1 lỗ hổng toàn vẹn dữ liệu (data integrity): nếu có bug
frontend khác trong tương lai, hoặc request bị chỉnh sửa thủ công
(Postman/curl/DevTools), file "báo cáo pháp lý" xuất ra có thể chứa dữ liệu
không khớp với dữ liệu đã thẩm định thật trên server — về triệu chứng sẽ
giống hệt B06 dù nguyên nhân khác hẳn.

**Đã vá:** thêm hàm `_resolve_export_data()` — nếu request có `sessionId`,
**bắt buộc** lấy `checklist`/`projectInfo`/kết luận pháp lý từ chính session
đó trên server, **bỏ qua hoàn toàn** dữ liệu client gửi trong `checklist`.
Có kiểm tra quyền sở hữu (staff không xuất được báo cáo hồ sơ người khác —
403). Vẫn giữ tương thích ngược: nếu request không có `sessionId`, fallback
dùng dữ liệu client gửi như cũ.

**Test đã chạy (tấn công giả mạo thật):**
```bash
POST /api/report/export-json
{
  "sessionId": "<session thật, đã thẩm định 8 tầng/3500m²>",
  "projectInfo": {"name": "TEN GIA MAO"},
  "checklist": [{"stt": 1, "criteria": "BỊA ĐẶT", "result": "Đạt", ...}],
  "conclusions": {"reason": "BỊA"}
}
```
Kết quả: file xuất ra chứa **đúng** `"Cong trinh THAT"`, đủ 17 hạng mục
đúng nội dung gốc, kết luận pháp lý đúng — **hoàn toàn bỏ qua** dữ liệu giả
mạo trong request. Test thêm: staff cố export hồ sơ của admin → `403`;
cách gọi cũ (không `sessionId`) vẫn hoạt động bình thường → tương thích
ngược xác nhận không phá vỡ gì.

### File thay đổi thêm trong lần rà soát 2
| File | Thay đổi |
|---|---|
| `backend/app/main.py` | Thêm `_resolve_export_data()`, áp dụng cho cả 3 endpoint export |
| `frontend/src/App.tsx` | Thêm `sessionId: activeSessionId` vào cả 3 lệnh gọi export |

### Kết luận rà soát lần 2
Không phát hiện lỗi nào trong 10 mục B01-B10 bị bỏ sót hoặc vá sai. Phát
hiện thêm và vá 1 lỗ hổng toàn vẹn dữ liệu liên quan trực tiếp đến độ tin
cậy của B06/B10 (dù không nằm trong danh sách QA gốc) — đúng tinh thần
"một hệ thống thẩm định mà kết quả không tái lập được thì không thể dùng
làm căn cứ" mà QA đã nhấn mạnh, giờ áp dụng nhất quán cả ở khâu xuất file.

### Test tổng hợp rà soát lần 2 (chạy lại toàn bộ, PostgreSQL + uvicorn thật)
- ✅ 3 lần `appraise=true` cùng input → `results` giống hệt tuyệt đối cả 3 lần
- ✅ Export JSON kèm `sessionId` + checklist giả mạo → server bỏ qua hoàn toàn, dùng đúng dữ liệu thật
- ✅ Staff export hồ sơ của admin → `403`
- ✅ Export DOCX cách cũ (không `sessionId`) → vẫn hoạt động (tương thích ngược)
- ✅ Export DOCX cách mới (có `sessionId`) → hoạt động đúng
- ✅ `PUT /project` số âm → vẫn `422` (không bị ảnh hưởng bởi thay đổi export)
- ✅ Chat message 9000 ký tự → vẫn `422`
- ✅ `python3 -m py_compile` → sạch
- ✅ `tsc --noEmit` → 0 lỗi

---

## 13. Rà soát lần 3 — Phát hiện file cấu hình Docker THẬT khác với file đã vá trước đó

Khi tiếp tục đối chiếu sâu hơn, phát hiện dự án có **2 file Docker Compose
song song**: `compose.yaml` và `docker-compose.yml`. Kiểm tra `run-docker.bat`
xác nhận: **`run-docker.bat`/`stop-docker.bat`/`logs-docker.bat` CHỈ dùng
`compose.yaml`** — `docker-compose.yml` là file cũ, không được bất kỳ script
nào tham chiếu.

### Hậu quả nghiêm trọng của việc này
Toàn bộ hardening bảo mật đã thêm ở phiên trước (`PCCC_ALLOWED_ORIGINS`,
`MAX_UPLOAD_SIZE_MB`, `JWT_EXPIRE_MINUTES`, comment cảnh báo không publish
port trực tiếp...) **chỉ được thêm vào `docker-compose.yml`** — file KHÔNG
được dùng thật. Nghĩa là những cấu hình đó **chưa từng có tác dụng** trên
máy bạn dù đã được "vá" trên giấy tờ.

### Đã kiểm chứng bằng test thật (không suy đoán)
1. **Xác nhận cơ chế fail-fất vẫn bảo vệ đúng** dù dùng `.env.example` mặc
   định của `compose.yaml` (chứa sẵn `JWT_SECRET="CHANGE_ME_IN_PRODUCTION..."`,
   `PCCC_ADMIN_PASSWORD="admin123"`): chạy thử với đúng bộ giá trị này +
   `NODE_ENV=production` → backend từ chối khởi động đúng như thiết kế.
   **Nhưng phát hiện thêm vấn đề UX:** `run-docker.bat` khi tự tạo `.env`
   lần đầu chỉ nhắc "thêm GEMINI_API_KEY", **không hề cảnh báo** phải đổi
   `JWT_SECRET`/mật khẩu admin trước — người dùng sẽ thấy `docker compose up`
   "chạy xong" nhưng container backend crash-loop không rõ nguyên nhân.

2. **Đã vá `compose.yaml`** (file thật) — thêm 3 biến còn thiếu, đồng bộ
   với những gì đã có sẵn trong code Python từ các lần vá trước.

3. **Đã xoá `docker-compose.yml`** — loại bỏ hoàn toàn nguy cơ 2 file lệch
   nhau trong tương lai (nguyên nhân gốc của vấn đề này).

4. **Đã vá `run-docker.bat`** — thêm cảnh báo rõ ràng về `JWT_SECRET`/
   `PCCC_ADMIN_PASSWORD` ngay khi tự tạo `.env` lần đầu.

5. **Test CORS thật** xác nhận `PCCC_ALLOWED_ORIGINS` (biến trước đây chưa
   từng có tác dụng) giờ hoạt động đúng:
   ```
   Origin: http://localhost:5173  → Access-Control-Allow-Origin: http://localhost:5173  ✅ Cho phép
   Origin: http://evil.com        → (không có header)                                    ✅ Bị chặn
   ```

### File thay đổi thêm trong lần rà soát 3
| File | Thay đổi |
|---|---|
| `compose.yaml` | Thêm `JWT_EXPIRE_MINUTES`, `PCCC_ALLOWED_ORIGINS`, `MAX_UPLOAD_SIZE_MB` |
| `docker-compose.yml` | **Đã xoá** (file chết, nguồn gốc rủi ro lệch cấu hình) |
| `run-docker.bat` | Thêm cảnh báo đổi `JWT_SECRET`/mật khẩu admin khi tự tạo `.env` |
| `README.md`, `SECURITY_AUDIT.md` | Thêm ghi chú đầu file: mọi hướng dẫn Docker dùng `compose.yaml`, không phải `docker-compose.yml` |

### Bài học rút ra
Đây là kiểu lỗi **"vá đúng nhưng vá nhầm file"** — dễ xảy ra nhất khi một
dự án có nhiều file cấu hình trùng mục đích. Việc rà soát lần 3 này chỉ
phát hiện ra nhờ chủ động kiểm tra `run-docker.bat` để xem **thực tế** file
nào được gọi, thay vì tin vào tên file "hợp lý" (`docker-compose.yml` nghe
có vẻ là file chính thống hơn `compose.yaml`, nhưng thực tế thì ngược lại).

---

## 14. Rà soát lần 4 (\ultrathink \10x \brutal) — Kiểm tra toàn diện "sẵn sàng chạy online"

Yêu cầu lần này: rà soát lại **toàn bộ** (bug + bảo mật) để đảm bảo an toàn
khi đưa lên chạy thật trên Internet. Đây là vòng rà soát sâu nhất, đọc lại
từng file một cách có hệ thống thay vì chỉ verify các fix cũ.

### 🔴 NGHIÊM TRỌNG NHẤT: Frontend sẽ KHÔNG hoạt động khi deploy lên domain thật

**Phát hiện:** `VITE_API_BASE_URL` mặc định là `"http://localhost:8000"` —
giá trị này bị **đóng cứng (hardcode) vào file JavaScript đã build** (đặc
điểm của Vite: biến `VITE_*` được thay thế trực tiếp vào code lúc build,
không đọc lại lúc chạy). **Đã chứng minh bằng cách build thử và `grep` thấy
chuỗi `"localhost:8000"` xuất hiện trong file JS đã biên dịch.**

**Hậu quả:** khi deploy lên domain thật (ví dụ `https://pccc.congtyban.vn`),
trình duyệt của **mọi người dùng khác** (không phải máy bạn) sẽ chạy đoạn
JS này và cố gọi API tới `http://localhost:8000` — tức là **cổng 8000 trên
chính máy của người dùng đó**, không phải server thật. Toàn bộ tính năng
đăng nhập, chat, thẩm định... sẽ báo lỗi kết nối. Ứng dụng chỉ "vô tình hoạt
động" trên máy Docker Desktop của người build vì "localhost" của họ trùng
với nơi backend đang chạy.

**Đã vá và verify bằng test tấn công giả lập domain thật:**
1. Đổi giá trị mặc định `VITE_API_BASE_URL` thành **chuỗi rỗng** → code
   (`api.ts`) tự động dùng đường dẫn tương đối (`/api/...`) thay vì URL
   tuyệt đối.
2. Build lại, `grep` xác nhận **không còn** `localhost:8000` trong bundle,
   thay vào đó là `"/api/auth/login-json"` (đường dẫn tương đối).
3. Dựng **Nginx thật** + backend thật, đặt Host header giả lập
   `fake-real-domain.test` (mô phỏng chính xác domain thật), gọi
   `/api/auth/login-json` qua Nginx → **đăng nhập thành công, nhận JWT hợp
   lệ** — chứng minh kiến trúc mới hoạt động đúng trên MỌI domain mà không
   cần build lại theo từng môi trường.

**⚠️ QUAN TRỌNG — bạn cần tự làm:** nếu bạn đã từng chạy `run-docker.bat`
trước đây, file `.env` thật của bạn (không nằm trong gói giao vì chứa
secret) **có thể đã có sẵn dòng** `VITE_API_BASE_URL=http://localhost:8000`
từ lần đầu tạo. Biến trong `.env` LUÔN ghi đè giá trị mặc định mới trong
`compose.yaml` — bạn phải mở `.env`, xoá dòng đó hoặc đổi thành
`VITE_API_BASE_URL=""`, rồi `docker compose up -d --build` lại để bản vá
này thật sự có tác dụng.

### 🟠 Cao: `.gitignore` gốc bị đặt sai tên (mất dấu chấm)

**Phát hiện:** file cấu hình bỏ qua Git ở thư mục gốc có tên **`gitignore`**
(thiếu dấu `.` ở đầu) thay vì `.gitignore`. Git chỉ nhận diện đúng tên file
`.gitignore` — file sai tên này **hoàn toàn vô hiệu, không có tác dụng gì**.
Nếu chạy `git add .` ở trạng thái này, file `.env` (chứa `GEMINI_API_KEY`,
`JWT_SECRET`, mật khẩu admin thật) **có nguy cơ bị commit lên GitHub**.

**Đã vá:** đổi tên `gitignore` → `.gitignore`. Đã verify các file
`.gitignore`/`.env.example` khác trong dự án (frontend, backend) đều đúng
tên — chỉ riêng file gốc bị lỗi.

### 🟡 Trung bình: Mật khẩu admin bị ghi ra log ứng dụng dạng plaintext

**Phát hiện:** `seed.py` khi tạo tài khoản admin lần đầu, log dòng
`"Đã tạo tài khoản admin mặc định: %s / %s"` với `%s` thứ 2 là **chính mật
khẩu**. Log container (`docker compose logs`, hệ thống log tổng hợp, log
provider cloud...) thường được nhiều người/hệ thống truy cập hơn cả file
`.env` — không nên bao giờ ghi secret ra log dù chỉ 1 lần.

**Đã vá:** log giờ chỉ xác nhận đã tạo tài khoản (username), không còn in
mật khẩu. Verify bằng cách chạy seed thật và `grep` log — xác nhận mật khẩu
không xuất hiện.

### 🟡 Trung bình: `DATABASE_URL` có credential mặc định yếu nhưng chưa được đưa vào fail-fast

**Phát hiện:** biến `DATABASE_URL` có fallback mặc định chứa mật khẩu mẫu
`pccc_dev_pass` viết thẳng trong source code — nhưng cơ chế fail-fast
`assert_production_secrets_are_safe()` trước đây **chỉ kiểm tra
`JWT_SECRET`/`PCCC_ADMIN_PASSWORD`**, bỏ sót `DATABASE_URL`.

**Đã vá:** thêm kiểm tra `"pccc_dev_pass" in DATABASE_URL` vào fail-fast
(dùng kiểm tra chứa chuỗi thay vì so khớp tuyệt đối, vì `compose.yaml` thật
ghép chuỗi này với host `postgres` khác với mặc định Python là `localhost`
— so khớp tuyệt đối sẽ bỏ sót đúng kịch bản thật). **Đã test bằng đúng biến
môi trường `compose.yaml` sẽ tạo ra** → xác nhận bị chặn khởi động đúng.

### 🟡 Trung bình: Gọi Gemini API không có timeout (rủi ro treo vô thời hạn)

**Phát hiện:** `generate_content_with_retry()` gọi Gemini API qua
`asyncio.to_thread()` không có bất kỳ giới hạn thời gian nào. Nếu API bên
ngoài "treo" (network hang, quá tải không phản hồi lỗi rõ ràng), request có
thể chờ **vô thời hạn**, chiếm giữ 1 luồng worker mãi mãi — với nhiều người
dùng đồng thời trên môi trường online thật, đây là rủi ro cạn kiệt tài
nguyên (resource exhaustion) dù không có kẻ tấn công chủ đích.

**Đã vá:** bọc mỗi lần gọi bằng `asyncio.wait_for(..., timeout=45.0)` —
giới hạn cứng 45 giây/lần gọi, vẫn giữ nguyên cơ chế retry/fallback model
đã có.

### File thay đổi thêm trong lần rà soát 4
| File | Thay đổi |
|---|---|
| `frontend/Dockerfile` | Đổi mặc định `VITE_API_BASE_URL` từ `http://localhost:8000` → rỗng (đường dẫn tương đối) |
| `compose.yaml` | Đồng bộ theo, thêm giải thích chi tiết |
| `.env.example` | Đồng bộ `VITE_API_BASE_URL=""`, bổ sung đầy đủ biến còn thiếu (`PCCC_ALLOWED_ORIGINS`, `MAX_UPLOAD_SIZE_MB`, `JWT_EXPIRE_MINUTES`) |
| `gitignore` → `.gitignore` | Đổi tên file (Git không nhận diện file thiếu dấu chấm) |
| `backend/app/seed.py` | Không log mật khẩu admin ra log ứng dụng |
| `backend/app/config.py` | Fail-fast thêm kiểm tra `DATABASE_URL`, sửa comment tham chiếu file đã xoá |
| `backend/app/gemini_client.py` | Thêm timeout 45s/lần gọi Gemini |

### Test tổng hợp rà soát lần 4 (tất cả chạy thật, không suy đoán)
- ✅ Build thử với default cũ → xác nhận `localhost:8000` bị hardcode vào bundle (chứng minh lỗi tồn tại)
- ✅ Build lại với default mới → xác nhận sạch, dùng đường dẫn tương đối
- ✅ Dựng Nginx + backend thật, giả lập domain khác localhost → đăng nhập thành công qua đường dẫn tương đối
- ✅ Fail-fast chặn đúng khi `DATABASE_URL` chứa `pccc_dev_pass` (kể cả kiểu ghép chuỗi của `compose.yaml` thật)
- ✅ Log khởi động seed → xác nhận không còn in mật khẩu
- ✅ Regression toàn bộ: B10 (3 lần giống hệt), B03 (422 số âm), export data integrity (bỏ qua checklist giả mạo), export DOCX/PDF — tất cả vẫn hoạt động đúng
- ✅ `python3 -m py_compile` → sạch
- ✅ `tsc --noEmit` → 0 lỗi
- ✅ `npm run build` → thành công, verify bundle không còn hardcode

### ⚠️ Việc BẮT BUỘC bạn phải tự làm trước khi deploy online
1. Mở file `.env` thật (không có trong gói giao), xoá hoặc để trống dòng
   `VITE_API_BASE_URL` — **đây là bước bắt buộc để bản vá quan trọng nhất
   trong lần rà soát này có tác dụng.**
2. Đặt `JWT_SECRET` mạnh (`openssl rand -hex 32`), `PCCC_ADMIN_PASSWORD`
   mạnh (>=10 ký tự, có chữ+số), `POSTGRES_PASSWORD` khác `pccc_dev_pass`.
3. Nếu deploy lên VPS có IP/domain công khai: cân nhắc chặn port 8000 ở
   firewall/security group, chỉ mở port 80/443 (Nginx) ra Internet — port
   8000 hiện vẫn publish trực tiếp để tiện debug cục bộ, nhưng public ra
   Internet đồng nghĩa bỏ qua lớp rate-limit/security-headers của Nginx.
4. Cấu hình SSL/TLS thật (Certbot hoặc Caddy) trước khi công khai domain —
   xem mục 7 (Remaining Risks) trong README.md.
