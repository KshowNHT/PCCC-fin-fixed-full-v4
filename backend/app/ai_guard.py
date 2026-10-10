"""Lớp bảo vệ giữa AI và hồ sơ: hai việc, đều là hàm thuần (không I/O) nên test được hàng loạt.

1) `sanitize_extracted_info()` — số liệu do AI "trích xuất" từ đoạn chat/bản vẽ KHÔNG được ghi thẳng
   vào hồ sơ. Trước đây `extractedProjectInfo` đi qua `apply_dict()` không kiểm tra gì, bỏ qua cả luật
   khoảng giá trị và luật diện tích của `ProjectUpdateRequest`. Hệ quả: kết luận thẩm duyệt tính chính xác
   nhưng trên số liệu có thể sai (AI bịa số tầng, ghi đè số người dùng đã nhập, đổi loại công trình thành
   karaoke...). Quy tắc: một giá trị AI muốn THAY ĐỔI hồ sơ chỉ được nhận khi
     - đúng kiểu và nằm trong khoảng hợp lệ, và qua luật liên trường (diện tích/số tầng);
     - xuất hiện trong chính lời người dùng (hoặc là tích số tầng × diện tích 1 tầng đã có);
     - các trường mô tả (tên, địa điểm, chủ đầu tư...) chỉ được điền khi đang trống, không ghi đè.

2) `guard_reply()` — phần `reply` của AI chỉ được dặn qua prompt, không có gì ngăn nó nói ngược kết luận
   hiển thị trên màn hình (ví dụ "vượt ngưỡng" trong khi 5 < 7). Hàm này tìm các câu mâu thuẫn với
   `appraisalBasis` và lược bỏ chúng.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from app.appraisal_basis import (
    _EXACT_TYPE_MAP,
    _KARAOKE_REGEX,
    _match_category,
    classify_building,
    fmt_number,
    to_number,
)
from app.schemas_project import ProjectUpdateRequest

NUMERIC_FIELDS = ("length", "width", "height", "pcccHeight", "floorArea", "totalFloorArea", "floors", "basements")
INT_FIELDS = {"floors", "basements"}
METADATA_FIELDS = ("name", "location", "investor", "designer", "stage")
KNOWN_RATINGS = ("Bậc I", "Bậc II", "Bậc III", "Bậc IV", "Bậc V")
DEFAULT_PLACEHOLDER_NAMES = {"", "dự án mới", "hồ sơ mới"}

FIELD_LABELS = {
    "length": "chiều dài", "width": "chiều rộng", "height": "chiều cao công trình", "pcccHeight": "chiều cao PCCC",
    "floorArea": "diện tích xây dựng 1 tầng", "totalFloorArea": "tổng diện tích sàn", "floors": "số tầng nổi",
    "basements": "số tầng hầm", "type": "loại công trình", "fireRating": "bậc chịu lửa",
    "commercialDetails": "chi tiết kinh doanh", "floorFunctions": "công năng từng tầng",
    "name": "tên công trình", "location": "địa điểm", "investor": "chủ đầu tư", "designer": "đơn vị thiết kế",
    "stage": "giai đoạn",
}

# Giá trị công năng từng tầng mà giao diện cho chọn (Sidebar.tsx) — AI chỉ được dùng đúng các giá trị này.
ALLOWED_FLOOR_FUNCTIONS = {
    "Nhà ở riêng lẻ / Dân dụng", "Kinh doanh thương mại / Dịch vụ nhẹ", "Dịch vụ giải trí Karaoke, Vũ trường",
    "Văn phòng, Phòng làm việc", "Nhà kho lưu trữ hàng hóa", "Bãi đỗ xe hoặc gian kĩ thuật",
    "Xưởng sản xuất / Dây chuyền công nghệ", "Lớp học / Phòng thí nghiệm",
    "Khán phòng / Rạp hát / Khu vực khán giả", "Khu vực bếp ăn / Căng tin tập thể",
}

# ---------------------------------------------------------------------------
# 1. Chặn dữ liệu trích xuất
# ---------------------------------------------------------------------------
_FLOOR_FUNCTION_KEYWORDS = [  # thứ tự quan trọng: nhóm nguy cơ cao trước
    (r"karaoke|vũ trường|vu truong|\bbar\b|\bpub\b", "Dịch vụ giải trí Karaoke, Vũ trường"),
    (r"khán phòng|rạp|hội trường", "Khán phòng / Rạp hát / Khu vực khán giả"),
    (r"lớp học|giáo dục|thí nghiệm|phòng học", "Lớp học / Phòng thí nghiệm"),
    (r"xưởng|sản xuất|dây chuyền", "Xưởng sản xuất / Dây chuyền công nghệ"),
    (r"\bkho\b|lưu trữ|chứa hàng", "Nhà kho lưu trữ hàng hóa"),
    (r"bếp|căng tin", "Khu vực bếp ăn / Căng tin tập thể"),
    (r"gara|đỗ xe|kĩ thuật|kỹ thuật|máy phát", "Bãi đỗ xe hoặc gian kĩ thuật"),
    (r"văn phòng|làm việc|công sở", "Văn phòng, Phòng làm việc"),
    (r"cửa hàng|kinh doanh|thương mại|dịch vụ|bán hàng", "Kinh doanh thương mại / Dịch vụ nhẹ"),
    (r"nhà ở|dân dụng|phòng ngủ|sinh hoạt|\bở\b", "Nhà ở riêng lẻ / Dân dụng"),
]


def map_floor_function(text: str) -> Optional[str]:
    """Đưa công năng tầng AI/OCR viết tự do về đúng giá trị mà giao diện cho chọn (None = không nhận diện)."""
    if text in ALLOWED_FLOOR_FUNCTIONS:
        return text
    low = (text or "").lower()
    for pattern, value in _FLOOR_FUNCTION_KEYWORDS:
        if re.search(pattern, low):
            return value
    return None

_WORD_UNITS = {"một": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "sáu": 6, "bảy": 7, "bẩy": 7, "tám": 8, "chín": 9}


def numbers_in_text(text: str) -> List[float]:
    """Mọi con số người dùng đã viết: '5 tầng', '1.200 m2', '12,5m', và số chữ 'năm tầng', 'mười hai tầng'."""
    low = (text or "").lower()
    nums = [to_number(m.group(0)) for m in re.finditer(r"\d[\d.,]*", low)]
    for m in re.finditer(r"\b(một|hai|ba|bốn|tư|năm|sáu|bảy|bẩy|tám|chín|mười)\s+(tầng|hầm)\b", low):
        nums.append(10 if m.group(1) == "mười" else _WORD_UNITS[m.group(1)])
    for m in re.finditer(r"\bmười\s+(một|hai|ba|bốn|lăm|sáu|bảy|tám|chín)\s+(tầng|hầm)\b", low):
        nums.append(10 + (5 if m.group(1) == "lăm" else _WORD_UNITS[m.group(1)]))
    return [n for n in nums if n > 0]


def _grounded(value: float, nums: List[float]) -> bool:
    return any(abs(value - n) < 1e-6 for n in nums)


def _rating_grounded(rating: str, text: str) -> bool:
    roman = rating.replace("Bậc", "").strip().lower()
    digit = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5"}[roman]
    low = (text or "").lower()
    return bool(re.search(rf"bậc\s*({roman}|{digit})\b", low))


_TYPE_VALUE_BY_CATEGORY = {}
for _label, _cat in _EXACT_TYPE_MAP.items():
    _TYPE_VALUE_BY_CATEGORY.setdefault(_cat, _label)
_DROPDOWN_VALUES = {
    "nhà ở riêng lẻ kết hợp kinh doanh": "Nhà ở riêng lẻ kết hợp kinh doanh",
    "nhà ở riêng lẻ": "Nhà ở riêng lẻ",
    "cơ sở kinh doanh karaoke, vũ trường": "Cơ sở kinh doanh Karaoke, Vũ trường",
    "gara ô tô": "Gara ô tô",
    "văn phòng, khách sạn công cộng": "Văn phòng, khách sạn công cộng",
    "nhà kho xếp giá đỡ kệ cao": "Nhà kho xếp giá đỡ kệ cao",
    "chợ, trung tâm thương mại": "Chợ, Trung tâm thương mại",
    "nhà máy, nhà xưởng sản xuất": "Nhà máy, nhà xưởng sản xuất",
    "cơ sở giáo dục, trường học": "Cơ sở giáo dục, trường học",
    "rạp hát, hội trường, trung tâm tổ chức sự kiện": "Rạp hát, hội trường, trung tâm tổ chức sự kiện",
}


def _dropdown_value_for(category: str) -> Optional[str]:
    for low, original in _DROPDOWN_VALUES.items():
        if _EXACT_TYPE_MAP.get(low) == category:
            return original
    return None


def _vi_message(msg: str) -> str:
    """Việt hoá thông báo lỗi của pydantic để hiển thị cho người dùng (không lộ tiếng Anh thô)."""
    msg = re.sub(r"^Value error,\s*", "", msg or "").strip()
    m = re.search(r"less than or equal to ([\d.]+)", msg)
    if m:
        return f"giá trị phải nhỏ hơn hoặc bằng {fmt_number(float(m.group(1)))}"
    m = re.search(r"greater than or equal to ([\d.]+)", msg)
    if m:
        return f"giá trị phải lớn hơn hoặc bằng {fmt_number(float(m.group(1)))}"
    if re.search(r"[a-zA-Z]{4,} (should|must|is) ", msg):
        return "giá trị không hợp lệ"
    return msg or "không hợp lệ"


def _validate_merged(current: Dict[str, Any], accepted: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Thử kiểm tra (hồ sơ hiện tại + giá trị AI) bằng đúng schema của API. Trả về [(trường, lý do)] bị lỗi."""
    merged = {k: current.get(k) for k in NUMERIC_FIELDS if to_number(current.get(k)) > 0}
    merged.update({k: v for k, v in accepted.items() if k in NUMERIC_FIELDS})
    try:
        ProjectUpdateRequest(**merged)
        return []
    except ValidationError as exc:
        problems = []
        for err in exc.errors():
            loc = [p for p in err.get("loc", ()) if isinstance(p, str)]
            problems.append((loc[-1] if loc else "*", _vi_message(err.get("msg", ""))))
        return problems


