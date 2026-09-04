"""17 core Vietnamese regulatory standards checklist item templates.

Direct port of STANDARDS_CHECKLIST_TEMPLATE from the original server.ts.
"""

STANDARDS_CHECKLIST_TEMPLATE = [
    {
        "stt": 1,
        "criteria": "Thẩm duyệt PCCC bởi Cảnh sát PCCC",
        "requirement": "Bắt buộc thẩm duyệt thiết kế kĩ thuật PCCC bởi Cục/Phòng Cảnh sát PCCC đối với công trình thuộc Phụ lục III - Nghị định 105/2025/NĐ-CP (Nhà hỗn hợp F1.4 cao từ 7 tầng nổi trở lên hoặc tổng diện tích sàn từ 3.000 m² trở lên). Các cơ sở dưới ngưỡng tự thiết kế, tự chịu trách nhiệm và lưu hồ sơ.",
        "reference": "Nghị định 105/2025/NĐ-CP",
    },
    {
        "stt": 2,
        "criteria": "Bậc chịu lửa tối thiểu của nhà",
        "requirement": "Yêu cầu quy chuẩn về bậc chịu lửa tối thiểu dựa theo số tầng và nhóm công năng. Với nhà hỗn hợp F1.4 cao đến 4 tầng, tối thiểu đạt Bậc III (Cột chịu lửa R45, Dầm R45, Sàn REI45, Tường chịu lực REI45). Nhà cao trên 4 tầng yêu cầu bậc II.",
        "reference": "QCVN 06:2022 Phụ lục H",
    },
    {
        "stt": 3,
        "criteria": "Khoảng cách an toàn PCCC lân cận",
        "requirement": "Khoảng cách tối thiểu giữa các nhà từ Bậc III đến nhà khác: >= 8m (hoặc >= 6m nếu tường đối diện đặc chống cháy REI45); đến nhà bậc IV/V: >= 10m; ranh giới đất tách biệt >= 3m không lỗ mở hoặc >= 6m có cửa sổ. Liền kề phố bằng 0 khi tường chung đặc ngăn cháy REI45.",
        "reference": "QCVN 06:2022 Mục 4",
    },
    {
        "stt": 4,
        "criteria": "Tường ngăn cháy bộ phận kinh doanh",
        "requirement": "Khu vực kinh doanh (tầng thấp) bắt buộc ngăn cách hoàn toàn với khu nhà ở phía trên bằng tường ngăn cháy dầy đạt tối thiểu REI 45 hoặc vách chống cháy đạt tiêu chuẩn EI 45; cửa thông liên kết nội bộ phải là cửa chống cháy đạt EI 30 tự động đóng.",
        "reference": "QCVN 06:2022 Mục 4",
    },
    {
        "stt": 5,
        "criteria": "Cầu thang bộ thoát nạn thông thủy",
        "requirement": "Yêu cầu cầu thang bộ thoát hiểm trong nhà cho công trình nhóm F1.4 phải có kích thước chiều rộng thông thủy bản thang >= 1.05m; chiều rộng chiếu nghỉ thang bộ >= chiều rộng bản thang. Cho phép thang bộ hở (loại 2) khi chiều cao PCCC <= 9m.",
        "reference": "QCVN 06:2022 Phần 6",
    },
    {
        "stt": 6,
        "criteria": "Cửa thoát nạn và lối ra tầng 1",
        "requirement": "Lối ra thoát nạn chính tầng 1 trực tiếp ra ngoài đường hoặc qua khoảng sân trống rộng thông thủy >= 0.9m, cửa thoát hiểm phải mở ra hướng thoát nạn (ra ngoài). Nghiêm cấm bố trí kho chứa hàng nguy cơ cháy cao (A, B, C) tại tầng thoát nạn trực tiếp.",
        "reference": "QCVN 06:2022 Phần 6",
    },
    {
        "stt": 7,
        "criteria": "Hệ thống chiếu sáng sự cố & đèn EXIT",
        "requirement": "Bắt buộc trang bị dọc toàn bộ đường thoát nạn, hành lang, buồng thang bộ để định vị và chỉ dẫn lối thoát an toàn khi mất điện. Đèn EXIT chỉ hướng tích hợp pin dự phòng hoạt động liên tục >= 2 giờ, độ rọi trung bình nền >= 1 lux.",
        "reference": "TCVN 13456:2022",
    },
    {
        "stt": 8,
        "criteria": "Bình chữa cháy xách tay trang bị",
        "requirement": "Bắt buộc trang bị đầy đủ bình phát chữa cháy xách tay dạng bột khô ABC (khối lượng >= 4kg) hoặc khí CO2 (>= 3kg). Định mức trang bị tối thiểu 1 bình/tầng, bán kính bảo vệ <= 25m. Gian kinh doanh tầng 1 nguy cơ cao yêu cầu tối thiểu 2 bình chữa cháy.",
        "reference": "QCVN 10:2025 Điều 2.6",
    },
    {
        "stt": 9,
        "criteria": "Hệ thống báo cháy tự động",
        "requirement": "Bắt buộc thiết kế và trang bị hệ thống báo cháy tự động toàn diện liên kết tủ trung tâm điều khiển cho các nhà ở kết hợp kinh doanh thương mại có chiều cao từ 7 tầng nổi trở lên, hoặc nhóm diện tích công cộng quy mô lớn.",
        "reference": "QCVN 10:2025 Phụ lục A",
    },
    {
        "stt": 10,
        "criteria": "Hệ thống báo cháy độc lập liên động",
        "requirement": "Khuyến nghị mạnh mẽ trang bị cho nhà ở kết hợp kinh doanh dưới 7 tầng (khi chưa đạt điều kiện bắt buộc hệ thống tự động). Lắp đặt tối thiểu 1 thiết bị cảm biến cháy độc lập dùng pin tại mỗi phòng ngủ và 1 thiết bị/hành lang, âm thanh liên động còi khẩn cấp.",
        "reference": "QCVN 10:2025 Điều 2.1",
    },
    {
        "stt": 11,
        "criteria": "Hệ thống họng nước chữa cháy trong nhà",
        "requirement": "Công trình hỗn hợp có khối tích tổng cộng từ 5.000 m³ hoặc cao trên 12m yêu cầu trang bị tối thiểu 1 tia phun nước đồng thời, lưu lượng họng đạt >= 2.5 L/s. Khuyến cáo lắp đặt họng vòi DN50 kết nối sẵn lăng tại các chiếu nghỉ lối thang.",
        "reference": "QCVN 10:2025 Bảng H.5",
    },
    {
        "stt": 12,
        "criteria": "Hệ thống sprinkler tự động chữa cháy",
        "requirement": "Yêu cầu trang bị hệ thống đầu phun tự động sprinkler đối với các không gian kinh doanh, dịch vụ thương mại, nhà nghỉ, dã ngoại khi công trình có chiều cao PCCC đạt >= 30m hoặc thuộc diện quy định nguy cơ cháy đặc biệt.",
        "reference": "QCVN 10:2025 Bảng A.1",
    },
    {
        "stt": 13,
        "criteria": "Hệ thống cấp nước và trụ ngoài nhà",
        "requirement": "Bán kính di chuyển từ công trình đến các trụ nước chữa cháy ngoài nhà đô thị không được vượt quá 150m. Trường hợp hạ tầng xung quanh không đáp ứng, công trình phải tự trang bị bể dự trữ nước chữa cháy dung tích tối thiểu >= 18 m³.",
        "reference": "TCVN 2622:1995",
    },
    {
        "stt": 14,
        "criteria": "Khai báo dữ liệu cơ sở PCCC quốc gia",
        "requirement": "Nhà ở kết hợp kinh doanh dịch vụ thuộc danh mục Nghị định 105 phải lập hồ sơ quản lý và hoàn thành thủ tục đăng ký, khai báo thông tin an toàn PCCC lên hệ thống cơ sở dữ liệu quốc gia trước ngày 01/7/2027.",
        "reference": "Nghị định 105/2025/NĐ-CP",
    },
    {
        "stt": 15,
        "criteria": "Thiết bị truyền tin báo cháy sự cố",
        "requirement": "Bắt buộc thi công lắp đặt thiết bị tích hợp truyền nhận thông tin cảnh báo cháy tự động kết nối trực tiếp về Trung tâm tiếp nhận của cơ quan Cảnh sát PCCC tỉnh/thành phố đối với công trình thuộc diện Phụ lục I trước 01/7/2027.",
        "reference": "Nghị định 105/2025/NĐ-CP",
    },
    {
        "stt": 16,
        "criteria": "Bảo hiểm cháy nổ bắt buộc chủ sở hữu",
        "requirement": "Không thuộc diện ép buộc tham gia mua bảo hiểm cháy nổ bắt buộc đối với nhà riêng lẻ kết hợp kinh doanh nhỏ lẻ ngoài Phụ lục VII, tuy nhiên chủ tài sản được khuyến khích mạnh mẽ tham gia tự nguyện bảo vệ rủi ro kinh tế.",
        "reference": "Nghị định 97/2021/NĐ-CP",
    },
    {
        "stt": 17,
        "criteria": "Tự kiểm tra định kỳ an toàn PCCC",
        "requirement": "Chủ sở hữu, chủ cơ sở kinh doanh bắt buộc định kỳ tự rà soát, kiểm tra tình trạng hoạt động thực tế của bình chữa cháy xách tay, đèn EXIT thoát hiểm, lối thoát mở thông thoáng và tự lập hồ sơ lưu trữ theo dõi tối đa 1 tháng/lần.",
        "reference": "Nghị định 105 Quy định XII",
    },
]
