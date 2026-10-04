# Báo cáo Fix — "Bất đồng bộ hiển thị" / "Bất đồng bộ kết luận" (theo ảnh chụp)

Người dùng gửi 2 ảnh chụp từ hồ sơ thật ("QA Karaoke 5 tầng") phát hiện 2 lỗi
hiển thị mâu thuẫn nhau. Rà soát xác định cả 2 lỗi cùng chung 1 gốc rễ.

---

## Gốc rễ chung

Fix B12 (phiên trước — phân loại công năng karaoke/vũ trường để tính đúng
ngưỡng thẩm duyệt) chỉ sửa **mục 1** và **mục 9** trong 17 hạng mục. Các
mục khác (đặc biệt **mục 12 — sprinkler**) vẫn chỉ tính theo ngưỡng chung
(chiều cao ≥30m) như nhà hỗn hợp thông thường, trong khi AI (Gemini) — nay
hoạt động thật trong môi trường của người dùng — trả về ghi chú đúng theo
kiến thức thật: karaoke có ngưỡng bắt buộc sprinkler RIÊNG, thấp hơn hẳn
30m, theo Thông tư 147/2020/TT-BCA. Hai nguồn dữ liệu (note của AI và
result tính cứng) không khớp nhau → hiển thị mâu thuẫn.

## Lỗi 1 (ảnh 1): "1/17 đạt 6%" nhưng bảng không có mục nào ghi "Đạt"

**Nguyên nhân:** mục 12 bị tính sai thành "Không bắt buộc" (do chỉ xét
pcccHeight=18m < 30m, chưa biết là karaoke), khiến bộ đếm "Đạt & Không bắt
buộc" đếm nhầm 1 mục — dù mục đó thực chất không phải "Đạt", chỉ là
"Không bắt buộc" bị tính sai.

**Đã vá:** sau khi sửa mục 12 (bên dưới) thành đúng "Không đạt" cho
karaoke, bộ đếm tự động trở về 0/17 — khớp chính xác với những gì bảng
17 mục hiển thị. Không cần sửa riêng logic đếm, vì logic đó vốn đã đúng
— chỉ dữ liệu đầu vào (result của mục 12) bị sai.

## Lỗi 2 (ảnh 2): Mục 12 — "Kết luận chi tiết" ghi "bắt buộc" nhưng "Đánh giá" ghi "Không bắt buộc"

**Nguyên nhân:** như gốc rễ chung ở trên — `rules_engine.py` mục 12 chỉ có
2 nhánh: `pccc_height >= 30` (Không đạt) hoặc còn lại (Không bắt buộc),
không có nhánh riêng cho karaoke.

**Đã vá** (`backend/app/rules_engine.py`):
- **Mục 12 (sprinkler):** thêm điều kiện `category == "karaoke_entertainment"`
  — karaoke giờ LUÔN "Không đạt" (bắt buộc), khớp đúng Thông tư 147/2020/TT-BCA,
  bất kể chiều cao công trình.
- **Mục 11 (họng nước chữa cháy):** áp dụng cùng logic, chủ động vá trước
  khi lỗi tương tự xuất hiện ở công trình karaoke có chiều cao/diện tích
  nhỏ hơn ngưỡng chung (chưa xuất hiện trong ảnh chụp, nhưng cùng bản chất
  lỗi, cùng căn cứ pháp lý).

## Rà soát "các trường hợp tương tự" (theo đúng yêu cầu)

Đọc lại toàn bộ 17 mục, đối chiếu ngôn từ trong `note` (bắt buộc/yêu
cầu/phải — hàm ý mệnh lệnh) với `result` được chọn (Đạt/Không đạt/Không
bắt buộc/Khuyến nghị...). Phát hiện thêm 2 mục có cùng dạng bất đồng bộ
ngôn từ (ở mức nhẹ hơn, không phải do thiếu nhánh karaoke mà do lựa chọn
từ ngữ ban đầu quá mạnh so với result):

- **Mục 4** (tường ngăn cháy tầng 1): note cũ dùng "phải ngăn cách hoàn
  toàn..." nhưng result là "Khuyến nghị mạnh" — đã đổi note sang "Khuyến
  nghị... nên ngăn cách..." cho khớp đúng mức độ.
- **Mục 7** (đèn EXIT): note cũ dùng "Yêu cầu lắp..." nhưng result là
  "Khuyến nghị mạnh" — đã đổi thành "Khuyến nghị lắp...".
- **Mục 8** (bình chữa cháy xách tay): note cũ dùng "Bắt buộc trang bị..."
  nhưng result là "Khuyến nghị mạnh" — đã đổi thành "Khuyến nghị mạnh
  trang bị...".

