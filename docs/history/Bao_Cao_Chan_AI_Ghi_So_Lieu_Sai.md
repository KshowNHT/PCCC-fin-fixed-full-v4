# Báo cáo: chặn AI ghi số liệu sai vào hồ sơ và nói ngược kết luận

## Vấn đề

Sau đợt sửa trước, kết luận thẩm duyệt được tính chính xác từ số liệu hồ sơ. Nhưng số liệu đó vẫn có thể sai
vì hai chỗ chưa được kiểm soát:

1. **Số liệu do AI trích xuất** (`extractedProjectInfo`) đi thẳng vào DB qua `apply_dict()`, bỏ qua cả luật khoảng
   giá trị và luật diện tích của API. AI có thể bịa số tầng, ghi đè số người dùng đã nhập, hoặc đổi loại công trình
   (ví dụ thành karaoke, làm kết luận chuyển sang "bắt buộc"). Kết luận khi đó đúng trên số liệu sai.
2. **Câu trả lời chat của AI** chỉ được dặn qua prompt. Không có gì ngăn nó nói "vượt ngưỡng" khi 5 < 7, hoặc nói
   "không thuộc diện" khi hệ thống kết luận "bắt buộc". Cảnh báo (`warnings`) do AI viết cũng đi thẳng vào hồ sơ.

## Cách xử lý

Mọi dữ liệu AI sinh ra đi qua một điểm duy nhất, `_apply_ai_outputs()` trong `main.py`, dùng module mới
`app/ai_guard.py`.

**Số liệu trích xuất.** Một giá trị AI muốn thay đổi hồ sơ chỉ được ghi khi:

- đúng kiểu và nằm trong khoảng hợp lệ, và qua luật liên trường của `ProjectUpdateRequest` (cùng schema với API nhập tay);
- xuất hiện trong lời người dùng (kể cả dạng `1.200`, `12,5m`, "năm tầng", "mười hai tầng"). Ngoại lệ duy nhất:
  tổng diện tích sàn bằng đúng số tầng × diện tích một tầng, khi đó được nhận kèm ghi chú "do AI tính, hãy kiểm tra";
- loại công trình thay đổi chỉ khi người dùng nhắc tới nhóm đó, và được chuẩn hóa về đúng giá trị trong dropdown;
- công năng từng tầng chỉ nhận giá trị trong danh sách của giao diện (chữ viết tự do được ánh xạ về giá trị gần nhất,
  không nhận diện được thì bỏ cả danh sách); tầng karaoke cần người dùng nhắc tới;
- thông tin mô tả (tên, địa điểm, chủ đầu tư...) chỉ được điền khi đang trống, không bao giờ ghi đè.

