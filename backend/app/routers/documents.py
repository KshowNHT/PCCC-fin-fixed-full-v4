"""Documents Management and Legal Search Router."""
import logging
from pathlib import Path
import re
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.config import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    LEGAL_DB_DIR,
    MAX_UPLOAD_SIZE_BYTES,
    UPLOADS_DIR,
)
from app.db import get_db
from app.db_models import Document, User
from app.doc_extract import (
    detect_document_metadata,
    extract_doc,
    extract_docx,
    extract_pdf,
    extract_pdf_async,
    extract_txt,
    sanitize_text,
)
from app.hardening import resolve_stored_file, validate_upload
from app.pdf_report import generate_document_pdf
from app.utils_file import (
    _extract_snippet,
    _generate_safe_storage_path,
    _read_upload_with_size_limit,
    _safe_filename,
    strip_vietnamese_accents,
)

logger = logging.getLogger("pccc.router.documents")

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def get_documents(
    full: bool = Query(False, description="Trả toàn bộ nội dung văn bản thay vì bản trích lược 8000 ký tự đầu"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if full:
        result = await db.execute(
            select(Document).order_by(Document.is_custom.desc(), Document.uploaded_at.desc(), Document.code.asc())
        )
        return [d.to_dict() for d in result.scalars().all()]

    stmt = select(
        Document.id,
        Document.code,
        Document.title,
        Document.type,
        Document.link,
        func.substr(Document.content, 1, 8000).label("content_preview"),
        Document.is_custom,
        Document.uploaded_at,
    ).order_by(Document.is_custom.desc(), Document.uploaded_at.desc(), Document.code.asc())
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "title": r.title,
            "type": r.type,
            "link": r.link,
            "content": r.content_preview or "",
            "isCustom": r.is_custom,
            "uploadedAt": r.uploaded_at.isoformat() if r.uploaded_at else None,
        }
        for r in rows
    ]


