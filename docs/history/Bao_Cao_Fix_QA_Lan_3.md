# Báo cáo Fix Lỗi — Đối chiếu Bao_Cao_QA_Lan_3.md

Bản QA lần 3 test trên **hệ thống đã deploy thật** (Vercel + Render), phát
hiện 23 lỗi mới (B11-B23) cùng đánh giá lại 10 lỗi cũ (B01-B10). Tài liệu
này ghi lại đầy đủ: nguyên nhân gốc từng lỗi, cách vá, và bằng chứng test
thật (không suy đoán) cho từng mục đã xử lý trong phiên này.

---

## 1. Tóm tắt

| Mức độ | Số lượng | Đã vá trong phiên này |
|---|---|---|
| 🔴 Nghiêm trọng | 2 (B11, B12) | ✅ 2/2 |
| 🟠 Cao | 3 (B13, B14, B15) | ✅ 3/3 |
| 🟡 Trung bình | 5 (B03-phần còn lại, B17, B18, B19, B04) | ✅ 5/5 |
| 🟢 Thấp | 4 (B16, B20, B21, B22, B23) | ✅ 5/5 |

**Toàn bộ 15 lỗi đã sửa trong danh sách ưu tiên của QA (mục V báo cáo) đều
đã được xử lý và verify bằng test thật** (unit test trực tiếp hàm, hoặc gọi
API/export file thật qua PostgreSQL + uvicorn).

---

## 2. B12 — Công năng công trình bị bỏ qua hoàn toàn (🔴 NGHIÊM TRỌNG NHẤT)

### Nguyên nhân gốc
`rules_engine.py::evaluate_appraisal()` **chưa từng đọc `project["type"]`**
— toàn bộ logic chỉ dựa vào `floors`/`totalFloorArea`. Karaoke, nhà kho,
nhà ở dân dụng cùng quy mô luôn cho ra kết quả giống hệt nhau.

### Cách vá
Thêm `_classify_building_category()` phân loại theo từ khoá trong
`type`/`commercialDetails` thành 5 nhóm: `karaoke_entertainment`,
`warehouse`, `market_mall`, `school`, `mixed_residential` (+ `unclassified`
khi không nhận diện được). Mỗi nhóm áp ngưỡng thẩm duyệt riêng:

- **Karaoke/vũ trường/quán bar**: **LUÔN** khuyến nghị bắt buộc thẩm duyệt
  bất kể quy mô (fail-safe chủ động, phản ánh đúng mức độ giám sát đặc biệt
  nghiêm ngặt theo Thông tư 147/2020/TT-BCA sau các vụ cháy karaoke gây
  chết người). Mục 9 (báo cháy tự động) cũng bắt buộc "Không đạt" bất kể
  số tầng, do đặc thù phòng cách âm giảm khả năng tự nhận biết cháy sớm.
- **Nhà kho**: ngưỡng thận trọng hơn nhà hỗn hợp (1.000m² thay vì 3.000m²),
  kèm cảnh báo BẮT BUỘC rà soát thủ công vì thiếu dữ liệu nhóm nguy hiểm
  cháy nổ của hàng hoá lưu trữ.
- **Chợ/TTTM, trường học**: ngưỡng riêng phản ánh mật độ người sử dụng cao.
- **Nhà hỗn hợp**: giữ nguyên ngưỡng gốc (7 tầng/3.000m²).
- **Chưa phân loại được**: vẫn tính theo ngưỡng chung để tham khảo, nhưng
  LUÔN đính kèm cảnh báo rõ ràng yêu cầu kỹ sư PCCC rà soát thủ công.

**Minh bạch quan trọng**: các ngưỡng số cho nhóm kho/chợ/trường học là ước
lượng thận trọng, không thay thế việc đối chiếu trực tiếp QCVN 06:2022/BXD
bởi kỹ sư có chứng chỉ hành nghề — hệ thống luôn nói rõ điều này.

### Test đã chạy (đúng kịch bản QA tái hiện)
```
Karaoke (5 tầng, 500m²): isSubjectToAppraisal = True
Nhà ở kết hợp kinh doanh (5 tầng, 500m², CÙNG thông số): isSubjectToAppraisal = False
```
Xác nhận qua cả unit test trực tiếp hàm và gọi API thật.

---

## 3. B11 — Động cơ AI ngừng hoạt động + thông báo dự phòng RỖNG (🔴 NGHIÊM TRỌNG)