def sanitize_extracted_info(
    extracted: Optional[Dict[str, Any]],
    current: Dict[str, Any],
    grounding_text: Optional[str],
) -> Dict[str, Any]:
    """Lọc dữ liệu AI trích xuất.

    `grounding_text`: lời người dùng làm căn cứ (tin nhắn chat, hoặc nội dung nút Kiểm duyệt).
    Truyền None khi nguồn không phải lời người dùng (OCR bản vẽ) — khi đó bỏ bước "phải xuất hiện
    trong lời người dùng" nhưng vẫn giữ kiểm tra khoảng giá trị và luật liên trường.

    Trả về {"accepted": {...}, "rejected": [str], "derived": [str]}.
    """
    accepted: Dict[str, Any] = {}
    rejected: List[str] = []
    derived: List[str] = []
    if not isinstance(extracted, dict):
        return {"accepted": accepted, "rejected": rejected, "derived": derived}

    text = grounding_text or ""
    nums = numbers_in_text(text)
    check_grounding = grounding_text is not None

    def reject(field: str, value: Any, why: str) -> None:
        rejected.append(f"Đã bỏ qua {FIELD_LABELS.get(field, field)} = “{value}” do AI đề xuất: {why}.")

    # ---- số liệu ----
    for field in NUMERIC_FIELDS:
        raw = extracted.get(field)
        if raw is None or raw == "":
            continue
        if field == "basements" and isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw == 0:
            if to_number(current.get(field)) != 0:
                accepted[field] = 0
            continue
        value = to_number(raw)
        if value <= 0:
            reject(field, raw, "không phải số dương hợp lệ")
            continue
        if field in INT_FIELDS:
            if abs(value - round(value)) > 1e-9:
                reject(field, raw, "phải là số nguyên")
                continue
            value = int(round(value))
        if abs(value - to_number(current.get(field))) < 1e-9:
            continue  # không đổi gì
        accepted[field] = value

    def enforce_rules() -> None:
        """Luật khoảng giá trị + liên trường: loại dần các trường do AI đề xuất mà làm hồ sơ vi phạm."""
        if not _validate_merged(current, {}):
            for _ in range(4):
                problems = _validate_merged(current, accepted)
                if not problems:
                    return
                area_trio = [f for f in ("floors", "floorArea", "totalFloorArea") if f in accepted]
                dropped = False
                for field, msg in problems:
                    targets = [field] if field in accepted else (area_trio if field == "*" else [])
                    for t in targets:
                        if t in accepted:
                            reject(t, accepted.pop(t), f"vi phạm luật dữ liệu ({msg})")
                            dropped = True
                if not dropped:
                    return
        else:
            # hồ sơ hiện tại đã lệch sẵn: chỉ còn kiểm tra khoảng giá trị từng trường
            for field in list(accepted):
                if _validate_merged({}, {field: accepted[field]}):
                    reject(field, accepted.pop(field), "ngoài khoảng giá trị cho phép")

    enforce_rules()  # lượt 1: bỏ ngay số ngoài khoảng/vi phạm luật — không để chúng làm gốc cho số "suy ra"

    # căn cứ trong lời người dùng — HAI LƯỢT: các trường gốc trước, tổng diện tích suy ra sau.
    # (Lỗi đã sửa: trước đây xét totalFloorArea trước nên có thể nhận "5 tầng × 100 m²" dù số "5 tầng"
    # sau đó bị loại vì không có trong lời người dùng.)
    if check_grounding:
        for field in [f for f in list(accepted) if f != "totalFloorArea"]:
            if not _grounded(float(accepted[field]), nums):
                reject(field, fmt_number(float(accepted[field])), "con số này không có trong lời bạn nhập (hệ thống không cho AI tự suy ra)")
                accepted.pop(field)
        if "totalFloorArea" in accepted and not _grounded(float(accepted["totalFloorArea"]), nums):
            value = accepted["totalFloorArea"]
            fl = accepted.get("floors", int(to_number(current.get("floors"))))
            fa = accepted.get("floorArea", to_number(current.get("floorArea")))
            if fl and fa and abs(value - fl * fa) < 1e-6:
                derived.append(
                    f"Tổng diện tích sàn {fmt_number(value)} m² do AI tính từ {fl} tầng × {fmt_number(fa)} m²/tầng — "
                    "hãy kiểm tra lại."
                )
            else:
                reject("totalFloorArea", fmt_number(float(value)), "con số này không có trong lời bạn nhập (hệ thống không cho AI tự suy ra)")
                accepted.pop("totalFloorArea")

    enforce_rules()  # lượt 2: loại bỏ một số trường có thể làm lộ vi phạm liên trường

    # ---- bậc chịu lửa ----
    rating = extracted.get("fireRating")
    if isinstance(rating, str) and rating.strip() and rating.strip() != str(current.get("fireRating") or "").strip():
        rating = rating.strip()
        if rating not in KNOWN_RATINGS:
            reject("fireRating", rating, "không thuộc Bậc I–V")
        elif check_grounding and not _rating_grounded(rating, text):
            reject("fireRating", rating, "bậc này không có trong lời bạn nhập")
        else:
            accepted["fireRating"] = rating

    # ---- loại công trình (ảnh hưởng trực tiếp tới kết luận nên kiểm chặt) ----
    ptype = extracted.get("type")
    if isinstance(ptype, str) and ptype.strip():
        ptype = ptype.strip()
        category, _ = classify_building({"type": ptype})
        current_category, _ = classify_building({"type": current.get("type")})
        if category == "unclassified":
            reject("type", ptype, "hệ thống không nhận diện được loại công trình này")
        elif ptype != str(current.get("type") or "").strip():
            low = text.lower()
            supported = (not check_grounding) or ptype.lower() in low or _match_category(low) == category or (
                category == "karaoke_entertainment" and bool(_KARAOKE_REGEX.search(low))
            )
            if not supported:
                reject("type", ptype, "loại công trình này không được nhắc trong lời bạn nhập")
            else:
                accepted["type"] = ptype

    # ---- chi tiết kinh doanh: không để AI "bịa" công năng nguy cơ cao ----
    details = extracted.get("commercialDetails")
    if isinstance(details, str) and details.strip() and details.strip() != str(current.get("commercialDetails") or "").strip():
        details = details.strip()[:2000]
        if _KARAOKE_REGEX.search(details.lower()) and check_grounding and not _KARAOKE_REGEX.search(text.lower()):
            reject("commercialDetails", details[:60], "nhắc tới karaoke/vũ trường nhưng bạn không nói vậy")
        elif str(current.get("commercialDetails") or "").strip():
            reject("commercialDetails", details[:60], "không ghi đè nội dung bạn đã nhập")
        else:
            accepted["commercialDetails"] = details

    # ---- công năng từng tầng ----
    funcs = extracted.get("floorFunctions")
    if isinstance(funcs, list) and funcs:
        mapped = [map_floor_function(f) if isinstance(f, str) else None for f in funcs]
        clean = [m for m in mapped if m]
        if len(clean) != len(funcs) or len(clean) > 200:
            reject("floorFunctions", f"{len(funcs)} mục", "có công năng hệ thống không nhận diện được")
        elif clean != list(current.get("floorFunctions") or []):
            if check_grounding and any(_KARAOKE_REGEX.search(f.lower()) for f in clean) and not _KARAOKE_REGEX.search(text.lower()):
                reject("floorFunctions", "có tầng karaoke", "bạn không nhắc tới karaoke/vũ trường")
            else:
                accepted["floorFunctions"] = clean

    # ---- thông tin mô tả: chỉ điền chỗ trống ----
    for field in METADATA_FIELDS:
        value = extracted.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()[:500]
        existing = str(current.get(field) or "").strip()
        if value == existing:
            continue
        if existing.lower() in DEFAULT_PLACEHOLDER_NAMES or not existing:
            accepted[field] = value
        else:
            reject(field, value[:60], "không ghi đè nội dung bạn đã nhập")

    return {"accepted": accepted, "rejected": rejected, "derived": derived}


