"""BM-04: Phân đoạn Tri thức Pháp lý Chuyên dụng cho Quy chuẩn & Tiêu chuẩn PCCC Việt Nam.
Bóc tách theo cấu trúc: Chương -> Mục -> Điều -> Khoản / Phụ lục / Bảng.
Bảo toàn trọn vẹn từng Điều luật kỹ thuật cùng các ngoại lệ và bảng số liệu.
"""
from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional, Tuple

from app.utils_file import RAG_STOPWORDS, strip_vietnamese_accents


@dataclass
class LegalChunk:
    chunk_id: str
    doc_code: str
    chapter: str
    article: str
    title: str
    content: str
    full_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunkId": self.chunk_id,
            "docCode": self.doc_code,
            "chapter": self.chapter,
            "article": self.article,
            "title": self.title,
            "content": self.content,
            "fullText": self.full_text,
        }


# Regex nhận diện các cấu trúc phân cấp pháp lý chuẩn
RE_CHAPTER = re.compile(
    r"(?im)^(?:[\s\-\*#]*)(Chương\s+[IVXLCDM0-9]+(?:[\.\:\-]\s*([^\n\r]+)|(?:\s+([^\n\r]+))|(?=\n|$)))"
)
RE_SECTION = re.compile(
    r"(?im)^(?:[\s\-\*#]*)(Mục\s+[0-9IVXLCDM]+(?:[\.\:\-]\s*([^\n\r]+)|(?:\s+([^\n\r]+))|(?=\n|$)))"
)
RE_ARTICLE = re.compile(
    r"(?im)^(?:[\s\-\*#]*)(Điều\s+(\d+)(?:[\.\:\-]\s*([^\n\r]+)|(?:\s+([^\n\r]+))|(?=\n|$)))"
)
RE_APPENDIX = re.compile(
    r"(?im)^(?:[\s\-\*#]*)(Phụ\s+lục\s+([A-Z0-9\.]+)(?:[\.\:\-]\s*([^\n\r]+)|(?:\s+([^\n\r]+))|(?=\n|$)))"
)
RE_TABLE = re.compile(
    r"(?im)^(?:[\s\-\*#]*)(Bảng\s+([A-Z0-9\.]+)(?:[\.\:\-]\s*([^\n\r]+)|(?:\s+([^\n\r]+))|(?=\n|$)))"
)


