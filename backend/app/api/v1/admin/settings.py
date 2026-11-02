"""
Admin API - Runtime Site Settings (SQLAlchemy)

Currently owns the global upload-moderation policy:
auto_approve_moderation=True → every non-private upload is approved
without review (moderation disabled site-wide, except for the always-on
exemptions below). False → normal moderation (default).
"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.services.settings import get_bool_setting, set_bool_setting
from app.schemas.settings import ModerationAutoApproveResponse
from app.api.v1.deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


class ModerationAutoApproveUpdate(BaseModel):
    auto_approve_moderation: bool


@router.get("/moderation", response_model=ModerationAutoApproveResponse)
async def get_moderation_setting(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Current global upload-moderation policy (admin only)."""
    current = await get_bool_setting(db, "moderation_auto_approve", default=False)
    return ModerationAutoApproveResponse(auto_approve_moderation=current)


@router.patch("/moderation", response_model=ModerationAutoApproveResponse)
async def update_moderation_setting(
    data: ModerationAutoApproveUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggle site-wide moderation of public uploads (admin only)."""
    await set_bool_setting(
        db, "moderation_auto_approve", data.auto_approve_moderation,
        description="When true, every non-private upload is approved without review.",
    )
    return ModerationAutoApproveResponse(auto_approve_moderation=data.auto_approve_moderation)
