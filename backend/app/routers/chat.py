"""AI Chatbot and Consultation Router (Hybrid RAG)."""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.db_models import ChatMessage, User
from app.hardening import lock_session
from app.limiter import limiter
from app.schemas_auth import ChatRequest
from app.services.rag_service import (
    generate_hybrid_rag_reply,
    is_general_theory_query,
    is_project_verdict_query,
)
from app.services.session_service import (
    _check_revision,
    _is_reviewed,
    _load_session_full,
    _session_to_dict,
)

logger = logging.getLogger("pccc.router.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
@limiter.limit("30/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    expected_revision: Optional[str] = Header(None, alias="If-Match"),
):
    session_id = body.sessionId
    message_text = body.messageText

    await lock_session(db, session_id)
    session = await _load_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập hồ sơ của người khác.")

    _check_revision(session, expected_revision)

    citations = []
    is_verdict_query = is_project_verdict_query(message_text)
    is_theory_query = is_general_theory_query(message_text)
    session_reviewed = _is_reviewed(session)
    q_lower = message_text.lower().strip()
    has_project_type = bool(
        session.project_data and str(session.project_data.type or "").strip()
    )
    has_pccc_consultation_intent = bool(
        re.search(
            r"(?:kết luận|kết quả|quy mô|thuộc diện|ngưỡng|thẩm duyệt|thẩm định|luật|quy chuẩn|tiêu chuẩn|nghị định|"
            r"trích dẫn|tra cứu|yêu cầu kỹ thuật|cần lưu ý|lưu ý gì|yêu cầu gì|trang bị gì|cần trang bị|mấy lối|"
            r"lối thoát|kiểm tra|rà soát|đánh giá|tư vấn|hướng dẫn|bố trí|thiết kế)",
            q_lower,
        )
        and not re.search(
            r"(?:thời tiết|bóng đá|giá vàng|xổ số|chứng khoán|nấu ăn)",
            q_lower,
        )
    )

    # 1. Trường hợp hồ sơ chưa được kiểm duyệt (bản nháp):
    if not session_reviewed:
        # Nếu hỏi về kết luận thẩm duyệt/cấp phép của chính dự án này -> Yêu cầu kiểm duyệt trước (DEF-01)
        if is_verdict_query:
            reply = "Thông số đang là bản nháp, chưa được rà soát. Hãy nhập xong và bấm Kiểm duyệt hồ sơ; tôi không tự dùng thông số đang nhập để kết luận."
        # Nếu hỏi lý thuyết / quy chuẩn / kỹ thuật chung hoặc hỏi tư vấn cho loại công trình đang chọn -> Trả lời ngay kèm trích dẫn (DEF-01)
        elif is_theory_query or (has_project_type and has_pccc_consultation_intent):
            rag_res = await generate_hybrid_rag_reply(
                db,
                session,
                message_text,
                is_general_theory=True,
            )
            reply = rag_res["reply"]
            citations = rag_res["citations"]
        else:
            reply = "Không tìm thấy quy định phù hợp để trả lời câu hỏi này trong bộ quy tắc đã xác minh. Không đủ căn cứ đưa ra kết luận kỹ thuật; cần kỹ sư bổ sung và xác nhận quy định áp dụng."
    # 2. Trường hợp hồ sơ ĐÃ được kiểm duyệt:
    else:
        has_specific_target = bool(
            re.search(r"\b(?:này|hiện tại|đang nhập|đang xét|của tôi|của em|của mình)\b", q_lower)
            or is_verdict_query
        )

        # Nếu hỏi về đối tượng / dự án cụ thể này: trả về tư vấn toàn diện gắn với hồ sơ dự án đã kiểm duyệt
        if has_specific_target:
            if is_theory_query or is_verdict_query or has_pccc_consultation_intent:
                rag_res = await generate_hybrid_rag_reply(
                    db,
                    session,
                    message_text,
                    is_general_theory=False,
                )
                reply = rag_res["reply"]
                citations = rag_res["citations"]
            else:
                reply = "Không tìm thấy quy định phù hợp để trả lời câu hỏi này trong bộ quy tắc đã xác minh. Không đủ căn cứ đưa ra kết luận kỹ thuật; cần kỹ sư bổ sung và xác nhận quy định áp dụng."
        # Câu hỏi lý thuyết quy chuẩn chung hoặc tư vấn công năng
        elif is_theory_query or has_pccc_consultation_intent:
            rag_res = await generate_hybrid_rag_reply(
                db,
                session,
                message_text,
                is_general_theory=True,
            )
            reply = rag_res["reply"]
            citations = rag_res["citations"]
        else:
            reply = "Không tìm thấy quy định phù hợp để trả lời câu hỏi này trong bộ quy tắc đã xác minh. Không đủ căn cứ đưa ra kết luận kỹ thuật; cần kỹ sư bổ sung và xác nhận quy định áp dụng."

    db.add(ChatMessage(session_id=session.id, sender="user", text=message_text))
    db.add(ChatMessage(session_id=session.id, sender="assistant", text=reply))
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    full = await _load_session_full(db, session_id)
    return {**_session_to_dict(full), "reply": reply, "citations": citations}
