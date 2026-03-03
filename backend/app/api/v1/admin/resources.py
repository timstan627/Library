"""
Admin API - Resource Management (SQLAlchemy)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.api.v1.deps import require_admin

router = APIRouter()


@router.get("")
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
    """Delete a single resource by ID."""
    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    resource.is_deleted = True
    resource.updated_at = datetime.now(timezone.utc)
    await db.flush()
    
    return {"message": "Resource deleted successfully", "id": resource_id}


@router.post("/bulk-delete")
async def bulk_delete_resources(
    resource_ids: List[str] = Body(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple resources by IDs."""
    deleted = 0
    failed = 0
    
    for resource_id in resource_ids:
        try:
            result = await db.execute(select(Resource).where(Resource.id == resource_id))
            resource = result.scalar_one_or_none()
            if resource:
                resource.is_deleted = True
                resource.updated_at = datetime.now(timezone.utc)
                deleted += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    
    await db.flush()
    return {"message": f"Deleted {deleted} resources", "deleted": deleted, "failed": failed}
