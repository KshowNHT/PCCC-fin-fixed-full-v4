> Báo cáo lịch sử. Luồng và kết quả kiểm thử hiện hành: RA_SOAT_V11_2.md.

# Rà soát đồng bộ v11.1 — 08/10/2026

## Kết luận

Version 11 vẫn có lỗi đồng bộ. Bản 11.1 đã sửa các lỗi xác định được bằng đọc mã
và kiểm thử tái hiện. Không thể cam kết chương trình không còn mọi lỗi; chưa chạy
Docker, PostgreSQL thật, HTTPS của hosting và Gemini thật trong môi trường này.
Không dùng kết quả local để thay biên bản nghiệm thu production.

## Đối chiếu bốn ảnh khách hàng

- Nhà xưởng 1 tầng, 7.200 m², cao 16 m: giao diện cũ dùng ngưỡng nhà hỗn hợp và
  diễn giải “1 tầng vượt ngưỡng” là không nhất quán. v11.1 giữ nhóm nhà xưởng,
  trả trạng thái cần rà soát thủ công, không áp ngưỡng dân dụng vào nhà xưởng.
- Karaoke 5 tầng, 500 m²: phần kết luận và phần ngưỡng phải lấy cùng appraisalBasis.
  Bộ fixture karaoke đã kiểm tra banner/khối ngưỡng cùng một nguồn; không dùng
  câu cũ “bất kể quy mô” và không hiện khối ngưỡng nhà hỗn hợp cho karaoke.
- Tài liệu OCR trong ảnh có nhà kho, kho thành phẩm, nhà xưởng và nhà văn phòng,
  với chiều cao, diện tích, bậc chịu lửa khác nhau. Đây là nhiều hạng mục; không
  thể mặc nhiên gộp thành một nhà. OCR được đổi thành xem trước, chỉ lưu sau
  xác nhận. Prompt yêu cầu để trống trường chưa rõ phạm vi và không lấy diện
  tích “Nhà có quy mô lớn nhất” làm tổng diện tích dự án. Đây là hạn chế hướng
  dẫn AI, không phải chứng minh OCR luôn nhận đúng. Cần file PDF gốc và thử API
  Vision thật để xác nhận ca tài liệu này; ảnh chụp không thay thế tài liệu gốc.

## Các sửa đổi

1. OCR mặc định không ghi DB hoặc tạo log. Client gửi apply_to_session=false;
   nút Áp dụng mới gọi lưu đã validate. API vẫn cho phép caller được xác thực
   chủ động gửi apply_to_session=true để ghi atomically.
2. Xuất Word/PDF/JSON chờ hàng đợi lưu; chỉ gửi sessionId, nội dung lấy từ server.
3. Lưu lỗi đánh dấu các trường chưa lưu, chặn thẩm định/xuất tới khi sửa trường đó.
   Không rollback bằng snapshot cũ ghi đè những lần cập nhật đã thành công.
4. Khóa thao tác ngay trước khi chờ lưu, tránh hai click cùng gửi yêu cầu. Chặn
   chuyển/xóa/tạo hồ sơ khi đang lưu hoặc xử lý; khóa input khi xử lý dài.
5. Hủy chỉ hủy chờ ở trình duyệt, không hứa hủy giao dịch server. Client đọc lại
   snapshot có kiểm tra quyền và khóa session trước khi mở thao tác tiếp theo.
   Nếu không xác nhận được trạng thái server, cần tải lại trước khi tiếp tục.
   Bỏ tin nhắn optimistic để tránh tin nhắn xuất hiện dù server chưa lưu.
6. Giữ chính xác tên loại công trình do AI cung cấp, kể cả đổi giữa hai loại thuộc
   cùng nhóm. Thêm lựa chọn Nhà hỗn hợp và hiển thị nguyên giá trị ngoài dropdown.
7. Remount form/OCR theo session để tránh giữ draft của hồ sơ cũ. Không render
   kết quả trung gian của hàng đợi làm lùi các draft mảng công năng đang sửa.
8. Phản hồi dùng token cũ không được cập nhật màn hình hay xóa token đăng nhập mới;
   queued save không chạy bằng token của lần đăng nhập kế tiếp.
