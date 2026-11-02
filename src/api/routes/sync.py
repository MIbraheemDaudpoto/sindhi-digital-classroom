"""Offline Unit Pack download and Client Queue Sync routes for SDC.
Authored under agency-backend-architect.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from src.api.deps import get_current_user, require_roles
from src.models.schemas import UserRole
from src.services.sync_service import sync_service

router = APIRouter(prefix="/api/sync", tags=["Offline & Sync"])


class QueueSyncRequest(BaseModel):
    queue: List[Dict[str, Any]]


@router.get("/unit-pack/{lesson_id}")
async def get_offline_unit_pack(lesson_id: str):
    """Download bundled unit pack (metadata, transcripts, approved questions) for 100% offline use (FR-32)."""
    pack = sync_service.generate_unit_pack(lesson_id)
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson unit not found.")
    return pack


@router.post("/queue", status_code=status.HTTP_200_OK)
async def sync_offline_queue(
    req: QueueSyncRequest,
    current_user: dict = Depends(require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN))
):
    """Process queued offline attempts and progress records once reconnected (FR-19)."""
    return sync_service.process_sync_queue(user_id=current_user["id"], queue_items=req.queue)
