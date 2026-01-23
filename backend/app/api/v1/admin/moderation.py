"""
Admin API - Content Moderation & Approval Workflow
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from beanie import PydanticObjectId
from datetime import datetime, timezone

from app.models.user import User
from app.models.resource import Resource
from app.schemas.moderation import (
    ModerationAction,
    ResourceModerationStatus
)
from app.api.v1.deps import get_current_user, require_admin
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/admin/moderation", tags=["Admin - Moderation"])


@router.get("/pending", response_model=List[ResourceModerationStatus])
async def get_pending_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
):
    """Get all pending resources awaiting moderation."""
    resources = (
        await Resource.find(
            Resource.moderation_status == "pending",
            Resource.is_deleted == False
        )
        .sort("-created_at")
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list()
    )
    
    result = []
    for resource in resources:
        # Fetch uploader details
        await resource.fetch_all_links()
        
        uploader_name = None
        uploader_email = None
        if resource.uploader:
            uploader_name = resource.uploader.display_name or "Unknown"
            uploader_email = resource.uploader.email
        
        result.append(
            ResourceModerationStatus(
                resource_id=str(resource.id),
                title=resource.title,
                status=resource.moderation_status,
                uploader_name=uploader_name,
                uploader_email=uploader_email,
                uploaded_at=resource.created_at,
            )
        )
    
    return result


@router.post("/{resource_id}/moderate")
async def moderate_resource(
    resource_id: str,
    action: ModerationAction,
    current_user: User = Depends(require_admin),
):
    """Approve or reject a resource."""
    try:
        obj_id = PydanticObjectId(resource_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resource ID")
    
    resource = await Resource.get(obj_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    if resource.moderation_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resource is already {resource.moderation_status}"
        )
    
    # Validate action
    if action.action not in ["approve", "reject"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'"
        )
    
    # Perform action
    if action.action == "approve":
        resource.moderation_status = "approved"
        resource.moderated_by = current_user
        resource.moderated_at = datetime.now(timezone.utc)
        audit_action = "approve_resource"
        
    else:  # reject
        if not action.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        resource.moderation_status = "rejected"
        resource.moderated_by = current_user
        resource.moderated_at = datetime.now(timezone.utc)
        resource.rejection_reason = action.rejection_reason
        audit_action = "reject_resource"
    
    await resource.save()
    
    # Audit log
    audit = AuditLog(
        action=audit_action,
        actor=current_user,
        target_type="resource",
        target_id=resource_id,
        details={
            "title": resource.title,
            "action": action.action,
            "rejection_reason": action.rejection_reason if action.action == "reject" else None
        }
    )
    await audit.create()
    
    # Fetch uploader for response
    await resource.fetch_all_links()
    uploader_name = resource.uploader.display_name if resource.uploader else None
    uploader_email = resource.uploader.email if resource.uploader else None
    
    return ResourceModerationStatus(
        resource_id=str(resource.id),
        title=resource.title,
        status=resource.moderation_status,
        uploader_name=uploader_name,
        uploader_email=uploader_email,
        uploaded_at=resource.created_at,
        moderated_by=str(current_user.id),
        moderated_at=resource.moderated_at,
        rejection_reason=resource.rejection_reason,
    )


@router.get("/history", response_model=List[ResourceModerationStatus])
async def get_moderation_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: str = Query(None, pattern="^(approved|rejected)$"),
    current_user: User = Depends(require_admin),
):
    """Get moderation history (approved/rejected resources)."""
    query = {
        "moderation_status": {"$in": ["approved", "rejected"]},
        "is_deleted": False
    }
    
    if status_filter:
        query["moderation_status"] = status_filter
    
    resources = (
        await Resource.find(query)
        .sort("-moderated_at")
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list()
    )
    
    result = []
    for resource in resources:
        await resource.fetch_all_links()
        
        uploader_name = resource.uploader.display_name if resource.uploader else None
        uploader_email = resource.uploader.email if resource.uploader else None
        moderated_by_id = str(resource.moderated_by.id) if resource.moderated_by else None
        
        result.append(
            ResourceModerationStatus(
                resource_id=str(resource.id),
                title=resource.title,
                status=resource.moderation_status,
                uploader_name=uploader_name,
                uploader_email=uploader_email,
                uploaded_at=resource.created_at,
                moderated_by=moderated_by_id,
                moderated_at=resource.moderated_at,
                rejection_reason=resource.rejection_reason,
            )
        )
    
    return result


@router.get("/stats")
async def get_moderation_stats(
    current_user: User = Depends(require_admin),
):
    """Get moderation statistics."""
    pending_count = await Resource.find(
        Resource.moderation_status == "pending",
        Resource.is_deleted == False
    ).count()
    
    approved_count = await Resource.find(
        Resource.moderation_status == "approved",
        Resource.is_deleted == False
    ).count()
    
    rejected_count = await Resource.find(
        Resource.moderation_status == "rejected",
        Resource.is_deleted == False
    ).count()
    
    return {
        "pending": pending_count,
        "approved": approved_count,
        "rejected": rejected_count,
        "total": pending_count + approved_count + rejected_count
    }
