"""FastAPI backend v2 cho hệ thống Chatbot AI Tư vấn PCCC (self-hosted).
Kiến trúc MVC / Modular Routers (Tách nhỏ routers, services, utils).
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import (
    ALLOWED_ORIGINS,
    DRAWINGS_DIR,
    FRONTEND_DIST_DIR,
    LEGAL_DB_DIR,
    MAX_STAFF_ACCOUNTS,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    NODE_ENV,
    UPLOADS_DIR,
    assert_production_secrets_are_safe,
)
from app.db import init_db
from app.gemini_client import run_deep_llm_appraisal
from app.limiter import limiter
from app.ocr_vision import (
    OCRInputError,
    extract_project_data_from_drawing,
    extract_project_data_from_multiple_drawings,
)
from app.routers import auth, chat, documents, health, inspection_logs, ocr, reports, sessions
from app.rules_engine import DETERMINISTIC_WARNING_PREFIXES, evaluate_appraisal
from app.seed import seed_initial_data
from app.services.session_service import (
    DEFAULT_PROJECT,
    _apply_ai_outputs,
    _check_revision,
    _clear_review,
    _is_reviewed,
    _load_session_full,
    _log_inspection,
    _merge_checklist,
    _now_iso,
    _owner_filter,
    _project_fingerprint,
    _session_revision,
    _session_to_dict,
    _user_grounding_text,
)
from app.storage import ensure_fonts_exist
from app.utils_file import (
    _extract_snippet,
    _generate_safe_storage_path,
    _read_upload_with_size_limit,
    _safe_filename,
)

# Re-exports for test compatibility and backward compatibility
__all__ = [
    "app", "limiter", "LEGAL_DB_DIR", "UPLOADS_DIR", "DRAWINGS_DIR", "NODE_ENV",
    "MAX_STAFF_ACCOUNTS", "MAX_UPLOAD_SIZE_BYTES", "MAX_UPLOAD_SIZE_MB",
    "extract_project_data_from_drawing", "extract_project_data_from_multiple_drawings",
    "OCRInputError", "run_deep_llm_appraisal", "evaluate_appraisal",
    "DETERMINISTIC_WARNING_PREFIXES", "DEFAULT_PROJECT", "_now_iso", "_safe_filename",
    "_generate_safe_storage_path", "_read_upload_with_size_limit", "_extract_snippet",
    "_load_session_full", "_session_revision", "_check_revision", "_project_fingerprint",
    "_is_reviewed", "_clear_review", "_session_to_dict", "_owner_filter",
    "_user_grounding_text", "_apply_ai_outputs", "_merge_checklist", "_log_inspection",
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pccc.main")

# Chặn khởi động ở production nếu secret còn giá trị mặc định không an toàn
assert_production_secrets_are_safe()

app = FastAPI(
    title="PCCC Screening API v11.3",
    version="11.3.0",
    docs_url=None if NODE_ENV == "production" else "/docs",
    redoc_url=None if NODE_ENV == "production" else "/redoc",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "If-Match", "Accept", "X-Requested-With"],
    expose_headers=["ETag"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Header bảo mật chuẩn (OWASP Secure Headers)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; frame-ancestors 'none'",
    )
    return response


@app.on_event("startup")
async def _startup() -> None:
    await init_db()
    await seed_initial_data()
    await ensure_fonts_exist()


# Đăng ký các Router theo mô hình MVC / Modular Architecture
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(ocr.router)
app.include_router(inspection_logs.router)
app.include_router(reports.router)

# Frontend static hosting (production build)
if NODE_ENV == "production" and FRONTEND_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
