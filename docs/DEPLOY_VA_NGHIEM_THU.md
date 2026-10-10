# Triển khai và nghiệm thu v11

## Thông số bắt buộc

Domain, email ACME, mật khẩu DB, JWT secret, admin password; nếu dùng AI/OCR cần
Google API key có quota và quyền model. Sinh bằng `scripts/configure_env.py`.
Password DB script sinh là hex, tránh lỗi ký tự đặc biệt trong DATABASE_URL.
Nếu tự đặt password có ký tự @, :, / hoặc %, phải percent-encode đúng phần
password của URL hoặc sửa cách cấu hình kết nối, không ghép thô vào Compose.

Hosting phải hỗ trợ container dài hạn, PostgreSQL và volume bền vững; bản static
React không thay được backend. Caddy cần DNS trỏ đúng và truy cập ACME. Nếu DNS
AAAA tồn tại nhưng IPv6 VPS chưa hoạt động, bỏ AAAA hoặc sửa IPv6 trước cấp TLS.

## Trình tự chạy

1. Giải nén và kiểm tra README. Giữ project name/volume nếu nâng cấp v10.
2. Sinh `.env`, thêm key, hạn chế quyền file. Mật khẩu admin chỉ dùng để seed DB
   trống; sửa biến này không đổi mật khẩu tài khoản đã tồn tại.
3. Chạy `docker compose config --quiet`. Không xuất cấu hình chứa secrets ra log
   công khai. Build và chạy theo README; theo dõi migration và readiness.
4. HTTPS phải tự chuyển từ HTTP, chứng chỉ hợp lệ, chỉ 80/443 công khai.
5. Đăng nhập admin, cấp nhân viên, kiểm tra cô lập hồ sơ giữa hai nhân viên.
6. Kiểm tra OCR bản vẽ thật; dữ liệu OCR phải được kỹ sư đối chiếu trước sử dụng.
7. Chạy bộ 40 tình huống trên PostgreSQL `pccc_test` riêng và kiểm tra đồng thời.
8. Sao lưu, khôi phục vào môi trường riêng, kiểm tra một hồ sơ và file gốc.

## Kiểm tra cần thực hiện trên môi trường khách hàng

| Kiểm tra | Điều kiện chấp nhận |
|---|---|
| Build Docker và migration | Tất cả container healthy, migration 001_v11 áp dụng, restart không mất dữ liệu |
| TLS/domain | Chứng chỉ hợp lệ, HTTP chuyển HTTPS, DB/backend không truy cập trực tiếp từ internet |
| IP và rate limit | Hai client khác IP có hạn mức độc lập, header X-Forwarded-For giả không đổi danh tính |
| Khóa ghi PostgreSQL | Chat/OCR/cập nhật/xóa cùng hồ sơ được tuần tự, không tái sử dụng hồ sơ đã xóa |
| Quota tài khoản đồng thời | Hai yêu cầu khi còn một suất staff chỉ một được tạo |
| AI thật | Model cho phép text/image + structured output, timeout và quota có thông báo đúng |
| OCR PDF thật | Poppler đọc được tối đa 4 trang đầu, PNG/JPEG/WebP đưa sang PNG đúng MIME |
| Upload và ổ đĩa | Không còn file khi parse/commit lỗi; dung lượng volume và quyền UID 1001 đúng |
| Khôi phục | Database và legal_db từ cùng backup; file gốc tải được, tên project/volume đúng |
| Tải thực tế | Đo theo cấu hình VPS và số user đồng thời; không suy SLA từ 40 test chức năng |
| Pháp lý | Kỹ sư xác nhận hiệu lực, ngoại lệ, chuyển tiếp, subtype và phạm vi từng công trình |

Các mục trên chưa được chứng nhận trên hosting khách hàng. Docker daemon,
PostgreSQL server và quyền đổi user hệ thống không có trong môi trường kiểm tra
hiện tại; không gọi đây là nghiệm thu production đã hoàn tất.

## Sao lưu và khôi phục

`bash scripts/backup.sh` dừng backend trong thời gian chụp DB và volume file;
PostgreSQL vẫn chạy. Script chỉ khởi động lại backend nếu nó đang chạy trước khi sao lưu.
Không để tiến trình ngoài ứng dụng ghi vào DB/file trong khoảng sao lưu.
Kiểm tra checksum, `pg_restore --list` và `tar -tzf`; checksum chỉ chứng minh byte
không đổi, không chứng minh phục hồi sử dụng được.

Khôi phục trên môi trường riêng: tạo database mới, phục hồi `database.dump` bằng
`pg_restore`, giải nén `files.tar.gz` vào volume ứng dụng, đảm bảo owner UID 1001,
đặt cùng JWT secret nếu cần giữ phiên (hoặc xoay để buộc đăng nhập lại), rồi chạy
migration và health check. Giữ snapshot v10 đến khi kiểm tra hồ sơ, tài liệu và
báo cáo đầy đủ. Không phục hồi đè DB production khi chưa có backup và kế hoạch
thời gian dừng.

## Vận hành

Theo dõi `/api/ready`, dung lượng volume, lỗi 5xx, tỉ lệ fallback AI, thời gian
OCR/chat, quota Google và số đăng nhập bị 429. Hạn mức IP không thay thế quản lý
chi phí theo tổ chức. Log server có thể chứa thông tin hồ sơ/exception; hạn chế
người xem log và tránh chuyển sang hệ thống bên ngoài nếu chưa phù hợp chính
sách dữ liệu của khách hàng. RAG gửi nội dung tài liệu custom được chọn và hồ sơ
hiện tại đến Google; đã bỏ việc gửi hồ sơ khác. Cần xác nhận quyền sử dụng dịch
vụ AI với dữ liệu khách hàng trước vận hành thực tế.

Mọi sửa đổi rule cần số hiệu điều khoản, nguồn chính thức, phạm vi và kiểm thử
biên mới. Để đủ tự chấm các hạng mục kỹ thuật phải mở rộng schema thu thập bằng
chứng và được kỹ sư xác nhận từng quy tắc; không lấy lại các ngưỡng ước lượng v10.

## Nghiệm thu bổ sung v11.2

Nhập liệu/OCR chỉ lưu draft; chưa bấm Kiểm duyệt không được có đánh giá mới.
Thiếu quy tắc báo Không tìm thấy quy định phù hợp; không chấm đạt/không đạt.
Xuất draft phải nhận 409, revision cũ nhận 412, thiếu revision production nhận 428.
Kiểm tra hai tab, refresh frontend và hồ sơ cũ trước bàn giao. Xem RA_SOAT_V11_2.md.
