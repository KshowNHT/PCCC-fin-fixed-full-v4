> Báo cáo lịch sử. Luồng và kết quả kiểm thử hiện hành: RA_SOAT_V11_2.md.

# Báo cáo rà soát PCCC v11

Ngày thực hiện: 08/10/2026. Đầu vào gồm gói full v10 và gói patch ChanAI.
Gói patch chứa các file trùng gói full; không có bản vá độc lập bị bỏ sót.

## Kết quả và phạm vi

Đã sửa backend, frontend, upload, xác thực, AI/OCR, logic kết luận, xuất báo cáo
và bộ triển khai. 40/40 tình huống API đạt; 3.000 hồ sơ fuzz đạt; 6 fixture React
đạt. TypeScript và build Vite đạt. `pip-audit` trên requirements-lock và
`npm audit` trên package-lock không ghi nhận lỗ hổng đã biết tại thời điểm chạy.
Audit không chứng minh không còn lỗ hổng, không bao gồm image OS Docker và
không thay thế kiểm tra định kỳ.

Không thể chứng minh “mọi lỗi có thể xảy ra” bằng số lượng test cố định. Đây là
rà soát mã nguồn và thử nghiệm các nhóm lỗi có khả năng ảnh hưởng vận hành;
không phải chứng nhận hệ thống không còn lỗi hoặc đầy đủ nghiệp vụ PCCC.

## Các lỗi đã xử lý

| Nhóm | Phát hiện v10 | Hoàn thiện v11 |
|---|---|---|
| Rò rỉ ngữ cảnh | Query các hồ sơ khác rồi gửi đến Gemini dù staff không được xem | Bỏ ngữ cảnh liên hồ sơ khỏi AI |
| OCR phân quyền | Gọi AI, lưu bản vẽ trước khi kiểm tra chủ hồ sơ | Kiểm tra quyền trước đọc/gọi AI |
| OCR đồng bộ | Apply số liệu nhưng chưa cập nhật kết luận và nhật ký | Tính lại checklist/verdict, ghi ocr_autofill |
| OCR lưu trữ | Không dọn file thành công hoặc lỗi | finally xóa file tạm |
| Upload RAM | Đọc toàn bộ trước khi kiểm tra giới hạn | Đọc từng chunk và dừng khi vượt |
| File giả | Chỉ kiểm tra đuôi file | Kiểm tra PDF, DOCX, encoding và ảnh |
| ZIP bomb | DOCX giải nén không ràng buộc | Giới hạn kích thước, số entry và tỷ lệ nén |
| PDF scan/hỏng | Nạp lời báo lỗi như nội dung pháp lý | Từ chối; yêu cầu OCR trước |
| Upload batch | Có thể để file mồ côi sau lỗi giữa batch | Rollback DB và dọn mọi file của batch |
| Metadata quá dài | type vượt String(64) gây lỗi DB | Từ chối 422 trước commit |
| Reset | Đổi DB nhưng giữ file custom trên volume | Dọn file sau commit reset |
| Download path | Thiếu confinement cho dữ liệu link đã lưu | Kiểm tra resolved path trong thư mục cho phép |
| Xuất báo cáo | Không có sessionId thì nhận checklist giả từ client | Bắt buộc sessionId, đọc lại hồ sơ server |
| Mật khẩu | bcrypt âm thầm cắt sau 72 byte | Validate byte UTF-8; không truncate |
| JWT | Token vẫn còn hiệu lực sau đổi password | Bind token với fingerprint password hash |
| Tạo tài khoản | Public bootstrap; đếm cả admin vào quota | Đóng public register; quota chỉ đếm staff |
| Xung đột username/email | Có thể lỗi commit không được xử lý | Rollback và trả 409 |
| Schema | Mảng hầm/tầng không giới hạn; PATCH tránh luật liên trường | Kiểm tra mảng/số hữu hạn và dữ liệu sau merge |
| Nhà giật cấp | Quy tắc tối thiểu 50% tự đặt chặn dữ liệu có thể đúng | Bỏ quy tắc ước lượng; chỉ cảnh báo đối chiếu |
| Ghi đồng thời | Chat/OCR/manual/xóa có thể chồng lên nhau | Khóa giao dịch theo session PostgreSQL |
| AI timeout | to_thread timeout không dừng HTTP thread; nhiều retry kéo dài | Async SDK, HTTP timeout, ngân sách tổng 75s |
| MIME ảnh OCR | JPEG/WebP bị gán image/png | Convert thực sang PNG; giới hạn kích thước và rasterize |
| Nghiệp vụ | Karaoke “bất kể quy mô”; nhóm chưa xác minh vẫn ra quyết định | Ngưỡng Annex III được đối chiếu; nhóm thiếu căn cứ chờ kỹ sư |
| Chấm tuân thủ | Không có bằng chứng nhưng quy mô kích hoạt Không đạt/Không bắt buộc | Không tự chấm 16 mục kỹ thuật; cần hồ sơ/bằng chứng |
| Tài liệu nền | Tóm tắt tự sinh bị coi là luật đầy đủ | Metadata chưa xác minh; không đưa catalog mặc định vào RAG |
| Giao diện | Cache chỉ cập nhật một phần; lỗi API vẫn thay dữ liệu; percent như chứng nhận | Đồng bộ dữ liệu, hiển thị lỗi, xếp hàng PATCH, nhãn tiến độ xác nhận |
| Hồ sơ lâu năm | Hard limit 200, mất đường truy cập lịch sử cũ | API phân trang, nút tải thêm lịch sử |
| PDF | Input dài tính chiều cao nhưng vẫn vẽ một dòng; title/note có thể tràn | Báo cáo dùng Paragraph/LongTable, wrap và phân trang |
| Proxy | Nginx timeout nhỏ hơn tổng AI; IP bị gom chung hoặc tin header tùy ý | 100s, trust mạng nội bộ; edge ghi đè forwarded header |
| Deployment | Port backend public; secrets có fallback; không có TLS tích hợp | Caddy HTTPS; DB/backend nội bộ; secrets bắt buộc |
| Database | create_all không có version | Migration baseline tiếp nhận v10 và thêm index |
| Test runner | grep/true có thể nuốt lỗi UI | set -euo pipefail, test thất bại dừng ngay |
| Dependencies | Nhiều advisory ở HTTP/parser/JWT và dependency frontend | Phiên bản đã vá, PyJWT, lockfile, npm ci |
| Backup | Chưa có snapshot nhất quán DB + file | Script dừng writer, dump DB và tar volume |

