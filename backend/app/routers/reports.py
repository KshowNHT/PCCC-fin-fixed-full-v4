"""Reports Generation and Export Router (Word, PDF, JSON)."""
import json
import logging
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.db_models import User
from app.docx_report import generate_pccc_report
from app.hardening import lock_session
from app.pdf_report import generate_compliance_report_pdf
from app.services.session_service import (
    _check_revision,
    _is_reviewed,
    _load_session_full,
    _now_iso,
    _session_to_dict,
)

logger = logging.getLogger("pccc.router.reports")

router = APIRouter(prefix="/api/report", tags=["reports"])


def _export_conclusions(project_info: dict, warnings: list, basis: dict) -> dict:
    """Kết luận dùng cho báo cáo Word/PDF/JSON."""
    return {
        "appraisalBasis": basis,
        "status": basis["status"],
        "isAppraisalRequired": basis["status"] == "required",
        "reason": basis["conclusion"],
        "basisText": f"Nhóm công năng áp dụng: {basis['categoryLabel']}. {basis['legalText']}",
        "warnings": warnings,
    }


async def _resolve_export_data(body: dict, db: AsyncSession, user: User) -> tuple[dict, list, dict]:
    """Lấy dữ liệu đã thẩm định từ cơ sở dữ liệu trên server."""
    session_id = body.get("sessionId")
    if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
        raise HTTPException(status_code=422, detail="Cần sessionId hợp lệ để xuất báo cáo.")

    await lock_session(db, session_id)
    session = await _load_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat để xuất báo cáo.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xuất báo cáo của hồ sơ người khác.")

    _check_revision(session, body.get("expectedRevision"))
    if not _is_reviewed(session):
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ chưa kiểm duyệt hoặc thông số đã thay đổi. Bấm Kiểm duyệt hồ sơ trước khi xuất báo cáo.",
        )

    project_info = session.project_data.to_dict() if session.project_data else {}
    payload = _session_to_dict(session)
    if project_info.get("components"):
        ignored = (
            "type",
            "floors",
            "basements",
            "height",
            "pcccHeight",
            "floorArea",
            "totalFloorArea",
            "fireRating",
            "volume",
            "hazardClass",
            "industrialSubtype",
        )
        legacy = {key: project_info.get(key) for key in ignored}
        project_info = {
            **project_info,
            "assessmentScope": "components",
            "legacySingleBuildingInput": legacy,
            "type": "Dự án nhiều hạng mục — xem danh sách từng nhà",
            "fireRating": "",
            "hazardClass": "",
            "industrialSubtype": "",
        }
        for key in ("floors", "basements", "height", "pcccHeight", "floorArea", "totalFloorArea", "volume"):
            project_info[key] = 0
    return (
        project_info,
        payload["checklist"] or [],
        _export_conclusions(project_info, payload["warnings"] or [], payload["appraisalBasis"]),
    )


@router.post("/export")
async def export_report_docx(
    body: dict = Body(default={}), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    project_info, checklist, conclusions = await _resolve_export_data(body, db, user)
    try:
        buffer = await run_in_threadpool(generate_pccc_report, project_info, checklist, conclusions)
        filename = f"Tu_van_PCCC_{str(project_info.get('name', '')).replace(' ', '_')}.docx"
        return Response(
            content=buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={quote(filename)}"},
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Lỗi kết xuất báo cáo Word: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Lỗi kết xuất báo cáo Word. Vui lòng thử lại hoặc liên hệ quản trị viên."
        )


@router.post("/export-pdf")
async def export_report_pdf(
    body: dict = Body(default={}), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    project_info, checklist, conclusions = await _resolve_export_data(body, db, user)
    try:
        filename = f"Tu_van_PCCC_{str(project_info.get('name', '')).replace(' ', '_')}.pdf"
        pdf_bytes = await run_in_threadpool(generate_compliance_report_pdf, project_info, checklist, conclusions)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={quote(filename)}"},
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Lỗi kết xuất báo cáo PDF: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Lỗi kết xuất báo cáo PDF. Vui lòng thử lại hoặc liên hệ quản trị viên."
        )


@router.post("/export-json")
async def export_report_json(
    body: dict = Body(default={}), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    project_info, checklist, conclusions = await _resolve_export_data(body, db, user)
    payload = {
        "exportedAt": _now_iso(),
        "projectInfo": project_info,
        "checklist": checklist,
        "conclusions": conclusions,
    }
    filename = f"Tu_van_PCCC_{str(project_info.get('name', '')).replace(' ', '_')}.json"
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={quote(filename)}"},
    )

