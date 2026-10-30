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


def _extract_snippet(content: str, query: str, max_chars: int = 240) -> str:
    """Trích đoạn văn bản xung quanh từ khóa tìm kiếm (snippet highlight) (Ngày 3 kế hoạch)."""
    if not content or not query:
        text_content = content or ""
        snippet = text_content[:max_chars].strip()
        return snippet + ("..." if len(text_content) > max_chars else "")

    lower_content = content.lower()
    lower_query = query.lower()
    idx = lower_content.find(lower_query)
    if idx == -1:
        snippet = content[:max_chars].strip()
        return snippet + ("..." if len(content) > max_chars else "")

    half = max_chars // 2
    start = max(0, idx - half)
    end = min(len(content), idx + len(query) + half)

    snippet = content[start:end].replace("\r", " ").replace("\n", " ")
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(content) else ""
    return f"{prefix}{snippet.strip()}{suffix}"
