"""Inspection Logs Router."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.db_models import InspectionLog, User

logger = logging.getLogger("pccc.router.inspection_logs")

router = APIRouter(prefix="/api/inspection-logs", tags=["inspection-logs"])


@router.get("")
async def list_inspection_logs(
    session_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(InspectionLog).order_by(InspectionLog.created_at.desc()).limit(limit)
    if session_id:
        stmt = stmt.where(InspectionLog.session_id == session_id)
    if user.role != "admin":
        stmt = stmt.where(InspectionLog.owner_id == user.id)
    result = await db.execute(stmt)
    return [log.to_dict() for log in result.scalars().all()]

