"""
Admin API - Content Moderation (SQLAlchemy)
"""
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.schemas.moderation import ModerationAction, ResourceModerationStatus
from app.api.v1.deps import require_moderator
from app.models.audit_log import AuditLog

router = APIRouter()


@router.get("/pending")
async def get_pending_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    """Get all pending resources awaiting moderation."""
    base_filter = and_(Resource.moderation_status == "pending", Resource.is_deleted == False)
    
    count_result = await db.execute(select(func.count()).select_from(Resource).where(base_filter))
    total = count_result.scalar()
    
    result = await db.execute(
        select(Resource).where(base_filter)
        .order_by(Resource.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    resources = result.scalars().all()
    
    # Get uploader names
    uploader_ids = {r.uploader_id for r in resources if r.uploader_id}
    user_map = {}
    if uploader_ids:
        users_result = await db.execute(select(User).where(User.id.in_(uploader_ids)))
        user_map = {u.id: u.display_name or "Unknown" for u in users_result.scalars().all()}
    
    results = []
    for resource in resources:
        results.append({
            "id": str(resource.id), "title": resource.title, "slug": resource.slug,
            "course_code": resource.course_code,
            "department_name": None,
            "uploader_name": user_map.get(resource.uploader_id),
            "file_size": resource.file_size,
            "created_at": resource.created_at.isoformat() if resource.created_at else None,
        })
    
    return {
        "results": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.post("/{resource_id}/moderate")
async def moderate_resource(
    resource_id: str,
    action: ModerationAction,
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a resource."""
    # M5: soft-deleted resources are out of the moderation queue entirely.
    result = await db.execute(
        select(Resource).where(
            Resource.id == resource_id,
            Resource.is_deleted == False,  # noqa: E712
        )
    )
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    if resource.moderation_status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Resource is already {resource.moderation_status}")
    
    if action.action not in ["approve", "reject"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be 'approve' or 'reject'")
    
    now = datetime.now(timezone.utc)
    if action.action == "approve":
        new_status = "approved"
        audit_action = "approve_resource"
        rejection_reason = None
    else:
        if not action.rejection_reason:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection reason is required")
        new_status = "rejected"
        audit_action = "reject_resource"
        rejection_reason = action.rejection_reason

    # M5: atomic write closes the check-then-act race between two moderators.
    upd = await db.execute(
        update(Resource)
        .where(
            Resource.id == resource_id,
            Resource.moderation_status == "pending",
        )
        .values(
            moderation_status=new_status,
            moderated_by_id=current_user.id,
            moderated_at=now,
            rejection_reason=rejection_reason,
        )
    )
    if upd.rowcount == 0:
        # Lost the race (or concurrently soft-deleted): re-read for an accurate error.
        recheck = await db.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        current = recheck.scalar_one_or_none()
        if current is None or current.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resource is already {current.moderation_status}",
        )

    resource.moderation_status = new_status
    resource.moderated_by_id = current_user.id
    resource.moderated_at = now
    resource.rejection_reason = rejection_reason
    
    # Audit log
    audit = AuditLog(
        action=audit_action, actor_id=current_user.id, target_type="resource", target_id=resource_id,
        details_json=json.dumps({"title": resource.title, "action": action.action,
                                "rejection_reason": action.rejection_reason if action.action == "reject" else None})
    )
    db.add(audit)
    await db.flush()
    
    # Invalidate cached stats
    from app.services.cache import cache_service
    cache_service.invalidate_on_moderation()
    
    # Get uploader info
    uploader_name = None
    uploader_email = None
    if resource.uploader_id:
        up_result = await db.execute(select(User).where(User.id == resource.uploader_id))
        uploader = up_result.scalar_one_or_none()
        if uploader:
            uploader_name = uploader.display_name
            uploader_email = uploader.email
    
    return ResourceModerationStatus(
        resource_id=str(resource.id), title=resource.title,
        status=resource.moderation_status,
        uploader_name=uploader_name, uploader_email=uploader_email,
        uploaded_at=resource.created_at,
        moderated_by=str(current_user.id), moderated_at=resource.moderated_at,
        rejection_reason=resource.rejection_reason,
    )


@router.get("/history")
async def get_moderation_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: str = Query(None, pattern="^(approved|rejected)$"),
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    """Get moderation history."""
    filters = [Resource.moderation_status.in_(["approved", "rejected"]), Resource.is_deleted == False]
    if status_filter:
        filters = [Resource.moderation_status == status_filter, Resource.is_deleted == False]
    
    result = await db.execute(
        select(Resource).where(and_(*filters))
        .order_by(Resource.moderated_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    resources = result.scalars().all()
    
    # Batch fetch users
    user_ids = set()
    for r in resources:
        if r.uploader_id: user_ids.add(r.uploader_id)
        if r.moderated_by_id: user_ids.add(r.moderated_by_id)
    
    user_map = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map = {u.id: u for u in users_result.scalars().all()}
    
    results = []
    for resource in resources:
        uploader = user_map.get(resource.uploader_id)
        results.append(ResourceModerationStatus(
            resource_id=str(resource.id), title=resource.title,
            status=resource.moderation_status,
            uploader_name=uploader.display_name if uploader else None,
            uploader_email=uploader.email if uploader else None,
            uploaded_at=resource.created_at,
            moderated_by=resource.moderated_by_id,
            moderated_at=resource.moderated_at,
            rejection_reason=resource.rejection_reason,
        ))
    
    # M15: standard pagination envelope (was an unpageable bare list).
    history_total = (
        await db.execute(
            select(func.count()).select_from(Resource).where(and_(*filters))
        )
    ).scalar()
    return {
        "results": [r.model_dump(mode="json") for r in results],
        "total": history_total,
        "page": page,
        "page_size": page_size,
        "pages": (history_total + page_size - 1) // page_size,
    }


@router.get("/stats")
async def get_moderation_stats(
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    """Get moderation statistics (served from StatsEngine cache)."""
    from app.services.cache import cache_service
    
    data = await cache_service.get_stats("moderation_stats")
    if data:
        return data
    
    # Fallback
    base = and_(Resource.is_deleted == False)
    pending = (await db.execute(select(func.count()).select_from(Resource).where(base, Resource.moderation_status == "pending"))).scalar()
    approved = (await db.execute(select(func.count()).select_from(Resource).where(base, Resource.moderation_status == "approved"))).scalar()
    rejected = (await db.execute(select(func.count()).select_from(Resource).where(base, Resource.moderation_status == "rejected"))).scalar()
    
    return {"pending": pending, "approved": approved, "rejected": rejected, "total": pending + approved + rejected}


@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str = Query(None),
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    """Get the admin audit trail (paginated, optionally filtered by action)."""
    base = []
    if action:
        base.append(AuditLog.action == action)

    count_result = await db.execute(select(func.count()).select_from(AuditLog).where(*base))
    total = count_result.scalar()

    result = await db.execute(
        select(AuditLog).where(*base)
        .order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()

    # Batch fetch actors
    actor_ids = {log.actor_id for log in logs if log.actor_id}
    actor_map = {}
    if actor_ids:
        users_result = await db.execute(select(User).where(User.id.in_(actor_ids)))
        actor_map = {u.id: u for u in users_result.scalars().all()}

    results = []
    for log in logs:
        actor = actor_map.get(log.actor_id)
        results.append({
            "id": str(log.id),
            "action": log.action,
            "actor_name": actor.display_name if actor else None,
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        })

    return {
        "results": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }
