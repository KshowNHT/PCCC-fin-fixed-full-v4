> Báo cáo lịch sử v11.2. Bản hiện hành và quy định thay thế: RA_SOAT_V11_3.md.

# Rà soát v11.2 — 08/10/2026

## Yêu cầu đã triển khai

- Nhập/sửa thông số chỉ là bản nháp. Không gọi rules/LLM pháp lý trước nút Kiểm duyệt.
- Ô đang nhập chưa blur cũng đánh dấu draft ngay, ẩn kết luận/checklist cũ.
- Nút Kiểm duyệt blur ô nhập cuối, chờ hàng đợi lưu, chặn nếu lưu lỗi; chạy quy tắc
  đã xác minh và lưu kết quả gắn với fingerprint dữ liệu đầu vào.
- GET/list/chat không tự chạy lại rà soát. Chat không trích số liệu để sửa form.
  Bản chưa kiểm duyệt trả hướng dẫn; câu hỏi chưa có quy tắc trả thông báo thiếu căn cứ.
- Sửa/áp dụng OCR xóa xác nhận kiểm duyệt. Xuất Word/PDF/JSON từ draft nhận 409.
  Hồ sơ cũ không có marker xác nhận mới trở về draft, giữ thông số và lịch sử.
- Không tìm được quy tắc phù hợp thì hiện “Không tìm thấy quy định phù hợp trong
  bộ quy tắc đã xác minh”, không bịa ngưỡng/trích dẫn/kết luận. Các mục kỹ thuật
  chưa hỗ trợ không ghi QCVN/TCVN như thể đã đối chiếu. Không suy ra pháp luật không có quy định.
- Không dùng LLM tự do để tạo kết luận pháp lý. Gemini chỉ dùng OCR; OCR vẫn cần
  người kiểm tra số liệu và phạm vi từng nhà/hạng mục trước khi áp dụng.
- Bỏ mặc định bậc chịu lửa III, loại nhà hỗn hợp/nhà kết hợp kinh doanh, công năng
  tầng là nhà ở, công năng hầm là bãi đỗ xe và chiều cao hầm 3,3 m khi chưa nhập.
  OCR “0 hầm” được phép thay số cũ và xóa mảng thông số hầm cũ.
- Báo cáo Word bỏ câu “Bộ luật PCCC” gắn chung mọi hồ sơ và giai đoạn thiết kế
  tự điền. Word/PDF của nhóm chưa hỗ trợ cũng có thông báo thiếu quy định phù hợp.

## Chống mất đồng bộ giữa tab / đăng nhập

Server tạo revision từ timestamp UTC và thông số hồ sơ. Sau kiểm tra quyền và
khóa giao dịch theo session, so khớp If-Match cho cập nhật/xóa/chat/kiểm duyệt/
OCR ghi trực tiếp, hoặc expectedRevision trong body xuất báo cáo. Khi khác trả
412 trước khi ghi/AI, thiếu revision ở production trả 428. Không tự retry bản cũ.
Có nút Tải lại hồ sơ để người dùng chủ động bỏ draft và xem bản mới.
Development cho phép API test/legacy không gửi revision; production bắt buộc.
Không có push realtime; optimistic concurrency chặn ghi từ bản cũ, không phải
hợp nhất cộng tác tự động. Atomicity với PostgreSQL cần test tại staging.

Đã chặn cả phản hồi và body đang stream của token cũ. Handler đang chờ lưu
không khởi chạy bằng token đăng nhập mới. Finalizer cũ không mở khóa thao tác
của người đăng nhập sau. Các ca HTTP/body stream dùng fetch giả lập để tái hiện.

## Migration

Migration dùng một transaction ngoài và pg_advisory_xact_lock để các tiến trình
khởi động không cùng áp migration. Sau migration kiểm tra bảng/cột ORM cần có;
thiếu cột chặn khởi động thay vì để API lỗi khi khách hàng sử dụng. Đây là kiểm
tra cấu trúc tối thiểu, không chứng minh mọi kiểu dữ liệu/index/chất lượng dữ liệu
cũ đều đúng. Đã chạy tạo mới/chạy lại/giữ dữ liệu và từ chối schema lỗi trên SQLite.
Chưa chạy PostgreSQL thật; không suy transactional DDL của PostgreSQL từ SQLite.

## Kiểm thử mới tiếp nối v11.1

| Ca | Kiểm chứng | Kết quả |
|---|---|---|
| S15 | Tab cũ không ghi đè hoặc xóa hồ sơ đã đổi | PASS |
| S16 | Thẩm định/chat/export/OCR dùng revision cũ bị chặn trước AI | PASS |
| S17 | Production yêu cầu revision, kiểm tra quyền trước khi lộ xung đột | PASS |
| S18 | Tạo/lưu/GET/list/chat bản nháp không gọi rules hoặc LLM | PASS |
| S19 | Nút kiểm duyệt nhóm chưa hỗ trợ báo thiếu quy định, bỏ câu bịa AI | PASS |
| S20 | Sửa thông số mất xác nhận, xuất bị chặn đến lần kiểm duyệt mới | PASS |
| S21 | Áp dụng OCR chỉ cập nhật draft, không tạo đánh giá/log kiểm duyệt | PASS |
| S22 | Đang gõ chưa blur ẩn kết luận cũ và chặn xuất | PASS |
| S23 | Token đổi khi body đang stream không dùng dữ liệu tài khoản cũ | PASS |
| S24 | Tab kết luận của draft không có verdict/cảnh báo tính tự động | PASS |
| S25 | Công năng tầng/hầm chưa nhập không tự thành nhà ở/gara | PASS |
| S26 | OCR 0 hầm xóa số liệu/công năng hầm cũ, không tự rà soát | PASS |
| S27 | Migration tạo mới/chạy lại giữ dữ liệu | PASS |
| S28 | Schema cũ thiếu cột bị từ chối, dữ liệu mẫu giữ nguyên | PASS |
| S29 | Word/PDF thiếu quy tắc báo rõ, không bịa luật/giai đoạn | PASS |

40 ca gốc được cập nhật hai kỳ vọng OCR/chat theo yêu cầu mới, helper gọi
kiểm duyệt tường minh khi ca cần hồ sơ đã rà soát. Tổng: 55 ca backend, 12 ca
React orchestration/component và 2 ca migration = 69. Thêm 3.000 hồ sơ fuzz,
6 fixture kết luận React, TypeScript lint, build Vite production đều đạt.
Log đầy đủ: docs/qa/full-suite-v11-2.log; script: scripts/run_all_tests.sh.

## Giới hạn bàn giao

Chưa có rule kỹ thuật đã xác minh đủ để tự chấm toàn bộ 17 mục. Không tự diễn giải
mọi file pháp lý upload thành luật. Các nhóm/phạm vi chưa hỗ trợ cần kỹ sư xác
nhận. Đây là thiếu phạm vi chức năng thực tế, không thể khắc phục bằng cách
nhờ AI tạo câu trả lời nghe thuyết phục.

Docker build, migration bản sao PostgreSQL thật, HTTPS/hosting, phục hồi backup,
quyền volume và OCR tài liệu gốc qua Google thật vẫn phải nghiệm thu tại staging.
Các kiểm thử local này không phải chứng nhận “không còn lỗi” hoặc nghiệm thu hosting.
