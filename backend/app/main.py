"""FastAPI backend v2 cho hệ thống Chatbot AI Tư vấn PCCC (self-hosted).

Đối chiếu với Ke_hoach_Models_Chatbot_PCCC*.md — bản v2 này bổ sung đầy đủ:
- Giai đoạn 1: PostgreSQL, User/JWT Auth, Document/ChatSession/ChatMessage Model, RAG
- Giai đoạn 2: ProjectData/InspectionLog Model, OCR/Vision đọc bản vẽ, Rules Engine,
  xuất báo cáo PDF/Word/JSON
- Giai đoạn 3: hỗ trợ Docker qua Dockerfile + docker-compose.yml riêng (xem thư mục gốc)

=== SECURITY HARDENING (audit \\brutal \\10x \\ultrathink) ===
Xem SECURITY_AUDIT.md ở thư mục gốc để biết đầy đủ danh sách lỗ hổng đã vá.
Tóm tắt các thay đổi chính trong file này:
- Xoá 3 static mount /data/uploads,/data/legal_db,/data/drawings KHÔNG xác
  thực (frontend không hề dùng trực tiếp — xác nhận bằng grep trước khi xoá).
- Sinh tên file lưu trên đĩa bằng uuid4, KHÔNG còn nội suy filename người
  dùng gửi lên vào đường dẫn (chặn path traversal / arbitrary file write).
- Whitelist phần mở rộng nghiêm ngặt + giới hạn dung lượng file upload.
- Rate limit (slowapi) cho các endpoint auth/chat/ocr — chống brute-force
  và lạm dụng chi phí gọi Gemini API.
- Thêm security headers middleware (CSP, X-Frame-Options, nosniff, HSTS...).
- Không trả nguyên văn exception cho client — log chi tiết ở server, trả
  thông điệp chung chung cho người dùng.
- Giới hạn thao tác trên thư viện tài liệu pháp lý dùng chung (upload/xoá)
  về admin-only, đúng với ý đồ kế hoạch gốc ("Admin có thể upload...").
- Thêm endpoint tự đổi mật khẩu (trước đây không có, bắt buộc phải có để
  yêu cầu người dùng đổi mật khẩu admin mặc định khi đưa vào production).
"""
import asyncio
import hashlib
import json
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

import logging
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Literal
from urllib.parse import quote

from fastapi import Body, Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import (
    compute_password_fingerprint,
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    oauth2_scheme,
    require_admin,
    revoke_token_payload,
    verify_password,
)
from app.checklist_data import STANDARDS_CHECKLIST_TEMPLATE
from app.config import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    ALLOWED_DRAWING_EXTENSIONS,
    ALLOWED_ORIGINS,
    DRAWINGS_DIR,
    FRONTEND_DIST_DIR,
    JWT_EXPIRE_MINUTES,
    JWT_REFRESH_GRACE_SECONDS,
    LEGAL_DB_DIR,
    MAX_CHAT_MESSAGE_LENGTH,
    MAX_STAFF_ACCOUNTS,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    NODE_ENV,
    UPLOADS_DIR,
    assert_production_secrets_are_safe,
)
from app.db import get_db, init_db
from app.db_models import ChatMessage, ChatSession, Document, InspectionLog, ProjectData, User
from app.doc_extract import extract_docx, extract_pdf, extract_txt, sanitize_text
from app.docx_report import generate_pccc_report
from app.gemini_client import run_deep_llm_appraisal
from app.ocr_vision import extract_project_data_from_drawing, OCRInputError
from app.pdf_report import generate_compliance_report_pdf, generate_document_pdf
from app.ai_guard import guard_reply, guard_warnings, sanitize_extracted_info
from app.rules_engine import DETERMINISTIC_WARNING_PREFIXES, evaluate_appraisal
from app.schemas_auth import (
    AdminUpdateUserRequest,
    ChangePasswordRequest,
    ChatRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.schemas_project import ProjectUpdateRequest
from app.seed import seed_initial_data
from app.storage import ensure_fonts_exist
from app.hardening import validate_upload, resolve_stored_file, lock_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pccc.main")

# Chặn khởi động ở production nếu JWT_SECRET / mật khẩu admin còn giá trị
# mặc định không an toàn — xem app/config.py::assert_production_secrets_are_safe.
assert_production_secrets_are_safe()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="PCCC Screening API v11.3", version="11.3.0", docs_url=None if NODE_ENV == "production" else "/docs", redoc_url=None if NODE_ENV == "production" else "/redoc")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Header bảo mật chuẩn (OWASP Secure Headers). HSTS chỉ có tác dụng
    thật khi chạy sau HTTPS (Nginx/Certbot) — vẫn set ở đây để không quên
    nếu backend có lúc bị truy cập trực tiếp qua HTTPS."""
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


# LƯU Ý BẢO MẬT: các mount StaticFiles công khai /data/uploads, /data/legal_db,
# /data/drawings ĐÃ BỊ XOÁ khỏi bản này. Đã xác nhận bằng grep rằng frontend
# không tham chiếu trực tiếp các URL này (mọi tải file đều đi qua endpoint
# có xác thực /api/documents/{id}/download). Mount công khai trước đây cho
# phép BẤT KỲ AI không cần đăng nhập tải toàn bộ tài liệu pháp lý/bản vẽ nếu
# đoán được tên file — lỗ hổng lộ dữ liệu nghiêm trọng, không phải tính năng
# cần thiết nên được xoá thẳng thay vì thêm lớp xác thực phức tạp cho nó.


@app.on_event("startup")
async def _startup() -> None:
    import asyncio

    await init_db()
    await seed_initial_data()
    await ensure_fonts_exist()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    """Chỉ dùng để đặt tên file trong header Content-Disposition (tên hiển
    thị cho người tải về) — KHÔNG được dùng để dựng đường dẫn ổ đĩa thật."""
    return re.sub(r"\s+", "_", re.sub(r"[^a-zA-Z0-9_À-ỹ\- ]", "", name))


def _generate_safe_storage_path(directory: Path, original_filename: str, allowed_extensions: set) -> tuple[Path, str]:
    """Sinh đường dẫn lưu file AN TOÀN trên đĩa từ 1 file upload.

    SECURITY FIX: bản trước dùng trực tiếp `original_filename` (do người
    dùng/đầu client tự đặt, hoàn toàn không đáng tin) để ghép vào đường dẫn
    lưu file (`f"{timestamp}_{original_filename}"`). Nếu filename chứa
    "../" hoặc dấu "/", pathlib/OS sẽ hiểu đó là chỉ định thư mục cha —
    cho phép ghi đè bất kỳ file nào server có quyền ghi (path traversal ->
    arbitrary file write, có thể dẫn tới RCE). Hàm này chỉ giữ lại PHẦN MỞ
    RỘNG đã qua whitelist, còn tên file sinh ngẫu nhiên bằng uuid4 — loại
    bỏ hoàn toàn khả năng client điều khiển đường dẫn ổ đĩa.
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng file '{ext or '(không rõ)'}' không được hỗ trợ. Chỉ chấp nhận: {', '.join(sorted(allowed_extensions))}",
        )
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return directory / safe_name, safe_name


