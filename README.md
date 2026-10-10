# PCCC v11.3 — nhà xưởng và hồ sơ nhiều hạng mục, kiểm duyệt tường minh

Ứng dụng React + FastAPI + PostgreSQL hỗ trợ quản lý hồ sơ, đọc lại kết quả rà soát,
OCR bản vẽ và xuất Word/PDF/JSON. Đây là công cụ **sàng lọc và hỗ trợ rà soát**;
không tự xác nhận thiết kế đạt/không đạt, không thay thế thẩm định hay nghiệm thu.

## Triển khai production

Cần VPS Linux hỗ trợ Docker Engine + Docker Compose v2, khuyến nghị 4 GB RAM,
2 vCPU trở lên, domain đã trỏ A/AAAA đến VPS và cổng 80/443 được mở. Hosting
chỉ phục vụ HTML/PHP hoặc chỉ cho upload `dist/` không chạy được toàn bộ hệ thống.
Phải cho phép máy chủ truy cập registry Docker, ACME và Google nếu dùng Gemini.

```bash
python3 scripts/configure_env.py --domain pccc.tenmien.vn --email ops@tenmien.vn
# Mở .env để bổ sung GEMINI_API_KEY; không đưa file này vào Git.
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl -f https://pccc.tenmien.vn/api/ready
```

Đăng nhập bằng `admin` và mật khẩu được sinh trong `.env`. Dùng POST
`/api/auth/users` với Bearer token admin để tạo nhân viên; đăng ký công khai đã tắt.
Đổi mật khẩu qua PUT `/api/auth/me/password`; mọi token đã cấp trước đó bị thu hồi.
Đăng nhập lại sau khi đổi mật khẩu. Giới hạn tài khoản chỉ đếm role `staff`.
Không nhập API key vào `frontend/.env`: các biến VITE được công khai trong bundle.

Caddy tự cấp và gia hạn TLS. Backend và PostgreSQL không publish port ra host.
Nginx và Uvicorn chỉ tin proxy trong mạng Docker `172.28.76.0/24`. Nếu subnet
trùng mạng VPS, phải sửa đồng thời `compose.yaml`, `frontend/nginx.conf` và
`backend/entrypoint.sh`. Không đặt thêm proxy/CDN mà chưa kiểm tra IP client thật
và rate limit. Khi thay `.env`, chạy lại `docker compose up -d`; khi sửa frontend
hoặc mã nguồn cần `--build`.

## Luồng nghiệp vụ bắt buộc

Nhập / sửa thông số hoặc áp dụng OCR chỉ lưu **bản nháp**. Khi đang gõ, giao diện
ẩn kết luận cũ. Bấm **Kiểm duyệt hồ sơ** mới chạy bộ quy tắc đã xác minh và lưu
kết quả gắn với chính thông số đó. Không tự rà soát khi mở hồ sơ, GET danh sách,
chat, thay đổi ô nhập hoặc áp dụng OCR. Xuất báo cáo bị chặn cho tới khi có kết
quả kiểm duyệt phù hợp với bản dữ liệu hiện tại. Sửa lại sẽ phải kiểm duyệt lại.

Nếu không có quy tắc phù hợp đã xác minh, hiển thị **Không tìm thấy quy định phù hợp**
và giữ trạng thái cần rà soát, không tự tạo ngưỡng, trích dẫn hay chấm đạt/không đạt.
Thông báo này nói về phạm vi bộ quy tắc trong phần mềm, không khẳng định pháp luật
không có quy định. Hiện chưa tự chấm đủ 17 hạng mục kỹ thuật; đây là giới hạn
nghiệp vụ thực tế, không phải cam kết thẩm định toàn diện.

Trong v11.3, Gemini chỉ phục vụ OCR. Kết luận và trả lời pháp lý không dùng nội dung
LLM tự do. Chat đọc lại kết quả đã kiểm duyệt, hướng dẫn nhập liệu, hoặc thông báo
chưa tìm thấy quy tắc để trả lời; không sửa thông số bên trái. Tài liệu upload
được lưu để đọc/đối chiếu, chưa tự chuyển thành quy tắc pháp lý được xác minh.
`GEMINI_MODELS` mặc định `gemini-3.8-flash`; phải kiểm tra quyền model với key thật.
OCR lỗi thì nhập tay. Timeout AI 75 giây, proxy 150 giây. Một worker backend;
khóa ghi và kiểm tra phiên bản hồ sơ thực hiện trong PostgreSQL.

Hai tab cùng sửa: client gửi revision nhận từ server. Bản cũ bị từ chối HTTP 412,
không tự ghi đè hoặc tự thử lại. Nút **Tải lại hồ sơ** bỏ các chỉnh sửa chưa lưu
và nạp bản mới nhất. Production bắt buộc revision cho thao tác sửa/xóa/chat/
kiểm duyệt/OCR ghi trực tiếp và xuất báo cáo; client cũ không gửi sẽ nhận 428.
Không có push realtime; tải lại hoặc mở lại hồ sơ để thấy thay đổi từ tab khác.

## Cài và chạy kiểm thử

