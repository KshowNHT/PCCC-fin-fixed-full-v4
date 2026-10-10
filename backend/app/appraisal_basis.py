"""Classification and scale screening. Unsupported groups require manual review."""
import math
import unicodedata
import re
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# 1. Tiện ích số liệu
# --------------------------------------------------------------------------


def to_number(value: Any) -> float:
    """Ép giá trị bất kỳ về số thực an toàn (>= 0).

    Dữ liệu có thể đến từ form (số), từ OCR/AI (chuỗi như "1.200", "12,5",
    "5 tầng", "500 m2") hoặc rỗng/None. Sai kiểu hoặc không đọc được -> 0
    (nghĩa là "chưa có dữ liệu"), KHÔNG ném lỗi làm hỏng cả bước thẩm định.
    """
    if value is None or isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) and value > 0 else 0.0
    if isinstance(value, str):
        if re.search(r"-\s*\d", value):
            return 0.0
        match = re.search(r"\d[\d.,]*", value)
        if not match:
            return 0.0
        raw = match.group(0).rstrip(".,")
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):  # 1.200 / 3.000.000 (dấu chấm ngăn nghìn)
            raw = raw.replace(".", "")
        elif re.fullmatch(r"\d{1,3}(,\d{3})+", raw):  # 1,200 kiểu quốc tế
            raw = raw.replace(",", "")
        else:
            raw = raw.replace(",", ".")
        try:
            number = float(raw)
        except ValueError:
            return 0.0
        return number if math.isfinite(number) and number > 0 else 0.0
    return 0.0


def fmt_number(value: float) -> str:
    """Định dạng số kiểu Việt Nam: 3000 -> '3.000', 12.5 -> '12,5'."""
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}".replace(",", ".")
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def effective_height(project: Dict[str, Any]) -> float:
    """Chiều cao dùng để xét ngưỡng = chiều cao PCCC nếu có, nếu không thì chiều cao công trình.

    LỖI ĐÃ SỬA: form nhập liệu chỉ có ô "Chiều cao PCCC" (trường `pcccHeight`),
    KHÔNG có ô nhập `height`. Nhưng quy tắc họng nước (mục 11) và ngưỡng nhà
    kho trước đây đọc `height` → với dữ liệu nhập từ form luôn bằng 0 nên các
    quy tắc theo chiều cao KHÔNG BAO GIỜ được kích hoạt.
    """
    pccc = to_number(project.get("pcccHeight"))
    return pccc if pccc > 0 else to_number(project.get("height"))


# --------------------------------------------------------------------------
# 2. Danh mục nhóm công năng
# --------------------------------------------------------------------------

# Annex III items 3 and 6; applied only after classification.
GENERAL_THRESHOLDS = (("floors", ">=", 7), ("totalFloorArea", ">=", 3000))
CATEGORY_INFO = {
    "karaoke_entertainment": {"label": "Karaoke / vũ trường / quán bar"},
    "mixed_residential": {"label": "Nhà ở riêng lẻ kết hợp kinh doanh / nhà hỗn hợp"},
    "private_house": {"label": "Nhà ở riêng lẻ"},
    "warehouse": {"label": "Nhà kho / kho chứa hàng"},
    "market_mall": {"label": "Chợ / trung tâm thương mại / siêu thị"},
    "school": {"label": "Trường học / cơ sở giáo dục"},
    "office_hotel": {"label": "Văn phòng / công sở / khách sạn"},
    "garage": {"label": "Gara ô tô / bãi đỗ xe"},
    "factory": {"label": "Nhà máy / nhà xưởng"},
    "assembly": {"label": "Rạp hát / hội trường / sự kiện"},
    "unclassified": {"label": "Chưa xác định nhóm công năng"},
}

THRESHOLD_LABELS = {
    "floors": ("Số tầng nổi", "tầng"),
    "totalFloorArea": ("Tổng diện tích sàn", "m²"),
    "height": ("Chiều cao PCCC", "m"),
}