@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=1, max_length=200, description="Từ khóa tìm kiếm trong mã hiệu, tiêu đề hoặc nội dung văn bản luật"),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),  # noqa: A002
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ngày 3 kế hoạch: Tìm kiếm sâu trong toàn bộ kho luật PCCC kèm trích đoạn snippet."""
    clean_q = q.strip()
    if not clean_q:
        return []

    stmt = select(Document)
    if type and type.strip():
        stmt = stmt.where(Document.type == type.strip())
    result = await db.execute(stmt)
    docs = result.scalars().all()

    lower_q = clean_q.lower()
    norm_q = re.sub(r"[\s_\-:/]+", " ", lower_q).strip()
    stripped_q = strip_vietnamese_accents(lower_q)
    stripped_norm_q = re.sub(r"[\s_\-:/]+", " ", stripped_q).strip()

    words = [w for w in re.split(r"[\s_\-:/]+", lower_q) if w]
    stripped_words = [strip_vietnamese_accents(w) for w in words if len(w) >= 2]
    numbers = re.findall(r"\b\d+\b", clean_q)

    scored_results = []
    for doc in docs:
        d_code = (doc.code or "").lower()
        d_title = (doc.title or "").lower()
        d_content = (doc.content or "").lower()

        d_code_stripped = strip_vietnamese_accents(d_code)
        d_title_stripped = strip_vietnamese_accents(d_title)
        d_content_stripped = strip_vietnamese_accents(d_content)
        norm_code_stripped = re.sub(r"[\s_\-:/]+", " ", d_code_stripped).strip()

        score = 0
        match_type = "other"

        # 1. Khớp mã hiệu
        code_matched = False
        if d_code in lower_q or d_code_stripped in stripped_q:
            score += 100
            code_matched = True
        elif bool(norm_code_stripped) and (norm_code_stripped in stripped_norm_q or stripped_norm_q in norm_code_stripped):
            score += 90
            code_matched = True
        elif any(num in d_code for num in numbers if len(num) >= 2):
            matched_nums = sum(1 for num in numbers if re.search(r"(?<!\d)" + num + r"(?!\d)", d_code))
            if matched_nums > 0:
                score += matched_nums * 45
                code_matched = True

        # 2. Khớp tiêu đề
        title_matched = False
        if stripped_q in d_title_stripped or (bool(stripped_norm_q) and stripped_norm_q in d_title_stripped):
            score += 70
            title_matched = True
        else:
            title_word_matches = sum(1 for w in stripped_words if w in d_title_stripped)
            if title_word_matches > 0:
                score += title_word_matches * 15
                title_matched = True

        # 3. Khớp tổ hợp từ khóa trong toàn bộ (mã hiệu + tiêu đề + nội dung)
        combined_meta = f"{norm_code_stripped} {d_title_stripped}"
        if stripped_words:
            all_in_meta = all(w in combined_meta for w in stripped_words)
            if all_in_meta:
                score += 85
                code_matched = True
                title_matched = True

        # 4. Khớp nội dung
        content_word_matches = sum(1 for w in stripped_words if len(w) >= 3 and w in d_content_stripped)
        if content_word_matches > 0:
            score += min(content_word_matches * 5, 35)

        if code_matched and title_matched:
            match_type = "code_and_title"
        elif code_matched:
            match_type = "code"
        elif title_matched:
            match_type = "title"
        elif content_word_matches > 0:
            match_type = "content"

        if score > 0:
            if doc.is_custom:
                score += 50

            snippet = _extract_snippet(doc.content or "", clean_q)
            scored_results.append({
                "id": doc.id,
                "code": doc.code,
                "title": doc.title,
                "type": doc.type,
                "link": doc.link,
                "content": doc.content,
                "isCustom": doc.is_custom,
                "uploadedAt": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "snippet": snippet,
                "matchType": match_type,
                "score": score,
            })

    scored_results.sort(key=lambda x: x["score"], reverse=True)
    return scored_results[:limit]



@router.post("/upload", status_code=201)
async def upload_documents(
    file: List[UploadFile] = File(...),
    code: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    type: Optional[str] = Form(None),  # noqa: A002
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if not file or len(file) > 10:
        raise HTTPException(status_code=400, detail="Chọn từ 1 đến 10 file mỗi lần.")
    if type and len(type) > 64:
        raise HTTPException(status_code=422, detail="Loại tài liệu tối đa 64 ký tự.")
    created_docs, written_paths = [], []
    total_size = 0
    try:
        for i, upload in enumerate(file):
            original_name = upload.filename or f"file_{i}"
            dest_path, stored_name = _generate_safe_storage_path(LEGAL_DB_DIR, original_name, ALLOWED_DOCUMENT_EXTENSIONS)
            ext = dest_path.suffix
            content = await _read_upload_with_size_limit(upload)
            total_size += len(content)
            if total_size > MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(status_code=413, detail="Tổng dung lượng file vượt giới hạn upload.")
            await run_in_threadpool(validate_upload, content, ext)
            written_paths.append(dest_path)
            await run_in_threadpool(dest_path.write_bytes, content)
            if ext == ".txt":
                extracted = await run_in_threadpool(extract_txt, str(dest_path))
            elif ext == ".docx":
                extracted = await run_in_threadpool(extract_docx, str(dest_path))
            elif ext == ".doc":
                extracted = await run_in_threadpool(extract_doc, str(dest_path))
            else:
                extracted = await extract_pdf_async(str(dest_path), original_name)
            safe_text = sanitize_text(extracted)
            if not safe_text:
                raise HTTPException(status_code=422, detail="Không có văn bản có thể đọc. Hãy OCR tài liệu trước khi nạp vào thư viện.")
            if len(safe_text) > 2_000_000:
                raise HTTPException(status_code=413, detail="Nội dung trích xuất quá lớn.")
            base = sanitize_text(Path(original_name.replace("\\", "/")).stem)[:255]
            auto_meta = detect_document_metadata(original_name, safe_text)
            doc_code = (code or "").strip() if len(file) == 1 else ""
            doc_title = (title or "").strip() if len(file) == 1 else ""
            doc_type = (type or "").strip() if type and type.strip() and type not in ("Khác", "Tự động") else auto_meta["type"]

            final_code = (doc_code or auto_meta["code"] or base.upper() or "VANBAN")[:255]
            final_title = (doc_title or auto_meta["title"] or base.replace("_", " ") or "Tài liệu")[:500]

            new_doc = Document(
                code=final_code,
                title=final_title,
                type=doc_type or "Khác",
                link=f"/data/legal_db/{stored_name}",
                content=safe_text,
                is_custom=True,
                uploaded_by=admin.id,
            )
            db.add(new_doc)
            created_docs.append(new_doc)
        await db.flush()
        result = [d.to_dict() for d in created_docs]
        await db.commit()
        return result[0] if len(result) == 1 else result
    except Exception as err:
        await db.rollback()
        for path in written_paths:
            path.unlink(missing_ok=True)
        if isinstance(err, HTTPException):
            raise
        if isinstance(err, ValueError):
            raise HTTPException(status_code=422, detail=str(err))
        logger.exception("Upload tài liệu thất bại")
        raise HTTPException(status_code=422, detail="File không hợp lệ hoặc không thể trích xuất. Kiểm tra lại tài liệu.")


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu cần xóa.")

    path = resolve_stored_file(doc.link or "", UPLOADS_DIR, LEGAL_DB_DIR) if doc.is_custom else None
    await db.delete(doc)
    await db.commit()
    if path:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Không dọn được file đã xóa metadata; cần dọn volume khi bảo trì")
    return {"success": True, "message": "Đã xóa tài liệu khỏi danh mục RAG."}


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    format: Optional[str] = Query(None),  # noqa: A002
    inline: Optional[bool] = Query(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu để tải về.")
    doc_dict = doc.to_dict()
    disp_type = "inline" if inline else "attachment"

    if format == "pdf":
        if doc.is_custom:
            actual_path = None
            link = doc.link or ""
            if link.startswith("/data/uploads/") or link.startswith("/data/legal_db/"):
                actual_path = resolve_stored_file(link, UPLOADS_DIR, LEGAL_DB_DIR)
            if actual_path and actual_path.exists() and link.lower().endswith(".pdf"):
                safe_title = _safe_filename(doc.title)
                return FileResponse(
                    str(actual_path),
                    media_type="application/pdf",
                    content_disposition_type=disp_type,
                    filename=f"{safe_title}.pdf",
                )

        pdf_bytes = await run_in_threadpool(generate_document_pdf, doc_dict)
        safe_filename = _safe_filename(doc.title) + ".pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"{disp_type}; filename={quote(safe_filename)}"},
        )

    if doc.is_custom:
        link = doc.link or ""
        actual_path, filename = None, ""
        if link.startswith("/data/uploads/"):
            filename = link.replace("/data/uploads/", "")
            actual_path = resolve_stored_file(link, UPLOADS_DIR, LEGAL_DB_DIR)
        elif link.startswith("/data/legal_db/"):
            filename = link.replace("/data/legal_db/", "")
            actual_path = resolve_stored_file(link, UPLOADS_DIR, LEGAL_DB_DIR)
        if actual_path and actual_path.exists():
            safe_title = _safe_filename(doc.title)
            ext = Path(filename).suffix
            return FileResponse(str(actual_path), filename=f"{safe_title}{ext}")

    safe_title = _safe_filename(doc.title)
    file_content = (
        f"KÝ HIỆU: {doc.code}\nTIÊU ĐỀ: {doc.title}\nLOẠI VĂN BẢN: {doc.type}\n\n"
        f"NỘI DUNG PHÁP LÝ:\n----------------------------------------\n{doc.content}\n"
    )
    return Response(
        content=file_content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={quote(safe_title)}.txt"},
    )


@router.get("/{doc_id}/preview")
async def preview_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ngày 3 kế hoạch: Xem trực tiếp file PDF văn bản luật gốc ngay trên màn hình phần mềm."""
    return await download_document(doc_id=doc_id, format="pdf", inline=True, db=db, user=user)


@router.post("/reset")
async def reset_documents(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Chỉ admin được reset toàn bộ thư viện pháp lý dùng chung (Ngày 2 kế hoạch)."""
    from app.default_documents import DEFAULT_DOCUMENTS
    from app.seed import _load_document_text_from_file

    old_docs = (await db.execute(select(Document).where(Document.is_custom.is_(True)))).scalars().all()
    paths = [resolve_stored_file(d.link, UPLOADS_DIR, LEGAL_DB_DIR) for d in old_docs]
    await db.execute(delete(Document))
    for d in DEFAULT_DOCUMENTS:
        content = _load_document_text_from_file(d["id"], d["content"])
        db.add(
            Document(
                id=d["id"],
                code=d["code"],
                title=d["title"],
                type=d["type"],
                link=d["link"],
                content=content,
                is_custom=False,
            )
        )
    await db.commit()
    for path in paths:
        if path:
            path.unlink(missing_ok=True)
    result = await db.execute(select(Document).order_by(Document.is_custom.desc(), Document.uploaded_at.desc(), Document.code.asc()))
    return [d.to_dict() for d in result.scalars().all()]

