import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.db import get_db
from app.db_models import User

logger = logging.getLogger("pccc.health")
router = APIRouter(tags=["Health"])


@router.get("/api/health")
def health():
    return {"status": "ok"}


@router.get("/api/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Cơ sở dữ liệu chưa sẵn sàng.")


@router.get("/api/health/ai")
async def health_ai(user: User = Depends(get_current_user)):
    from app.config import GEMINI_API_KEY

    configured = bool(GEMINI_API_KEY and GEMINI_API_KEY.strip())
    return {
        "geminiApiKeyConfigured": configured,
        "status": "unknown",
        "detail": "Chưa cấu hình GEMINI_API_KEY trên máy chủ." if not configured else "Đã cấu hình, chưa kiểm tra kết nối thật (dùng ?ping=true để kiểm tra).",
    }


@router.get("/api/health/ai/ping")
async def health_ai_ping(user: User = Depends(require_admin)):
    from app.gemini_client import generate_content_with_retry
    from google.genai import types

    try:
        config = types.GenerateContentConfig(temperature=0.0, max_output_tokens=10)
        await generate_content_with_retry(contents=[{"role": "user", "parts": [{"text": "ping"}]}], config=config)
        return {"status": "ok", "detail": "Gọi Gemini API thành công."}
    except Exception as e:
        logger.error("Health check AI ping thất bại: %s", e, exc_info=True)
        return {"status": "error", "detail": f"Không gọi được Gemini API: {str(e)[:300]}"}

