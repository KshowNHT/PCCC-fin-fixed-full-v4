"""Rules Engine (Decision Tree) — Ngày 18-21 kế hoạch:

'Code Rules Engine (Decision Trees) đối chiếu quy định cứng QCVN 06:2022/BXD.'
'Đóng vai trò "Kỹ sư thẩm định". Ra kết luận cuối cùng (Đạt/Chưa đạt/Cần bổ
sung) và tự động xuất báo cáo liệt kê lỗi thiết kế.'

`evaluate_appraisal()` là cây quyết định (decision tree) offline, không phụ
thuộc LLM: mỗi nhánh if/elif ứng với một quy tắc cứng đối chiếu QCVN
06:2022/BXD, QCVN 10:2025/BCA, Nghị định 105/2025/NĐ-CP cho từng mục trong
17 hạng mục checklist. Dùng làm (a) fallback khi Gemini lỗi/quá tải, và
(b) nguồn tham chiếu "ground truth" để đối chiếu kết quả LLM trả về.

Cũng chứa RAG context builder (getRagContextForProject) và cơ chế học từ
lịch sử dự án tương đồng (getPriorProjectsContext) — port từ server.ts gốc.
"""
from typing import Any, Dict, List, Optional

from app.checklist_data import STANDARDS_CHECKLIST_TEMPLATE


def evaluate_appraisal(project: Dict[str, Any]) -> Dict[str, Any]:
    floors = project.get("floors") or 0
    total_floor_area = project.get("totalFloorArea") or 0
    floor_area = project.get("floorArea") or 0
    fire_rating = project.get("fireRating")
    pccc_height = project.get("pcccHeight") or 0
    height = project.get("height") or 0

    is_subject = floors >= 7 or total_floor_area >= 3000

    checklist = []
    for t in STANDARDS_CHECKLIST_TEMPLATE:
        stt = t["stt"]
        result = "Cần xem xét"
        note = "Chưa đủ dữ liệu rà soát chuyên nghiệp."

        if stt == 1:
            result = "Không đạt" if is_subject else "Không bắt buộc"
            note = (
                f"Công trình quy mô lớn ({floors} tầng, {total_floor_area}m² sàn) bắt buộc nộp hồ sơ "
                "thẩm duyệt thiết kế PCCC tại Cảnh sát PCCC."
                if is_subject
                else "Không thuộc diện bắt buộc thẩm duyệt cơ quan công an. Chủ đầu tư tự thiết kế và chịu trách nhiệm."
            )
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
            if floors >= 7:
                result = "Không đạt"
                note = "Bắt buộc phải trang bị hệ thống báo cháy tự động liên tủ trung tâm cho nhà cao từ 7 tầng trở lên."
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

    return {
        "warnings": warnings,
        "checklist": checklist,
        "isSubjectToAppraisal": is_subject,
        "appraisalReason": (
            "Quy mô diện tích sàn >= 3.000m² hoặc số tầng >= 7 bắt buộc thẩm duyệt thiết kế PCCC theo Nghị định 105/2025/NĐ-CP."
            if is_subject
            else "Quy mô số tầng < 7 và diện tích sàn < 3.000m² không thuộc diện bắt buộc thẩm duyệt PCCC Công an theo Nghị định 105/2025/NĐ-CP, chỉ cần tự rà soát."
        ),
    }


def get_local_fallback_response(project: Dict[str, Any]) -> Dict[str, Any]:
    result = evaluate_appraisal(project)
    return {
        "reply": "Do lỗi kết nối hoặc giới hạn từ hệ thống AI, hệ thống tạm thời chuyển sang chế độ tự động rà soát cứng theo quy chuẩn quốc gia hiện hành. Dưới đây là kết quả rà soát thiết kế dựa trên các thông số của bạn:",
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
