"""Upload resource limits, stored-file confinement, and PostgreSQL writer locks."""
import hashlib
import io
import zipfile
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import text


def validate_upload(content: bytes, extension: str) -> None:
    def reject(message):
        raise HTTPException(status_code=422, detail=message)
    if extension == ".txt":
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            reject("TXT phải dùng mã hóa UTF-8.")
        if b"\x00" in content:
            reject("File TXT chứa dữ liệu nhị phân.")
    elif extension == ".pdf":
        if not content.lstrip().startswith(b"%PDF-"):
            reject("Nội dung file không phải PDF.")
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(content))
            if reader.is_encrypted or not reader.pages or len(reader.pages) > 200:
                reject("PDF bị khóa, rỗng hoặc vượt 200 trang.")
        except HTTPException:
            raise
        except Exception:
            reject("PDF bị hỏng hoặc không đọc được.")
    elif extension == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                items = archive.infolist()
                if len(items) > 2000 or sum(x.file_size for x in items) > 50 * 1024 * 1024:
                    reject("DOCX quá lớn sau giải nén.")
                if "word/document.xml" not in archive.namelist():
                    reject("File không phải tài liệu DOCX.")
                for item in items:
                    if item.flag_bits & 1 or item.file_size > 20 * 1024 * 1024:
                        reject("DOCX bị khóa hoặc có thành phần quá lớn.")
                    if item.file_size / max(item.compress_size, 1) > 200:
                        reject("DOCX có tỷ lệ nén bất thường.")
        except HTTPException:
            raise
        except (zipfile.BadZipFile, ValueError):
            reject("File DOCX bị hỏng.")
    else:
        from PIL import Image
        expected = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
        try:
            with Image.open(io.BytesIO(content)) as img:
                if img.format != expected.get(extension) or img.width * img.height > 20_000_000:
                    reject("Ảnh sai định dạng hoặc vượt 20 triệu điểm ảnh.")
                img.verify()
        except HTTPException:
            raise
        except Exception:
            reject("Ảnh bị hỏng hoặc không đọc được.")


def resolve_stored_file(link: str, uploads: Path, legal: Path):
    for prefix, base in (("/data/uploads/", uploads), ("/data/legal_db/", legal)):
        if link.startswith(prefix):
            path = (base / link[len(prefix):]).resolve()
            if not path.is_relative_to(base.resolve()) or path == base.resolve():
                raise HTTPException(status_code=400, detail="Đường dẫn tài liệu không hợp lệ.")
            return path
    return None


async def lock_session(db, session_id: str):
    # Cross-process transaction lock: prevents chat/OCR/manual writers overwriting one another.
    # SQLite is supported ONLY by isolated automated tests, never production.
    if db.bind.dialect.name == "postgresql":
        key = int.from_bytes(hashlib.sha256(session_id.encode()).digest()[:8], "big", signed=True)
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
