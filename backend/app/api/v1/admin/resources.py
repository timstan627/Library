"""
Admin API - Resource Management (SQLAlchemy)
"""
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.api.v1.deps import require_admin
from app.models.audit_log import AuditLog
from app.schemas.moderation import AdminResourceListResponse

logger = logging.getLogger(__name__)

router = APIRouter()

BULK_DELETE_MAX_IDS = 100


@router.get("", response_model=AdminResourceListResponse)
async def list_all_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all resources for admin management."""
    filters = [Resource.is_deleted == False]
    
    if status_filter:
        filters.append(Resource.moderation_status == status_filter)
    if search:
        q_like = f"%{search}%"
        filters.append(or_(
            Resource.title.ilike(q_like),
            Resource.file_name.ilike(q_like),
            Resource.course_code.ilike(q_like),
        ))
    
    combined = and_(*filters)
    
    count_result = await db.execute(select(func.count()).select_from(Resource).where(combined))
    total = count_result.scalar()
    
    result = await db.execute(
        select(Resource).where(combined)
        .order_by(Resource.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    resources = result.scalars().all()
    
    results = []
    for resource in resources:
        results.append({
            "id": str(resource.id), "title": resource.title, "slug": resource.slug,
            "course_code": resource.course_code, "file_name": resource.file_name,
            "file_size": resource.file_size, "downloads": resource.downloads,
            "views": resource.views, "visibility": resource.visibility,
            "moderation_status": resource.moderation_status,
            "created_at": resource.created_at.isoformat() if resource.created_at else None,
        })
    
    return {
        "results": results, "total": total, "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single resource by ID (soft delete with audit trail, M16)."""
    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    now = datetime.now(timezone.utc)
    resource.is_deleted = True
    resource.deleted_at = now
    resource.deleted_by_id = str(current_user.id)
    resource.updated_at = now
    await db.flush()

    try:
        audit = AuditLog(
            action="delete_resource",
            actor_id=str(current_user.id),
            target_type="resource",
            target_id=str(resource.id),
            details_json=json.dumps({
                "title": resource.title,
                "course_code": resource.course_code,
            }),
        )
        db.add(audit)
        await db.flush()
    except Exception:
        logger.exception("Audit log error on resource delete")

    return {"message": "Resource deleted successfully", "id": resource_id}


@router.post("/bulk-delete")
async def bulk_delete_resources(
    resource_ids: List[str] = Body(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete multiple resources by ID (H5: bounded, deduped, one UPDATE, audited)."""
    if len(resource_ids) > BULK_DELETE_MAX_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bulk delete is limited to {BULK_DELETE_MAX_IDS} resources per request",
        )

    # Dedupe while preserving order so duplicates cannot inflate the counter.
    unique_ids = list(dict.fromkeys(resource_ids))
    if not unique_ids:
        return {"message": "Deleted 0 resources", "deleted": 0, "failed": 0}

    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Resource)
        .where(Resource.id.in_(unique_ids), Resource.is_deleted == False)  # noqa: E712
        .values(
            is_deleted=True,
            deleted_at=now,
            deleted_by_id=str(current_user.id),
            updated_at=now,
        )
    )
    deleted = result.rowcount or 0
    failed = len(unique_ids) - deleted
    await db.flush()

    try:
        audit = AuditLog(
            action="bulk_delete_resources",
            actor_id=str(current_user.id),
            target_type="resource",
            target_id="bulk",
            details_json=json.dumps({
                "resource_ids": unique_ids,
                "deleted": deleted,
                "failed": failed,
            }),
        )
        db.add(audit)
        await db.flush()
    except Exception:
        logger.exception("Audit log error on bulk resource delete")

    return {"message": f"Deleted {deleted} resources", "deleted": deleted, "failed": failed}