## Những quyết định nghiệp vụ đáng lưu ý

Đối chiếu bản PDF ký số tại:
https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/5/105-ndcp.signed.pdf
Phụ lục III nằm ở trang 68–69 của PDF (số trang đọc trên trình xem, bắt đầu 1).
Mục 3, 6, 7, 9 có các nhóm khác nhau; không sử dụng một ngưỡng chung cho mọi
công trình. Căn cứ này được dùng để sửa quy tắc v10, chưa có nghĩa toàn bộ văn
bản sửa đổi/phạm vi chuyển tiếp đã được chứng nhận đầy đủ cho mọi công trình.

Không đồng nhất F1.4 với mọi nhà hỗn hợp. Không dùng nghĩa vụ thẩm định để
suy ra thiết kế “không đạt”. Không chứng minh một hệ thống chữa cháy không
bắt buộc chỉ bằng số tầng hay chiều cao. Không khẳng định mọi nội dung thẩm
định đều do Công an thực hiện. Khi thiếu dữ liệu, status là insufficient_data;
boolean false đơn lẻ không phải kết luận miễn thủ tục.

Google model mặc định đã đổi thành `gemini-3.8-flash` theo danh mục chính thức
được kiểm tra ngày 08/10/2026:
https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash
Có thể cấu hình bằng GEMINI_MODELS. Chưa có API key khách hàng để kiểm chứng
quota, quyền truy cập, chất lượng OCR và thời gian xử lý thực tế.

## Kết quả kiểm tra kỹ thuật

| Kiểm tra | Kết quả | Giới hạn |
|---|---|---|
| 40 tình huống | PASS | API + SQLite tạm; AI/OCR fake có chủ đích |
| Fuzz 3.000 hồ sơ | PASS | Rule invariant, không chứng minh toàn bộ luật pháp |
| 6 fixture React | PASS | jsdom, không phải trình duyệt thật trên điện thoại |
| tsc --noEmit | PASS | Kiểm tra type, không thay kiểm tra UX |
| vite build | PASS | Build bundle; chưa chạy image Nginx thật |
| Python compile | PASS | Kiểm tra cú pháp/import |
| Migration | PASS trên SQLite cho baseline/repeat | PostgreSQL/container chưa chạy được tại đây |
| Dependency audit | 0 advisory trong hai lockfile tại lúc chạy | Image OS, CVE chưa công bố và config không nằm trong kết quả này |
| Docker Compose/Caddy/Nginx | Rà soát tĩnh | Không có daemon/binaries để xác nhận runtime |
| Hosting thật, TLS, restore, load | Chưa chạy | Cần môi trường và cấu hình khách hàng |

## Rủi ro còn lại và việc cần xác nhận

- Chưa có bộ rule kỹ thuật được kỹ sư xác nhận theo toàn bộ điều khoản, ngoại
  lệ và chuyển tiếp. Các nhóm chưa hỗ trợ được đánh dấu rà soát thủ công.
- OCR vẫn có thể đọc sai chữ/số, và đối chiếu số trong chat không chứng minh
  đúng trường ngữ nghĩa. Kỹ sư cần xác nhận số liệu AI trước quyết định.
- Token nằm trong localStorage; giảm XSS bằng CSP và render React không đồng
  nghĩa token không thể bị đánh cắp. Có thể triển khai cookie HttpOnly/CSRF
  trong giai đoạn tiếp theo nếu kiến trúc khách hàng yêu cầu.
- Danh sách session đã phân trang; mỗi page vẫn gồm tin nhắn của các hồ sơ.
  Cần tách list metadata/detail nếu hồ sơ có lịch sử rất dài hoặc số user lớn.
- Nhân viên/AI của tổ chức vẫn có thể nạp thông tin sai; thư viện pháp lý custom
  chưa có chữ ký xác minh nguồn và chính sách phê duyệt phiên bản.
- Lock giao dịch ngăn writer cùng hồ sơ nhưng phải đo với PostgreSQL thật;
  chưa có SLA, kiểm thử soak/load hoặc bài tập khôi phục thực tế tại khách hàng.
- Có Docker images dùng tag cập nhật, chưa khóa digest cụ thể; chốt digest và
  quét image trên hạ tầng build của khách hàng trước release chính thức.

Bộ code đã chuẩn bị cho quy trình deploy có cấu hình trong README. Chỉ nghiệm
thu production sau khi hoàn thành kiểm tra trong `DEPLOY_VA_NGHIEM_THU.md`.
