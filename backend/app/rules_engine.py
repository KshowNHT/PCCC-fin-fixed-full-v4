"""Rules Engine (Decision Tree) — Ngày 18-21 kế hoạch:

'Code Rules Engine (Decision Trees) đối chiếu quy định cứng QCVN 06:2022/BXD.'
'Đóng vai trò "Kỹ sư thẩm định". Ra kết luận cuối cùng (Đạt/Chưa đạt/Cần bổ
sung) và tự động xuất báo cáo liệt kê lỗi thiết kế.'

`evaluate_appraisal()` là cây quyết định (decision tree) offline, không phụ
thuộc LLM: mỗi nhánh if/elif ứng với một quy tắc cứng đối chiếu QCVN
06:2022/BXD, QCVN 10:2025/BCA, Nghị định 105/2025/NĐ-CP cho từng mục trong
17 hạng mục checklist. Dùng làm (a) fallback khi Gemini lỗi/quá tải, và
(b) nguồn tham chiếu "ground truth" để đối chiếu kết quả LLM trả về.

=== FIX B12 (Bao_Cao_QA_Lan_3.md — NGHIÊM TRỌNG) ===
Trước đây hàm này KHÔNG hề đọc `project["type"]` — công năng công trình bị
bỏ qua hoàn toàn. QA lần 3 đã chứng minh: quán karaoke 5 tầng, nhà ở dân
dụng 5 tầng, và nhà kho 5 tầng cùng diện tích cho ra kết quả 17 mục GIỐNG
HỆT NHAU và đều "không bắt buộc thẩm duyệt". Đây là rủi ro pháp lý thật —
karaoke/vũ trường tại Việt Nam chịu giám sát PCCC nghiêm ngặt hơn hẳn nhà
hỗn hợp thông thường (Thông tư 147/2020/TT-BCA, siết chặt thêm sau hàng
loạt vụ cháy karaoke gây chết người 2022-2023), không thể áp chung ngưỡng
"7 tầng hoặc 3.000m²" của nhóm F1.4.

Hàm `_classify_building_category()` mới phân loại công năng theo từ khoá
trong `type`/`commercialDetails`, rồi `evaluate_appraisal()` áp ngưỡng khác
nhau theo từng nhóm. MINH BẠCH QUAN TRỌNG: các ngưỡng số cụ thể cho nhóm
kho/chợ/trường học dưới đây là ƯỚC LƯỢNG THẬN TRỌNG (an toàn hơn là bỏ sót)
dựa trên đặc điểm nguy cơ cháy của từng loại hình, KHÔNG thay thế được việc
đối chiếu trực tiếp bảng phân loại nhóm nguy hiểm cháy nổ trong QCVN
06:2022/BXD bởi kỹ sư PCCC có chứng chỉ hành nghề — hệ thống luôn gắn kèm
cảnh báo yêu cầu rà soát thủ công cho các nhóm này và nhóm "chưa phân loại
được", đúng khuyến nghị của QA (ưu tiên #2).

Cũng chứa RAG context builder (getRagContextForProject) và cơ chế học từ
lịch sử dự án tương đồng (getPriorProjectsContext) — port từ server.ts gốc.
"""
from typing import Any, Dict, List, Optional

from app.checklist_data import STANDARDS_CHECKLIST_TEMPLATE

# FIX B12: các nhóm công năng được phân loại riêng, thứ tự kiểm tra có ý
# nghĩa (karaoke kiểm tra trước "kinh doanh" chung chung vì 1 quán karaoke
# vẫn có thể tự mô tả là "dịch vụ kinh doanh").
_CATEGORY_KEYWORDS = {
    "karaoke_entertainment": ("karaoke", "vũ trường", "quán bar", "disco", "vu truong", "bar/pub", "vũ trường"),
    "warehouse": ("nhà kho", "kho chứa", "giá kệ", "kệ cao", "warehouse", " kho "),
    "market_mall": ("chợ", "trung tâm thương mại", "siêu thị", "ttmm", "market", "shopping"),
    "school": ("trường học", "mầm non", "tiểu học", "trung học", "school", "nhà trẻ"),
    "mixed_residential": ("nhà hỗn hợp", "nhà ở kết hợp kinh doanh", "chung cư", "nhà ở riêng lẻ", "văn phòng"),
}


