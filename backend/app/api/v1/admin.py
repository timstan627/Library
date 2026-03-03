"""
Admin API Routes (SQLAlchemy) - Dashboard, User mgmt, Reports, Resource mgmt
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_db_path, get_db_size
from app.models.user import User
from app.models.resource import Resource
from app.models.download import Download
from app.models.report import Report
from app.api.v1.deps import get_admin_user, get_moderator_user
from app.services.telegram import telegram_service
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Dashboard ====================

@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_moderator_user),
):
    """Get admin dashboard statistics (served from StatsEngine cache)."""
    from app.services.cache import cache_service
    
    data = await cache_service.get_stats("admin_dashboard_full")
    if data:
        return data
    
    return {
        "total_users": 0, "total_resources": 0, "total_downloads": 0,
        "total_storage_bytes": 0, "total_storage_gb": 0, "total_storage_mb": 0,
        "pending_reports": 0, "new_users_7d": 0, "new_resources_7d": 0,
    }


@router.get("/dashboard/storage")
async def get_database_stats(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SQLite database statistics."""
    db_size = get_db_size()
    db_path = str(get_db_path())
    
    # Count records in each table
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar()
    resource_count = (await db.execute(select(func.count()).select_from(Resource))).scalar()
    download_count = (await db.execute(select(func.count()).select_from(Download))).scalar()
    
    return {
        "db_name": "student_library.db",
        "db_path": db_path,
        "storage_size_bytes": db_size,
        "storage_size_mb": round(db_size / (1024 * 1024), 2),
        "users": user_count,
        "resources": resource_count,
        "downloads": download_count,
    }


