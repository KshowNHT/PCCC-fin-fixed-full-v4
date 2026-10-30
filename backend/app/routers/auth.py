"""Authentication and User Management Router."""
import logging
import sys
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.config import (
    JWT_EXPIRE_MINUTES,
    JWT_REFRESH_GRACE_SECONDS,
    MAX_STAFF_ACCOUNTS,
)
from app.db import get_db
from app.db_models import Document, InspectionLog, User
from app.limiter import limiter
from app.schemas_auth import (
    AdminUpdateUserRequest,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

logger = logging.getLogger("pccc.router.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    raise HTTPException(status_code=403, detail="Đăng ký công khai đã tắt. Liên hệ quản trị viên để cấp tài khoản.")


@router.post("/users", response_model=UserOut, status_code=201)
async def create_staff_user(
    body: RegisterRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    """Admin tạo tài khoản nhân viên mới, tối đa MAX_STAFF_ACCOUNTS tài khoản."""
    if db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(72190001)"))

    main_mod = sys.modules.get("app.main")
    max_staff = getattr(main_mod, "MAX_STAFF_ACCOUNTS", MAX_STAFF_ACCOUNTS) if main_mod else MAX_STAFF_ACCOUNTS

    user_count = (await db.execute(select(func.count()).select_from(User).where(User.role == "staff"))).scalar_one()
    if body.role == "staff" and user_count >= max_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Đã đạt giới hạn {max_staff} tài khoản nhân viên theo hợp đồng.",
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


@router.get("/users", response_model=List[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


@router.put("/users/{user_id}", response_model=UserOut)
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


@router.delete("/users/{user_id}")
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


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
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


@router.post("/login-json", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login_json(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Alias JSON body cho /api/auth/login."""
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


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Tự động gia hạn (Sliding Refresh) cấp Access Token mới cho người dùng đang hoạt động."""
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


@router.post("/logout")
async def logout_endpoint(token: Optional[str] = Depends(oauth2_scheme)):
    """Thu hồi ngay lập tức token và phiên đăng nhập hiện tại trên máy chủ khi đăng xuất."""
    if token:
        try:
            payload = decode_access_token(token, allow_grace_seconds=JWT_REFRESH_GRACE_SECONDS)
            revoke_token_payload(payload)
        except HTTPException:
            pass
    return {"success": True, "message": "Đã đăng xuất thành công."}


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me/password")
@limiter.limit("5/minute")
async def change_my_password(
    request: Request,
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cho phép người dùng tự đổi mật khẩu cá nhân."""
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không chính xác.")
    user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"success": True, "message": "Đã đổi mật khẩu thành công."}
