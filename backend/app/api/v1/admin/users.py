"""
Admin API - User Promotion (SQLAlchemy)
"""
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.schemas.moderation import UserPromotionRequest, UserPromotionResponse
from app.api.v1.deps import require_admin
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def list_users(
    q: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List/search all users (admin only)."""
    filters = []
    if q:
        q_like = f"%{q}%"
        filters.append(or_(User.email.ilike(q_like), User.display_name.ilike(q_like)))
    
    combined = and_(*filters) if filters else True
    
    count_result = await db.execute(select(func.count()).select_from(User).where(combined))
    total = count_result.scalar()
    
    result = await db.execute(
        select(User).where(combined)
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    
    # Batch count uploads per user
    user_ids = [u.id for u in users]
    upload_counts = {}
    approved_counts = {}
    
    if user_ids:
        for uid in user_ids:
            uc = await db.execute(select(func.count()).select_from(Resource).where(Resource.uploader_id == uid, Resource.is_deleted == False))
            upload_counts[uid] = uc.scalar()
            ac = await db.execute(select(func.count()).select_from(Resource).where(Resource.uploader_id == uid, Resource.moderation_status == "approved", Resource.is_deleted == False))
            approved_counts[uid] = ac.scalar()
    
    results = []
    for user in users:
        results.append({
            "id": str(user.id), "email": user.email,
            "display_name": user.display_name,
            "role": "admin" if user.is_admin else ("moderator" if user.is_moderator else "user"),
            "is_trusted": user.is_trusted, "is_banned": user.is_banned,
            "upload_count": upload_counts.get(user.id, 0),
            "approved_count": approved_counts.get(user.id, 0),
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })
    
    return {"results": results, "total": total, "page": page, "pages": (total + page_size - 1) // page_size}


@router.get("/{user_id}/promotion", response_model=UserPromotionResponse)
async def get_user_promotion_status(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get user's trusted contributor status."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return UserPromotionResponse(
        user_id=str(user.id), email=user.email,
        is_trusted=user.is_trusted, promoted_at=user.promoted_at,
        promoted_by=user.promoted_by,
    )


@router.post("/{user_id}/promote", response_model=UserPromotionResponse)
async def promote_user(
    user_id: str,
    promotion: UserPromotionRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Promote or demote a user's trusted contributor status."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify your own trusted status")
    if user.is_admin or user.is_moderator:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify trusted status of admins/moderators")
    
    old_status = user.is_trusted
    user.is_trusted = promotion.is_trusted
    
    if promotion.is_trusted and not old_status:
        user.promoted_at = datetime.now(timezone.utc)
        user.promoted_by = str(current_user.id)
        action = "promote_user"
    elif not promotion.is_trusted and old_status:
        user.promoted_at = None
        user.promoted_by = None
        action = "demote_user"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User is already {'trusted' if old_status else 'not trusted'}")
    
    audit = AuditLog(
        action=action, actor_id=current_user.id, target_type="user", target_id=user_id,
        details_json=json.dumps({"email": user.email, "old_status": old_status, "new_status": promotion.is_trusted, "reason": promotion.reason})
    )
    db.add(audit)
    await db.flush()
    
    return UserPromotionResponse(
        user_id=str(user.id), email=user.email,
        is_trusted=user.is_trusted, promoted_at=user.promoted_at,
        promoted_by=user.promoted_by,
    )


@router.get("/trusted", response_model=List[UserPromotionResponse])
async def list_trusted_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all trusted contributors."""
    result = await db.execute(
        select(User).where(User.is_trusted == True)
        .order_by(User.promoted_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    
    return [
        UserPromotionResponse(
            user_id=str(user.id), email=user.email,
            is_trusted=user.is_trusted, promoted_at=user.promoted_at,
            promoted_by=user.promoted_by,
        )
        for user in users
    ]