def chunk_legal_document(doc_code: str, doc_title: str, text: str) -> List[LegalChunk]:
    """Phân đoạn toàn bộ văn bản pháp lý thành danh sách các LegalChunk theo Điều/Khoản luật (BM-04).
    Bảo toàn trọn vẹn toàn bộ từng Điều luật kỹ thuật cùng các ngoại lệ và bảng số liệu."""
    if not text or not text.strip():
        return []

    clean_text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = clean_text.split("\n")

    # 1. Tìm vị trí các tiêu đề Chương, Mục, Điều, Phụ lục, Bảng
    # Mỗi marker lưu: (char_start, type, header_line, number_or_id, title)
    markers: List[Tuple[int, str, str, str, str]] = []

    pos = 0
    for line in lines:
        line_len = len(line) + 1  # tính cả newline
        sline = line.strip()
        if sline:
            # Kiểm tra Điều
            m_art = RE_ARTICLE.match(line)
            if m_art:
                art_header = m_art.group(1).strip()
                art_num = m_art.group(2).rstrip(".:- ").strip()
                art_title = (m_art.group(3) or m_art.group(4) or "").strip().rstrip("*#_ ").strip()
                markers.append((pos, "ARTICLE", art_header, art_num, art_title))
                pos += line_len
                continue

            # Kiểm tra Chương
            m_chap = RE_CHAPTER.match(line)
            if m_chap:
                chap_header = m_chap.group(1).strip()
                chap_title = (m_chap.group(2) or m_chap.group(3) or "").strip().rstrip("*#_ ").strip()
                markers.append((pos, "CHAPTER", chap_header, "", chap_title))
                pos += line_len
                continue

            # Kiểm tra Mục
            m_sec = RE_SECTION.match(line)
            if m_sec:
                sec_header = m_sec.group(1).strip()
                sec_title = (m_sec.group(2) or m_sec.group(3) or "").strip().rstrip("*#_ ").strip()
                markers.append((pos, "SECTION", sec_header, "", sec_title))
                pos += line_len
                continue

            # Kiểm tra Phụ lục
            m_app = RE_APPENDIX.match(line)
            if m_app:
                app_header = m_app.group(1).strip()
                app_id = m_app.group(2).rstrip(".:- ").strip()
                app_title = (m_app.group(3) or m_app.group(4) or "").strip().rstrip("*#_ ").strip()
                markers.append((pos, "APPENDIX", app_header, app_id, app_title))
                pos += line_len
                continue

            # Kiểm tra Bảng
            m_tab = RE_TABLE.match(line)
            if m_tab:
                tab_header = m_tab.group(1).strip()
                tab_id = m_tab.group(2).rstrip(".:- ").strip()
                tab_title = (m_tab.group(3) or m_tab.group(4) or "").strip().rstrip("*#_ ").strip()
                markers.append((pos, "TABLE", tab_header, tab_id, tab_title))
                pos += line_len
                continue

        pos += line_len

    primary_markers = [m for m in markers if m[1] in ("ARTICLE", "APPENDIX")]
    table_markers = [m for m in markers if m[1] == "TABLE"]

    # Nếu văn bản không có Điều hay Phụ lục nào (chỉ có Bảng hoặc văn bản tự do)
    if not primary_markers:
        if table_markers:
            primary_markers = table_markers
            table_markers = []
        else:
            return [
                LegalChunk(
                    chunk_id=f"{doc_code or 'doc'}_full",
                    doc_code=doc_code,
                    chapter="",
                    article="Toàn văn",
                    title=doc_title or "Nội dung văn bản",
                    content=clean_text.strip(),
                    full_text=clean_text.strip(),
                )
            ]

    chunks: List[LegalChunk] = []
    current_chapter = ""

    # Nếu có phần mở đầu trước Điều/Phụ lục đầu tiên
    first_marker_pos = primary_markers[0][0]
    if first_marker_pos > 80:
        intro_text = clean_text[:first_marker_pos].strip()
        if len(intro_text) > 40:
            chunks.append(
                LegalChunk(
                    chunk_id=f"{doc_code or 'doc'}_intro",
                    doc_code=doc_code,
                    chapter="Quy định chung",
                    article="Mở đầu",
                    title="Phần mở đầu / Phạm vi áp dụng",
                    content=intro_text,
                    full_text=intro_text,
                )
            )

    # 1. Trích xuất từng Điều luật hoặc Phụ lục chính (bảo toàn 100% không bị cắt bởi bảng nhúng)
    for i, marker in enumerate(primary_markers):
        m_pos, m_type, m_header, m_id, m_title = marker

        for prev_m in markers:
            if prev_m[0] > m_pos:
                break
            if prev_m[1] == "CHAPTER":
                current_chapter = prev_m[2]

        next_pos = primary_markers[i + 1][0] if i + 1 < len(primary_markers) else len(clean_text)
        chunk_full_text = clean_text[m_pos:next_pos].strip()

        body_lines = chunk_full_text.split("\n", 1)
        content_body = body_lines[1].strip() if len(body_lines) > 1 else ""

        if m_type == "ARTICLE":
            art_label = f"Điều {m_id}"
            chunk_id = f"{doc_code or 'doc'}_dieu_{m_id}"
        elif m_type == "APPENDIX":
            art_label = f"Phụ lục {m_id}"
            chunk_id = f"{doc_code or 'doc'}_phuluc_{m_id}"
        else:
            art_label = f"Bảng {m_id}"
            chunk_id = f"{doc_code or 'doc'}_bang_{m_id}"

        chunks.append(
            LegalChunk(
                chunk_id=chunk_id,
                doc_code=doc_code,
                chapter=current_chapter,
                article=art_label,
                title=m_title or art_label,
                content=content_body,
                full_text=chunk_full_text,
            )
        )

    # 2. Trích xuất các chunk Bảng bổ sung để hỗ trợ tra cứu chính xác theo số hiệu Bảng
    for t_marker in table_markers:
        t_pos, _, t_header, t_id, t_title = t_marker

        for prev_m in markers:
            if prev_m[0] > t_pos:
                break
            if prev_m[1] == "CHAPTER":
                current_chapter = prev_m[2]

        next_boundary = len(clean_text)
        for m in markers:
            if m[0] > t_pos and m[0] < next_boundary:
                next_boundary = m[0]

        raw_tab_text = clean_text[t_pos:next_boundary].strip()
        tab_lines = raw_tab_text.split("\n")
        filtered_lines = [tab_lines[0]]
        for l in tab_lines[1:]:
            if re.match(r"^\s*(?:[0-9]+\.\s+[A-ZÀ-Ỹ]|\bKhoản\s+[0-9]+|\bĐiều\s+[0-9]+|\bPhụ\s+lục\b|\bBảng\b)", l):
                break
            filtered_lines.append(l)

        table_full_text = "\n".join(filtered_lines).strip()
        body_lines = table_full_text.split("\n", 1)
        t_body = body_lines[1].strip() if len(body_lines) > 1 else ""

        art_label = f"Bảng {t_id}"
        chunk_id = f"{doc_code or 'doc'}_bang_{t_id}"
        chunks.append(
            LegalChunk(
                chunk_id=chunk_id,
                doc_code=doc_code,
                chapter=current_chapter,
                article=art_label,
                title=t_title or art_label,
                content=t_body,
                full_text=table_full_text,
            )
        )

    return chunks


