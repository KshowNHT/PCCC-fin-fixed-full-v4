"""Hybrid RAG Service for PCCC Legal Knowledge Base & Deterministic Rules Engine."""
import logging
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import ChatSession, Document
from app.utils_file import _extract_rich_context, _extract_snippet, strip_vietnamese_accents

logger = logging.getLogger("pccc.service.rag")


async def search_citations_for_project_and_query(
    db: AsyncSession,
    message_text: str,
    project_info: Dict[str, Any],
    basis: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Tra cứu các văn bản luật liên quan trực tiếp đến câu hỏi và hồ sơ công trình (Hybrid RAG)."""
    p_type = str(project_info.get("type") or "").lower()
    q_lower = message_text.lower()
    norm_q = re.sub(r"[\s_\-:/]+", " ", q_lower).strip()
    stripped_q = strip_vietnamese_accents(q_lower)
    stripped_norm_q = re.sub(r"[\s_\-:/]+", " ", stripped_q).strip()

    # Xác định các mã văn bản ưu tiên theo ngữ cảnh
    target_codes: List[str] = []

    # 1. Văn bản thẩm duyệt & an toàn cháy chung
    target_codes.append("NĐ105/2025/NĐ-CP")
    target_codes.append("QCVN 06:2022/BXD (Sửa đổi 01-2023)")

    # 2. Đặc thù công năng
    if "karaoke" in p_type or "vũ trường" in p_type or "karaoke" in q_lower or "karaoke" in stripped_q:
        target_codes.append("147/2020/TT-BCA")
    if "xăng dầu" in p_type or "xang dau" in stripped_q or "xăng dầu" in q_lower:
        target_codes.append("QCVN 01:2020/BCT")
    if any(k in p_type or k in stripped_q for k in ["gara", "xe o to", "bai do xe", "xe ô tô", "bãi đỗ xe"]):
        target_codes.append("QCVN 13:2018/BXD")
    if any(k in p_type or k in stripped_q for k in ["cho", "trung tam thuong mai", "sieu thi", "chợ", "trung tâm thương mại", "siêu thị"]):
        target_codes.append("TCVN 6161:1996")
    if "kho" in p_type or "gia do" in stripped_q or "kho" in stripped_q or "giá đỡ" in q_lower:
        target_codes.append("TCVN 14496:2025")

    # 3. Đặc thù thiết bị & hệ thống kỹ thuật
    if any(k in stripped_q for k in ["bom", "tram bom", "may bom"]):
        target_codes.append("QCVN 02:2020/BCA")
    if any(k in stripped_q for k in ["chua chay", "sprinkler", "nuoc", "bot"]):
        target_codes.append("TCVN 7336:2021")
    if any(k in stripped_q for k in ["bao chay", "dau bao", "trung tam bao"]):
        target_codes.append("TCVN 7568-14:2025")
    if any(k in stripped_q for k in ["binh chua chay", "binh bot", "binh co2"]):
        target_codes.append("TCVN 7435-1:2004 / TCVN 7435-2:2004")
    if any(k in stripped_q for k in ["khi", "hfc", "fm200", "aerosol"]):
        target_codes.append("TCVN 7161-9:2009")
    if any(k in stripped_q for k in ["hut khoi", "thong gio", "ap suat", "tang ap"]):
        target_codes.append("TCVN 5687:2024")
    if any(k in stripped_q for k in ["thoat nan", "chieu sang su co", "chi dan", "den", "exit"]):
        target_codes.append("TCVN 13456:2022")
    if any(k in stripped_q for k in ["set", "chong set"]):
        target_codes.append("TCVN 9385:2012")

    if any(k in stripped_q for k in ["thang", "buong thang", "cau thang", "loai thang"]):
        target_codes.append("QCVN 06:2022/BXD (Sửa đổi 01-2023)")
        target_codes.append("TCVN 2622:1995")
    if any(k in stripped_q for k in ["trang bi", "phuong tien", "bo tri", "qcvn 10", "tcvn 3890", "thiet bi"]):
        target_codes.append("QCVN 10:2025/BCA")
    if any(k in stripped_q for k in ["khoang cach", "khoang lui", "bac chiu lua", "tuong ngan"]):
        target_codes.append("TCVN 2622:1995")

    # Tải toàn bộ tài liệu từ cơ sở dữ liệu để tìm kiếm kết hợp Hybrid RAG
    stmt = select(Document)
    result = await db.execute(stmt)
    all_db_docs = result.scalars().all()

    query_numbers = re.findall(r"\b[0-9]{1,5}\b", q_lower)
    words = [w for w in re.split(r"[\s_\-:/]+", q_lower) if w]
    stripped_words = [strip_vietnamese_accents(w) for w in words if len(w) >= 2]

    is_asking_about_uploads = any(
        k in stripped_q for k in [
            "tai lieu", "file", "vua tai", "vua up", "vua nap", "tui up",
            "da up", "tui da up", "da tai", "tui tai", "trich luc", "thu vien", "tai len"
        ]
    )

    doc_scores: List[tuple[int, Document]] = []
    for doc in all_db_docs:
        score = 0
        d_code = (doc.code or "").lower()
        d_title = (doc.title or "").lower()
        d_content = (doc.content or "").lower()

        d_code_stripped = strip_vietnamese_accents(d_code)
        d_title_stripped = strip_vietnamese_accents(d_title)
        d_content_stripped = strip_vietnamese_accents(d_content)
        norm_code = re.sub(r"[\s_\-:/]+", " ", d_code).strip()
        norm_code_stripped = strip_vietnamese_accents(norm_code)

        # 1. Khớp mã văn bản trong câu hỏi (ví dụ hỏi 2622, 13456, TCVN 2622, QCVN 02-2020)
        code_matched = False
        if d_code in q_lower or d_code_stripped in stripped_q:
            score += 160
            code_matched = True
        elif bool(norm_code_stripped) and (norm_code_stripped in stripped_norm_q or stripped_norm_q in norm_code_stripped):
            score += 150
            code_matched = True
        elif len(query_numbers) >= 1:
            matched_nums = sum(1 for num in query_numbers if len(num) >= 2 and re.search(r"(?<!\d)" + num + r"(?!\d)", d_code))
            if matched_nums > 0:
                score += matched_nums * 60
                code_matched = True

        # 2. Khớp cụm từ tiêu đề
        if stripped_q in d_title_stripped or (bool(stripped_norm_q) and stripped_norm_q in d_title_stripped):
            score += 90
        else:
            title_word_matches = sum(1 for w in stripped_words if w in d_title_stripped)
            score += title_word_matches * 15

        # 3. Khớp trong danh sách target_codes theo ngữ cảnh dự án (chỉ cộng nếu người dùng không hỏi chuyên về file tải lên)
        if not code_matched and not is_asking_about_uploads:
            for tc in target_codes:
                tc_norm = re.sub(r"[\s_\-:/]+", " ", tc.lower()).strip()
                if tc.lower() in d_code or (bool(tc_norm) and tc_norm in norm_code):
                    score += 85
                    break

        # 4. Khớp nội dung văn bản
        content_word_matches = sum(1 for w in stripped_words if len(w) >= 3 and w in d_content_stripped)
        score += min(content_word_matches * 5, 40)

        # 5. Ưu tiên tuyệt đối tài liệu do người dùng tải lên (is_custom=True)
        if doc.is_custom:
            if is_asking_about_uploads:
                score += 250
            elif code_matched or content_word_matches > 0 or any(w in d_title_stripped for w in stripped_words):
                score += 130

        # 6. Ưu tiên tài liệu có toàn văn thực thụ
        if len(doc.content or "") > 500 and "chưa có toàn văn" not in (doc.content or ""):
            score += 25

        if score > 0:
            doc_scores.append((score, doc))

    doc_scores.sort(key=lambda x: x[0], reverse=True)

    citations: List[Dict[str, Any]] = []
    seen_ids = set()
    seen_core_codes = set()

    for _, doc in doc_scores:
        if doc.id in seen_ids:
            continue
        d_code_stripped = strip_vietnamese_accents((doc.code or "").lower())
        core_code = re.sub(r"[\s_\-:/]+", " ", d_code_stripped).strip()
        core_code = re.sub(r"\b(bca|bxd|bct|cp|tt|nd)\b", "", core_code).strip()
        core_code = re.sub(r"\b0+(\d+)\b", r"\1", core_code).strip()

        if core_code and core_code in seen_core_codes:
            continue

        seen_ids.add(doc.id)
        if core_code:
            seen_core_codes.add(core_code)

        snippet = _extract_snippet(doc.content or "", q_lower if len(q_lower) > 2 else "thẩm duyệt", max_chars=350)
        rich_context = _extract_rich_context(doc.content or "", q_lower if len(q_lower) > 2 else "thẩm duyệt", max_chars=2500)
        citations.append({
            "id": doc.id,
            "code": doc.code,
            "title": doc.title,
            "type": doc.type,
            "snippet": snippet,
            "full_context": rich_context,
        })
        if len(citations) >= 6:
            break

    # Dự phòng nếu chưa có đủ tài liệu
    if len(citations) < 2:
        for doc in all_db_docs:
            d_code_stripped = strip_vietnamese_accents((doc.code or "").lower())
            core_code = re.sub(r"[\s_\-:/]+", " ", d_code_stripped).strip()
            core_code = re.sub(r"\b(bca|bxd|bct|cp|tt|nd)\b", "", core_code).strip()
            core_code = re.sub(r"\b0+(\d+)\b", r"\1", core_code).strip()

            if doc.id not in seen_ids and (not core_code or core_code not in seen_core_codes) and any(tc[:8].lower() in (doc.code or "").lower() for tc in target_codes[:2]):
                seen_ids.add(doc.id)
                if core_code:
                    seen_core_codes.add(core_code)
                snippet = _extract_snippet(doc.content or "", "thẩm duyệt", max_chars=350)
                rich_context = _extract_rich_context(doc.content or "", "thẩm duyệt", max_chars=2500)
                citations.append({
                    "id": doc.id,
                    "code": doc.code,
                    "title": doc.title,
                    "type": doc.type,
                    "snippet": snippet,
                    "full_context": rich_context,
                })
                if len(citations) >= 6:
                    break

    return citations[:6]


def is_project_verdict_query(text: str) -> bool:
    """Phân loại ý định: Người dùng đang hỏi về kết luận thẩm duyệt/cấp phép của CHÍNH DỰ ÁN NÀY (DEF-01).

    Chỉ khi hỏi về 'kết luận cấp phép/thẩm duyệt của dự án/công trình này' thì mới yêu cầu
    hồ sơ phải được kiểm duyệt trước.
    """
    if not text:
        return False
    t = text.lower().strip()
    stripped_t = strip_vietnamese_accents(t)

    for candidate in (t, stripped_t):
        # 1. Các lệnh trực tiếp yêu cầu hệ thống thẩm định/kết luận dự án hiện tại
        if re.search(r"^(?:hay\s+|hãy\s+)?(?:tham dinh|thẩm định|tham duyet|thẩm duyệt|kiem duyet|kiểm duyệt|ket luan|kết luận)(?:\s+ngay|\s+giup|\s+giúp|\s+ho so|\s+hồ sơ|\s+du an|\s+dự án)?", candidate):
            return True

        # 2. Đích danh hồ sơ/dự án/công trình này
        has_project_ref = bool(re.search(
            r"(?:du an|dự án|cong trinh|công trình|ho so|hồ sơ|ban ve|bản vẽ|toa nha|toà nhà|tòa nhà|ngoi nha|ngôi nhà|nha|nhà)\s+(?:nay|này|hien tai|hiện tại|dang nhap|đang nhập|dang xet|đang xét|cua toi|của tôi|cua em|của em|cua minh|của mình)",
            candidate,
        ))

        # 3. Yêu cầu kết luận / cấp phép / đạt chuẩn
        has_verdict_intent = bool(re.search(
            r"(?:ket luan|kết luận|ket qua|kết quả|cap phep|cấp phép|duoc duyet|được duyệt|tham duyet|thẩm duyệt|tham dinh|thẩm định|nghiem thu|nghiệm thu|thuoc dien|thuộc diện|dat chuan|đạt chuẩn|co dat|có đạt|du dieu kien|đủ điều kiện|dat khong|đạt không|duoc khong|được không|phe duyet|phê duyệt)",
            candidate,
        ))

        if has_project_ref and has_verdict_intent:
            return True

        # 4. Các câu hỏi đặc thù kết luận cấp phép
        if re.search(r"(?:ket luan|kết luận|ket qua|kết quả)\s+(?:cap phep|cấp phép|tham duyet|thẩm duyệt|tham dinh|thẩm định)", candidate):
            return True
        if re.search(r"(?:co|có|duoc|được)\s+(?:cap phep|cấp phép|nghiem thu|nghiệm thu|phe duyet|phê duyệt|tham duyet|thẩm duyệt)\s+(?:khong|không)", candidate):
            return True

    return False


def is_general_theory_query(text: str) -> bool:
    """Xác định xem câu hỏi có thuộc phạm vi lý thuyết, quy chuẩn, kỹ thuật PCCC hay không (DEF-01)."""
    if not text:
        return False
    t = text.lower().strip()
    stripped_t = strip_vietnamese_accents(t)

    for candidate in (t, stripped_t):
        if re.search(
            r"(?:pccc|phong chay|phòng cháy|chua chay|chữa cháy|cuu hoa|cứu hỏa|cuu nan|cứu nạn|cuu ho|cứu hộ|luat|luật|quy chuan|quy chuẩn|tieu chuan|tiêu chuẩn|nghi dinh|nghị định|thong tu|thông tư|quy dinh|quy định|huong dan|hướng dẫn|dieu khoan|điều khoản|trich dan|trích dẫn|trich luc|trích lục|tra cuu|tra cứu|van ban|văn bản|ma hieu|mã hiệu|qcvn|tcvn|nd105|nđ105|147/2020|loai thang|loại thang|buong thang|buồng thang|cau thang|cầu thang|thang bo|thang bộ|thang thoat|thang thoát|thang may|thang máy|thoat hiem|thoát hiểm|thoat nan|thoát nạn|loi thoat|lối thoát|cua thoat|cửa thoát|cua chong chay|cửa chống cháy|vach ngan|vách ngăn|ngan chay|ngăn cháy|chong chay|chống cháy|bao chay|báo cháy|dau bao|đầu báo|sprinkler|hong nuoc|họng nước|vach tuong|vách tường|tram bom|trạm bơm|may bom|máy bơm|be nuoc|bể nước|binh chua chay|bình chữa cháy|binh bot|bình bột|binh co2|bình co2|khi|khí|hut khoi|hút khói|thong gio|thông gió|ap suat|áp suất|tang ap|tăng áp|chong set|chống sét|khoang cach|khoảng cách|khoang lui|khoảng lùi|bac chiu lua|bậc chịu lửa|khoang chay|khoang cháy|chieu cao|chiều cao|dien tich|diện tích|khoi tich|khối tích|gioi han chiu lua|giới hạn chịu lửa|\bei\b|\brei\b|karaoke|vu truong|vũ trường|gara|bai do|bãi đỗ|xang dau|xăng dầu|nha cao|nhà cao|chung cu|chung cư|nha xuong|nhà xưởng|nha kho|nhà kho|gia do|giá đỡ|cho|chợ|sieu thi|siêu thị|truong hoc|trường học|benh vien|bệnh viện|khach san|khách sạn|tham duyet|thẩm duyệt|tham dinh|thẩm định|nghiem thu|nghiệm thu|cap phep|cấp phép|kiem dinh|kiểm định|trang bi|trang bị|phuong tien|phương tiện|quy mo|quy mô|thuoc dien|thuộc diện|nguong|ngưỡng|tai lieu|tài liệu|file|tai len|tải lên|vua tai|vừa tải|vua up|vừa up|vua nap|vừa nạp|nap file|nạp file|tri thuc|tri thức|da up|đã up|da nap|đã nạp|da tai|đã tải|tui up|tui tai|thu vien|thư viện|doc file|đọc file|noi dung|nội dung|tom tat|tóm tắt|tim hieu|tìm hiểu|nghien cuu|nghiên cứu|he thong|hệ thống|ban ve|bản vẽ|\b2622\b|\b13456\b|\b7336\b|\b5687\b|\b9385\b|\b7568\b|\b12110\b|\b13333\b|\b13657\b|\b14496\b)",
            candidate,
        ):
            return True
    return False


async def _ask_gemini_theory(query: str, citations: List[Dict[str, Any]]) -> Optional[str]:
    """Tối ưu tốc độ & token: Gọi Gemini với thinking_budget=0 và failover model để giải đáp lý thuyết nhanh."""
    import asyncio
    import os
    from app import config as app_config

    api_key = (app_config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")).strip()
    if not api_key:
        return None

    try:
        from app.gemini_client import generate_content_with_retry
        from google.genai import types

        cit_parts = []
        for c in citations[:6]:
            body = c.get("full_context") or c.get("snippet") or ""
            if "chưa có toàn văn" in body.lower():
                cit_parts.append(f"- [{c['code']}] {c['title']}")
            else:
                cit_parts.append(f"- [{c['code']}] {c['title']}:\n{body}")

        cit_text = "\n\n".join(cit_parts)
        sys_prompt = (
            "Bạn là chuyên gia tư vấn quy chuẩn PCCC Việt Nam (QCVN 06:2022/BXD, TCVN, NĐ 105/2025/NĐ-CP và các tài liệu chuyên ngành do người dùng nạp vào). "
            "Trả lời ngắn gọn, chuẩn xác, đầy đủ và trực tiếp vào câu hỏi của người dùng dựa trên các tài liệu tham khảo trong thư viện RAG dưới đây. "
            "Nếu người dùng hỏi về tài liệu hoặc file vừa tải lên, hãy ưu tiên trích dẫn các quy định, thông số, bảng biểu và điều khoản từ chính tài liệu đó. "
            "Luôn đính kèm trích dẫn mã quy chuẩn dạng [Mã văn bản] (ví dụ: [QCVN 02:2020/BCA] hoặc [TCVN 2622:1995]) để người dùng bấm xem. "
            "Không tự nhận thẩm quyền nhà nước và không suy đoán số liệu chưa có."
        )
        user_content = f"Câu hỏi của người dùng: {query}\n\nTài liệu tham khảo đối chiếu từ thư viện RAG:\n{cit_text}"
        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.1,
            max_output_tokens=1000,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        response = await generate_content_with_retry(
            contents=[{"role": "user", "parts": [{"text": user_content}]}],
            config=config,
        )
        text = getattr(response, "text", "") or ""
        return text.strip() if text.strip() else None
    except Exception as e:
        logger.warning("Gemini theory answering failed, falling back to deterministic RAG: %s", e)
        return None



async def generate_hybrid_rag_reply(
    db: AsyncSession,
    session: ChatSession,
    message_text: str,
    is_general_theory: bool = False,
) -> Dict[str, Any]:
    """Tạo câu trả lời kết hợp tra cứu điều khoản thật và bộ quy tắc thẩm định (Ngày 4 kế hoạch & DEF-01)."""
    pinfo = session.project_data.to_dict() if session.project_data else {}
    basis = (
        session.checklist[0].get("reviewedBasis")
        if session.checklist and isinstance(session.checklist[0], dict)
        else None
    )

    # 1. Tra cứu các văn bản luật phù hợp trong cơ sở dữ liệu
    citations = await search_citations_for_project_and_query(
        db,
        message_text,
        pinfo if not is_general_theory else {},
        basis,
    )

    # 2. Xử lý trường hợp câu hỏi lý thuyết / quy chuẩn chung (DEF-01)
    if is_general_theory:
        ai_reply = await _ask_gemini_theory(message_text, citations)
        if ai_reply:
            reply = ai_reply
        elif citations:
            lines = [
                "Chào bạn! Dưới đây là giải đáp lý thuyết & căn cứ quy chuẩn PCCC cho câu hỏi của bạn:\n"
            ]
            for cit in citations:
                tag = f"[{cit['code']}]"
                lines.append(f"• Theo **{tag}** ({cit['title']}):")
                text_extract = cit.get("full_context") or cit.get("snippet") or ""
                cleaned_extract = re.sub(r"\s+", " ", text_extract).strip()
                if len(cleaned_extract) > 420:
                    cleaned_extract = cleaned_extract[:417] + "..."
                if cleaned_extract and "chưa có toàn văn" not in cleaned_extract.lower():
                    lines.append(f"  *Trích lục quy định:* \"{cleaned_extract}\"")
                elif cit.get("snippet"):
                    lines.append(f"  *Trích yếu:* \"{cit['snippet']}\"")
            lines.append("\n💡 *Bạn có thể bấm vào thẻ [Mã văn bản] để xem tài liệu gốc chi tiết.*")
            reply = "\n".join(lines)
        else:
            reply = (
                "Chào bạn! Dưới đây là thông tin tra cứu quy chuẩn PCCC cho câu hỏi của bạn:\n"
                "• Quy chuẩn áp dụng nền tảng: **[QCVN 06:2022/BXD (Sửa đổi 01-2023)]** và **[NĐ105/2025/NĐ-CP]**.\n"
                "💡 *Bạn có thể bấm vào thẻ [Mã văn bản] để xem toàn văn quy chuẩn hoặc đặt câu hỏi kèm từ khóa kỹ thuật cụ thể.*"
            )

        return {
            "reply": reply,
            "citations": citations,
        }

    # 3. Câu hỏi gắn liền với kết luận và hồ sơ công trình cụ thể
    p_name = pinfo.get("name") or "Công trình"
    p_type = pinfo.get("type") or "Chưa rõ công năng"
    floors = pinfo.get("floors") or 0
    area = pinfo.get("totalFloorArea") or pinfo.get("floorArea") or 0
    pccc_height = pinfo.get("pcccHeight") or pinfo.get("height") or 0

    reason = session.appraisal_reason or "Chưa có kết luận thẩm duyệt."
    warnings = session.warnings or []

    lines = []
    lines.append(f"Chào bạn! Dưới đây là thông tin tư vấn PCCC cho dự án **{p_name}** ({p_type}):\n")
    lines.append(f"• **Kết quả thẩm định:** {reason}")

    try:
        area_num = float(area)
        area_str = f"{area_num:,.1f}".rstrip("0").rstrip(".") if area_num % 1 else f"{int(area_num):,}"
    except (ValueError, TypeError):
        area_str = str(area)

    if pccc_height:
        lines.append(f"• **Thông số kỹ thuật:** Quy mô {floors} tầng, tổng diện tích {area_str} m², chiều cao PCCC {pccc_height} m.")
    else:
        lines.append(f"• **Thông số kỹ thuật:** Quy mô {floors} tầng, tổng diện tích {area_str} m².")

    if warnings:
        lines.append("\n⚠️ **Lưu ý & Khuyến nghị kỹ thuật:**")
        for w in warnings:
            lines.append(f"- {w}")

    # Danh sách căn cứ và trích dẫn điều khoản thật kèm thẻ bấm được
    lines.append("\n📚 **Căn cứ pháp lý & Nguồn trích dẫn điều khoản áp dụng:**")
    for cit in citations:
        tag = f"[{cit['code']}]"
        lines.append(f"- {tag} ({cit['type']}): {cit['title']}")
        if cit.get("snippet"):
            lines.append(f"  *Trích yếu:* \"{cit['snippet']}\"")

    lines.append("\n💡 *Bạn có thể bấm trực tiếp vào thẻ mã văn bản [Mã văn bản] ở trên để mở trực tiếp tài liệu PDF gốc.*")

    reply = "\n".join(lines)
    return {
        "reply": reply,
        "citations": citations,
    }

