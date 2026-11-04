"""Additional 3000 reproducible generated profiles; independent of the 40 API scenarios."""
from pathlib import Path
import sys
import random
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rules_engine import evaluate_appraisal
from app.ai_guard import guard_reply, sanitize_extracted_info

VALID_RESULTS = {
    "Đạt",
    "Không đạt",
    "Không bắt buộc",
    "Khuyến nghị mạnh",
    "Khuyến nghị",
    "Cần đo đạc",
    "Cần xem xét",
}


def run_fuzz_3000() -> None:
    rng = random.Random(20261008)
    for i in range(3000):
        p = {
            "type": rng.choice([
                "Nhà hỗn hợp",
                "Gara ô tô",
                "Nhà kho",
                "Trường học",
                "Karaoke",
                "Nhà ở riêng lẻ kết hợp kinh doanh",
            ]),
            "floors": rng.randint(0, 200),
            "totalFloorArea": rng.randint(0, 10000),
            "pcccHeight": rng.randint(0, 500),
            "volume": rng.choice([0, rng.randint(500, 80000)]),
            "fireRating": rng.choice(["", "Bậc I", "Bậc II", "Bậc III", "Bậc IV", "Bậc V"]),
        }
        a = evaluate_appraisal(p)
        assert a == evaluate_appraisal(p)
        assert [c["stt"] for c in a["checklist"]] == list(range(1, 18))
        assert a["checklist"][0]["result"] in {"Thuộc diện thẩm định", "Dưới ngưỡng danh mục", "Cần xem xét"}
        assert all(c["result"] in VALID_RESULTS for c in a["checklist"][1:])
        assert all(bool(c.get("note")) and bool(c.get("reference")) for c in a["checklist"][1:])
        has_tech = (
            p["pcccHeight"] > 0
            or p["volume"] > 0
            or a["appraisalBasis"]["status"] in ("required", "not_required")
        )
        if not has_tech:
            assert all(c["result"] == "Cần xem xét" for c in a["checklist"][1:])
        assert a["isSubjectToAppraisal"] == (a["appraisalBasis"]["status"] == "required")
        if a["appraisalBasis"]["thresholdSource"] != "statutory":
            assert a["appraisalBasis"]["status"] == "insufficient_data"
        reply, errors = guard_reply("Công trình bắt buộc thẩm định bất kể quy mô.", a["appraisalBasis"], p)
        assert errors and "bất kể quy mô" not in reply

    # Edge case: zero-scale building with only fireRating set must not falsely score "Đạt"
    zero_scale = evaluate_appraisal({
        "type": "Nhà hỗn hợp",
        "floors": 0,
        "totalFloorArea": 0,
        "pcccHeight": 0,
        "volume": 0,
        "fireRating": "Bậc IV",
    })
    assert all(c["result"] == "Cần xem xét" for c in zero_scale["checklist"][1:])


class RulesFuzzTests(unittest.TestCase):
    def test_3000_generated_profiles(self):
        run_fuzz_3000()


if __name__ == "__main__":
    run_fuzz_3000()
    print("PASS: 3000 generated profiles; deterministic verdicts, dynamic 16-item QCVN 06 scoring, 17 items, unsupported AI claim guard.")

