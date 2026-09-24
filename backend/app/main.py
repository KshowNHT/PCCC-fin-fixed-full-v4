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
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from app.checklist_data import STANDARDS_CHECKLIST_TEMPLATE
from app.config import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    ALLOWED_DRAWING_EXTENSIONS,
    ALLOWED_ORIGINS,
    DRAWINGS_DIR,
    FRONTEND_DIST_DIR,
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
from app.ocr_vision import extract_project_data_from_drawing
from app.pdf_report import generate_compliance_report_pdf, generate_document_pdf
from app.rules_engine import evaluate_appraisal
from app.schemas_auth import (
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pccc.main")

# Chặn khởi động ở production nếu JWT_SECRET / mật khẩu admin còn giá trị
# mặc định không an toàn — xem app/config.py::assert_production_secrets_are_safe.
assert_production_secrets_are_safe()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="PCCC Compliance AI API v2")
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
    asyncio.create_task(ensure_fonts_exist())


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
    content = await upload.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413, detail=f"File vượt quá giới hạn cho phép ({MAX_UPLOAD_SIZE_MB}MB)."
        )
    return content


# ---------------------------------------------------------------------------
# 0. Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


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
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()

    if user_count == 0:
        # Bootstrap: người đầu tiên đăng ký trở thành admin.
        role = "admin"
    else:
        # Từ người thứ 2 trở đi bắt buộc phải là admin đang đăng nhập mới được tạo tài khoản
        # (giới hạn tối đa MAX_STAFF_ACCOUNTS theo hợp đồng, Ngày 1-2 kế hoạch).
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hệ thống đã có tài khoản. Vui lòng liên hệ quản trị viên để được cấp tài khoản "
            "qua endpoint POST /api/auth/users (yêu cầu quyền admin).",
        )

    existing = (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại.")

    user = User(
        username=body.username,
        full_name=body.full_name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


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
    await db.execute(text("SELECT pg_advisory_xact_lock(72190001)"))

    user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    if user_count >= MAX_STAFF_ACCOUNTS:
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
    await db.commit()
    await db.refresh(user)
    return user


@app.get("/api/auth/users", response_model=List[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


@app.post("/api/auth/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # SECURITY FIX: chống brute-force dò mật khẩu (trước đây không giới hạn)
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản hoặc mật khẩu không chính xác.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khoá.")

    token = create_access_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token,
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

    token = create_access_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "fullName": user.full_name, "role": user.role},
    )


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
    if not file:
        raise HTTPException(status_code=400, detail="Vui lòng chọn file tải lên.")
    user = admin

    created_docs = []
    for i, upload in enumerate(file):
        original_name = upload.filename or f"file_{i}"

        # SECURITY FIX: sinh tên file lưu trên đĩa bằng uuid4 qua whitelist,
        # KHÔNG còn nội suy `original_name` (client-controlled) vào đường
        # dẫn — chặn path traversal / arbitrary file write. Đồng thời từ
        # chối thẳng các định dạng ngoài .txt/.docx/.pdf thay vì "chấp nhận
        # mọi loại file" như bản trước (chặn upload .html/.js giả dạng tài
        # liệu rồi bị mở ra gây stored XSS).
        tmp_path, stored_name = _generate_safe_storage_path(UPLOADS_DIR, original_name, ALLOWED_DOCUMENT_EXTENSIONS)
        ext = Path(stored_name).suffix.lower()
        content = await _read_upload_with_size_limit(upload)
        tmp_path.write_bytes(content)

        if ext == ".txt":
            extracted_text = extract_txt(str(tmp_path))
        elif ext == ".docx":
            extracted_text = extract_docx(str(tmp_path))
        else:  # .pdf — whitelist ở _generate_safe_storage_path đảm bảo không còn nhánh "khác"
            extracted_text = extract_pdf(str(tmp_path), original_name)

        safe_extracted_text = sanitize_text(extracted_text)
        # original_name chỉ dùng để hiển thị (code/title), KHÔNG dùng cho đường dẫn ổ đĩa.
        base_name = original_name.rsplit(".", 1)[0] if "." in original_name else original_name
        base_name = sanitize_text(base_name)[:255]

        doc_code = (code or "").strip()
        doc_title = (title or "").strip()
        if len(file) > 1 or not doc_code:
            doc_code = re.sub(r"[^A-Za-zÀ-ỹ0-9_-]", "", base_name.upper()) or f"VĂNBẢN_{int(time.time() * 1000)}_{i}"
        if len(file) > 1 or not doc_title:
            doc_title = base_name.replace("_", " ")
        doc_code, doc_title = doc_code[:255], doc_title[:500]

        dest_path = LEGAL_DB_DIR / stored_name
        try:
            dest_path.write_bytes(tmp_path.read_bytes())
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception as copy_err:  # noqa: BLE001
            logger.error("Lỗi sao chép file pháp lý vào thư mục legal_db: %s", copy_err)

        new_doc = Document(
            code=doc_code,
            title=doc_title,
            type=type or "Khác",
            link=f"/data/legal_db/{stored_name}",
            content=safe_extracted_text,
            is_custom=True,
            uploaded_by=user.id,
        )
        db.add(new_doc)
        created_docs.append(new_doc)

    await db.commit()
    for d in created_docs:
        await db.refresh(d)

    result = [d.to_dict() for d in created_docs]
    return result[0] if len(result) == 1 else result


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    # SECURITY FIX: admin-only, cùng lý do với upload_documents ở trên.
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu cần xóa.")

    if doc.is_custom:
        link = doc.link or ""
        if link.startswith("/data/uploads/"):
            p = UPLOADS_DIR / link.replace("/data/uploads/", "")
            if p.exists() and p.resolve().is_relative_to(UPLOADS_DIR.resolve()):
                p.unlink()
        elif link.startswith("/data/legal_db/"):
            p = LEGAL_DB_DIR / link.replace("/data/legal_db/", "")
            if p.exists() and p.resolve().is_relative_to(LEGAL_DB_DIR.resolve()):
                p.unlink()

    await db.delete(doc)
    await db.commit()
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
                actual_path = UPLOADS_DIR / link.replace("/data/uploads/", "")
            elif link.startswith("/data/legal_db/"):
                actual_path = LEGAL_DB_DIR / link.replace("/data/legal_db/", "")
            if actual_path and actual_path.exists() and link.lower().endswith(".pdf"):
                safe_title = _safe_filename(doc.title)
                return FileResponse(str(actual_path), media_type="application/pdf", filename=f"{safe_title}.pdf")

        pdf_bytes = generate_document_pdf(doc_dict)
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
            actual_path = UPLOADS_DIR / filename
        elif link.startswith("/data/legal_db/"):
            filename = link.replace("/data/legal_db/", "")
            actual_path = LEGAL_DB_DIR / filename
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

    await db.execute(delete(Document))
    for d in DEFAULT_DOCUMENTS:
        db.add(
            Document(id=d["id"], code=d["code"], title=d["title"], type=d["type"], link=d["link"],
                     content=d["content"], is_custom=False)
        )
    await db.commit()
    result = await db.execute(select(Document).order_by(Document.uploaded_at))
    return [d.to_dict() for d in result.scalars().all()]


# ---------------------------------------------------------------------------
# 3. Chat sessions + ProjectData (Ngày 3, 9-10 kế hoạch)
# ---------------------------------------------------------------------------
DEFAULT_PROJECT = {
    "name": "Dự án mới", "location": "", "investor": "", "designer": "",
    "stage": "Thiết kế cơ sở", "type": "Nhà ở riêng lẻ kết hợp kinh doanh",
    "length": 0, "width": 0, "height": 0, "pcccHeight": 0, "floorArea": 0,
    "totalFloorArea": 0, "floors": 0, "basements": 0, "fireRating": "Bậc III",
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


def _session_to_dict(session: ChatSession) -> dict:
    project = session.project_data.to_dict() if session.project_data else dict(DEFAULT_PROJECT)
    return {
        "id": session.id,
        "title": session.title,
        "projectInfo": project,
        "messages": [m.to_dict() for m in session.messages],
        "updatedAt": session.updated_at.isoformat() if session.updated_at else _now_iso(),
        "checklist": session.checklist,
        "isSubjectToAppraisal": session.is_subject_to_appraisal,
        "appraisalReason": session.appraisal_reason,
        "warnings": session.warnings,
    }


def _owner_filter(user: User):
    """Admin thấy toàn bộ hồ sơ của tổ; nhân viên chỉ thấy hồ sơ của mình."""
    return None if user.role == "admin" else ChatSession.owner_id == user.id


@app.get("/api/sessions")
async def get_sessions(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
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
        .limit(200)
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
    initial_appraisal = evaluate_appraisal(project_info)

    session = ChatSession(
        owner_id=user.id,
        title=title or "Hồ sơ mới thẩm định",
        checklist=initial_appraisal["checklist"],
        is_subject_to_appraisal=initial_appraisal["isSubjectToAppraisal"],
        appraisal_reason=initial_appraisal["appraisalReason"],
        warnings=initial_appraisal["warnings"],
    )
    db.add(session)
    await db.flush()

    project_row = ProjectData(session_id=session.id)
    project_row.apply_dict(project_info)
    db.add(project_row)

    welcome_msg = ChatMessage(
        session_id=session.id,
        sender="assistant",
        text=(
            "Xin chào! Tôi là Chuyên gia AI Thẩm định Hồ sơ Thiết kế Phòng cháy chữa cháy với 20 năm "
            "kinh nghiệm.\n\nHãy mô tả thông tin cơ bản về công trình của bạn (loại công trình, số "
            "tầng, diện tích sàn, kích thước đất, chiều cao, công năng chi tiết...), hoặc tải lên bản vẽ "
            "để tôi tự động đọc và điền thông số (tính năng OCR). Tôi sẽ hỗ trợ rà soát, đối chiếu và "
            "thẩm định tỷ mỉ đối với các quy định hiện hành mới nhất (Nghị định 105/2025/NĐ-CP, QCVN "
            "06:2022/BXD) cho bạn!"
        ),
    )
    db.add(welcome_msg)

    await db.commit()
    full = await _load_session_full(db, session.id)
    return _session_to_dict(full)


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    session = await db.get(ChatSession, session_id)
    if session and user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xoá hồ sơ của người khác.")
    if session:
        await db.delete(session)
        await db.commit()
    return {"success": True}


def _merge_checklist(ai_checklist: Optional[List[dict]], deterministic_checklist: List[dict]) -> List[dict]:
    """FIX B06 + B10 (Bao_Cao_QA_Lan_2.md): trước đây 'result' của cả 17
    hạng mục được lấy thẳng từ JSON do Gemini tự sinh, khớp theo 'stt' do
    chính AI tự gán trong cùng lượt trả lời. Với temperature > 0, LLM có
    thể (a) gán sai stt cho một note (khiến cột 'Kết luận chi tiết' nói về
    hạng mục khác — B06), và (b) trả 'result' khác nhau giữa các lần gọi
    dù đầu vào giống hệt (B10 — số mục 'Đạt' nhảy loạn 0→7/17).

    Sửa tận gốc: 'result' của TẤT CẢ 17 hạng mục giờ LUÔN lấy từ
    `deterministic_checklist` (rules_engine.evaluate_appraisal — cây quyết
    định thuần toán học, 100% tái lập được, đã test kỹ). AI chỉ còn quyền
    đóng góp phần 'note' (văn bản phân tích ngữ cảnh, không ảnh hưởng kết
    luận Đạt/Không đạt) — và CHỈ khi ai_checklist hợp lệ (đủ đúng 17 phần
    tử, stt là hoán vị 1..17, không trùng/thiếu). Nếu Gemini trả về dữ liệu
    dị dạng (thiếu/thừa/trùng stt — dấu hiệu điển hình của lần chạy lỗi),
    toàn bộ note cũng fallback về rules_engine để tránh lệch nội dung.
    """
    ai_list = ai_checklist or []
    stt_values = []
    for it in ai_list:
        try:
            stt_values.append(int(it.get("stt")))
        except (TypeError, ValueError):
            continue

    is_ai_checklist_valid = len(ai_list) == 17 and sorted(stt_values) == list(range(1, 18))
    ai_by_stt = {int(it["stt"]): it for it in ai_list} if is_ai_checklist_valid else {}

    det_by_stt = {d["stt"]: d for d in deterministic_checklist}

    merged = []
    for t in STANDARDS_CHECKLIST_TEMPLATE:
        det = det_by_stt.get(t["stt"], {})
        ai_item = ai_by_stt.get(t["stt"])
        ai_note = (ai_item or {}).get("note")
        merged.append(
            {
                "stt": t["stt"], "category": t["criteria"], "criteria": t["criteria"],
                "requirement": t["requirement"],
                "result": det.get("result") or "Cần xem xét",  # LUÔN deterministic, không cho AI ghi đè
                "note": (ai_note.strip() if isinstance(ai_note, str) and ai_note.strip() else None)
                or det.get("note")
                or f"Chưa đủ thông tin rà soát cụ thể. Vui lòng trao đổi thêm về thông số {t['criteria'].lower()} của công trình.",
                "reference": t["reference"],
            }
        )
    return merged


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
    session_id: str, body: ProjectUpdateRequest, appraise: str = Query("false"),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    session = await _load_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền chỉnh sửa hồ sơ của người khác.")

    if not session.project_data:
        session.project_data = ProjectData(session_id=session.id)
        db.add(session.project_data)
    # FIX B03: body giờ đã qua Pydantic validation (ge=0, kiểm tra logic diện
    # tích) — request có giá trị âm/vô lý sẽ bị chặn ở tầng FastAPI với 422
    # trước khi tới được đây, không cần validate thủ công nữa.
    session.project_data.apply_dict(body.model_dump(exclude_unset=True))
    pinfo = session.project_data.to_dict()

    should_appraise = appraise == "true"

    # Tải danh sách toàn bộ documents + sessions khác để build RAG / prior-project context.
    docs_result = await db.execute(select(Document))
    documents = [d.to_dict() for d in docs_result.scalars().all()]

    other_sessions_result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id != session_id)
        .options(selectinload(ChatSession.project_data))
    )
    other_sessions = [
        {
            "id": s.id, "projectInfo": s.project_data.to_dict() if s.project_data else {},
            "checklist": s.checklist, "isSubjectToAppraisal": s.is_subject_to_appraisal,
            "appraisalReason": s.appraisal_reason,
        }
        for s in other_sessions_result.scalars().all()
    ]

    if should_appraise:
        floor_funcs_str = ""
        if pinfo.get("floorFunctions"):
            floor_funcs_str = ", ".join(f"Tầng nổi {i + 1}: {fn}" for i, fn in enumerate(pinfo["floorFunctions"]))

        basement_specs_str = "Không có tầng hầm"
        if pinfo.get("basements") and pinfo["basements"] > 0:
            detail_list = []
            for i in range(pinfo["basements"]):
                b_fn = (pinfo.get("basementFunctions") or [])[i] if pinfo.get("basementFunctions") and i < len(pinfo["basementFunctions"]) else "Bãi đỗ xe hầm"
                b_h = (pinfo.get("basementHeights") or [])[i] if pinfo.get("basementHeights") and i < len(pinfo["basementHeights"]) else 3.3
                b_a = (pinfo.get("basementAreas") or [])[i] if pinfo.get("basementAreas") and i < len(pinfo["basementAreas"]) else 0
                b_f = (pinfo.get("basementFootprints") or [])[i] if pinfo.get("basementFootprints") and i < len(pinfo["basementFootprints"]) else 0
                detail_list.append(f"Tầng hầm {i + 1} (Công năng: {b_fn}, Chiều cao: {b_h}m, Diện tích sàn: {b_a}m², Diện tích xây dựng hầm: {b_f}m²)")
            basement_specs_str = "; ".join(detail_list)

        trigger_text = f"""[Phản hồi Hệ thống]: Khách hàng yêu cầu KÍCH HOẠT KIỂM DUYỆT HỒ SƠ từ bảng điều khiển dựa trên toàn bộ thông số kỹ thuật chi tiết của công trình đã nhập:
- Tên công trình: {pinfo.get('name') or 'N/A'}
- Địa điểm: {pinfo.get('location') or 'N/A'}
- Chủ đầu tư: {pinfo.get('investor') or 'N/A'}
- Đơn vị thiết kế: {pinfo.get('designer') or 'N/A'}
- Loại hình công trình diện kiểm duyệt: {pinfo.get('type') or 'N/A'}
- Số tầng nổi: {pinfo.get('floors') or 0} tầng
- Số tầng hầm: {pinfo.get('basements') or 0} hầm
- Chiều cao PCCC thiết kế: {pinfo.get('pcccHeight') or 0} m
- Diện tích sàn xây dựng cơ sở: {pinfo.get('floorArea') or 0} m²
- Tổng diện tích sàn cộng dồn: {pinfo.get('totalFloorArea') or 0} m²
- Bậc chịu lửa dự kiến thiết kế: {pinfo.get('fireRating') or 'Chưa lựa chọn'}
- Chi tiết kinh doanh phát sinh: {pinfo.get('commercialDetails') or 'N/A'}
- Chi tiết công năng từng tầng nổi: {floor_funcs_str or 'Chưa tách biệt công năng'}
- Chi tiết thông số các tầng hầm: {basement_specs_str}

Hãy rà soát kỹ lưỡng toàn bộ quy mô kỹ thuật xây dựng và công năng này đối chiếu với Toàn bộ Cơ sở dữ liệu Pháp lý (RAG) để đưa ra Kết luận Pháp lý rõ ràng và chi tiết hóa Bảng checklist 17 mục quy chuẩn PCCC (Đạt/Không đạt/Khuyến nghị/Cần xem xét)."""

        try:
            messages_history = [m.to_dict() for m in session.messages]
            parsed_response = await run_deep_llm_appraisal(
                pinfo, messages_history, documents, other_sessions, trigger_text, session_id
            )

            if parsed_response.get("extractedProjectInfo"):
                session.project_data.apply_dict(parsed_response["extractedProjectInfo"])

            # FIX B10 + B06 (Bao_Cao_QA_Lan_2.md): tính lại bằng rules_engine
            # (deterministic) dựa trên thông số CUỐI CÙNG (đã áp dụng
            # extractedProjectInfo nếu AI có trích xuất thêm) — đây là nguồn
            # sự thật DUY NHẤT cho 'result' từng hạng mục và kết luận pháp lý
            # isSubjectToAppraisal/appraisalReason. AI chỉ còn đóng góp phần
            # 'note' (văn phong phân tích) và 'reply' (lời thoại hội thoại).
            final_pinfo = session.project_data.to_dict()
            deterministic = evaluate_appraisal(final_pinfo)
            merged_checklist = _merge_checklist(parsed_response.get("checklist"), deterministic["checklist"])

            assistant_msg = ChatMessage(
                session_id=session.id, sender="assistant",
                text=parsed_response.get("reply") or "Tôi đã hoàn thành kiểm thẩm định hồ sơ của bạn đối chiếu với CSDL.",
            )
            db.add(assistant_msg)

            session.checklist = merged_checklist
            session.is_subject_to_appraisal = deterministic["isSubjectToAppraisal"]
            session.appraisal_reason = deterministic["appraisalReason"]
            # Gộp cảnh báo từ cả rules_engine (mâu thuẫn số liệu cứng, luôn đúng)
            # và AI (mâu thuẫn ngữ nghĩa AI phát hiện được, ví dụ công năng
            # khai báo mâu thuẫn giữa các lượt chat) — loại trùng, giữ thứ tự.
            ai_warnings = parsed_response.get("warnings") or []
            session.warnings = list(dict.fromkeys(deterministic["warnings"] + ai_warnings))

            await _log_inspection(
                db, session, user.id, "manual_appraise",
                session.is_subject_to_appraisal, session.appraisal_reason, merged_checklist, session.warnings,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Lỗi cập nhật thẩm duyệt LLM: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Lỗi thẩm duyệt hồ sơ. Vui lòng thử lại hoặc liên hệ quản trị viên.")
    else:
        local_eval = evaluate_appraisal(pinfo)
        session.checklist = local_eval["checklist"]
        session.is_subject_to_appraisal = local_eval["isSubjectToAppraisal"]
        session.appraisal_reason = local_eval["appraisalReason"]
        session.warnings = local_eval["warnings"]

    await db.commit()
    full = await _load_session_full(db, session_id)
    return _session_to_dict(full)


# ---------------------------------------------------------------------------
# 4. AI Chatbot / RAG (Ngày 4-8 kế hoạch)
# ---------------------------------------------------------------------------
@app.post("/api/chat")
@limiter.limit("30/minute")  # SECURITY FIX: chống lạm dụng chi phí gọi Gemini API
async def chat(request: Request, body: ChatRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # SECURITY FIX: trước đây nhận `dict` thô không kiểm tra kiểu/độ dài —
    # giờ dùng ChatRequest (Pydantic) validate sessionId/messageText, giới
    # hạn độ dài tin nhắn = MAX_CHAT_MESSAGE_LENGTH ký tự.
    session_id = body.sessionId
    message_text = body.messageText

    session = await _load_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập hồ sơ của người khác.")

    if not session.project_data:
        session.project_data = ProjectData(session_id=session.id)
        db.add(session.project_data)
    project = session.project_data.to_dict()

    user_msg = ChatMessage(session_id=session.id, sender="user", text=message_text)
    db.add(user_msg)
    await db.flush()

    docs_result = await db.execute(select(Document))
    documents = [d.to_dict() for d in docs_result.scalars().all()]
    other_sessions_result = await db.execute(
        select(ChatSession).where(ChatSession.id != session_id).options(selectinload(ChatSession.project_data))
    )
    other_sessions = [
        {
            "id": s.id, "projectInfo": s.project_data.to_dict() if s.project_data else {},
            "checklist": s.checklist, "isSubjectToAppraisal": s.is_subject_to_appraisal,
            "appraisalReason": s.appraisal_reason,
        }
        for s in other_sessions_result.scalars().all()
    ]

    try:
        messages_history = [m.to_dict() for m in session.messages] + [user_msg.to_dict()]
        parsed_response = await run_deep_llm_appraisal(
            project, messages_history, documents, other_sessions, message_text, session_id
        )

        if parsed_response.get("extractedProjectInfo"):
            session.project_data.apply_dict(parsed_response["extractedProjectInfo"])

        # FIX B10 + B06: xem chú thích chi tiết ở update_session_project() —
        # cùng nguyên tắc: result/isSubjectToAppraisal LUÔN deterministic.
        final_pinfo = session.project_data.to_dict()
        deterministic = evaluate_appraisal(final_pinfo)
        merged_checklist = _merge_checklist(parsed_response.get("checklist"), deterministic["checklist"])

        assistant_msg = ChatMessage(
            session_id=session.id, sender="assistant",
            text=parsed_response.get("reply") or "Tôi đã nhận thông tin và cập nhật hệ thống.",
        )
        db.add(assistant_msg)

        session.checklist = merged_checklist
        session.is_subject_to_appraisal = deterministic["isSubjectToAppraisal"]
        session.appraisal_reason = deterministic["appraisalReason"]
        ai_warnings = parsed_response.get("warnings") or []
        session.warnings = list(dict.fromkeys(deterministic["warnings"] + ai_warnings))

        await _log_inspection(
            db, session, user.id, "chat",
            session.is_subject_to_appraisal, session.appraisal_reason, merged_checklist, session.warnings,
        )
        await db.commit()

        full = await _load_session_full(db, session_id)
        return {
            "reply": parsed_response.get("reply") or assistant_msg.text,
            "warnings": full.warnings or [],
            "isSubjectToAppraisal": full.is_subject_to_appraisal or False,
            "appraisalReason": full.appraisal_reason or "Chưa có báo cáo chi tiết.",
            "checklist": merged_checklist,
            "projectInfo": full.project_data.to_dict(),
            "messages": [m.to_dict() for m in full.messages],
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Lỗi chatbot: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi xử lý trò chuyện AI. Vui lòng thử lại hoặc liên hệ quản trị viên.")


# ---------------------------------------------------------------------------
# 5. OCR / Vision đọc bản vẽ (Ngày 12-17 kế hoạch)
# ---------------------------------------------------------------------------
@app.post("/api/ocr/extract-drawing")
@limiter.limit("15/minute")  # SECURITY FIX: OCR gọi Gemini Vision — giới hạn để chống lạm dụng chi phí
async def ocr_extract_drawing(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """'Phát triển Vision/OCR Model (GPT-4o) để trích xuất thông tin từ file
    PDF/PNG bản vẽ' + 'tự điền dữ liệu bóc tách được vào ProjectData Model'
    (Ngày 12-17). Nếu kèm session_id, tự động ghi đè vào ProjectData của
    phiên đó; luôn trả JSON đã trích xuất để frontend autofill form."""
    original_name = file.filename or "drawing"

    # SECURITY FIX: cùng lỗi path traversal như upload_documents — sinh tên
    # file bằng uuid4 qua whitelist, không nội suy filename người dùng gửi.
    dest_path, stored_name = _generate_safe_storage_path(DRAWINGS_DIR, original_name, ALLOWED_DRAWING_EXTENSIONS)
    content = await _read_upload_with_size_limit(file)
    dest_path.write_bytes(content)

    try:
        extracted = await extract_project_data_from_drawing(str(dest_path), file.content_type or "")
    except Exception as e:  # noqa: BLE001
        # SECURITY FIX: không trả nguyên văn exception (có thể lộ traceback/nội
        # bộ hệ thống) — log đầy đủ ở server, trả thông điệp chung cho client.
        logger.error("Lỗi OCR bản vẽ: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi trích xuất bản vẽ. Vui lòng thử lại hoặc liên hệ quản trị viên.")

    if session_id:
        session = await _load_session_full(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat để áp dụng dữ liệu OCR.")
        if user.role != "admin" and session.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Không có quyền chỉnh sửa hồ sơ của người khác.")
        if not session.project_data:
            session.project_data = ProjectData(session_id=session.id)
            db.add(session.project_data)
        session.project_data.apply_dict(extracted)
        session.project_data.source = "ocr"
        await db.commit()

    # SECURITY FIX: không còn trả về URL công khai /data/drawings/... (mount đã bị xoá).
    return {"extractedProjectInfo": extracted, "appliedToSession": bool(session_id)}


# ---------------------------------------------------------------------------
# 6. Inspection Log — nhật ký kiểm tra (Ngày 9-11 kế hoạch)
# ---------------------------------------------------------------------------
@app.get("/api/inspection-logs")
async def list_inspection_logs(
    session_id: Optional[str] = Query(None), limit: int = Query(50, le=200),
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
    Nếu không có `sessionId` (client cũ chưa cập nhật), fallback dùng dữ
    liệu client gửi như trước để không phá vỡ khả năng tương thích ngược.
    """
    session_id = body.get("sessionId")
    if session_id:
        session = await _load_session_full(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat để xuất báo cáo.")
        if user.role != "admin" and session.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Không có quyền xuất báo cáo của hồ sơ người khác.")

        project_info = session.project_data.to_dict() if session.project_data else {}
        checklist = session.checklist or []
        conclusions = {
            "isAppraisalRequired": session.is_subject_to_appraisal or False,
            "reason": session.appraisal_reason or "",
            "warnings": session.warnings or [],
        }
        return project_info, checklist, conclusions

    # Fallback tương thích ngược (không có sessionId trong request)
    return body.get("projectInfo") or {}, body.get("checklist") or [], body.get("conclusions") or {}


@app.post("/api/report/export")
async def export_report_docx(
    body: dict = Body(default={}), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    project_info, checklist, conclusions = await _resolve_export_data(body, db, user)
    try:
        buffer = generate_pccc_report(project_info, checklist, conclusions)
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
        pdf_bytes = generate_compliance_report_pdf(project_info, checklist, conclusions)
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
