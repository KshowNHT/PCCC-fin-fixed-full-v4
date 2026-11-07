"""Deterministic scale screening and explicit unknown technical criteria.
Current verified source: replacement Annex III, ND347/2026.
Each building is evaluated independently; output is not compliance certification.
"""
from typing import Any, Dict, List, Optional

from app.appraisal_basis import (
    STATUS_INSUFFICIENT,
    STATUS_NOT_REQUIRED,
    STATUS_REQUIRED,
    build_appraisal_basis,
    category_warning,
    effective_height,
    fmt_number,
    to_number,
)
from app.checklist_data import STANDARDS_CHECKLIST_TEMPLATE

AREA_MISMATCH_WARNING = (
    "Tổng diện tích sàn khai báo không trùng khớp với tích số giữa (diện tích sàn x số tầng), "
    "cần đối chiếu kiểm tra thực tế."
)
REQUIRED_SIGNATURE_WARNING = (
    "Hồ sơ thuộc diện bắt buộc thẩm duyệt: bản thiết kế PCCC cần có chữ ký của tư vấn thiết kế được cấp "
    "chứng chỉ hành nghề."
)
# Các cảnh báo do rules_engine tự sinh (dùng để làm mới/loại trùng khi đọc lại hồ sơ cũ).
DETERMINISTIC_WARNING_PREFIXES = (
    "Thiết kế quy mô lớn bậc chịu lửa",
    "Tổng diện tích sàn khai báo không trùng khớp",
    "Nhóm nhà kho:",
    "Hệ thống CHƯA nhận diện được nhóm công năng",
    "Hệ thống CHƯA có ngưỡng thẩm duyệt riêng",
    "Hồ sơ thuộc diện bắt buộc thẩm duyệt",
)

_KNOWN_RATINGS = ("Bậc I", "Bậc II", "Bậc III", "Bậc IV", "Bậc V")


def _need_data(fields: List[str]) -> tuple:
    return "Cần xem xét", f"Chưa đủ thông số ({', '.join(fields)}) để rà soát mục này — vui lòng bổ sung rồi kiểm duyệt lại."


def _compute_fire_rating_rule(eff_h: float, floors: int, basements: int, volume: float, category: str) -> tuple:
    """Xác định bậc chịu lửa tối thiểu theo Phụ lục H QCVN 06:2022/BXD dựa trên chiều cao PCCC, số tầng, khối tích."""
    if eff_h > 50 or floors > 16 or basements >= 2:
        return ("Bậc I",), "Tối thiểu đạt Bậc I (cao PCCC > 50m, > 16 tầng hoặc >= 2 tầng hầm theo Phụ lục H QCVN 06:2022/BXD)"
    if eff_h > 15 or floors >= 5 or volume >= 5000 or basements >= 1 or category == "karaoke_entertainment":
        return ("Bậc I", "Bậc II"), "Tối thiểu đạt Bậc II (cao PCCC > 15m, >= 5 tầng hoặc khối tích >= 5.000 m³ theo Phụ lục H QCVN 06:2022/BXD)"
    if eff_h > 9 or floors >= 3 or volume >= 1500:
        return ("Bậc I", "Bậc II", "Bậc III"), "Tối thiểu đạt Bậc III (cao PCCC <= 15m, 3–4 tầng, khối tích < 5.000 m³ theo Phụ lục H QCVN 06:2022/BXD)"
    return ("Bậc I", "Bậc II", "Bậc III", "Bậc IV"), "Cho phép đến Bậc IV (nhà thấp tầng <= 2 tầng, cao PCCC <= 9m, khối tích < 1.500 m³ theo QCVN 06:2022/BXD)"