def _classify_building_category(project: Dict[str, Any]) -> str:
    text = f"{project.get('type') or ''} {project.get('commercialDetails') or ''}".lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            return category
    return "unclassified"


def _appraisal_threshold_for_category(category: str, floors: int, total_floor_area: float, height: float) -> tuple:
    """Trả về (is_subject: bool, reason: str, category_warning: Optional[str])
    theo đúng nhóm công năng — thay cho ngưỡng cứng duy nhất trước đây."""
    if category == "karaoke_entertainment":
        # FIX B12: karaoke/vũ trường/quán bar LUÔN thuộc diện khuyến nghị
        # thẩm duyệt bất kể quy mô — không áp ngưỡng diện tích/tầng như nhà
        # hỗn hợp thông thường, do lịch sử nguy cơ cháy đặc biệt cao và quy
        # định siết chặt riêng (Thông tư 147/2020/TT-BCA và các văn bản sửa
        # đổi sau 2022). Đây là lựa chọn AN TOÀN CHỦ ĐỘNG (fail-safe): thà
        # yêu cầu thẩm duyệt dư còn hơn bỏ sót một cơ sở nguy cơ cao.
        return (
            True,
            "Công trình có công năng kinh doanh dịch vụ karaoke/vũ trường/quán bar — nhóm ngành thuộc diện giám "
            "sát PCCC đặc biệt nghiêm ngặt theo Thông tư 147/2020/TT-BCA (đã được sửa đổi bổ sung siết chặt hơn "
            "sau các vụ cháy nghiêm trọng). Hệ thống mặc định khuyến nghị BẮT BUỘC thẩm duyệt thiết kế bởi cơ "
            "quan Cảnh sát PCCC bất kể quy mô diện tích/số tầng, KHÔNG áp dụng ngưỡng của nhóm nhà hỗn hợp "
            "thông thường (F1.4). Cần đối chiếu trực tiếp Thông tư 147/2020/TT-BCA và văn bản sửa đổi mới nhất.",
            None,
        )

    if category == "warehouse":
        is_subject = floors >= 1 and (total_floor_area >= 1000 or height >= 25)
        return (
            is_subject,
            (
                f"Công trình là nhà kho/kho chứa hàng — quy mô {total_floor_area}m² sàn / cao {height}m vượt "
                "ngưỡng thận trọng cho nhóm kho hàng (ước lượng an toàn, chưa xét nhóm nguy hiểm cháy nổ cụ thể "
                "của hàng hoá lưu trữ), khuyến nghị thẩm duyệt thiết kế PCCC."
                if is_subject
                else f"Công trình kho quy mô {total_floor_area}m² sàn / cao {height}m dưới ngưỡng thận trọng — "
                "tuy nhiên BẮT BUỘC xác định nhóm nguy hiểm cháy nổ của hàng hoá lưu trữ (A/B/C/D/E theo QCVN "
                "06:2022/BXD) trước khi kết luận cuối cùng, vì kho chứa hàng nhóm A/B/C có thể yêu cầu thẩm "
                "duyệt ở quy mô nhỏ hơn nhiều."
            ),
            "Nhóm nhà kho: hệ thống CHƯA có dữ liệu về nhóm nguy hiểm cháy nổ của hàng hoá lưu trữ (A/B/C/D/E). "
            "BẮT BUỘC kỹ sư PCCC rà soát thủ công đối chiếu QCVN 06:2022/BXD trước khi sử dụng kết luận này.",
        )

    if category == "market_mall":
        is_subject = total_floor_area >= 1500 or floors >= 3
        return (
            is_subject,
            f"Công trình chợ/trung tâm thương mại/siêu thị quy mô {total_floor_area}m² sàn, {floors} tầng — "
            f"{'vượt' if is_subject else 'dưới'} ngưỡng thận trọng cho nhóm mật độ người sử dụng cao, "
            f"{'khuyến nghị thẩm duyệt thiết kế PCCC.' if is_subject else 'vẫn cần tự rà soát đầy đủ QCVN 06:2022/BXD Bảng H.5.'}",
            None,
        )

    if category == "school":
        is_subject = floors >= 3 or total_floor_area >= 1500
        return (
            is_subject,
            f"Công trình trường học/cơ sở giáo dục quy mô {floors} tầng, {total_floor_area}m² sàn — "
            f"{'vượt' if is_subject else 'dưới'} ngưỡng thận trọng cho nhóm công trình có trẻ em/học sinh (khả "
            f"năng thoát nạn hạn chế), {'khuyến nghị thẩm duyệt thiết kế PCCC.' if is_subject else 'vẫn cần tự rà soát an toàn thoát nạn kỹ lưỡng.'}",
            None,
        )

    if category == "mixed_residential":
        is_subject = floors >= 7 or total_floor_area >= 3000
        return (
            is_subject,
            "Quy mô diện tích sàn >= 3.000m² hoặc số tầng >= 7 bắt buộc thẩm duyệt thiết kế PCCC theo Nghị "
            "định 105/2025/NĐ-CP (nhóm nhà hỗn hợp/nhà ở kết hợp kinh doanh F1.4)."
            if is_subject
            else "Quy mô số tầng < 7 và diện tích sàn < 3.000m² không thuộc diện bắt buộc thẩm duyệt PCCC Công "
            "an theo Nghị định 105/2025/NĐ-CP (nhóm nhà hỗn hợp F1.4), chỉ cần tự rà soát.",
            None,
        )

    # "unclassified": KHÔNG âm thầm dùng ngưỡng F1.4 mặc định như bug cũ —
    # vẫn tính theo ngưỡng chung để có kết quả tham khảo, nhưng LUÔN đính
    # kèm cảnh báo rõ ràng rằng công năng chưa được hệ thống nhận diện.
    is_subject = floors >= 7 or total_floor_area >= 3000
    return (
        is_subject,
        "CHƯA XÁC ĐỊNH được nhóm công năng cụ thể từ thông tin đã nhập — hệ thống tạm áp ngưỡng chung của nhà "
        f"hỗn hợp (7 tầng/3.000m² sàn) để tham khảo: {total_floor_area}m² sàn, {floors} tầng "
        f"{'vượt ngưỡng, khuyến nghị thẩm duyệt.' if is_subject else 'dưới ngưỡng tham khảo.'}",
        "Hệ thống CHƯA nhận diện được nhóm công năng cụ thể của công trình này từ mô tả đã nhập. Kết luận trên "
        "chỉ mang tính tham khảo theo ngưỡng chung — BẮT BUỘC kỹ sư PCCC có chứng chỉ hành nghề rà soát thủ "
        "công trước khi sử dụng làm căn cứ, đặc biệt nếu công trình thuộc nhóm nguy cơ cháy đặc biệt (karaoke, "
        "vũ trường, kho hoá chất, gara ô tô, cơ sở y tế nội trú...).",
    )


