"""Schema validate thông số dự án — FIX B03 (Bao_Cao_QA_Lan_2.md):

'Ô number KHÔNG đặt min=0: vẫn nhập được -5 tầng, -9.999.999 m² và sai
logic (4 tầng nhưng tổng 50m²). Chỉ hiện banner cảnh báo + để AI tự bắt
lỗi, KHÔNG chặn cứng tại frontend.'

Trước đây endpoint PUT /api/sessions/{id}/project nhận `body: dict` thô,
KHÔNG hề validate — bất kỳ giá trị nào (kể cả âm, kể cả vô lý) đều được
ghi thẳng vào DB. Module này định nghĩa schema chặn cứng ở tầng API
(không phụ thuộc frontend có validate hay không — người dùng có thể gọi
thẳng API bằng curl/Postman bỏ qua UI).
"""
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=500)
    investor: Optional[str] = Field(default=None, max_length=255)
    designer: Optional[str] = Field(default=None, max_length=255)
    stage: Optional[str] = Field(default=None, max_length=255)
    type: Optional[str] = Field(default=None, max_length=255)

    # FIX B03: ge=0 chặn cứng số âm (trước đây nhập được -5 tầng, -9.999.999 m²)
    length: Optional[float] = Field(default=None, ge=0, le=100_000)
    width: Optional[float] = Field(default=None, ge=0, le=100_000)
    height: Optional[float] = Field(default=None, ge=0, le=1000)
    pcccHeight: Optional[float] = Field(default=None, ge=0, le=1000)
    floorArea: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    totalFloorArea: Optional[float] = Field(default=None, ge=0, le=10_000_000)
    floors: Optional[int] = Field(default=None, ge=0, le=200)
    basements: Optional[int] = Field(default=None, ge=0, le=20)
    fireRating: Optional[str] = Field(default=None, max_length=32)
    commercialDetails: Optional[str] = Field(default=None, max_length=2000)

    floorFunctions: Optional[List[str]] = None
    basementFunctions: Optional[List[str]] = None
    basementHeights: Optional[List[float]] = None
    basementAreas: Optional[List[float]] = None
    basementFootprints: Optional[List[float]] = None

    @model_validator(mode="after")
    def _check_area_consistency(self) -> "ProjectUpdateRequest":
        """FIX B03: chặn cứng trường hợp 'Tầng=4, DT=30, Tổng=50' (sai logic
        — QA lần 2 ghi nhận). Quy tắc: tổng diện tích sàn không được nhỏ hơn
        diện tích 1 tầng (luôn đúng về mặt toán học), và không được nhỏ hơn
        50% của (diện tích tầng điển hình × số tầng) — cho phép sai số 50%
        để không chặn nhầm các công trình có tầng thu hẹp dần (giật cấp,
        tầng áp mái nhỏ hơn) nhưng vẫn chặn được các trường hợp vô lý rõ
        ràng như ví dụ QA nêu (30×4=120, nhập 50 → 50 < 120×0.5=60 → chặn)."""
        floors = self.floors or 0
        floor_area = self.floorArea or 0
        total = self.totalFloorArea or 0

        if floor_area > 0 and total > 0 and total < floor_area:
            raise ValueError(
                f"Tổng diện tích sàn ({total}m²) không thể nhỏ hơn diện tích 1 tầng ({floor_area}m²) — "
                "vui lòng kiểm tra lại số liệu."
            )

        if floors >= 1 and floor_area > 0 and total > 0:
            expected_min = floor_area * floors * 0.5
            if total < expected_min:
                raise ValueError(
                    f"Tổng diện tích sàn ({total}m²) quá nhỏ so với {floors} tầng × {floor_area}m²/tầng "
                    f"(dự kiến tối thiểu ~{expected_min:.0f}m²) — vui lòng kiểm tra lại số liệu."
                )

        return self