def _evaluate_technical_item(
    stt: int,
    template: Dict[str, Any],
    *,
    floors: int,
    basements: int,
    floor_area: float,
    est_area: float,
    eff_h: float,
    volume: float,
    fire_rating: str,
    category: str,
    status: str,
    allowed_ratings: tuple,
    min_rating_text: str,
) -> Dict[str, Any]:
    """Chấm điểm tự động 16 hạng mục kỹ thuật QCVN 06:2022/BXD & QCVN 10:2025/BCA (stt 2..17)
    theo chiều cao PCCC (eff_h), số tầng (floors) và khối tích công trình (volume).
    """
    req_auto_alarm = (
        floors >= 7
        or eff_h >= 25
        or est_area >= 3000
        or volume >= 5000
        or category == "karaoke_entertainment"
        or (category in ("market_mall", "office_hotel", "warehouse", "factory", "garage", "hospital_medical", "fuel_energy", "school", "assembly") and (est_area >= 1000 or volume >= 3000))
    )
    req_indoor_hydrant = (
        volume >= 5000
        or eff_h > 12
        or floors >= 5
        or category == "karaoke_entertainment"
        or (category in ("warehouse", "factory", "market_mall", "garage", "hospital_medical", "fuel_energy", "assembly") and (volume >= 2500 or est_area >= 1000))
    )
    req_sprinkler = (
        eff_h >= 25
        or floors >= 10
        or volume >= 15000
        or category == "karaoke_entertainment"
        or (basements >= 1 and est_area >= 1000)
        or (category in ("warehouse", "factory", "market_mall", "garage", "hospital_medical", "fuel_energy", "assembly") and (est_area >= 2000 or volume >= 10000))
    )

    floors_label = f"{floors} tầng" if floors > 0 else "chưa khai báo số tầng"
    result = "Cần xem xét"
    note = ""

    if stt == 2:
        if fire_rating in _KNOWN_RATINGS:
            if fire_rating in allowed_ratings:
                result = "Đạt"
                note = (
                    f"Bậc chịu lửa khai báo ({fire_rating}) đáp ứng yêu cầu ({min_rating_text}) cho quy mô "
                    f"{floors_label}, chiều cao PCCC {fmt_number(eff_h)}m, khối tích {fmt_number(volume)} m³."
                )
            else:
                result = "Không đạt"
                note = (
                    f"Không đạt bậc chịu lửa: Quy mô {floors_label}, cao PCCC {fmt_number(eff_h)}m, khối tích "
                    f"{fmt_number(volume)} m³ yêu cầu {min_rating_text}, nhưng đang khai báo {fire_rating}."
                )
        else:
            if eff_h > 15 or floors >= 5 or volume >= 5000 or category == "karaoke_entertainment":
                result = "Không đạt"
                note = (
                    f"Chưa khai báo bậc chịu lửa cho công trình quy mô lớn ({floors_label}, cao PCCC {fmt_number(eff_h)}m, "
                    f"khối tích {fmt_number(volume)} m³) — bắt buộc thiết kế {min_rating_text}."
                )
            else:
                result = "Đạt"
                note = (
                    f"Quy mô {floors_label}, cao PCCC {fmt_number(eff_h)}m, khối tích {fmt_number(volume)} m³: "
                    f"{min_rating_text}. Cần ghi rõ bậc chịu lửa trên bản vẽ thuyết minh."
                )

    elif stt == 3:
        result = "Cần đo đạc"
        if eff_h > 28 or volume >= 10000 or fire_rating in ("Bậc IV", "Bậc V"):
            note = (
                f"Công trình cao PCCC {fmt_number(eff_h)}m, khối tích {fmt_number(volume)} m³ ({fire_rating or 'chưa chọn bậc'}): "
                "bắt buộc đo đạc khoảng cách phòng cháy chống cháy >= 8m–10m và bố trí bãi đỗ xe thang chữa cháy theo Phụ lục E QCVN 06:2022/BXD."
            )
        else:
            note = (
                f"Đo đạc thực tế khoảng cách PCCC đến nhà lân cận (>= 6m với Bậc I/II, >= 8m với Bậc III) hoặc kiểm tra "
                f"tường ngăn cháy đặc REI 45 phía tiếp giáp cho công trình cao {fmt_number(eff_h)}m."
            )

    elif stt == 4:
        if category == "private_house" and floors <= 3 and volume < 1500:
            result = "Không bắt buộc"
            note = "Nhà ở riêng lẻ thuần túy không bố trí khu kinh doanh thương mại nên không bắt buộc tường ngăn cháy phân chia công năng."
        else:
            result = "Khuyến nghị mạnh"
            note = (
                f"Công trình {floors_label} (cao PCCC {fmt_number(eff_h)}m, khối tích {fmt_number(volume)} m³) cần ngăn cách khu vực "
                "kinh doanh/kho với khu vực ở và buồng thang bằng tường ngăn cháy EI 45, sàn REI 45 và cửa chống cháy EI 30 tự đóng."
            )

    elif stt == 5:
        if eff_h > 28 or floors >= 10:
            result = "Không đạt"
            note = (
                f"Chiều cao PCCC {fmt_number(eff_h)}m (> 28m, {floors_label}) bắt buộc thiết kế buồng thang bộ không nhiễm khói "
                "loại N1 (hoặc N2/N3 có tăng áp), tối thiểu 02 thang thoát nạn, bản thang rộng >= 1,20m theo QCVN 06:2022/BXD."
            )
        elif eff_h > 9 or floors >= 4 or category == "karaoke_entertainment":
            result = "Cần đo đạc"
            note = (
                f"Chiều cao PCCC {fmt_number(eff_h)}m (> 9m, {floors_label}) bắt buộc bố trí buồng thang bộ kín loại L1/L2 "
                "(không dùng thang bộ hở thông tầng), bề rộng thông thủy bản thang >= 1,05m (công cộng/karaoke >= 1,20m)."
            )
        else:
            result = "Đạt"
            note = (
                f"Chiều cao PCCC {fmt_number(eff_h)}m (<= 9m, {floors_label}) được phép bố trí cầu thang bộ thoát nạn trong nhà "
                "(loại 2) với bề rộng thông thủy bản thang >= 0,90m–1,05m theo QCVN 06:2022/BXD."
            )

    elif stt == 6:
        if floors >= 7 or eff_h > 21 or floor_area > 300 or volume >= 5000 or category == "karaoke_entertainment":
            result = "Khuyến nghị mạnh"
            note = (
                f"Quy mô {floors_label}, cao PCCC {fmt_number(eff_h)}m, khối tích {fmt_number(volume)} m³ bắt buộc tối thiểu "
                "02 lối ra thoát nạn độc lập mỗi tầng; cửa thoát nạn tầng 1 mở ra ngoài rộng thông thủy >= 0,90m–1,20m."
            )
        else:
            result = "Đạt"
            note = (
                f"Quy mô {floors_label}, cao PCCC {fmt_number(eff_h)}m, khối tích {fmt_number(volume)} m³ đáp ứng điều kiện bố trí "
                "lối thoát nạn trực tiếp ra ngoài tại tầng 1 với cửa mở xuôi chiều thoát nạn rộng >= 0,90m."
            )

    elif stt == 7:
        if category == "private_house" and floors <= 3 and eff_h <= 9:
            result = "Khuyến nghị"
            note = "Nhà ở riêng lẻ thấp tầng (<= 3 tầng, cao <= 9m) khuyến khích lắp đèn chiếu sáng sự cố tự nạp điện tại cầu thang."
        else:
            result = "Khuyến nghị mạnh"
            note = (
                f"Bắt buộc lắp đặt đèn chiếu sáng sự cố (>= 1 lux) và đèn chỉ dẫn thoát nạn EXIT (pin dự phòng >= 2 giờ) "
                f"dọc hành lang, chiếu nghỉ thang bộ và cửa ra tầng 1 cho công trình {floors_label} (cao {fmt_number(eff_h)}m)."
            )

    elif stt == 8:
        min_bins = max(max(floors, 1) * 2, int(round(est_area / 75)) if est_area > 0 else 2)
        if volume >= 5000 or floors >= 7 or category in ("karaoke_entertainment", "warehouse", "factory", "fuel_energy", "hospital_medical"):
            result = "Khuyến nghị mạnh"
            note = (
                f"Khối tích {fmt_number(volume)} m³ ({floors_label}, {fmt_number(est_area)} m² sàn) yêu cầu trang bị tối thiểu "
                f"{min_bins} bình chữa cháy xách tay (bột ABC >= 4kg và khí CO2 >= 3kg), khoảng cách di chuyển <= 20m."
            )
        else:
            result = "Đạt"
            note = (
                f"Định mức trang bị tối thiểu {min_bins} bình chữa cháy xách tay (bột ABC >= 4kg hoặc CO2 >= 3kg, tối thiểu "
                f"2 bình/tầng, bán kính bảo vệ <= 25m) phù hợp quy mô {floors_label} ({fmt_number(est_area)} m² sàn)."
            )

    elif stt == 9:
        if req_auto_alarm:
            result = "Không đạt"
            note = (
                f"Công trình ({floors_label}, cao PCCC {fmt_number(eff_h)}m, sàn {fmt_number(est_area)} m², khối tích "
                f"{fmt_number(volume)} m³) thuộc diện bắt buộc thiết kế hệ thống báo cháy tự động trung tâm theo Phụ lục A QCVN 10:2025/BCA."
            )
        else:
            result = "Không bắt buộc"
            note = (
                f"Quy mô {floors_label} (< 7 tầng), cao PCCC {fmt_number(eff_h)}m (< 25m), khối tích {fmt_number(volume)} m³ "
                "(< 5.000 m³) không bắt buộc trang bị hệ thống báo cháy tự động trung tâm."
            )

    elif stt == 10:
        if req_auto_alarm:
            result = "Không bắt buộc"
            note = "Công trình đã thuộc diện bắt buộc trang bị hệ thống báo cháy tự động trung tâm (mục 9) nên không dùng đầu báo độc lập đơn lẻ thay thế."
        elif floors >= 5 or eff_h > 15 or volume >= 3000:
            result = "Khuyến nghị mạnh"
            note = (
                f"Công trình {floors_label} (cao PCCC {fmt_number(eff_h)}m, khối tích {fmt_number(volume)} m³) cần lắp đặt "
                "hệ thống cảm biến khói/nhiệt độc lập có liên động âm thanh còi báo động toàn nhà."
            )
        else:
            result = "Đạt"
            note = (
                f"Quy mô {floors_label} (cao PCCC {fmt_number(eff_h)}m, khối tích {fmt_number(volume)} m³) phù hợp phương án "
                "lắp đặt đầu báo khói độc lập liên động tại từng tầng và khu kinh doanh theo Điều 2.1 QCVN 10:2025/BCA."
            )

    elif stt == 11:
        if req_indoor_hydrant:
            result = "Không đạt"
            note = (
                f"Chiều cao PCCC {fmt_number(eff_h)}m (> 12m), {floors_label}, hoặc khối tích {fmt_number(volume)} m³ "
                "(>= 5.000 m³) bắt buộc trang bị hệ thống họng nước chữa cháy trong nhà (lưu lượng >= 2,5 L/s, họng DN50/DN65) theo QCVN 10:2025/BCA."
            )
        else:
            result = "Đạt"
            note = (
                f"Chiều cao PCCC {fmt_number(eff_h)}m (<= 12m), {floors_label} (< 5 tầng), khối tích {fmt_number(volume)} m³ "
                "(< 5.000 m³) nằm dưới ngưỡng bắt buộc lắp đặt hệ thống họng nước chữa cháy trong nhà."
            )

    elif stt == 12:
        if req_sprinkler:
            result = "Không đạt"
            note = (
                f"Công trình (cao PCCC {fmt_number(eff_h)}m, {floors_label}, khối tích {fmt_number(volume)} m³) thuộc diện "
                "bắt buộc trang bị hệ thống chữa cháy tự động Sprinkler theo Bảng A.1 QCVN 10:2025/BCA."
            )
        else:
            result = "Không bắt buộc"
            note = (
                f"Chiều cao PCCC {fmt_number(eff_h)}m (< 25m) và khối tích {fmt_number(volume)} m³ (< 15.000 m³) "
                "chưa thuộc diện bắt buộc lắp đặt hệ thống chữa cháy tự động Sprinkler."
            )

    elif stt == 13:
        if volume >= 5000 or eff_h > 15 or floors >= 7:
            flow_ls = 20 if (volume >= 15000 or eff_h >= 28) else 15
            tank_m3 = int(flow_ls * 3.6 * 2)
            result = "Cần xem xét"
            note = (
                f"Khối tích {fmt_number(volume)} m³ (cao PCCC {fmt_number(eff_h)}m) yêu cầu lưu lượng nước chữa cháy ngoài nhà "
                f">= {flow_ls} L/s; phải có trụ nước đô thị trong bán kính <= 150m hoặc bể nước chữa cháy dự trữ >= {tank_m3} m³."
            )
        else:
            result = "Khuyến nghị"
            note = (
                f"Khối tích {fmt_number(volume)} m³ (< 5.000 m³) yêu cầu lưu lượng cấp nước chữa cháy ngoài nhà 10 L/s; "
                "đảm bảo khoảng cách đến trụ nước chữa cháy đô thị <= 150m hoặc trang bị bể dự trữ >= 18 m³."
            )

    elif stt == 14:
        if category == "private_house" and floors <= 6 and est_area < 3000:
            result = "Không bắt buộc"
            note = "Nhà ở riêng lẻ thuần túy không thuộc danh mục cơ sở phải lập hồ sơ khai báo cơ sở dữ liệu PCCC quốc gia."
        else:
            result = "Khuyến nghị"
            note = "Cơ sở kinh doanh / hỗn hợp thuộc danh mục quản lý theo Nghị định 105/2025/NĐ-CP cần lập hồ sơ và khai báo dữ liệu PCCC quốc gia."

    elif stt == 15:
        if status == STATUS_REQUIRED or req_auto_alarm:
            result = "Khuyến nghị mạnh"
            note = (
                f"Công trình ({floors_label}, cao PCCC {fmt_number(eff_h)}m, khối tích {fmt_number(volume)} m³) thuộc diện "
                "phải lắp đặt thiết bị truyền tin báo cháy sự cố kết nối hệ thống cơ sở dữ liệu PCCC theo Nghị định 105/2025/NĐ-CP."
            )
        else:
            result = "Không bắt buộc"
            note = "Công trình quy mô nhỏ dưới ngưỡng thẩm định và báo cháy tự động chưa bắt buộc lắp đặt thiết bị truyền tin báo cháy sự cố."

    elif stt == 16:
        if (
            status == STATUS_REQUIRED
            or floors >= 5
            or est_area >= 1500
            or volume >= 5000
            or category in ("karaoke_entertainment", "warehouse", "factory", "market_mall", "office_hotel", "garage", "hospital_medical", "fuel_energy", "school", "assembly")
        ):
            result = "Khuyến nghị mạnh"
            note = "Cơ sở có nguy hiểm về cháy, nổ thuộc danh mục phải mua bảo hiểm cháy, nổ bắt buộc đối với tài sản khi đưa vào vận hành."
        else:
            result = "Đạt"
            note = "Cơ sở quy mô nhỏ ngoài danh mục bắt buộc mua bảo hiểm cháy, nổ; khuyến khích chủ sở hữu tham gia tự nguyện."

    elif stt == 17:
        result = "Đạt"
        note = (
            "Chủ cơ sở / chủ đầu tư duy trì chế độ tự kiểm tra an toàn PCCC định kỳ tối thiểu 1 tháng/lần đối với "
            "hệ thống điện, lối thoát nạn, đèn EXIT và bình chữa cháy theo Nghị định 105/2025/NĐ-CP."
        )

    return {
        "stt": stt,
        "category": template.get("category") or template["criteria"],
        "criteria": template["criteria"],
        "result": result,
        "requirement": template["requirement"],
        "note": note,
        "reference": template["reference"],
    }


