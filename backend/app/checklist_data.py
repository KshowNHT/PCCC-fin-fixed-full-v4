"""17 core Vietnamese regulatory standards checklist item templates (1 Annex III item + 16 QCVN 06/QCVN 10 technical items).

Direct port and upgrade of STANDARDS_CHECKLIST_TEMPLATE for dynamic evaluation by PCCC height, floors, and building volume.
"""

STANDARDS_CHECKLIST_TEMPLATE = [
    {
        "stt": 1,
        "category": "Pháp lý thẩm định",
        "criteria": "Thẩm duyệt PCCC bởi Cảnh sát PCCC",
        "requirement": "Bắt buộc thẩm định thiết kế về PCCC đối với công trình thuộc Phụ lục III Nghị định 105/2025/NĐ-CP (được thay thế bởi Phụ lục III Nghị định 347/2026/NĐ-CP) dựa theo nhóm công năng, số tầng nổi, tổng diện tích sàn và khối tích.",
        "reference": "Nghị định 105/2025/NĐ-CP & Nghị định 347/2026/NĐ-CP",
    },
    {
        "stt": 2,
        "category": "Bậc chịu lửa & Kết cấu",
        "criteria": "Bậc chịu lửa tối thiểu của nhà",
        "requirement": "Bậc chịu lửa tối thiểu của công trình xác định theo chiều cao PCCC, số tầng và khối tích (Phụ lục H QCVN 06:2022/BXD): cao > 50m hoặc > 16 tầng yêu cầu Bậc I; cao > 15m, từ 5 tầng hoặc khối tích >= 5.000 m³ yêu cầu tối thiểu Bậc II; đến 4 tầng (cao <= 15m, khối tích < 5.000 m³) tối thiểu Bậc III.",
        "reference": "QCVN 06:2022/BXD Phụ lục H",
    },
    {
        "stt": 3,
        "category": "Khoảng cách PCCC",
        "criteria": "Khoảng cách an toàn PCCC lân cận",
        "requirement": "Khoảng cách phòng cháy chống cháy tối thiểu giữa các nhà Bậc I, II là >= 6m; đến nhà Bậc III là >= 8m; đến nhà Bậc IV/V là >= 10m (Phụ lục E QCVN 06:2022/BXD). Cho phép giảm hoặc tiếp giáp bằng 0 khi tường ngoài là tường ngăn cháy đặc REI 45–REI 60.",
        "reference": "QCVN 06:2022/BXD Phụ lục E",
    },
    {
        "stt": 4,
        "category": "Ngăn cháy lan",
        "criteria": "Tường ngăn cháy bộ phận kinh doanh",
        "requirement": "Khu vực kinh doanh thương mại, kho hàng phải ngăn cách với khu vực ở và đường thoát nạn bằng tường/vách ngăn cháy tối thiểu EI 45, sàn ngăn cháy REI 45 và cửa ngăn cháy EI 30 có cơ cấu tự đóng.",
        "reference": "QCVN 06:2022/BXD Mục 4",
    },
    {
        "stt": 5,
        "category": "Lối thoát nạn",
        "criteria": "Cầu thang bộ thoát nạn thông thủy",
        "requirement": "Chiều rộng thông thủy bản thang thoát nạn >= 1,05m (công cộng/karaoke >= 1,20m). Khi chiều cao PCCC > 28m bắt buộc buồng thang không nhiễm khói N1/N2/N3; khi 9m < chiều cao PCCC <= 28m bắt buộc buồng thang bộ kín L1/L2; chiều cao PCCC <= 9m cho phép thang bộ loại 2.",
        "reference": "QCVN 06:2022/BXD Phần 3 & Phần 6",
    },
    {
        "stt": 6,
        "category": "Lối thoát nạn",
        "criteria": "Cửa thoát nạn và lối ra tầng 1",
        "requirement": "Lối ra thoát nạn tầng 1 phải dẫn trực tiếp ra ngoài hoặc qua sảnh an toàn; cửa thoát nạn mở theo chiều thoát nạn, chiều rộng thông thủy >= 0,90m. Nhà từ 7 tầng, cao > 21m, diện tích tầng > 300 m² hoặc khối tích >= 5.000 m³ bắt buộc tối thiểu 02 lối thoát nạn/tầng.",
        "reference": "QCVN 06:2022/BXD Mục 3.2",
    },
    {
        "stt": 7,
        "category": "Chỉ dẫn thoát nạn",
        "criteria": "Hệ thống chiếu sáng sự cố & đèn EXIT",
        "requirement": "Bắt buộc trang bị đèn chiếu sáng sự cố (độ rọi nền >= 1 lux) và biển báo chỉ dẫn thoát nạn EXIT (nguồn điện dự phòng hoạt động liên tục >= 2 giờ) dọc hành lang, buồng thang bộ và cửa thoát hiểm.",
        "reference": "TCVN 13456:2022 & QCVN 06:2022/BXD",
    },
    {
        "stt": 8,
        "category": "Phương tiện ban đầu",
        "criteria": "Bình chữa cháy xách tay trang bị",
        "requirement": "Trang bị đầy đủ bình chữa cháy xách tay bột khô ABC (>= 4kg) hoặc khí CO2 (>= 3kg) theo định mức diện tích sàn và số tầng (tối thiểu 2 bình/tầng, định mức 1 cụm bình/50–100 m², bán kính bảo vệ <= 20–25m).",
        "reference": "QCVN 10:2025/BCA Điều 2.6 & TCVN 3890:2023",
    },
    {
        "stt": 9,
        "category": "Hệ thống báo cháy",
        "criteria": "Hệ thống báo cháy tự động",
        "requirement": "Bắt buộc trang bị hệ thống báo cháy tự động trung tâm đối với nhà hỗn hợp/dân dụng cao từ 7 tầng trở lên, chiều cao PCCC >= 25m, tổng diện tích sàn >= 3.000 m², khối tích >= 5.000 m³, hoặc cơ sở karaoke/thương mại nguy cơ cháy cao.",
        "reference": "QCVN 10:2025/BCA Phụ lục A",
    },
    {
        "stt": 10,
        "category": "Hệ thống báo cháy",
        "criteria": "Hệ thống báo cháy độc lập liên động",
        "requirement": "Đối với công trình dưới ngưỡng bắt buộc hệ thống báo cháy tự động trung tâm (< 7 tầng, cao PCCC < 25m, khối tích < 5.000 m³), trang bị đầu báo khói/nhiệt độc lập hoặc liên động không dây tại từng tầng và gian kinh doanh.",
        "reference": "QCVN 10:2025/BCA Điều 2.1",
    },
    {
        "stt": 11,
        "category": "Hệ thống chữa cháy",
        "criteria": "Hệ thống họng nước chữa cháy trong nhà",
        "requirement": "Công trình có khối tích từ 5.000 m³ trở lên, chiều cao PCCC > 12m (hoặc từ 5 tầng trở lên), hoặc cơ sở karaoke bắt buộc trang bị hệ thống họng nước chữa cháy trong nhà (tối thiểu 1–2 tia phun đồng thời, lưu lượng >= 2,5 L/s, họng DN50/DN65).",
        "reference": "QCVN 10:2025/BCA Phụ lục B & QCVN 06:2022/BXD",
    },
    {
        "stt": 12,
        "category": "Hệ thống chữa cháy",
        "criteria": "Hệ thống sprinkler tự động chữa cháy",
        "requirement": "Bắt buộc trang bị hệ thống chữa cháy tự động Sprinkler đối với công trình có chiều cao PCCC >= 25m (hoặc >= 10 tầng), khối tích >= 15.000 m³, cơ sở karaoke/vũ trường, hoặc tầng hầm/nhà kho/xưởng quy mô lớn.",
        "reference": "QCVN 10:2025/BCA Bảng A.1",
    },
    {
        "stt": 13,
        "category": "Cấp nước chữa cháy",
        "criteria": "Hệ thống cấp nước và trụ ngoài nhà",
        "requirement": "Đảm bảo cấp nước chữa cháy ngoài nhà theo khối tích công trình (lưu lượng 10–20 L/s): bán kính từ công trình đến trụ nước chữa cháy đô thị <= 150m; trường hợp không đảm bảo phải xây dựng bể nước chữa cháy dự trữ >= 18–108 m³.",
        "reference": "QCVN 06:2022/BXD Phần 5 & QCVN 10:2025/BCA",
    },
    {
        "stt": 14,
        "category": "Quản lý vận hành",
        "criteria": "Khai báo dữ liệu cơ sở PCCC quốc gia",
        "requirement": "Cơ sở thuộc diện quản lý PCCC phải lập hồ sơ quản lý, theo dõi hoạt động PCCC và hoàn thành thủ tục khai báo, cập nhật dữ liệu lên hệ thống Cơ sở dữ liệu quốc gia về PCCC.",
        "reference": "Nghị định 105/2025/NĐ-CP",
    },
    {
        "stt": 15,
        "category": "Quản lý vận hành",
        "criteria": "Thiết bị truyền tin báo cháy sự cố",
        "requirement": "Bắt buộc lắp đặt thiết bị truyền tin báo cháy sự cố kết nối với hệ thống Cơ sở dữ liệu về PCCC và truyền tin báo cháy của cơ quan Cảnh sát PCCC đối với công trình thuộc diện thẩm định / báo cháy tự động.",
        "reference": "Nghị định 105/2025/NĐ-CP",
    },
    {
        "stt": 16,
        "category": "Quản lý vận hành",
        "criteria": "Bảo hiểm cháy nổ bắt buộc chủ sở hữu",
        "requirement": "Cơ sở có nguy hiểm về cháy, nổ thuộc danh mục quy định bắt buộc phải mua bảo hiểm cháy, nổ bắt buộc đối với tài sản của cơ sở; các cơ sở quy mô nhỏ khuyến khích tham gia tự nguyện.",
        "reference": "Nghị định 105/2025/NĐ-CP & Nghị định 67/2023/NĐ-CP",
    },
    {
        "stt": 17,
        "category": "Quản lý vận hành",
        "criteria": "Tự kiểm tra định kỳ an toàn PCCC",
        "requirement": "Chủ sở hữu, người đứng đầu cơ sở có trách nhiệm tổ chức tự kiểm tra an toàn PCCC định kỳ (tối thiểu 1 tháng/lần), bảo dưỡng bình chữa cháy, đèn EXIT, hệ thống điện và duy trì lối thoát nạn thông thoáng.",
        "reference": "Nghị định 105/2025/NĐ-CP",
    },
]

