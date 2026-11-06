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
from app.schemas.moderation import (
    UserPromotionRequest,
    UserPromotionResponse,
    ModerationExemptRequest,
    AdminUserListResponse,
    UserPromotionListResponse,
)
from app.api.v1.deps import require_admin
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter()


def _role_label(user: User) -> str:
    """Admin-page role label; students render as 'user' (matches /admin/users listing)."""
    return "admin" if user.is_admin else ("moderator" if user.is_moderator else "user")


async def _contribution_counts(db: AsyncSession, user_id: str) -> tuple:
    """(upload_count, approved_count) across a user's non-deleted resources."""
    upload_rows = await db.execute(
        select(func.count()).select_from(Resource).where(
            Resource.uploader_id == user_id,
            Resource.is_deleted == False,  # noqa: E712
        )
    )
    approved_rows = await db.execute(
        select(func.count()).select_from(Resource).where(
            Resource.uploader_id == user_id,
            Resource.is_deleted == False,  # noqa: E712
            Resource.moderation_status == "approved",
        )
    )
    return int(upload_rows.scalar_one() or 0), int(approved_rows.scalar_one() or 0)


@router.get("", response_model=AdminUserListResponse)
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

    # H4: grouped aggregate queries instead of 2 sequential queries per user.
    user_ids = [u.id for u in users]
    upload_counts: dict = {}
    approved_counts: dict = {}

    if user_ids:
        upload_rows = await db.execute(
            select(Resource.uploader_id, func.count())
            .where(
                Resource.uploader_id.in_(user_ids),
                Resource.is_deleted == False,  # noqa: E712
            )
            .group_by(Resource.uploader_id)
        )
        upload_counts = {uid: count for uid, count in upload_rows.all()}

        approved_rows = await db.execute(
            select(Resource.uploader_id, func.count())
            .where(
                Resource.uploader_id.in_(user_ids),
                Resource.is_deleted == False,  # noqa: E712
                Resource.moderation_status == "approved",
            )
            .group_by(Resource.uploader_id)
        )
        approved_counts = {uid: count for uid, count in approved_rows.all()}
    
    results = []
    for user in users:
        results.append({
            "id": str(user.id), "email": user.email,
            "display_name": user.display_name,
            "role": "admin" if user.is_admin else ("moderator" if user.is_moderator else "user"),
            "is_trusted": user.is_trusted, "is_banned": user.is_banned,
            "moderation_exempt": bool(user.moderation_exempt),
            "upload_count": upload_counts.get(user.id, 0),
            "approved_count": approved_counts.get(user.id, 0),
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })
    
    return {"results": results, "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size}


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
    
    uploads, approved = await _contribution_counts(db, str(user.id))
    return UserPromotionResponse(
        user_id=str(user.id), email=user.email,
        is_trusted=user.is_trusted, promoted_at=user.promoted_at,
        promoted_by=user.promoted_by,
        display_name=user.display_name, role=_role_label(user),
        moderation_exempt=bool(user.moderation_exempt),
        upload_count=uploads, approved_count=approved,
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
    
    # Audit failure must never fail the user action (unified policy).
    try:
        audit = AuditLog(
            action=action, actor_id=current_user.id, target_type="user", target_id=user_id,
            details_json=json.dumps({"email": user.email, "old_status": old_status, "new_status": promotion.is_trusted, "reason": promotion.reason})
        )
        db.add(audit)
    except Exception:
        logger.exception("Audit log error on user promotion")
    await db.flush()
    
    uploads, approved = await _contribution_counts(db, str(user.id))
    return UserPromotionResponse(
        user_id=str(user.id), email=user.email,
        is_trusted=user.is_trusted, promoted_at=user.promoted_at,
        promoted_by=user.promoted_by,
        display_name=user.display_name, role=_role_label(user),
        moderation_exempt=bool(user.moderation_exempt),
        upload_count=uploads, approved_count=approved,
    )


@router.patch("/{user_id}/moderation-exempt", response_model=UserPromotionResponse)
async def set_user_moderation_exempt(
    user_id: str,
    data: ModerationExemptRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggle a user's per-user upload moderation exemption (idempotent).

    Exempt users' public uploads are auto-approved without review,
    regardless of the global moderation setting. Admins/moderators do not
    need this flag (they always bypass), and self-modification is blocked.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify your own moderation exemption")
    if user.is_admin or user.is_moderator:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins/moderators do not need a moderation exemption")

    user.moderation_exempt = data.moderation_exempt

    # Audit failure must never fail the user action (unified policy).
    try:
        audit = AuditLog(
            action="set_moderation_exempt", actor_id=current_user.id, target_type="user", target_id=user_id,
            details_json=json.dumps({"email": user.email, "moderation_exempt": data.moderation_exempt})
        )
        db.add(audit)
    except Exception:
        logger.exception("Audit log error on moderation exemption toggle")
    await db.flush()

    uploads, approved = await _contribution_counts(db, str(user.id))
    return UserPromotionResponse(
        user_id=str(user.id), email=user.email,
        is_trusted=user.is_trusted, promoted_at=user.promoted_at,
        promoted_by=user.promoted_by,
        display_name=user.display_name, role=_role_label(user),
        moderation_exempt=bool(user.moderation_exempt),
        upload_count=uploads, approved_count=approved,
    )


@router.get("/trusted", response_model=UserPromotionListResponse)
async def list_trusted_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all trusted contributors (M15: standard pagination envelope)."""
    count_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_trusted == True)  # noqa: E712
    )
    total = count_result.scalar()

    result = await db.execute(
        select(User).where(User.is_trusted == True)  # noqa: E712
        .order_by(User.promoted_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    
    user_ids = [str(u.id) for u in users]
    upload_counts: dict = {}
    approved_counts: dict = {}
    if user_ids:
        upload_rows = await db.execute(
            select(Resource.uploader_id, func.count())
            .where(
                Resource.uploader_id.in_(user_ids),
                Resource.is_deleted == False,  # noqa: E712
            )
            .group_by(Resource.uploader_id)
        )
        upload_counts = {uid: count for uid, count in upload_rows.all()}

        approved_rows = await db.execute(
            select(Resource.uploader_id, func.count())
            .where(
                Resource.uploader_id.in_(user_ids),
                Resource.is_deleted == False,  # noqa: E712
                Resource.moderation_status == "approved",
            )
            .group_by(Resource.uploader_id)
        )
        approved_counts = {uid: count for uid, count in approved_rows.all()}

    return {
        "results": [
            UserPromotionResponse(
                user_id=str(user.id), email=user.email,
                is_trusted=user.is_trusted, promoted_at=user.promoted_at,
                promoted_by=user.promoted_by,
                display_name=user.display_name, role=_role_label(user),
                moderation_exempt=bool(user.moderation_exempt),
                upload_count=upload_counts.get(str(user.id), 0),
                approved_count=approved_counts.get(str(user.id), 0),
            ).model_dump(mode="json")
            for user in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }
