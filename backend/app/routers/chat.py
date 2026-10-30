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
from app.services.rag_service import generate_hybrid_rag_reply
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
    # 1. Nếu hồ sơ chưa kiểm duyệt (bản nháp): Không đưa ra kết luận tự ý
    if not _is_reviewed(session):
        reply = "Thông số đang là bản nháp, chưa được rà soát. Hãy nhập xong và bấm Kiểm duyệt hồ sơ; tôi không tự dùng thông số đang nhập để kết luận."
    # 2. Câu hỏi về kết luận, quy mô, thẩm duyệt, căn cứ pháp lý & tra cứu luật (Hybrid RAG)
    elif re.search(r"kết luận|kết quả|quy mô|thuộc diện|ngưỡng|thẩm duyệt|thẩm định|luật|quy chuẩn|nghị định|trích dẫn|tra cứu", message_text.lower()):
        rag_res = await generate_hybrid_rag_reply(db, session, message_text)
        reply = rag_res["reply"]
        citations = rag_res["citations"]
    # 3. Yêu cầu kỹ thuật không có quy định xác minh trong bộ rules
    else:
        reply = "Không tìm thấy quy định phù hợp để trả lời câu hỏi này trong bộ quy tắc đã xác minh. Không đủ căn cứ đưa ra kết luận kỹ thuật; cần kỹ sư bổ sung và xác nhận quy định áp dụng."

    db.add(ChatMessage(session_id=session.id, sender="user", text=message_text))
    db.add(ChatMessage(session_id=session.id, sender="assistant", text=reply))
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    full = await _load_session_full(db, session_id)
    return {**_session_to_dict(full), "reply": reply, "citations": citations}