async def _read_upload_with_size_limit(upload: UploadFile) -> bytes:
    """Đọc nội dung file upload, từ chối nếu vượt MAX_UPLOAD_SIZE_MB (chống
    DoS bằng file khổng lồ nếu request không đi qua Nginx client_max_body_size)."""
    chunks = []
    size = 0
    while chunk := await upload.read(64 * 1024):
        size += len(chunk)
        if size > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"File vượt quá giới hạn cho phép ({MAX_UPLOAD_SIZE_MB}MB).")
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=400, detail="File rỗng.")
    return content


# ---------------------------------------------------------------------------
# 0. Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Cơ sở dữ liệu chưa sẵn sàng.")


@app.get("/api/health/ai")
async def health_ai(user: User = Depends(get_current_user)):
    """MỚI (Bao_Cao_QA_Lan_3.md — khuyến nghị #1 cho B11): 'Nên có trang
    trạng thái dịch vụ để bên mình tự kiểm tra.' Endpoint chẩn đoán riêng
    cho dịch vụ AI — trả về đã cấu hình GEMINI_API_KEY hay chưa, và (tuỳ
    chọn qua query ?ping=true) thử gọi thật 1 lần để xác nhận key còn hoạt
    động, KHÔNG lộ giá trị key ra response."""
    from app.config import GEMINI_API_KEY

    configured = bool(GEMINI_API_KEY and GEMINI_API_KEY.strip())
    result = {
        "geminiApiKeyConfigured": configured,
        "status": "unknown",
        "detail": "Chưa cấu hình GEMINI_API_KEY trên máy chủ." if not configured else "Đã cấu hình, chưa kiểm tra kết nối thật (dùng ?ping=true để kiểm tra).",
    }
    return result


@app.get("/api/health/ai/ping")
async def health_ai_ping(user: User = Depends(require_admin)):
    """Gọi thật 1 lần tới Gemini (model nhẹ nhất, prompt ngắn) để xác nhận
    API key + kết nối mạng còn hoạt động. Chỉ admin được gọi (tốn 1 lượt
    gọi API thật, tránh lạm dụng)."""
    from app.gemini_client import generate_content_with_retry
    from google.genai import types

    try:
        config = types.GenerateContentConfig(temperature=0.0, max_output_tokens=10)
        await generate_content_with_retry(contents=[{"role": "user", "parts": [{"text": "ping"}]}], config=config)
        return {"status": "ok", "detail": "Gọi Gemini API thành công."}
    except Exception as e:  # noqa: BLE001
        logger.error("Health check AI ping thất bại: %s", e, exc_info=True)
        return {"status": "error", "detail": f"Không gọi được Gemini API: {str(e)[:300]}"}