9. Tải tài liệu dùng fetch có Authorization rồi tải Blob, thay liên kết thiếu JWT.
10. Nhật ký hủy yêu cầu cũ khi đổi scope, kiểm tra HTTP/mảng dữ liệu; lỗi không gây
    crash logs.map. Phân biệt ba trạng thái, thiếu căn cứ không hiện “Không bắt buộc”.
    Log cũ vẫn giữ lịch sử; trạng thái không có marker đáng tin cậy được hiện cần rà soát.
11. Snapshot hồ sơ hiện tại không giữ lại các cảnh báo AI của số liệu cũ; luôn
    dựng checklist/cảnh báo từ dữ liệu hiện tại. Lịch sử nằm trong nhật ký.
12. Xóa/reset tài liệu kiểm tra HTTP status và báo lỗi. Sao lưu không gọi exec
    backend đã dừng, không ghi đè backup cũ; chỉ khởi động lại backend nếu trước
    đó đang chạy. SHA256 dùng tên tương đối để kiểm tra sau khi chuyển nơi lưu.

## Kiểm thử tái hiện mới

| Ca | Nội dung | Kết quả |
|---|---|---|
| S01 | OCR preview không đổi DB/checklist/log/timestamp | PASS |
| S02 | Snapshot một hồ sơ kiểm tra owner, 401, 403, 404 | PASS |
| S03 | AI giữ Nhà hỗn hợp, không đổi thành nhà riêng lẻ kết hợp kinh doanh | PASS |
| S04 | Nhà xưởng 7.200 m² không dùng ngưỡng nhà hỗn hợp | PASS |
| S05 | Xuất chờ lưu; chuyển hồ sơ bị chặn khi lưu/xuất | PASS |
| S06 | Lưu lỗi chặn thẩm định/xuất, sửa đúng mở lại thao tác | PASS |
| S07 | Bấm hai lần lúc đang lưu chỉ chạy một thẩm định | PASS |
| S08 | Hủy chat đối chiếu snapshot, không có tin nhắn giả | PASS |
| S09 | 401 cũ không đăng xuất token mới | PASS |
| S10 | Dropdown hiển thị loại OCR; tải tài liệu gửi JWT | PASS |
| S11 | Phản hồi scope cũ không ghi đè scope mới, unknown không thành miễn | PASS |
| S12 | Nhật ký HTTP 503 hiện lỗi, không crash | PASS |
| S13 | Backend log chỉ cho trạng thái dưới ngưỡng khi có marker đúng | PASS |
| S14 | Checklist/cảnh báo hiện tại không kế thừa kết luận AI cũ | PASS |

Bộ chạy: scripts/run_all_tests.sh; log cuối: docs/qa/full-suite-sync.log.
46 backend + 8 ca React bổ sung đạt; 40 ca gốc, 3.000 hồ sơ fuzz, 6 fixture
kết luận React được chạy lại. React kiểm tra App thật với component fixture
ở các ca orchestration; Sidebar/InspectionLogPanel thật ở các ca thành phần.
Fetch/Gemini được giả lập; backend dùng SQLite cô lập. Không gọi đây là test E2E hosting.

## Điều kiện nghiệm thu còn lại

- Docker build/start thật, migration trên bản sao PostgreSQL v10/v11, kiểm tra
  quyền volume, HTTP/TLS, rate limit và phục hồi backup ở staging.
- OCR tài liệu gốc nhiều nhà, quota/model API AI thật, đối chiếu thủ công từng
  hạng mục. Không coi output Vision là dữ liệu đã được kỹ sư xác nhận.
- Không có push realtime hoặc khóa phiên bản giữa nhiều tab/nhân viên. Hai
  client cùng sửa một trường: lần ghi sau thắng. Tránh cùng sửa một hồ sơ,
  tải lại khi đổi người làm; muốn cộng tác realtime cần cơ chế revision riêng.
- Nhà xưởng/nhà kho vẫn cần phân loại pháp lý và thông số chuyên môn thủ công.
  Bộ phần mềm hiện sàng lọc, chưa tự chứng minh tuân thủ 17 mục kỹ thuật PCCC.