def evaluate_appraisal(project: Dict[str, Any]) -> Dict[str, Any]:
    if project.get("components"):
        return evaluate_components(project)
    basis = build_appraisal_basis(project)
    status = basis["status"]
    category = basis["category"]

    floor_area, floors_val, total, raw_volume, basements_val = (
        to_number(project.get(k)) for k in ("floorArea", "floors", "totalFloorArea", "volume", "basements")
    )
    floors = int(floors_val)
    basements = int(basements_val)
    h = effective_height(project)
    eff_h = h if h > 0 else (floors * 3.6 if floors > 0 else 0.0)
    est_area = total if total > 0 else (floor_area * floors if floor_area > 0 and floors > 0 else 0.0)
    avg_story_h = (
        max(3.6, eff_h / floors)
        if (floors > 0 and eff_h > 0)
        else (max(3.6, eff_h) if eff_h > 0 else 3.6)
    )
    volume = (
        raw_volume
        if raw_volume > 0
        else (est_area * avg_story_h if est_area > 0 else (floor_area * eff_h if floor_area > 0 and eff_h > 0 else 0.0))
    )
    fire_rating = str(project.get("fireRating") or "").strip()

    has_tech_inputs = (
        h > 0
        or raw_volume > 0
        or status in (STATUS_REQUIRED, STATUS_NOT_REQUIRED)
    )

    allowed_ratings, min_rating_text = _compute_fire_rating_rule(eff_h, floors, basements, volume, category)
    if has_tech_inputs:
        basis["minFireRatingText"] = min_rating_text

    checklist = []
    for t in STANDARDS_CHECKLIST_TEMPLATE:
        if t["stt"] == 1:
            checklist.append({
                "stt": 1,
                "category": t.get("category") or t["criteria"],
                "criteria": t["criteria"],
                "result": (
                    "Thuộc diện thẩm định"
                    if status == STATUS_REQUIRED
                    else "Dưới ngưỡng danh mục"
                    if status == STATUS_NOT_REQUIRED
                    else "Cần xem xét"
                ),
                "requirement": "Xác nhận phân loại, quy mô, thẩm quyền.",
                "note": basis["summary"],
                "reference": (
                    "Nghị định 347/2026/NĐ-CP, Phụ lục III thay thế; Điều 6, Điều 9 Nghị định 105/2025 đã sửa đổi"
                    if basis["thresholdSource"] == "statutory"
                    else "Chưa tìm thấy quy định phù hợp trong bộ quy tắc đã xác minh"
                ),
            })
        elif has_tech_inputs:
            checklist.append(
                _evaluate_technical_item(
                    t["stt"],
                    t,
                    floors=floors,
                    basements=basements,
                    floor_area=floor_area,
                    est_area=est_area,
                    eff_h=eff_h,
                    volume=volume,
                    fire_rating=fire_rating,
                    category=category,
                    status=status,
                    allowed_ratings=allowed_ratings,
                    min_rating_text=min_rating_text,
                )
            )
        else:
            checklist.append({
                "stt": t["stt"],
                "category": t.get("category") or t["criteria"],
                "criteria": t["criteria"],
                "result": "Cần xem xét",
                "requirement": "Xác định điều kiện áp dụng và kiểm tra hồ sơ, bản vẽ hoặc bằng chứng thực tế.",
                "note": (
                    f"Không tìm thấy quy định phù hợp cho {t['criteria'].lower()} trong bộ quy tắc đã xác minh của chương trình. "
                    "Không đủ căn cứ chấm đạt/không đạt; cần kỹ sư bổ sung quy định áp dụng và bằng chứng thực tế."
                ),
                "reference": "Chưa tìm thấy quy định phù hợp trong bộ quy tắc đã xác minh",
            })

    warnings = ["Kết quả là sàng lọc sơ bộ; không phải chứng nhận tuân thủ, văn bản thẩm định hoặc nghiệm thu PCCC."]
    if not has_tech_inputs:
        warnings.append(
            "Không tìm thấy quy định phù hợp đã được mã hóa và xác minh cho các hạng mục kỹ thuật còn lại. "
            "Không suy diễn kết luận từ ngưỡng quy mô; không có nghĩa pháp luật không quy định các hạng mục này."
        )
    else:
        failed_items = [c["criteria"] for c in checklist[1:] if c["result"] == "Không đạt"]
        if failed_items:
            warnings.append(
                f"Phát hiện {len(failed_items)} hạng mục kỹ thuật QCVN 06:2022/BXD & QCVN 10:2025 chưa đạt hoặc bắt buộc phải bổ sung thiết kế: "
                + ", ".join(failed_items)
                + "."
            )
    if status == STATUS_REQUIRED:
        warnings.append(REQUIRED_SIGNATURE_WARNING)
    if status == STATUS_INSUFFICIENT:
        warnings.append(basis["summary"])
    if floor_area > 0 and floors > 0 and total > 0 and abs(total - floor_area * floors) > 10:
        warnings.append(AREA_MISMATCH_WARNING + " Đây là cảnh báo đối chiếu; công trình có tầng giật cấp có thể có chênh lệch hợp lệ.")
    return {
        "warnings": warnings,
        "checklist": checklist,
        "isSubjectToAppraisal": status == STATUS_REQUIRED,
        "appraisalReason": basis["summary"],
        "appraisalBasis": basis,
        "buildingCategory": basis["category"],
    }


