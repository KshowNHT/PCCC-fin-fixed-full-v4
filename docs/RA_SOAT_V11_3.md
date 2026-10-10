# Rà soát v11.3 — nhà xưởng và hồ sơ nhiều hạng mục

Ngày rà soát: 08/10/2026. Bản này tiếp nối luồng bản nháp / Kiểm duyệt của v11.2.

## Phát hiện và sửa

1. Giá trị dropdown “Nhà máy, nhà xưởng sản xuất” đã được nhận diện đúng trong
   v11.2, nhưng chưa có quy tắc công nghiệp đã xác minh. Không được thay bằng
   ngưỡng nhà hỗn hợp. v11.3 bổ sung khối tích, hạng nguy hiểm cháy/nổ và phân
   loại sản xuất công nghiệp khác / chuyên ngành. Thiếu hoặc ngoài phạm vi
   đã xác minh sẽ báo “Không tìm thấy quy định phù hợp”, giữ trạng thái cần xem xét.
2. v11.2 chỉ có cấu trúc một nhà; OCR nhiều nhà chỉ cảnh báo nhập tay. v11.3 thêm
   danh sách components trong database, schema API, OCR, form, kết quả và báo cáo.
   Mỗi nhà có mã, tên, công năng, số tầng, chiều cao, diện tích, khối tích, hạng,
   bậc chịu lửa và bằng chứng nguồn riêng. Không kế thừa số liệu nhà khác hoặc
   công năng ở cấp dự án. Khi có components, bộ quy tắc chỉ xét danh sách này.
3. “Nhà có quy mô lớn nhất” và “Tổng cộng” bị chặn như một hạng mục độc lập.
   Không cộng diện tích nhiều nhà để xét ngưỡng của một nhà. Danh sách chưa
   xác nhận đầy đủ không được kết luận toàn dự án dưới ngưỡng.
4. Kết luận tổng hợp dùng kết quả tất cả nhà, không lấy nhà đầu tiên. Nhật ký,
   Word/PDF/JSON và web dùng cùng snapshot. Danh sách bốn nhà có một dòng tổng
   hợp và 17 tiêu chí mỗi nhà: 69 dòng, không cắt xuống 17 dòng toàn dự án.
5. Ghi chú hệ thống báo cháy/chữa cháy dùng chung được rà soát riêng: nếu có
   nhà thuộc diện, các nhà dưới ngưỡng thiết kế đồng thời và dùng chung hệ thống
   phải hiển thị phạm vi thẩm định nội dung hệ thống chung. Chưa xác nhận thì
   cảnh báo cần rà soát, không suy ra “không bắt buộc” cho nội dung dùng chung.
6. OCR thật bắt buộc trả danh sách nhà kể cả một nhà, có trang nguồn và dòng
   số liệu; sai cấu trúc, trùng mã/tên, thiếu nguồn hoặc số âm bị từ chối.
   Không suy hạng C từ nhóm F5.2; không suy khối tích từ diện tích × chiều cao;
   không coi diện tích xây dựng là tổng sàn khi tài liệu không ghi rõ.
7. PDF đọc mọi trang trong giới hạn 24 trang, không âm thầm cắt còn bốn trang.
   Vượt giới hạn trả lỗi 422 yêu cầu tách tài liệu. Giới hạn upload 25 MB vẫn giữ.
   Gửi đủ trang không chứng minh AI đã nhận diện đủ mọi nhà; người dùng phải đối chiếu.
8. Sửa thông số/hạng mục/OCR chỉ lưu draft. Chưa bấm Kiểm duyệt không gọi quy tắc.
   Sửa một nhà ẩn kết luận cũ và chặn xuất. Mọi sửa danh sách làm mất xác nhận
   đầy đủ, trừ khi người dùng xác nhận rõ trong cùng yêu cầu. Danh sách thay đổi
   mã nhà không giữ mặc định quan hệ hệ thống dùng chung của danh sách cũ.

## Căn cứ pháp lý hiện hành đã đối chiếu

Nghị định 347/2026/NĐ-CP, ban hành 08/9/2026, hiệu lực 15/9/2026. Điều 31 khoản 1
thay thế Phụ lục III Nghị định 105/2025/NĐ-CP. Vì vậy các ngưỡng của bộ quy tắc
v11.2 theo phụ lục gốc không được tiếp tục coi là kết quả hiện hành.