def evaluate_appraisal(project: Dict[str, Any]) -> Dict[str, Any]:
    floors = project.get("floors") or 0
    total_floor_area = project.get("totalFloorArea") or 0
    floor_area = project.get("floorArea") or 0
    fire_rating = project.get("fireRating")
    pccc_height = project.get("pcccHeight") or 0
    height = project.get("height") or 0

    # FIX B12: phân loại công năng trước khi tính is_subject — không còn
    # dùng chung 1 ngưỡng "7 tầng/3.000m²" cho mọi loại công trình.
    category = _classify_building_category(project)
    is_subject, appraisal_reason, category_warning = _appraisal_threshold_for_category(
        category, floors, total_floor_area, height
    )

    checklist = []
    for t in STANDARDS_CHECKLIST_TEMPLATE:
        stt = t["stt"]
        result = "Cần xem xét"
        note = "Chưa đủ dữ liệu rà soát chuyên nghiệp."

        if stt == 1:
            result = "Không đạt" if is_subject else "Không bắt buộc"
            # FIX B12: note mục 1 giờ phản ánh ĐÚNG nhóm công năng đã phân loại,
            # không còn mô tả chung chung "công trình quy mô lớn" cho mọi loại hình.
            note = appraisal_reason
        elif stt == 2:
            if floors > 4:
                result = "Đạt" if fire_rating in ("Bậc I", "Bậc II") else "Không đạt"
                note = f"Nhà cao trên 4 tầng bắt buộc bậc chịu lửa II trở lên. Hiện tại khai báo: {fire_rating or 'Chưa chọn'}."
            else:
                result = "Đạt"
                note = f"Cho phép đạt Bậc III cho công trình dưới 4 tầng. Hiện tại khai báo: {fire_rating or 'Bậc III'}."
        elif stt == 3:
            result = "Cần đo đạc"
            note = "Yêu cầu khoảng cách an toàn đến nhà lân cận tối thiểu 8m (Bậc III) hoặc 6m (Tường đặc chống cháy REI 45)."
        elif stt == 4:
            result = "Khuyến nghị mạnh"
            note = "Gian kinh doanh thương mại tại tầng 1 phải ngăn cách hoàn toàn bằng tường ngăn cháy EI 45 và cửa chống cháy tự đóng EI 30."
        elif stt == 5:
            result = "Cần đo đạc"
            note = "Đo đạc kiểm tra chiều rộng thông thủy bản thang bộ tối thiểu đạt 1.05m và chiều rộng chiếu nghỉ."
        elif stt == 6:
            result = "Cần xem xét"
            note = "Cửa lối ra thoát nạn tầng 1 mở ra hướng thoát nạn, chiều rộng thông thủy >= 0.9m. Không để kho hàng tại sảnh thoát."
        elif stt == 7:
            result = "Khuyến nghị mạnh"
            note = "Yêu cầu lắp dọc đường thoát lối đi, chiếu nghỉ cầu thang bằng đèn EXIT và chiếu sáng sự cố thời lượng cứu hộ >= 2h."
        elif stt == 8:
            result = "Khuyến nghị mạnh"
            note = "Bắt buộc trang bị bình bột chữa cháy xách tay ABC >= 4kg (mỗi tầng tối thiểu 1 bình; tầng kinh doanh tối thiểu 2 bình)."
        elif stt == 9:
            # FIX B12: karaoke/vũ trường bắt buộc báo cháy tự động ở mọi quy mô
            # (không chỉ từ 7 tầng như nhóm nhà hỗn hợp) do đặc thù đông người,
            # ánh sáng/âm thanh lớn làm giảm khả năng nhận biết cháy sớm.
            requires_auto_alarm = floors >= 7 or category == "karaoke_entertainment"
            if requires_auto_alarm:
                result = "Không đạt"
                note = (
                    "Karaoke/vũ trường BẮT BUỘC trang bị hệ thống báo cháy tự động bất kể số tầng, do đặc thù "
                    "phòng cách âm, ánh sáng/âm thanh lớn làm giảm khả năng người bên trong tự nhận biết cháy sớm."
                    if category == "karaoke_entertainment"
                    else "Bắt buộc phải trang bị hệ thống báo cháy tự động liên tủ trung tâm cho nhà cao từ 7 tầng trở lên."
                )
            else:
                result = "Không bắt buộc"
                note = "Nhà quy mô nhỏ dưới 7 tầng không cưỡng bức trang bị hệ thống liên thông báo cháy tự động toàn diện."
        elif stt == 10:
            result = "Khuyến nghị mạnh" if floors < 7 else "Không bắt buộc"
            note = (
                "Khuyên lắp cảm biến khói độc lập dùng pin tại các hành lang và từng phòng ngủ để phản ứng nhanh bảo vệ tính mạng."
                if floors < 7
                else "Nên ưu tiên hệ thống báo cháy tự động tập trung."
            )
        elif stt == 11:
            is_volume_required = (floor_area * floors) >= 5000 or height > 12
            result = "Không đạt" if is_volume_required else "Khuyến nghị"
            note = (
                f"Chiều cao {height}m hoặc khối tích lớn yêu cầu thiết kế hệ thống họng nước chữa cháy trong nhà kết nối DN50."
                if is_volume_required
                else "Dưới ngưỡng bắt buộc trang bị họng nước vòi rồng. Khuyên lắp vòi mềm hoặc bình khí dự phòng phụ."
            )
        elif stt == 12:
            result = "Không đạt" if pccc_height >= 30 else "Không bắt buộc"
            note = (
                "Bắt buộc trang bị hệ thống đầu phun chữa cháy sprinkler tự động khi chiều cao thiết kế PCCC >= 30m."
                if pccc_height >= 30
                else "Không bắt buộc sprinkler tự động theo chiều cao (dưới 30m). Có thể trang bị tự nguyện tại tầng kinh doanh."
            )
        elif stt == 13:
            result = "Cần xem xét"
            note = "Bán kính tiếp cận từ trụ nước chữa cháy công cộng ngoài đường <= 150m, nếu không có phải tự làm bể chứa >= 18 m³."
        elif stt == 14:
            result = "Khuyến nghị"
            note = "Hoàn thành thủ tục đăng ký dữ liệu an toàn PCCC lên hệ thống thông tin quốc gia trước ngày 01/7/2027."
        elif stt == 15:
            result = "Cần xem xét"
            note = "Lắp thiết bị cảnh báo cháy sớm truyền tin trực tiếp về Trung tâm điều hành PCCC nếu thuộc diện Phụ lục C Nghị định 105."
        elif stt == 16:
            result = "Khuyến nghị"
            note = "Khuyến khích chủ hộ kinh doanh tham gia bảo hiểm cháy nổ tự nguyện bảo vệ giá trị đầu tư tài sản thương mại."
        elif stt == 17:
            result = "Khuyến nghị mạnh"
            note = "Định kỳ ít nhất 1 tháng/lần tự kiểm tra, lập sổ theo dõi bình bọt chữa cháy, tình trạng đèn EXIT và sảnh thoát nạn."

        checklist.append(
            {
                "stt": stt,
                "category": t["criteria"],
                "criteria": t["criteria"],
                "requirement": t["requirement"],
                "note": note,
                "result": result,
                "reference": t["reference"],
            }
        )

    warnings: List[str] = []
    if is_subject:
        warnings.append(
            "Thiết kế quy mô lớn bậc chịu lửa và lối thoát hiểm cần có chữ ký tư vấn được cấp chứng chỉ hành nghề."
        )
    if floors > 0 and floor_area > 0 and abs(total_floor_area - (floor_area * floors)) > 10:
        warnings.append(
            "Tổng diện tích sàn khai báo không trùng khớp với tích số giữa (diện tích sàn x số tầng), cần đối chiếu kiểm tra thực tế."
        )
    # FIX B12: đính kèm cảnh báo riêng cho nhóm kho / chưa phân loại được —
    # bắt buộc rà soát thủ công, không để hệ thống "tự tin" kết luận thay
    # kỹ sư có chứng chỉ hành nghề cho các nhóm công năng rủi ro cao.
    if category_warning:
        warnings.append(category_warning)

    return {
        "warnings": warnings,
        "checklist": checklist,
        "isSubjectToAppraisal": is_subject,
        "appraisalReason": appraisal_reason,
        "buildingCategory": category,
    }


