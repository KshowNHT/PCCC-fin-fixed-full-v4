"""Hybrid RAG Service for PCCC Legal Knowledge Base & Deterministic Rules Engine."""
import logging
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import ChatSession, Document
from app.utils_file import _extract_rich_context, _extract_snippet

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

    # Xác định các mã văn bản ưu tiên theo ngữ cảnh
    target_codes: List[str] = []

    # 1. Văn bản thẩm duyệt & an toàn cháy chung
    target_codes.append("NĐ105/2025/NĐ-CP")
    target_codes.append("QCVN 06:2022/BXD (Sửa đổi 01-2023)")

    # 2. Đặc thù công năng
    if "karaoke" in p_type or "vũ trường" in p_type or "karaoke" in q_lower:
        target_codes.append("147/2020/TT-BCA")
    if "xăng dầu" in p_type or "xăng dầu" in q_lower:
        target_codes.append("QCVN 01:2020/BCT")
    if "gara" in p_type or "xe ô tô" in p_type or "gara" in q_lower or "bãi đỗ xe" in q_lower:
        target_codes.append("QCVN 13:2018/BXD")
    if "chợ" in p_type or "trung tâm thương mại" in p_type or "siêu thị" in p_type:
        target_codes.append("TCVN 6161:1996")
    if "kho" in p_type or "giá đỡ" in q_lower:
        target_codes.append("TCVN 14496:2025")

    # 3. Đặc thù thiết bị & hệ thống kỹ thuật
    if any(k in q_lower for k in ["bơm", "trạm bơm"]):
        target_codes.append("QCVN 02:2020/BCA")
    if any(k in q_lower for k in ["chữa cháy", "sprinkler", "nước", "bọt"]):
        target_codes.append("TCVN 7336:2021")
    if any(k in q_lower for k in ["báo cháy", "đầu báo"]):
        target_codes.append("TCVN 7568-14:2025")
    if any(k in q_lower for k in ["bình chữa cháy", "bình bột", "bình co2"]):
        target_codes.append("TCVN 7435-1:2004 / TCVN 7435-2:2004")
    if any(k in q_lower for k in ["khí", "hfc"]):
        target_codes.append("TCVN 7161-9:2009")
    if any(k in q_lower for k in ["hút khói", "thông gió", "áp suất"]):
        target_codes.append("TCVN 5687:2024")
    if any(k in q_lower for k in ["thoát nạn", "chiếu sáng sự cố", "chỉ dẫn", "đèn"]):
        target_codes.append("TCVN 13456:2022")
    if any(k in q_lower for k in ["sét", "chống sét"]):
        target_codes.append("TCVN 9385:2012")

    if any(k in q_lower for k in ["thang", "buồng thang", "cầu thang", "loại thang"]):
        target_codes.append("QCVN 06:2022/BXD (Sửa đổi 01-2023)")
        target_codes.append("TCVN 2622:1995")
    if any(k in q_lower for k in ["trang bị", "phương tiện", "bố trí", "qcvn 10", "tcvn 3890", "thiết bị"]):
        target_codes.append("QCVN 10:2025/BCA")
    if any(k in q_lower for k in ["khoảng cách", "khoảng lùi", "bậc chịu lửa", "tường ngăn"]):
        target_codes.append("TCVN 2622:1995")

    # Tải toàn bộ tài liệu từ cơ sở dữ liệu để tìm kiếm kết hợp Hybrid RAG
    stmt = select(Document)
    result = await db.execute(stmt)
    all_db_docs = result.scalars().all()

    query_numbers = re.findall(r"\b[0-9]{2,5}\b", q_lower)
    query_tokens = [t for t in re.split(r"[\s_\-:/.,?!()]+", q_lower) if len(t) >= 2]

    doc_scores: List[tuple[int, Document]] = []
    for doc in all_db_docs:
        score = 0
        d_code = (doc.code or "").lower()
        d_title = (doc.title or "").lower()
        d_content = (doc.content or "").lower()
        norm_code = re.sub(r"[\s_\-:/]+", " ", d_code).strip()

        # 1. Khớp mã văn bản trong câu hỏi (ví dụ hỏi 2622, 13456, TCVN 2622)
        code_matched = False
        if d_code in q_lower or (bool(norm_code) and norm_code in norm_q):
            score += 130
            code_matched = True
        elif any(num in d_code for num in query_numbers):
            score += 95
            code_matched = True

        # 2. Khớp trong danh sách target_codes theo ngữ cảnh
        for tc in target_codes:
            tc_norm = re.sub(r"[\s_\-:/]+", " ", tc.lower()).strip()
            if tc.lower() in d_code or tc[:10].lower() in d_code or (bool(tc_norm) and tc_norm in norm_code):
                score += 50
                break

        # 3. Khớp tiêu đề
        if any(tok in d_title for tok in query_tokens if len(tok) >= 4):
            score += 40

        # 4. Khớp nội dung văn bản
        content_matches = sum(1 for tok in query_tokens if len(tok) >= 4 and tok in d_content)
        score += min(content_matches * 10, 40)

        # 5. Ưu tiên tài liệu do người dùng tải lên (is_custom=True) nếu có liên quan
        if doc.is_custom:
            if code_matched or content_matches > 0 or any(tok in d_title for tok in query_tokens if len(tok) >= 3):
                score += 65
            elif any(k in q_lower for k in ["tài liệu", "file", "vừa tải", "vừa up", "vừa nạp"]):
                score += 40

        # 6. Ưu tiên tài liệu có toàn văn thực thụ
        if len(doc.content or "") > 200 and "chưa có toàn văn" not in (doc.content or ""):
            score += 20

        if score > 0:
            doc_scores.append((score, doc))

    doc_scores.sort(key=lambda x: x[0], reverse=True)

    citations: List[Dict[str, Any]] = []
    seen_ids = set()
    seen_codes = set()

    for _, doc in doc_scores:
        if doc.id in seen_ids:
            continue
        norm_code = re.sub(r"[\s_\-:/]+", " ", (doc.code or "").lower()).strip()
        if norm_code in seen_codes:
            continue

        seen_ids.add(doc.id)
        if norm_code:
            seen_codes.add(norm_code)

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
        if len(citations) >= 5:
            break

    # Dự phòng nếu chưa có đủ tài liệu
    if len(citations) < 2:
        for doc in all_db_docs:
            norm_code = re.sub(r"[\s_\-:/]+", " ", (doc.code or "").lower()).strip()
            if doc.id not in seen_ids and norm_code not in seen_codes and any(tc[:8].lower() in (doc.code or "").lower() for tc in target_codes[:2]):
                seen_ids.add(doc.id)
                if norm_code:
                    seen_codes.add(norm_code)
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
                if len(citations) >= 5:
                    break

    return citations[:5]


