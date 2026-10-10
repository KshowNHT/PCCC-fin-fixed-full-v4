"""Regression tests: separate buildings, current industrial law, explicit review.
OCR service is mocked: these tests do not certify Google recognition accuracy.
"""
from pathlib import Path
import asyncio
import copy
import io
import sys
import unittest
from unittest.mock import AsyncMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_operations_40 as operations
from test_operations_40 import main, png, WordDocument, PdfReader
from app.rules_engine import evaluate_appraisal
from app.schemas_project import ProjectUpdateRequest
from app.ocr_vision import _pdf_to_images, OCRInputError
from app.db import AsyncSessionLocal
from app.db_models import ChatSession
from reportlab.pdfgen import canvas


def house(name, kind, area=0, volume=0, grade='', floors=0, subtype=''):
    return {'id':name,'name':name,'type':kind,'totalFloorArea':area,'volume':volume,
            'hazardClass':grade,'floors':floors,'industrialSubtype':subtype}

SABACO = [house('Nhà kho','Nhà kho',0,30259.2,'C'),
          house('Kho thành phẩm','Nhà kho',0,59294.4,'C'),
          house('Nhà xưởng','Nhà máy, nhà xưởng sản xuất',0,98935.2,'C',subtype='other'),
          house('Nhà văn phòng','Văn phòng',540,0,'',0)]
for c, height, area, rating in zip(SABACO,[14.6,16,16,13.1],[2304,4312,7200,540],['Bậc IV','Bậc IV','Bậc IV','Bậc II']):
    c.update(height=height,floorArea=area,fireRating=rating,sourcePages=[1],sourceText=f"{c['name']}: cao {height} m; diện tích {area} m²; khối tích {c['volume']} m³")
# Hazard C and industrial subtype above are explicitly confirmed test input,
# not a claim that all buildings' grades were read from the real screenshot.

