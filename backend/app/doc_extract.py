"""Text extraction for uploaded .txt / .docx / .pdf legal documents.

Port of the extraction branch inside POST /api/documents/upload in server.ts:
- .txt  -> read as-is                      (fs.readFileSync)
- .docx -> mammoth.extractRawText          -> docx2txt.process
- .pdf  -> pdf-parse                       -> pypdf.PdfReader
"""
import logging
import re

import docx2txt
from pypdf import PdfReader

logger = logging.getLogger("pccc.doc_extract")


def extract_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="strict") as f:
        return f.read()


def extract_docx(path: str) -> str:
    return docx2txt.process(path) or ""


def extract_pdf(path: str, original_filename: str) -> str:
    try:
        reader = PdfReader(path)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        if text.strip():
            return text
        raise ValueError("PDF không có lớp văn bản. Cần OCR trước khi nạp thư viện.")
    except Exception:
        logger.exception("Không trích xuất được PDF")
        raise


def sanitize_text(text: str) -> str:
    """Strip control bytes & null terminators, matching the JS regex sanitation."""
    text = (text or "").replace("\u0000", "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    return text.strip()
