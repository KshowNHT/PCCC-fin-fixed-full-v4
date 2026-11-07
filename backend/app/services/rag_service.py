"""Hybrid RAG Service for PCCC Legal Knowledge Base & Deterministic Rules Engine."""
import logging
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import ChatSession, Document
from app.utils_file import _extract_rich_context, _extract_snippet, strip_vietnamese_accents

logger = logging.getLogger("pccc.service.rag")


async def search_citations_for_project_and_query(
    db: AsyncSession,
    message_text: str,
    project_info: Dict[str, Any],
    basis: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Tra cứu các văn bản luật liên quan trực tiếp đến câu hỏi và hồ sơ công trình (Hybrid RAG)."""
    p_type = str(project_info.get("type") or "").lower()
    q_lower = message_text.lower()
    norm_q = re.sub(r"[\s_\-:/]+", " ", q_lower).strip()
    stripped_q = strip_vietnamese_accents(q_lower)
    stripped_norm_q = re.sub(r"[\s_\-:/]+", " ", stripped_q).strip()

    # Xác định các mã văn bản ưu tiên theo ngữ cảnh
    target_codes: List[str] = []

    # 1. Văn bản thẩm duyệt & an toàn cháy chung
    target_codes.append("NĐ105/2025/NĐ-CP")
    target_codes.append("QCVN 06:2022/BXD (Sửa đổi 01-2023)")

    # 2. Đặc thù công năng (bao phủ toàn bộ 14 nhóm loại hình công trình theo NĐ 105/2025 & QCVN 06:2022)
    combined_ctx = f"{p_type} {q_lower}"
    combined_stripped = f"{strip_vietnamese_accents(p_type)} {stripped_q}"

    if any(k in combined_ctx or k in combined_stripped for k in ["karaoke", "vu truong", "vũ trường", "bar", "club"]):
        target_codes.append("147/2020/TT-BCA")
        target_codes.append("QCVN 10:2025/BCA")
    if any(k in combined_ctx or k in combined_stripped for k in ["xang dau", "xăng dầu", "khi dot", "khí đốt", "lpg", "tram bien ap", "trạm biến áp"]):
        target_codes.append("QCVN 01:2020/BCT")
        target_codes.append("TCVN 9385:2012")
    if any(k in combined_ctx or k in combined_stripped for k in ["gara", "xe o to", "bai do xe", "nha de xe", "xe ô tô", "bãi đỗ xe", "nhà để xe"]):
        target_codes.append("QCVN 13:2018/BXD")
        target_codes.append("TCVN 5687:2024")
        target_codes.append("TCVN 7336:2021")
    if any(k in combined_ctx or k in combined_stripped for k in ["cho", "trung tam thuong mai", "sieu thi", "cua hang", "nha hang", "chợ", "trung tâm thương mại", "siêu thị", "cửa hàng", "nhà hàng"]):
        target_codes.append("TCVN 6161:1996")
        target_codes.append("QCVN 10:2025/BCA")
        target_codes.append("TCVN 7336:2021")
    if any(k in combined_ctx or k in combined_stripped for k in ["kho", "gia do", "ke cao", "giá đỡ", "kệ cao"]):
        target_codes.append("TCVN 14496:2025")
        target_codes.append("QCVN 10:2025/BCA")
        target_codes.append("TCVN 7336:2021")
    if any(k in combined_ctx or k in combined_stripped for k in ["nha may", "nha xuong", "san xuat", "xi nghiep", "khu cong nghiep", "nhà máy", "nhà xưởng", "sản xuất"]):
        target_codes.append("QCVN 10:2025/BCA")
        target_codes.append("TCVN 2622:1995")
        target_codes.append("TCVN 7336:2021")
        target_codes.append("TCVN 9385:2012")
    if any(k in combined_ctx or k in combined_stripped for k in ["truong hoc", "giao duc", "mam non", "nha tre", "tieu hoc", "trung hoc", "dai hoc", "cao dang", "trường học", "giáo dục", "mầm non"]):
        target_codes.append("QCVN 10:2025/BCA")
        target_codes.append("TCVN 2622:1995")
        target_codes.append("TCVN 13456:2022")
    if any(k in combined_ctx or k in combined_stripped for k in ["benh vien", "y te", "phong kham", "dieu duong", "bệnh viện", "y tế", "phòng khám"]):
        target_codes.append("QCVN 10:2025/BCA")
        target_codes.append("TCVN 7336:2021")
        target_codes.append("TCVN 5687:2024")
    if any(k in combined_ctx or k in combined_stripped for k in ["rap hat", "hoi truong", "su kien", "rap chieu phim", "nha van hoa", "san van dong", "nha thi dau", "rạp hát", "hội trường", "sự kiện"]):
        target_codes.append("QCVN 10:2025/BCA")
        target_codes.append("TCVN 2622:1995")
        target_codes.append("TCVN 5687:2024")
        target_codes.append("TCVN 7336:2021")
    if any(k in combined_ctx or k in combined_stripped for k in ["nha hon hop", "hon hop", "chung cu", "khach san", "van phong", "nha nghi", "nha tro", "ky tuc xa", "tru so", "cong so", "nhà hỗn hợp", "chung cư", "khách sạn", "văn phòng"]):
        target_codes.append("QCVN 10:2025/BCA")
        target_codes.append("TCVN 7336:2021")
        target_codes.append("TCVN 7568-14:2025")
        target_codes.append("TCVN 5687:2024")
    if any(k in combined_ctx or k in combined_stripped for k in ["nha o rieng le", "ket hop kinh doanh", "shophouse", "nha pho", "biet thu", "nha dan", "nhà ở riêng lẻ", "kết hợp kinh doanh"]):
        target_codes.append("QCVN 10:2025/BCA")
        target_codes.append("TCVN 2622:1995")
        target_codes.append("TCVN 13456:2022")

    # 3. Đặc thù thiết bị & hệ thống kỹ thuật
    if any(k in stripped_q for k in ["bom", "tram bom", "may bom"]):
        target_codes.append("QCVN 02:2020/BCA")
    if any(k in stripped_q for k in ["chua chay", "sprinkler", "nuoc", "bot"]):
        target_codes.append("TCVN 7336:2021")
    if any(k in stripped_q for k in ["bao chay", "dau bao", "trung tam bao"]):
        target_codes.append("TCVN 7568-14:2025")
    if any(k in stripped_q for k in ["binh chua chay", "binh bot", "binh co2"]):
        target_codes.append("TCVN 7435-1:2004 / TCVN 7435-2:2004")
    if any(k in stripped_q for k in ["khi", "hfc", "fm200", "aerosol"]):
        target_codes.append("TCVN 7161-9:2009")
    if any(k in stripped_q for k in ["hut khoi", "thong gio", "ap suat", "tang ap"]):
        target_codes.append("TCVN 5687:2024")
    if any(k in stripped_q for k in ["thoat nan", "chieu sang su co", "chi dan", "den", "exit"]):
        target_codes.append("TCVN 13456:2022")
    if any(k in stripped_q for k in ["set", "chong set"]):
        target_codes.append("TCVN 9385:2012")

    if any(k in stripped_q for k in ["thang", "buong thang", "cau thang", "loai thang"]):
        target_codes.append("QCVN 06:2022/BXD (Sửa đổi 01-2023)")
        target_codes.append("TCVN 2622:1995")
    if any(k in stripped_q for k in ["trang bi", "phuong tien", "bo tri", "qcvn 10", "tcvn 3890", "thiet bi"]):
        target_codes.append("QCVN 10:2025/BCA")
    if any(k in stripped_q for k in ["khoang cach", "khoang lui", "bac chiu lua", "tuong ngan"]):
        target_codes.append("TCVN 2622:1995")

    # Tải toàn bộ tài liệu từ cơ sở dữ liệu để tìm kiếm kết hợp Hybrid RAG
    stmt = select(Document)
    result = await db.execute(stmt)
    all_db_docs = result.scalars().all()

    query_numbers = re.findall(r"\b[0-9]{1,5}\b", q_lower)
    words = [w for w in re.split(r"[\s_\-:/]+", q_lower) if w]
    stripped_words = [strip_vietnamese_accents(w) for w in words if len(w) >= 2]

    is_asking_about_uploads = any(
        k in stripped_q for k in [
            "tai lieu", "file", "vua tai", "vua up", "vua nap", "tui up",
            "da up", "tui da up", "da tai", "tui tai", "trich luc", "thu vien", "tai len"
        ]
    )

    doc_scores: List[tuple[int, Document]] = []
    for doc in all_db_docs:
        score = 0
        d_code = (doc.code or "").lower()
        d_title = (doc.title or "").lower()
        d_content = (doc.content or "").lower()

        d_code_stripped = strip_vietnamese_accents(d_code)
        d_title_stripped = strip_vietnamese_accents(d_title)
        d_content_stripped = strip_vietnamese_accents(d_content)
        norm_code = re.sub(r"[\s_\-:/]+", " ", d_code).strip()
        norm_code_stripped = strip_vietnamese_accents(norm_code)

        # 1. Khớp mã văn bản trong câu hỏi (ví dụ hỏi 2622, 13456, TCVN 2622, QCVN 02-2020)
        code_matched = False
        if d_code in q_lower or d_code_stripped in stripped_q:
            score += 160
            code_matched = True
        elif bool(norm_code_stripped) and (norm_code_stripped in stripped_norm_q or stripped_norm_q in norm_code_stripped):
            score += 150
            code_matched = True
        elif len(query_numbers) >= 1:
            matched_nums = sum(1 for num in query_numbers if len(num) >= 2 and re.search(r"(?<!\d)" + num + r"(?!\d)", d_code))
            if matched_nums > 0:
                score += matched_nums * 60
                code_matched = True

        # 2. Khớp cụm từ tiêu đề
        if stripped_q in d_title_stripped or (bool(stripped_norm_q) and stripped_norm_q in d_title_stripped):
            score += 90
        else:
            title_word_matches = sum(1 for w in stripped_words if w in d_title_stripped)
            score += title_word_matches * 15

        # 3. Khớp trong danh sách target_codes theo ngữ cảnh dự án (chỉ cộng nếu người dùng không hỏi chuyên về file tải lên)
        if not code_matched and not is_asking_about_uploads:
            for tc in target_codes:
                tc_norm = re.sub(r"[\s_\-:/]+", " ", tc.lower()).strip()
                if tc.lower() in d_code or (bool(tc_norm) and tc_norm in norm_code):
                    score += 85
                    break

        # 4. Khớp nội dung văn bản
        content_word_matches = sum(1 for w in stripped_words if len(w) >= 3 and w in d_content_stripped)
        score += min(content_word_matches * 5, 40)

        # 5. Ưu tiên tuyệt đối tài liệu do người dùng tải lên (is_custom=True)
        if doc.is_custom:
            if is_asking_about_uploads:
                score += 250
            elif code_matched or content_word_matches > 0 or any(w in d_title_stripped for w in stripped_words):
                score += 130

        # 6. Ưu tiên tài liệu có toàn văn thực thụ
        if len(doc.content or "") > 500 and "chưa có toàn văn" not in (doc.content or ""):
            score += 25

        if score > 0:
            doc_scores.append((score, doc))

    doc_scores.sort(key=lambda x: x[0], reverse=True)

    citations: List[Dict[str, Any]] = []
    seen_ids = set()
    seen_core_codes = set()

    for _, doc in doc_scores:
        if doc.id in seen_ids:
            continue
        d_code_stripped = strip_vietnamese_accents((doc.code or "").lower())
        core_code = re.sub(r"[\s_\-:/]+", " ", d_code_stripped).strip()
        core_code = re.sub(r"\b(bca|bxd|bct|cp|tt|nd)\b", "", core_code).strip()
        core_code = re.sub(r"\b0+(\d+)\b", r"\1", core_code).strip()

        if core_code and core_code in seen_core_codes:
            continue

        seen_ids.add(doc.id)
        if core_code:
            seen_core_codes.add(core_code)

        snippet = _extract_snippet(doc.content or "", q_lower if len(q_lower) > 2 else "thẩm duyệt", max_chars=350)
        rich_context = _extract_rich_context(doc.content or "", q_lower if len(q_lower) > 2 else "thẩm duyệt", max_chars=2500)
        citations.append({
            "id": doc.id,
            "code": doc.code,
            "title": doc.title,
            "type": doc.type,
            "snippet": snippet,
            "full_context": rich_context,
        })
        if len(citations) >= 6:
            break

    # Dự phòng nếu chưa có đủ tài liệu
    if len(citations) < 2:
        for doc in all_db_docs:
            d_code_stripped = strip_vietnamese_accents((doc.code or "").lower())
            core_code = re.sub(r"[\s_\-:/]+", " ", d_code_stripped).strip()
            core_code = re.sub(r"\b(bca|bxd|bct|cp|tt|nd)\b", "", core_code).strip()
            core_code = re.sub(r"\b0+(\d+)\b", r"\1", core_code).strip()

            if doc.id not in seen_ids and (not core_code or core_code not in seen_core_codes) and any(tc[:8].lower() in (doc.code or "").lower() for tc in target_codes[:2]):
                seen_ids.add(doc.id)
                if core_code:
                    seen_core_codes.add(core_code)
                snippet = _extract_snippet(doc.content or "", "thẩm duyệt", max_chars=350)
                rich_context = _extract_rich_context(doc.content or "", "thẩm duyệt", max_chars=2500)
                citations.append({
                    "id": doc.id,
                    "code": doc.code,
                    "title": doc.title,
                    "type": doc.type,
                    "snippet": snippet,
                    "full_context": rich_context,
                })
                if len(citations) >= 6:
                    break

    return citations[:6]


def is_project_verdict_query(text: str) -> bool:
    """Phân loại ý định: Người dùng đang hỏi về kết luận thẩm duyệt/cấp phép của CHÍNH DỰ ÁN NÀY (DEF-01).

    Chỉ khi hỏi về 'kết luận cấp phép/thẩm duyệt của dự án/công trình này' thì mới yêu cầu
    hồ sơ phải được kiểm duyệt trước. Nếu câu hỏi tự nêu kịch bản thông số độc lập (ví dụ Quick Prompt)
    mà không trỏ vào 'dự án này / hồ sơ này', sẽ coi là câu hỏi tư vấn tình huống.
    """
    if not text:
        return False
    t = text.lower().strip()
    stripped_t = strip_vietnamese_accents(t)

    for candidate in (t, stripped_t):
        # Đích danh hồ sơ/dự án/công trình này
        has_project_ref = bool(re.search(
            r"(?:du an|dự án|cong trinh|công trình|ho so|hồ sơ|ban ve|bản vẽ|toa nha|toà nhà|tòa nhà|ngoi nha|ngôi nhà|nha|nhà)\s+(?:nay|này|hien tai|hiện tại|dang nhap|đang nhập|dang xet|đang xét|cua toi|của tôi|cua em|của em|cua minh|của mình)",
            candidate,
        ))

        # Nếu câu hỏi mô tả một kịch bản có sẵn số tầng / diện tích / chiều cao độc lập mà không trỏ vào "dự án này"
        has_inline_scenario_scale = bool(re.search(
            r"\b\d+\s*(?:tang|tầng|m2|m²|m3|m³|met|mét)\b",
            candidate,
        ))
        if has_inline_scenario_scale and not has_project_ref:
            return False

        # 1. Các lệnh trực tiếp ngắn gọn yêu cầu hệ thống thẩm định/kết luận dự án hiện tại
        if re.search(
            r"^(?:hay\s+|hãy\s+)?(?:tham dinh|thẩm định|tham duyet|thẩm duyệt|kiem duyet|kiểm duyệt|ket luan|kết luận)(?:\s+(?:ngay|giup|giúp|toi|tôi|ho so|hồ sơ|du an|dự án|cong trinh|công trình|nay|này|hien tai|hiện tại|pccc))*[\s?.!]*$",
            candidate,
        ):
            return True

        # 2. Yêu cầu kết luận / cấp phép / đạt chuẩn cho dự án hiện tại
        has_verdict_intent = bool(re.search(
            r"(?:ket luan|kết luận|ket qua|kết quả|cap phep|cấp phép|duoc duyet|được duyệt|tham duyet|thẩm duyệt|tham dinh|thẩm định|nghiem thu|nghiệm thu|thuoc dien|thuộc diện|dat chuan|đạt chuẩn|co dat|có đạt|du dieu kien|đủ điều kiện|dat khong|đạt không|duoc khong|được không|phe duyet|phê duyệt)",
            candidate,
        ))

        if has_project_ref and has_verdict_intent:
            return True

        # 3. Các câu hỏi đặc thù kết luận cấp phép trực tiếp
        if re.search(r"(?:ket luan|kết luận|ket qua|kết quả)\s+(?:cap phep|cấp phép|tham duyet|thẩm duyệt|tham dinh|thẩm định)", candidate):
            return True
        if not has_inline_scenario_scale and re.search(
            r"(?:co|có|duoc|được)\s+(?:cap phep|cấp phép|nghiem thu|nghiệm thu|phe duyet|phê duyệt|tham duyet|thẩm duyệt)\s+(?:khong|không)",
            candidate,
        ):
            return True

    return False


def is_general_theory_query(text: str) -> bool:
    """Xác định xem câu hỏi có thuộc phạm vi lý thuyết, quy chuẩn, kỹ thuật PCCC hoặc các loại hình công trình hay không (DEF-01)."""
    if not text:
        return False
    t = text.lower().strip()
    stripped_t = strip_vietnamese_accents(t)

    # Chặn sớm các câu hỏi ngoài lề hoàn toàn (thời tiết, bóng đá, nấu ăn...)
    if re.search(r"(?:thoi tiet|thời tiết|bong da|bóng đá|gia vang|giá vàng|xo so|xổ số|chung khoan|chứng khoán)", stripped_t):
        return False

    for candidate in (t, stripped_t):
        if re.search(
            r"(?:pccc|phong chay|phòng cháy|chua chay|chữa cháy|cuu hoa|cứu hỏa|cuu nan|cứu nạn|cuu ho|cứu hộ|"
            r"luat|luật|quy chuan|quy chuẩn|tieu chuan|tiêu chuẩn|nghi dinh|nghị định|thong tu|thông tư|quy dinh|quy định|"
            r"huong dan|hướng dẫn|dieu khoan|điều khoản|trich dan|trích dẫn|trich luc|trích lục|tra cuu|tra cứu|van ban|văn bản|"
            r"ma hieu|mã hiệu|qcvn|tcvn|nd105|nđ105|147/2020|"
            r"loai thang|loại thang|buong thang|buồng thang|cau thang|cầu thang|thang bo|thang bộ|thang thoat|thang thoát|thang may|thang máy|"
            r"thoat hiem|thoát hiểm|thoat nan|thoát nạn|loi thoat|lối thoát|duong thoat|đường thoát|hanh lang|hành lang|cua thoat|cửa thoát|cua chong chay|cửa chống cháy|"
            r"vach ngan|vách ngăn|tuong ngan|tường ngăn|san ngan|sàn ngăn|ngan chay|ngăn cháy|chong chay|chống cháy|chay lan|cháy lan|"
            r"bao chay|báo cháy|dau bao|đầu báo|sprinkler|drencher|hong nuoc|họng nước|vach tuong|vách tường|tru nuoc|trụ nước|"
            r"tram bom|trạm bơm|may bom|máy bơm|be nuoc|bể nước|binh chua chay|bình chữa cháy|binh bot|bình bột|binh co2|bình co2|"
            r"khi|khí|hut khoi|hút khói|thong gio|thông gió|ap suat|áp suất|tang ap|tăng áp|khoang dem|khoang đệm|"
            r"chong set|chống sét|khoang cach|khoảng cách|khoang lui|khoảng lùi|duong giao thong|đường giao thông|xe chua chay|xe chữa cháy|"
            r"bac chiu lua|bậc chịu lửa|khoang chay|khoang cháy|chieu cao|chiều cao|dien tich|diện tích|khoi tich|khối tích|so tang|số tầng|tang ham|tầng hầm|"
            r"gioi han chiu lua|giới hạn chịu lửa|hang nguy hiem|hạng nguy hiểm|\bei\b|\brei\b|"
            r"karaoke|vu truong|vũ trường|quan bar|quán bar|gara|bai do|bãi đỗ|nha de xe|nhà để xe|xang dau|xăng dầu|khi dot|khí đốt|\blpg\b|tram bien ap|trạm biến áp|"
            r"nha cao|nhà cao|nha hon hop|nhà hỗn hợp|hon hop|hỗn hợp|da nang|đa năng|ket hop kinh doanh|kết hợp kinh doanh|nha o rieng le|nhà ở riêng lẻ|nha dan|nhà dân|biet thu|biệt thự|nha pho|nhà phố|shophouse|"
            r"chung cu|chung cư|ky tuc xa|ký túc xá|nha tro|nhà trọ|phong tro|phòng trọ|nha tap the|nhà tập thể|"
            r"van phong|văn phòng|cong so|công sở|tru so|trụ sở|khach san|khách sạn|nha nghi|nhà nghỉ|nha khach|nhà khách|resort|"
            r"cho|chợ|sieu thi|siêu thị|trung tam thuong mai|trung tâm thương mại|cua hang|cửa hàng|nha hang|nhà hàng|quan an|quán ăn|"
            r"nha xuong|nhà xưởng|nha may|nhà máy|xuong san xuat|xưởng sản xuất|co so san xuat|cơ sở sản xuất|xi nghiep|xí nghiệp|khu cong nghiep|khu công nghiệp|"
            r"nha kho|nhà kho|kho hang|kho hàng|gia do|giá đỡ|ke cao|kệ cao|"
            r"truong hoc|trường học|co so giao duc|cơ sở giáo dục|mam non|mầm non|nha tre|nhà trẻ|tieu hoc|tiểu học|trung hoc|trung học|dai hoc|đại học|cao dang|cao đẳng|"
            r"benh vien|bệnh viện|co so y te|cơ sở y tế|phong kham|phòng khám|tram y te|trạm y tế|dieu duong|điều dưỡng|"
            r"rap hat|rạp hát|hoi truong|hội trường|su kien|sự kiện|rap chieu phim|rạp chiếu phim|nha van hoa|nhà văn hóa|trung tam hoi nghi|trung tâm hội nghị|san van dong|sân vận động|nha thi dau|nhà thi đấu|"
            r"tham duyet|thẩm duyệt|tham dinh|thẩm định|nghiem thu|nghiệm thu|cap phep|cấp phép|kiem dinh|kiểm định|kiem duyet|kiểm duyệt|"
            r"trang bi|trang bị|phuong tien|phương tiện|quy mo|quy mô|thuoc dien|thuộc diện|nguong|ngưỡng|"
            r"tai lieu|tài liệu|file|tai len|tải lên|vua tai|vừa tải|vua up|vừa up|vua nap|vừa nạp|nap file|nạp file|tri thuc|tri thức|"
            r"da up|đã up|da nap|đã nạp|da tai|đã tải|tui up|tui tai|thu vien|thư viện|doc file|đọc file|noi dung|nội dung|tom tat|tóm tắt|"
            r"tim hieu|tìm hiểu|nghien cuu|nghiên cứu|he thong|hệ thống|ban ve|bản vẽ|chieu sang su co|chiếu sáng sự cố|den exit|đèn exit|"
            r"\b2622\b|\b13456\b|\b7336\b|\b5687\b|\b9385\b|\b7568\b|\b12110\b|\b13333\b|\b13657\b|\b14496\b|\b6161\b|\b3890\b)",
            candidate,
        ):
            return True
    return False


def _get_building_type_pccc_guidance(project_info: Dict[str, Any], message_text: str) -> List[str]:
    """Trả về hướng dẫn kỹ thuật PCCC chi tiết và căn cứ quy chuẩn cho từng loại hình công trình (14 nhóm công năng)."""
    p_type = str(project_info.get("type") or "").lower()
    q_lower = (message_text or "").lower()
    combined = f"{p_type} {q_lower}"
    stripped = strip_vietnamese_accents(combined)

    guidance: List[str] = []

    if any(k in stripped for k in ["karaoke", "vu truong", "quan bar", "dich vu vu truong"]):
        guidance.extend([
            "- **Loại hình công trình:** Cơ sở kinh doanh dịch vụ Karaoke, Vũ trường (Nhóm F2.1/F3.2).",
            "- **Ngưỡng thẩm định thiết kế PCCC ([NĐ105/2025/NĐ-CP]):** Bắt buộc thẩm định khi cao từ **3 tầng** trở lên hoặc tổng diện tích sàn từ **500 m²** trở lên (hoặc khối tích từ 1.500 m³).",
            "- **Yêu cầu kỹ thuật trọng tâm ([147/2020/TT-BCA], [QCVN 06:2022/BXD (Sửa đổi 01-2023)], [QCVN 10:2025/BCA]):**",
            "  + Bố trí tối thiểu **02 lối thoát nạn độc lập** cho mỗi tầng; chiều rộng lối đi, bản thang và cửa thoát nạn >= 1,0m–1,2m; vật liệu trang trí cách âm/tiêu âm phải là vật liệu khó cháy hoặc không cháy.",
            "  + Trang bị hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, hệ thống họng nước chữa cháy trong nhà, chữa cháy tự động Sprinkler **[TCVN 7336:2021]**, đèn chỉ dẫn thoát nạn **[TCVN 13456:2022]** và mặt nạ phòng độc tại các phòng hát.",
        ])
    elif any(k in stripped for k in ["ket hop kinh doanh", "shophouse", "nha o ket hop"]):
        guidance.extend([
            "- **Loại hình công trình:** Nhà ở riêng lẻ kết hợp sản xuất, kinh doanh (Shophouse).",
            "- **Căn cứ áp dụng:** **[QCVN 06:2022/BXD (Sửa đổi 01-2023)]** (Mục A.4 Phụ lục A), **[NĐ105/2025/NĐ-CP]**, **[QCVN 10:2025/BCA]**.",
            "- **Yêu cầu kỹ thuật trọng tâm:**",
            "  + Khu vực kinh doanh, tồn chứa hàng hóa phải được **ngăn cháy lan** với phần để ở và cầu thang thoát nạn bằng tường/vách ngăn cháy (EI 45–60) và sàn ngăn cháy (REI 45–60).",
            "  + Đảm bảo lối thoát nạn từ phần ở không đi xuyên qua khu vực kinh doanh không được ngăn cháy; bố trí lối thoát khẩn cấp thứ 2 qua ban công, lô gia, sân thượng hoặc thang ngoài nhà.",
            "  + Không bố trí kinh doanh, bảo quản hàng hóa nguy hiểm cháy nổ hạng A, B trong nhà ở; trang bị báo cháy tự động, bình chữa cháy xách tay và đèn chiếu sáng sự cố **[TCVN 13456:2022]**.",
        ])
    elif any(k in stripped for k in ["nha o rieng le", "nha dan", "biet thu", "nha pho"]):
        guidance.extend([
            "- **Loại hình công trình:** Nhà ở riêng lẻ (Nhóm F1.4).",
            "- **Căn cứ áp dụng:** **[QCVN 06:2022/BXD (Sửa đổi 01-2023)]**, **[TCVN 2622:1995]**, **[NĐ105/2025/NĐ-CP]**.",
            "- **Yêu cầu kỹ thuật trọng tâm:**",
            "  + Nhà ở riêng lẻ từ **6 tầng trở xuống** không thuộc diện bắt buộc thẩm định thiết kế về PCCC (trừ khi chuyển đổi công năng kết hợp sản xuất, kinh doanh đạt ngưỡng Phụ lục III).",
            "  + Khuyến nghị bố trí tối thiểu **02 lối thoát hiểm** (cầu thang bộ trong nhà và lối thoát khẩn cấp qua ban công, sân thượng hoặc ô cửa mở trên lồng sắt), lắp đặt thiết bị cảnh báo khói độc lập và bình chữa cháy xách tay tại mỗi tầng.",
        ])
    elif any(k in stripped for k in ["nha hon hop", "hon hop", "da nang"]):
        guidance.extend([
            "- **Loại hình công trình:** Nhà hỗn hợp (thương mại, dịch vụ, văn phòng kết hợp căn hộ ở).",
            "- **Ngưỡng thẩm định thiết kế PCCC ([NĐ105/2025/NĐ-CP]):** Bắt buộc thẩm định khi cao từ **7 tầng** trở lên hoặc tổng diện tích sàn từ **3.000 m²** trở lên.",
            "- **Yêu cầu kỹ thuật trọng tâm ([QCVN 06:2022/BXD (Sửa đổi 01-2023)], [QCVN 10:2025/BCA]):**",
            "  + Phân chia khoang cháy và ngăn cách phần công năng thương mại/công cộng với phần ở bằng tường và sàn ngăn cháy loại 1 (REI 150) hoặc loại 2 (REI 60); lối thoát nạn của khối ở phải tách biệt với khối thương mại.",
            "  + Khi chiều cao PCCC > 28m: bắt buộc bố trí buồng thang bộ không nhiễm khói (**N1**, hoặc **N2/N3** có tăng áp **[TCVN 5687:2024]**) và thang máy chữa cháy.",
            "  + Trang bị hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, chữa cháy tự động Sprinkler **[TCVN 7336:2021]**, họng nước chữa cháy trong/ngoài nhà và hệ thống hút khói hành lang.",
        ])
    elif any(k in stripped for k in ["chung cu", "ky tuc xa", "nha tro", "phong tro", "nha tap the"]):
        guidance.extend([
            "- **Loại hình công trình:** Nhà chung cư, ký túc xá, nhà tập thể, nhà trọ (Nhóm F1.2, F1.3).",
            "- **Ngưỡng thẩm định thiết kế PCCC ([NĐ105/2025/NĐ-CP]):** Bắt buộc thẩm định khi cao từ **7 tầng** trở lên hoặc tổng diện tích sàn từ **3.000 m²** trở lên.",
            "- **Yêu cầu kỹ thuật trọng tâm ([QCVN 06:2022/BXD (Sửa đổi 01-2023)], [QCVN 10:2025/BCA]):**",
            "  + Mỗi tầng có diện tích >= 500 m² (hoặc theo quy mô người) phải có tối thiểu **02 lối thoát nạn độc lập**; nhà có chiều cao PCCC > 28m phải sử dụng buồng thang bộ không nhiễm khói N1/N2/N3.",
            "  + Trang bị hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, hệ thống chữa cháy tự động Sprinkler **[TCVN 7336:2021]** (khi cao >= 25m hoặc thuộc diện bắt buộc), họng nước chữa cháy vách tường, hệ thống hút khói **[TCVN 5687:2024]** và đèn chỉ dẫn thoát nạn **[TCVN 13456:2022]**.",
        ])
    elif any(k in stripped for k in ["khach san", "van phong", "nha nghi", "nha khach", "resort", "tru so", "cong so"]):
        guidance.extend([
            "- **Loại hình công trình:** Trụ sở cơ quan, văn phòng làm việc, khách sạn, cơ sở lưu trú (Nhóm F1.2, F4.3).",
            "- **Ngưỡng thẩm định thiết kế PCCC ([NĐ105/2025/NĐ-CP]):** Bắt buộc thẩm định khi cao từ **7 tầng** trở lên hoặc tổng diện tích sàn từ **3.000 m²** trở lên.",
            "- **Yêu cầu kỹ thuật trọng tâm ([QCVN 06:2022/BXD (Sửa đổi 01-2023)], [QCVN 10:2025/BCA]):**",
            "  + Đảm bảo bậc chịu lửa (Bậc I, II hoặc III theo chiều cao và diện tích khoang cháy); mỗi tầng bố trí tối thiểu **02 lối thoát nạn**, cửa buồng thang bộ ngăn cháy có cơ cấu tự đóng.",
            "  + Trang bị hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, họng nước chữa cháy trong nhà, chữa cháy tự động Sprinkler **[TCVN 7336:2021]**, hút khói hành lang **[TCVN 5687:2024]** và chiếu sáng sự cố **[TCVN 13456:2022]**.",
        ])
    elif any(k in stripped for k in ["cho", "trung tam thuong mai", "sieu thi", "cua hang", "nha hang", "quan an"]):
        guidance.extend([
            "- **Loại hình công trình:** Chợ, Trung tâm thương mại, Siêu thị, Cửa hàng dịch vụ ăn uống (Nhóm F3.1, F3.2).",
            "- **Ngưỡng thẩm định thiết kế PCCC ([NĐ105/2025/NĐ-CP]):** Bắt buộc thẩm định khi tổng diện tích sàn từ **300 m²** trở lên.",
            "- **Yêu cầu kỹ thuật trọng tâm ([TCVN 6161:1996], [QCVN 06:2022/BXD (Sửa đổi 01-2023)], [QCVN 10:2025/BCA]):**",
            "  + Phân chia khoang cháy, bố trí lối đi thoát nạn thông thoáng giữa các dãy quầy hàng (rộng >= 1,4m–2,0m) dẫn trực tiếp ra tối thiểu **02 lối thoát nạn độc lập**; cửa thoát nạn mở ra ngoài theo chiều thoát nạn.",
            "  + Trang bị hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, chữa cháy tự động Sprinkler **[TCVN 7336:2021]**, họng nước chữa cháy trong/ngoài nhà, hệ thống hút khói **[TCVN 5687:2024]** và chiếu sáng sự cố **[TCVN 13456:2022]**.",
        ])
    elif any(k in stripped for k in ["gara", "xe o to", "bai do", "nha de xe"]):
        guidance.extend([
            "- **Loại hình công trình:** Nhà để xe ô tô, xe máy dạng kín / Gara tầng hầm (Nhóm F5.2).",
            "- **Ngưỡng thẩm định thiết kế PCCC ([NĐ105/2025/NĐ-CP]):** Nhà để xe ô tô dạng kín có tổng diện tích sàn từ **2.000 m²** trở lên (hoặc nằm trong công trình thuộc diện thẩm duyệt).",
            "- **Yêu cầu kỹ thuật trọng tâm ([QCVN 13:2018/BXD], [QCVN 06:2022/BXD (Sửa đổi 01-2023)], [QCVN 10:2025/BCA]):**",
            "  + Ngăn cách gara với các khu vực công năng khác bằng tường ngăn cháy loại 1 (REI 150) và sàn ngăn cháy (REI 90–150); bố trí ram dốc cho xe và tối thiểu **02 lối thoát nạn cho người** qua khoang đệm ngăn cháy có tăng áp.",
            "  + Bắt buộc trang bị hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, hệ thống chữa cháy tự động Sprinkler/bọt **[TCVN 7336:2021]**, họng nước vách tường và hệ thống hút khói cơ khí **[TCVN 5687:2024]**.",
        ])
    elif any(k in stripped for k in ["nha kho", "kho hang", "gia do", "ke cao"]) or re.search(r"\bkho\b", stripped):
        guidance.extend([
            "- **Loại hình công trình:** Nhà kho, kho hàng hóa, kho xếp giá đỡ kệ cao (Nhóm F5.2).",
            "- **Căn cứ áp dụng:** **[TCVN 14496:2025]**, **[QCVN 06:2022/BXD (Sửa đổi 01-2023)]**, **[NĐ105/2025/NĐ-CP]**, **[QCVN 10:2025/BCA]**.",
            "- **Yêu cầu kỹ thuật trọng tâm:**",
            "  + Cần xác định rõ **hạng nguy hiểm cháy và cháy nổ (A, B, C, D, E)** để xác định ngưỡng thẩm định Phụ lục III, bậc chịu lửa và diện tích khoang cháy tối đa cho phép.",
            "  + Đối với kho có chiều cao xếp hàng trên 5,5m (kho kệ cao), bắt buộc áp dụng **[TCVN 14496:2025]** và **[TCVN 7336:2021]** bố trí hệ thống chữa cháy tự động Sprinkler (bao gồm đầu phun trần và đầu phun trong kệ hàng), hệ thống báo cháy tự động, hút khói và đường cho xe chữa cháy tiếp cận.",
        ])
    elif any(k in stripped for k in ["nha may", "nha xuong", "san xuat", "xi nghiep", "khu cong nghiep"]):
        guidance.extend([
            "- **Loại hình công trình:** Nhà máy, nhà xưởng sản xuất công nghiệp (Nhóm F5.1).",
            "- **Căn cứ áp dụng:** **[QCVN 06:2022/BXD (Sửa đổi 01-2023)]**, **[NĐ105/2025/NĐ-CP]**, **[QCVN 10:2025/BCA]**, **[TCVN 2622:1995]**.",
            "- **Yêu cầu kỹ thuật trọng tâm:**",
            "  + Cần phân loại **hạng nguy hiểm cháy nổ (A, B, C1–C4, D, E)** của gian phòng và nhà xưởng để đối chiếu ngưỡng thẩm định theo Phụ lục III **[NĐ105/2025/NĐ-CP]** cũng như diện tích khoang cháy tối đa.",
            "  + Đảm bảo khoảng cách đến lối thoát nạn gần nhất, tối thiểu **02 lối thoát nạn độc lập** có chiều rộng >= 1,0m–1,2m, cửa mở ra ngoài theo chiều thoát nạn.",
            "  + Trang bị hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, chữa cháy tự động **[TCVN 7336:2021]** (cho các gian phòng/xưởng hạng A, B, C từ ngưỡng diện tích quy định tại **[QCVN 10:2025/BCA]**), cấp nước chữa cháy trong/ngoài nhà, thông gió hút khói **[TCVN 5687:2024]** và chống sét **[TCVN 9385:2012]**.",
        ])
    elif any(k in stripped for k in ["truong hoc", "giao duc", "mam non", "nha tre", "tieu hoc", "trung hoc", "dai hoc", "cao dang"]):
        guidance.extend([
            "- **Loại hình công trình:** Cơ sở giáo dục, trường học, nhà trẻ, trường mầm non (Nhóm F1.1, F4.1, F4.2).",
            "- **Căn cứ áp dụng:** **[QCVN 06:2022/BXD (Sửa đổi 01-2023)]**, **[NĐ105/2025/NĐ-CP]**, **[QCVN 10:2025/BCA]**, **[TCVN 2622:1995]**.",
            "- **Yêu cầu kỹ thuật trọng tâm:**",
            "  + Đối chiếu ngưỡng thẩm định theo cấp học (số cháu/diện tích đối với mầm non; số tầng/tổng diện tích sàn hoặc khối tích đối với trường phổ thông, đại học theo Phụ lục III **[NĐ105/2025/NĐ-CP]**).",
            "  + Khối nhà trẻ, mầm non (F1.1) giới hạn chiều cao bố trí tầng và bắt buộc có tối thiểu **02 lối thoát nạn độc lập** mỗi tầng, hành lang rộng >= 1,4m–2,2m, tuyệt đối không dùng cầu thang xoắn hoặc bậc thang hình rẻ quạt.",
            "  + Trang bị hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, hệ thống loa thông báo hướng dẫn thoát nạn, họng nước chữa cháy trong nhà, bình chữa cháy và đèn chỉ dẫn thoát nạn **[TCVN 13456:2022]**.",
        ])
    elif any(k in stripped for k in ["benh vien", "y te", "phong kham", "tram y te", "dieu duong"]):
        guidance.extend([
            "- **Loại hình công trình:** Bệnh viện, phòng khám, cơ sở y tế, nhà điều dưỡng (Nhóm F1.1, F3.4).",
            "- **Ngưỡng thẩm định thiết kế PCCC ([NĐ105/2025/NĐ-CP]):** Bắt buộc thẩm định khi cao từ **3 tầng** trở lên hoặc tổng diện tích sàn từ **300 m²** trở lên.",
            "- **Yêu cầu kỹ thuật trọng tâm ([QCVN 06:2022/BXD (Sửa đổi 01-2023)], [QCVN 10:2025/BCA]):**",
            "  + Đảm bảo bậc chịu lửa Bậc I/II; hành lang khu điều trị nội trú có chiều rộng thông thủy >= 2,4m để quay cáng bệnh nhân, cửa phòng bệnh và cửa thoát nạn rộng >= 1,2m; bố trí tối thiểu **02 lối thoát nạn** và vùng an toàn ngăn cháy.",
            "  + Trang bị thang máy chữa cháy/chở cáng bệnh nhân, hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, hệ thống chữa cháy tự động Sprinkler **[TCVN 7336:2021]**, họng nước chữa cháy, hút khói **[TCVN 5687:2024]** và chiếu sáng sự cố **[TCVN 13456:2022]**.",
        ])
    elif any(k in stripped for k in ["rap hat", "hoi truong", "su kien", "rap chieu phim", "nha van hoa", "trung tam hoi nghi", "san van dong", "nha thi dau"]):
        guidance.extend([
            "- **Loại hình công trình:** Rạp hát, rạp chiếu phim, hội trường, trung tâm tổ chức sự kiện, nhà văn hóa (Nhóm F2.1, F2.2).",
            "- **Căn cứ áp dụng:** **[QCVN 06:2022/BXD (Sửa đổi 01-2023)]**, **[NĐ105/2025/NĐ-CP]**, **[QCVN 10:2025/BCA]**, **[TCVN 2622:1995]**.",
            "- **Yêu cầu kỹ thuật trọng tâm:**",
            "  + Đối chiếu ngưỡng thẩm định theo sức chứa (số chỗ ngồi từ 300 chỗ trở lên) hoặc số tầng / tổng diện tích sàn theo Phụ lục III **[NĐ105/2025/NĐ-CP]**.",
            "  + Gian khán giả đông người bắt buộc có tối thiểu **02–04 lối thoát nạn độc lập**, tổng chiều rộng cửa thoát nạn tính theo số người lớn nhất (cửa mở ra ngoài theo chiều thoát nạn, không làm bậc ngưỡng cửa); ghế ngồi khán phòng phải được cố định xuống sàn.",
            "  + Trang bị hệ thống báo cháy tự động **[TCVN 7568-14:2025]**, chữa cháy tự động Sprinkler/Drencher màn nước sân khấu **[TCVN 7336:2021]**, hệ thống hút khói **[TCVN 5687:2024]** và đèn chiếu sáng sự cố **[TCVN 13456:2022]**.",
        ])
    elif any(k in stripped for k in ["xang dau", "khi dot", "lpg", "tram bien ap"]):
        guidance.extend([
            "- **Loại hình công trình:** Cửa hàng xăng dầu, trạm cấp khí đốt LPG, công trình năng lượng.",
            "- **Ngưỡng thẩm định thiết kế PCCC ([NĐ105/2025/NĐ-CP]):** Bắt buộc thẩm định thiết kế về PCCC đối với mọi quy mô cửa hàng xăng dầu (từ 01 cột bơm trở lên).",
            "- **Yêu cầu kỹ thuật trọng tâm ([QCVN 01:2020/BCT], [TCVN 9385:2012], [QCVN 10:2025/BCA]):**",
            "  + Đảm bảo khoảng cách an toàn PCCC từ bể chứa xăng dầu đặt ngầm, cột bơm và họng nhập kín đến ranh giới công trình lân cận theo **[QCVN 01:2020/BCT]**.",
            "  + Hệ thống điện, chiếu sáng và máy bơm đạt chuẩn phòng nổ (Ex); trang bị hệ thống chống sét đánh thẳng và nối đất chống tĩnh điện **[TCVN 9385:2012]**, hệ thống thu hồi hơi xăng dầu và đầy đủ bình chữa cháy bột/CO2.",
        ])

    return guidance


async def _ask_gemini_theory(
    query: str,
    citations: List[Dict[str, Any]],
    project_info: Optional[Dict[str, Any]] = None,
    building_guidance: Optional[List[str]] = None,
) -> Optional[str]:
    """Tối ưu tốc độ & token: Gọi Gemini với thinking_budget=0 và failover model để giải đáp lý thuyết nhanh."""
    import os
    from app import config as app_config

    api_key = (app_config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")).strip()
    if not api_key:
        return None

    try:
        from app.gemini_client import generate_content_with_retry
        from google.genai import types

        cit_parts = []
        for c in citations[:6]:
            body = c.get("full_context") or c.get("snippet") or ""
            if "chưa có toàn văn" in body.lower():
                cit_parts.append(f"- [{c['code']}] {c['title']}")
            else:
                cit_parts.append(f"- [{c['code']}] {c['title']}:\n{body}")

        cit_text = "\n\n".join(cit_parts)
        p_context = ""
        if project_info and project_info.get("type"):
            p_context = (
                f"\nLoại công trình đang chọn trên hồ sơ: {project_info.get('type')} "
                f"(Quy mô: {project_info.get('floors') or 0} tầng, diện tích: {project_info.get('totalFloorArea') or 0} m²)."
            )
        if building_guidance:
            p_context += "\nKhung quy định chuẩn cho loại công trình này:\n" + "\n".join(building_guidance)

        sys_prompt = (
            "Bạn là chuyên gia tư vấn quy chuẩn PCCC Việt Nam (QCVN 06:2022/BXD, TCVN, NĐ 105/2025/NĐ-CP và các tài liệu chuyên ngành do người dùng nạp vào). "
            "Trả lời ngắn gọn, chuẩn xác, đầy đủ và trực tiếp vào câu hỏi của người dùng dựa trên các tài liệu tham khảo trong thư viện RAG dưới đây. "
            "Nếu người dùng hỏi về tài liệu hoặc file vừa tải lên, hãy ưu tiên trích dẫn các quy định, thông số, bảng biểu và điều khoản từ chính tài liệu đó. "
            "Luôn đính kèm trích dẫn mã quy chuẩn dạng [Mã văn bản] (ví dụ: [QCVN 06:2022/BXD (Sửa đổi 01-2023)], [NĐ105/2025/NĐ-CP], [QCVN 02:2020/BCA] hoặc [TCVN 2622:1995]) để người dùng bấm xem. "
            "Không tự nhận thẩm quyền nhà nước và không suy đoán số liệu chưa có."
        )
        user_content = f"Câu hỏi của người dùng: {query}{p_context}\n\nTài liệu tham khảo đối chiếu từ thư viện RAG:\n{cit_text}"
        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.1,
            max_output_tokens=1000,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        response = await generate_content_with_retry(
            contents=[{"role": "user", "parts": [{"text": user_content}]}],
            config=config,
        )
        text = getattr(response, "text", "") or ""
        return text.strip() if text.strip() else None
    except Exception as e:
        logger.warning("Gemini theory answering failed, falling back to deterministic RAG: %s", e)
        return None


async def generate_hybrid_rag_reply(
    db: AsyncSession,
    session: ChatSession,
    message_text: str,
    is_general_theory: bool = False,
) -> Dict[str, Any]:
    """Tạo câu trả lời kết hợp tra cứu điều khoản thật và bộ quy tắc thẩm định (Ngày 4 kế hoạch & DEF-01)."""
    pinfo = session.project_data.to_dict() if session.project_data else {}
    basis = (
        session.checklist[0].get("reviewedBasis")
        if session.checklist and isinstance(session.checklist[0], dict)
        else None
    )

    # 1. Tra cứu các văn bản luật phù hợp trong cơ sở dữ liệu (luôn truyền pinfo để giữ ngữ cảnh loại công trình)
    citations = await search_citations_for_project_and_query(
        db,
        message_text,
        pinfo,
        basis,
    )
    building_guidance = _get_building_type_pccc_guidance(pinfo, message_text)

    # 2. Xử lý trường hợp câu hỏi lý thuyết / quy chuẩn chung hoặc tư vấn theo loại công trình (DEF-01)
    if is_general_theory:
        ai_reply = await _ask_gemini_theory(message_text, citations, pinfo, building_guidance)
        if ai_reply:
            reply = ai_reply
        elif citations or building_guidance:
            lines = [
                "Chào bạn! Dưới đây là giải đáp lý thuyết & căn cứ quy chuẩn PCCC cho câu hỏi của bạn:\n"
            ]
            if building_guidance:
                lines.append("🏢 **Hướng dẫn kỹ thuật PCCC trọng tâm theo loại hình công trình:**")
                lines.extend(building_guidance)
                lines.append("")
            for cit in citations:
                tag = f"[{cit['code']}]"
                lines.append(f"• Theo **{tag}** ({cit['title']}):")
                text_extract = cit.get("full_context") or cit.get("snippet") or ""
                cleaned_extract = re.sub(r"\s+", " ", text_extract).strip()
                if len(cleaned_extract) > 420:
                    cleaned_extract = cleaned_extract[:417] + "..."
                if cleaned_extract and "chưa có toàn văn" not in cleaned_extract.lower():
                    lines.append(f"  *Trích lục quy định:* \"{cleaned_extract}\"")
                elif cit.get("snippet"):
                    lines.append(f"  *Trích yếu:* \"{cit['snippet']}\"")
            lines.append("\n💡 *Bạn có thể bấm vào thẻ [Mã văn bản] để xem tài liệu gốc chi tiết.*")
            reply = "\n".join(lines)
        else:
            reply = (
                "Chào bạn! Dưới đây là thông tin tra cứu quy chuẩn PCCC cho câu hỏi của bạn:\n"
                "• Quy chuẩn áp dụng nền tảng: **[QCVN 06:2022/BXD (Sửa đổi 01-2023)]** và **[NĐ105/2025/NĐ-CP]**.\n"
                "💡 *Bạn có thể bấm vào thẻ [Mã văn bản] để xem toàn văn quy chuẩn hoặc đặt câu hỏi kèm từ khóa kỹ thuật cụ thể.*"
            )

        return {
            "reply": reply,
            "citations": citations,
        }

    # 3. Câu hỏi gắn liền với kết luận và hồ sơ công trình cụ thể
    p_name = pinfo.get("name") or "Công trình"
    p_type = pinfo.get("type") or "Chưa rõ công năng"
    floors = pinfo.get("floors") or 0
    area = pinfo.get("totalFloorArea") or pinfo.get("floorArea") or 0
    pccc_height = pinfo.get("pcccHeight") or pinfo.get("height") or 0

    reason = session.appraisal_reason or "Chưa có kết luận thẩm duyệt."
    warnings = session.warnings or []

    lines = []
    lines.append(f"Chào bạn! Dưới đây là thông tin tư vấn PCCC cho dự án **{p_name}** ({p_type}):\n")
    lines.append(f"• **Kết quả thẩm định:** {reason}")

    try:
        area_num = float(area)
        area_str = f"{area_num:,.1f}".rstrip("0").rstrip(".") if area_num % 1 else f"{int(area_num):,}"
    except (ValueError, TypeError):
        area_str = str(area)

    if pccc_height:
        lines.append(f"• **Thông số kỹ thuật:** Quy mô {floors} tầng, tổng diện tích {area_str} m², chiều cao PCCC {pccc_height} m.")
    else:
        lines.append(f"• **Thông số kỹ thuật:** Quy mô {floors} tầng, tổng diện tích {area_str} m².")

    if building_guidance:
        lines.append("\n🏢 **Yêu cầu kỹ thuật PCCC đặc thù theo công năng:**")
        lines.extend(building_guidance)

    if warnings:
        lines.append("\n⚠️ **Lưu ý & Khuyến nghị kỹ thuật:**")
        for w in warnings:
            lines.append(f"- {w}")

    # Danh sách căn cứ và trích dẫn điều khoản thật kèm thẻ bấm được
    lines.append("\n📚 **Căn cứ pháp lý & Nguồn trích dẫn điều khoản áp dụng:**")
    for cit in citations:
        tag = f"[{cit['code']}]"
        lines.append(f"- {tag} ({cit['type']}): {cit['title']}")
        if cit.get("snippet"):
            lines.append(f"  *Trích yếu:* \"{cit['snippet']}\"")

    lines.append("\n💡 *Bạn có thể bấm trực tiếp vào thẻ mã văn bản [Mã văn bản] ở trên để mở trực tiếp tài liệu PDF gốc.*")

    reply = "\n".join(lines)
    return {
        "reply": reply,
        "citations": citations,
    }

