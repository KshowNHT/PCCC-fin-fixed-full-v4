"""Acceptance Test Suite for Backend Upgrades BM-01 through BM-05.
Hỗ trợ tương thích cả pytest và unittest CI/CD runner:
- pytest backend/tests/test_backend_upgrades.py -v
- python -m unittest discover -s backend/tests -p "test_*.py" -v
"""
import asyncio
import io
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_operations_40 as operations
from test_operations_40 import main, png

from app.auth import _REVOKED_JTIS, _REVOKED_SIDS
from app.db_models import Document, RevokedToken
from app.routers.ocr import OCR_SEMAPHORE
from app.services.document_parser import (
    LegalChunk,
    chunk_legal_document,
    find_best_legal_article,
)
from app.services.rag_service import SimpleTTLCache, rag_query_cache
from app.utils_file import _extract_rich_context


class TestBackendUpgrades(operations.Operations40):
    """Test suite nghiệm thu toàn diện 5 hạng mục nâng cấp BM-01 -> BM-05."""

    def test_bm01_rag_query_cache(self) -> None:
        """BM-01: Triển khai SimpleTTLCache cho Chatbot RAG, phản hồi < 0.05s."""
        # 1. Ghi dữ liệu mẫu vào rag_query_cache
        sample_query = "Nhà ở kết hợp kinh doanh có cần thẩm duyệt PCCC không?"
        sample_data = {
            "reply": "Theo NĐ 105/2025/NĐ-CP, nhà ở kết hợp kinh doanh cao từ 7 tầng hoặc diện tích từ 3.000 m² thuộc diện thẩm duyệt.",
            "citations": [{"code": "NĐ105/2025/NĐ-CP", "title": "Nghị định 105/2025"}],
        }
        rag_query_cache.set(sample_query, sample_data)

        # 2. Đọc lại từ cache với câu hỏi có định dạng viết hoa và khoảng trắng khác nhau
        varied_query = "  NHÀ Ở KẾT HỢP   KINH DOANH CÓ CẦN THẨM DUYỆT PCCC KHÔNG?  "
        start_time = time.perf_counter()
        cached_result = rag_query_cache.get(varied_query)
        elapsed = time.perf_counter() - start_time

        # 3. Khẳng định: thời gian tra cứu < 0.05s và nội dung khớp 100%
        self.assertIsNotNone(cached_result, "Query cache phải tìm thấy kết quả sau khi chuẩn hóa")
        self.assertLess(elapsed, 0.05, f"Thời gian đọc cache ({elapsed:.5f}s) vượt ngưỡng 0.05 giây")
        self.assertEqual(cached_result["reply"], sample_data["reply"])
        self.assertEqual(len(cached_result["citations"]), 1)

        # 4. Kiểm tra cơ chế tự động dọn rác khi cache đầy (maxsize và evict 200)
        small_cache = SimpleTTLCache(maxsize=10, ttl_seconds=60)
        for i in range(10):
            small_cache.set(f"query_{i}", f"answer_{i}")
        self.assertEqual(len(small_cache), 10)

        # Thêm mục thứ 11 -> kích hoạt dọn rác
        small_cache.set("query_overflow", "answer_overflow")
        self.assertLessEqual(len(small_cache), 10)
        self.assertEqual(small_cache.get("query_overflow"), "answer_overflow")

        # 5. Kiểm tra hết hạn TTL
        expired_cache = SimpleTTLCache(maxsize=10, ttl_seconds=0.01)
        expired_cache.set("quick_query", "quick_answer")
        time.sleep(0.02)
        self.assertIsNone(expired_cache.get("quick_query"), "Entry quá hạn TTL phải tự hủy và trả về None")

        # Dọn dẹp
        rag_query_cache.clear()

    def test_bm02_document_deduplication(self) -> None:
        """BM-02: Khử trùng lặp tại tầng DB khi Upload tài liệu (In-place Upgrade)."""
        doc_code = "QCVN 99:2026/TEST"
        content_v1 = b"Noi dung goc cua Quy chuan QCVN 99 ban hanh nam 2026."
        content_v2 = b"Noi dung CAP NHAT sua doi bo sung cua Quy chuan QCVN 99."

        # 1. Tải lên lần 1 (Tạo mới -> 201 Created)
        files_v1 = {"file": ("qcvn99_v1.txt", content_v1, "text/plain")}
        data_v1 = {"code": doc_code, "title": "Quy chuẩn PCCC Kiểm thử v1", "type": "QCVN"}
        resp1 = self.client.post("/api/documents/upload", headers=self.admin, files=files_v1, data=data_v1)
        self.assertEqual(resp1.status_code, 201, f"Lần upload đầu tiên phải trả về 201 Created: {resp1.text}")
        doc1 = resp1.json()
        doc1_id = doc1.get("id")
        self.assertTrue(doc1_id)
        self.assertEqual(doc1.get("title"), "Quy chuẩn PCCC Kiểm thử v1")

        # Đặt 1 item vào cache để kiểm tra việc xóa cache RAG
        rag_query_cache.set("test_dedup_cache", {"data": "cached"})
        self.assertGreater(len(rag_query_cache), 0)

        # 2. Tải lên lần 2 với mã hiệu trùng nhưng khác hoa thường ("qcvn 99:2026/test") -> 200 OK
        files_v2 = {"file": ("qcvn99_v2.txt", content_v2, "text/plain")}
        data_v2 = {"code": doc_code.lower(), "title": "Quy chuẩn PCCC Kiểm thử v2 (Đã Cập Nhật)", "type": "QCVN"}
        resp2 = self.client.post("/api/documents/upload", headers=self.admin, files=files_v2, data=data_v2)
        self.assertEqual(resp2.status_code, 200, f"Ghi đè nâng cấp tài liệu phải trả về 200 OK: {resp2.text}")
        doc2 = resp2.json()

        # 3. Khẳng định: ID bản ghi giữ nguyên (in-place upgrade) và tiêu đề đã được cập nhật
        self.assertEqual(doc2.get("id"), doc1_id, "In-place upgrade phải cập nhật trực tiếp trên ID bản ghi cũ")
        self.assertEqual(doc2.get("title"), "Quy chuẩn PCCC Kiểm thử v2 (Đã Cập Nhật)")

        # 4. Kiểm tra trong cơ sở dữ liệu: chỉ tồn tại duy nhất 1 bản ghi có mã hiệu này
        list_resp = self.client.get("/api/documents?full=true", headers=self.admin)
        self.assertEqual(list_resp.status_code, 200)
        matching_docs = [d for d in list_resp.json() if d.get("code", "").upper() == doc_code.upper()]
        self.assertEqual(len(matching_docs), 1, "Cơ sở dữ liệu chỉ được phép chứa duy nhất 1 bản ghi cho mã hiệu này")

        # 5. Khẳng định cache RAG đã được xóa sạch sau khi upload
        self.assertEqual(len(rag_query_cache), 0, "Upload tài liệu mới phải xóa cache RAG để cập nhật tri thức")

        # 6. Kiểm tra in-place update qua form data không kèm file (giữ 200 OK và không trùng lặp)
        resp3 = self.client.post(
            "/api/documents/upload",
            headers=self.admin,
            data={"code": doc_code, "title": "Quy chuẩn v3 (Form Text)", "content": "Noi dung form text."},
        )
        self.assertEqual(resp3.status_code, 200, f"Cập nhật bằng form content phải trả về 200 OK: {resp3.text}")
        self.assertEqual(resp3.json().get("id"), doc1_id)

        # Dọn dẹp tài liệu test
        del_resp = self.client.delete(f"/api/documents/{doc1_id}", headers=self.admin)
        self.assertEqual(del_resp.status_code, 200)

    def test_bm03_token_revocation_persistence(self) -> None:
        """BM-03: Quản lý thu hồi phiên Token bền vững qua Database PostgreSQL/SQLite."""
        # 1. Đăng nhập tài khoản cán bộ staffa lấy token
        login_resp = self.client.post(
            "/api/auth/login-json",
            json={"username": "staffa", "password": "StaffTest12345"},
        )
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.json().get("access_token")
        self.assertTrue(token)
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Kiểm tra token hoạt động bình thường
        me_resp1 = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(me_resp1.status_code, 200)
        self.assertEqual(me_resp1.json().get("username"), "staffa")

        # 3. Đăng xuất tài khoản
        logout_resp = self.client.post("/api/auth/logout", headers=headers)
        self.assertEqual(logout_resp.status_code, 200)

        # 4. Xóa sạch RAM cache _REVOKED_JTIS và _REVOKED_SIDS (mô phỏng restart tiến trình server hoặc multi-workers)
        _REVOKED_JTIS.clear()
        _REVOKED_SIDS.clear()
        self.assertEqual(len(_REVOKED_JTIS), 0)
        self.assertEqual(len(_REVOKED_SIDS), 0)

        # 5. Dùng lại token gọi /api/auth/me: Khẳng định bị chặn 401 Unauthorized nhờ bản ghi trong bảng revoked_tokens
        me_resp2 = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(
            me_resp2.status_code,
            401,
            f"Token đã logout phải bị từ chối 401 Unauthorized ngay cả khi đã xóa RAM cache: {me_resp2.text}",
        )
        self.assertIn("đăng xuất", me_resp2.json().get("detail", "").lower())

        # 6. Khẳng định token bị thu hồi được tự động đồng bộ lại vào L1 RAM cache
        self.assertGreater(len(_REVOKED_JTIS), 0, "Token thu hồi từ DB phải được nạp lại vào L1 RAM cache")

        # 7. Kiểm tra trường hợp một session có nhiều token bị thu hồi trong DB không làm sập MultipleResultsFound
        login2 = self.client.post("/api/auth/login-json", json={"username": "staffa", "password": "StaffTest12345"})
        tok2 = login2.json().get("access_token")
        h2 = {"Authorization": f"Bearer {tok2}"}
        # Refresh để tạo token thứ hai cùng session_id
        ref_resp = self.client.post("/api/auth/refresh", headers=h2)
        self.assertEqual(ref_resp.status_code, 200)
        tok3 = ref_resp.json().get("access_token")
        h3 = {"Authorization": f"Bearer {tok3}"}
        # Logout cả 2 token để tạo 2 bản ghi trùng sid trong revoked_tokens
        self.client.post("/api/auth/logout", headers=h2)
        self.client.post("/api/auth/logout", headers=h3)
        # Xóa RAM cache để buộc kiểm tra DB
        _REVOKED_JTIS.clear()
        _REVOKED_SIDS.clear()
        # Gọi lại /me với h2 -> phải trả về 401 chứ không phải 500 lỗi MultipleResultsFound
        check_mult = self.client.get("/api/auth/me", headers=h2)
        self.assertEqual(check_mult.status_code, 401)

        # 8. Gọi lại /refresh với h2 khi đã xóa RAM cache -> phải trả về 401 (không bị NameError crash 500)
        _REVOKED_JTIS.clear()
        _REVOKED_SIDS.clear()
        check_ref = self.client.post("/api/auth/refresh", headers=h2)
        self.assertEqual(check_ref.status_code, 401)
        self.assertIn("đăng xuất", check_ref.json().get("detail", "").lower())

    def test_bm04_semantic_chunking_articles(self) -> None:
        """BM-04: Phân đoạn Tri thức theo Chương -> Mục -> Điều -> Khoản (Semantic Chunking)."""
        # Tạo văn bản quy chuẩn mô phỏng với đầy đủ cấu trúc và Điều luật dài > 2.500 ký tự
        long_technical_body = (
            "1. Khoảng cách an toàn PCCC giữa các nhà và công trình phải bảo đảm ngăn cháy lan.\n"
            "2. Chiều rộng thông thủy của lối thoát nạn không được nhỏ hơn 1,0 m; cửa thoát nạn không nhỏ hơn 0,8 m.\n"
            "3. Bảng tra cứu số lượng lối thoát nạn tối thiểu:\n"
            + ("- Bậc chịu lửa I, II: Cho phép khoảng cách di chuyển tối đa 40 m.\n" * 20)
            + "4. Ngoại lệ kỹ thuật PCCC đặc thù:\n"
            + ("- Đối với công trình có hệ thống chữa cháy tự động Sprinkler toàn bộ, khoảng cách được tăng thêm 25%.\n" * 15)
        )
        # Đảm bảo nội dung dài > 2.500 ký tự
        self.assertGreater(len(long_technical_body), 2500)

        sample_law = f"""Chương I. QUY ĐỊNH CHUNG
Điều 1. Phạm vi điều chỉnh
Quy chuẩn này quy định các yêu cầu kỹ thuật an toàn PCCC cho nhà và công trình.

Điều 2. Đối tượng áp dụng
Áp dụng đối với mọi cơ quan, tổ chức, cá nhân tham gia hoạt động xây dựng trên lãnh thổ Việt Nam.

Chương II. QUY ĐỊNH KỸ THUẬT
Mục 1. Giải pháp thoát nạn cho công trình
Điều 5. Lối thoát nạn và đường thoát nạn
{long_technical_body}

Phụ lục A. Bảng thông số kỹ thuật bổ sung
Bảng A.1 quy định về giới hạn chịu lửa tối thiểu của cấu kiện.
"""

        # 1. Kiểm tra chunk_legal_document
        chunks = chunk_legal_document("QCVN 06:2022/BXD", "An toàn cháy nhà", sample_law)
        self.assertGreaterEqual(len(chunks), 4, "Phải bóc tách được ít nhất 4 chunk (Điều 1, 2, 5 và Phụ lục A)")

        # Tìm chunk Điều 5
        art5 = next((c for c in chunks if "Điều 5" in c.article), None)
        self.assertIsNotNone(art5, "Phải tìm thấy LegalChunk cho Điều 5")
        assert art5 is not None
        self.assertEqual(art5.chapter, "Chương II. QUY ĐỊNH KỸ THUẬT")
        self.assertIn("Lối thoát nạn", art5.title)
        self.assertGreater(
            len(art5.full_text),
            2500,
            "LegalChunk phải lưu trọn vẹn toàn bộ Điều 5 (> 2.500 ký tự) không bị cắt xén",
        )

        # 2. Kiểm tra find_best_legal_article theo truy vấn số Điều cụ thể
        found_by_num = find_best_legal_article(sample_law, "Quy định tại Điều 5 về đường thoát nạn")
        self.assertIsNotNone(found_by_num)
        assert found_by_num is not None
        self.assertIn("Điều 5", found_by_num.article)

        # 3. Kiểm tra find_best_legal_article theo từ khóa ngữ nghĩa tiêu đề
        found_by_topic = find_best_legal_article(sample_law, "tiêu chuẩn lối thoát nạn và đường thoát nạn")
        self.assertIsNotNone(found_by_topic)
        assert found_by_topic is not None
        self.assertIn("Điều 5", found_by_topic.article)

        # 4. Kiểm tra _extract_rich_context tích hợp bóc tách trọn vẹn Điều luật (> 2.500 ký tự)
        rich_context = _extract_rich_context(sample_law, "Điều 5", max_chars=2500, doc_code="QCVN 06:2022/BXD")
        self.assertGreater(
            len(rich_context),
            2500,
            "BM-04 yêu cầu trích xuất toàn vẹn Điều 5 (> 2.500 ký tự) để giữ nguyên ngoại lệ kỹ thuật",
        )
        self.assertIn("Điều 5. Lối thoát nạn và đường thoát nạn", rich_context)
        self.assertIn("Ngoại lệ kỹ thuật PCCC đặc thù", rich_context)

        # 5. Kiểm tra không nhận diện nhầm thông số đường kính ống kỹ thuật (d 65) thành Điều luật
        found_pipe = find_best_legal_article(sample_law, "Họng nước vách tường dùng đường kính d 65")
        self.assertTrue(
            found_pipe is None or "65" not in found_pipe.article,
            "d 65 là thông số đường kính ống, không được nhận nhầm thành Điều 65",
        )

        # 6. Kiểm tra tìm kiếm theo số hiệu Bảng kỹ thuật
        found_tab = find_best_legal_article(sample_law, "Tra cứu Bảng A.1 về giới hạn chịu lửa")
        self.assertIsNotNone(found_tab, "Phải tìm thấy chunk chứa Bảng A.1")
        assert found_tab is not None
        self.assertIn("Bảng A.1", found_tab.full_text)

        # 7. Kiểm tra Điều luật chứa Bảng nhúng không bị cắt xén ngoại lệ kỹ thuật
        sample_law_embedded_table = """Điều 10. Khoảng cách an toàn PCCC
1. Yêu cầu chung về khoảng cách ngăn cháy.
Bảng 2. Khoảng cách an toàn tối thiểu theo bậc chịu lửa
- Bậc I, II: 6m.
- Bậc III: 8m.
2. Ngoại lệ kỹ thuật PCCC:
Trường hợp tường đối diện là tường ngăn cháy loại 1 thì không yêu cầu khoảng cách.

Điều 11. Bậc chịu lửa công trình
Quy định bậc chịu lửa.
"""
        chunks_tab = chunk_legal_document("TCVN 2622:1995", "PCCC", sample_law_embedded_table)
        art10 = next((c for c in chunks_tab if "Điều 10" in c.article), None)
        self.assertIsNotNone(art10, "Điều 10 phải được trích xuất")
        assert art10 is not None
        self.assertIn("Bảng 2", art10.full_text, "Điều 10 phải chứa Bảng 2 nhúng bên trong")
        self.assertIn("Ngoại lệ kỹ thuật PCCC", art10.full_text, "Điều 10 không được bị cắt đứt sau Bảng 2")

        # Kiểm tra _extract_rich_context trích xuất trọn vẹn Điều 10
        ctx10 = _extract_rich_context(sample_law_embedded_table, "Điều 10", doc_code="TCVN 2622:1995")
        self.assertIn("Ngoại lệ kỹ thuật PCCC", ctx10)
        self.assertIn("tường ngăn cháy loại 1", ctx10)

        # Kiểm tra tra cứu Phụ lục A trả về đầy đủ bảng biểu trong Phụ lục
        ctx_app = _extract_rich_context(sample_law, "Quy định tại Phụ lục A", doc_code="QCVN 06:2022/BXD")
        self.assertIn("Phụ lục A", ctx_app)
        self.assertIn("Bảng A.1", ctx_app)

    def test_bm05_ocr_semaphore_and_limiter(self) -> None:
        """BM-05: Khóa Semaphore(3) giới hạn 3 tác vụ OCR song song & Rate Limit 5/phút."""
        # 1. Kiểm tra cấu hình Semaphore(3)
        self.assertEqual(OCR_SEMAPHORE._value, 3, "OCR_SEMAPHORE phải có hạn mức 3 tác vụ đồng thời")

        # 2. Kiểm tra Semaphore bảo vệ khi nhiều coroutine cùng chạy
        async def mock_worker():
            async with OCR_SEMAPHORE:
                await asyncio.sleep(0.01)
                return True

        async def run_concurrent():
            tasks = [asyncio.create_task(mock_worker()) for _ in range(5)]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(run_concurrent())
        self.assertEqual(len(results), 5)
        self.assertEqual(OCR_SEMAPHORE._value, 3, "Sau khi hoàn thành, Semaphore phải trả về giá trị ban đầu là 3")

        # 3. Kiểm tra Rate Limit 5 requests/phút cho endpoint /api/ocr/extract-drawing
        main.limiter.reset()

        dummy_png = png()
        with patch.object(main, "extract_project_data_from_drawing", AsyncMock(return_value={"floors": 3})):
            # Gửi liên tiếp 5 requests đầu tiên -> tất cả phải thành công (200 OK)
            for i in range(5):
                resp = self.client.post(
                    "/api/ocr/extract-drawing",
                    headers=self.staffa,
                    files={"file": (f"drawing_{i}.png", dummy_png, "image/png")},
                )
                self.assertEqual(
                    resp.status_code,
                    200,
                    f"Request thứ {i+1} trong hạn mức 5/phút phải thành công: {resp.text}",
                )

            # Gửi request thứ 6 trong cùng 1 phút -> khẳng định bị chặn HTTP 429 Too Many Requests
            resp_6 = self.client.post(
                "/api/ocr/extract-drawing",
                headers=self.staffa,
                files={"file": ("drawing_overflow.png", dummy_png, "image/png")},
            )
            self.assertEqual(
                resp_6.status_code,
                429,
                f"Request thứ 6 phải bị Rate Limit 5/phút chặn với HTTP 429: {resp_6.status_code}",
            )
            main.limiter.reset()


if __name__ == "__main__":
    unittest.main()