def get_local_fallback_response(project: Dict[str, Any]) -> Dict[str, Any]:
    """Phản hồi dự phòng khi Gemini không dùng được — 'reply' TỰ CHỨA tóm tắt
    (không "hứa" nội dung nằm ở nơi khác), kết luận lấy từ cùng nguồn
    `appraisalBasis` như mọi nơi khác trên giao diện."""
    result = evaluate_appraisal(project)
    basis = result["appraisalBasis"]
    non_compliant = [c["criteria"] for c in result["checklist"] if c["result"] == "Không đạt"]
    subject_text = {
        STATUS_REQUIRED: "thuộc ngưỡng sàng lọc thẩm định thiết kế PCCC",
        STATUS_NOT_REQUIRED: "dưới ngưỡng danh mục đã xét; cần kiểm tra phạm vi áp dụng",
        STATUS_INSUFFICIENT: "CHƯA ĐỦ THÔNG SỐ để kết luận thẩm duyệt",
    }[basis["status"]]

    summary_lines = [
        "⚠️ Hệ thống AI (Gemini) hiện không phản hồi được — có thể do chưa cấu hình GEMINI_API_KEY, hết hạn "
        "mức sử dụng, hoặc dịch vụ Google đang gián đoạn. Hệ thống đã TỰ ĐỘNG chuyển sang bộ luật cứng "
        "(rules engine nội bộ, không cần AI) để bạn vẫn có kết quả rà soát ngay lập tức:",
        "",
        f"• Kết luận: công trình {subject_text}.",
        f"• Lý do: {basis['summary']}",
    ]
    if non_compliant:
        summary_lines.append(f"• {len(non_compliant)} hạng mục CHƯA ĐẠT: {', '.join(non_compliant)}.")
    else:
        summary_lines.append("• Chưa có bằng chứng để chấm đạt/không đạt các hạng mục kỹ thuật.")
    summary_lines.append("• Xem đầy đủ 17 hạng mục kèm giải trình chi tiết trong bảng bên dưới/panel thông số dự án.")
    summary_lines.append(
        "Lưu ý: kết quả trên chỉ dựa vào công thức cố định, CHƯA có phân tích ngữ cảnh sâu như khi AI hoạt "
        "động bình thường — khuyến nghị thử lại sau hoặc liên hệ quản trị viên kiểm tra cấu hình dịch vụ AI."
    )

    return {
        "reply": "\n".join(summary_lines),
        "warnings": result["warnings"],
        "isSubjectToAppraisal": result["isSubjectToAppraisal"],
        "appraisalReason": result["appraisalReason"],
        "checklist": result["checklist"],
        "extractedProjectInfo": project,
    }