# Giá trị chuẩn của dropdown "Loại & công năng công trình" (Sidebar.tsx) — khớp
# TUYỆT ĐỐI (không quét từ khoá) để mọi lựa chọn có sẵn trên giao diện đều
# được phân loại có chủ đích, không rơi vào "chưa xác định".
_EXACT_TYPE_MAP = {
    "nhà ở riêng lẻ kết hợp kinh doanh": "mixed_residential",
    "nhà ở riêng lẻ": "private_house",
    "cơ sở kinh doanh karaoke, vũ trường": "karaoke_entertainment",
    "gara ô tô": "garage",
    "văn phòng, khách sạn công cộng": "office_hotel",
    "nhà kho xếp giá đỡ kệ cao": "warehouse",
    "chợ, trung tâm thương mại": "market_mall",
    "nhà máy, nhà xưởng sản xuất": "factory",
    "cơ sở giáo dục, trường học": "school",
    "rạp hát, hội trường, trung tâm tổ chức sự kiện": "assembly",
}

# Thứ tự có ý nghĩa: nhóm nguy cơ cao kiểm tra trước. Dùng regex (\b) để tránh
# khớp nhầm chuỗi con (vd "kho" trong "khoảng", "chợ" trong từ khác).
_KEYWORD_PATTERNS: List[Tuple[str, Tuple[str, ...]]] = [
    ("karaoke_entertainment", (r"karaoke", r"vũ trường", r"vu truong", r"quán bar", r"\bbar\b", r"\bpub\b", r"\bdisco(theque)?\b")),
    ("school", (r"trường học", r"mầm non", r"tiểu học", r"trung học", r"\bschool\b", r"nhà trẻ", r"cơ sở giáo dục", r"đại học", r"cao đẳng")),
    ("assembly", (r"rạp hát", r"rạp chiếu", r"hội trường", r"sự kiện", r"nhà hát", r"cinema")),
    ("market_mall", (r"\bchợ\b", r"trung tâm thương mại", r"siêu thị", r"\bttmm\b", r"\bmarket\b", r"shopping", r"\bmall\b")),
    ("warehouse", (r"nhà kho", r"kho chứa", r"kho hàng", r"kho lạnh", r"giá kệ", r"kệ cao", r"warehouse", r"\bkho\b")),
    ("factory", (r"nhà máy", r"nhà xưởng", r"xưởng sản xuất", r"factory", r"xí nghiệp")),
    ("garage", (r"\bgara\b", r"\bga ra\b", r"garage", r"bãi đỗ xe", r"nhà để xe")),
    ("office_hotel", (r"văn phòng", r"công sở", r"khách sạn", r"nhà nghỉ", r"\bhotel\b", r"\bmotel\b", r"nhà khách")),
    ("mixed_residential", (r"nhà hỗn hợp", r"kết hợp kinh doanh", r"chung cư", r"nhà phố", r"shophouse")),
    ("private_house", (r"nhà ở riêng lẻ", r"nhà ở dân dụng", r"nhà dân", r"biệt thự", r"nhà ở")),
]

# Từ chỉ vị trí/phủ định: phần văn bản đứng SAU chúng KHÔNG mô tả công năng của
# chính công trình ("tạp hoá đối diện trường học", "gần chợ", "không có kho").
_PROXIMITY = re.compile(
    r"\b(gần|cạnh|đối diện|sát|kế bên|bên cạnh|lân cận|phía trước|phía sau|không phải|không có|không|chưa)\b"
)
_KARAOKE_REGEX = re.compile("|".join(dict(_KEYWORD_PATTERNS)["karaoke_entertainment"]))


def _strip_proximity(text: str) -> str:
    """Giữ phần mô tả công trình, bỏ phần mô tả vùng lân cận / phủ định trong từng mệnh đề."""
    kept: List[str] = []
    for clause in re.split(r"[;\n.]+", text.lower()):
        match = _PROXIMITY.search(clause)
        kept.append(clause[: match.start()] if match else clause)
    return " ; ".join(kept)