def is_project_verdict_query(text: str) -> bool:
    """Phân loại ý định: Người dùng đang hỏi về kết luận thẩm duyệt/cấp phép của CHÍNH DỰ ÁN NÀY (DEF-01).

    Chỉ khi hỏi về 'kết luận cấp phép/thẩm duyệt của dự án/công trình này' thì mới yêu cầu
    hồ sơ phải được kiểm duyệt trước.
    """
    if not text:
        return False
    t = text.lower().strip()

    # 1. Các lệnh trực tiếp yêu cầu hệ thống thẩm định/kết luận dự án hiện tại
    if re.search(r"^(?:hãy\s+)?(?:thẩm định|thẩm duyệt|kiểm duyệt|kết luận)(?:\s+ngay|\s+giúp|\s+hồ sơ|\s+dự án)?", t):
        return True

    # 2. Đích danh hồ sơ/dự án/công trình này
    has_project_ref = bool(re.search(
        r"(?:dự án|công trình|hồ sơ|bản vẽ|toà nhà|tòa nhà|ngôi nhà|nhà)\s+(?:này|hiện tại|đang nhập|đang xét|của tôi|của em|của mình)",
        t,
    ))

    # 3. Yêu cầu kết luận / cấp phép / đạt chuẩn
    has_verdict_intent = bool(re.search(
        r"(?:kết luận|kết quả|cấp phép|được duyệt|thẩm duyệt|thẩm định|nghiệm thu|thuộc diện|đạt chuẩn|có đạt|đủ điều kiện|đạt không|được không|phê duyệt)",
        t,
    ))

    if has_project_ref and has_verdict_intent:
        return True

    # 4. Các câu hỏi đặc thù kết luận cấp phép
    if re.search(r"(?:kết luận|kết quả)\s+(?:cấp phép|thẩm duyệt|thẩm định)", t):
        return True
    if re.search(r"(?:có|được)\s+(?:cấp phép|nghiệm thu|phê duyệt|thẩm duyệt)\s+không", t):
        return True

    return False


