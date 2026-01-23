"""
Admin API - Resource Management
Allows admins to view, edit, and delete all resources
"""
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from beanie import PydanticObjectId
from datetime import datetime, timezone

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
):
    """List all resources for admin management."""
    # Build query filters
    filters = [Resource.is_deleted == False]
    
    if status_filter:
        filters.append(Resource.moderation_status == status_filter)
    
    # Get total count
    total = await Resource.find(*filters).count()
    
    # Fetch paginated resources
    resources = (
        await Resource.find(*filters)
        .sort("-created_at")
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list()
    )
    
    # Filter by search if provided (case-insensitive)
    if search:
        search_lower = search.lower()
        resources = [
            r for r in resources
            if search_lower in r.title.lower()
            or search_lower in r.file_name.lower()
            or search_lower in r.course_code.lower()
        ]
    
    # Build response
    results = []
    for resource in resources:
        results.append({
            "id": str(resource.id),
            "title": resource.title,
            "slug": resource.slug,
            "course_code": resource.course_code,
            "file_name": resource.file_name,
            "file_size": resource.file_size,
            "downloads": resource.downloads,
            "views": resource.views,
            "visibility": resource.visibility,
            "moderation_status": resource.moderation_status,
            "created_at": resource.created_at.isoformat() if resource.created_at else None,
        })
    
    return {
        "results": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: str,
    current_user: User = Depends(require_admin),
):
    """Delete a single resource by ID."""
    import uuid as uuid_module
    try:
        res_uuid = uuid_module.UUID(resource_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource ID"
        )
    
    resource = await Resource.find_one(Resource.id == res_uuid)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    # Soft delete
    resource.is_deleted = True
    resource.updated_at = datetime.now(timezone.utc)
    await resource.save()
    
    return {"message": "Resource deleted successfully", "id": resource_id}


@router.post("/bulk-delete")
async def bulk_delete_resources(
    resource_ids: List[str] = Body(...),
    current_user: User = Depends(require_admin),
):
    """Delete multiple resources by IDs."""
    import uuid as uuid_module
    deleted = 0
    failed = 0
    
    for resource_id in resource_ids:
        try:
            res_uuid = uuid_module.UUID(resource_id)
            resource = await Resource.find_one(Resource.id == res_uuid)
            if resource:
                resource.is_deleted = True
                resource.updated_at = datetime.now(timezone.utc)
                await resource.save()
                deleted += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    
    return {
        "message": f"Deleted {deleted} resources",
        "deleted": deleted,
        "failed": failed,
    }

