"""
Admin API Routes - User management, moderation, analytics
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.models.user import User
from app.models.resource import Resource
from app.models.download import Download
from app.models.report import Report
from app.api.v1.deps import get_admin_user, get_moderator_user
from app.services.telegram import telegram_service
from app.models.audit_log import AuditLog

router = APIRouter()


# ==================== Dashboard ====================

@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_moderator_user),
):
    """Get admin dashboard statistics."""
    # Total users
    total_users = await User.count()
    
    # Total resources
    total_resources = await Resource.find(Resource.is_deleted == False).count()
    
    # Total downloads
    total_downloads = await Download.count()
    
    # Total storage used (from DB Stats for accuracy)
    try:
        db = User.get_motor_collection().database
        stats = await db.command("dbStats")
        total_storage = stats.get("storageSize", 0)
    except:
        # Fallback to resource sum if DB stats fail
        resources = await Resource.find(Resource.is_deleted == False).to_list()
        total_storage = sum(r.file_size for r in resources)
    
    # Pending reports
    pending_reports = await Report.find(Report.status == "pending").count()
    
    # New users (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_users = await User.find(User.created_at >= week_ago).count()
    
    # New resources (last 7 days)
    new_resources = await Resource.find(
        Resource.is_deleted == False,
        Resource.created_at >= week_ago
    ).count()
    
    return {
        "total_users": total_users,
        "total_resources": total_resources,
        "total_downloads": total_downloads,
        "total_storage_bytes": total_storage,
        "total_storage_gb": round(total_storage / (1024 * 1024 * 1024), 2),
        "total_storage_mb": round(total_storage / (1024 * 1024), 2),
        "pending_reports": pending_reports,
        "new_users_7d": new_users,
        "new_resources_7d": new_resources,
    }


@router.get("/dashboard/storage")
async def get_database_stats(
    current_user: User = Depends(get_admin_user),
):
    """Get MongoDB database statistics."""
    try:
        # Get DB stats using a collection's database reference
        db = User.get_motor_collection().database
        stats = await db.command("dbStats")
        
        return {
            "db_name": stats.get("db"),
            "collections": stats.get("collections"),
            "objects": stats.get("objects"),
            "avg_obj_size": stats.get("avgObjSize"),
            "data_size_bytes": stats.get("dataSize"),
            "storage_size_bytes": stats.get("storageSize"),
            "index_size_bytes": stats.get("indexSize"),
            "storage_size_mb": round(stats.get("storageSize", 0) / (1024 * 1024), 2),
            "data_size_mb": round(stats.get("dataSize", 0) / (1024 * 1024), 2),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch database stats: {str(e)}",
        )


@router.get("/resources")
async def list_all_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_moderator_user),
):
    """List all resources for admin management."""
    filters = [Resource.is_deleted == False]
    
    query = Resource.find(*filters).sort("-created_at")
    
    total = await query.count()
    resources = await query.skip((page - 1) * page_size).limit(page_size).to_list()
    
    # Convert to response format
    results = []
    for r in resources:
        results.append({
            "id": str(r.id),
            "title": r.title,
            "slug": r.slug,
            "course_code": r.course_code,
            "file_name": r.file_name,
            "file_size": r.file_size,
            "downloads": r.downloads,
            "views": r.views,
            "visibility": r.visibility,
            "moderation_status": r.moderation_status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    
    return {
        "results": results,
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


# ==================== Users Management ====================

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    is_banned: Optional[bool] = None,
    current_user: User = Depends(get_admin_user),
):
    """List all users with filters."""
    # Build query
    filters = []
    if role:
        filters.append(User.role == role)
    if is_banned is not None:
        filters.append(User.is_banned == is_banned)
        
    query = User.find(*filters).sort("-created_at")
    
    total = await query.count()
    users = await query.skip((page - 1) * size).limit(size).to_list()
    
    pages = (total + size - 1) // size if total > 0 else 0
    
    return {
        "results": users,
        "total": total,
        "page": page,
        "pages": pages,
    }


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    role: str = Query(..., pattern="^(student|moderator|admin)$"),
    current_user: User = Depends(get_admin_user),
):
    """Update user role."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )
    
    user = await User.find_one(User.id == user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.role = role
    await user.save()
    
    return {"message": f"User role updated to {role}"}


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: uuid.UUID,
    reason: str = Query(..., min_length=5, max_length=500),
    current_user: User = Depends(get_admin_user),
):
    """Ban a user."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ban yourself",
        )
    
    user = await User.find_one(User.id == user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot ban an admin",
        )
    
    user.is_banned = True
    user.ban_reason = reason
    await user.save()
    
    # HIGH-005: Audit log for ban action
    try:
        audit = AuditLog(
            action="ban_user",
            actor=current_user,
            target_type="user",
            target_id=str(user_id),
            details={"email": user.email, "reason": reason}
        )
        await audit.create()
    except Exception as e:
        print(f"AUDIT LOG ERROR: {e}")
    
    return {"message": "User banned successfully"}


@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_admin_user),
):
    """Unban a user."""
    user = await User.find_one(User.id == user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.is_banned = False
    user.ban_reason = None
    await user.save()
    
    # HIGH-005: Audit log for unban action
    try:
        audit = AuditLog(
            action="unban_user",
            actor=current_user,
            target_type="user",
            target_id=str(user_id),
            details={"email": user.email}
        )
        await audit.create()
    except Exception as e:
        print(f"AUDIT LOG ERROR: {e}")
    
    return {"message": "User unbanned successfully"}


# ==================== Reports Management ====================

@router.get("/reports")
async def list_reports(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_moderator_user),
):
    """List all reports."""
    filters = []
    if status_filter:
        filters.append(Report.status == status_filter)
        
    query = Report.find(*filters).sort("-created_at")
    
    total = await query.count()
    reports = await query.skip((page - 1) * size).limit(size).to_list()
    
    pages = (total + size - 1) // size if total > 0 else 0
    
    # Convert reports to dict with necessary fields
    results = []
    for report in reports:
        results.append({
            "id": str(report.id),
            "reporter_id": str(report.reporter_id),
            "resource_id": str(report.resource_id),
            "reason": report.reason,
            "details": report.details,
            "status": report.status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        })
    
    return {
        "results": results,
        "total": total,
        "page": page,
        "pages": pages,
    }


@router.put("/reports/{report_id}")
async def update_report(
    report_id: uuid.UUID,
    status_update: str = Query(..., alias="status", pattern="^(reviewing|resolved|dismissed)$"),
    notes: Optional[str] = None,
    current_user: User = Depends(get_moderator_user),
):
    """Update report status."""
    report = await Report.find_one(Report.id == report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    report.status = status_update
    # report.moderator_notes = notes # Field might be missing in model definition, let's skip for now or add to model if needed. 
    # Beanie documents are flexible but we defined a schema.
    # The Report model in step 613 has `resolution_note` instead of `moderator_notes`.
    if notes:
        report.resolution_note = notes
        
    if status_update in ("resolved", "dismissed"):
        report.resolved_by = current_user
        # report.resolved_at = datetime.now(timezone.utc) # Missing in schema?
        # Checked step 613: Report model has `resolved_by`. Does not have `resolved_at`.
        pass
    
    await report.save()
    
    return {"message": f"Report status updated to {status_update}"}


# ==================== Resource Management ====================

@router.delete("/resources/{resource_id}/permanent")
async def permanently_delete_resource(
    resource_id: uuid.UUID,
    current_user: User = Depends(get_admin_user),
):
    """Permanently delete a resource (including from Telegram)."""
    resource = await Resource.find_one(Resource.id == resource_id)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    # Delete from Telegram
    try:
        await telegram_service.delete_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id,
            backup_message_id=resource.backup_telegram_message_id,
        )
    except Exception as e:
        # Log but continue with database deletion
        pass
    
    # Delete from database
    await resource.delete()
    
    return {"message": "Resource permanently deleted"}


@router.delete("/resources/{resource_id}")
async def delete_resource_admin(
    resource_id: uuid.UUID,
    current_user: User = Depends(get_admin_user),
):
    """Delete a resource (simpler endpoint for admin panel)."""
    resource = await Resource.find_one(Resource.id == resource_id)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    # Delete from Telegram (best effort)
    try:
        await telegram_service.delete_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id,
            backup_message_id=resource.backup_telegram_message_id,
        )
    except Exception:
        pass
    
    await resource.delete()
    return {"message": "Deleted"}


@router.post("/resources/bulk-delete")
async def bulk_delete_resources(
    resource_ids: List[str],
    current_user: User = Depends(get_admin_user),
):
    """Bulk delete multiple resources without confirmation."""
    deleted = 0
    errors = 0
    
    for rid in resource_ids:
        try:
            resource_uuid = uuid.UUID(rid)
            resource = await Resource.find_one(Resource.id == resource_uuid)
            if resource:
                try:
                    await telegram_service.delete_file(
                        message_id=resource.telegram_message_id,
                        channel_id=resource.telegram_channel_id,
                        backup_message_id=resource.backup_telegram_message_id,
                    )
                except Exception:
                    pass
                await resource.delete()
                deleted += 1
        except Exception:
            errors += 1
    
    return {"deleted": deleted, "errors": errors}


@router.delete("/clear-all-data")
async def clear_all_data(
    confirm: str = Query(..., description="Must be 'CONFIRM_DELETE_ALL' to proceed"),
    current_user: User = Depends(get_admin_user),
):
    """Clear ALL resources from the system (DANGEROUS - Admin only).
    
    This deletes all resources from:
    - MongoDB database
    - Telegram storage (best effort)
    
    Requires confirm='CONFIRM_DELETE_ALL' query parameter.
    """
    if confirm != "CONFIRM_DELETE_ALL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide confirm='CONFIRM_DELETE_ALL' to proceed"
        )
    
    # Get all resources
    resources = await Resource.find_all().to_list()
    deleted_count = 0
    telegram_errors = 0
    
    for resource in resources:
        # Try to delete from Telegram
        try:
            await telegram_service.delete_file(
                message_id=resource.telegram_message_id,
                channel_id=resource.telegram_channel_id,
                backup_message_id=resource.backup_telegram_message_id,
            )
        except Exception:
            telegram_errors += 1
        
        # Delete from database
        await resource.delete()
        deleted_count += 1
    
    # Reset user storage counts
    await User.find({}).update_many({"$set": {"storage_used_bytes": 0}})
    
    # Log the action
    await AuditLog.create(
        actor_id=current_user.id,
        action="clear_all_data",
        target_type="system",
        details={
            "deleted_resources": deleted_count,
            "telegram_errors": telegram_errors,
        }
    )
    
    return {
        "message": f"Cleared {deleted_count} resources",
        "deleted_count": deleted_count,
        "telegram_errors": telegram_errors,
    }