Nguồn chính thức:
- https://vanban.chinhphu.vn/?docid=219411&pageid=27160
- https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/9/347_2026_nd-cp_08092026_7-signed.signed.pdf
- https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/9/347_2026_nd-cp_08092026_11-signed.pdf

Các nhánh công nghiệp xét đúng điểm 9(d), kho xét mục 10; thỏa một trong các
ngưỡng diện tích hoặc khối tích đã xác minh có thể nhận diện diện quy mô. Khi
chưa thỏa một ngưỡng nhưng ngưỡng còn lại chưa biết, kết quả chưa đủ dữ liệu.
Chỉ chọn “sản xuất công nghiệp khác” sau khi xác nhận đúng đối tượng; công
nghiệp chuyên ngành vẫn cần rà soát riêng, không dùng 9(d) thay thế tùy ý.

Bộ quy tắc hiện hành cũng cập nhật các nhánh đã hỗ trợ về nhà chung cư/tập thể,
nhà hỗn hợp, văn phòng/khách sạn, karaoke/vũ trường, nhà để xe dạng kín và chợ/
trung tâm thương mại. Nhà hỗn hợp dưới ngưỡng tổng vẫn phải kiểm tra các phần
có công năng/quy mô thuộc danh mục; chưa có thông tin đó không kết luận dưới
mọi điều kiện. Nhóm giáo dục chưa rõ phân loại, chuyên ngành và các nhóm chưa
hỗ trợ vẫn báo thiếu căn cứ phù hợp. Không tuyên bố đã mã hóa toàn bộ phụ lục.

## Sabaco và kiểm thử

Dữ liệu minh họa từ bảng ảnh gồm Nhà kho (14,6 m / 2.304 m² / 30.259,2 m³),
Kho thành phẩm (16 m / 4.312 m² / 59.294,4 m³), Nhà xưởng (16 m / 7.200 m² /
98.935,2 m³), Nhà văn phòng (13,1 m / 540 m² / 4.860 m³). Diện tích trong ảnh
không tự coi là tổng sàn. Bậc chịu lửa IV/IV/IV/II được giữ riêng.

Test sử dụng hạng C và phân loại “other” như thông số người dùng đã xác nhận;
không chứng minh ảnh ghi hạng C cho tất cả các nhà. Văn phòng chưa rõ số tầng
vẫn cần bổ sung, không lấy số tầng của nhà xưởng. Bộ test OCR giả lập Google;
không phải nghiệm thu độ chính xác nhận dạng trên PDF Sabaco gốc.

Các ca mới M01–M21 kiểm tra phân loại, biên ngưỡng A/B/C/D/E, thiếu hạng, không
cộng quy mô, bốn nhà độc lập, danh sách chưa đầy đủ, OCR xem trước/áp dụng,
rollback dữ liệu sai, revision, Word/PDF, nhật ký, vô hiệu kết quả luật cũ,
không rà soát tự động, PDF dài, trùng/dòng tổng hợp, hệ thống chung và contract OCR.
M22 kiểm tra nâng cấp schema 001 sang 002 giữ hồ sơ cũ. U01–U02 kiểm tra form
hạng mục và kết quả React, không lấy thông số nhà đơn lẻ cũ cho dự án nhiều nhà.

Tổng bộ kiểm thử: 76 ca backend, 14 ca React và 3 ca migration SQLite = 93 ca;
thêm 3.000 hồ sơ fuzz, 8 fixture kết luận React, TypeScript lint và Vite build.
Kết quả thực tế xem docs/qa/full-suite-v11-3.log; mọi bước phải PASS.

## Nâng cấp và giới hạn bàn giao

Migration 002_components thêm cột nullable, giữ dữ liệu và không tự tách hồ sơ cũ
bằng suy đoán. Kết quả lưu với rulesVersion cũ trở về draft; cần kiểm duyệt lại
sau khi đối chiếu văn bản hiện hành và trường hợp chuyển tiếp. Nhật ký cũ giữ
nguyên như lịch sử, không coi là kết quả hiện hành.

Chưa nghiệm thu Docker/PostgreSQL thật, HTTPS, restore backup, quyền volume hay
Google với API key khách hàng. Nghiệm thu staging bằng PDF/PNG gốc và cấu hình
khách hàng là việc còn phải làm trước bàn giao production. Không cam kết không
còn lỗi hoặc nhận dạng 100%. Chưa tự chấm đủ 16 tiêu chí kỹ thuật còn lại cho
mỗi nhà; vẫn cần kỹ sư, quy định áp dụng và bằng chứng thiết kế thực tế.
