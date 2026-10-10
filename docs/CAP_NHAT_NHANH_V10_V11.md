# Cập nhật nhanh v10/v11 lên v11.3

Dùng Linux/Bash/WSL và Docker Compose v2; thực hiện trên staging với bản sao dữ
liệu trước. Giữ thư mục triển khai, tên project Compose, postgres_data và pccc_data.
Không dùng docker compose down -v. Không chép file .env mẫu lên .env đang dùng.

1. Lưu riêng mã nguồn/compose/.env hiện tại để rollback, bảo vệ bản chứa secret.
2. Chép scripts/backup.sh của bản mới vào scripts của thư mục đang chạy, rồi từ
   đúng thư mục đó chạy: bash scripts/backup.sh backups/truoc-v11-3
   Script dừng backend và dùng compose run tạo container tar để đọc volume;
   không exec backend đã dừng. Chỉ tự khởi động lại nếu backend trước đó đang chạy.
   Kiểm tra database.dump, files.tar.gz, SHA256SUMS; thử khôi phục ở staging.
3. Sau khi backup thành công, dừng backend/frontend/edge hiện có. Giải nén bản
   mới ra thư mục tạm, chép mã và cấu hình vào đúng thư mục triển khai hiện tại;
   giữ .env, dữ liệu khách hàng và backups. Giữ nguyên tên project Compose.
4. Với v11: giữ secret/password DB. Với v10: kiểm tra secret/password theo yêu
   cầu production ở README. Nếu DB đang dùng pccc_dev_pass, đổi mật khẩu role
   PostgreSQL thật và cấu hình ứng dụng đồng bộ trong maintenance; chỉ sửa
   POSTGRES_PASSWORD trong .env không đổi password DB đã có. JWT đổi sẽ yêu cầu
   đăng nhập lại; PCCC_ADMIN_PASSWORD không đổi mật khẩu admin đã tồn tại.
5. Bổ sung PCCC_DOMAIN, ACME_EMAIL; kiểm tra DNS và cổng 80/443. Password DB do
   script sinh dùng hex. Password có ký tự đặc biệt cần encoding URL đúng theo
   docs/DEPLOY_VA_NGHIEM_THU.md. Không chạy configure_env.py để ghi đè .env cũ.
6. Chạy lần lượt từ thư mục triển khai:

   docker compose config --quiet
   docker compose up -d --build
   docker compose ps
   docker compose logs --tail=100 backend frontend edge

7. Backend chạy migration khi khởi động. Kiểm tra readiness:

   docker compose exec -T backend curl -fsS http://localhost:3000/api/ready

8. Mở domain HTTPS, tải lại trang, kiểm tra nhãn v11.3. Đăng nhập, mở hồ sơ cũ,
   đối chiếu số hồ sơ/tài liệu. Thử sửa rồi xuất ngay, OCR chỉ xem trước rồi đóng
   không đổi hồ sơ, áp dụng OCR, chuyển hồ sơ, nhật ký và tải tài liệu.
9. Bản v11.3 giữ hồ sơ/log, nhưng kết quả cũ chưa có xác nhận mới sẽ là bản nháp.
   Thử nhập chưa blur: không có kết luận mới; bấm Kiểm duyệt mới xuất được. Nhóm
   chưa có quy tắc phải báo Không tìm thấy quy định phù hợp. Mở hai tab, sửa ở tab
   đầu rồi sửa ở tab cũ: phải nhận xung đột, không ghi đè. Client/API cũ thiếu revision
   trong production nhận 428; reload để nạp frontend v11.3.
10. Chỉ bàn giao sau nghiệm thu hosting/API thật. Khi lỗi, dừng writer, khôi phục
   mã/compose/.env cũ cùng DB và file của một backup nhất quán theo hướng dẫn
   deploy; giữ nguyên project/volume. Không tự chạy downgrade Alembic (không hỗ trợ).

Ghi chú đính chính: lệnh docker compose exec backend tar sau docker compose stop
backend trong hướng dẫn trước không chạy được. Dùng scripts/backup.sh ở bước 2.
Tài liệu này không xác nhận script Docker đã chạy trong môi trường rà soát local.

Bổ sung v11.3: migration head là 002_components. Giữ dữ liệu cũ; không tự suy
ra hạng mục từ hồ sơ một nhà. Mọi kết quả dùng phiên bản quy tắc cũ trở về
bản nháp để kiểm duyệt lại theo Phụ lục III đã thay thế từ 15/9/2026. Cần xây
lại cả backend và frontend; không chỉ chép dist. Với Sabaco: OCR xem trước →
kiểm tra bốn nhà độc lập → áp dụng → sửa hạng, phân loại, quy mô còn thiếu →
xác nhận danh sách đầy đủ và hệ thống chung → bấm Kiểm duyệt → đối chiếu Word/PDF.
Không dùng Reset tài liệu như một bước nâng cấp: thao tác đó xóa tài liệu custom.
Nguồn, ca thử và giới hạn bàn giao: docs/RA_SOAT_V11_3.md.
