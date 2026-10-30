"""OCR and Drawing Vision Extraction Router."""
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_guard import sanitize_extracted_info
from app.auth import get_current_user
from app.config import ALLOWED_DRAWING_EXTENSIONS, DRAWINGS_DIR
from app.db import get_db
from app.db_models import ProjectData, User
from app.hardening import lock_session, validate_upload
from app.limiter import limiter
from app.ocr_vision import OCRInputError, extract_project_data_from_drawing
from app.schemas_project import ProjectUpdateRequest
from app.services.session_service import (
    _check_revision,
    _clear_review,
    _is_reviewed,
    _load_session_full,
)
from app.utils_file import (
    _generate_safe_storage_path,
    _read_upload_with_size_limit,
)

logger = logging.getLogger("pccc.router.ocr")

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/extract-drawing")
@limiter.limit("15/minute")
async def ocr_extract_drawing(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    apply_to_session: bool = Form(False),
    expected_revision: Optional[str] = Header(None, alias="If-Match"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Preview OCR by default. Explicit apply_to_session=true opts into a
    validated atomic write; the UI saves only after the user confirms."""
    session = None
    if session_id:
        await lock_session(db, session_id)
        session = await _load_session_full(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
        if user.role != "admin" and session.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Không có quyền chỉnh sửa hồ sơ của người khác.")
        if apply_to_session:
            _check_revision(session, expected_revision)

    dest_path, _ = _generate_safe_storage_path(DRAWINGS_DIR, file.filename or "drawing", ALLOWED_DRAWING_EXTENSIONS)
    content = await _read_upload_with_size_limit(file)
    await run_in_threadpool(validate_upload, content, dest_path.suffix)
    try:
        await run_in_threadpool(dest_path.write_bytes, content)
        main_mod = sys.modules.get("app.main")
        ocr_fn = getattr(main_mod, "extract_project_data_from_drawing", extract_project_data_from_drawing) if main_mod else extract_project_data_from_drawing
        extracted = await ocr_fn(str(dest_path), "")
        if not isinstance(extracted, dict):
            raise ValueError("OCR output must be an object")
        current = session.project_data.to_dict() if session and session.project_data else {}
        clean = sanitize_extracted_info(extracted, current, None)
        accepted = clean["accepted"]
        if extracted.get("components") is not None:
            component_data = ProjectUpdateRequest.model_validate({"components": extracted["components"]})
            accepted["components"] = component_data.model_dump(exclude_none=True)["components"]
            accepted["componentsComplete"] = False
            if accepted["components"]:
                for key in (
                    "type",
                    "height",
                    "pcccHeight",
                    "floorArea",
                    "totalFloorArea",
                    "floors",
                    "fireRating",
                    "volume",
                    "hazardClass",
                    "industrialSubtype",
                ):
                    accepted.pop(key, None)
        for key in ("volume", "hazardClass", "industrialSubtype"):
            if not accepted.get("components") and extracted.get(key) is not None:
                checked = ProjectUpdateRequest.model_validate({key: extracted[key]})
                accepted[key] = checked.model_dump(exclude_none=True)[key]
        for count_key, array_keys in (
            ("floors", ("floorFunctions",)),
            ("basements", ("basementFunctions", "basementHeights", "basementAreas", "basementFootprints")),
        ):
            if count_key in accepted:
                for key in array_keys:
                    accepted[key] = (accepted.get(key, current.get(key)) or [])[: accepted[count_key]]
        merged = ProjectUpdateRequest.model_validate({**current, **accepted})
        if session and apply_to_session:
            if not session.project_data:
                session.project_data = ProjectData(session_id=session.id)
                db.add(session.project_data)
            session.project_data.apply_dict(merged.model_dump(exclude_none=True))
            if "components" in accepted:
                session.project_data.shared_systems = None
                session.project_data.concurrent_design = None
            session.project_data.source = "ocr"
            session.updated_at = datetime.now(timezone.utc)
            if not _is_reviewed(session):
                _clear_review(session)
            await db.commit()
        return {
            "extractedProjectInfo": accepted,
            "appliedToSession": bool(session and apply_to_session),
            "rejectedFields": clean["rejected"],
            "coverage": extracted.get("_ocrCoverage"),
        }
    except HTTPException:
        raise
    except OCRInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValidationError:
        raise HTTPException(status_code=422, detail="Dữ liệu OCR mâu thuẫn với hồ sơ. Vui lòng nhập tay để xác nhận.")
    except Exception:
        logger.exception("OCR không thành công")
        raise HTTPException(status_code=502, detail="Dịch vụ OCR không sẵn sàng. Bạn có thể nhập thông số thủ công.")
    finally:
        dest_path.unlink(missing_ok=True)
