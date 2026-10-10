"""Additional 3000 reproducible generated profiles; independent of the 40 API scenarios."""
from pathlib import Path
import sys
import random
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.rules_engine import evaluate_appraisal
from app.ai_guard import guard_reply, sanitize_extracted_info

rng=random.Random(20261008)
for i in range(3000):
    p={"type":rng.choice(["Nhà hỗn hợp","Gara ô tô","Nhà kho","Trường học","Karaoke","Nhà ở riêng lẻ kết hợp kinh doanh"]),
       "floors":rng.randint(0,200),"totalFloorArea":rng.randint(0,10000),"pcccHeight":rng.randint(0,500)}
    a=evaluate_appraisal(p)
    assert a==evaluate_appraisal(p)
    assert [c['stt'] for c in a['checklist']]==list(range(1,18))
    assert all(c['result']=="Cần xem xét" for c in a['checklist'][1:])
    assert a['isSubjectToAppraisal']==(a['appraisalBasis']['status']=='required')
    if a['appraisalBasis']['thresholdSource']!='statutory':
        assert a['appraisalBasis']['status']=='insufficient_data'
    reply,errors=guard_reply("Công trình bắt buộc thẩm định bất kể quy mô.",a['appraisalBasis'],p)
    assert errors and "bất kể quy mô" not in reply
print("PASS: 3000 generated profiles; deterministic verdicts, manual review, 17 items, unsupported AI claim guard.")