def find_best_legal_article(content: str, query: str, doc_code: str = "") -> Optional[LegalChunk]:
    """Tìm Điều luật hoặc Phụ lục khớp chính xác nhất với truy vấn của người dùng."""
    if not content or not query:
        return None

    chunks = chunk_legal_document(doc_code, "", content)
    if not chunks:
        return None

    q_lower = query.lower().strip()
    q_norm = re.sub(r"[?!,;:()\"'*#]+", " ", q_lower)
    q_norm = re.sub(r"\s+", " ", q_norm).strip()

    # 1. Tìm theo số Điều rõ ràng (ví dụ: "Điều 5", "dieu 5", "Điều số 5", "Đ.5", "đ5")
    # Không dùng đơn ký tự 'd' đứng riêng để tránh nhận diện nhầm đường kính ống kỹ thuật (vd: d 65, d 100)
    m_dieu = re.search(
        r"(?i)(?:\b(?:điều|dieu)\s*(?:số\s*)?([0-9]{1,4})\b|\b(?:đ|d)\.\s*([0-9]{1,4})\b|\bđ([0-9]{1,4})\b)",
        q_norm,
    )
    if m_dieu:
        target_num = m_dieu.group(1) or m_dieu.group(2) or m_dieu.group(3)
        for c in chunks:
            if re.search(rf"\bĐiều\s+{re.escape(target_num)}\b", c.article, re.IGNORECASE):
                return c

    # 2. Tìm theo Phụ lục hoặc Bảng
    m_app = re.search(r"(?i)\b(?:phụ lục|phu luc)\s*([A-Z0-9]+(?:\.[A-Z0-9]+)?)\b", q_norm)
    if m_app:
        target_app = m_app.group(1).upper()
        for c in chunks:
            if (
                re.search(rf"\bPhụ\s+lục\s+{re.escape(target_app)}\b", c.article, re.IGNORECASE)
                or f"PHỤ LỤC {target_app}" in c.full_text.upper()
            ):
                return c

    m_tab = re.search(r"(?i)\b(?:bảng|bang)\s*([A-Z0-9]+(?:\.[A-Z0-9]+)?)\b", q_norm)
    if m_tab:
        target_tab = m_tab.group(1).upper()
        # Ưu tiên chunk Bảng cụ thể trước
        for c in chunks:
            if re.search(rf"\bBảng\s+{re.escape(target_tab)}\b", c.article, re.IGNORECASE):
                return c
        for c in chunks:
            if f"BẢNG {target_tab}" in c.full_text.upper():
                return c

    # 3. Phân tích ngữ nghĩa từ khóa (Semantic Keyword Scoring)
    words = [w for w in q_norm.split() if len(w) >= 2]
    topical_tokens = [w for w in words if w not in RAG_STOPWORDS and not (len(w) == 4 and w.isdigit())]
    if not topical_tokens:
        topical_tokens = words

    unaccented_tokens = [strip_vietnamese_accents(w) for w in topical_tokens]
    unaccented_query = strip_vietnamese_accents(q_norm)

    best_chunk: Optional[LegalChunk] = None
    max_score = 0

    for c in chunks:
        score = 0
        t_lower = (c.title or "").lower()
        t_unaccented = strip_vietnamese_accents(t_lower)
        art_lower = (c.article or "").lower()
        content_lower = (c.content or "").lower()
        content_unaccented = strip_vietnamese_accents(content_lower)

        # Trùng tiêu đề đầy đủ
        if unaccented_query and unaccented_query in t_unaccented:
            score += 160

        # Trùng từ khóa trong tiêu đề
        for tok, utok in zip(topical_tokens, unaccented_tokens):
            if tok in t_lower or utok in t_unaccented:
                score += 35
            if tok in art_lower:
                score += 30

        # Cụm từ ghép 2-3 từ trong nội dung
        if len(topical_tokens) >= 2:
            phrase = " ".join(topical_tokens[:3])
            uphrase = " ".join(unaccented_tokens[:3])
            if phrase in content_lower or uphrase in content_unaccented:
                score += 45

        # Mật độ và tần suất từ khóa trong nội dung
        cnt = sum(
            min(content_lower.count(tok) + content_unaccented.count(utok), 10)
            for tok, utok in zip(topical_tokens, unaccented_tokens)
        )
        score += min(cnt * 2, 35)

        if score > max_score:
            max_score = score
            best_chunk = c

    if max_score >= 35 and best_chunk:
        return best_chunk

    return None
