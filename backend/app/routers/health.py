import asyncio
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.db import get_db
from app.db_models import User

logger = logging.getLogger("pccc.health")
router = APIRouter(tags=["Health"])


def _get_gemini_key() -> str:
    from app import config

    key = config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
    return key.strip() if key else ""


def _is_gemini_key_configured() -> bool:
    return bool(_get_gemini_key())


async def _ping_gemini_api() -> dict:
    from app.gemini_client import generate_content_with_retry
    from google.genai import types

    key = _get_gemini_key()
    if not key:
        return {
            "geminiApiKeyConfigured": False,
            "status": "error",
            "detail": "Chưa cấu hình GEMINI_API_KEY trên máy chủ.",
        }
    try:
        config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=10,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        async with asyncio.timeout(10):
            await generate_content_with_retry(contents=[{"role": "user", "parts": [{"text": "ping"}]}], config=config)
        return {
            "geminiApiKeyConfigured": True,
            "status": "ok",
            "detail": "Gọi Gemini API thành công.",
        }
    except Exception as e:
        raw_msg = str(e).strip()
        if isinstance(e, TimeoutError) or not raw_msg:
            safe_reason = "Quá thời gian phản hồi từ máy chủ Gemini AI (timeout 10s)."
        else:
            safe_reason = raw_msg.replace(key, "***REDACTED***")[:300]
        logger.error("Health check AI ping thất bại: %s", safe_reason, exc_info=True)
        return {
            "geminiApiKeyConfigured": True,
            "status": "error",
            "detail": f"Không gọi được Gemini API: {safe_reason}",
        }


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
async def health_ai(ping: bool = False, user: User = Depends(get_current_user)):
    if ping:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Chỉ quản trị viên mới có quyền kiểm tra kết nối AI trực tiếp.")
        return await _ping_gemini_api()

    configured = _is_gemini_key_configured()
    return {
        "geminiApiKeyConfigured": configured,
        "status": "unknown",
        "detail": (
            "Chưa cấu hình GEMINI_API_KEY trên máy chủ."
            if not configured
            else "Đã cấu hình, chưa kiểm tra kết nối thật (dùng ?ping=true để kiểm tra)."
        ),
    }


@router.get("/api/health/ai/ping")
async def health_ai_ping(user: User = Depends(require_admin)):
    return await _ping_gemini_api()


