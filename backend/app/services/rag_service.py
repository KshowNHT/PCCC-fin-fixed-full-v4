"""Hybrid RAG Service for PCCC Legal Knowledge Base & Deterministic Rules Engine."""
import logging
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import ChatSession, Document
from app.utils_file import _extract_snippet

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

    # Lấy văn bản từ database
    stmt = select(Document).where(
        or_(*[Document.code.ilike(f"%{code[:15]}%") for code in target_codes])
    )
    result = await db.execute(stmt)
    matched_docs = {d.code: d for d in result.scalars().all()}

    # Format danh sách trích dẫn có thứ tự
    citations: List[Dict[str, Any]] = []
    for code in target_codes:
        doc = matched_docs.get(code)
        if not doc:
            # Tìm gần đúng
            for d in matched_docs.values():
                if code[:10].lower() in d.code.lower():
                    doc = d
                    break
        if doc and doc.id not in [c["id"] for c in citations]:
            snippet = _extract_snippet(doc.content, q_lower if len(q_lower) > 3 else "thẩm duyệt")
            citations.append({
                "id": doc.id,
                "code": doc.code,
                "title": doc.title,
                "type": doc.type,
                "snippet": snippet,
            })

    return citations[:5]


async def generate_hybrid_rag_reply(
    db: AsyncSession,
    session: ChatSession,
    message_text: str,
) -> Dict[str, Any]:
    """Tạo câu trả lời kết hợp tra cứu điều khoản thật và bộ quy tắc thẩm định (Ngày 4 kế hoạch)."""
    pinfo = session.project_data.to_dict() if session.project_data else {}
    basis = (
        session.checklist[0].get("reviewedBasis")
        if session.checklist and isinstance(session.checklist[0], dict)
        else None
    )

    # 1. Tra cứu các văn bản luật phù hợp trong cơ sở dữ liệu
    citations = await search_citations_for_project_and_query(db, message_text, pinfo, basis)

    # 2. Xây dựng câu trả lời kết hợp kết luận và trích dẫn điều khoản thật
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

