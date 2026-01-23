"""
Admin API - User Promotion (Trusted Contributors)
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from beanie import PydanticObjectId
from datetime import datetime, timezone

from app.models.user import User
from app.schemas.moderation import UserPromotionRequest, UserPromotionResponse
from app.api.v1.deps import get_current_user, require_admin
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/admin/users", tags=["Admin - Users"])


@router.get("/{user_id}/promotion", response_model=UserPromotionResponse)
async def get_user_promotion_status(
    user_id: str,
    current_user: User = Depends(require_admin),
):
    """Get user's trusted contributor status."""
    try:
        obj_id = PydanticObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    
    user = await User.get(obj_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return UserPromotionResponse(
        user_id=str(user.id),
        email=user.email,
        is_trusted=user.is_trusted,
        promoted_at=user.promoted_at,
        promoted_by=user.promoted_by,
    )


@router.post("/{user_id}/promote", response_model=UserPromotionResponse)
async def promote_user(
    user_id: str,
    promotion: UserPromotionRequest,
    current_user: User = Depends(require_admin),
):
    """Promote or demote a user's trusted contributor status."""
    try:
        obj_id = PydanticObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    
    user = await User.get(obj_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Prevent self-promotion/demotion
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own trusted status"
        )
    
    # Prevent modifying admin/moderator status via this endpoint
    if user.is_admin or user.is_moderator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify trusted status of admins/moderators"
        )
    
    old_status = user.is_trusted
    user.is_trusted = promotion.is_trusted
    
    if promotion.is_trusted and not old_status:
        # Promoting to trusted
        user.promoted_at = datetime.now(timezone.utc)
        user.promoted_by = str(current_user.id)
        action = "promote_user"
    elif not promotion.is_trusted and old_status:
        # Demoting from trusted
        user.promoted_at = None
        user.promoted_by = None
        action = "demote_user"
    else:
        # No change
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is already {'trusted' if old_status else 'not trusted'}"
        )
    
    await user.save()
    
    # Audit log
    audit = AuditLog(
        action=action,
        actor=current_user,
        target_type="user",
        target_id=user_id,
        details={
            "email": user.email,
            "old_status": old_status,
            "new_status": promotion.is_trusted,
            "reason": promotion.reason
        }
    )
    await audit.create()
    
    return UserPromotionResponse(
        user_id=str(user.id),
        email=user.email,
        is_trusted=user.is_trusted,
        promoted_at=user.promoted_at,
        promoted_by=user.promoted_by,
    )


@router.get("/trusted", response_model=List[UserPromotionResponse])
async def list_trusted_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin),
):
    """List all trusted contributors."""
    users = (
        await User.find(User.is_trusted == True)
        .sort("-promoted_at")
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list()
    )
    
    return [
        UserPromotionResponse(
            user_id=str(user.id),
            email=user.email,
            is_trusted=user.is_trusted,
            promoted_at=user.promoted_at,
            promoted_by=user.promoted_by,
        )
        for user in users
    ]