class ComponentTests(unittest.TestCase):
    setUpClass = classmethod(operations.Operations40.setUpClass.__func__)
    tearDownClass = classmethod(operations.Operations40.tearDownClass.__func__)
    setUp = operations.Operations40.setUp
    session = operations.Operations40.session

    def project(self, components=None, **kwargs):
        return {'components':copy.deepcopy(components or SABACO),'componentsComplete':True,
                'sharedSystems':False,'concurrentDesign':True,**kwargs}

    def test_M01_exact_factory_never_residential(self):
        r=evaluate_appraisal({'type':'Nhà máy, nhà xưởng sản xuất','floors':1,'totalFloorArea':7200})
        self.assertEqual(r['appraisalBasis']['category'],'factory')
        self.assertEqual(r['appraisalBasis']['thresholds'],[])
        self.assertNotIn('7 tầng',r['appraisalReason'])

    def test_M02_industrial_A_B_boundaries(self):
        for grade in ('A','B'):
            for area,volume,status in ((999,6999,'not_required'),(1000,0,'required'),(0,7000,'required'),(0,6999,'insufficient_data')):
                p=house('Xưởng','Nhà xưởng',area,volume,grade,subtype='other')
                self.assertEqual(evaluate_appraisal(p)['appraisalBasis']['status'],status)

    def test_M03_industrial_C_boundaries(self):
        for area,volume,status in ((1999,14999,'not_required'),(2000,0,'required'),(0,15000,'required'),(1999,0,'insufficient_data')):
            p=house('Xưởng','Nhà xưởng',area,volume,'C',subtype='other')
            self.assertEqual(evaluate_appraisal(p)['appraisalBasis']['status'],status)

    def test_M04_industrial_D_E_boundaries(self):
        for grade in ('D','E'):
            for area,volume,status in ((9999,29999,'not_required'),(10000,0,'required'),(0,30000,'required')):
                self.assertEqual(evaluate_appraisal(house('Xưởng','Nhà xưởng',area,volume,grade,subtype='other'))['appraisalBasis']['status'],status)

    def test_M05_unknown_hazard_and_special_never_guess(self):
        for grade,subtype in (('','other'),('C','special'),('C','')):
            r=evaluate_appraisal(house('Xưởng','Nhà xưởng',7200,98935.2,grade,subtype=subtype))
            self.assertEqual(r['appraisalBasis']['status'],'insufficient_data')
            self.assertIn('Không tìm thấy quy định phù hợp',r['appraisalReason'])

    def test_M06_no_sum_or_largest_row_as_house(self):
        p=self.project([house('Kho 1','Nhà kho',1200,10000,'C'),house('Kho 2','Nhà kho',1200,10000,'C')])
        r=evaluate_appraisal(p)
        self.assertEqual(r['appraisalBasis']['status'],'not_required')
        self.assertEqual(len(r['appraisalBasis']['componentResults']),2)
        self.assertEqual(r['appraisalBasis']['thresholds'],[])

    def test_M07_sabaco_four_separate_results(self):
        r=evaluate_appraisal(self.project())
        results=r['appraisalBasis']['componentResults']
        self.assertEqual([x['appraisalBasis']['category'] for x in results],['warehouse','warehouse','factory','office_hotel'])
        self.assertEqual([x['appraisalBasis']['status'] for x in results],['required','required','required','insufficient_data'])
        self.assertEqual(len(r['checklist']),69)
        self.assertEqual([c['stt'] for c in r['checklist']],list(range(1,70)))
        self.assertNotIn('7 tầng',results[2]['appraisalReason'])

    def test_M08_unconfirmed_inventory_no_exemption(self):
        p=self.project([house('Kho 1','Nhà kho',1200,10000,'C')],componentsComplete=False)
        self.assertEqual(evaluate_appraisal(p)['appraisalBasis']['status'],'insufficient_data')

    def test_M09_ocr_preview_keeps_all_no_write(self):
        sid=self.session(reviewed=False)
        with patch.object(main,'extract_project_data_from_drawing',AsyncMock(return_value=self.project())):
            r=self.client.post('/api/ocr/extract-drawing',headers=self.staffa,files={'file':('sabaco.png',png())},data={'session_id':sid})
        self.assertEqual(r.status_code,200,r.text)
        extracted=r.json()['extractedProjectInfo']
        self.assertEqual(len(extracted['components']),4)
        self.assertFalse(extracted['componentsComplete'])
        self.assertFalse(self.client.get(f'/api/sessions/{sid}',headers=self.staffa).json()['projectInfo'].get('components'))

    def test_M10_ocr_apply_preserves_each_building_remains_draft(self):
        sid=self.session()
        with patch.object(main,'extract_project_data_from_drawing',AsyncMock(return_value=self.project())), patch.object(main,'evaluate_appraisal',side_effect=AssertionError('no automatic review')):
            r=self.client.post('/api/ocr/extract-drawing',headers=self.staffa,files={'file':('sabaco.png',png())},data={'session_id':sid,'apply_to_session':'true'})
        self.assertEqual(r.status_code,200,r.text)
        stored=self.client.get(f'/api/sessions/{sid}',headers=self.staffa).json()
        self.assertEqual(len(stored['projectInfo']['components']),4)
        self.assertEqual(stored['reviewState'],'draft')
        self.assertEqual(stored['checklist'],[])

    def test_M11_invalid_component_atomic_rejection(self):
        sid=self.session(reviewed=False)
        before=self.client.get(f'/api/sessions/{sid}',headers=self.staffa).json()
        p=self.project();p['components'][2]['volume']=-1
        with patch.object(main,'extract_project_data_from_drawing',AsyncMock(return_value=p)):
            r=self.client.post('/api/ocr/extract-drawing',headers=self.staffa,files={'file':('sabaco.png',png())},data={'session_id':sid,'apply_to_session':'true'})
        self.assertEqual(r.status_code,422)
        self.assertEqual(self.client.get(f'/api/sessions/{sid}',headers=self.staffa).json()['revision'],before['revision'])

    def test_M12_revision_protects_building_edit(self):
        sid=self.session(project=self.project(),reviewed=False)
        revision=self.client.get(f'/api/sessions/{sid}',headers=self.staffa).json()['revision']
        p=self.project();p['components'][2]['volume']=5000
        self.assertEqual(self.client.put(f'/api/sessions/{sid}/project',headers={**self.staffa,'If-Match':revision},json=p).status_code,200)
        self.assertEqual(self.client.put(f'/api/sessions/{sid}/project',headers={**self.staffa,'If-Match':revision},json=self.project()).status_code,412)

    def test_M13_word_pdf_keep_all_buildings(self):
        sid=self.session(project=self.project(type="Nhà hỗn hợp",floors=77,totalFloorArea=777777))
        for route in ('export','export-pdf'):
            r=self.client.post('/api/report/'+route,headers=self.staffa,json={'sessionId':sid})
            self.assertEqual(r.status_code,200,r.text[:200] if r.status_code!=200 else '')
            if route=='export':
                doc=WordDocument(io.BytesIO(r.content))
                text=' '.join(p.text for p in doc.paragraphs)+' '.join(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
            else:
                text=' '.join(page.extract_text() for page in PdfReader(io.BytesIO(r.content)).pages)
            for c in SABACO:self.assertIn(c['name'],text)
            self.assertIn('347/2026',text)
            self.assertNotIn('777777',text)
            self.assertNotIn('777.777',text)
        exported=self.client.post('/api/report/export-json',headers=self.staffa,json={'sessionId':sid}).json()
        self.assertEqual(exported['projectInfo']['assessmentScope'],'components')
        self.assertEqual(exported['projectInfo']['totalFloorArea'],0)
        self.assertEqual(len(exported['conclusions']['appraisalBasis']['componentResults']),4)

    def test_M14_log_aggregate_when_first_below_second_required(self):
        p=self.project([house('Kho nhỏ','Nhà kho',1000,10000,'C'),house('Xưởng lớn','Nhà xưởng',7200,98935,'C',subtype='other')])
        sid=self.session(project=p)
        logs=self.client.get(f'/api/sessions/{sid}/inspection-logs',headers=self.staffa).json()
        self.assertEqual(logs[0]['appraisalStatus'],'required')

    def test_M15_obsolete_cached_law_becomes_draft(self):
        sid=self.session(project=self.project())
        async def obsolete():
            async with AsyncSessionLocal() as db:
                session=await db.get(ChatSession,sid)
                rows=copy.deepcopy(session.checklist)
                rows[0]['reviewedBasis']['rulesVersion']='v11-nd105-original-annexIII-2026-10-08'
                session.checklist=rows;await db.commit()
        asyncio.run(obsolete())
        result=self.client.get(f'/api/sessions/{sid}',headers=self.staffa).json()
        self.assertEqual(result['reviewState'],'draft')
        self.assertEqual(self.client.post('/api/report/export',headers=self.staffa,json={'sessionId':sid}).status_code,409)

    def test_M16_no_auto_review_components(self):
        with patch.object(main,'evaluate_appraisal',side_effect=AssertionError('no automatic review')):
            sid=self.session(project=self.project(),reviewed=False)
            self.assertEqual(self.client.put(f'/api/sessions/{sid}/project?appraise=false',headers=self.staffa,json=self.project()).status_code,200)
            self.assertEqual(self.client.get(f'/api/sessions/{sid}',headers=self.staffa).json()['checklist'],[])
            self.assertEqual(self.client.post('/api/chat',headers=self.staffa,json={'sessionId':sid,'messageText':'Rà soát các nhà này'}).status_code,200)

    def test_M17_long_pdf_rejected_no_page_silently_skipped(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            c=canvas.Canvas(f.name)
            for i in range(25):c.drawString(50,50,str(i));c.showPage()
            c.save()
            with patch('pdf2image.convert_from_path',side_effect=AssertionError('must reject before conversion')):
                with self.assertRaisesRegex(OCRInputError,'25 trang'):_pdf_to_images(f.name)

    def test_M18_summary_duplicate_and_invalid_classes_rejected(self):
        for components in ([house('Nhà có quy mô lớn nhất','Nhà kho')],[house('Kho','Nhà kho'),house('Kho','Nhà kho')],[house('X','Nhà xưởng',grade='F5.2')]):
            with self.assertRaises(ValueError):ProjectUpdateRequest.model_validate({'components':components})

    def test_M19_shared_system_scope_is_not_exempt(self):
        p=self.project([house('Kho nhỏ','Nhà kho',1000,10000,'C'),house('Xưởng lớn','Nhà xưởng',7200,98935,'C',subtype='other')],sharedSystems=True)
        r=evaluate_appraisal(p)
        first=r['appraisalBasis']['componentResults'][0]
        self.assertEqual(first['appraisalBasis']['status'],'not_required')
        self.assertEqual(first['sharedSystemScope']['status'],'required')
        self.assertIn('hệ thống dùng chung',r['appraisalReason'])

    def test_M20_real_ocr_contract_rejects_flat_or_missing_sources(self):
        from app import ocr_vision
        bad=[{'type':'Nhà xưởng','floorArea':7200}, {'components':[house('X','Nhà xưởng',7200)]}]
        for data in bad:
            with patch.object(ocr_vision,'_load_images_from_upload',return_value=[png()]), patch.object(ocr_vision,'_call_vision_model',AsyncMock(return_value=data)):
                with self.assertRaises(OCRInputError):asyncio.run(ocr_vision.extract_project_data_from_drawing('unused.png'))

    def test_M21_real_ocr_contract_retains_four_sources(self):
        from app import ocr_vision
        with patch.object(ocr_vision,'_load_images_from_upload',return_value=[png()]), patch.object(ocr_vision,'_call_vision_model',AsyncMock(return_value={'components':copy.deepcopy(SABACO)})):
            data=asyncio.run(ocr_vision.extract_project_data_from_drawing('unused.png'))
        self.assertEqual(len(data['components']),4)
        self.assertTrue(data['_ocrCoverage']['completePageCoverage'])
        self.assertEqual(data['components'][2]['volume'],98935.2)

if __name__=='__main__':unittest.main(verbosity=2)
