"""Session Service / Controller logic for PCCC project sessions and inspection logs."""
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import NODE_ENV
from app.db_models import ChatSession, InspectionLog, ProjectData, User
from app.ai_guard import guard_reply, guard_warnings, sanitize_extracted_info
from app.rules_engine import evaluate_appraisal
from app.schemas_project import ProjectUpdateRequest

logger = logging.getLogger("pccc.service.session")

DEFAULT_PROJECT = {
    "name": "Dự án mới", "location": "", "investor": "", "designer": "",
    "stage": "", "type": "",
    "length": 0, "width": 0, "height": 0, "pcccHeight": 0, "floorArea": 0,
    "totalFloorArea": 0, "floors": 0, "basements": 0, "fireRating": "",
    "commercialDetails": "",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _load_session_full(db: AsyncSession, session_id: str) -> Optional[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .options(selectinload(ChatSession.messages), selectinload(ChatSession.project_data))
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


def _session_revision(session: ChatSession) -> str:
    stamp = session.updated_at
    if stamp and stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    data = {
        "updatedAt": stamp.astimezone(timezone.utc).isoformat() if stamp else None,
        "project": session.project_data.to_dict() if session.project_data else dict(DEFAULT_PROJECT),
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _check_revision(session: ChatSession, expected: Optional[str]) -> None:
    main_mod = sys.modules.get("app.main")
    env = getattr(main_mod, "NODE_ENV", NODE_ENV) if main_mod else NODE_ENV

    if expected is None:
        if env == "production":
            raise HTTPException(status_code=428, detail="Cần phiên bản hồ sơ. Tải lại trang trước khi tiếp tục.")
        return
    if not isinstance(expected, str) or not re.fullmatch(r'"?[a-f0-9]{64}"?', expected):
        raise HTTPException(status_code=422, detail="Mã phiên bản hồ sơ không hợp lệ.")
    if expected.strip('"') != _session_revision(session):
        raise HTTPException(
            status_code=412,
            detail="Hồ sơ đã được thay đổi ở phiên khác. Tải lại hồ sơ trước khi tiếp tục; dữ liệu chưa được ghi đè.",
        )


def _project_fingerprint(project: dict) -> str:
    return hashlib.sha256(json.dumps(project, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _is_reviewed(session: ChatSession) -> bool:
    project = session.project_data.to_dict() if session.project_data else dict(DEFAULT_PROJECT)
    first = session.checklist[0] if session.checklist and isinstance(session.checklist[0], dict) else {}
    return (
        first.get("reviewedProjectHash") == _project_fingerprint(project)
        and isinstance(first.get("reviewedBasis"), dict)
        and first["reviewedBasis"].get("rulesVersion") == "v11.3-347-2026-annexIII"
    )


def _clear_review(session: ChatSession) -> None:
    session.checklist = None
    session.is_subject_to_appraisal = None
    session.appraisal_reason = ""
    session.warnings = []


def _session_to_dict(session: ChatSession) -> dict:
    project = session.project_data.to_dict() if session.project_data else dict(DEFAULT_PROJECT)
    reviewed = _is_reviewed(session)
    basis = session.checklist[0]["reviewedBasis"] if reviewed else None
    checklist = (
        [{k: v for k, v in item.items() if k not in {"reviewedProjectHash", "reviewedBasis"}} for item in session.checklist]
        if reviewed
        else []
    )
    return {
        "id": session.id,
        "title": session.title,
        "projectInfo": project,
        "messages": [m.to_dict() for m in session.messages],
        "updatedAt": session.updated_at.isoformat() if session.updated_at else _now_iso(),
        "revision": _session_revision(session),
        "reviewState": "reviewed" if reviewed else "draft",
        "checklist": checklist,
        "isSubjectToAppraisal": session.is_subject_to_appraisal if reviewed else None,
        "appraisalReason": session.appraisal_reason if reviewed else "Chưa kiểm duyệt. Hoàn tất thông số rồi bấm Kiểm duyệt hồ sơ.",
        "appraisalBasis": basis,
        "warnings": session.warnings or [] if reviewed else [],
    }


def _owner_filter(user: User):
    return None if user.role == "admin" else ChatSession.owner_id == user.id


def _user_grounding_text(history: List[dict], current_text: str) -> str:
    recent = [str(m.get("text") or "") for m in history[-8:] if m.get("sender") == "user"]
    return "\n".join(recent + [current_text or ""])


def _apply_ai_outputs(session: "ChatSession", parsed: dict, grounding_text: Optional[str]) -> dict:
    main_mod = sys.modules.get("app.main")
    eval_fn = getattr(main_mod, "evaluate_appraisal", evaluate_appraisal) if main_mod else evaluate_appraisal

    current = session.project_data.to_dict()
    result = sanitize_extracted_info(parsed.get("extractedProjectInfo"), current, grounding_text)
    if result["accepted"]:
        try:
            checked = ProjectUpdateRequest.model_validate({**current, **result["accepted"]})
            session.project_data.apply_dict(checked.model_dump(exclude_none=True))
        except ValidationError:
            result["rejected"].append("Dữ liệu AI mâu thuẫn hoặc sai cấu trúc; giữ hồ sơ hiện tại.")
    for note in result["rejected"]:
        logger.warning("[ai_guard] session=%s %s", session.id, note)

    final_pinfo = session.project_data.to_dict()
    deterministic = eval_fn(final_pinfo)
    basis = deterministic["appraisalBasis"]

    reply, violations = guard_reply(parsed.get("reply"), basis, final_pinfo)
    if violations:
        logger.warning("[ai_guard] session=%s đã lược bỏ nhận định mâu thuẫn trong reply: %s", session.id, violations)
    notes = result["rejected"] + result["derived"]
    if result["rejected"] and reply:
        shown = "; ".join(result["rejected"][:3])
        reply = f"{reply}\n\nℹ️ Một số số liệu AI đề xuất chưa được ghi vào hồ sơ: {shown}"

    ai_warnings, dropped = guard_warnings(parsed.get("warnings"), basis, final_pinfo)
    if dropped:
        logger.warning("[ai_guard] session=%s đã loại %d cảnh báo AI mâu thuẫn kết luận", session.id, dropped)
    warnings = list(dict.fromkeys(deterministic["warnings"] + notes + ai_warnings))
    return {"deterministic": deterministic, "reply": reply, "warnings": warnings, "final_pinfo": final_pinfo}


def _merge_checklist(ai_checklist: Optional[List[dict]], deterministic_checklist: List[dict]) -> List[dict]:
    return [dict(item) for item in deterministic_checklist]


async def _log_inspection(
    db: AsyncSession, session: ChatSession, user_id: str, trigger_source: str,
    is_subject: bool, reason: str, checklist: list, warnings: list,
) -> None:
    db.add(
        InspectionLog(
            session_id=session.id, owner_id=user_id, trigger_source=trigger_source,
            is_subject_to_appraisal=is_subject, appraisal_reason=reason,
            checklist_snapshot=checklist, warnings=warnings,
        )
    )


class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    projectInfo: Optional[ProjectUpdateRequest] = None