# ---------------------------------------------------------------------------
# 2. Kiểm tra cứng phần trả lời chat
# ---------------------------------------------------------------------------
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…;])\s+|\n+")
_NEG_WINDOW = re.compile(r"(không|chưa|miễn|chẳng|đâu|hết|nếu không)\s*(thuộc diện|cần|phải|bắt buộc|còn)?\s*$")
_CONDITIONAL = re.compile(
    r"\b(nếu|khi|trường hợp|giả sử|với điều kiện|trừ khi|thì sẽ|ví dụ|hay không|liệu|chưa thể|chưa đủ|có thuộc|có phải)\b"
)

_REQUIRED_CLAIM = re.compile(
    r"(bắt buộc|buộc phải|phải|cần|thuộc diện)\s+(phải\s+)?(nộp\s+hồ sơ\s+|trình\s+|đệ trình\s+)?(để\s+)?(được\s+)?thẩm duyệt"
    r"|thuộc diện\s+(bắt buộc\s+)?thẩm duyệt"
)
_NOT_REQUIRED_CLAIM = re.compile(
    r"không\s+(thuộc diện|cần|phải|bắt buộc)\s+(phải\s+)?(nộp\s+hồ sơ\s+)?(để\s+)?(được\s+)?thẩm duyệt|miễn\s+(thủ tục\s+)?thẩm duyệt"
)
_REACHED_CLAIM = re.compile(r"(đạt hoặc vượt|vượt|đạt tới|đạt|chạm|đã đạt)\s+(một trong\s+)?(các\s+|cả\s+)?(hai\s+)?ngưỡng")
_NOT_REACHED_CLAIM = re.compile(
    r"(dưới|chưa đạt|chưa vượt|không vượt|không đạt|thấp hơn|nhỏ hơn)\s+(cả\s+)?(các\s+|hai\s+|mọi\s+)?ngưỡng"
)
_FLOOR_CLAIM = re.compile(
    r"\b(công trình|tòa nhà|dự án|nhà)\b[^.\n]{0,25}?(?<!từ )(?<!trên )(?<!dưới )(?<!đến )(?<!tối thiểu )(?<!lên )\b(\d{1,3})\s*tầng"
)
_AREA_CLAIM = re.compile(r"(tổng diện tích sàn|diện tích sàn)[^.\n\d]{0,20}(\d[\d.,]*)\s*m(?:²|2)")
_KNOWN_LIMITS = {3000.0, 1000.0, 1500.0, 5000.0, 7.0, 4.0, 3.0}
# "ngưỡng" còn xuất hiện trong ngữ cảnh THIẾT BỊ ("dưới ngưỡng bắt buộc trang bị họng nước") — đó không phải
# ngưỡng quy mô thẩm duyệt nên không được đem so với kết luận thẩm duyệt.
_EQUIPMENT_CONTEXT = re.compile(r"họng nước|vòi rồng|sprinkler|đầu phun|báo cháy|cảm biến|đèn exit|bình bột|bể chứa|trụ nước|bậc chịu lửa")