def _match_category(text: str) -> Optional[str]:
    for category, patterns in _KEYWORD_PATTERNS:
        if any(re.search(p, text) for p in patterns):
            return category
    return None


def classify_building(project: Dict[str, Any]) -> Tuple[str, str]:
    """Trả về (nhóm công năng, bằng chứng phân loại bằng tiếng Việt).

    Quy tắc (theo thứ tự ưu tiên):
      1. Nhóm karaoke/vũ trường là NÂNG CẤP AN TOÀN (fail-safe): chỉ cần xuất
         hiện ở loại công trình, ở "Chi tiết kinh doanh" HOẶC ở công năng của
         một tầng bất kỳ là xếp vào nhóm này. Thà yêu cầu thẩm duyệt dư còn
         hơn bỏ sót cơ sở nguy cơ cháy cao. Không áp dụng lọc "gần/đối diện"
         cho nhóm này, vì nhầm theo hướng bắt buộc an toàn hơn nhầm theo hướng bỏ sót.
      2. Giá trị chọn trong dropdown -> khớp tuyệt đối.
      3. Loại công trình nhập tự do (OCR/AI/chat) -> quét từ khoá.
      4. Nếu vẫn chưa xác định -> thử "Chi tiết kinh doanh" (đã lọc phần lân cận/phủ định).
      Chi tiết kinh doanh KHÔNG được dùng để đổi nhóm khi loại công trình đã xác
      định (nhà ở có "siêu thị mini" ở tầng trệt vẫn là nhà ở, không phải trung tâm thương mại).
    """
    ptype = unicodedata.normalize("NFC", str(project.get("type") or "")).strip()
    details = str(project.get("commercialDetails") or "").strip()
    floors = int(to_number(project.get("floors")))
    raw_floor_funcs = project.get("floorFunctions") or []
    floor_funcs = [str(x or "") for x in raw_floor_funcs if isinstance(x, (str, int, float))]
    considered = floor_funcs[:floors] if floors > 0 else floor_funcs

    # (1) nâng cấp an toàn cho karaoke
    if _KARAOKE_REGEX.search(_strip_proximity(ptype.lower())):
        return "karaoke_entertainment", f"Loại công trình đã khai báo: “{ptype}”."
    if details and _KARAOKE_REGEX.search(_strip_proximity(details.lower())):
        return "karaoke_entertainment", "Phát hiện công năng karaoke/vũ trường/bar trong mục “Chi tiết kinh doanh”."
    karaoke_floors = [i + 1 for i, fn in enumerate(considered) if _KARAOKE_REGEX.search(_strip_proximity(fn.lower()))]
    if karaoke_floors:
        listed = ", ".join(str(n) for n in karaoke_floors)
        return "karaoke_entertainment", f"Phát hiện công năng karaoke/bar tại tầng {listed} (mục “Công năng từng tầng”)."

    # (2) khớp tuyệt đối dropdown
    exact = _EXACT_TYPE_MAP.get(ptype.lower())
    if exact:
        return exact, f"Loại công trình đã chọn: “{ptype}”."

    # (3) quét từ khoá trên loại công trình nhập tự do
    if ptype:
        category = _match_category(_strip_proximity(ptype))
        if category:
            return category, f"Nhận diện từ loại công trình: “{ptype}”."

    # (4) chỉ khi loại công trình chưa xác định mới tham khảo chi tiết kinh doanh
    if details:
        category = _match_category(_strip_proximity(details))
        if category:
            return category, "Nhận diện từ mục “Chi tiết kinh doanh” (loại công trình chưa xác định)."

    if ptype:
        return "unclassified", f"Loại công trình “{ptype}” chưa khớp nhóm nào trong hệ thống."
    return "unclassified", "Chưa khai báo loại công trình."


# --------------------------------------------------------------------------
# 3. Căn cứ pháp lý có cấu trúc
# --------------------------------------------------------------------------

