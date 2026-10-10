"""40 numbered, reproducible operational scenarios. Isolated SQLite by default.
Set TEST_DATABASE_URL to a disposable PostgreSQL database named pccc_test to
also exercise PostgreSQL advisory locks. NEVER run this suite on customer data.
"""
import asyncio
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, AsyncMock
import zipfile

TMP = tempfile.TemporaryDirectory(prefix="pccc-qa-")
TEST_URL = os.getenv("TEST_DATABASE_URL", f"sqlite+aiosqlite:///{TMP.name}/qa.sqlite")
if not TEST_URL.startswith("sqlite+") and not TEST_URL.endswith("/pccc_test"):
    raise RuntimeError("TEST_DATABASE_URL must target disposable database pccc_test")
os.environ.update(DATABASE_URL=TEST_URL, NODE_ENV="development", PCCC_DATA_DIR=TMP.name,
                  JWT_SECRET="qa-only-secret-" + "a" * 40, PCCC_ADMIN_PASSWORD="TestAdmin12345")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlalchemy import select
import jwt
from app import main
from app.auth import hash_password, create_access_token
from app.config import JWT_SECRET
from app.db import engine, Base, AsyncSessionLocal
from app.db_models import User
from app.hardening import validate_upload, resolve_stored_file
from app.rules_engine import evaluate_appraisal, get_local_fallback_response
from app.schemas_auth import RegisterRequest
from app.schemas_project import ProjectUpdateRequest
from docx import Document as WordDocument
from pypdf import PdfReader
from PIL import Image
from reportlab.pdfgen import canvas


def png():
    buf = io.BytesIO(); Image.new("RGB", (8, 8), "white").save(buf, "PNG"); return buf.getvalue()


def docx():
    buf = io.BytesIO(); d = WordDocument(); d.add_paragraph("Văn bản pháp lý kiểm thử"); d.save(buf); return buf.getvalue()


