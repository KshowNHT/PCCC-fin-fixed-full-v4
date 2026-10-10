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
from typing import List, Optional, Annotated

from pydantic import BaseModel, Field, model_validator, ConfigDict


class BuildingComponent(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid", strict=True)
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=500)
    type: str = Field(default="", max_length=255)
    floors: int = Field(default=0, ge=0, le=200)
    basements: int = Field(default=0, ge=0, le=20)
    height: float = Field(default=0, ge=0, le=1000)
    pcccHeight: float = Field(default=0, ge=0, le=1000)
    floorArea: float = Field(default=0, ge=0, le=1000000)
    totalFloorArea: float = Field(default=0, ge=0, le=10000000)
    volume: float = Field(default=0, ge=0, le=1000000000)
    hazardClass: str = Field(default="", pattern=r"^(|A|B|C|D|E)$")
    industrialSubtype: str = Field(default="", pattern=r"^(|other|special)$")
    fireRating: str = Field(default="", max_length=32)
    commercialDetails: str = Field(default="", max_length=2000)
    sourcePages: List[Annotated[int, Field(ge=1, le=200)]] = Field(default_factory=list, max_length=200)
    sourceText: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def check_component(self):
        if self.totalFloorArea and self.floorArea and self.totalFloorArea < self.floorArea:
            raise ValueError("Diện tích sàn hạng mục nhỏ hơn diện tích một tầng")
        if any(t in self.name.lower() for t in ("quy mô lớn nhất", "tổng cộng", "toàn dự án")):
            raise ValueError("Dòng tổng hợp không phải hạng mục độc lập")
        return self


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid", strict=True)
    name: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=500)
    investor: Optional[str] = Field(default=None, max_length=255)
    designer: Optional[str] = Field(default=None, max_length=255)
    stage: Optional[str] = Field(default=None, max_length=255)
    type: Optional[str] = Field(default=None, max_length=255)

    components: Optional[List[BuildingComponent]] = Field(default=None, max_length=100)
    componentsComplete: Optional[bool] = None
    sharedSystems: Optional[bool] = None
    concurrentDesign: Optional[bool] = None
    volume: Optional[float] = Field(default=None, ge=0, le=1000000000)
    hazardClass: Optional[str] = Field(default=None, pattern=r"^(|A|B|C|D|E)$")
    industrialSubtype: Optional[str] = Field(default=None, pattern=r"^(|other|special)$")

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

    floorFunctions: Optional[List[Annotated[str, Field(max_length=500)]]] = Field(default=None, max_length=200)
    basementFunctions: Optional[List[Annotated[str, Field(max_length=500)]]] = Field(default=None, max_length=20)
    basementHeights: Optional[List[Annotated[float, Field(ge=0, le=100)]]] = Field(default=None, max_length=20)
    basementAreas: Optional[List[Annotated[float, Field(ge=0, le=1000000)]]] = Field(default=None, max_length=20)
    basementFootprints: Optional[List[Annotated[float, Field(ge=0, le=1000000)]]] = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def _check_area_consistency(self) -> "ProjectUpdateRequest":
        """Validate only known contradictions; stepped buildings may be legitimate."""
        if self.components:
            ids = [c.id for c in self.components]
            names = [c.name.strip().casefold() for c in self.components]
            if len(set(ids)) != len(ids) or len(set(names)) != len(names):
                raise ValueError("Hạng mục trùng mã hoặc tên; cần phân biệt từng nhà")
        floors = self.floors or 0
        floor_area = self.floorArea or 0
        total = self.totalFloorArea or 0

        if floor_area > 0 and total > 0 and total < floor_area:
            raise ValueError(
                f"Tổng diện tích sàn ({total}m²) không thể nhỏ hơn diện tích 1 tầng ({floor_area}m²) — "
                "vui lòng kiểm tra lại số liệu."
            )

        return self
