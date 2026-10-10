import re
from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator

from app.config import MAX_CHAT_MESSAGE_LENGTH, MIN_PASSWORD_LENGTH


def _validate_password_strength(v: str) -> str:
    """SECURITY FIX: bản trước chỉ yêu cầu min_length=6 — quá yếu, dễ bị
    brute-force/dò offline nếu hash rò rỉ. Nâng lên MIN_PASSWORD_LENGTH
    (mặc định 10) + bắt buộc có cả chữ và số để chặn các mật khẩu kiểu
    "aaaaaaaaaa" hay "1111111111" vẫn thoả điều kiện độ dài."""
    if len(v.encode("utf-8")) > 72:
        raise ValueError("Mật khẩu không được vượt quá 72 byte UTF-8.")
    if len(v) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự.")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
        raise ValueError("Mật khẩu phải chứa cả chữ cái và chữ số.")
    return v


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)
    full_name: str = Field(default="", max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    role: Literal["admin", "staff"] = "staff"  # chỉ admin mới được set "admin" cho người khác (kiểm tra ở route)

    _validate_password = field_validator("password")(_validate_password_strength)


class LoginRequest(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)


class ChangePasswordRequest(BaseModel):
    """Mới bổ sung (security audit): trước đây KHÔNG có cách nào để người
    dùng tự đổi mật khẩu — nghĩa là không thể ép buộc xoay vòng mật khẩu
    admin mặc định sau lần đăng nhập đầu. Bắt buộc phải nhập đúng mật khẩu
    cũ (chống kẻ tấn công đã cướp phiên JWT tạm thời tự ý đổi mật khẩu để
    chiếm tài khoản vĩnh viễn)."""
    old_password: str = Field(max_length=128)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)

    _validate_new_password = field_validator("new_password")(_validate_password_strength)


class ChatRequest(BaseModel):
    """Mới bổ sung (security audit): endpoint /api/chat trước đây nhận
    `dict` thô không giới hạn độ dài messageText — cho phép gửi payload
    khổng lồ vừa tốn chi phí gọi Gemini API vừa có thể gây lỗi/DoS."""
    sessionId: str = Field(min_length=1, max_length=128)
    messageText: str = Field(min_length=1, max_length=MAX_CHAT_MESSAGE_LENGTH)

    @field_validator("messageText")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Tin nhắn không được để trống.")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserOut(BaseModel):
    id: str
    username: str
    full_name: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