class Operations40(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        async def reset():
            import app.db_models
            async with engine.begin() as c:
                await c.run_sync(Base.metadata.drop_all)
        asyncio.run(reset())
        cls.ctx = TestClient(main.app)
        cls.client = cls.ctx.__enter__()
        r = cls.client.post("/api/auth/login-json", json={"username":"admin", "password":"TestAdmin12345"})
        assert r.status_code == 200, r.text
        cls.admin = {"Authorization": "Bearer " + r.json()["access_token"]}
        for name in ("staffa", "staffb"):
            r = cls.client.post("/api/auth/users", headers=cls.admin, json={"username":name,"password":"StaffTest12345"})
            assert r.status_code == 201, r.text
            r = cls.client.post("/api/auth/login-json", json={"username":name,"password":"StaffTest12345"})
            setattr(cls, name, {"Authorization":"Bearer " + r.json()["access_token"]})

    @classmethod
    def tearDownClass(cls):
        cls.ctx.__exit__(None, None, None)

    def setUp(self):
        main.limiter.reset()

    def session(self, auth=None, project=None, reviewed=True):
        r = self.client.post("/api/sessions", headers=auth or self.staffa,
                             json={"projectInfo":project or {"type":"Nhà hỗn hợp","floors":2,"floorArea":100,"totalFloorArea":200}})
        self.assertEqual(r.status_code, 201, r.text)
        sid=r.json()["id"]
        if reviewed:
            result=self.client.put(f"/api/sessions/{sid}/project?appraise=true",headers=auth or self.staffa,json={})
            self.assertEqual(result.status_code,200,result.text)
        return sid

    def upload(self, name, data, **extra):
        return self.client.post("/api/documents/upload", headers=self.admin,
                                files={"file":(name,data)}, data=extra)

    def test_T01_health_and_readiness(self):
        self.assertEqual(self.client.get("/api/health").status_code,200)
        self.assertEqual(self.client.get("/api/ready").json()["status"],"ready")

    def test_T02_missing_authentication(self):
        for route in ("/api/documents","/api/sessions","/api/auth/me","/api/inspection-logs"):
            self.assertEqual(self.client.get(route).status_code,401)

    def test_T03_invalid_and_expired_jwt(self):
        for token in ("invalid", jwt.encode({"sub":"none","exp":1}, JWT_SECRET, algorithm="HS256")):
            self.assertEqual(self.client.get("/api/auth/me",headers={"Authorization":"Bearer "+token}).status_code,401)

    def test_T04_public_registration_closed(self):
        self.assertEqual(self.client.post("/api/auth/register",json={"username":"intruder","password":"Intruder12345"}).status_code,403)

    def test_T05_staff_cannot_manage_users(self):
        self.assertEqual(self.client.post("/api/auth/users", headers=self.staffa,json={"username":"attacker","password":"Attacker12345","role":"admin"}).status_code,403)

    def test_T06_duplicate_username(self):
        self.assertEqual(self.client.post("/api/auth/users",headers=self.admin,json={"username":"staffa","password":"ValidTest12345"}).status_code,409)

    def test_T07_staff_quota_excludes_admin(self):
        with patch.object(main,"MAX_STAFF_ACCOUNTS",2):
            self.assertEqual(self.client.post("/api/auth/users",headers=self.admin,json={"username":"thirdstaff","password":"ValidTest12345"}).status_code,403)
        with patch.object(main,"MAX_STAFF_ACCOUNTS",3):
            r=self.client.post("/api/auth/users",headers=self.admin,json={"username":"quotastaff","password":"ValidTest12345"})
            self.assertEqual(r.status_code,201,r.text)

    def test_T08_bad_role_and_password(self):
        for payload in ({"role":"root","password":"ValidTest12345"},{"password":"aaaaaaaaaaaa"},{"password":"é"*40+"A1"}):
            r=self.client.post("/api/auth/users",headers=self.admin,json={"username":"baduser",**payload})
            self.assertEqual(r.status_code,422,r.text)

    def test_T09_login_wrong_credentials(self):
        for route,opts in (("/api/auth/login-json",{"json":{"username":"admin","password":"wrong"}}),("/api/auth/login",{"data":{"username":"admin","password":"wrong"}})):
            self.assertEqual(self.client.post(route,**opts).status_code,401)

    def test_T10_login_rate_limit(self):
        codes=[self.client.post("/api/auth/login-json",json={"username":"none","password":"wrong"}).status_code for _ in range(11)]
        self.assertEqual(codes[-1],429)

    def test_T11_password_change_revokes_old_token(self):
        self.client.post("/api/auth/users",headers=self.admin,json={"username":"pwuser","password":"BeforeTest12345"})
        token=self.client.post("/api/auth/login-json",json={"username":"pwuser","password":"BeforeTest12345"}).json()["access_token"]
        h={"Authorization":"Bearer "+token}
        self.assertEqual(self.client.put("/api/auth/me/password",headers=h,json={"old_password":"BeforeTest12345","new_password":"AfterTest12345"}).status_code,200)
        self.assertEqual(self.client.get("/api/auth/me",headers=h).status_code,401)
        self.assertEqual(self.client.post("/api/auth/login-json",json={"username":"pwuser","password":"AfterTest12345"}).status_code,200)

    def test_T12_owner_only_session_listing(self):
        sid=self.session(self.staffb)
        self.assertNotIn(sid,[s["id"] for s in self.client.get("/api/sessions",headers=self.staffa).json()])
        self.assertIn(sid,[s["id"] for s in self.client.get("/api/sessions",headers=self.admin).json()])

    def test_T13_cross_owner_write_delete_chat(self):
        sid=self.session(self.staffb)
        self.assertEqual(self.client.put(f"/api/sessions/{sid}/project",headers=self.staffa,json={"name":"hack"}).status_code,403)
        self.assertEqual(self.client.delete(f"/api/sessions/{sid}",headers=self.staffa).status_code,403)
        with patch.object(main,"run_deep_llm_appraisal",AsyncMock()) as ai:
            self.assertEqual(self.client.post("/api/chat",headers=self.staffa,json={"sessionId":sid,"messageText":"Hi"}).status_code,403)
            ai.assert_not_awaited()

    def test_T14_cross_owner_export_and_log(self):
        sid=self.session(self.staffb)
        self.assertEqual(self.client.post("/api/report/export-json",headers=self.staffa,json={"sessionId":sid}).status_code,403)
        self.assertEqual(self.client.get(f"/api/sessions/{sid}/inspection-logs",headers=self.staffa).status_code,403)

    def test_T15_ocr_authorization_before_ai(self):
        sid=self.session(self.staffb)
        with patch.object(main,"extract_project_data_from_drawing",AsyncMock()) as ai:
            r=self.client.post("/api/ocr/extract-drawing",headers=self.staffa,data={"session_id":sid},files={"file":("plan.png",png(),"image/png")})
            self.assertEqual(r.status_code,403); ai.assert_not_awaited()

    def test_T16_missing_session(self):
        self.assertEqual(self.client.put("/api/sessions/does-not-exist/project",headers=self.staffa,json={}).status_code,404)
        self.assertEqual(self.client.post("/api/report/export-json",headers=self.staffa,json={"sessionId":"missing"}).status_code,404)

    def test_T17_negative_project_numbers(self):
        for field in ("floors","totalFloorArea","pcccHeight","basements"):
            self.assertEqual(self.client.post("/api/sessions",headers=self.staffa,json={"projectInfo":{field:-1}}).status_code,422)

    def test_T18_invalid_nested_arrays(self):
        for payload in ({"basementHeights":[-2]}, {"basementAreas":["NaN"]}, {"floorFunctions":["x"*501]}, {"basementFunctions":["x"]*21}):
            self.assertEqual(self.client.post("/api/sessions",headers=self.staffa,json={"projectInfo":payload}).status_code,422)

    def test_T19_nonfinite_and_fractional_floor(self):
        for payload in ({"height":"Infinity"},{"floorArea":"NaN"},{"floors":1.5}):
            self.assertEqual(self.client.post("/api/sessions",headers=self.staffa,json={"projectInfo":payload}).status_code,422)

    def test_T20_partial_patch_revalidates_saved_project(self):
        sid=self.session()
        r=self.client.put(f"/api/sessions/{sid}/project",headers=self.staffa,json={"totalFloorArea":50})
        self.assertEqual(r.status_code,422)
        r=self.client.put(f"/api/sessions/{sid}/project",headers=self.staffa,json={"name":"Updated"})
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()["projectInfo"]["floors"],2)

    def test_T21_valid_stepped_building_not_rejected(self):
        sid=self.session(project={"type":"Nhà hỗn hợp","floors":10,"floorArea":1000,"totalFloorArea":2000})
        self.assertTrue(sid)

    def test_T22_blank_and_overlong_chat(self):
        for msg in ("   ","x"*8001):
            self.assertEqual(self.client.post("/api/chat",headers=self.staffa,json={"sessionId":"x","messageText":msg}).status_code,422)

    def test_T23_staff_cannot_upload_delete_reset(self):
        self.assertEqual(self.client.post("/api/documents/upload",headers=self.staffa,files={"file":("law.txt",b"text")}).status_code,403)
        self.assertEqual(self.client.post("/api/documents/reset",headers=self.staffa).status_code,403)
        self.assertEqual(self.client.delete("/api/documents/x",headers=self.staffa).status_code,403)

    def test_T24_valid_txt_roundtrip_and_safe_name(self):
        r=self.upload("../../law.txt","Nội dung kiểm thử".encode());self.assertEqual(r.status_code,201,r.text)
        d=r.json();self.assertNotIn("..",d["link"])
        download=self.client.get(f"/api/documents/{d['id']}/download",headers=self.admin)
        self.assertEqual(download.content,"Nội dung kiểm thử".encode())
        self.assertEqual(self.client.delete(f"/api/documents/{d['id']}",headers=self.admin).status_code,200)

    def test_T25_disallowed_extension(self):
        self.assertEqual(self.upload("law.exe",b"MZ").status_code,400)

    def test_T26_spoofed_pdf(self):
        self.assertEqual(self.upload("law.pdf",b"<script>alert(1)</script>").status_code,422)

    def test_T27_corrupt_docx(self):
        self.assertEqual(self.upload("law.docx",b"bad zip").status_code,422)

    def test_T28_docx_zip_bomb(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w",zipfile.ZIP_DEFLATED) as z:z.writestr("word/document.xml","x"*1_000_000)
        self.assertEqual(self.upload("law.docx",b.getvalue()).status_code,422)

    def test_T29_empty_binary_and_invalid_utf8_txt(self):
        for b in (b"",b"abc\x00",b"\xff\xfe"):
            self.assertIn(self.upload("law.txt",b).status_code,(400,422))

    def test_T30_upload_size_limit(self):
        with patch.object(main,"MAX_UPLOAD_SIZE_BYTES",10):
            self.assertEqual(self.upload("law.txt",b"x"*11).status_code,413)

    def test_T31_atomic_multifile_upload(self):
        before=set(main.LEGAL_DB_DIR.iterdir())
        count=len(self.client.get("/api/documents",headers=self.admin).json())
        r=self.client.post("/api/documents/upload",headers=self.admin,files=[("file",("ok.txt",b"valid")),("file",("bad.pdf",b"not pdf"))])
        self.assertEqual(r.status_code,422)
        self.assertEqual(before,set(main.LEGAL_DB_DIR.iterdir()))
        self.assertEqual(count,len(self.client.get("/api/documents",headers=self.admin).json()))

    def test_T32_valid_docx_and_metadata_bounds(self):
        self.assertEqual(self.upload("law.docx",docx()).status_code,201)
        self.assertEqual(self.upload("law.txt",b"valid",type="x"*65).status_code,422)

    def test_T33_scanned_pdf_not_fake_rag(self):
        b=io.BytesIO();c=canvas.Canvas(b);c.showPage();c.save()
        self.assertEqual(self.upload("scan.pdf",b.getvalue()).status_code,422)

    def test_T34_download_path_confined(self):
        with self.assertRaises(Exception):resolve_stored_file("/data/legal_db/../../secrets",main.UPLOADS_DIR,main.LEGAL_DB_DIR)
        self.assertIsNone(resolve_stored_file("https://example.org/file",main.UPLOADS_DIR,main.LEGAL_DB_DIR))

    def test_T35_reset_cleans_custom_files(self):
        self.upload("temporary.txt",b"valid text")
        self.assertTrue(list(main.LEGAL_DB_DIR.iterdir()))
        self.assertEqual(self.client.post("/api/documents/reset",headers=self.admin).status_code,200)
        self.assertEqual(list(main.LEGAL_DB_DIR.iterdir()),[])

    def test_T36_export_uses_saved_data_not_client(self):
        sid=self.session()
        r=self.client.post("/api/report/export-json",headers=self.staffa,json={"sessionId":sid,"projectInfo":{"name":"forged"},"checklist":[{"result":"Đạt"}]})
        self.assertEqual(r.status_code,200)
        self.assertNotEqual(r.json()["projectInfo"]["name"],"forged")
        self.assertEqual(len(r.json()["checklist"]),17)
        self.assertEqual(self.client.post("/api/report/export-json",headers=self.staffa,json={}).status_code,422)

    def test_T37_docx_and_pdf_exports_open(self):
        sid=self.session(project={"name":"Công trình Việt Nam","type":"Nhà hỗn hợp","floors":7,"totalFloorArea":2000})
        word=self.client.post("/api/report/export",headers=self.staffa,json={"sessionId":sid})
        self.assertEqual(word.status_code,200,word.text[:100])
        text=" ".join(p.text for p in WordDocument(io.BytesIO(word.content)).paragraphs)
        self.assertIn("CÔNG TRÌNH VIỆT NAM",text.upper())
        pdf=self.client.post("/api/report/export-pdf",headers=self.staffa,json={"sessionId":sid})
        self.assertEqual(pdf.status_code,200)
        self.assertGreater(len(PdfReader(io.BytesIO(pdf.content)).pages),0)
        self.assertNotIn("BỞI CƠ QUAN CÔNG AN",text)

    def test_T38_ocr_updates_draft_and_cleans_temp(self):
        sid=self.session()
        with patch.object(main,"extract_project_data_from_drawing",AsyncMock(return_value={"floors":7})):
            r=self.client.post("/api/ocr/extract-drawing",headers=self.staffa,data={"session_id":sid,"apply_to_session":"true"},files={"file":("plan.png",png(),"image/png")})
        self.assertEqual(r.status_code,200,r.text)
        logs=self.client.get(f"/api/sessions/{sid}/inspection-logs",headers=self.staffa).json()
        self.assertTrue(all(log["triggerSource"] != "ocr_autofill" for log in logs))
        snapshot=self.client.get(f"/api/sessions/{sid}",headers=self.staffa).json()
        self.assertEqual(snapshot["reviewState"],"draft")
        self.assertEqual(snapshot["checklist"],[])
        reviewed=self.client.put(f"/api/sessions/{sid}/project?appraise=true",headers=self.staffa,json={})
        self.assertTrue(reviewed.json()["isSubjectToAppraisal"])
        self.assertEqual(list(main.DRAWINGS_DIR.iterdir()),[])
        with patch.object(main,"extract_project_data_from_drawing",AsyncMock(side_effect=RuntimeError("private token"))):
            r=self.client.post("/api/ocr/extract-drawing",headers=self.staffa,files={"file":("plan.png",png(),"image/png")})
        self.assertEqual(r.status_code,502);self.assertNotIn("private token",r.text)
        self.assertEqual(list(main.DRAWINGS_DIR.iterdir()),[])

    def test_T39_chat_cannot_apply_ai_hallucinations(self):
        sid=self.session()
        async def fake(project,history,documents,others,*args):
            self.assertEqual(others,[])
            return {**get_local_fallback_response(project),"extractedProjectInfo":{"floors":999},"checklist":["bad"]}
        with patch.object(main,"run_deep_llm_appraisal",side_effect=fake):
            r=self.client.post("/api/chat",headers=self.staffa,json={"sessionId":sid,"messageText":"Xin kiểm tra"})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()["projectInfo"]["floors"],2)
        self.assertEqual(len(r.json()["checklist"]),17)
        self.assertTrue(all(c["result"]=="Cần xem xét" for c in r.json()["checklist"][1:]))

    def test_T40_legal_thresholds_missing_data_and_determinism(self):
        cases=[("Cơ sở kinh doanh karaoke, vũ trường",2,499,"not_required"),
               ("Cơ sở kinh doanh karaoke, vũ trường",4,100,"required"),
               ("Cơ sở kinh doanh karaoke, vũ trường",1,1000,"required"),
               ("Cơ sở kinh doanh karaoke, vũ trường",0,0,"insufficient_data"),
               ("Nhà hỗn hợp",6,2999,"insufficient_data"),("Nhà hỗn hợp",7,1000,"required"),
               ("Nhà hỗn hợp",6,3000,"required"),("Nhà ở riêng lẻ kết hợp kinh doanh",8,4000,"insufficient_data"),
               ("Nhà kho",1,10000,"insufficient_data"),("Nhà để xe ô tô dạng kín",0,2000,"required"),
               ("Cơ sở giáo dục, trường học",5,9000,"insufficient_data")]
        for kind,floors,area,status in cases:
            with self.subTest(kind=kind,floors=floors,area=area):
                p={"type":kind,"floors":floors,"totalFloorArea":area}
                result=evaluate_appraisal(p)
                self.assertEqual(result["appraisalBasis"]["status"],status)
                self.assertEqual(result,evaluate_appraisal(p))
                self.assertEqual(len(result["checklist"]),17)
        from app.appraisal_basis import to_number, classify_building
        self.assertEqual(to_number("-5 tầng"),0)
        self.assertEqual(classify_building({"type":"Nhà ở riêng lẻ","commercialDetails":"không có karaoke"})[0],"private_house")

    def test_S01_ocr_preview_does_not_mutate_project_or_logs(self):
        sid=self.session(self.staffa)
        before=self.client.get(f"/api/sessions/{sid}",headers=self.staffa).json()
        logs=self.client.get(f"/api/sessions/{sid}/inspection-logs",headers=self.staffa).json()
        with patch.object(main,"extract_project_data_from_drawing",AsyncMock(return_value={"floors":7})):
            r=self.client.post("/api/ocr/extract-drawing",headers=self.staffa,data={"session_id":sid},files={"file":("plan.png",png(),"image/png")})
        self.assertEqual(r.status_code,200,r.text)
        self.assertFalse(r.json()["appliedToSession"])
        self.assertEqual(r.json()["extractedProjectInfo"]["floors"],7)
        self.assertEqual(before,self.client.get(f"/api/sessions/{sid}",headers=self.staffa).json())
        self.assertEqual(logs,self.client.get(f"/api/sessions/{sid}/inspection-logs",headers=self.staffa).json())

    def test_S02_single_snapshot_owner_and_missing(self):
        sid=self.session(self.staffa)
        self.assertEqual(self.client.get(f"/api/sessions/{sid}",headers=self.staffb).status_code,403)
        self.assertEqual(self.client.get("/api/sessions/nonexistent",headers=self.staffa).status_code,404)
        self.assertEqual(self.client.get(f"/api/sessions/{sid}").status_code,401)

    def test_S03_ai_preserves_exact_legal_building_type(self):
        from app.ai_guard import sanitize_extracted_info
        for source in (None,"Nhà hỗn hợp"):
            accepted=sanitize_extracted_info({"type":"Nhà hỗn hợp"},{"type":"Nhà ở riêng lẻ kết hợp kinh doanh"},source)["accepted"]
            self.assertEqual(accepted["type"],"Nhà hỗn hợp")
            result=evaluate_appraisal({**accepted,"floors":7,"totalFloorArea":700})
            self.assertEqual(result["appraisalBasis"]["status"],"required")

    def test_S04_factory_screenshot_does_not_use_residential_threshold(self):
        result=evaluate_appraisal({"type":"Nhà máy, nhà xưởng sản xuất","floors":1,"totalFloorArea":7200,"height":16,"fireRating":"Bậc IV"})
        self.assertEqual(result["appraisalBasis"]["status"],"insufficient_data")
        self.assertEqual(result["appraisalBasis"]["thresholds"],[])
        self.assertFalse(result["isSubjectToAppraisal"])

    def test_S13_history_does_not_turn_unknown_into_exemption(self):
        from app.db_models import InspectionLog
        for first,status in (("Cần xem xét","insufficient_data"),("Đạt","insufficient_data"),("Dưới ngưỡng danh mục","not_required"),("Thuộc diện thẩm định","required")):
            log=InspectionLog(id="log",session_id="A",owner_id="u",checklist_snapshot=[{"result":first}],warnings=[])
            self.assertEqual(log.to_dict()["appraisalStatus"],status)

    def test_S14_current_snapshot_ignores_old_ai_warnings(self):
        from app.db_models import ChatSession
        sid=self.session(self.staffa)
        async def inject():
            async with AsyncSessionLocal() as db:
                row=await db.get(ChatSession,sid)
                row.warnings=["OLD false karaoke conclusion"]
                row.checklist=[{"result":"Đạt","note":"old claim"}]
                await db.commit()
        asyncio.run(inject())
        payload=self.client.get(f"/api/sessions/{sid}",headers=self.staffa).json()
        self.assertNotIn("OLD false karaoke conclusion",payload["warnings"])
        self.assertEqual(payload["checklist"],[])
        self.assertEqual(payload["reviewState"],"draft")

    def test_S15_stale_tab_cannot_overwrite_or_delete(self):
        sid=self.session(self.staffa)
        original=self.client.get(f"/api/sessions/{sid}",headers=self.staffa).json()
        headers={**self.staffa,"If-Match":original["revision"]}
        saved=self.client.put(f"/api/sessions/{sid}/project",headers=headers,json={"floors":7})
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertNotEqual(saved.json()["revision"],original["revision"])
        stale=self.client.put(f"/api/sessions/{sid}/project",headers=headers,json={"floors":2})
        self.assertEqual(stale.status_code,412,stale.text)
        self.assertEqual(self.client.delete(f"/api/sessions/{sid}",headers=headers).status_code,412)
        self.assertEqual(self.client.get(f"/api/sessions/{sid}",headers=self.staffa).json()["projectInfo"]["floors"],7)

    def test_S16_stale_appraisal_chat_export_rejected_before_ai(self):
        sid=self.session(self.staffa)
        old=self.client.get(f"/api/sessions/{sid}",headers=self.staffa).json()["revision"]
        self.client.put(f"/api/sessions/{sid}/project",headers=self.staffa,json={"floors":8})
        headers={**self.staffa,"If-Match":old}
        with patch.object(main,"run_deep_llm_appraisal",AsyncMock()) as ai:
            self.assertEqual(self.client.put(f"/api/sessions/{sid}/project?appraise=true",headers=headers,json={}).status_code,412)
            self.assertEqual(self.client.post("/api/chat",headers=headers,json={"sessionId":sid,"messageText":"test"}).status_code,412)
            ai.assert_not_awaited()
        for endpoint in ("export","export-pdf","export-json"):
            self.assertEqual(self.client.post(f"/api/report/{endpoint}",headers=self.staffa,json={"sessionId":sid,"expectedRevision":old}).status_code,412)
        with patch.object(main,"extract_project_data_from_drawing",AsyncMock()) as ai:
            self.assertEqual(self.client.post("/api/ocr/extract-drawing",headers=headers,data={"session_id":sid,"apply_to_session":"true"},files={"file":("plan.png",png(),"image/png")}).status_code,412)
            ai.assert_not_awaited()

    def test_S17_production_requires_revision_after_authorization(self):
        sid=self.session(self.staffa)
        revision=self.client.get(f"/api/sessions/{sid}",headers=self.staffa).json()["revision"]
        with patch.object(main,"NODE_ENV","production"):
            self.assertEqual(self.client.put(f"/api/sessions/{sid}/project",headers=self.staffa,json={"floors":7}).status_code,428)
            self.assertEqual(self.client.post("/api/report/export-json",headers=self.staffa,json={"sessionId":sid}).status_code,428)
            self.assertEqual(self.client.put(f"/api/sessions/{sid}/project",headers=self.staffb,json={"floors":7}).status_code,403)
            self.assertEqual(self.client.put(f"/api/sessions/{sid}/project",headers={**self.staffa,"If-Match":revision},json={"floors":7}).status_code,200)
        self.assertEqual(self.client.put(f"/api/sessions/{sid}/project",headers={**self.staffa,"If-Match":"*"},json={"floors":7}).status_code,422)

    def test_S18_draft_create_save_read_chat_never_review(self):
        with patch.object(main,"evaluate_appraisal",side_effect=AssertionError("draft must not run rules")) as rules, patch.object(main,"run_deep_llm_appraisal",AsyncMock()) as ai:
            sid=self.session(reviewed=False)
            response=self.client.put(f"/api/sessions/{sid}/project",headers=self.staffa,json={"floors":7,"totalFloorArea":3000})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()["reviewState"],"draft")
            self.assertEqual(response.json()["checklist"],[])
            self.assertIsNone(response.json()["appraisalBasis"])
            self.assertIsNone(response.json()["isSubjectToAppraisal"])
            self.assertEqual(self.client.get(f"/api/sessions/{sid}",headers=self.staffa).status_code,200)
            self.assertEqual(self.client.get("/api/sessions",headers=self.staffa).status_code,200)
            r=self.client.post("/api/chat",headers=self.staffa,json={"sessionId":sid,"messageText":"Hãy thẩm định ngay"})
            self.assertEqual(r.status_code,200,r.text)
            self.assertIn("bản nháp",r.json()["reply"])
            self.assertEqual(self.client.post("/api/report/export-json",headers=self.staffa,json={"sessionId":sid}).status_code,409)
            ai.assert_not_awaited();rules.assert_not_called()

    def test_S19_explicit_review_missing_regulation_never_uses_ai_claim(self):
        sid=self.session(project={"type":"Nhà máy, nhà xưởng sản xuất","floors":1,"totalFloorArea":7200},reviewed=False)
        with patch.object(main,"run_deep_llm_appraisal",AsyncMock(return_value={"reply":"Đạt tất cả quy định", "checklist":[{"result":"Đạt"}]})) as ai:
            r=self.client.put(f"/api/sessions/{sid}/project?appraise=true",headers=self.staffa,json={})
            self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json()["reviewState"],"reviewed")
            self.assertIn("Không tìm thấy quy định phù hợp",r.json()["appraisalReason"])
            self.assertTrue(all(c["result"]=="Cần xem xét" for c in r.json()["checklist"]))
            self.assertNotIn("Đạt tất cả quy định",r.text)
            ai.assert_not_awaited()
        reply=self.client.post("/api/chat",headers=self.staffa,json={"sessionId":sid,"messageText":"Đường thoát nạn này rộng bao nhiêu thì đạt?"}).json()
        self.assertIn("Không tìm thấy quy định phù hợp",reply["reply"])

    def test_S20_edit_invalidates_review_and_export_until_clicked_again(self):
        sid=self.session()
        r=self.client.put(f"/api/sessions/{sid}/project",headers=self.staffa,json={"floors":7})
        self.assertEqual(r.json()["reviewState"],"draft")
        self.assertEqual(r.json()["checklist"],[])
        for endpoint in ("export","export-pdf","export-json"):
            self.assertEqual(self.client.post(f"/api/report/{endpoint}",headers=self.staffa,json={"sessionId":sid}).status_code,409)
        r=self.client.put(f"/api/sessions/{sid}/project?appraise=true",headers=self.staffa,json={})
        self.assertEqual(r.json()["reviewState"],"reviewed")
        self.assertEqual(r.json()["appraisalBasis"]["status"],"required")
        self.assertEqual(self.client.post("/api/report/export-json",headers=self.staffa,json={"sessionId":sid}).status_code,200)

    def test_S21_ocr_apply_is_draft_not_implicit_review(self):
        sid=self.session(reviewed=False)
        with patch.object(main,"evaluate_appraisal",side_effect=AssertionError("OCR must not review")), patch.object(main,"extract_project_data_from_drawing",AsyncMock(return_value={"floors":7})):
            r=self.client.post("/api/ocr/extract-drawing",headers=self.staffa,data={"session_id":sid,"apply_to_session":"true"},files={"file":("plan.png",png(),"image/png")})
            self.assertEqual(r.status_code,200,r.text)
            r=self.client.get(f"/api/sessions/{sid}",headers=self.staffa)
            self.assertEqual(r.json()["checklist"],[])
            self.assertEqual(r.json()["reviewState"],"draft")
        self.assertEqual(self.client.get(f"/api/sessions/{sid}/inspection-logs",headers=self.staffa).json(),[])

    def test_S26_ocr_zero_basements_clears_old_details_without_review(self):
        sid=self.session(project={"type":"Nhà hỗn hợp","floors":2,"floorArea":100,"totalFloorArea":200,"basements":1,"basementFunctions":["Bãi đỗ xe hầm"],"basementHeights":[3.3]},reviewed=False)
        with patch.object(main,"extract_project_data_from_drawing",AsyncMock(return_value={"basements":0})):
            r=self.client.post("/api/ocr/extract-drawing",headers=self.staffa,data={"session_id":sid,"apply_to_session":"true"},files={"file":("plan.png",png(),"image/png")})
            self.assertEqual(r.status_code,200,r.text)
        p=self.client.get(f"/api/sessions/{sid}",headers=self.staffa).json()
        self.assertEqual(p["projectInfo"]["basements"],0)
        self.assertEqual(p["projectInfo"]["basementFunctions"],[])
        self.assertEqual(p["projectInfo"]["basementHeights"],[])
        self.assertEqual(p["reviewState"],"draft")

    def test_S29_export_missing_regulation_has_no_fabricated_law_or_stage(self):
        sid=self.session(project={"type":"Nhà xưởng sản xuất","floors":1,"totalFloorArea":7200})
        r=self.client.post("/api/report/export",headers=self.staffa,json={"sessionId":sid})
        self.assertEqual(r.status_code,200,r.text[:100])
        doc=WordDocument(io.BytesIO(r.content))
        text=" ".join([p.text for p in doc.paragraphs]+[cell.text for table in doc.tables for row in table.rows for cell in row.cells])
        self.assertIn("Không tìm thấy quy định phù hợp",text)
        self.assertNotIn("Bộ luật PCCC",text)
        self.assertNotIn("Thiết kế cơ sở",text)
        r=self.client.post("/api/report/export-pdf",headers=self.staffa,json={"sessionId":sid})
        self.assertEqual(r.status_code,200,r.text[:100])
        self.assertIn("Không tìm thấy quy định phù hợp"," ".join(page.extract_text() for page in PdfReader(io.BytesIO(r.content)).pages))


if __name__ == "__main__":
    unittest.main(verbosity=2)