def get_local_fallback_response(project: Dict[str, Any]) -> Dict[str, Any]:
    """FIX B11 (Bao_Cao_QA_Lan_3.md — NGHIÊM TRỌNG): trước đây câu 'reply'
    hứa hẹn "Dưới đây là kết quả rà soát..." nhưng KHÔNG có nội dung gì theo
    sau NGAY TRONG KHUNG CHAT — 17 mục checklist thật ra hiển thị ở bảng
    riêng (specs panel), không phải trong bong bóng chat. Người dùng đọc
    "Dưới đây là..." rồi thấy trống → tưởng phần mềm hỏng hoàn toàn, dù dữ
    liệu rà soát vẫn có đầy đủ và đúng ở nơi khác trên giao diện.

    Sửa: 'reply' giờ TỰ CHỨA một bản tóm tắt ngắn gọn ngay trong khung chat
    (không phụ thuộc người dùng phải tìm đúng bảng khác), đồng thời nói rõ
    lý do (thiếu/lỗi cấu hình GEMINI_API_KEY hoặc dịch vụ Google gặp sự cố)
    thay vì chỉ nói chung chung "lỗi kết nối hoặc giới hạn".
    """
    result = evaluate_appraisal(project)
    non_compliant = [c["criteria"] for c in result["checklist"] if c["result"] == "Không đạt"]
    subject_text = "BẮT BUỘC thẩm duyệt thiết kế PCCC" if result["isSubjectToAppraisal"] else "KHÔNG bắt buộc thẩm duyệt (Công an)"

    summary_lines = [
        "⚠️ Hệ thống AI (Gemini) hiện không phản hồi được — có thể do chưa cấu hình GEMINI_API_KEY, hết hạn "
        "mức sử dụng, hoặc dịch vụ Google đang gián đoạn. Hệ thống đã TỰ ĐỘNG chuyển sang bộ luật cứng "
        "(rules engine nội bộ, không cần AI) để bạn vẫn có kết quả rà soát ngay lập tức:",
        "",
        f"• Kết luận: công trình {subject_text}.",
    ]
    if non_compliant:
        summary_lines.append(f"• {len(non_compliant)} hạng mục CHƯA ĐẠT: {', '.join(non_compliant)}.")
    else:
        summary_lines.append("• Không có hạng mục nào bị đánh giá KHÔNG ĐẠT theo bộ luật cứng.")
    summary_lines.append("• Xem đầy đủ 17 hạng mục kèm giải trình chi tiết trong bảng bên dưới/panel thông số dự án.")
    summary_lines.append(
        "Lưu ý: kết quả trên chỉ dựa vào công thức cố định, CHƯA có phân tích ngữ cảnh sâu như khi AI hoạt "
        "động bình thường — khuyến nghị thử lại sau hoặc liên hệ quản trị viên kiểm tra cấu hình dịch vụ AI."
    )

    return {
        "reply": "\n".join(summary_lines),
        "warnings": result["warnings"],
        "isSubjectToAppraisal": result["isSubjectToAppraisal"],
        "appraisalReason": result["appraisalReason"],
        "checklist": result["checklist"],
        "extractedProjectInfo": project,
    }


