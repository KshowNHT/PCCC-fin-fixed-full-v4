"""Deterministic scale screening and explicit unknown technical criteria.
Current verified source: replacement Annex III, ND347/2026.
Each building is evaluated independently; output is not compliance certification.
"""
from typing import Any, Dict, List, Optional

from app.appraisal_basis import (
    STATUS_INSUFFICIENT,
    STATUS_NOT_REQUIRED,
    STATUS_REQUIRED,
    build_appraisal_basis,
    category_warning,
    effective_height,
    fmt_number,
    to_number,
)
from app.checklist_data import STANDARDS_CHECKLIST_TEMPLATE

AREA_MISMATCH_WARNING = (
    "Tổng diện tích sàn khai báo không trùng khớp với tích số giữa (diện tích sàn x số tầng), "
    "cần đối chiếu kiểm tra thực tế."
)
REQUIRED_SIGNATURE_WARNING = (
    "Hồ sơ thuộc diện bắt buộc thẩm duyệt: bản thiết kế PCCC cần có chữ ký của tư vấn thiết kế được cấp "
    "chứng chỉ hành nghề."
)
# Các cảnh báo do rules_engine tự sinh (dùng để làm mới/loại trùng khi đọc lại hồ sơ cũ).
DETERMINISTIC_WARNING_PREFIXES = (
    "Thiết kế quy mô lớn bậc chịu lửa",
    "Tổng diện tích sàn khai báo không trùng khớp",
    "Nhóm nhà kho:",
    "Hệ thống CHƯA nhận diện được nhóm công năng",
    "Hệ thống CHƯA có ngưỡng thẩm duyệt riêng",
    "Hồ sơ thuộc diện bắt buộc thẩm duyệt",
)

_KNOWN_RATINGS = ("Bậc I", "Bậc II", "Bậc III", "Bậc IV", "Bậc V")


def _need_data(fields: List[str]) -> tuple:
    return "Cần xem xét", f"Chưa đủ thông số ({', '.join(fields)}) để rà soát mục này — vui lòng bổ sung rồi kiểm duyệt lại."


def evaluate_appraisal(project: Dict[str, Any]) -> Dict[str, Any]:
    if project.get("components"):
        return evaluate_components(project)
    basis = build_appraisal_basis(project)
    status = basis["status"]
    checklist = []
    for t in STANDARDS_CHECKLIST_TEMPLATE:
        first = t["stt"] == 1
        checklist.append({"stt": t["stt"], "category": t["criteria"], "criteria": t["criteria"],
            "result": ("Thuộc diện thẩm định" if status == STATUS_REQUIRED else "Dưới ngưỡng danh mục" if status == STATUS_NOT_REQUIRED else "Cần xem xét") if first else "Cần xem xét",
            "requirement": "Xác nhận phân loại, quy mô, thẩm quyền." if first else "Xác định điều kiện áp dụng và kiểm tra hồ sơ, bản vẽ hoặc bằng chứng thực tế.",
            "note": basis["summary"] if first else f"Không tìm thấy quy định phù hợp cho {t['criteria'].lower()} trong bộ quy tắc đã xác minh của chương trình. Không đủ căn cứ chấm đạt/không đạt; cần kỹ sư bổ sung quy định áp dụng và bằng chứng thực tế.",
            "reference": ("Nghị định 347/2026/NĐ-CP, Phụ lục III thay thế; Điều 6, Điều 9 Nghị định 105/2025 đã sửa đổi" if basis["thresholdSource"] == "statutory" else "Chưa tìm thấy quy định phù hợp trong bộ quy tắc đã xác minh") if first else "Chưa tìm thấy quy định phù hợp trong bộ quy tắc đã xác minh"})
    warnings = ["Kết quả là sàng lọc sơ bộ; không phải chứng nhận tuân thủ, văn bản thẩm định hoặc nghiệm thu PCCC."]
    warnings.append("Không tìm thấy quy định phù hợp đã được mã hóa và xác minh cho các hạng mục kỹ thuật còn lại. Không suy diễn kết luận từ ngưỡng quy mô; không có nghĩa pháp luật không quy định các hạng mục này.")
    if status == STATUS_INSUFFICIENT:
        warnings.append(basis["summary"])
    floor_area, floors, total = (to_number(project.get(k)) for k in ("floorArea", "floors", "totalFloorArea"))
    if floor_area > 0 and floors > 0 and total > 0 and abs(total - floor_area * floors) > 10:
        warnings.append(AREA_MISMATCH_WARNING + " Đây là cảnh báo đối chiếu; công trình có tầng giật cấp có thể có chênh lệch hợp lệ.")
    return {"warnings": warnings, "checklist": checklist, "isSubjectToAppraisal": status == STATUS_REQUIRED,
        "appraisalReason": basis["summary"], "appraisalBasis": basis, "buildingCategory": basis["category"]}