_MISSING_LABELS = {
    "floors": "số tầng nổi",
    "totalFloorArea": "tổng diện tích sàn",
    "height": "chiều cao PCCC",
    "type": "loại công trình / công năng",
}

STATUS_REQUIRED = "required"
STATUS_NOT_REQUIRED = "not_required"
STATUS_INSUFFICIENT = "insufficient_data"

def category_warning(category: str) -> Optional[str]:
    return None  # Current basis carries the manual-review explanation.


def _build_threshold_rows(info: Dict[str, Any], values: Dict[str, float]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key, op, limit in info["thresholds"]:
        label, unit = THRESHOLD_LABELS[key]
        actual = values[key]
        if actual <= 0:
            state, actual_text, actual_val = "missing", "Chưa nhập", None
        else:
            met = actual >= limit
            state = "met" if met else "not_met"
            actual_text, actual_val = f"{fmt_number(actual)} {unit}", actual
        rows.append(
            {
                "key": key,
                "label": label,
                "operator": op,
                "limit": limit,
                "unit": unit,
                "limitText": f"≥ {fmt_number(limit)} {unit}",
                "actual": actual_val,
                "actualText": actual_text,
                "state": state,
            }
        )
    return rows


def _row_phrase(row: Dict[str, Any]) -> str:
    sign = "≥" if row["state"] == "met" else "<"
    name = row["label"].lower().replace("pccc", "PCCC")
    return f"{name} {row['actualText']} {sign} {fmt_number(row['limit'])} {row['unit']}"


RULES_VERSION = "v11.3-347-2026-annexIII"
SOURCE_URL = "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/9/347_2026_nd-cp_08092026_11-signed.pdf"
THRESHOLD_LABELS["volume"] = ("Khối tích", "m³")
_MISSING_LABELS["volume"] = "khối tích"


def build_appraisal_basis(project: Dict[str, Any]) -> Dict[str, Any]:
    """Verified Annex III replaced by ND347/2026 effective 15 September 2026.
    Scale screening only. Unknown subtype, hazard or scope never gets a fallback.
    """
    category, evidence = classify_building(project)
    label = CATEGORY_INFO[category]["label"]
    ptype = unicodedata.normalize("NFC", str(project.get("type") or "")).strip().lower()
    grade = str(project.get("hazardClass") or "")
    subtype = project.get("industrialSubtype") or ""
    limits, clause, needed = (), "", []
    if category == "factory":
        if subtype != "other":
            needed = ["industrialSpecialRule"] if subtype == "special" else ["industrialSubtype"] + (["hazardClass"] if not grade else [])
        elif grade not in {"A", "B", "C", "D", "E"}:
            needed = ["hazardClass"]
        else:
            volume, area = (7000, 1000) if grade in {"A", "B"} else (15000, 2000) if grade == "C" else (30000, 10000)
            limits, clause = (("volume", ">=", volume), ("totalFloorArea", ">=", area)), "mục 9 điểm d"
    elif category == "warehouse":
        if grade in {"A", "B", "C"}:
            limits, clause = (("volume", ">=", 15000), ("totalFloorArea", ">=", 2000)), "mục 10"
        else:
            needed = ["hazardClass"] if not grade else ["warehouseScope"]
    elif category == "karaoke_entertainment" and re.search(r"karaoke|vũ trường|vu truong", ptype):
        limits, clause = (("floors", ">=", 4), ("totalFloorArea", ">=", 1000)), "mục 5"
    elif category == "mixed_residential" and ptype in {"nhà hỗn hợp", "công trình hỗn hợp", "công trình đa năng"}:
        limits, clause = GENERAL_THRESHOLDS, "mục 8"
    elif category == "mixed_residential" and ptype in {"nhà chung cư", "chung cư", "nhà tập thể", "nhà ở tập thể"}:
        limits, clause = GENERAL_THRESHOLDS, "mục 1"
    elif category == "office_hotel":
        limits, clause = GENERAL_THRESHOLDS, "mục 7"
    elif category == "garage" and "kín" in ptype:
        limits, clause = (("totalFloorArea", ">=", 2000),), "mục 12"
    elif category == "market_mall" and re.search(r"chợ|trung tâm thương mại|siêu thị", ptype):
        limits, clause = (("totalFloorArea", ">=", 2000),), "mục 6"
    values = {k: to_number(project.get(k)) for k in ("floors", "totalFloorArea", "volume")}
    values["height"] = effective_height(project)
    thresholds = _build_threshold_rows({"thresholds": limits}, values)
    met = [row for row in thresholds if row["state"] == "met"]
    missing = [row["key"] for row in thresholds if row["state"] == "missing"]
    source = "statutory" if clause else "manual_review"
    display_missing = {"industrialSubtype": "phân loại sản xuất công nghiệp khác hay chuyên ngành", "hazardClass": "hạng nguy hiểm cháy/nổ", "mixedUseParts": "quy mô và công năng các phần của nhà hỗn hợp", "industrialSpecialRule": "quy định áp dụng cho loại công nghiệp chuyên ngành đã khai báo", "warehouseScope": "phạm vi quy định áp dụng cho kho hạng D/E"}
    legal = (f"Sàng lọc quy mô theo {clause}, Phụ lục III kèm Nghị định 347/2026/NĐ-CP thay thế Phụ lục III của Nghị định 105/2025/NĐ-CP, hiệu lực 15/9/2026. "
             "Phải xác nhận loại dự án, giai đoạn, điều kiện áp dụng và thẩm quyền theo Điều 6, Điều 9 đã sửa đổi; không phải chứng nhận tuân thủ.") if clause else "Chưa áp dụng ngưỡng pháp định cho phân loại này; không dùng ngưỡng nhà hỗn hợp để thay thế."
    if not clause:
        status = STATUS_INSUFFICIENT
        missing = needed or ["type"]
        summary = f"Không tìm thấy quy định phù hợp đã xác minh và đủ điều kiện áp dụng cho nhóm {label}. Cần bổ sung hoặc xác nhận: {', '.join(display_missing.get(k, k) for k in missing)}; rà soát thủ công, chưa kết luận thuộc hoặc không thuộc diện thẩm định."
    else:
        status = STATUS_REQUIRED if met else STATUS_INSUFFICIENT if missing else STATUS_NOT_REQUIRED
        if category == "mixed_residential" and clause == "mục 8" and not met:
            status = STATUS_INSUFFICIENT
            missing.append("mixedUseParts")
        if status == STATUS_REQUIRED:
            summary = f"THUỘC NGƯỠNG DANH MỤC thẩm định: {'; '.join(_row_phrase(row) for row in met)}."
        elif status == STATUS_NOT_REQUIRED:
            summary = f"CHƯA ĐẠT NGƯỠNG tại {clause}: {'; '.join(_row_phrase(row) for row in thresholds)}. Không phải miễn mọi thủ tục PCCC."
        else:
            summary = f"CHƯA ĐỦ THÔNG SỐ để kết luận: {', '.join(_MISSING_LABELS.get(k, display_missing.get(k, k)) for k in missing)}."
    return {"minFireRatingText": "Chưa đủ căn cứ xác định bậc chịu lửa tối thiểu",
        "status": status, "category": category, "categoryLabel": label, "categoryEvidence": evidence,
        "ruleMode": "threshold" if clause else "manual_review", "thresholdSource": source,
        "legalText": legal, "thresholds": thresholds, "triggeredBy": [r["key"] for r in met],
        "missingFields": missing, "summary": summary, "conclusion": summary + " " + legal,
        "actualScale": f"{fmt_number(values['floors'])} tầng nổi, {fmt_number(values['totalFloorArea'])} m² sàn, {fmt_number(values['volume'])} m³ khối tích; hạng {grade or 'chưa xác định'}",
        "rulesVersion": RULES_VERSION, "sourceUrl": SOURCE_URL if clause else ""}
