import re
import sys
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from app.config import MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB


def _safe_filename(name: str) -> str:
    """Chỉ dùng để đặt tên file trong header Content-Disposition (tên hiển
    thị cho người tải về) — KHÔNG được dùng để dựng đường dẫn ổ đĩa thật."""
    return re.sub(r"\s+", "_", re.sub(r"[^a-zA-Z0-9_À-ỹ\- ]", "", name))


def _generate_safe_storage_path(directory: Path, original_filename: str, allowed_extensions: set) -> tuple[Path, str]:
    """Sinh đường dẫn lưu file AN TOÀN trên đĩa từ 1 file upload.
    Chỉ giữ lại PHẦN MỞ RỘNG đã qua whitelist, còn tên file sinh ngẫu nhiên bằng uuid4 —
    loại bỏ hoàn toàn path traversal / arbitrary file write.
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng file '{ext or '(không rõ)'}' không được hỗ trợ. Chỉ chấp nhận: {', '.join(sorted(allowed_extensions))}",
        )
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return directory / safe_name, safe_name


async def _read_upload_with_size_limit(upload: UploadFile) -> bytes:
    """Đọc nội dung file upload, từ chối nếu vượt MAX_UPLOAD_SIZE_MB."""
    main_mod = sys.modules.get("app.main")
    limit_bytes = getattr(main_mod, "MAX_UPLOAD_SIZE_BYTES", MAX_UPLOAD_SIZE_BYTES) if main_mod else MAX_UPLOAD_SIZE_BYTES

    chunks = []
    size = 0
    while chunk := await upload.read(64 * 1024):
        size += len(chunk)
        if size > limit_bytes:
            raise HTTPException(status_code=413, detail=f"File vượt quá giới hạn cho phép ({MAX_UPLOAD_SIZE_MB}MB).")
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=400, detail="File rỗng.")
    return content


RAG_STOPWORDS = {
    "theo", "tiêu", "chuẩn", "quy", "luật", "nghị", "định", "thông", "tư",
    "tcvn", "qcvn", "file", "tài", "liệu", "văn", "bản", "vừa", "tải", "lên",
    "nạp", "up", "là", "gì", "bao", "nhiêu", "như", "thế", "nào", "cho", "tôi",
    "biết", "pccc", "hỏi", "về", "của", "các", "những", "trong", "được", "có",
    "và", "hoặc", "khi", "nào", "ở", "tại", "mới", "đã", "này", "bởi",
}

import unicodedata


def strip_vietnamese_accents(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để tìm kiếm & so khớp không phân biệt dấu (accent-insensitive)."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_combining = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_combining.replace("đ", "d").replace("Đ", "D").replace("Ð", "D")


def _extract_snippet(content: str, query: str, max_chars: int = 350) -> str:
    """Trích đoạn văn bản xung quanh từ khóa tìm kiếm (snippet highlight) (Ngày 3 kế hoạch)."""
    if not content:
        return ""
    if not query:
        snippet = content[:max_chars].strip()
        return snippet + ("..." if len(content) > max_chars else "")

    lower_content = content.lower()
    lower_query = query.lower().strip()

    # 1. Tách các token truy vấn ngữ nghĩa (loại trừ từ dừng và mã hiệu văn bản phổ biến)
    tokens = [t for t in re.split(r"[\s_\-:/.,?!()]+", lower_query) if len(t) >= 2]
    topical_tokens = [t for t in tokens if t not in RAG_STOPWORDS and not (len(t) == 4 and t.isdigit())]

    idx = -1
    # 2. Thử tìm cụm từ ngữ nghĩa ghép từ 2-4 token liên tiếp
    if len(topical_tokens) >= 2:
        for window_size in range(min(4, len(topical_tokens)), 1, -1):
            for i in range(len(topical_tokens) - window_size + 1):
                phrase = " ".join(topical_tokens[i : i + window_size])
                pos = lower_content.find(phrase)
                if pos != -1:
                    idx = pos
                    break
            if idx != -1:
                break

    # 3. Tìm vị trí xuất hiện của block có mật độ từ khóa ngữ nghĩa cao nhất
    if idx == -1 and topical_tokens:
        best_pos = -1
        max_score = 0
        step = 250
        for block_start in range(0, min(len(lower_content), 120_000), step):
            block = lower_content[block_start : block_start + 800]
            score = sum(10 for t in topical_tokens if t in block)
            if score > max_score:
                max_score = score
                best_pos = block_start

        if max_score > 0 and best_pos != -1:
            first_tok_pos = len(lower_content)
            for t in topical_tokens:
                p = lower_content.find(t, best_pos, best_pos + 800)
                if p != -1 and p < first_tok_pos:
                    first_tok_pos = p
            idx = first_tok_pos if first_tok_pos < len(lower_content) else best_pos

    # 4. Fallback tìm nguyên văn query hoặc token bất kỳ
    if idx == -1:
        idx = lower_content.find(lower_query)
    if idx == -1 and tokens:
        for t in tokens:
            p = lower_content.find(t)
            if p != -1:
                idx = p
                break

    # 5. Fallback tìm kiếm không dấu (accent-insensitive)
    if idx == -1:
        stripped_content = strip_vietnamese_accents(lower_content)
        stripped_query = strip_vietnamese_accents(lower_query)
        pos = stripped_content.find(stripped_query)
        if pos != -1:
            idx = pos
        else:
            stripped_topical = [strip_vietnamese_accents(t) for t in topical_tokens if len(t) >= 3]
            for st in stripped_topical:
                p = stripped_content.find(st)
                if p != -1:
                    idx = p
                    break

    if idx == -1:
        idx = 0

    half = max_chars // 2
    start = max(0, idx - 40)
    end = min(len(content), start + max_chars)

    snippet = content[start:end].replace("\r", " ").replace("\n", " ")
    snippet = re.sub(r"\s+", " ", snippet).strip()
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(content) else ""
    return f"{prefix}{snippet}{suffix}"


def _extract_rich_context(content: str, query: str, max_chars: int = 2500) -> str:
    """Trích xuất khối nội dung chuyên sâu (nhiều điều khoản/bảng biểu) phục vụ Gemini RAG reasoning."""
    if not content:
        return ""
    lower_content = content.lower()
    lower_query = query.lower().strip()

    tokens = [t for t in re.split(r"[\s_\-:/.,?!()]+", lower_query) if len(t) >= 2]
    topical_tokens = [t for t in tokens if t not in RAG_STOPWORDS and not (len(t) == 4 and t.isdigit())]

    idx = -1
    # 1. Tìm cụm từ ngữ nghĩa chính xác
    if len(topical_tokens) >= 2:
        for ws in range(min(4, len(topical_tokens)), 1, -1):
            for i in range(len(topical_tokens) - ws + 1):
                phrase = " ".join(topical_tokens[i : i + ws])
                p = lower_content.find(phrase)
                if p != -1:
                    idx = p
                    break
            if idx != -1:
                break

    # 2. Tìm block có mật độ từ khóa kỹ thuật cao nhất
    if idx == -1 and topical_tokens:
        best_pos = -1
        max_score = 0
        step = 300
        for b_start in range(0, min(len(lower_content), 120_000), step):
            block = lower_content[b_start : b_start + 1200]
            sc = sum(10 for t in topical_tokens if t in block)
            if sc > max_score:
                max_score = sc
                best_pos = b_start
        if max_score > 0 and best_pos != -1:
            idx = best_pos

    # 3. Fallback tìm cụm từ hoặc từ khóa không dấu (accent-insensitive)
    if idx == -1:
        stripped_content = strip_vietnamese_accents(lower_content)
        stripped_query = strip_vietnamese_accents(lower_query)
        p = stripped_content.find(stripped_query)
        if p != -1:
            idx = p
        else:
            stripped_topical = [strip_vietnamese_accents(t) for t in topical_tokens if len(t) >= 3]
            for st in stripped_topical:
                p = stripped_content.find(st)
                if p != -1:
                    idx = p
                    break

    if idx == -1:
        preamble = re.search(r"(?i)(?:phạm vi áp dụng|quy định chung|1\.\s+phạm vi)", lower_content)
        idx = preamble.start() if preamble else 0

    start = max(0, idx - 60)
    end = min(len(content), start + max_chars)
    return content[start:end].strip()