def get_local_fallback_response(project: Dict[str, Any]) -> Dict[str, Any]:
    """Phản hồi dự phòng khi Gemini không dùng được — 'reply' TỰ CHỨA tóm tắt
    (không "hứa" nội dung nằm ở nơi khác), kết luận lấy từ cùng nguồn
    `appraisalBasis` như mọi nơi khác trên giao diện."""
    result = evaluate_appraisal(project)
    basis = result["appraisalBasis"]
    non_compliant = [c["criteria"] for c in result["checklist"] if c["result"] == "Không đạt"]
    subject_text = {
        STATUS_REQUIRED: "thuộc ngưỡng sàng lọc thẩm định thiết kế PCCC",
        STATUS_NOT_REQUIRED: "dưới ngưỡng danh mục đã xét; cần kiểm tra phạm vi áp dụng",
        STATUS_INSUFFICIENT: "CHƯA ĐỦ THÔNG SỐ để kết luận thẩm duyệt",
    }[basis["status"]]

    summary_lines = [
        "⚠️ Hệ thống AI (Gemini) hiện không phản hồi được — có thể do chưa cấu hình GEMINI_API_KEY, hết hạn "
        "mức sử dụng, hoặc dịch vụ Google đang gián đoạn. Hệ thống đã TỰ ĐỘNG chuyển sang bộ luật cứng "
        "(rules engine nội bộ, không cần AI) để bạn vẫn có kết quả rà soát ngay lập tức:",
        "",
        f"• Kết luận: công trình {subject_text}.",
        f"• Lý do: {basis['summary']}",
    ]
    if non_compliant:
        summary_lines.append(f"• {len(non_compliant)} hạng mục CHƯA ĐẠT: {', '.join(non_compliant)}.")
    else:
        summary_lines.append("• Chưa có bằng chứng để chấm đạt/không đạt các hạng mục kỹ thuật.")
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


def evaluate_components(project: Dict[str, Any]) -> Dict[str, Any]:
    """Independent parameters and rules per building; never sum into a fictitious house."""
    from app.appraisal_basis import RULES_VERSION, SOURCE_URL
    results = []
    checklist, warnings = [], []
    for component in project["components"]:
        result = evaluate_appraisal(component)
        results.append({"id": component["id"], "name": component["name"], **result})
        for row in result["checklist"]:
            checklist.append({**row, "stt": len(checklist) + 2, "componentId": component["id"],
                              "componentName": component["name"], "criteria": f"{component['name']} — {row['criteria']}"})
        warnings.extend(f"{component['name']}: {w}" for w in result["warnings"])
    statuses = [r["appraisalBasis"]["status"] for r in results]
    complete = project.get("componentsComplete") is True
    shared, concurrent = project.get("sharedSystems"), project.get("concurrentDesign")
    required = STATUS_REQUIRED in statuses
    uncertain = STATUS_INSUFFICIENT in statuses or not complete
    if required and shared is not False and concurrent is not False:
        uncertain = True
        warnings.append("Cần xác nhận thiết kế đồng thời và dùng chung hệ thống báo cháy/chữa cháy. Ghi chú Phụ lục III có thể yêu cầu thẩm định nội dung hệ thống chung của hạng mục dưới ngưỡng.")
    if required and shared is True and concurrent is True:
        shared_text = "Thuộc phạm vi thẩm định nội dung hệ thống dùng chung theo ghi chú Phụ lục III vì thiết kế đồng thời và dùng chung hệ thống báo cháy/chữa cháy với hạng mục thuộc diện. Ngưỡng riêng của nhà không thay đổi."
        for r in results:
            if r["appraisalBasis"]["status"] == STATUS_NOT_REQUIRED:
                r["sharedSystemScope"] = {"status": "required", "reason": shared_text}
                r["appraisalBasis"]["sharedSystemScope"] = r["sharedSystemScope"]
                r["appraisalBasis"]["summary"] += " " + shared_text
                r["appraisalBasis"]["conclusion"] += " " + shared_text
                for row in checklist:
                    if row.get("componentId") == r["id"] and row["result"] == "Dưới ngưỡng danh mục":
                        row["note"] += " " + shared_text
    status = STATUS_REQUIRED if required else STATUS_INSUFFICIENT if uncertain else STATUS_NOT_REQUIRED
    if not complete:
        warnings.append("Chưa xác nhận danh sách hạng mục đầy đủ; không được kết luận miễn cho toàn dự án.")
    lines = [f"{r['name']} ({r['appraisalBasis']['categoryLabel']}): {r['appraisalBasis']['summary']} {r['appraisalBasis']['legalText']}" for r in results]
    headline = "Có hạng mục thuộc ngưỡng danh mục." if required else "Chưa đủ căn cứ kết luận toàn dự án." if uncertain else "Các hạng mục đã khai báo dưới ngưỡng danh mục; không phải miễn mọi thủ tục."
    summary = headline + "\n" + "\n".join(lines)
    basis = {"status": status, "category": "multi_component", "categoryLabel": "Dự án nhiều hạng mục",
        "categoryEvidence": f"{len(results)} hạng mục độc lập đã khai báo", "ruleMode": "manual_review",
        "thresholdSource": "statutory", "legalText": "Phụ lục III Nghị định 347/2026/NĐ-CP; xét riêng từng nhà, không cộng diện tích thành một nhà. Phạm vi hệ thống dùng chung cần rà soát theo ghi chú Phụ lục.",
        "thresholds": [], "triggeredBy": [r["id"] for r in results if r["appraisalBasis"]["status"] == STATUS_REQUIRED],
        "missingFields": ["componentsComplete"] if not complete else [], "summary": summary, "conclusion": summary,
        "actualScale": f"{len(results)} hạng mục; không gộp quy mô", "componentResults": results,
        "rulesVersion": RULES_VERSION, "sourceUrl": SOURCE_URL}
    checklist.insert(0, {"stt": 1, "category": "Tổng hợp phạm vi dự án", "criteria": "Tổng hợp phạm vi dự án",
        "requirement": "Rà soát từng nhà và phạm vi hệ thống dùng chung; không gộp quy mô.",
        "result": "Thuộc diện thẩm định" if required else "Cần xem xét" if uncertain else "Dưới ngưỡng danh mục",
        "note": summary, "reference": "Phụ lục III Nghị định 347/2026/NĐ-CP"})
    return {"warnings": list(dict.fromkeys(warnings)), "checklist": checklist,
        "isSubjectToAppraisal": required, "appraisalReason": summary, "appraisalBasis": basis, "buildingCategory": "multi_component"}
