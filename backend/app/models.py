"""Pydantic schemas mirroring the original src/types.ts definitions."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectInfo(BaseModel):
    name: str = "Dự án mới"
    location: str = ""
    investor: str = ""
    designer: str = ""
    stage: str = "Thiết kế cơ sở"
    type: str = "Nhà ở riêng lẻ kết hợp kinh doanh"
    length: float = 0
    width: float = 0
    height: float = 0
    pcccHeight: float = 0
    floorArea: float = 0
    totalFloorArea: float = 0
    floors: int = 0
    basements: int = 0
    fireRating: str = "Bậc III"
    commercialDetails: str = ""
    floorFunctions: Optional[List[str]] = None
    basementFunctions: Optional[List[str]] = None
    basementHeights: Optional[List[float]] = None
    basementAreas: Optional[List[float]] = None
    basementFootprints: Optional[List[float]] = None

    class Config:
        extra = "allow"


class DocumentItem(BaseModel):
    id: str
    code: str
    title: str
    type: str  # "LUẬT" | "Nghị định" | "Thông tư" | "QCVN" | "TCVN" | "Khác"
    link: str
    content: Optional[str] = ""
    isCustom: Optional[bool] = False
    uploadedAt: Optional[str] = None


class ChatMessage(BaseModel):
    id: str
    sender: str  # "user" | "assistant"
    text: str
    timestamp: str


class ChecklistItem(BaseModel):
    stt: int
    category: str
    criteria: str
    requirement: str
    result: str
    note: str
    reference: str


class Session(BaseModel):
    id: str
    title: str
    projectInfo: ProjectInfo
    messages: List[ChatMessage] = Field(default_factory=list)
    updatedAt: str
    checklist: Optional[List[ChecklistItem]] = None
    isSubjectToAppraisal: Optional[bool] = None
    appraisalReason: Optional[str] = None
    warnings: Optional[List[str]] = None

    class Config:
        extra = "allow"


# ---------------------------------------------------------------------------
# Structured-output schema used for the Gemini "responseSchema" JSON contract.
# ---------------------------------------------------------------------------

class ChecklistItemAI(BaseModel):
    stt: int = Field(description="STT từ 1 đến 17 đúng theo bảng quy chuẩn kiểm tra.")
    result: str = Field(
        description="Một trong các giá trị: Đạt | Không đạt | Không bắt buộc | "
        "Khuyến nghị mạnh | Khuyến nghị | Cần xem xét | Cần đo đạc"
    )
    note: str = Field(
        description="Phân tích kĩ thuật sắc sảo, ngắn gọn (tối đa 2 câu) áp dụng riêng cho công trình này."
    )


class ExtractedProjectInfo(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    investor: Optional[str] = None
    designer: Optional[str] = None
    stage: Optional[str] = None
    type: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    pcccHeight: Optional[float] = None
    floorArea: Optional[float] = None
    totalFloorArea: Optional[float] = None
    floors: Optional[int] = None
    basements: Optional[int] = None
    fireRating: Optional[str] = None
    commercialDetails: Optional[str] = None
    floorFunctions: Optional[List[str]] = Field(
        default=None,
        description="Danh sách công năng chi tiết của từng tầng nổi theo thứ tự từ tầng 1 đến tầng cao.",
    )


class DeepAppraisalResponse(BaseModel):
    reply: str = Field(
        description="Tin nhắn trả lời phân tích hướng dẫn cụ thể cho khách hàng dạng markdown, súc tích, cởi mở."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Danh sách 1-4 thông báo cảnh báo mâu thuẫn hay thiếu sót dữ liệu kĩ thuật của công trình.",
    )
    isSubjectToAppraisal: bool = Field(
        description="Xác nhận công trình có thuộc đối tượng bắt buộc thực hiện thủ tục thẩm duyệt PCCC Công an hay không."
    )
    appraisalReason: str = Field(
        description="Lý giải chi tiết căn cứ tính pháp lý Nghị định 105 cho việc thuộc hay không thuộc diện thẩm duyệt."
    )
    checklist: List[ChecklistItemAI] = Field(default_factory=list)
    extractedProjectInfo: Optional[ExtractedProjectInfo] = None