def get_rag_context_for_project(project: Dict[str, Any], document_database: List[Dict[str, Any]]) -> str:
    query_words: List[str] = []

    project_type = (project.get("type") or "").lower()
    if project_type:
        if any(k in project_type for k in ("karaoke", "vũ trường", "hát")):
            query_words += ["karaoke", "thông tư 147", "147/2020"]
        elif any(k in project_type for k in ("gara", "ô tô")):
            query_words += ["gara", "quy chuẩn 13", "qcvn 13:2018"]
        elif any(k in project_type for k in ("kho", "giá đỡ", "kệ")):
            query_words += ["nhà kho", "kho chứa", "giá đỡ", "kệ cao", "ngăn cháy"]
        elif any(k in project_type for k in ("chợ", "thương mại", "siêu thị")):
            query_words += ["chợ", "bảng h.5", "tổng diện tích", "trung tâm thương mại"]
        elif any(k in project_type for k in ("hỗn hợp", "kinh doanh", "văn phòng")):
            query_words += ["hỗn hợp", "f1.4", "kinh doanh", "tường ngăn cháy"]

    query_words += ["qcvn 06", "qcvn 10", "nghị định 105", "phụ lục iii"]

    matched_docs = []
    for d in document_database:
        text_to_search = f"{d.get('code', '')} {d.get('title', '')} {d.get('content', '')}".lower()
        if any(word in text_to_search for word in query_words):
            matched_docs.append(d)

    if matched_docs:
        return "\n\n".join(
            f"[TÀI LIỆU CỐT LÕI: {d.get('code')} - {d.get('title')}]\n{d.get('content')}"
            for d in matched_docs[:4]
        )

    return "Không tìm thấy tài liệu phù hợp trực tiếp, ưu tiên áp dụng QCVN 06:2022 và QCVN 10:2025."