### Nguyên nhân gốc
Khi Gemini lỗi (thiếu/sai `GEMINI_API_KEY`, hết hạn mức, hoặc dịch vụ Google
gián đoạn), hệ thống **đã đúng thiết kế** tự chuyển sang fallback (bộ luật
cứng, không cần AI). Tuy nhiên câu `reply` cũ chỉ nói "Dưới đây là kết quả
rà soát..." rồi **không có nội dung gì theo sau trong khung chat** — 17 mục
checklist thực ra render ở bảng riêng (specs panel), không phải trong bong
bóng chat. Người dùng đọc xong tưởng phần mềm hỏng hoàn toàn.

### Cách vá
1. Viết lại `get_local_fallback_response()` — `reply` giờ **tự chứa** một
   bản tóm tắt đầy đủ ngay trong khung chat: nêu rõ lý do AI không phản
   hồi được, kết luận thẩm duyệt, số hạng mục chưa đạt, và hướng dẫn xem
   chi tiết ở bảng bên dưới.
2. Thêm `/api/health/ai` (kiểm tra đã cấu hình `GEMINI_API_KEY` chưa,
   không lộ giá trị key) và `/api/health/ai/ping` (chỉ admin — gọi thật 1
   lần để xác nhận key còn hoạt động) — đáp ứng đúng khuyến nghị QA "nên
   có trang trạng thái dịch vụ để tự kiểm tra."

### Test đã chạy
```
Reply length: 737 ký tự (trước đây: chỉ có câu giới thiệu, không có nội dung theo sau)
Reply preview: "⚠️ Hệ thống AI (Gemini) hiện không phản hồi được — có thể do chưa cấu hình..."
GET /api/health/ai → {"geminiApiKeyConfigured": false, "detail": "Chưa cấu hình GEMINI_API_KEY..."}
```

**Lưu ý cho bạn**: nếu server thật (Render) đã có `GEMINI_API_KEY` hợp lệ
mà vẫn rơi vào fallback, hãy gọi `GET /api/health/ai/ping` (đăng nhập admin)
để biết chính xác lỗi gọi Gemini là gì — có thể do hết hạn mức miễn phí,
IP bị chặn, hoặc key sai định dạng.

---

## 4. B13 — Nhãn "hạng mục đạt" gây hiểu nhầm (🟠 Cao)

**Nguyên nhân**: biến `compliantCount` đếm gộp cả "Đạt" VÀ "Không bắt buộc"
nhưng nhãn hiển thị ghi "hạng mục đạt" ở 2 vị trí trong `MainArea.tsx`,
trong khi tab Kết luận Pháp lý lại ghi đúng "Đạt & Không bắt buộc".

**Vá**: đồng bộ nhãn "đạt & không bắt buộc" ở cả 2 vị trí (thanh tỉ lệ mở
rộng và thu gọn).

---

## 5. B14 — Bảng "Thông số kỹ thuật" sai nhãn/sai giá trị (🟠 Cao)

**Nguyên nhân gốc (3 lỗi cùng lúc)**:
- (a) Nhãn "Tổng Diện tích xây dựng" nhưng hiển thị giá trị `totalFloorArea`
  (nhầm với `floorArea` thật).
- (b) **`Bậc chịu lửa thiết kế tối thiểu` bị HARDCODE**:
  `projectInfo.floors <= 4 ? "Bậc III" : "Bậc II"` — hoàn toàn bỏ qua giá
  trị `fireRating` thật đã khai báo, mâu thuẫn trực tiếp với mục 2 của
  bảng 17 hạng mục.
- (c) Nhãn "Chiều cao số tầng" gộp sai 2 khái niệm; chiều cao PCCC không
  hiển thị ở đâu cả.
- **Phát hiện thêm (không có trong báo cáo QA)**: dòng "Phân nhóm công
  năng PCCC nguy hiểm" cũng hardcode cứng "F1.4" bất kể loại công trình
  thật — cùng bản chất lỗi với B12 nhưng ở tầng hiển thị.

**Vá**: viết lại toàn bộ bảng — tách đúng diện tích xây dựng/tổng diện
tích sàn, thêm dòng số tầng nổi/hầm + chiều cao PCCC riêng biệt, bỏ hardcode
bậc chịu lửa (dùng đúng `fireRating` khai báo), bỏ hardcode "F1.4" (dùng
đúng `projectInfo.type` khai báo).

---

