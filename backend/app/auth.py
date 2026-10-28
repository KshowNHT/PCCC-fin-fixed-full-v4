"""Authentication: bcrypt password hashing + JWT lifecycle & revocation (Ngày 1 kế hoạch).

'Viết API Authentication (Đăng nhập/Đăng ký) + JWT.'
Nâng cấp bảo mật vòng đời Token (Senior Security Architecture):
- Access Token có tuổi thọ ngắn (JWT_EXPIRE_MINUTES) kèm đầy đủ claims: sub, iat, nbf, exp, jti, sid, siat, pwd.
- Hỗ trợ Sliding Refresh (/api/auth/refresh) giữ nguyên Session ID (sid) & thời điểm login gốc (siat),
  giới hạn tổng thời gian phiên tối đa bằng JWT_ABSOLUTE_SESSION_MINUTES.
- Hỗ trợ Grace Period (JWT_REFRESH_GRACE_SECONDS) khi người dùng chuyển sang tab khác rồi quay lại.
- Hỗ trợ Thu hồi Token/Phiên tức thì khi Đăng xuất (/api/auth/logout) qua danh sách thu hồi tự dọn rác.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import time
from typing import Optional
import uuid

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import ExpiredSignatureError, PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import (
    JWT_ABSOLUTE_SESSION_MINUTES,
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_REFRESH_GRACE_SECONDS,
    JWT_SECRET,
)
from app.db import get_db
from app.db_models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Danh sách thu hồi token (jti) và phiên (sid) khi người dùng chủ động đăng xuất.
# Lưu {id: expire_epoch_seconds} và tự động dọn các mục đã quá hạn để không rò rỉ bộ nhớ.
_REVOKED_JTIS: dict[str, int] = {}
_REVOKED_SIDS: dict[str, int] = {}


def _prune_revoked(now_ts: int) -> None:
    expired_jtis = [k for k, exp in _REVOKED_JTIS.items() if exp <= now_ts]
    for k in expired_jtis:
        _REVOKED_JTIS.pop(k, None)
    expired_sids = [k for k, exp in _REVOKED_SIDS.items() if exp <= now_ts]
    for k in expired_sids:
        _REVOKED_SIDS.pop(k, None)


def revoke_token_payload(payload: dict) -> None:
    """Thu hồi cả token hiện tại (jti) và phiên đăng nhập (sid) khi người dùng đăng xuất."""
    now_ts = int(time.time())
    _prune_revoked(now_ts)
    exp_ts = int(payload.get("exp") or (now_ts + JWT_EXPIRE_MINUTES * 60)) + JWT_REFRESH_GRACE_SECONDS + 60
    jti = payload.get("jti")
    sid = payload.get("sid")
    if isinstance(jti, str) and jti:
        _REVOKED_JTIS[jti] = exp_ts
    if isinstance(sid, str) and sid:
        _REVOKED_SIDS[sid] = exp_ts


def is_payload_revoked(payload: dict) -> bool:
    now_ts = int(time.time())
    _prune_revoked(now_ts)
    jti = payload.get("jti")
    sid = payload.get("sid")
    if isinstance(jti, str) and jti in _REVOKED_JTIS:
        return True
    if isinstance(sid, str) and sid in _REVOKED_SIDS:
        return True
    return False


def compute_password_fingerprint(password_hash: str, role: str = "") -> str:
    """Sinh dấu vân tay bảo mật từ password_hash. Khi đổi mật khẩu, mọi token cũ tự động vô hiệu."""
    return hashlib.sha256(password_hash.encode()).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        raw = plain.encode("utf-8")
        return len(raw) <= 72 and bcrypt.checkpw(raw, hashed.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    password_hash: str = "",
    *,
    session_id: Optional[str] = None,
    session_iat: Optional[int] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    now = datetime.now(timezone.utc)
    now_ts = int(now.timestamp())
    ttl_minutes = expires_minutes if expires_minutes is not None else JWT_EXPIRE_MINUTES
    expire = now + timedelta(minutes=ttl_minutes)
    sid = session_id or uuid.uuid4().hex
    siat = int(session_iat) if session_iat is not None else now_ts

    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": now_ts,
        "nbf": now_ts,
        "exp": int(expire.timestamp()),
        "jti": uuid.uuid4().hex,
        "sid": sid,
        "siat": siat,
        "pwd": compute_password_fingerprint(password_hash, role),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, *, allow_grace_seconds: int = 0) -> dict:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            leeway=max(0, int(allow_grace_seconds)),
            options={"require": ["exp", "sub"]},
        )
    except ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    if is_payload_revoked(payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã đăng xuất hoặc bị thu hồi. Vui lòng đăng nhập lại.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now_ts = int(time.time())
    siat = payload.get("siat") or payload.get("iat")
    if isinstance(siat, (int, float)):
        max_session_seconds = JWT_ABSOLUTE_SESSION_MINUTES * 60
        if now_ts - int(siat) > max_session_seconds:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên làm việc đã đạt thời hạn tối đa. Vui lòng đăng nhập lại để bảo mật.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return payload


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa đăng nhập. Vui lòng cung cấp token xác thực.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
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
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yêu cầu quyền quản trị viên.")
    return user