def get_prior_projects_context(
    project: Dict[str, Any],
    chat_sessions: List[Dict[str, Any]],
    current_session_id: Optional[str] = None,
) -> str:
    scored = []
    for s in chat_sessions:
        if s.get("id") == current_session_id:
            continue
        sp = s.get("projectInfo")
        if not sp or not s.get("checklist"):
            continue

        score = 0
        if sp.get("type") == project.get("type"):
            score += 30
        if sp.get("floors") == project.get("floors"):
            score += 20
        diff_area = abs((sp.get("totalFloorArea") or 0) - (project.get("totalFloorArea") or 0))
        if diff_area < 50:
            score += 25
        elif diff_area < 200:
            score += 15
        if sp.get("fireRating") == project.get("fireRating"):
            score += 15
        if sp.get("basements") == project.get("basements"):
            score += 10

        if score >= 30:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    similar = [s for _, s in scored[:3]]

    if not similar:
        return "Không có dự án tương đồng nào trong lịch sử trước đây để đối chiếu học hỏi."

    context = (
        "DƯỚI ĐÂY LÀ CÁC CÔNG TRÌNH TƯƠNG ĐỒNG ĐÃ ĐƯỢC KIỂM TRA TRONG LỊCH SỬ (HỆ THỐNG CẦN HỌC HỎI CÁC "
        "THÔNG SỐ VÀ KẾT QUẢ ĐÃ DUYỆT ĐỂ KIỂM TRA NHANH HƠN VÀ ĐỒNG NHẤT KHÔNG CẦN TÍNH TOÁN LẠI TỪ ĐẦU):\n"
    )
    for idx, entry in enumerate(similar):
        sp = entry.get("projectInfo", {})
        context += f"\n[Mẫu Học tập {idx + 1}]"
        context += f"\n- Tên công trình trước: {sp.get('name')}"
        context += (
            f"\n- Quy mô: {sp.get('floors')} tầng nổi, {sp.get('basements')} tầng hầm, "
            f"diện tích sàn: {sp.get('floorArea')} m2, tổng diện tích: {sp.get('totalFloorArea')} m2."
        )
        context += f"\n- Loại hình: {sp.get('type')}, Bậc chịu lửa: {sp.get('fireRating')}"
        context += f"\n- Thẩm duyệt Công an bắt buộc: {'Bắt buộc' if entry.get('isSubjectToAppraisal') else 'Không bắt buộc'}"
        context += f"\n- Lý do thẩm duyệt: {entry.get('appraisalReason')}"

        checklist = entry.get("checklist")
        if checklist:
            non_compliant = ", ".join(c["criteria"] for c in checklist if c.get("result") == "Không đạt")
            compliant = ", ".join(c["criteria"] for c in checklist if c.get("result") == "Đạt")
            context += f"\n- Các mục ĐẠT của công trình trước: {compliant or 'Không'}"
            context += f"\n- Các mục KHÔNG ĐẠT của công trình trước: {non_compliant or 'Không'}"
        context += "\n"

    return context