# ---------------------------------------------------------------------------
# 1. Auth (Ngày 1 kế hoạch: 'Viết API Authentication + JWT')
# ---------------------------------------------------------------------------
@app.post("/api/auth/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    raise HTTPException(status_code=403, detail="Đăng ký công khai đã tắt. Liên hệ quản trị viên để cấp tài khoản.")


@app.post("/api/auth/users", response_model=UserOut, status_code=201)
async def create_staff_user(
    body: RegisterRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    """Admin tạo tài khoản nhân viên mới, tối đa MAX_STAFF_ACCOUNTS tài khoản (Ngày 1-2 kế hoạch).

    FIX (rà soát cuối cùng trước bàn giao): trước đây kiểm tra `user_count`
    rồi mới `commit()` — kinh điển race condition "check-then-act". Nếu 2
    request tạo tài khoản chạy đồng thời (double-click, hoặc 2 phiên admin
    cùng thao tác), cả 2 có thể cùng đọc `user_count` TRƯỚC khi request kia
    kịp commit, cả 2 đều pass điều kiện, dẫn tới vượt giới hạn hợp đồng.
    Mức độ rủi ro THẤP (chỉ admin - người dùng tin cậy - mới gọi được
    endpoint này) nhưng vẫn là lỗi đúng nghĩa vì đây là giới hạn cam kết
    hợp đồng. Dùng `pg_advisory_xact_lock` — khoá cấp transaction PostgreSQL,
    tự động giải phóng khi commit/rollback, đảm bảo tại một thời điểm chỉ 1
    transaction được phép đếm+tạo tài khoản, loại bỏ hoàn toàn race condition.
    """
    # Khoá độc quyền cho toàn bộ thao tác "đếm + tạo tài khoản" — số hiệu khoá
    # (hash cố định) chỉ cần duy nhất trong phạm vi ứng dụng, không đụng độ
    # với khoá khác trong hệ thống.
    if db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(72190001)"))

    user_count = (await db.execute(select(func.count()).select_from(User).where(User.role == "staff"))).scalar_one()
    if body.role == "staff" and user_count >= MAX_STAFF_ACCOUNTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Đã đạt giới hạn {MAX_STAFF_ACCOUNTS} tài khoản nhân viên theo hợp đồng.",
        )
    existing = (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại.")

    user = User(
        username=body.username,
        full_name=body.full_name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role if body.role in ("admin", "staff") else "staff",
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tên đăng nhập hoặc email đã tồn tại.")
    await db.refresh(user)
    return user


@app.get("/api/auth/users", response_model=List[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


@app.put("/api/auth/users/{user_id}", response_model=UserOut)
async def update_user_by_admin(
    user_id: str,
    body: AdminUpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin cập nhật thông tin, khoá/mở khoá hoặc đặt lại mật khẩu cho nhân viên."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if user.id == admin.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="Không thể tự khoá tài khoản quản trị đang đăng nhập.")

    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.email is not None:
        user.email = body.email.strip() or None
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.new_password:
        user.hashed_password = hash_password(body.new_password)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email đã được sử dụng bởi tài khoản khác.")
    await db.refresh(user)
    return user


@app.delete("/api/auth/users/{user_id}")
async def delete_user_by_admin(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin xoá tài khoản nhân viên (giải phóng suất trong giới hạn 10 tài khoản)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Không thể tự xoá tài khoản quản trị đang đăng nhập.")

    await db.execute(update(Document).where(Document.uploaded_by == user.id).values(uploaded_by=None))
    await db.execute(delete(InspectionLog).where(InspectionLog.owner_id == user.id))
    await db.delete(user)
    await db.commit()
    return {"success": True, "message": "Đã xoá tài khoản thành công."}



@app.post("/api/auth/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # SECURITY FIX: chống brute-force dò mật khẩu (trước đây không giới hạn)
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản hoặc mật khẩu không chính xác.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khoá.")

    ttl_seconds = JWT_EXPIRE_MINUTES * 60
    token = create_access_token(user.id, user.username, user.role, user.hashed_password)
    return TokenResponse(
        access_token=token,
        expires_in=ttl_seconds,
        expires_at=int(time.time()) + ttl_seconds,
        user={"id": user.id, "username": user.username, "fullName": user.full_name, "role": user.role},
    )


@app.post("/api/auth/login-json", response_model=TokenResponse)
@limiter.limit("10/minute")  # SECURITY FIX: chống brute-force dò mật khẩu
async def login_json(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Alias JSON body cho /api/auth/login (tiện cho fetch() JSON thay vì form-urlencoded)."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản hoặc mật khẩu không chính xác.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khoá.")

    ttl_seconds = JWT_EXPIRE_MINUTES * 60
    token = create_access_token(user.id, user.username, user.role, user.hashed_password)
    return TokenResponse(
        access_token=token,
        expires_in=ttl_seconds,
        expires_at=int(time.time()) + ttl_seconds,
        user={"id": user.id, "username": user.username, "fullName": user.full_name, "role": user.role},
    )


@app.post("/api/auth/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Tự động gia hạn (Sliding Refresh) cấp Access Token mới cho người dùng đang hoạt động.
    - Hỗ trợ ân hạn JWT_REFRESH_GRACE_SECONDS (5 phút) để cứu phiên khi người dùng chuyển sang
      tab trình duyệt khác (timer bị đóng băng) rồi vừa quay lại tab hệ thống.
    - Giữ nguyên mã phiên gốc (sid) và thời điểm đăng nhập gốc (siat) để không vượt quá
      tuổi thọ phiên tối đa JWT_ABSOLUTE_SESSION_MINUTES.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa đăng nhập. Vui lòng cung cấp token xác thực.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token, allow_grace_seconds=JWT_REFRESH_GRACE_SECONDS)
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không tồn tại hoặc đã bị khoá.",
        )
    if payload.get("pwd") != compute_password_fingerprint(user.hashed_password, user.role):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã bị thu hồi. Vui lòng đăng nhập lại.",
        )

    ttl_seconds = JWT_EXPIRE_MINUTES * 60
    new_token = create_access_token(
        user.id,
        user.username,
        user.role,
        user.hashed_password,
        session_id=payload.get("sid"),
        session_iat=payload.get("siat") or payload.get("iat"),
    )
    return TokenResponse(
        access_token=new_token,
        expires_in=ttl_seconds,
        expires_at=int(time.time()) + ttl_seconds,
        user={"id": user.id, "username": user.username, "fullName": user.full_name, "role": user.role},
    )


@app.post("/api/auth/logout")
async def logout_endpoint(token: Optional[str] = Depends(oauth2_scheme)):
    """Thu hồi ngay lập tức token và phiên đăng nhập hiện tại trên máy chủ khi đăng xuất."""
    if token:
        try:
            payload = decode_access_token(token, allow_grace_seconds=JWT_REFRESH_GRACE_SECONDS)
            revoke_token_payload(payload)
        except HTTPException:
            pass
    return {"success": True, "message": "Đã đăng xuất thành công."}


@app.get("/api/auth/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@app.put("/api/auth/me/password")
@limiter.limit("5/minute")
async def change_my_password(
    request: Request, body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """MỚI (security audit): cho phép tự đổi mật khẩu — bắt buộc để xoay
    vòng mật khẩu admin mặc định được seed lúc khởi tạo lần đầu. Yêu cầu
    xác nhận đúng mật khẩu cũ để chống chiếm quyền vĩnh viễn nếu 1 JWT bị
    đánh cắp tạm thời (ví dụ qua XSS) — kẻ tấn công có token nhưng không
    biết mật khẩu cũ thì không tự đổi mật khẩu để khoá chủ tài khoản ra được."""
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không chính xác.")
    user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"success": True, "message": "Đã đổi mật khẩu thành công."}


# ---------------------------------------------------------------------------
# 2. Documents (Ngày 2: Document Model, dùng chung toàn tổ chức)
# ---------------------------------------------------------------------------
@app.get("/api/documents")
async def get_documents(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Document).order_by(Document.uploaded_at))
    return [d.to_dict() for d in result.scalars().all()]


@app.post("/api/documents/upload", status_code=201)
async def upload_documents(
    file: List[UploadFile] = File(...),
    code: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    type: Optional[str] = Form(None),  # noqa: A002
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    # SECURITY FIX: trước đây `get_current_user` (BẤT KỲ nhân viên nào cũng
    # upload/xoá được thư viện pháp lý dùng chung toàn tổ chức). Kế hoạch
    # gốc (Ngày 2) ghi rõ đây là thao tác của ADMIN — siết lại đúng ý đồ
    # thiết kế, đồng thời giảm bề mặt tấn công (staff bị chiếm tài khoản
    # không thể phá hoại/đầu độc cơ sở dữ liệu RAG dùng chung).
):
    if not file or len(file) > 10:
        raise HTTPException(status_code=400, detail="Chọn từ 1 đến 10 file mỗi lần.")
    if type and len(type) > 64:
        raise HTTPException(status_code=422, detail="Loại tài liệu tối đa 64 ký tự.")
    created_docs, written_paths = [], []
    total_size = 0
    try:
        for i, upload in enumerate(file):
            original_name = upload.filename or f"file_{i}"
            dest_path, stored_name = _generate_safe_storage_path(LEGAL_DB_DIR, original_name, ALLOWED_DOCUMENT_EXTENSIONS)
            ext = dest_path.suffix
            content = await _read_upload_with_size_limit(upload)
            total_size += len(content)
            if total_size > MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(status_code=413, detail="Tổng dung lượng file vượt giới hạn upload.")
            await run_in_threadpool(validate_upload, content, ext)
            written_paths.append(dest_path)
            await run_in_threadpool(dest_path.write_bytes, content)
            if ext == ".txt":
                extracted = await run_in_threadpool(extract_txt, str(dest_path))
            elif ext == ".docx":
                extracted = await run_in_threadpool(extract_docx, str(dest_path))
            else:
                extracted = await run_in_threadpool(extract_pdf, str(dest_path), original_name)
            safe_text = sanitize_text(extracted)
            if not safe_text:
                raise HTTPException(status_code=422, detail="Không có văn bản có thể đọc. Hãy OCR tài liệu trước khi nạp vào thư viện.")
            if len(safe_text) > 2_000_000:
                raise HTTPException(status_code=413, detail="Nội dung trích xuất quá lớn.")
            base = sanitize_text(Path(original_name.replace("\\", "/")).stem)[:255]
            doc_code = (code or "").strip() if len(file) == 1 else ""
            doc_title = (title or "").strip() if len(file) == 1 else ""
            new_doc = Document(code=(doc_code or base.upper() or "VANBAN")[:255],
                title=(doc_title or base.replace("_", " ") or "Tài liệu")[:500],
                type=type or "Khác", link=f"/data/legal_db/{stored_name}",
                content=safe_text, is_custom=True, uploaded_by=admin.id)
            db.add(new_doc)
            created_docs.append(new_doc)
        await db.flush()
        result = [d.to_dict() for d in created_docs]
        await db.commit()
        return result[0] if len(result) == 1 else result
    except Exception as err:
        await db.rollback()
        for path in written_paths:
            path.unlink(missing_ok=True)
        if isinstance(err, HTTPException):
            raise
        logger.exception("Upload tài liệu thất bại")
        raise HTTPException(status_code=422, detail="File không hợp lệ hoặc không thể trích xuất. Kiểm tra lại tài liệu.")


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    # SECURITY FIX: admin-only, cùng lý do với upload_documents ở trên.
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu cần xóa.")

    path = resolve_stored_file(doc.link or "", UPLOADS_DIR, LEGAL_DB_DIR) if doc.is_custom else None
    await db.delete(doc)
    await db.commit()
    if path:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Không dọn được file đã xóa metadata; cần dọn volume khi bảo trì")
    return {"success": True, "message": "Đã xóa tài liệu khỏi danh mục RAG."}


@app.get("/api/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    format: Optional[str] = Query(None),  # noqa: A002
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu để tải về.")
    doc_dict = doc.to_dict()

    if format == "pdf":
        if doc.is_custom:
            actual_path = None
            link = doc.link or ""
            if link.startswith("/data/uploads/"):
                actual_path = resolve_stored_file(link, UPLOADS_DIR, LEGAL_DB_DIR)
            elif link.startswith("/data/legal_db/"):
                actual_path = resolve_stored_file(link, UPLOADS_DIR, LEGAL_DB_DIR)
            if actual_path and actual_path.exists() and link.lower().endswith(".pdf"):
                safe_title = _safe_filename(doc.title)
                return FileResponse(str(actual_path), media_type="application/pdf", filename=f"{safe_title}.pdf")

        pdf_bytes = await run_in_threadpool(generate_document_pdf, doc_dict)
        safe_filename = _safe_filename(doc.title) + ".pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={quote(safe_filename)}"},
        )

    if doc.is_custom:
        link = doc.link or ""
        actual_path, filename = None, ""
        if link.startswith("/data/uploads/"):
            filename = link.replace("/data/uploads/", "")
            actual_path = resolve_stored_file(link, UPLOADS_DIR, LEGAL_DB_DIR)
        elif link.startswith("/data/legal_db/"):
            filename = link.replace("/data/legal_db/", "")
            actual_path = resolve_stored_file(link, UPLOADS_DIR, LEGAL_DB_DIR)
        if actual_path and actual_path.exists():
            safe_title = _safe_filename(doc.title)
            ext = Path(filename).suffix
            return FileResponse(str(actual_path), filename=f"{safe_title}{ext}")

    safe_title = _safe_filename(doc.title)
    file_content = (
        f"KÝ HIỆU: {doc.code}\nTIÊU ĐỀ: {doc.title}\nLOẠI VĂN BẢN: {doc.type}\n\n"
        f"NỘI DUNG PHÁP LÝ:\n----------------------------------------\n{doc.content}\n"
    )
    return Response(
        content=file_content.encode("utf-8"), media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={quote(safe_title)}.txt"},
    )


@app.post("/api/documents/reset")
async def reset_documents(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Chỉ admin được reset toàn bộ thư viện pháp lý dùng chung (Ngày 2 kế hoạch)."""
    from app.default_documents import DEFAULT_DOCUMENTS

    old_docs = (await db.execute(select(Document).where(Document.is_custom.is_(True)))).scalars().all()
    paths = [resolve_stored_file(d.link, UPLOADS_DIR, LEGAL_DB_DIR) for d in old_docs]
    await db.execute(delete(Document))
    for d in DEFAULT_DOCUMENTS:
        db.add(
            Document(id=d["id"], code=d["code"], title=d["title"], type=d["type"], link=d["link"],
                     content=d["content"], is_custom=False)
        )
    await db.commit()
    for path in paths:
        if path:
            path.unlink(missing_ok=True)
    result = await db.execute(select(Document).order_by(Document.uploaded_at))
    return [d.to_dict() for d in result.scalars().all()]


# ---------------------------------------------------------------------------
# 3. Chat sessions + ProjectData (Ngày 3, 9-10 kế hoạch)
# ---------------------------------------------------------------------------
DEFAULT_PROJECT = {
    "name": "Dự án mới", "location": "", "investor": "", "designer": "",
    "stage": "", "type": "",
    "length": 0, "width": 0, "height": 0, "pcccHeight": 0, "floorArea": 0,
    "totalFloorArea": 0, "floors": 0, "basements": 0, "fireRating": "",
    "commercialDetails": "",
}


async def _load_session_full(db: AsyncSession, session_id: str) -> Optional[ChatSession]:
    # populate_existing=True bắt buộc SQLAlchemy nạp lại dữ liệu mới nhất từ DB
    # cho các object đã có trong identity map của session hiện tại (quan trọng
    # vì AsyncSessionLocal dùng expire_on_commit=False để tối ưu hiệu năng —
    # nếu thiếu populate_existing, các quan hệ .messages/.project_data đã
    # từng được nạp trước đó trong cùng 1 request sẽ KHÔNG được refresh sau
    # khi thêm bản ghi mới bằng db.add() + commit()).
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .options(selectinload(ChatSession.messages), selectinload(ChatSession.project_data))
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


def _session_revision(session: ChatSession) -> str:
    stamp = session.updated_at
    if stamp and stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    data = {"updatedAt": stamp.astimezone(timezone.utc).isoformat() if stamp else None,
            "project": session.project_data.to_dict() if session.project_data else dict(DEFAULT_PROJECT)}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _check_revision(session: ChatSession, expected: Optional[str]) -> None:
    if expected is None:
        if NODE_ENV == "production":
            raise HTTPException(status_code=428, detail="Cần phiên bản hồ sơ. Tải lại trang trước khi tiếp tục.")
        return
    if not isinstance(expected, str) or not re.fullmatch(r'"?[a-f0-9]{64}"?', expected):
        raise HTTPException(status_code=422, detail="Mã phiên bản hồ sơ không hợp lệ.")
    if expected.strip('"') != _session_revision(session):
        raise HTTPException(status_code=412, detail="Hồ sơ đã được thay đổi ở phiên khác. Tải lại hồ sơ trước khi tiếp tục; dữ liệu chưa được ghi đè.")


def _project_fingerprint(project: dict) -> str:
    return hashlib.sha256(json.dumps(project, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _is_reviewed(session: ChatSession) -> bool:
    project = session.project_data.to_dict() if session.project_data else dict(DEFAULT_PROJECT)
    first = session.checklist[0] if session.checklist and isinstance(session.checklist[0], dict) else {}
    return first.get("reviewedProjectHash") == _project_fingerprint(project) and isinstance(first.get("reviewedBasis"), dict) and first["reviewedBasis"].get("rulesVersion") == "v11.3-347-2026-annexIII"


def _clear_review(session: ChatSession) -> None:
    session.checklist = None
    session.is_subject_to_appraisal = None
    session.appraisal_reason = ""
    session.warnings = []


def _session_to_dict(session: ChatSession) -> dict:
    """Draft reads never run rules. A reviewed result is only for its exact inputs."""
    project = session.project_data.to_dict() if session.project_data else dict(DEFAULT_PROJECT)
    reviewed = _is_reviewed(session)
    basis = session.checklist[0]["reviewedBasis"] if reviewed else None
    checklist = [{k: v for k, v in item.items() if k not in {"reviewedProjectHash", "reviewedBasis"}} for item in session.checklist] if reviewed else []
    return {
        "id": session.id, "title": session.title, "projectInfo": project,
        "messages": [m.to_dict() for m in session.messages],
        "updatedAt": session.updated_at.isoformat() if session.updated_at else _now_iso(),
        "revision": _session_revision(session), "reviewState": "reviewed" if reviewed else "draft",
        "checklist": checklist,
        "isSubjectToAppraisal": session.is_subject_to_appraisal if reviewed else None,
        "appraisalReason": session.appraisal_reason if reviewed else "Chưa kiểm duyệt. Hoàn tất thông số rồi bấm Kiểm duyệt hồ sơ.",
        "appraisalBasis": basis,
        "warnings": session.warnings or [] if reviewed else [],
    }


def _owner_filter(user: User):
    """Admin thấy toàn bộ hồ sơ của tổ; nhân viên chỉ thấy hồ sơ của mình."""
    return None if user.role == "admin" else ChatSession.owner_id == user.id


@app.get("/api/sessions")
async def get_sessions(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # FIX (rà soát cuối cùng trước bàn giao): trước đây KHÔNG có giới hạn —
    # tải TOÀN BỘ session (kèm toàn bộ tin nhắn từng session) mỗi lần gọi.
    # Với quy mô đội ngũ nhỏ (<=10 nhân viên theo hợp đồng) đây chưa phải
    # vấn đề ngay, nhưng số lượng hồ sơ tích luỹ theo THÁNG/NĂM sử dụng sẽ
    # khiến response ngày càng chậm và payload ngày càng nặng — một lỗi
    # "âm thầm xuống cấp hiệu năng" điển hình, khó phát hiện trong giai đoạn
    # demo/nghiệm thu (còn ít dữ liệu) nhưng chắc chắn xuất hiện sau vài
    # tháng vận hành thật. Giới hạn 200 hồ sơ gần nhất — đủ dùng cho nhu cầu
    # thực tế (danh sách bên trái chỉ hiển thị để chọn/tiếp tục làm việc),
    # không cần đổi UI vì đây chỉ là an toàn ở biên, không phải phân trang.
    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages), selectinload(ChatSession.project_data))
        .order_by(ChatSession.updated_at.desc())
        .limit(limit).offset(offset)
    )
    cond = _owner_filter(user)
    if cond is not None:
        stmt = stmt.where(cond)
    result = await db.execute(stmt)
    return [_session_to_dict(s) for s in result.scalars().all()]


class CreateSessionRequest(BaseModel):
    """FIX B03: cùng lý do với ProjectUpdateRequest — trước đây body của
    POST /api/sessions cũng là dict thô, projectInfo gửi kèm lúc tạo mới
    (nếu có) không được validate."""
    title: Optional[str] = Field(default=None, max_length=500)
    projectInfo: Optional[ProjectUpdateRequest] = None


@app.post("/api/sessions", status_code=201)
async def create_session(
    body: CreateSessionRequest = Body(default_factory=CreateSessionRequest),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    title = body.title
    project_overrides = body.projectInfo.model_dump(exclude_unset=True) if body.projectInfo else {}
    project_info = {**DEFAULT_PROJECT, **project_overrides}

    session = ChatSession(
        owner_id=user.id,
        title=title or "Hồ sơ mới thẩm định",
        checklist=None, is_subject_to_appraisal=None, appraisal_reason="", warnings=[],
    )
    db.add(session)
    await db.flush()

    project_row = ProjectData(session_id=session.id)
    project_row.apply_dict(project_info)
    db.add(project_row)

    welcome_msg = ChatMessage(
        session_id=session.id,
        sender="assistant",
        text="Xin chào! Tôi là trợ lý hỗ trợ rà soát hồ sơ PCCC. Hãy nhập công năng, số tầng, diện tích và chiều cao PCCC hoặc tải bản vẽ. Kết quả sàng lọc cần kỹ sư xác nhận; không thay thế thẩm định hoặc nghiệm thu của cơ quan có thẩm quyền.",
    )
    db.add(welcome_msg)

    await db.commit()
    full = await _load_session_full(db, session.id)
    return _session_to_dict(full)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await lock_session(db, session_id)
    session = await _load_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền đọc hồ sơ này.")
    return _session_to_dict(session)


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user), expected_revision: Optional[str] = Header(None, alias="If-Match")):
    await lock_session(db, session_id)
    session = await _load_session_full(db, session_id)
    if session and user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xoá hồ sơ của người khác.")
    if session:
        _check_revision(session, expected_revision)
        await db.delete(session)
        await db.commit()
    return {"success": True}


def _user_grounding_text(history: List[dict], current_text: str) -> str:
    """Lời người dùng làm căn cứ cho số liệu AI trích xuất: tin hiện tại + các tin người dùng gần nhất."""
    recent = [str(m.get("text") or "") for m in history[-8:] if m.get("sender") == "user"]
    return "\n".join(recent + [current_text or ""])


def _apply_ai_outputs(session: "ChatSession", parsed: dict, grounding_text: Optional[str]) -> dict:
    """Điểm DUY NHẤT để dữ liệu do AI sinh ra đi vào hồ sơ.

    1. Số liệu trích xuất: chỉ ghi phần hợp lệ + có căn cứ (xem ai_guard.sanitize_extracted_info).
    2. Tính lại kết luận bằng rules_engine trên số liệu cuối cùng.
    3. Lọc `reply` và `warnings` của AI mâu thuẫn với kết luận (xem ai_guard.guard_reply).
    Trả về {"deterministic", "reply", "warnings"}.
    """
    current = session.project_data.to_dict()
    result = sanitize_extracted_info(parsed.get("extractedProjectInfo"), current, grounding_text)
    if result["accepted"]:
        try:
            checked = ProjectUpdateRequest.model_validate({**current, **result["accepted"]})
            session.project_data.apply_dict(checked.model_dump(exclude_none=True))
        except ValidationError:
            result["rejected"].append("Dữ liệu AI mâu thuẫn hoặc sai cấu trúc; giữ hồ sơ hiện tại.")
    for note in result["rejected"]:
        logger.warning("[ai_guard] session=%s %s", session.id, note)

    final_pinfo = session.project_data.to_dict()
    deterministic = evaluate_appraisal(final_pinfo)
    basis = deterministic["appraisalBasis"]

    reply, violations = guard_reply(parsed.get("reply"), basis, final_pinfo)
    if violations:
        logger.warning("[ai_guard] session=%s đã lược bỏ nhận định mâu thuẫn trong reply: %s", session.id, violations)
    notes = result["rejected"] + result["derived"]
    if result["rejected"] and reply:
        shown = "; ".join(result["rejected"][:3])
        reply = f"{reply}\n\nℹ️ Một số số liệu AI đề xuất chưa được ghi vào hồ sơ: {shown}"

    ai_warnings, dropped = guard_warnings(parsed.get("warnings"), basis, final_pinfo)
    if dropped:
        logger.warning("[ai_guard] session=%s đã loại %d cảnh báo AI mâu thuẫn kết luận", session.id, dropped)
    warnings = list(dict.fromkeys(deterministic["warnings"] + notes + ai_warnings))
    return {"deterministic": deterministic, "reply": reply, "warnings": warnings, "final_pinfo": final_pinfo}


def _merge_checklist(ai_checklist: Optional[List[dict]], deterministic_checklist: List[dict]) -> List[dict]:
    """Return verified screening notes; AI cannot certify technical compliance."""
    # Checklist chỉ dùng nhận xét được xác định trong rules engine. AI không có bằng chứng
    # về cấu kiện/thiết bị thực tế và không được tự chứng nhận tuân thủ.
    return [dict(item) for item in deterministic_checklist]


async def _log_inspection(
    db: AsyncSession, session: ChatSession, user_id: str, trigger_source: str,
    is_subject: bool, reason: str, checklist: list, warnings: list,
) -> None:
    """Ngày 9-11: mỗi lần chạy thẩm định ghi một dòng InspectionLog để truy vết."""
    db.add(
        InspectionLog(
            session_id=session.id, owner_id=user_id, trigger_source=trigger_source,
            is_subject_to_appraisal=is_subject, appraisal_reason=reason,
            checklist_snapshot=checklist, warnings=warnings,
        )
    )


@app.put("/api/sessions/{session_id}/project")
async def update_session_project(
    session_id: str, body: ProjectUpdateRequest, appraise: Literal["true", "false"] = Query("false"),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
    expected_revision: Optional[str] = Header(None, alias="If-Match"),
):
    await lock_session(db, session_id)
    session = await _load_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền chỉnh sửa hồ sơ của người khác.")

    _check_revision(session, expected_revision)

    if not session.project_data:
        session.project_data = ProjectData(session_id=session.id)
        db.add(session.project_data)
    # FIX B03: body giờ đã qua Pydantic validation (ge=0, kiểm tra logic diện
    # tích) — request có giá trị âm/vô lý sẽ bị chặn ở tầng FastAPI với 422
    # trước khi tới được đây, không cần validate thủ công nữa.
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    merged = {**session.project_data.to_dict(), **changes}
    if "components" in changes and changes["components"] != session.project_data.components:
        if "componentsComplete" not in changes:
            merged["componentsComplete"] = False
        old_ids = {c["id"] for c in (session.project_data.components or [])}
        new_ids = {c["id"] for c in (changes["components"] or [])}
        if old_ids != new_ids:
            for key, attribute in (("sharedSystems", "shared_systems"), ("concurrentDesign", "concurrent_design")):
                if key not in changes:
                    merged[key] = None
                    setattr(session.project_data, attribute, None)
    for count_key, array_keys in (("floors", ("floorFunctions",)), ("basements", ("basementFunctions", "basementHeights", "basementAreas", "basementFootprints"))):
        if count_key in changes:
            for key in array_keys:
                merged[key] = (merged.get(key) or [])[:changes[count_key]]
    try:
        validated = ProjectUpdateRequest.model_validate(merged)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Thông số cập nhật mâu thuẫn với hồ sơ đã lưu (diện tích/tầng).")
    session.project_data.apply_dict(validated.model_dump(exclude_none=True))
    session.project_data.source = "manual"
    session.updated_at = datetime.now(timezone.utc)
    pinfo = session.project_data.to_dict()

    should_appraise = appraise == "true"

    if should_appraise:
        evaluation = evaluate_appraisal(pinfo)
        stored = [dict(item) for item in evaluation["checklist"]]
        stored[0]["reviewedProjectHash"] = _project_fingerprint(pinfo)
        stored[0]["reviewedBasis"] = evaluation["appraisalBasis"]
        session.checklist = stored
        session.is_subject_to_appraisal = evaluation["isSubjectToAppraisal"]
        session.appraisal_reason = evaluation["appraisalReason"]
        session.warnings = evaluation["warnings"]
        message = ChatMessage(session_id=session.id, sender="assistant",
            text=evaluation["appraisalReason"] + "\n" + "\n".join(evaluation["warnings"]))
        db.add(message)
        await _log_inspection(db, session, user.id, "manual_appraise",
            session.is_subject_to_appraisal, session.appraisal_reason, evaluation["checklist"], session.warnings)
    else:
        _clear_review(session)

    await db.commit()
    full = await _load_session_full(db, session_id)
    return _session_to_dict(full)


# ---------------------------------------------------------------------------
# 4. AI Chatbot / RAG (Ngày 4-8 kế hoạch)
# ---------------------------------------------------------------------------
@app.post("/api/chat")
@limiter.limit("30/minute")  # SECURITY FIX: chống lạm dụng chi phí gọi Gemini API
async def chat(request: Request, body: ChatRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user), expected_revision: Optional[str] = Header(None, alias="If-Match")):
    # SECURITY FIX: trước đây nhận `dict` thô không kiểm tra kiểu/độ dài —
    # giờ dùng ChatRequest (Pydantic) validate sessionId/messageText, giới
    # hạn độ dài tin nhắn = MAX_CHAT_MESSAGE_LENGTH ký tự.
    session_id = body.sessionId
    message_text = body.messageText

    await lock_session(db, session_id)
    session = await _load_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập hồ sơ của người khác.")

    _check_revision(session, expected_revision)

    # Chat cannot trigger a review or alter the inputs entered in the left form.
    if not _is_reviewed(session):
        reply = "Thông số đang là bản nháp, chưa được rà soát. Hãy nhập xong và bấm Kiểm duyệt hồ sơ; tôi không tự dùng thông số đang nhập để kết luận."
    elif re.search(r"kết luận|kết quả|quy mô|thuộc diện|ngưỡng", message_text.lower()):
        reply = session.appraisal_reason + "\n" + "\n".join(session.warnings or [])
    else:
        reply = "Không tìm thấy quy định phù hợp để trả lời câu hỏi này trong bộ quy tắc đã xác minh. Không đủ căn cứ đưa ra kết luận kỹ thuật; cần kỹ sư bổ sung và xác nhận quy định áp dụng."
    db.add(ChatMessage(session_id=session.id, sender="user", text=message_text))
    db.add(ChatMessage(session_id=session.id, sender="assistant", text=reply))
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    full = await _load_session_full(db, session_id)
    return {**_session_to_dict(full), "reply": reply}


# ---------------------------------------------------------------------------
# 5. OCR / Vision đọc bản vẽ (Ngày 12-17 kế hoạch)
# ---------------------------------------------------------------------------
@app.post("/api/ocr/extract-drawing")
@limiter.limit("15/minute")  # SECURITY FIX: OCR gọi Gemini Vision — giới hạn để chống lạm dụng chi phí
async def ocr_extract_drawing(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    apply_to_session: bool = Form(False),
    expected_revision: Optional[str] = Header(None, alias="If-Match"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Preview OCR by default. Explicit apply_to_session=true opts into a
    validated atomic write; the UI saves only after the user confirms."""
    session = None
    if session_id:
        await lock_session(db, session_id)
        session = await _load_session_full(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
        if user.role != "admin" and session.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Không có quyền chỉnh sửa hồ sơ của người khác.")
        if apply_to_session:
            _check_revision(session, expected_revision)
    dest_path, _ = _generate_safe_storage_path(DRAWINGS_DIR, file.filename or "drawing", ALLOWED_DRAWING_EXTENSIONS)
    content = await _read_upload_with_size_limit(file)
    await run_in_threadpool(validate_upload, content, dest_path.suffix)
    try:
        await run_in_threadpool(dest_path.write_bytes, content)
        extracted = await extract_project_data_from_drawing(str(dest_path), "")
        if not isinstance(extracted, dict):
            raise ValueError("OCR output must be an object")
        current = session.project_data.to_dict() if session and session.project_data else {}
        clean = sanitize_extracted_info(extracted, current, None)
        accepted = clean["accepted"]
        if extracted.get("components") is not None:
            # Validate atomically: never silently discard or collapse an invalid building.
            component_data = ProjectUpdateRequest.model_validate({"components": extracted["components"]})
            accepted["components"] = component_data.model_dump(exclude_none=True)["components"]
            accepted["componentsComplete"] = False
            if accepted["components"]:
                for key in ("type", "height", "pcccHeight", "floorArea", "totalFloorArea", "floors", "fireRating", "volume", "hazardClass", "industrialSubtype"):
                    accepted.pop(key, None)
        for key in ("volume", "hazardClass", "industrialSubtype"):
            if not accepted.get("components") and extracted.get(key) is not None:
                checked = ProjectUpdateRequest.model_validate({key: extracted[key]})
                accepted[key] = checked.model_dump(exclude_none=True)[key]
        for count_key, array_keys in (("floors", ("floorFunctions",)), ("basements", ("basementFunctions", "basementHeights", "basementAreas", "basementFootprints"))):
            if count_key in accepted:
                for key in array_keys:
                    accepted[key] = (accepted.get(key, current.get(key)) or [])[:accepted[count_key]]
        merged = ProjectUpdateRequest.model_validate({**current, **accepted})
        if session and apply_to_session:
            if not session.project_data:
                session.project_data = ProjectData(session_id=session.id)
                db.add(session.project_data)
            session.project_data.apply_dict(merged.model_dump(exclude_none=True))
            if "components" in accepted:
                session.project_data.shared_systems = None
                session.project_data.concurrent_design = None
            session.project_data.source = "ocr"
            session.updated_at = datetime.now(timezone.utc)
            if not _is_reviewed(session):
                _clear_review(session)
            await db.commit()
        return {"extractedProjectInfo": accepted, "appliedToSession": bool(session and apply_to_session), "rejectedFields": clean["rejected"], "coverage": extracted.get("_ocrCoverage")}
    except HTTPException:
        raise
    except OCRInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValidationError:
        raise HTTPException(status_code=422, detail="Dữ liệu OCR mâu thuẫn với hồ sơ. Vui lòng nhập tay để xác nhận.")
    except Exception:
        logger.exception("OCR không thành công")
        raise HTTPException(status_code=502, detail="Dịch vụ OCR không sẵn sàng. Bạn có thể nhập thông số thủ công.")
    finally:
        dest_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 6. Inspection Log — nhật ký kiểm tra (Ngày 9-11 kế hoạch)
# ---------------------------------------------------------------------------
@app.get("/api/inspection-logs")
async def list_inspection_logs(
    session_id: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    stmt = select(InspectionLog).order_by(InspectionLog.created_at.desc()).limit(limit)
    if session_id:
        stmt = stmt.where(InspectionLog.session_id == session_id)
    if user.role != "admin":
        stmt = stmt.where(InspectionLog.owner_id == user.id)
    result = await db.execute(stmt)
    return [log.to_dict() for log in result.scalars().all()]


@app.get("/api/sessions/{session_id}/inspection-logs")
async def session_inspection_logs(
    session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xem nhật ký của hồ sơ người khác.")
    result = await db.execute(
        select(InspectionLog).where(InspectionLog.session_id == session_id).order_by(InspectionLog.created_at.desc())
    )
    return [log.to_dict() for log in result.scalars().all()]


# ---------------------------------------------------------------------------
# 7. Export báo cáo: Word / PDF / JSON (Ngày 22-25 kế hoạch)
# ---------------------------------------------------------------------------
async def _resolve_export_data(body: dict, db: AsyncSession, user: User) -> tuple[dict, list, dict]:
    """FIX bổ sung (rà soát B06 lần 2): trước đây 3 endpoint export tin
    tưởng HOÀN TOÀN `projectInfo`/`checklist` do client gửi lên trong body,
    không đối chiếu lại với `session.checklist` — vốn là bản đã qua
    `_merge_checklist` deterministic (nguồn sự thật duy nhất theo fix B10).
    Về lý thuyết, nếu có bug ở tầng frontend (hoặc request bị chỉnh sửa thủ
    công) khiến `checklist` gửi lên bị sai lệch, file xuất ra vẫn "hợp lệ"
    về mặt kỹ thuật nhưng sai lệch nội dung — tái phát đúng triệu chứng B06
    dù nguyên nhân gốc trong `_merge_checklist` đã được vá.

    Nếu request có `sessionId`, hàm này BẮT BUỘC lấy `checklist`/`projectInfo`/
    kết luận pháp lý từ chính session đó trên server (nguồn xác thực), bỏ
    qua hoàn toàn `checklist` client gửi — đảm bảo file xuất ra LUÔN khớp
    100% với dữ liệu đã chốt, không phụ thuộc client gửi đúng hay sai.
    sessionId và hồ sơ đã được kiểm duyệt là bắt buộc; không dùng dữ liệu
    client để tạo kết luận hoặc fallback cho hồ sơ nháp.
    """
    session_id = body.get("sessionId")
    if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
        raise HTTPException(status_code=422, detail="Cần sessionId hợp lệ để xuất báo cáo.")
    if session_id:
        await lock_session(db, session_id)
        session = await _load_session_full(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat để xuất báo cáo.")
        if user.role != "admin" and session.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Không có quyền xuất báo cáo của hồ sơ người khác.")

        _check_revision(session, body.get("expectedRevision"))
        if not _is_reviewed(session):
            raise HTTPException(status_code=409, detail="Hồ sơ chưa kiểm duyệt hoặc thông số đã thay đổi. Bấm Kiểm duyệt hồ sơ trước khi xuất báo cáo.")

        project_info = session.project_data.to_dict() if session.project_data else {}
        payload = _session_to_dict(session)  # cached explicitly approved snapshot, no rule execution
        if project_info.get("components"):
            ignored = ("type", "floors", "basements", "height", "pcccHeight", "floorArea", "totalFloorArea", "fireRating", "volume", "hazardClass", "industrialSubtype")
            legacy = {key: project_info.get(key) for key in ignored}
            project_info = {**project_info, "assessmentScope": "components", "legacySingleBuildingInput": legacy,
                            "type": "Dự án nhiều hạng mục — xem danh sách từng nhà", "fireRating": "", "hazardClass": "", "industrialSubtype": ""}
            for key in ("floors", "basements", "height", "pcccHeight", "floorArea", "totalFloorArea", "volume"):
                project_info[key] = 0
        return project_info, payload["checklist"] or [], _export_conclusions(project_info, payload["warnings"] or [], payload["appraisalBasis"])

    raise HTTPException(status_code=422, detail="sessionId là bắt buộc để xuất báo cáo từ hồ sơ đã lưu.")


def _export_conclusions(project_info: dict, warnings: list, basis: dict) -> dict:
    """Kết luận dùng cho báo cáo Word/PDF/JSON — cùng nguồn `appraisalBasis`
    với giao diện, nên tiêu đề/lý do trong file xuất không thể khác màn hình."""
    return {
        "appraisalBasis": basis,
        "status": basis["status"],
        "isAppraisalRequired": basis["status"] == "required",
        "reason": basis["conclusion"],
        "basisText": f"Nhóm công năng áp dụng: {basis['categoryLabel']}. {basis['legalText']}",
        "warnings": warnings,
    }


@app.post("/api/report/export")
async def export_report_docx(
    body: dict = Body(default={}), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    project_info, checklist, conclusions = await _resolve_export_data(body, db, user)
    try:
        buffer = await run_in_threadpool(generate_pccc_report, project_info, checklist, conclusions)
        filename = f"Tu_van_PCCC_{str(project_info.get('name', '')).replace(' ', '_')}.docx"
        return Response(
            content=buffer, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={quote(filename)}"},
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Lỗi kết xuất báo cáo Word: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi kết xuất báo cáo Word. Vui lòng thử lại hoặc liên hệ quản trị viên.")


@app.post("/api/report/export-pdf")
async def export_report_pdf(
    body: dict = Body(default={}), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    project_info, checklist, conclusions = await _resolve_export_data(body, db, user)
    try:
        filename = f"Tu_van_PCCC_{str(project_info.get('name', '')).replace(' ', '_')}.pdf"
        pdf_bytes = await run_in_threadpool(generate_compliance_report_pdf, project_info, checklist, conclusions)
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={quote(filename)}"},
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Lỗi kết xuất báo cáo PDF: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi kết xuất báo cáo PDF. Vui lòng thử lại hoặc liên hệ quản trị viên.")


@app.post("/api/report/export-json")
async def export_report_json(
    body: dict = Body(default={}), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Mới bổ sung theo kế hoạch Ngày 22-25: 'tự động xuất báo cáo (PDF, Word, JSON)'."""
    import json

    project_info, checklist, conclusions = await _resolve_export_data(body, db, user)
    payload = {
        "exportedAt": _now_iso(),
        "projectInfo": project_info,
        "checklist": checklist,
        "conclusions": conclusions,
    }
    filename = f"Tu_van_PCCC_{str(project_info.get('name', '')).replace(' ', '_')}.json"
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={quote(filename)}"},
    )


# ---------------------------------------------------------------------------
# Frontend static hosting (production build)
# ---------------------------------------------------------------------------
if NODE_ENV == "production" and FRONTEND_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
