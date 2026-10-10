"""Sinh dữ liệu mẫu cho test giao diện từ CHÍNH backend thật (không viết tay),
để test UI luôn kiểm tra đúng dữ liệu mà server sẽ trả về."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.rules_engine import evaluate_appraisal  # noqa: E402

MIXED = "Nhà hỗn hợp"
CASES = {
    "karaoke_5_500": {"type": "Cơ sở kinh doanh Karaoke, Vũ trường", "floors": 5, "totalFloorArea": 500, "floorArea": 100, "pcccHeight": 18, "fireRating": "Bậc III", "name": "Kiem lai 2"},
    "mixed_8_900": {"type": MIXED, "floors": 8, "totalFloorArea": 900, "floorArea": 112, "pcccHeight": 26, "fireRating": "Bậc II"},
    "mixed_5_500": {"type": MIXED, "floors": 5, "totalFloorArea": 500, "floorArea": 100, "pcccHeight": 18, "fireRating": "Bậc II"},
    "mixed_5_0": {"type": MIXED, "floors": 5, "totalFloorArea": 0, "floorArea": 100, "pcccHeight": 18, "fireRating": "Bậc II"},
    "warehouse_1_900": {"type": "Nhà kho xếp giá đỡ kệ cao", "floors": 1, "totalFloorArea": 900, "floorArea": 900, "pcccHeight": 8, "fireRating": "Bậc II"},
    "market_3_600": {"type": "Chợ, Trung tâm thương mại", "floors": 3, "totalFloorArea": 600, "floorArea": 200, "pcccHeight": 12, "fireRating": "Bậc II"},
}
CASES["factory_C_7200"] = {"name": "Nhà xưởng", "type": "Nhà máy, nhà xưởng sản xuất", "floors": 1, "totalFloorArea": 7200, "volume": 98935.2, "hazardClass": "C", "industrialSubtype": "other"}
CASES["sabaco_multi"] = {"name": "Sabaco", "componentsComplete": True, "sharedSystems": False, "concurrentDesign": True,
    "components": [{"id":"kho","name":"Nhà kho","type":"Nhà kho","volume":30259.2,"hazardClass":"C"},
                   {"id":"kho_tp","name":"Kho thành phẩm","type":"Nhà kho","volume":59294.4,"hazardClass":"C"},
                   {"id":"xuong","name":"Nhà xưởng","type":"Nhà xưởng","volume":98935.2,"hazardClass":"C","industrialSubtype":"other"},
                   {"id":"office","name":"Nhà văn phòng","type":"Văn phòng","totalFloorArea":540}]}
out = {}
for key, proj in CASES.items():
    ev = evaluate_appraisal(proj)
    out[key] = {"project": proj, "checklist": ev["checklist"], "isSubject": ev["isSubjectToAppraisal"],
                "reason": ev["appraisalReason"], "basis": ev["appraisalBasis"], "warnings": ev["warnings"]}
target = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "tests", "fixtures.json")
with open(target, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print("Đã sinh", len(out), "fixture ->", os.path.normpath(target))