def evaluate_components(project: Dict[str, Any]) -> Dict[str, Any]:
    """Independent parameters and rules per building; never sum into a fictitious house."""
    from app.appraisal_basis import RULES_VERSION, SOURCE_URL
    results = []
    checklist, warnings = [], []
    for component in project["components"]:
        result = evaluate_appraisal(component)
        results.append({"id": component["id"], "name": component["name"], **result})
        for row in result["checklist"]:
            checklist.append({**row, "stt": len(checklist) + 2, "componentId": component["id"],
                              "componentName": component["name"], "criteria": f"{component['name']} — {row['criteria']}"})
        warnings.extend(f"{component['name']}: {w}" for w in result["warnings"])
    statuses = [r["appraisalBasis"]["status"] for r in results]
    complete = project.get("componentsComplete") is True
    shared, concurrent = project.get("sharedSystems"), project.get("concurrentDesign")
    required = STATUS_REQUIRED in statuses
    uncertain = STATUS_INSUFFICIENT in statuses or not complete
    if required and shared is not False and concurrent is not False:
        uncertain = True
        warnings.append("Cần xác nhận thiết kế đồng thời và dùng chung hệ thống báo cháy/chữa cháy. Ghi chú Phụ lục III có thể yêu cầu thẩm định nội dung hệ thống chung của hạng mục dưới ngưỡng.")
    if required and shared is True and concurrent is True:
        shared_text = "Thuộc phạm vi thẩm định nội dung hệ thống dùng chung theo ghi chú Phụ lục III vì thiết kế đồng thời và dùng chung hệ thống báo cháy/chữa cháy với hạng mục thuộc diện. Ngưỡng riêng của nhà không thay đổi."
        for r in results:
            if r["appraisalBasis"]["status"] == STATUS_NOT_REQUIRED:
                r["sharedSystemScope"] = {"status": "required", "reason": shared_text}
                r["appraisalBasis"]["sharedSystemScope"] = r["sharedSystemScope"]
                r["appraisalBasis"]["summary"] += " " + shared_text
                r["appraisalBasis"]["conclusion"] += " " + shared_text
                for row in checklist:
                    if row.get("componentId") == r["id"] and row["result"] == "Dưới ngưỡng danh mục":
                        row["note"] += " " + shared_text
    status = STATUS_REQUIRED if required else STATUS_INSUFFICIENT if uncertain else STATUS_NOT_REQUIRED
    if not complete:
        warnings.append("Chưa xác nhận danh sách hạng mục đầy đủ; không được kết luận miễn cho toàn dự án.")
    lines = [f"{r['name']} ({r['appraisalBasis']['categoryLabel']}): {r['appraisalBasis']['summary']} {r['appraisalBasis']['legalText']}" for r in results]
    headline = "Có hạng mục thuộc ngưỡng danh mục." if required else "Chưa đủ căn cứ kết luận toàn dự án." if uncertain else "Các hạng mục đã khai báo dưới ngưỡng danh mục; không phải miễn mọi thủ tục."
    summary = headline + "\n" + "\n".join(lines)
    basis = {"status": status, "category": "multi_component", "categoryLabel": "Dự án nhiều hạng mục",
        "categoryEvidence": f"{len(results)} hạng mục độc lập đã khai báo", "ruleMode": "manual_review",
        "thresholdSource": "statutory", "legalText": "Phụ lục III Nghị định 347/2026/NĐ-CP; xét riêng từng nhà, không cộng diện tích thành một nhà. Phạm vi hệ thống dùng chung cần rà soát theo ghi chú Phụ lục.",
        "thresholds": [], "triggeredBy": [r["id"] for r in results if r["appraisalBasis"]["status"] == STATUS_REQUIRED],
        "missingFields": ["componentsComplete"] if not complete else [], "summary": summary, "conclusion": summary,
        "actualScale": f"{len(results)} hạng mục; không gộp quy mô", "componentResults": results,
        "rulesVersion": RULES_VERSION, "sourceUrl": SOURCE_URL}
    checklist.insert(0, {"stt": 1, "category": "Tổng hợp phạm vi dự án", "criteria": "Tổng hợp phạm vi dự án",
        "requirement": "Rà soát từng nhà và phạm vi hệ thống dùng chung; không gộp quy mô.",
        "result": "Thuộc diện thẩm định" if required else "Cần xem xét" if uncertain else "Dưới ngưỡng danh mục",
        "note": summary, "reference": "Phụ lục III Nghị định 347/2026/NĐ-CP"})
    return {"warnings": list(dict.fromkeys(warnings)), "checklist": checklist,
        "isSubjectToAppraisal": required, "appraisalReason": summary, "appraisalBasis": basis, "buildingCategory": "multi_component"}