def _asserts(pattern: "re.Pattern[str]", low: str) -> bool:
    """Câu có KHẲNG ĐỊNH theo `pattern` không (bỏ qua nếu ngay trước đó có từ phủ định)."""
    for m in pattern.finditer(low):
        window = low[max(0, m.start() - 18): m.start()]
        if not _NEG_WINDOW.search(window):
            return True
    return False


def _sentence_violations(sentence: str, basis: Dict[str, Any], project: Dict[str, Any]) -> List[str]:
    low = sentence.lower().replace("thẩm định", "thẩm duyệt")
    out: List[str] = []
    if "bất kể quy mô" in low or "không phụ thuộc quy mô" in low:
        out.append("Khẳng định miễn điều kiện quy mô không có căn cứ trong bộ quy tắc đang áp dụng")
    if re.search(r"(đã đạt|đạt yêu cầu|đảm bảo quy định|vi phạm|không đạt)" ,low) and _EQUIPMENT_CONTEXT.search(low):
        out.append("Chưa có bằng chứng để chứng nhận kết quả kỹ thuật")
    status = basis["status"]
    triggered = basis.get("triggeredBy") or []
    conditional = bool(_CONDITIONAL.search(low))

    about_equipment = bool(_EQUIPMENT_CONTEXT.search(low))
    if not conditional:
        if status != "required" and _asserts(_REQUIRED_CLAIM, low):
            out.append("nói công trình BẮT BUỘC thẩm duyệt trong khi hệ thống kết luận không phải vậy")
        if status in ("required", "insufficient_data") and _asserts(_NOT_REQUIRED_CLAIM, low):
            out.append("nói công trình KHÔNG thuộc diện thẩm duyệt trong khi hệ thống kết luận khác")
        if not triggered and not about_equipment and _asserts(_REACHED_CLAIM, low):
            out.append("nói công trình đạt/vượt ngưỡng quy mô nhưng không có ngưỡng nào đạt")
        if triggered and not about_equipment and _asserts(_NOT_REACHED_CLAIM, low) and basis.get("ruleMode") == "threshold":
            out.append("nói công trình dưới ngưỡng nhưng đã có ngưỡng đạt")

    floors = to_number(project.get("floors"))
    basements = to_number(project.get("basements"))
    for m in _FLOOR_CLAIM.finditer(low):
        n = float(m.group(2))
        if n in (floors, basements):
            continue
        # "ngưỡng 7 tầng", "thấp hơn 7 tầng", "tối thiểu 4 tầng"... là NGƯỠNG, không phải số tầng của công trình
        if re.search(r"ngưỡng|hơn|bằng|ít nhất|nhiều nhất|tối đa|tối thiểu|quy định|yêu cầu|mức", m.group(0)):
            continue
        if floors > 0 or n not in _KNOWN_LIMITS:
            out.append(f"nêu {int(n)} tầng, khác số tầng trong hồ sơ ({fmt_number(floors) if floors else 'chưa nhập'})")
    total = to_number(project.get("totalFloorArea"))
    for m in _AREA_CLAIM.finditer(low):
        n = to_number(m.group(2))
        if n > 0 and n not in _KNOWN_LIMITS and abs(n - total) > 1e-6 and abs(n - to_number(project.get("floorArea"))) > 1e-6:
            out.append(f"nêu diện tích {fmt_number(n)} m², khác hồ sơ ({fmt_number(total) if total else 'chưa nhập'} m²)")
    return out


