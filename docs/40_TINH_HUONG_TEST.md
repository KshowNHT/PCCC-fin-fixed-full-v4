# 40 tình huống kiểm thử vận hành — PCCC v11

Đã chạy tự động trên API FastAPI thực, database SQLite tạm và AI giả lập. PASS không đồng nghĩa đã nghiệm thu PostgreSQL, container, HTTPS hay khóa AI khách hàng. Test T40 gồm nhiều subcase về ngưỡng pháp lý. Xem log trong `qa/operations40.log`.

| Mã | Tình huống | Thao tác / dữ liệu | Kỳ vọng | Kết quả |
|---|---|---|---|---|
| T01 | Health và readiness | Gọi health/ready khi DB hoạt động | 200; readiness truy vấn DB | PASS |
| T02 | Thiếu xác thực | Gọi dữ liệu, hồ sơ, me, nhật ký không token | 401 | PASS |
| T03 | JWT sai hoặc hết hạn | Token rác và token exp trong quá khứ | 401 | PASS |
| T04 | Đăng ký công khai | Tự đăng ký khi không có quyền admin | 403; không bootstrap admin qua internet | PASS |
| T05 | Staff tạo admin | Nhân viên gọi tạo tài khoản role admin | 403 | PASS |
| T06 | Trùng username | Admin tạo tên đã tồn tại | 409 | PASS |
| T07 | Giới hạn staff | Giới hạn 2 rồi 3; admin không chiếm suất staff | Chặn khi đủ; tạo khi còn suất | PASS |
| T08 | Role/mật khẩu không hợp lệ | Role root, mật khẩu không số, vượt 72 byte UTF-8 | 422 | PASS |
| T09 | Sai đăng nhập | Gửi sai mật khẩu qua JSON và OAuth form | 401 | PASS |
| T10 | Rate limit đăng nhập | 11 yêu cầu liên tiếp cùng IP | Yêu cầu vượt hạn trả 429 | PASS |
| T11 | Thu hồi JWT sau đổi mật khẩu | Đổi password rồi dùng token cũ và đăng nhập mới | Token cũ 401; password mới dùng được | PASS |
| T12 | Cô lập danh sách hồ sơ | Hai nhân viên khác nhau; admin xem chung | Staff chỉ thấy hồ sơ mình | PASS |
| T13 | Cô lập cập nhật/xóa/chat | Dùng staff A tác động hồ sơ staff B | 403; không gọi AI | PASS |
| T14 | Cô lập xuất và nhật ký | Staff A xuất/xem nhật ký hồ sơ B | 403 | PASS |
| T15 | Quyền trước OCR | Gửi bản vẽ vào hồ sơ người khác | 403 trước khi gọi AI | PASS |
| T16 | Hồ sơ không tồn tại | Cập nhật/xuất mã hồ sơ không có | 404 | PASS |
| T17 | Thông số âm | Số tầng, diện tích, hầm, chiều cao âm | 422 | PASS |
| T18 | Mảng lồng không hợp lệ | Chiều cao hầm âm, NaN, tên quá dài, quá nhiều phần tử | 422 | PASS |
| T19 | Số không hữu hạn/tầng lẻ | Infinity, NaN, số tầng 1.5 | 422 | PASS |
| T20 | PATCH liên trường | Chỉ đổi tổng sàn nhỏ hơn diện tích tầng đã lưu | 422; PATCH tên giữ các trường khác | PASS |
| T21 | Nhà giật cấp hợp lệ | 10 tầng, tầng điển hình 1000, tổng 2000 | Không bị chặn bởi quy tắc 50% tự đặt | PASS |
| T22 | Chat trắng hoặc quá dài | Khoảng trắng hoặc >8000 ký tự | 422 trước AI | PASS |
| T23 | Staff quản lý pháp lý | Nhân viên upload/xóa/reset thư viện | 403 | PASS |
| T24 | TXT và tên path traversal | Upload ../../law.txt; tải và xóa file | 201; tên UUID an toàn; nội dung đúng | PASS |
| T25 | Đuôi file bị cấm | Upload .exe | 400 | PASS |
| T26 | PDF giả | HTML đặt tên .pdf | 422 | PASS |
| T27 | DOCX hỏng | Dữ liệu không phải ZIP/DOCX | 422 | PASS |
| T28 | DOCX nén bất thường | ZIP có tỷ lệ giải nén rất cao | 422 | PASS |
| T29 | TXT rỗng/nhị phân/sai UTF-8 | File rỗng, NUL, byte sai encoding | 400/422 | PASS |
| T30 | Vượt giới hạn upload | File vượt ngưỡng cấu hình | 413 trước khi lưu | PASS |
| T31 | Upload nhiều file nguyên tử | File đầu hợp lệ, file sau hỏng | Không lưu metadata/file của cả batch | PASS |
| T32 | DOCX hợp lệ và metadata | DOCX đọc được; type dài hơn DB cho phép | 201 cho DOCX; 422 cho type | PASS |
| T33 | PDF không có văn bản | PDF scan/blank chưa OCR | 422; không nạp câu báo lỗi làm căn cứ RAG | PASS |
| T34 | Download ra ngoài thư mục | Link lưu có ../ ra ngoài legal_db | Từ chối; không tải đường dẫn tùy ý | PASS |
| T35 | Reset dọn file | Upload custom rồi reset thư viện | Xóa metadata và file custom | PASS |
| T36 | Xuất từ dữ liệu server | Client gửi project/checklist giả; bỏ sessionId | Bỏ dữ liệu giả; thiếu sessionId 422 | PASS |
| T37 | Word/PDF mở được | Xuất hồ sơ tiếng Việt; parse DOCX/PDF | File hợp lệ; không gán mọi thẩm quyền cho Công an | PASS |
| T38 | OCR bản nháp/file tạm | OCR mock lên 7 tầng; mock dịch vụ lỗi | Chỉ cập nhật bản nháp, không chạy rà soát; dọn file cả khi lỗi | PASS |
| T39 | Chat không áp dụng số liệu AI | AI trả 999 tầng/checklist hỏng | Không đổi form bằng nội dung AI; chỉ đọc kết quả đã kiểm duyệt | PASS |
| T40 | Biên pháp lý và tái lập | Dưới/bằng/vượt ngưỡng; thiếu dữ liệu; nhóm chưa xác minh | Kết luận 3 trạng thái đúng; không tự chấm tuân thủ | PASS |

## Chạy lại

`python backend/tests/test_operations_40.py` sau khi cài `backend/requirements-test.txt`.

Trong test dùng quyền admin/staff thực và lưu dữ liệu thật vào DB tạm. AI/OCR giả lập chỉ dùng cho tình huống lỗi và nội dung trả về; không xác nhận chất lượng OCR hay model Google. Có thể chạy cùng suite trên database PostgreSQL riêng `pccc_test` bằng `TEST_DATABASE_URL`; xem README.

Ngoài 40 tình huống có 3.000 hồ sơ fuzz tái lập bằng seed 20261008 và 6 fixture React render qua jsdom.
