"""
Users API Routes (SQLAlchemy)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import security_manager
from app.models.user import User
from app.models.resource import Resource
from app.schemas.user import UserResponse, UserUpdate, PasswordChangeRequest
from app.api.v1.deps import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(redirect_slashes=False)


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    if data.display_name is not None:
        current_user.display_name = data.display_name
    if data.avatar_url is not None:
        current_user.avatar_url = data.avatar_url
    
    await db.flush()
    return current_user


@router.post("/me/change-password")
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Change current user password."""
    if not security_manager.verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    current_user.password_hash = security_manager.hash_password(data.new_password)
    await db.flush()
    
    return {"message": "Password changed successfully"}


@router.get("/me/storage")
async def get_storage_info(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user storage information (recalculated from actual resources)."""
    try:
        result = await db.execute(
            select(func.coalesce(func.sum(Resource.file_size), 0))
            .where(
                Resource.uploader_id == current_user.id,
                Resource.is_deleted == False,
            )
        )
        actual_used = result.scalar()
    except Exception as e:
        logger.warning(f"Could not recalculate storage for {current_user.email}: {e}")
        actual_used = current_user.storage_used_bytes
    
    # Update user model if stale
    if actual_used != current_user.storage_used_bytes:
        logger.info(f"Storage recalc for {current_user.email}: {current_user.storage_used_bytes} -> {actual_used}")
        current_user.storage_used_bytes = actual_used
        await db.flush()
    
    quota = current_user.storage_quota_bytes
    remaining = max(0, quota - actual_used)
    usage_pct = (actual_used / quota * 100) if quota > 0 else 0
    
    return {
        "quota_bytes": quota,
        "used_bytes": actual_used,
        "remaining_bytes": remaining,
        "usage_percent": round(usage_pct, 2),
        "quota_mb": round(quota / (1024 * 1024), 2),
        "used_mb": round(actual_used / (1024 * 1024), 2),
    }