def guard_reply(reply: Optional[str], basis: Dict[str, Any], project: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Lược bỏ các câu trong lời AI mâu thuẫn với kết luận tính cứng. Trả về (văn bản, danh sách vi phạm)."""
    text = (reply or "").strip()
    if not text:
        return "", []
    kept: List[str] = []
    violations: List[str] = []
    dropped = 0
    for sentence in _SENTENCE_SPLIT.split(text):
        if not sentence.strip():
            continue
        found = _sentence_violations(sentence, basis, project)
        if found:
            violations += found
            dropped += 1
        else:
            kept.append(sentence.strip())
    if not violations:
        return text, []
    body = "\n".join(kept).strip()
    note = (
        f"ℹ️ Hệ thống đã lược bỏ {dropped} câu trong phần trả lời của AI vì mâu thuẫn với kết luận tính từ "
        f"số liệu hồ sơ. Kết luận chính thức: {basis['conclusion']}"
    )
    return (f"{body}\n\n{note}" if body else f"Kết luận của hệ thống: {basis['conclusion']}"), violations


def guard_warnings(warnings: Optional[List[str]], basis: Dict[str, Any], project: Dict[str, Any]) -> Tuple[List[str], int]:
    """Loại các cảnh báo do AI viết mà mâu thuẫn với kết luận tính cứng. Trả về (danh sách giữ lại, số bị loại)."""
    kept: List[str] = []
    dropped = 0
    for w in warnings or []:
        if isinstance(w, str) and w.strip():
            if _sentence_violations(w, basis, project):
                dropped += 1
            else:
                kept.append(w.strip()[:1000])
    return kept, dropped