Lý do KHÔNG đổi `result` của 3 mục này thành "Không đạt": hệ thống không
thu thập đủ dữ liệu đầu vào (có/không có tường ngăn cháy thật, đã lắp đèn
EXIT thật hay chưa, số bình chữa cháy thật) để khẳng định chắc chắn là
"Không đạt" — làm vậy sẽ là một dạng "bịa kết luận" khác (đã từng bị phát
hiện và vá ở các phiên trước: B21). Thay vào đó, softening ngôn từ của
`note` để khớp đúng mức độ chắc chắn mà hệ thống THỰC SỰ có.

## Lớp phòng vệ bổ sung (chống tái diễn cho các trường hợp CHƯA BIẾT)

Thêm 1 cơ chế kiểm tra chung trong `backend/app/main.py::_merge_checklist()`:
nếu `result` deterministic là "Không bắt buộc" nhưng `note` do AI trả về
chứa từ "bắt buộc" — tự động **không dùng note của AI** cho mục đó, fallback
về note deterministic (vốn luôn tự nhất quán với chính result của nó), đồng
thời ghi log cảnh báo để admin biết có mâu thuẫn tiềm ẩn.

**Mục đích:** bảo vệ cho MỌI công năng khác (không chỉ karaoke) và MỌI hạng
mục khác (không chỉ mục 11/12) — nếu trong tương lai AI trả về ghi chú
"bắt buộc" cho 1 hạng mục mà `rules_engine.py` chưa từng được dạy riêng cho
loại công trình đó, hệ thống sẽ tự động ẩn note gây hiểu nhầm thay vì hiển
thị mâu thuẫn ra màn hình — đúng tinh thần "kiểm tra hết các trường hợp có
thể xảy ra tương tự" mà không cần liệt kê trước từng trường hợp cụ thể.

---

## Test đã chạy (thật, không suy đoán)

### 1. Đúng kịch bản trong ảnh chụp (unit test trực tiếp)
```
Input: Karaoke, 5 tầng, 18m PCCC, Bậc III, 100m²/tầng, 500m² tổng

Mục 12 — Result: Không đạt
Mục 12 — Note: "Karaoke/vũ trường BẮT BUỘC trang bị hệ thống chữa cháy tự động
                Sprinkler cho toàn bộ các phòng hát..." 
Đồng bộ đúng (Không đạt + note nói "bắt buộc")? → True

Đếm lại "Đạt & Không bắt buộc": 0 / 17  (khớp đúng những gì bảng 17 mục hiển thị)
```

### 2. Lớp phòng vệ chung — kịch bản HOÀN TOÀN giả định (chợ dân sinh, không phải karaoke)
```
Giả lập AI trả note "BẮT BUỘC" cho 1 mục (mục 9) mà rules_engine tính "Không bắt buộc"
→ Lớp phòng vệ TỰ ĐỘNG chặn, fallback về note deterministic, có log cảnh báo
→ Đã CHẶN đúng note mâu thuẫn? True
```

### 3. Regression — qua API thật (PostgreSQL + uvicorn)
```
Đúng kịch bản karaoke trong ảnh qua API → mục 12 "Không đạt" đúng, 0/17 đúng
B10 (3 lần chạy cùng input) → kết quả giống hệt nhau tuyệt đối
Nhà ở kết hợp kinh doanh (KHÔNG phải karaoke, cùng 18m) → mục 12 vẫn "Không bắt buộc"
  (xác nhận fix CHỈ áp dụng cho karaoke, không ảnh hưởng các loại hình khác)
Export DOCX/PDF → vẫn hoạt động bình thường (200)
```

### 4. Build & cú pháp
```
python3 -m py_compile app/*.py → sạch
tsc --noEmit → 0 lỗi (không có thay đổi frontend trong đợt fix này)
npm run build → thành công
```

---

## Danh sách file đã sửa

| File | Thay đổi |
|---|---|
| `backend/app/rules_engine.py` | Mục 12 (sprinkler) + mục 11 (họng nước): thêm nhánh `category == "karaoke_entertainment"`. Mục 4, 7, 8: softening ngôn từ note cho khớp result |
| `backend/app/main.py` | `_merge_checklist()`: thêm lớp phòng vệ chung chặn note AI mâu thuẫn với result "Không bắt buộc" |

**Không đổi:** toàn bộ frontend, các file backend khác — lỗi hoàn toàn nằm
ở tầng tính toán dữ liệu (rules_engine), không phải tầng hiển thị.

## Cập nhật nhanh (chỉ 2 file, vá tối thiểu)

Nếu bạn chỉ cần vá đúng 2 lỗi trong ảnh mà không cần tải lại toàn bộ dự án:
1. Copy đè `backend/app/rules_engine.py`
2. Copy đè `backend/app/main.py`
3. Khởi động lại backend (`docker compose restart backend` hoặc chạy lại uvicorn)

Không cần build lại frontend (không có thay đổi).
