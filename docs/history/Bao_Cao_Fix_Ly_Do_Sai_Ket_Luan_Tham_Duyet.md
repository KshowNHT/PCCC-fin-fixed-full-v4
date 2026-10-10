# Báo cáo sửa lỗi: kết luận "bắt buộc thẩm duyệt" nhưng lý do sai

## Hiện tượng (theo ảnh chụp)

Hồ sơ "Kiem lai 2": karaoke, 5 tầng nổi, 500 m², cao 18 m. Màn hình Kết luận pháp lý báo đúng
"BẮT BUỘC THẨM DUYỆT", nhưng khối "Lưu ý pháp lý" bên dưới lại hiện ngưỡng 7 tầng / 3.000 m² của nhóm
nhà hỗn hợp (F1.4) và câu "công trình của bạn ĐẠT HOẶC VƯỢT một trong các ngưỡng". Thực tế 5 < 7 và
500 < 3.000 nên câu này sai.

## Nguyên nhân gốc

Khối đó do giao diện (`MainArea.tsx`) tự viết cứng, không lấy từ backend. Nó chọn câu bằng
`isSubjectToAppraisal ? "đạt hoặc vượt" : "dưới ngưỡng"`, tức là giả định mọi hồ sơ bắt buộc thẩm duyệt đều
do vượt ngưỡng quy mô. Karaoke bắt buộc vì công năng nên luôn rơi vào nhánh sai. Khối này có hai bản sao.
Nhánh "không bắt buộc" cũng sai với kho, chợ, trường học (ngưỡng khác) và với hồ sơ chưa nhập số liệu.

## Cách sửa

Backend là nơi duy nhất quyết định. Hàm `build_appraisal_basis()` (file mới `appraisal_basis.py`) trả về
`appraisalBasis`: nhóm công năng, từng ngưỡng kèm giá trị thực, ngưỡng nào đã đạt, trường còn thiếu, lý do,
câu kết luận. Mọi nơi dùng chung nguồn này: banner, mục 1 của checklist, chat dự phòng, báo cáo Word/PDF,
và khối "Căn cứ pháp lý" mới (`LegalBasisPanel.tsx`). Giao diện không còn chứa con số ngưỡng hay câu pháp
lý nào.

Kết luận có 3 trạng thái thay cho 2: `required`, `not_required`, `insufficient_data`.

## Các lỗi cùng loại tìm thêm

| # | Lỗi | Sửa |
|---|-----|-----|
| 1 | Form chỉ có ô "Chiều cao PCCC", nhưng mục 11 và ngưỡng kho đọc `height` (luôn 0 khi nhập từ form) | Dùng chiều cao PCCC, nếu trống thì lấy `height` |
| 2 | Gara ô tô, nhà máy, rạp hát chọn trong dropdown vẫn bị xếp "chưa xác định"; văn phòng/khách sạn bị gắn nhãn F1.4 | Khớp tuyệt đối 10 giá trị dropdown; nhóm chưa có ngưỡng riêng được ghi rõ là "tham chiếu" |
| 3 | "tạp hóa đối diện trường học", "gần chợ" làm nhà ở bị xếp thành trường học/chợ | Chi tiết kinh doanh chỉ dùng khi loại công trình chưa xác định, và đã lọc phần "gần/đối diện/cạnh/không..." |
| 4 | Karaoke chọn ở "công năng từng tầng" bị bỏ qua | Một tầng karaoke là đủ để nâng cả công trình lên nhóm karaoke (an toàn hơn bỏ sót) |
| 5 | Thiếu số tầng/diện tích vẫn kết luận "không bắt buộc" | Trả "chưa đủ thông số" và nêu trường thiếu. Nếu một ngưỡng đã đạt thì vẫn kết luận được |
| 6 | Bậc chịu lửa "Chưa lựa chọn" bị chấm "Không đạt" | Chấm "Cần xem xét" |
| 7 | Hồ sơ lưu từ bản cũ giữ nguyên lý do sai trong DB | `_session_to_dict` tính lại khi đọc nên tự sửa |
| 8 | Word/PDF chỉ có 2 tiêu đề, hồ sơ thiếu số liệu bị in "KHÔNG THUỘC DIỆN" | Tiêu đề 3 trạng thái và dòng "Căn cứ áp dụng" |
| 9 | Ghi chú AI ở mục 1, 2, 9, 10, 11, 12 có thể nói ngược kết quả | Các mục phụ thuộc số liệu luôn dùng ghi chú tính cứng. Mục còn lại chặn ghi chú AI mâu thuẫn hai chiều |
| 10 | Prompt Gemini không biết kết luận hệ thống nên phần chat có thể nói "vượt ngưỡng" | Kết luận được đưa vào prompt như ràng buộc |
| 11 | Thẻ "Công năng nguy hiểm cháy: F1.4" và "Bậc chịu lửa yêu cầu" viết cứng | Lấy từ `appraisalBasis` |

