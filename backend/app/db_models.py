"""ORM models — port trực tiếp các "Model" nêu trong kế hoạch 33 ngày:

- User Model               (Ngày 1)
- Document Model           (Ngày 2)
- ChatSession Model        (Ngày 3)
- ChatMessage Model        (Ngày 3)
- ProjectData Model        (Ngày 9-10)
- InspectionLog Model      (Ngày 9-11)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Ngày 1: 'Viết API Authentication (Đăng nhập/Đăng ký) + JWT'.
    Giới hạn tối đa MAX_STAFF_ACCOUNTS tài khoản nhân viên (kiểm tra ở route)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="staff")  # "admin" | "staff"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Document(Base):
    """Ngày 2: 'Tạo Document Model. Viết API Upload văn bản luật PCCC & lưu metadata.'
    Thay thế knowledge_base.json bằng bảng thật, dùng chung cho toàn tổ chức (RAG)."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str] = mapped_column(String(64), default="Khác")
    link: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "title": self.title,
            "type": self.type,
            "link": self.link,
            "content": self.content,
            "isCustom": self.is_custom,
            "uploadedAt": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class ChatSession(Base):
    """Ngày 3: 'Tạo ChatSession & ChatMessage Model.'
    Lưu trạng thái thẩm định hiện tại (denormalized) để trả API nhanh; lịch
    sử chi tiết từng lần chạy nằm ở InspectionLog."""

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"session_{_uuid()}")
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="Hồ sơ mới thẩm định")

    checklist: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_subject_to_appraisal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    appraisal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    owner: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )
    project_data: Mapped["ProjectData | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    inspection_logs: Mapped[list["InspectionLog"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="InspectionLog.created_at.desc()"
    )


class ChatMessage(Base):
    """Ngày 3-4: lưu lịch sử hội thoại từng tin nhắn (thay vì mảng lồng trong JSON)."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"msg_{_uuid()}")
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id"), nullable=False)
    sender: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" | "assistant"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "text": self.text,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
        }


class ProjectData(Base):
    """Ngày 9-10: 'Tạo ProjectData Model. Viết API lưu trữ thông số dự án.'
    1-1 với ChatSession; cũng là bảng được OCR (Ngày 12-17) tự động điền."""

    __tablename__ = "project_data"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"proj_{_uuid()}")
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chat_sessions.id"), unique=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(500), default="Dự án mới")
    location: Mapped[str] = mapped_column(String(500), default="")
    investor: Mapped[str] = mapped_column(String(255), default="")
    designer: Mapped[str] = mapped_column(String(255), default="")
    stage: Mapped[str] = mapped_column(String(255), default="Thiết kế cơ sở")
    type: Mapped[str] = mapped_column(String(255), default="Nhà ở riêng lẻ kết hợp kinh doanh")

    length: Mapped[float] = mapped_column(Float, default=0)
    width: Mapped[float] = mapped_column(Float, default=0)
    height: Mapped[float] = mapped_column(Float, default=0)
    pccc_height: Mapped[float] = mapped_column(Float, default=0)
    floor_area: Mapped[float] = mapped_column(Float, default=0)
    total_floor_area: Mapped[float] = mapped_column(Float, default=0)
    floors: Mapped[int] = mapped_column(Integer, default=0)
    basements: Mapped[int] = mapped_column(Integer, default=0)
    fire_rating: Mapped[str] = mapped_column(String(32), default="Bậc III")
    commercial_details: Mapped[str] = mapped_column(Text, default="")

    floor_functions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    basement_functions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    basement_heights: Mapped[list | None] = mapped_column(JSON, nullable=True)
    basement_areas: Mapped[list | None] = mapped_column(JSON, nullable=True)
    basement_footprints: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Nguồn gốc dữ liệu: "manual" (nhập tay) hay "ocr" (AI đọc bản vẽ tự động, Ngày 12-17)
    source: Mapped[str] = mapped_column(String(16), default="manual")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    session: Mapped["ChatSession"] = relationship(back_populates="project_data")

    FIELD_MAP = {
        "name": "name", "location": "location", "investor": "investor", "designer": "designer",
        "stage": "stage", "type": "type", "length": "length", "width": "width", "height": "height",
        "pcccHeight": "pccc_height", "floorArea": "floor_area", "totalFloorArea": "total_floor_area",
        "floors": "floors", "basements": "basements", "fireRating": "fire_rating",
        "commercialDetails": "commercial_details", "floorFunctions": "floor_functions",
        "basementFunctions": "basement_functions", "basementHeights": "basement_heights",
        "basementAreas": "basement_areas", "basementFootprints": "basement_footprints",
    }

    def to_dict(self) -> dict:
        return {js_key: getattr(self, py_key) for js_key, py_key in self.FIELD_MAP.items()}

    def apply_dict(self, data: dict) -> None:
        for js_key, py_key in self.FIELD_MAP.items():
            if js_key in data and data[js_key] is not None:
                setattr(self, py_key, data[js_key])


class InspectionLog(Base):
    """Ngày 9-11: 'Viết API lấy danh sách Log kiểm tra (Inspection History)'.
    Nhật ký/audit trail — mỗi lần chạy thẩm định (chat, cập nhật project, OCR)
    tạo một bản ghi để kỹ sư truy vết kết quả AI qua thời gian."""

    __tablename__ = "inspection_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"log_{_uuid()}")
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False)

    trigger_source: Mapped[str] = mapped_column(String(32), default="chat")  # chat|manual_appraise|ocr_autofill
    is_subject_to_appraisal: Mapped[bool] = mapped_column(Boolean, default=False)
    appraisal_reason: Mapped[str] = mapped_column(Text, default="")
    checklist_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["ChatSession"] = relationship(back_populates="inspection_logs")

    def to_dict(self) -> dict:
        non_compliant = sum(1 for c in (self.checklist_snapshot or []) if c.get("result") == "Không đạt")
        compliant = sum(1 for c in (self.checklist_snapshot or []) if c.get("result") == "Đạt")
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "triggerSource": self.trigger_source,
            "isSubjectToAppraisal": self.is_subject_to_appraisal,
            "appraisalReason": self.appraisal_reason,
            "checklist": self.checklist_snapshot,
            "warnings": self.warnings,
            "compliantCount": compliant,
            "nonCompliantCount": non_compliant,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