def get_rag_context_for_project(project: Dict[str, Any], document_database: List[Dict[str, Any]]) -> str:
    query_words: List[str] = []

    project_type = (project.get("type") or "").lower()
    if project_type:
        if any(k in project_type for k in ("karaoke", "vũ trường", "hát")):
            query_words += ["karaoke", "thông tư 147", "147/2020"]
        elif any(k in project_type for k in ("gara", "ô tô")):
            query_words += ["gara", "quy chuẩn 13", "qcvn 13:2018"]
        elif any(k in project_type for k in ("kho", "giá đỡ", "kệ")):
            query_words += ["nhà kho", "kho chứa", "giá đỡ", "kệ cao", "ngăn cháy"]
        elif any(k in project_type for k in ("chợ", "thương mại", "siêu thị")):
            query_words += ["chợ", "bảng h.5", "tổng diện tích", "trung tâm thương mại"]
        elif any(k in project_type for k in ("hỗn hợp", "kinh doanh", "văn phòng")):
            query_words += ["hỗn hợp", "f1.4", "kinh doanh", "tường ngăn cháy"]

    query_words += ["qcvn 06", "qcvn 10", "nghị định 105", "phụ lục iii"]

    matched_docs = []
    for d in document_database:
        text_to_search = f"{d.get('code', '')} {d.get('title', '')} {d.get('content', '')}".lower()
        if any(word in text_to_search for word in query_words):
            matched_docs.append(d)

    if matched_docs:
        return "\n\n".join(
            f"[TÀI LIỆU CỐT LÕI: {d.get('code')} - {d.get('title')}]\n{d.get('content')}"
            for d in matched_docs[:4]
        )

    return "Không tìm thấy tài liệu phù hợp trực tiếp, ưu tiên áp dụng QCVN 06:2022 và QCVN 10:2025."


