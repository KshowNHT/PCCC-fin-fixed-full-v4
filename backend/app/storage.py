"""Tải trước font Roboto (hỗ trợ tiếng Việt) dùng cho PDF export.

Lưu ý: phần lưu trữ "database" JSON-file của bản v1 (`Store` class) đã được
thay thế hoàn toàn bằng PostgreSQL (xem app/db.py, app/db_models.py,
app/seed.py). Module này chỉ còn giữ lại trách nhiệm tải font.
"""
import logging

import httpx

from app.config import BOLD_FONT_PATH, BOLD_FONT_URL, REGULAR_FONT_PATH, REGULAR_FONT_URL

logger = logging.getLogger("pccc.storage")


async def ensure_fonts_exist() -> None:
    try:
        if not REGULAR_FONT_PATH.exists():
            logger.info("[PDFFont] Downloading Regular font for compliance reports...")
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(REGULAR_FONT_URL)
                resp.raise_for_status()
                REGULAR_FONT_PATH.write_bytes(resp.content)
            logger.info("[PDFFont] Regular font cached successfully.")
        if not BOLD_FONT_PATH.exists():
            logger.info("[PDFFont] Downloading Bold font for compliance reports...")
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(BOLD_FONT_URL)
                resp.raise_for_status()
                BOLD_FONT_PATH.write_bytes(resp.content)
            logger.info("[PDFFont] Bold font cached successfully.")
    except Exception as err:  # noqa: BLE001
        logger.error("[PDFFont] Failed to preheat fonts stream. Standard fallback will be used: %s", err)