Giá trị bị bỏ qua được ghi vào cảnh báo của hồ sơ và vào cuối câu trả lời ("Một số số liệu AI đề xuất chưa được ghi
vào hồ sơ: ..."), nên người dùng biết số nào chưa được áp dụng.

**Câu trả lời và cảnh báo của AI.** Câu nào mâu thuẫn với `appraisalBasis` bị lược bỏ, kèm một dòng nêu kết luận
chính thức. Các loại mâu thuẫn được bắt: nói "bắt buộc/không bắt buộc thẩm duyệt" trái kết luận; nói "vượt/đạt
ngưỡng" khi không có ngưỡng nào đạt (đúng lỗi trong ảnh), hoặc "dưới ngưỡng" khi đã có ngưỡng đạt; nêu sai số tầng
hoặc tổng diện tích sàn của công trình. Câu giả định ("nếu vượt 7 tầng thì...") và câu nêu sự chưa chắc chắn không
bị coi là khẳng định. Câu về ngưỡng thiết bị ("dưới ngưỡng bắt buộc trang bị họng nước") không bị so với ngưỡng
quy mô thẩm duyệt.

**OCR bản vẽ** (`/api/ocr/extract-drawing`) cũng đi qua bộ lọc khoảng giá trị và luật diện tích. Phản hồi có thêm
trường `rejectedFields`. Giao diện hiện chưa hiển thị trường này.

## Lỗi tìm thấy trong quá trình viết test

Fuzz tính chất phát hiện hai lỗi thật trong chính module mới, đều là lỗi phụ thuộc thứ tự xử lý:

1. Tổng diện tích "5 tầng × 100 m²" được nhận trước khi số "5 tầng" bị loại vì không có trong lời người dùng.
2. Tổng diện tích suy ra từ số tầng "500" đã được nhận trước khi số tầng này bị loại vì vượt khoảng cho phép.

Cả hai được sửa bằng cách kiểm tra luật dữ liệu trước và sau bước đối chiếu căn cứ, và xét các trường gốc trước,
trường suy ra sau. Fuzz cũng phát hiện bộ kiểm tra câu trả lời bắt nhầm chính câu của hệ thống ("Dưới ngưỡng bắt
buộc trang bị họng nước"); đã sửa bằng cách bỏ các câu về thiết bị khỏi phép so ngưỡng quy mô.

## Kiểm thử

| Lớp | Nội dung | Kết quả |
|-----|----------|---------|
| Số liệu AI | 37 ca viết tay (số bịa, ghi đè, âm, ngoài khoảng, không nguyên, số chữ, tổng suy ra, vi phạm luật diện tích, bậc chịu lửa, loại công trình, công năng tầng, OCR...) | 0 lỗi |
| Câu trả lời AI | 22 ca (đúng lỗi trong ảnh, giả định, thiếu số liệu, markdown nhiều dòng, nêu sai số tầng/diện tích...) | 0 lỗi |
| Fuzz tính chất | 4.000 đầu vào AI ngẫu nhiên kiểm tra các bất biến; 4.000 hồ sơ kiểm tra hệ thống không tự bắt lỗi câu chữ của mình | 0 lỗi |
| Kiểm thử đột biến | Tiêm 10 lỗi vào `ai_guard.py` (bỏ đối chiếu căn cứ, bỏ luật dữ liệu, cho ghi đè, tắt kiểm tra "vượt ngưỡng"...) | bắt được 10/10 |
| Tích hợp | AI giả lập "xấu" qua API thật + PostgreSQL thật, 5 kịch bản, 25 kiểm tra (chat, nút Kiểm duyệt, lịch sử hội thoại) | 0 lỗi |
| Hồi quy | Toàn bộ bộ test của đợt trước: 43 kịch bản, fuzz, e2e API, PDF/Word, giao diện jsdom, race condition | 0 lỗi |

## Giới hạn còn lại

1. **Đối chiếu căn cứ chỉ ở mức con số, không ở mức ý nghĩa.** Nếu người dùng viết "500 m2" và AI gán 500 vào
   diện tích một tầng thay vì tổng diện tích sàn, giá trị vẫn được nhận vì con số có trong lời. Tương tự với nhầm
   đơn vị. Bộ lọc không thể phân biệt hai trường hợp này.
2. **Bộ kiểm tra câu trả lời dựa trên mẫu câu tiếng Việt.** Nó bắt các cách nói phổ biến, không bắt mọi cách diễn
   đạt khác đi. Nguồn kết luận chính thức vẫn là banner và báo cáo, không phụ thuộc vào câu trả lời chat.
3. **Chưa thử với Gemini thật.** Mọi test dùng AI giả lập trả dữ liệu theo kịch bản. Cách AI thật diễn đạt có thể
   lộ thêm mẫu câu chưa được xử lý; log của server có dòng `[ai_guard]` mỗi lần bộ lọc hành động, nên xem chúng sau
   vài ngày chạy thật.
4. **Hành vi thay đổi.** AI không còn tự điền số người dùng chưa nói. Một số lượt chat trước đây tự điền hồ sơ giờ
   sẽ để trống và hỏi lại. Đây là chủ ý.

## File thay đổi

Backend: `app/ai_guard.py` (mới), `app/main.py`, `tests/test_ai_guard.py` (mới),
`tests/test_ai_guard_integration.py` (mới). Gốc: `scripts/run_all_tests.sh`, `README.md`.

## Cập nhật nhanh

1. Chép đè các file trên (giữ nguyên `.env`).
2. `docker compose up -d --build`.
3. Sau vài ngày chạy thật, xem log server tìm `[ai_guard]` để biết bộ lọc đã chặn gì.