def get_prior_projects_context(
    project: Dict[str, Any],
    chat_sessions: List[Dict[str, Any]],
    current_session_id: Optional[str] = None,
) -> str:
    scored = []
    for s in chat_sessions:
        if s.get("id") == current_session_id:
            continue
        sp = s.get("projectInfo")
        if not sp or not s.get("checklist"):
            continue

        score = 0
        if sp.get("type") == project.get("type"):
            score += 30
        if sp.get("floors") == project.get("floors"):
            score += 20
        diff_area = abs((sp.get("totalFloorArea") or 0) - (project.get("totalFloorArea") or 0))
        if diff_area < 50:
            score += 25
        elif diff_area < 200:
            score += 15
        if sp.get("fireRating") == project.get("fireRating"):
            score += 15
        if sp.get("basements") == project.get("basements"):
            score += 10

        if score >= 30:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    similar = [s for _, s in scored[:3]]

    if not similar:
        return "Không có dự án tương đồng nào trong lịch sử trước đây để đối chiếu học hỏi."

    context = (
        "DƯỚI ĐÂY LÀ CÁC CÔNG TRÌNH TƯƠNG ĐỒNG ĐÃ ĐƯỢC KIỂM TRA TRONG LỊCH SỬ (HỆ THỐNG CẦN HỌC HỎI CÁC "
        "THÔNG SỐ VÀ KẾT QUẢ ĐÃ DUYỆT ĐỂ KIỂM TRA NHANH HƠN VÀ ĐỒNG NHẤT KHÔNG CẦN TÍNH TOÁN LẠI TỪ ĐẦU):\n"
    )
    for idx, entry in enumerate(similar):
        sp = entry.get("projectInfo", {})
        context += f"\n[Mẫu Học tập {idx + 1}]"
        context += f"\n- Tên công trình trước: {sp.get('name')}"
        context += (
            f"\n- Quy mô: {sp.get('floors')} tầng nổi, {sp.get('basements')} tầng hầm, "
            f"diện tích sàn: {sp.get('floorArea')} m2, tổng diện tích: {sp.get('totalFloorArea')} m2."
        )
        context += f"\n- Loại hình: {sp.get('type')}, Bậc chịu lửa: {sp.get('fireRating')}"
        context += f"\n- Thẩm duyệt Công an bắt buộc: {'Bắt buộc' if entry.get('isSubjectToAppraisal') else 'Không bắt buộc'}"
        context += f"\n- Lý do thẩm duyệt: {entry.get('appraisalReason')}"

        checklist = entry.get("checklist")
        if checklist:
            non_compliant = ", ".join(c["criteria"] for c in checklist if c.get("result") == "Không đạt")
            compliant = ", ".join(c["criteria"] for c in checklist if c.get("result") == "Đạt")
            context += f"\n- Các mục ĐẠT của công trình trước: {compliant or 'Không'}"
            context += f"\n- Các mục KHÔNG ĐẠT của công trình trước: {non_compliant or 'Không'}"
        context += "\n"

    return context
