"""Sessions and Project Data Management Router."""
import logging
import sys
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db import get_db
from app.db_models import ChatMessage, ChatSession, InspectionLog, ProjectData, User
from app.hardening import lock_session
from app.rules_engine import evaluate_appraisal
from app.schemas_project import ProjectUpdateRequest
from app.services.session_service import (
    DEFAULT_PROJECT,
    CreateSessionRequest,
    _check_revision,
    _clear_review,
    _load_session_full,
    _log_inspection,
    _owner_filter,
    _project_fingerprint,
    _session_to_dict,
)

logger = logging.getLogger("pccc.router.sessions")

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def get_sessions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages), selectinload(ChatSession.project_data))
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    cond = _owner_filter(user)
    if cond is not None:
        stmt = stmt.where(cond)
    result = await db.execute(stmt)
    return [_session_to_dict(s) for s in result.scalars().all()]


@router.post("", status_code=201)
async def create_session(
    body: CreateSessionRequest = Body(default_factory=CreateSessionRequest),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    title = body.title
    project_overrides = body.projectInfo.model_dump(exclude_unset=True) if body.projectInfo else {}
    project_info = {**DEFAULT_PROJECT, **project_overrides}

    session = ChatSession(
        owner_id=user.id,
        title=title or "Hồ sơ mới thẩm định",
        checklist=None,
        is_subject_to_appraisal=None,
        appraisal_reason="",
        warnings=[],
    )
    db.add(session)
    await db.flush()

    project_row = ProjectData(session_id=session.id)
    project_row.apply_dict(project_info)
    db.add(project_row)

    welcome_msg = ChatMessage(
        session_id=session.id,
        sender="assistant",
        text=(
            "Xin chào! Tôi là trợ lý hỗ trợ rà soát hồ sơ PCCC. Hãy nhập công năng, số tầng, diện tích "
            "và chiều cao PCCC hoặc tải bản vẽ. Kết quả sàng lọc cần kỹ sư xác nhận; không thay thế "
            "thẩm định hoặc nghiệm thu của cơ quan có thẩm quyền."
        ),
    )
    db.add(welcome_msg)

    await db.commit()
    full = await _load_session_full(db, session.id)
    return _session_to_dict(full)


@router.get("/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await lock_session(db, session_id)
    session = await _load_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền đọc hồ sơ này.")
    return _session_to_dict(session)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    expected_revision: Optional[str] = Header(None, alias="If-Match"),
):
    await lock_session(db, session_id)
    session = await _load_session_full(db, session_id)
    if session and user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xoá hồ sơ của người khác.")
    if session:
        _check_revision(session, expected_revision)
        await db.delete(session)
        await db.commit()
    return {"success": True}


@router.put("/{session_id}/project")
async def update_session_project(
    session_id: str,
    body: ProjectUpdateRequest,
    appraise: Literal["true", "false"] = Query("false"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    expected_revision: Optional[str] = Header(None, alias="If-Match"),
):
    await lock_session(db, session_id)
    session = await _load_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền chỉnh sửa hồ sơ của người khác.")

    _check_revision(session, expected_revision)

    if not session.project_data:
        session.project_data = ProjectData(session_id=session.id)
        db.add(session.project_data)

    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    merged = {**session.project_data.to_dict(), **changes}
    if "components" in changes and changes["components"] != session.project_data.components:
        if "componentsComplete" not in changes:
            merged["componentsComplete"] = False
        old_ids = {c["id"] for c in (session.project_data.components or [])}
        new_ids = {c["id"] for c in (changes["components"] or [])}
        if old_ids != new_ids:
            for key, attribute in (("sharedSystems", "shared_systems"), ("concurrentDesign", "concurrent_design")):
                if key not in changes:
                    merged[key] = None
                    setattr(session.project_data, attribute, None)
    for count_key, array_keys in (
        ("floors", ("floorFunctions",)),
        ("basements", ("basementFunctions", "basementHeights", "basementAreas", "basementFootprints")),
    ):
        if count_key in changes:
            for key in array_keys:
                merged[key] = (merged.get(key) or [])[: changes[count_key]]
    try:
        validated = ProjectUpdateRequest.model_validate(merged)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Thông số cập nhật mâu thuẫn với hồ sơ đã lưu (diện tích/tầng).")

    session.project_data.apply_dict(validated.model_dump(exclude_none=True))
    session.project_data.source = "manual"
    session.updated_at = datetime.now(timezone.utc)
    pinfo = session.project_data.to_dict()

    should_appraise = appraise == "true"

    if should_appraise:
        main_mod = sys.modules.get("app.main")
        eval_fn = getattr(main_mod, "evaluate_appraisal", evaluate_appraisal) if main_mod else evaluate_appraisal
        evaluation = eval_fn(pinfo)
        stored = [dict(item) for item in evaluation["checklist"]]
        stored[0]["reviewedProjectHash"] = _project_fingerprint(pinfo)
        stored[0]["reviewedBasis"] = evaluation["appraisalBasis"]
        session.checklist = stored
        session.is_subject_to_appraisal = evaluation["isSubjectToAppraisal"]
        session.appraisal_reason = evaluation["appraisalReason"]
        session.warnings = evaluation["warnings"]
        message = ChatMessage(
            session_id=session.id,
            sender="assistant",
            text=evaluation["appraisalReason"] + "\n" + "\n".join(evaluation["warnings"]),
        )
        db.add(message)
        await _log_inspection(
            db,
            session,
            user.id,
            "manual_appraise",
            session.is_subject_to_appraisal,
            session.appraisal_reason,
            evaluation["checklist"],
            session.warnings,
        )
    else:
        _clear_review(session)

    await db.commit()
    full = await _load_session_full(db, session_id)
    return _session_to_dict(full)


@router.get("/{session_id}/inspection-logs")
async def session_inspection_logs(
    session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    if user.role != "admin" and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xem nhật ký của hồ sơ người khác.")
    result = await db.execute(
        select(InspectionLog).where(InspectionLog.session_id == session_id).order_by(InspectionLog.created_at.desc())
    )
    return [log.to_dict() for log in result.scalars().all()]