## Thay đổi hành vi mà người dùng sẽ thấy

- Nhà có chiều cao PCCC trên 12 m giờ thấy mục 11 (họng nước) "Không đạt" dù trước đây hiện "Khuyến nghị".
- Hồ sơ thiếu số liệu thấy nhiều mục "Cần xem xét" hơn và thanh "đạt & không bắt buộc" thấp hơn.
- Nhóm kho, chợ, trường học, gara, nhà máy, rạp hát, văn phòng/khách sạn kèm cảnh báo cần kỹ sư PCCC rà soát.

## Kiểm thử

Chạy toàn bộ bằng `bash scripts/run_all_tests.sh`. Kỳ vọng của từng kịch bản được suy luận tay từ luật,
không sao chép từ kết quả chạy.

| Lớp | Nội dung | Kết quả |
|-----|----------|---------|
| Backend | 43 kịch bản (biên 6/7 tầng, 2.999/3.000 m², từng nhóm công năng, thiếu số liệu, chuỗi OCR, từ khóa nhầm) | 0 lỗi |
| Backend | 13 bất biến kiểm tra chéo trên mọi kịch bản | 0 lỗi |
| Backend | Fuzz 3.000 hồ sơ ngẫu nhiên (gồm None, chuỗi, NaN, số âm) | 0 lỗi, không ngoại lệ |
| Backend | Kiểm thử đột biến: tiêm lại 8 lỗi (gồm lỗi trong ảnh) | bắt được 8/8 |
| Giao diện | Render `MainArea` thật trong jsdom, bấm tab Kết luận, 7 nhóm kịch bản | 0 lỗi |
| Giao diện | Cùng test chạy trên bản v8 cũ | 16 lỗi, gồm đúng lỗi trong ảnh |
| API thật | 43 kịch bản qua PUT /project (PostgreSQL + uvicorn) | 0 lỗi |
| API thật | Hồ sơ cũ tự sửa, chat dự phòng, Word, PDF 3 trạng thái, 422, dữ liệu giả mạo | 0 lỗi |
| API thật | Hồi quy: 15 request tạo tài khoản đồng thời (tổng 10), 3 lần thẩm định giống hệt | 0 lỗi |
| Build | `tsc --noEmit`, `npm run build`, `py_compile` | sạch |

Script riêng cho API thật: `backend/tests/api_e2e.py` và `backend/tests/api_regression.py` (cần backend và
PostgreSQL đang chạy; xem đầu mỗi file).

## Giới hạn cần biết trước khi giao khách

1. Ngưỡng cho kho (1.000 m² hoặc cao 25 m), chợ (1.500 m² hoặc 3 tầng), trường học (3 tầng hoặc 1.500 m²)
   là ngưỡng thận trọng do hệ thống đặt, không phải ngưỡng pháp định. Giao diện đã ghi rõ.
2. Việc áp Thông tư 147/2020/TT-BCA cho karaoke ("bắt buộc bất kể quy mô") là lựa chọn an toàn của hệ
   thống. Nên nhờ chuyên gia pháp lý PCCC xác nhận câu chữ trước khi bàn giao.
3. Test giao diện chạy trên jsdom, chưa chạy trên trình duyệt thật. Phần Gemini thật và Docker thật chưa được
   thử trong môi trường kiểm thử này (không có API key, không có Docker).
4. Khối "compact" trong `MainArea.tsx` là mã chết (`{false && ...}`); màn hình đang chạy là bản "full".
   Cả hai đều đã được vá cho đồng nhất.

## File thay đổi

Backend: `app/appraisal_basis.py` (mới), `app/rules_engine.py`, `app/main.py`, `app/gemini_client.py`,
`app/docx_report.py`, `app/pdf_report.py`, `tests/*` (mới).
Frontend: `src/components/LegalBasisPanel.tsx` (mới), `src/components/MainArea.tsx`, `src/App.tsx`,
`src/types.ts`, `tsconfig.json`, `tests/*` (mới).
Gốc: `scripts/run_all_tests.sh` (mới).

## Cập nhật nhanh

1. Chép đè các file trên vào dự án hiện có (giữ nguyên `.env`).
2. `docker compose up -d --build` (không cần đổi `.env` hay `compose.yaml`).
3. Mở lại một hồ sơ karaoke cũ để kiểm tra: lý do phải ghi "bất kể quy mô".
