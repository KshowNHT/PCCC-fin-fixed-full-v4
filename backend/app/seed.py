"""Khởi tạo dữ liệu mặc định khi database còn trống.

- Admin mặc định (đăng nhập lần đầu, giữ tương thích placeholder admin/admin
  của Login.tsx cũ, nhưng mật khẩu mạnh hơn — xem PCCC_ADMIN_PASSWORD).
- 18 tài liệu pháp lý mặc định (từ default_documents.py, đồng nhất với bản
  JSON-file trước đây, giờ ghi thẳng vào bảng documents).
"""
import logging

from sqlalchemy import func, select, text

from pathlib import Path
from typing import Dict, Optional

from app.auth import hash_password
from app.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from app.db import AsyncSessionLocal
from app.db_models import Document, User
from app.default_documents import DEFAULT_DOCUMENTS

logger = logging.getLogger("pccc.seed")

QC_TC_DOC_MAPPING: Dict[str, str] = {
    "doc_5": "QCVN 02-2020 Tram bom nuoc chua chay.pdf",
    "doc_4": "QCVN 01-2020.pdf",
    "doc_8": "QC13.2018.pdf",
    "doc_7": "QCVN 10.docx",
    "doc_6": "Sửa đổi 1 2023 QCVN 06 2022.pdf",
    "doc_17": "TCVN 13456-2022 PCCC phuong tien chieu sang su co va chi dan thoat nan yeu cau thiet ke lap dat.pdf",
    "doc_18": "TCVN 14496-2025-pccc-he-thong-chua-chay-tu-dong-bang-nuoc-cho-nha-kho.pdf",
    "doc_10": "TCVN 5687 - 2024 - ThongGio, DHKK.pdf",
    "doc_12": "TCVN 7161_9_2009 [Dep].pdf",
    "doc_13": "TCVN 7336_2021.doc",
    "doc_15": "TCVN 7568-14.2025 - Bao chay tu dong.pdf",
    "doc_16": "TCVN 9385- 2012 - CHONG SET.pdf",
    "doc_9": "TCVN_2622-1995.pdf",
    "doc_14": "TCVN 7435_1_2004.pdf",
    "doc_2": "Nghị định 105 mới 2025/Nghị định 105 ngày 15.5.2025.docx",
    "doc_19": "TCVN_12110_2018.doc",
    "doc_20": "TCVN_13333-2021.doc",
    "doc_21": "TCVN_13657_1_2023.docx",
    "doc_22": "TCVN_7568_25_2023.doc",
}


def _load_document_text_from_file(doc_id: str, default_content: str) -> str:
    rel_path = QC_TC_DOC_MAPPING.get(doc_id)
    if not rel_path:
        return default_content

    base_dir = Path(r"D:\PCCC_doc\QC -TC")
    full_path = base_dir / rel_path
    if not full_path.exists():
        return default_content

    try:
        from app.doc_extract import extract_doc, extract_docx, extract_pdf, sanitize_text

        ext = full_path.suffix.lower()
        if ext == ".pdf":
            raw = extract_pdf(str(full_path), full_path.name)
        elif ext == ".docx":
            raw = extract_docx(str(full_path))
        elif ext == ".doc":
            raw = extract_doc(str(full_path))
        else:
            return default_content

        clean = sanitize_text(raw)
        if len(clean) > 200:
            return clean
    except Exception as e:
        logger.warning("Không nạp được toàn văn cho %s từ %s: %s", doc_id, full_path, e)

    return default_content


async def seed_initial_data() -> None:
    async with AsyncSessionLocal() as db:
        if db.bind.dialect.name == "postgresql":
            await db.execute(text("SELECT pg_advisory_xact_lock(72190000)"))
        user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        if user_count == 0:
            admin = User(
                username=DEFAULT_ADMIN_USERNAME,
                full_name="Quản trị viên hệ thống",
                hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            logger.info(
                "[Seed] Đã tạo tài khoản admin mặc định: %s (dùng mật khẩu đã đặt trong PCCC_ADMIN_PASSWORD ở .env). "
                "Đổi mật khẩu ngay sau lần đăng nhập đầu qua PUT /api/auth/me/password.",
                DEFAULT_ADMIN_USERNAME,
            )

        # Tối ưu hóa: Nạp toàn bộ danh sách Document hiện có trong CSDL bằng 1 truy vấn duy nhất
        # thay vì 24 round-trips mạng tuần tự tới PostgreSQL (giảm mạnh thời gian Cold Start)
        existing_docs_result = await db.execute(select(Document))
        existing_map = {d.id: d for d in existing_docs_result.scalars().all()}

        if not existing_map:
            for d in DEFAULT_DOCUMENTS:
                content = _load_document_text_from_file(d["id"], d["content"])
                new_doc = Document(
                    id=d["id"],
                    code=d["code"],
                    title=d["title"],
                    type=d["type"],
                    link=d["link"],
                    content=content,
                    is_custom=False,
                )
                db.add(new_doc)
                existing_map[d["id"]] = new_doc
            logger.info("[Seed] Đã nạp %d tài liệu pháp lý mặc định vào PostgreSQL.", len(DEFAULT_DOCUMENTS))

        # Đồng bộ và cập nhật văn bản toàn văn thực thụ (thay thế placeholder tóm tắt cũ)
        for item in DEFAULT_DOCUMENTS:
            existing = existing_map.get(item["id"])
            if existing is None:
                content = _load_document_text_from_file(item["id"], item["content"])
                db.add(Document(
                    id=item["id"],
                    code=item["code"],
                    title=item["title"],
                    type=item["type"],
                    link=item["link"],
                    content=content,
                    is_custom=False,
                ))
            elif not existing.is_custom:
                # Nếu nội dung cũ là placeholder hoặc có file toàn văn chi tiết hơn từ thư mục QC-TC
                loaded = _load_document_text_from_file(item["id"], item["content"])
                if len(loaded) > len(existing.content or "") or "chưa có toàn văn" in (existing.content or ""):
                    existing.content = loaded

        await db.commit()