def is_general_theory_query(text: str) -> bool:
    """Xác định xem câu hỏi có thuộc phạm vi lý thuyết, quy chuẩn, kỹ thuật PCCC hay không (DEF-01)."""
    if not text:
        return False
    t = text.lower().strip()
    return bool(re.search(
        r"(?:pccc|phòng cháy|chữa cháy|cứu hỏa|cứu nạn|cứu hộ|luật|quy chuẩn|tiêu chuẩn|nghị định|thông tư|quy định|hướng dẫn|điều khoản|trích dẫn|tra cứu|văn bản|mã hiệu|qcvn|tcvn|nd105|nđ105|147/2020|loại thang|buồng thang|cầu thang|thang bộ|thang thoát|thang máy|thoát hiểm|thoát nạn|lối thoát|cửa thoát|cửa chống cháy|vách ngăn|ngăn cháy|chống cháy|báo cháy|đầu báo|sprinkler|họng nước|vách tường|trạm bơm|bể nước|bình chữa cháy|bình bột|bình co2|khí|hút khói|thông gió|áp suất|tăng áp|chống sét|khoảng cách|khoảng lùi|bậc chịu lửa|khoang cháy|chiều cao|diện tích|khối tích|giới hạn chịu lửa|\bei\b|\brei\b|karaoke|vũ trường|gara|bãi đỗ|xăng dầu|nhà cao|chung cư|nhà xưởng|nhà kho|giá đỡ|chợ|siêu thị|trường học|bệnh viện|khách sạn|thẩm duyệt|thẩm định|nghiệm thu|cấp phép|kiểm định|trang bị|phương tiện|quy mô|thuộc diện|ngưỡng|tài liệu|file|tải lên|vừa tải|vừa up|vừa nạp|nạp file|tri thức|đã nạp|thư viện|đọc file|nội dung|tóm tắt|tìm hiểu|nghiên cứu|hệ thống|bản vẽ|\b2622\b|\b13456\b|\b7336\b|\b5687\b|\b9385\b|\b7568\b|\b12110\b|\b13333\b|\b13657\b|\b14496\b)",
        t,
    ))


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
        for c in citations[:4]:
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
            "Luôn đính kèm trích dẫn mã quy chuẩn dạng [Mã văn bản] (ví dụ: [TCVN 2622:1995] hoặc [QCVN 06:2022/BXD (Sửa đổi 01-2023)]) để người dùng bấm xem. "
            "Không tự nhận thẩm quyền nhà nước và không suy đoán số liệu chưa có."
        )
        user_content = f"Câu hỏi của người dùng: {query}\n\nTài liệu tham khảo đối chiếu từ thư viện RAG:\n{cit_text}"
        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.1,
            max_output_tokens=600,
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
                if cit.get("snippet"):
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

