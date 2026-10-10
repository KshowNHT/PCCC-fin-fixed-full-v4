"""Authentication: bcrypt password hashing + JWT (Ngày 1 kế hoạch).

'Viết API Authentication (Đăng nhập/Đăng ký) + JWT.'
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError as JWTError
import bcrypt
import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from app.db import get_db
from app.db_models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        raw = plain.encode("utf-8")
        return len(raw) <= 72 and bcrypt.checkpw(raw, hashed.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def create_access_token(user_id: str, username: str, role: str, password_hash: str = "") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "username": username, "role": role, "exp": expire, "iat": datetime.now(timezone.utc), "pwd": hashlib.sha256(password_hash.encode()).hexdigest()}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]})
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không tồn tại hoặc đã bị khoá.")
    if payload.get("pwd") != hashlib.sha256(user.hashed_password.encode()).hexdigest():
        raise HTTPException(status_code=401, detail="Phiên đăng nhập đã bị thu hồi. Vui lòng đăng nhập lại.")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yêu cầu quyền quản trị viên.")
    return user
