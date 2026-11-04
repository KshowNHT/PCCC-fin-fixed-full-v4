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

TMP = tempfile.TemporaryDirectory(prefix="pccc-qa-", ignore_cleanup_errors=True)
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

    def test_S30_token_expiration_and_sliding_refresh_with_tab_grace(self):
        from app.auth import create_access_token, decode_access_token
        import time as _time
        login_res = self.client.post("/api/auth/login-json", json={"username": "staffa", "password": "StaffTest12345"})
        self.assertEqual(login_res.status_code, 200)
        tok1 = login_res.json()["access_token"]
        p1 = decode_access_token(tok1)
        self.assertIn("jti", p1)
        self.assertIn("sid", p1)
        self.assertIn("siat", p1)

        # 1. Token vừa hết hạn 60s (mô phỏng chuyển sang tab khác bị đóng băng timer rồi quay lại trong 5 phút ân hạn):
        # Gọi API trực tiếp bị chặn 401, nhưng gọi /api/auth/refresh được cứu phiên và cấp token mới cùng sid
        just_expired_tok = create_access_token(
            p1["sub"], p1["username"], p1["role"],
            session_id=p1["sid"], session_iat=p1["siat"], expires_minutes=-1,
        )
        # Bù đúng password fingerprint thật từ tok1
        import jwt as _jwt
        from app.config import JWT_SECRET, JWT_ALGORITHM
        raw_claims = _jwt.decode(just_expired_tok, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
        raw_claims["pwd"] = p1["pwd"]
        just_expired_tok = _jwt.encode(raw_claims, JWT_SECRET, algorithm=JWT_ALGORITHM)

        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + just_expired_tok}).status_code, 401)
        ref_res = self.client.post("/api/auth/refresh", headers={"Authorization": "Bearer " + just_expired_tok})
        self.assertEqual(ref_res.status_code, 200, ref_res.text)
        tok2 = ref_res.json()["access_token"]
        p2 = decode_access_token(tok2)
        self.assertEqual(p2["sid"], p1["sid"])
        self.assertEqual(p2["siat"], p1["siat"])
        self.assertNotEqual(p2["jti"], p1["jti"])
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + tok2}).status_code, 200)

        # 2. Token đã quá hạn vượt khỏi cả thời gian ân hạn (ví dụ hết hạn 20 phút trước) -> chặn 401 ở cả refresh
        long_expired_claims = dict(raw_claims, exp=int(_time.time()) - 1200)
        long_expired_tok = _jwt.encode(long_expired_claims, JWT_SECRET, algorithm=JWT_ALGORITHM)
        self.assertEqual(self.client.post("/api/auth/refresh", headers={"Authorization": "Bearer " + long_expired_tok}).status_code, 401)

        # 3. Token vượt quá tuổi thọ phiên tuyệt đối (JWT_ABSOLUTE_SESSION_MINUTES) -> chặn gia hạn vô tận
        ancient_session_claims = dict(p2, siat=int(_time.time()) - 86400 * 2, exp=int(_time.time()) + 1800)
        ancient_tok = _jwt.encode(ancient_session_claims, JWT_SECRET, algorithm=JWT_ALGORITHM)
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + ancient_tok}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/refresh", headers={"Authorization": "Bearer " + ancient_tok}).status_code, 401)

    def test_S31_logout_revokes_token_and_session_immediately(self):
        login_res = self.client.post("/api/auth/login-json", json={"username": "staffa", "password": "StaffTest12345"})
        tok1 = login_res.json()["access_token"]
        ref_res = self.client.post("/api/auth/refresh", headers={"Authorization": "Bearer " + tok1})
        self.assertEqual(ref_res.status_code, 200)
        tok2 = ref_res.json()["access_token"]

        # Đăng xuất bằng tok2 -> cả tok2 và tok1 (cùng phiên sid) đều bị thu hồi ngay lập tức
        out_res = self.client.post("/api/auth/logout", headers={"Authorization": "Bearer " + tok2})
        self.assertEqual(out_res.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + tok2}).status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + tok1}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/refresh", headers={"Authorization": "Bearer " + tok2}).status_code, 401)

    def test_S32_admin_lock_reset_and_delete_user(self):
        r = self.client.post("/api/auth/users", headers=self.admin, json={"username": "tempstaff", "password": "TempStaff12345", "full_name": "NV Tam"})
        self.assertEqual(r.status_code, 201, r.text)
        uid = r.json()["id"]
        tok = self.client.post("/api/auth/login-json", json={"username": "tempstaff", "password": "TempStaff12345"}).json()["access_token"]

        # Khoá tài khoản -> token đang sống lập tức bị chặn 401
        self.assertEqual(self.client.put(f"/api/auth/users/{uid}", headers=self.admin, json={"is_active": False}).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + tok}).status_code, 401)

        # Mở khoá + cấp lại mật khẩu mới -> mật khẩu mới đăng nhập thành công
        self.assertEqual(self.client.put(f"/api/auth/users/{uid}", headers=self.admin, json={"is_active": True, "new_password": "ResetStaff12345"}).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/login-json", json={"username": "tempstaff", "password": "ResetStaff12345"}).status_code, 200)

        # Xoá tài khoản -> giải phóng suất nhân viên
        self.assertEqual(self.client.delete(f"/api/auth/users/{uid}", headers=self.admin).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + tok}).status_code, 401)

    def test_S33_documents_search_and_inline_preview(self):
        # 1. Chặn truy cập chưa xác thực 401
        self.assertEqual(self.client.get("/api/documents/search?q=QCVN").status_code, 401)

        # 2. Tìm kiếm theo mã hiệu văn bản (cả admin và staff đều có quyền tra cứu)
        res_admin = self.client.get("/api/documents/search?q=QCVN", headers=self.admin)
        self.assertEqual(res_admin.status_code, 200)
        items = res_admin.json()
        self.assertGreater(len(items), 0)
        self.assertTrue(any("QCVN" in (d["code"] or "").upper() for d in items))

        res_staff = self.client.get("/api/documents/search?q=QCVN", headers=self.staffa)
        self.assertEqual(res_staff.status_code, 200)

        # 3. Tìm kiếm sâu trong nội dung văn bản (content search + snippet)
        first_doc = items[0]
        res_content = self.client.get("/api/documents/search?q=chữa cháy", headers=self.staffa)
        self.assertEqual(res_content.status_code, 200)
        content_items = res_content.json()
        self.assertGreater(len(content_items), 0)
        for d in content_items:
            self.assertIn("snippet", d)
            self.assertIn("matchType", d)
            self.assertIn("score", d)

        # 4. Xem trước PDF inline trực tiếp (cả 2 endpoint /preview và /download?inline=true)
        doc_id = first_doc["id"]
        prev_res = self.client.get(f"/api/documents/{doc_id}/preview", headers=self.staffa)
        self.assertEqual(prev_res.status_code, 200)
        self.assertIn("application/pdf", prev_res.headers.get("content-type", ""))
        self.assertIn("inline;", prev_res.headers.get("content-disposition", ""))

        inline_res = self.client.get(f"/api/documents/{doc_id}/download?format=pdf&inline=true", headers=self.staffa)
        self.assertEqual(inline_res.status_code, 200)
        self.assertIn("application/pdf", inline_res.headers.get("content-type", ""))
        self.assertIn("inline;", inline_res.headers.get("content-disposition", ""))

    def test_S34_hybrid_rag_citations_and_clickable_law_codes(self):
        # 1. Tạo session đã kiểm duyệt với công trình karaoke
        sid = self.session(project={"type": "Cơ sở kinh doanh karaoke, vũ trường", "floors": 4, "totalFloorArea": 600, "pcccHeight": 12}, reviewed=True)

        # 2. Gửi câu hỏi yêu cầu thẩm duyệt & trích dẫn quy chuẩn
        r = self.client.post("/api/chat", headers=self.staffa, json={
            "sessionId": sid,
            "messageText": "Công trình này có thuộc diện thẩm duyệt PCCC không? Hãy trích dẫn căn cứ luật."
        })
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("reply", data)
        self.assertIn("citations", data)
        self.assertGreater(len(data["citations"]), 0)

        # Kiểm tra trích dẫn văn bản luật thực tế trong response
        codes = [c["code"] for c in data["citations"]]
        self.assertTrue(any("105/2025" in c or "NĐ105" in c for c in codes))
        self.assertTrue(any("QCVN 06" in c for c in codes))
        self.assertTrue(any("147/2020" in c for c in codes))

        # Kiểm tra thẻ [Mã văn bản] xuất hiện trong câu trả lời văn bản
        reply_text = data["reply"]
        self.assertIn("[QCVN 06", reply_text)
        self.assertIn("[147/2020/TT-BCA]", reply_text)

    def test_S35_inspection_log_detail_expanded_with_basis_and_warnings(self):
        # Ngày 5: Kiểm tra lưu và mở rộng chi tiết log thẩm định (kết luận, căn cứ pháp lý, cảnh báo)
        sid = self.session(project={"type": "Nhà ở kết hợp kinh doanh", "floors": 4, "totalFloorArea": 400, "height": 14}, reviewed=True)
        r = self.client.get(f"/api/sessions/{sid}/inspection-logs", headers=self.staffa)
        self.assertEqual(r.status_code, 200, r.text)
        logs = r.json()
        self.assertGreater(len(logs), 0)
        first_log = logs[0]
        self.assertIn("appraisalReason", first_log)
        self.assertIn("checklist", first_log)
        self.assertIn("warnings", first_log)
        self.assertIn("appraisalBasis", first_log)

        # Kiểm tra API chi tiết theo ID
        log_id = first_log["id"]
        detail_r = self.client.get(f"/api/inspection-logs/{log_id}", headers=self.staffa)
        self.assertEqual(detail_r.status_code, 200, detail_r.text)
        detail = detail_r.json()
        self.assertEqual(detail["id"], log_id)
        self.assertIn("checklist", detail)
        self.assertIn("warnings", detail)

    def test_S36_multi_drawing_ocr_upload_up_to_5_files(self):
        # Ngày 6-7: Kiểm tra tải cùng lúc nhiều file bản vẽ (tối đa 5 file)
        sid = self.session()
        # 1. Thử gửi 6 file vượt giới hạn -> Phải nhận HTTP 400
        fake_files_6 = [("files", (f"drawing_{i}.png", png(), "image/png")) for i in range(6)]
        r_exceed = self.client.post("/api/ocr/extract-drawing", headers=self.staffa, data={"session_id": sid}, files=fake_files_6)
        self.assertEqual(r_exceed.status_code, 400)
        self.assertIn("tối đa 5 file", r_exceed.text)

        # 2. Thử gửi 2 file hợp lệ với mock OCR
        fake_files_2 = [
            ("files", ("ground_floor.png", png(), "image/png")),
            ("files", ("elevation_cut.png", png(), "image/png")),
        ]
        mock_result = {
            "name": "Nhà hỗn hợp PCCC",
            "type": "Nhà ở kết hợp kinh doanh",
            "floors": 4,
            "height": 14.5,
            "totalFloorArea": 500,
            "components": [{
                "id": "b1",
                "name": "Khối nhà A",
                "type": "Nhà hỗn hợp",
                "floors": 4,
                "height": 14.5,
                "totalFloorArea": 500,
                "floorArea": 125,
                "pcccHeight": 14.0,
                "sourcePages": [1, 2],
                "sourceText": "Quy mô 4 tầng, diện tích 500m2",
            }],
            "_ocrCoverage": {"filesRead": 2, "pagesRead": 2, "completePageCoverage": True}
        }
        with patch.object(main, "extract_project_data_from_multiple_drawings", AsyncMock(return_value=mock_result)):
            r_ok = self.client.post("/api/ocr/extract-drawing", headers=self.staffa, data={"session_id": sid}, files=fake_files_2)
            self.assertEqual(r_ok.status_code, 200, r_ok.text)
            resp = r_ok.json()
            self.assertIn("extractedProjectInfo", resp)
            self.assertEqual(resp["extractedProjectInfo"]["name"], "Nhà hỗn hợp PCCC")
            self.assertEqual(resp["extractedProjectInfo"]["components"][0]["floors"], 4)

    def test_S37_dynamic_16_technical_checklist_and_json_export(self):
        """Gói công việc 3: Chấm điểm động 16 hạng mục QCVN 06 theo chiều cao PCCC, số tầng, khối tích & xuất JSON."""
        sid = self.session()

        # 1. Công trình thấp tầng, khối tích nhỏ (3 tầng, cao PCCC 10.5m, khối tích 2.400m3, Bậc II)
        low_rise = {
            "name": "Trụ sở văn phòng 3 tầng",
            "type": "Trụ sở cơ quan, văn phòng làm việc",
            "floors": 3,
            "basements": 0,
            "pcccHeight": 10.5,
            "height": 11.2,
            "floorArea": 250,
            "totalFloorArea": 750,
            "volume": 2400,
            "fireRating": "Bậc II",
        }
        r_low = self.client.put(f"/api/sessions/{sid}/project?appraise=true", headers=self.staffa, json=low_rise)
        self.assertEqual(r_low.status_code, 200, r_low.text)
        cl_low = {c["stt"]: c for c in r_low.json()["checklist"]}
        self.assertEqual(len(cl_low), 17)
        # STT 2: Bậc II cho nhà 10.5m, 3 tầng, khối tích 2.400m3 -> Đạt
        self.assertEqual(cl_low[2]["result"], "Đạt")
        # STT 9: Báo cháy tự động trung tâm (3 tầng < 7, cao 10.5m < 25m, khối tích 2.400m3 < 5.000m3) -> Không bắt buộc
        self.assertEqual(cl_low[9]["result"], "Không bắt buộc")
        # STT 11: Khối tích 2.400 m3 (< 5.000 m3), cao 10.5m (<= 12m), 3 tầng (< 5 tầng) -> Đạt (dưới ngưỡng bắt buộc họng nước)
        self.assertEqual(cl_low[11]["result"], "Đạt")
        # STT 12: Cao 10.5m (< 25m), khối tích 2.400 m3 (< 15.000 m3) -> Sprinkler Không bắt buộc
        self.assertEqual(cl_low[12]["result"], "Không bắt buộc")
        # STT 15: Công trình dưới ngưỡng thẩm định và báo cháy tự động -> Thiết bị truyền tin Không bắt buộc
        self.assertEqual(cl_low[15]["result"], "Không bắt buộc")

        # 2. Công trình cao tầng, khối tích lớn nhưng bậc chịu lửa Bậc IV (12 tầng, cao PCCC 38m, khối tích 28.000m3, Bậc IV)
        high_rise = {
            "name": "Tòa nhà hỗn hợp 12 tầng",
            "type": "Nhà hỗn hợp",
            "floors": 12,
            "basements": 2,
            "pcccHeight": 38.0,
            "height": 40.5,
            "floorArea": 650,
            "totalFloorArea": 7800,
            "volume": 28000,
            "fireRating": "Bậc IV",
        }
        r_high = self.client.put(f"/api/sessions/{sid}/project?appraise=true", headers=self.staffa, json=high_rise)
        self.assertEqual(r_high.status_code, 200, r_high.text)
        cl_high = {c["stt"]: c for c in r_high.json()["checklist"]}
        self.assertEqual(cl_high[1]["result"], "Thuộc diện thẩm định")  # Phụ lục III: bắt buộc thẩm định
        # STT 2: Bậc IV cho nhà cao 38m, 12 tầng, khối tích 28.000m3 (yêu cầu Bậc I/II) -> Không đạt
        self.assertEqual(cl_high[2]["result"], "Không đạt")
        # STT 5: Cao 38m (> 28m, 12 tầng) bắt buộc buồng thang không nhiễm khói N1/N2/N3 -> Không đạt
        self.assertEqual(cl_high[5]["result"], "Không đạt")
        # STT 9: Báo cháy tự động trung tâm (12 tầng, cao 38m, khối tích 28.000m3) -> Không đạt (bắt buộc thiết kế)
        self.assertEqual(cl_high[9]["result"], "Không đạt")
        # STT 11: Khối tích 28.000m3 (>= 5.000m3), cao 38m (> 12m), 12 tầng -> Không đạt (bắt buộc họng nước trong nhà)
        self.assertEqual(cl_high[11]["result"], "Không đạt")
        # STT 12: Cao 38m (>= 25m), khối tích 28.000m3 (>= 15.000m3) -> Không đạt (bắt buộc Sprinkler)
        self.assertEqual(cl_high[12]["result"], "Không đạt")
        # STT 15: Thuộc diện thẩm định & báo cháy tự động -> Khuyến nghị mạnh (thiết bị truyền tin báo cháy)
        self.assertEqual(cl_high[15]["result"], "Khuyến nghị mạnh")

        # 3. Xuất đủ 3 định dạng báo cáo (Word, PDF, JSON) từ session thực tế, xác minh khối tích 28.000m3 có mặt
        r_json = self.client.post("/api/report/export-json", headers=self.staffa, json={"sessionId": sid})
        self.assertEqual(r_json.status_code, 200, r_json.text)
        self.assertIn("application/json", r_json.headers.get("content-type", ""))
        self.assertIn("attachment; filename=", r_json.headers.get("content-disposition", ""))
        payload = r_json.json()
        self.assertEqual(payload["projectInfo"]["volume"], 28000)
        self.assertEqual(payload["projectInfo"]["pcccHeight"], 38.0)
        self.assertEqual(len(payload["checklist"]), 17)
        self.assertEqual(payload["checklist"][1]["result"], "Không đạt")  # STT 2

        r_docx = self.client.post("/api/report/export", headers=self.staffa, json={"sessionId": sid})
        self.assertEqual(r_docx.status_code, 200)
        doc = WordDocument(io.BytesIO(r_docx.content))
        docx_text = " ".join(p.text for p in doc.paragraphs) + " " + " ".join(
            cell.text for table in doc.tables for row in table.rows for cell in row.cells
        )
        self.assertIn("28000", docx_text)

        r_pdf = self.client.post("/api/report/export-pdf", headers=self.staffa, json={"sessionId": sid})
        self.assertEqual(r_pdf.status_code, 200)
        pdf_text = " ".join(page.extract_text() for page in PdfReader(io.BytesIO(r_pdf.content)).pages)
        self.assertIn("28000", pdf_text)

        # 4. Nhà kho 1 tầng cao 18m (high-bay) chưa nhập volume (volume=0, totalFloorArea=1200m2)
        # -> Khối tích thực tế tính theo chiều cao 1200 * 18 = 21.600 m3 (>= 15.000 m3) -> Bắt buộc Họng nước (STT 11) & Sprinkler (STT 12)
        high_bay = {
            "name": "Nhà kho cao 18m",
            "type": "Nhà kho",
            "floors": 1,
            "basements": 0,
            "pcccHeight": 18.0,
            "floorArea": 1200,
            "totalFloorArea": 1200,
            "volume": 0,
            "hazardClass": "C",
            "fireRating": "Bậc II",
        }
        r_bay = self.client.put(f"/api/sessions/{sid}/project?appraise=true", headers=self.staffa, json=high_bay)
        self.assertEqual(r_bay.status_code, 200, r_bay.text)
        cl_bay = {c["stt"]: c for c in r_bay.json()["checklist"]}
        self.assertEqual(cl_bay[11]["result"], "Không đạt")
        self.assertIn("21.600 m³", cl_bay[11]["note"])
        self.assertEqual(cl_bay[12]["result"], "Không đạt")

        # 5. Công trình rỗng thông số quy mô (0 tầng, 0m, 0m3) chỉ chọn Bậc IV -> Không được chấm Đạt giả
        zero_scale = {
            "name": "Chưa nhập quy mô",
            "type": "Nhà hỗn hợp",
            "floors": 0,
            "basements": 0,
            "pcccHeight": 0,
            "height": 0,
            "floorArea": 0,
            "totalFloorArea": 0,
            "volume": 0,
            "fireRating": "Bậc IV",
        }
        r_zero = self.client.put(f"/api/sessions/{sid}/project?appraise=true", headers=self.staffa, json=zero_scale)
        self.assertEqual(r_zero.status_code, 200, r_zero.text)
        self.assertTrue(all(c["result"] == "Cần xem xét" for c in r_zero.json()["checklist"]))

    def test_S38_ai_health_monitoring_and_docker_1click_config(self):
        """Gói công việc 4: Giám sát trạng thái kết nối Gemini AI (/api/health/ai) & cấu hình Docker 1-Click + CI/CD."""
        from app import config, gemini_client

        # 1. Chặn truy cập chưa xác thực (401)
        self.assertEqual(self.client.get("/api/health/ai").status_code, 401)
        self.assertEqual(self.client.get("/api/health/ai/ping").status_code, 401)

        # 2. Phân quyền RBAC: Staff không được phép gọi ping trực tiếp (403)
        self.assertEqual(self.client.get("/api/health/ai?ping=true", headers=self.staffa).status_code, 403)
        self.assertEqual(self.client.get("/api/health/ai/ping", headers=self.staffa).status_code, 403)

        # 3. Trạng thái chưa cấu hình GEMINI_API_KEY
        with patch.object(config, "GEMINI_API_KEY", ""), patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            r_unconf = self.client.get("/api/health/ai", headers=self.admin)
            self.assertEqual(r_unconf.status_code, 200)
            self.assertFalse(r_unconf.json()["geminiApiKeyConfigured"])
            self.assertIn("Chưa cấu hình", r_unconf.json()["detail"])

            r_ping_unconf = self.client.get("/api/health/ai?ping=true", headers=self.admin)
            self.assertEqual(r_ping_unconf.status_code, 200)
            self.assertFalse(r_ping_unconf.json()["geminiApiKeyConfigured"])
            self.assertEqual(r_ping_unconf.json()["status"], "error")

        # 4. Trạng thái đã cấu hình GEMINI_API_KEY và Admin thực hiện Ping thành công / thất bại
        with patch.object(config, "GEMINI_API_KEY", "fake-gemini-key-for-qa"):
            r_conf = self.client.get("/api/health/ai", headers=self.admin)
            self.assertEqual(r_conf.status_code, 200)
            self.assertTrue(r_conf.json()["geminiApiKeyConfigured"])
            self.assertEqual(r_conf.json()["status"], "unknown")

            with patch.object(gemini_client, "generate_content_with_retry", AsyncMock(return_value=object())):
                r_ping_ok = self.client.get("/api/health/ai?ping=true", headers=self.admin)
                self.assertEqual(r_ping_ok.status_code, 200)
                self.assertTrue(r_ping_ok.json()["geminiApiKeyConfigured"])
                self.assertEqual(r_ping_ok.json()["status"], "ok")

                r_ping_route = self.client.get("/api/health/ai/ping", headers=self.admin)
                self.assertEqual(r_ping_route.status_code, 200)
                self.assertEqual(r_ping_route.json()["status"], "ok")

            with patch.object(
                gemini_client,
                "generate_content_with_retry",
                AsyncMock(side_effect=RuntimeError("API quota exceeded for key fake-gemini-key-for-qa")),
            ):
                r_ping_err = self.client.get("/api/health/ai?ping=true", headers=self.admin)
                self.assertEqual(r_ping_err.status_code, 200)
                self.assertTrue(r_ping_err.json()["geminiApiKeyConfigured"])
                self.assertEqual(r_ping_err.json()["status"], "error")
                self.assertIn("Không gọi được Gemini API", r_ping_err.json()["detail"])
                self.assertNotIn("fake-gemini-key-for-qa", r_ping_err.json()["detail"])

            with patch.object(gemini_client, "generate_content_with_retry", AsyncMock(side_effect=TimeoutError())):
                r_ping_timeout = self.client.get("/api/health/ai?ping=true", headers=self.admin)
                self.assertEqual(r_ping_timeout.status_code, 200)
                self.assertEqual(r_ping_timeout.json()["status"], "error")
                self.assertIn("Quá thời gian phản hồi", r_ping_timeout.json()["detail"])

            # Verify get_ai() dynamically picks up updated config.GEMINI_API_KEY
            with patch("app.gemini_client.genai.Client") as mock_genai_client:
                gemini_client.get_ai()
                mock_genai_client.assert_called_once()
                self.assertEqual(mock_genai_client.call_args.kwargs["api_key"], "fake-gemini-key-for-qa")

        # 5. Kiểm tra tồn tại và tính tương thích của compose.local.yaml, compose.yaml, run-docker.bat & CI/CD
        repo_root = Path(__file__).resolve().parents[2]
        compose_local = repo_root / "compose.local.yaml"
        compose_prod = repo_root / "compose.yaml"
        run_docker_bat = repo_root / "run-docker.bat"
        ci_workflow = repo_root / ".github" / "workflows" / "ci-cd.yml"

        self.assertTrue(compose_local.exists(), "compose.local.yaml must exist")
        self.assertTrue(compose_prod.exists(), "compose.yaml must exist")
        self.assertTrue(run_docker_bat.exists(), "run-docker.bat must exist")
        self.assertTrue(ci_workflow.exists(), ".github/workflows/ci-cd.yml must exist")

        local_text = compose_local.read_text(encoding="utf-8")
        self.assertIn("8000:3000", local_text)
        self.assertIn("5173:80", local_text)
        self.assertIn("postgres:16-alpine", local_text)
        self.assertNotIn("GEMINI_API_KEY:", local_text, "compose.local.yaml must not override backend/.env GEMINI_API_KEY in environment block")

        bat_text = run_docker_bat.read_text(encoding="utf-8")
        self.assertIn("compose.local.yaml", bat_text)
        self.assertIn("http://localhost:5173", bat_text)
        self.assertIn("http://localhost:8000", bat_text)
        self.assertNotIn('copy /Y ".env.example" ".env"', bat_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)