Python 3.12, Node 20 trở lên, npm tương thích package-lock; Poppler cho OCR PDF.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-test.txt
bash scripts/run_all_tests.sh
```

Script dừng khi bất kỳ kiểm tra nào thất bại. 40 ca gốc và các ca bổ sung mặc định dùng
SQLite tạm để chạy tái lập, AI giả lập; có 3.000 hồ sơ fuzz và 8 fixture React.
Muốn chạy trên PostgreSQL, tạo database **riêng** `pccc_test`, rồi đặt
`TEST_DATABASE_URL=postgresql+asyncpg://.../pccc_test`. Bộ test xóa dữ liệu trong
database này. Không trỏ test vào database khách hàng. Kết quả cụ thể và phạm vi
kiểm tra mới nhất nằm ở `docs/RA_SOAT_V11_3.md` và `docs/qa/full-suite-v11-3.log`.

## Căn cứ và giới hạn nghiệp vụ

Đã đối chiếu Phụ lục III thay thế kèm Nghị định 347/2026/NĐ-CP, hiệu lực
15/9/2026. Nhà xưởng thuộc sản xuất công nghiệp khác xét mục 9(d) theo hạng
nguy hiểm cháy/nổ, khối tích và tổng sàn; kho hạng A/B/C xét mục 10. Không lấy
ngưỡng nhà hỗn hợp cho nhà xưởng. Các phân loại hoặc số liệu chưa rõ vẫn cần
rà soát thủ công. Chi tiết nguồn và phạm vi: docs/RA_SOAT_V11_3.md.

OCR trả danh sách nhà độc lập; nhập/sửa trong phần “hồ sơ nhiều hạng mục”,
đối chiếu nguồn và xác nhận danh sách đầy đủ trước Kiểm duyệt. Có thể kiểm
duyệt tất cả hạng mục trong một lần. Không cộng các nhà thành một nhà hỗn hợp,
không tạo nhà từ dòng tổng hợp. PDF tối đa 24 trang và 25 MB; vượt giới hạn báo
lỗi yêu cầu tách, không âm thầm bỏ trang. OCR vẫn cần kiểm tra độ chính xác.

Ngưỡng quy mô không dùng để chấm 16 hạng mục kỹ thuật còn lại. Chương trình
chưa thu thập cấu kiện, thiết bị, lối thoát nạn, khoang cháy và điều kiện thiết
kế đủ để tự chấm đạt/không đạt. Hạng mục dưới ngưỡng có thể vẫn cần thẩm định
nội dung hệ thống dùng chung theo ghi chú phụ lục; form yêu cầu xác nhận.

Tài liệu mặc định là metadata tham khảo, không phải toàn văn đã xác minh.
Tài liệu custom không tự trở thành căn cứ kết luận. Quản trị viên phải
kiểm tra hiệu lực, văn bản sửa đổi và độ đầy đủ của tài liệu trước khi nạp.
Bộ quy tắc chưa bao phủ toàn bộ Phụ lục III, ngoại lệ, dự án cải tạo hay quy
định chuyển tiếp; cần xác nhận trước khi dùng cho quyết định pháp lý thực tế.

## Kết quả rà soát mới nhất

93 ca: 76 backend, 14 React, 3 migration SQLite; thêm 3.000 hồ sơ fuzz và
8 fixture kết luận React. Lint/build production đạt. Không có Docker daemon,
PostgreSQL server, hosting/TLS hoặc key AI khách hàng để nghiệm thu thực tế.
Xem `docs/RA_SOAT_V11_3.md`; các báo cáo v11/v11.1 là lịch sử, không mô tả
luồng tự kiểm duyệt của bản hiện hành.

## Nâng cấp từ v10

Sao lưu database và toàn bộ volume file trước. Giữ nguyên tên project Compose
và volume; đổi thư mục hoặc tên project có thể tạo volume mới, khiến ứng dụng
trông như mất dữ liệu. Migration `001_v11` tiếp nhận bảng v10 và thêm chỉ mục,
không xóa bảng; schema thiếu cột sẽ chặn khởi động. Kết quả cũ chưa có dấu xác
nhận kiểm duyệt mới sẽ trở về bản nháp; hồ sơ và log lịch sử vẫn giữ. Secret JWT nên xoay khi nâng cấp; token v10 sẽ không còn hợp lệ.
Tài liệu custom và hồ sơ khách hàng được giữ; các tóm tắt pháp lý tự sinh của
catalog mặc định được đổi thành thông báo chưa xác minh. Kiểm tra bản khôi phục
trên môi trường riêng trước khi nâng cấp production.

## Sao lưu và vận hành

```bash
bash scripts/backup.sh
# Kiểm tra nhật ký và trạng thái sau sao lưu
docker compose ps
docker compose logs --tail=100 backend edge
```

Backup dừng backend trong lúc chụp database và file để giữ nhất quán. Cất
`database.dump`, `files.tar.gz`, `.env` và bản code tương ứng ở nơi có kiểm soát
truy cập; `.env` phải lưu riêng, script không sao chép mật khẩu vào backup.
Kiểm tra khôi phục bằng `pg_restore` và giải nén file vào volume của môi trường
riêng, rồi kiểm tra quyền UID 1001. Không chạy `docker compose down -v` trên dữ
liệu khách hàng. Xem quy trình chi tiết trong `docs/DEPLOY_VA_NGHIEM_THU.md`.