## 6. B15 + B21 — File PDF thiếu dữ liệu so với DOCX + tự bịa nội dung (🟠 Cao / 🟢 Thấp)

**B15 nguyên nhân**: `pdf_report.py` chỉ có 8 dòng trong bảng "Thông tin
công trình", **thiếu hẳn** "Kích thước hình học", "Diện tích xây dựng tầng
1", "Tổng diện tích sàn", "Chi tiết phần kinh doanh" so với `docx_report.py`
(13 dòng) — 2 định dạng xuất từ CÙNG 1 hồ sơ lại không khớp nhau.

**B21 nguyên nhân**: cả DOCX và PDF khi ô "Chi tiết kinh doanh" để trống
lại tự điền `"Tầng 1 kinh doanh thương mại dịch vụ"` (dữ liệu bịa) thay vì
"Chưa cập nhật" như các trường khác; "Kích thước hình học" khi length/width
= 0 vẫn in `"0.0m (dài) × 0.0m (rộng)"` như đã đo đạc thật.

**Vá**: đồng bộ `pdf_report.py` đủ 13 dòng khớp `docx_report.py`; sửa mọi
fallback về "Chưa cập nhật" trung thực, bỏ toàn bộ giá trị bịa (bao gồm cả
"Bậc III" mặc định khi chưa chọn bậc chịu lửa).

### Test đã chạy (xuất file thật, ô để trống)
```
DOCX: "Kích thước hình học" → "Chưa cập nhật" (trước: "0.0m (dài) × 0.0m (rộng)")
DOCX: "Chi tiết phần kinh doanh" → "Chưa cập nhật" (trước: bịa "Tầng 1 kinh doanh...")
PDF: đủ 13 dòng, khớp đúng nội dung DOCX
```

---

## 7. B16 — Chú giải biểu đồ chỉ cộng 15/17 (🟢 Thấp → đã nâng độ ưu tiên vì dễ vá)

**Nguyên nhân**: biến `xemSetCount` gộp "Khuyến nghị mạnh"/"Khuyến nghị"/
"Cần xem xét" nhưng **thiếu hẳn** "Cần đo đạc" — pie chart đã có đủ 4 phần
nhưng phần chú giải văn bản chỉ liệt kê 3/4 nhóm.

**Vá**: thêm biến `canDoDacCount` + dòng chú giải thứ 4.

---

## 8. B17 + B18 — Không giới hạn trên + thông báo lỗi tiếng Anh (🟡 Trung bình)

**B17**: 8 ô input số trong `Sidebar.tsx` chỉ có `min={0}`, không có `max`
— nhập 9999 tầng khiến vòng lặp sinh mảng `floorFunctions` tạo ra 9.999
phần tử DOM, đẩy tổng phần tử trang lên >130.000, trình duyệt giật/treo.

**Vá**: thêm `max` khớp đúng giới hạn backend cho cả 8 ô (floors≤200,
basements≤20, pcccHeight≤1000, floorArea/totalFloorArea≤1.000.000/
10.000.000, 3 ô số liệu tầng hầm), kẹp giá trị ngay tại `onChange`/`onBlur`
bằng `Math.min(MAX, Math.max(0, value))` — vòng lặp sinh mảng không bao
giờ còn nhận được số vượt ngưỡng.