@router.get("/resources")
async def list_all_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_moderator_user),
    db: AsyncSession = Depends(get_db),
):
    """List all resources for admin management."""
    base_filter = Resource.is_deleted == False
    
    count_result = await db.execute(select(func.count()).select_from(Resource).where(base_filter))
    total = count_result.scalar()
    
    result = await db.execute(
        select(Resource).where(base_filter)
        .order_by(Resource.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    resources = result.scalars().all()
    
    results = []
    for r in resources:
        results.append({
            "id": str(r.id), "title": r.title, "slug": r.slug,
            "course_code": r.course_code, "file_name": r.file_name,
            "file_size": r.file_size, "downloads": r.downloads, "views": r.views,
            "visibility": r.visibility, "moderation_status": r.moderation_status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    
    return {
        "results": results, "total": total, "page": page,
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
    db: AsyncSession = Depends(get_db),
):
    """List all users with filters."""
    filters = []
    if role:
        filters.append(User.role == role)
    if is_banned is not None:
        filters.append(User.is_banned == is_banned)
    
    combined = and_(*filters) if filters else True
    
    count_result = await db.execute(select(func.count()).select_from(User).where(combined))
    total = count_result.scalar()
    
    result = await db.execute(
        select(User).where(combined)
        .order_by(User.created_at.desc())
        .offset((page - 1) * size).limit(size)
    )
    users = result.scalars().all()
    
    pages = (total + size - 1) // size if total > 0 else 0
    return {"results": users, "total": total, "page": page, "pages": pages}


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str = Query(..., pattern="^(student|moderator|admin)$"),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user role."""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.role = role
    await db.flush()
    return {"message": f"User role updated to {role}"}


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    reason: str = Query(..., min_length=5, max_length=500),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Ban a user."""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot ban yourself")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot ban an admin")
    
    user.is_banned = True
    user.ban_reason = reason
    
    try:
        audit = AuditLog(action="ban_user", actor_id=current_user.id, target_type="user",
                        target_id=str(user_id), details_json=json.dumps({"email": user.email, "reason": reason}))
        db.add(audit)
    except Exception as e:
        logger.error(f"Audit log error: {e}")
    
    await db.flush()
    return {"message": "User banned successfully"}


@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Unban a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.is_banned = False
    user.ban_reason = None
    
    try:
        audit = AuditLog(action="unban_user", actor_id=current_user.id, target_type="user",
                        target_id=str(user_id), details_json=json.dumps({"email": user.email}))
        db.add(audit)
    except Exception as e:
        logger.error(f"Audit log error: {e}")
    
    await db.flush()
    return {"message": "User unbanned successfully"}


# ==================== Reports ====================

@router.get("/reports")
async def list_reports(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_moderator_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reports."""
    filters = []
    if status_filter:
        filters.append(Report.status == status_filter)
    
    combined = and_(*filters) if filters else True
    
    count_result = await db.execute(select(func.count()).select_from(Report).where(combined))
    total = count_result.scalar()
    
    result = await db.execute(
        select(Report).where(combined)
        .order_by(Report.created_at.desc())
        .offset((page - 1) * size).limit(size)
    )
    reports = result.scalars().all()
    
    results = []
    for report in reports:
        results.append({
            "id": str(report.id), "reporter_id": str(report.reporter_id),
            "resource_id": str(report.resource_id), "reason": report.reason,
            "details": report.details, "status": report.status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        })
    
    pages = (total + size - 1) // size if total > 0 else 0
    return {"results": results, "total": total, "page": page, "pages": pages}


@router.put("/reports/{report_id}")
async def update_report(
    report_id: str,
    status_update: str = Query(..., alias="status", pattern="^(reviewing|resolved|dismissed)$"),
    notes: Optional[str] = None,
    current_user: User = Depends(get_moderator_user),
    db: AsyncSession = Depends(get_db),
):
    """Update report status."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    report.status = status_update
    if notes:
        report.resolution_note = notes
    if status_update in ("resolved", "dismissed"):
        report.resolved_by_id = current_user.id
    
    await db.flush()
    return {"message": f"Report status updated to {status_update}"}


# ==================== Resource Management ====================

@router.delete("/resources/{resource_id}/permanent")
async def permanently_delete_resource(
    resource_id: str,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a resource (including from Telegram)."""
    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    try:
        await telegram_service.delete_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id,
            backup_message_id=resource.backup_telegram_message_id,
        )
    except Exception:
        pass
    
    await db.delete(resource)
    await db.flush()
    return {"message": "Resource permanently deleted"}


@router.delete("/resources/{resource_id}")
async def delete_resource_admin(
    resource_id: str,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a resource."""
    result = await db.execute(select(Resource).where(Resource.id == resource_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    try:
        await telegram_service.delete_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id,
            backup_message_id=resource.backup_telegram_message_id,
        )
    except Exception:
        pass
    
    await db.delete(resource)
    await db.flush()
    return {"message": "Deleted"}


@router.post("/resources/bulk-delete")
async def bulk_delete_resources(
    resource_ids: List[str],
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk delete multiple resources."""
    deleted = 0
    errors = 0
    
    for rid in resource_ids:
        try:
            result = await db.execute(select(Resource).where(Resource.id == rid))
            resource = result.scalar_one_or_none()
            if resource:
                try:
                    await telegram_service.delete_file(
                        message_id=resource.telegram_message_id,
                        channel_id=resource.telegram_channel_id,
                        backup_message_id=resource.backup_telegram_message_id,
                    )
                except Exception:
                    pass
                await db.delete(resource)
                deleted += 1
        except Exception:
            errors += 1
    
    await db.flush()
    return {"deleted": deleted, "errors": errors}


@router.delete("/clear-all-data")
async def clear_all_data(
    confirm: str = Query(..., description="Must be 'CONFIRM_DELETE_ALL' to proceed"),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear ALL resources from the system (DANGEROUS)."""
    from app.core.config import settings
    
    if not settings.debug:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only available in development mode")
    if confirm != "CONFIRM_DELETE_ALL":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must provide confirm='CONFIRM_DELETE_ALL'")
    
    # Get all resources for Telegram deletion
    result = await db.execute(select(Resource))
    resources = result.scalars().all()
    deleted_count = 0
    telegram_errors = 0
    
    for resource in resources:
        try:
            await telegram_service.delete_file(
                message_id=resource.telegram_message_id,
                channel_id=resource.telegram_channel_id,
                backup_message_id=resource.backup_telegram_message_id,
            )
        except Exception:
            telegram_errors += 1
        
        await db.delete(resource)
        deleted_count += 1
    
    # Reset user storage
    await db.execute(update(User).values(storage_used_bytes=0))
    
    # Audit log
    audit = AuditLog(
        actor_id=current_user.id, action="clear_all_data", target_type="system", target_id="all",
        details_json=json.dumps({"deleted_resources": deleted_count, "telegram_errors": telegram_errors})
    )
    db.add(audit)
    await db.flush()
    
    return {"message": f"Cleared {deleted_count} resources", "deleted_count": deleted_count, "telegram_errors": telegram_errors}