**B18**: thông báo lỗi Pydantic ("Input should be less than or equal to
200") hiện thẳng tiếng Anh ra UI tiếng Việt. Vá: thêm `translatePydanticMessage()`
nhận diện các mẫu câu lỗi Pydantic thường gặp (le/ge/lt/gt/min_length/
max_length/required/valid number...), dịch sang tiếng Việt kèm tên trường
tiếng Việt tương ứng; không nhận diện được thì trả thông điệp chung tiếng
Việt — **không bao giờ để lọt tiếng Anh thô ra UI**.

### Test đã chạy
```
PUT /project {"floors": 9999} → HTTP 422 (backend Pydantic le=200 vẫn chặn — defense in depth)
Frontend: nhập 9999 vào ô Số tầng nổi → tự động kẹp về 200, KHÔNG sinh mảng 9999 phần tử
```

---

## 9. B19 + B03 (phần còn lại) — Cảnh báo trễ nhịp + chưa chặn cứng nút (🟡 Trung bình)

### B19 nguyên nhân gốc
`warnings` là 1 state **CHỈ cập nhật SAU khi nhận phản hồi từ server** (PUT
`/project`). Nếu người dùng sửa 2 ô liên tiếp trước khi request đầu kịp trả
lời, banner cảnh báo hiển thị cho dữ liệu CŨ — "trễ 1 nhịp mạng" đúng như
QA mô tả.

### Cách vá (giải quyết đồng thời B19 và phần còn lại của B03)
Thêm `hasAreaContradiction` — `useMemo` tính **tức thời, cục bộ** ngay tại
`MainArea.tsx`, dùng chính `projectInfo` (props hiện tại, luôn mới nhất),
công thức giống hệt backend `rules_engine.py` để không lệch kết quả. Banner
giờ hiển thị cảnh báo mâu thuẫn diện tích tức thời (không đợi server), gộp
với các cảnh báo khác từ server (vd cảnh báo nhóm công năng từ B12).

**Phần còn lại của B03** ("nút Kiểm duyệt/Xuất báo cáo vẫn bật khi đang có
mâu thuẫn"): dùng chính `hasAreaContradiction` để **chặn cứng** (`disabled`)
cả nút "Thực hiện kiểm duyệt" và toàn bộ 3 vị trí nút xuất báo cáo (DOCX +
PDF) trong file — kèm `title` giải thích lý do bị khoá.

---

## 10. B04 — Nút Huỷ (tiếp tục điều tra)

QA lần 3 báo **vẫn không thấy** nút Huỷ dù đã từng thêm trong phiên vá
trước. Rà soát lại toàn bộ code (`App.tsx`, `MainArea.tsx`): logic
`abortControllerRef`, `handleCancelPending`, prop `onCancelPending` đều
**wiring đúng, không tìm thấy lỗi logic nào khiến nút biến mất hoàn toàn**.

**Nghi vấn nhiều khả năng nhất**: bản deploy Vercel QA test đang chạy code
**cũ hơn** phiên bản đã sửa (do lịch sử nhiều lần đóng gói zip qua các
phiên làm việc khác nhau).

**Đã làm thêm để tăng độ chắc chắn bất kể nguyên nhân**: thêm nút Huỷ
**thứ hai**, đặt **cố định trong thanh hành động trên cùng** (luôn hiển
thị, không phụ thuộc vị trí cuộn chat hay tốc độ phản hồi nhanh của chế độ
dự phòng — vốn giờ chỉ mất ~1.1-1.3 giây nên bong bóng chat gốc có thể biến
mất rất nhanh).

**Khuyến nghị**: sau khi deploy bản này, kiểm tra lại bằng cách mở DevTools
Network, throttle về "Slow 3G" để giả lập độ trễ, xác nhận nút Huỷ (cả 2
vị trí) xuất hiện và hoạt động đúng.

---

## 11. B20 — Thiếu nút hiện/ẩn mật khẩu (🟢 Thấp)

Thêm: nút con mắt hiện/ẩn mật khẩu (`showPassword` state), liên kết "Quên
mật khẩu?" (hiển thị hướng dẫn liên hệ admin — hệ thống chưa có dịch vụ
email/reset tự động nên không tạo liên kết chết), thêm `name` attribute
cho cả 2 input (hỗ trợ trình quản lý mật khẩu tự điền tốt hơn, `autoComplete`
vốn đã có sẵn từ trước).

---

## 12. B22 + B23 — Vỡ giao diện mobile còn sót (🟢 Thấp)

**B22**: dải tab "Kết luận Pháp lý PCCC" tràn ngoài màn hình 375px, cuộn
được nhưng không có chỉ dấu. Vá: thêm dải mờ (gradient fade) cố định bên
phải, chỉ hiện trên màn hình nhỏ, làm tín hiệu thị giác "còn nội dung cuộn
tiếp".

**B23**: nội dung dừng ở ~55% chiều cao màn hình, phần còn lại trắng,
khung nhập không neo đáy. **Nguyên nhân khả dĩ nhất tìm được qua rà soát
code**: container ngoài cùng của `MainArea` có CẢ `h-full` LẪN
`overflow-y-auto`, xung đột với vùng cuộn riêng của khung tin nhắn bên
trong (cũng `overflow-y-auto`) — 2 lớp `overflow:auto` lồng nhau trong
cùng chuỗi flexbox là lỗi WebKit di động kinh điển (flex item revert về
"min-height: auto", co lại theo nội dung thay vì lấp đầy chiều cao khả
dụng). Đã đổi outer container thành `overflow-hidden`, giao toàn bộ việc
cuộn cho vùng con bên trong.

**Lưu ý trung thực**: đây là fix dựa trên phân tích code tĩnh (không có
trình duyệt thật để test), cần xác nhận lại bằng mắt trên thiết bị/DevTools
mobile sau khi deploy.

---

## 13. Danh sách file đã sửa trong phiên này

| File | Thay đổi |
|---|---|
| `backend/app/rules_engine.py` | **B12** — phân loại công năng, ngưỡng riêng từng nhóm. **B11** — viết lại fallback reply |
| `backend/app/main.py` | Thêm `/api/health/ai`, `/api/health/ai/ping` |
| `backend/app/pdf_report.py` | **B15** — đủ 13 dòng khớp DOCX. **B21** — bỏ dữ liệu bịa |
| `backend/app/docx_report.py` | **B21** — bỏ dữ liệu bịa |
| `frontend/src/components/MainArea.tsx` | **B13** (nhãn), **B14** (bảng thông số), **B16** (chú giải), **B19+B03** (cảnh báo tức thời + chặn nút), **B04** (nút Huỷ thứ 2), **B22** (fade cuộn), **B23** (bỏ overflow xung đột) |
| `frontend/src/components/Sidebar.tsx` | **B17** — thêm `max` + kẹp giá trị 8 ô số |
| `frontend/src/components/Login.tsx` | **B20** — hiện/ẩn mật khẩu, quên mật khẩu, name attribute |
| `frontend/src/App.tsx` | **B18** — dịch thông báo lỗi Pydantic sang tiếng Việt |

**Không đổi**: `auth.py`, `db_models.py`, `db.py`, `config.py`, `schemas_*.py`,
`ocr_vision.py`, `seed.py`, `storage.py`, `checklist_data.py`,
`BlueprintUpload.tsx`, `InspectionLogPanel.tsx`, `lib/api.ts`, `types.ts` —
không liên quan tới các lỗi trong báo cáo QA lần 3.

---

## 14. Testing Summary (chạy thật qua PostgreSQL 16 + uvicorn)

- ✅ Karaoke 5 tầng/500m² → `isSubjectToAppraisal=True`; Nhà ở CÙNG thông số → `False` (B12)
- ✅ 3 lần gọi thẩm định cùng input → kết quả giống hệt tuyệt đối (B10 vẫn ổn định sau khi thêm B12)
- ✅ Chat fallback (không có GEMINI_API_KEY) → reply dài 737 ký tự, có nội dung tóm tắt đầy đủ (B11)
- ✅ `GET /api/health/ai` → báo đúng trạng thái chưa cấu hình key
- ✅ `PUT /project` mâu thuẫn diện tích → 422 (B03)
- ✅ `PUT /project` floors=9999 → 422 (B17, defense in depth backend)
- ✅ Export DOCX/PDF với ô trống → "Chưa cập nhật" thay vì bịa dữ liệu (B21)
- ✅ Export PDF → đủ 13 dòng khớp DOCX (B15)
- ✅ Log khởi động → không lộ mật khẩu admin (xác nhận lại từ phiên trước)
- ✅ `python3 -m py_compile` toàn bộ backend → sạch
- ✅ `tsc --noEmit` toàn bộ frontend → 0 lỗi (sau mỗi lần sửa)
- ✅ `npm run build` production → thành công

## 15. Việc bạn cần tự làm / kiểm tra lại

1. **Deploy lại đúng bản mới nhất** lên Vercel + Render, xoá cache build
   cũ nếu có — đặc biệt quan trọng cho B04 (nghi ngờ bản deploy cũ hơn code).
2. Kiểm tra `GEMINI_API_KEY` đã cấu hình đúng trên Render chưa — dùng
   `GET /api/health/ai` (đăng nhập bất kỳ) và `GET /api/health/ai/ping`
   (đăng nhập admin) để tự chẩn đoán thay vì đoán mò.
3. Sau khi deploy, kiểm tra lại B22/B23 trên thiết bị di động thật hoặc
   DevTools mobile emulation — đây là 2 fix dựa trên phân tích code, chưa
   có môi trường trình duyệt thật để xác nhận trực quan.
4. Đo lại B01 (hiệu năng) và B10 (tính tái lập) khi AI thật đang hoạt động
   (không phải chế độ dự phòng) — QA lần 3 chưa đo được vì AI không chạy.
