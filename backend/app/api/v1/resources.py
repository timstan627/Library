"""
Resources API Routes - Upload, Download, Management (SQLAlchemy)
"""
import re
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import security_manager
from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.models.download import Download
from app.schemas.resource import (
    ResourceCreate,
    ResourceResponse,
    ResourceUpdate,
    ResourceListResponse,
    ResourceUploadResponse,
)
from app.api.v1.deps import get_current_user, get_current_active_user
from app.services.telegram import telegram_service

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


def generate_slug(title: str, existing_check: bool = False) -> str:
    """Generate URL-friendly slug from title."""
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    
    suffix = security_manager.generate_secure_token(4)
    return f"{slug[:50]}-{suffix}"


@router.get("/my", response_model=ResourceListResponse)
async def get_my_resources(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's own resources (all visibility levels)."""
    base_filter = and_(
        Resource.is_deleted == False,
        Resource.uploader_id == current_user.id,
    )
    
    # Count
    count_result = await db.execute(select(func.count()).select_from(Resource).where(base_filter))
    total = count_result.scalar()
    
    # Fetch page
    result = await db.execute(
        select(Resource)
        .where(base_filter)
        .order_by(Resource.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    resources = result.scalars().all()
    
    pages = (total + size - 1) // size if total > 0 else 0
    
    return ResourceListResponse(
        results=resources,
        total=total,
        page=page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
    )


@router.post("/upload", response_model=ResourceUploadResponse)
async def upload_resource(
    file: UploadFile = File(...),
    title: str = Form(...),
    course_code: str = Form(...),
    description: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    semester: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    visibility: str = Form("public"),
    password: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new resource file."""
    # Validate file size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB",
        )
    
    # Check storage quota
    if current_user.storage_used_bytes + file_size > current_user.storage_quota_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage quota exceeded",
        )
    
    # Validate file extension
    file_extension = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if file_extension not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.allowed_extensions_list)}",
        )
    
    # Check for duplicate
    file_hash = security_manager.hash_file(file_bytes)
    dup_result = await db.execute(
        select(Resource).where(
            Resource.file_hash == file_hash,
            Resource.uploader_id == current_user.id,
            Resource.course_code == course_code,
            Resource.title == title,
            Resource.is_deleted == False,
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already uploaded this file with the same title for this course.",
        )
    
    # Upload to Telegram
    try:
        telegram_result = await telegram_service.upload_file(
            file_bytes=file_bytes,
            filename=file.filename,
            caption=f"{title} | {course_code}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )
    
    # Parse tags
    tag_list = [t.strip().lower() for t in tags.split(',')] if tags else []
    tag_list = list(set(tag_list))[:10]
    
    # Create resource
    try:
        resource = Resource(
            title=title.strip(),
            slug=generate_slug(title),
            description=description.strip() if description else None,
            course_code=course_code.upper().strip(),
            semester=semester.strip() if semester else None,
            branch=branch.strip() if branch else None,
            tags_str=",".join(tag_list) if tag_list else None,
            
            # Telegram storage
            telegram_file_id=telegram_result["file_id"],
            telegram_message_id=telegram_result["message_id"],
            telegram_channel_id=telegram_result["channel_id"],
            
            # File metadata
            file_name=file.filename,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            file_hash=file_hash,
            file_extension=file_extension,
            
            # Uploader
            uploader_id=current_user.id,
            
            # Access
            visibility=visibility,
            password_hash=security_manager.hash_password(password) if password else None,
            
            # Moderation
            moderation_status="approved" if current_user.role in ["admin", "moderator"] else "pending",
        )
        db.add(resource)
        await db.flush()
        await db.refresh(resource)
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Resource creation error: {e}")
        if "UNIQUE" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This exact resource (file/slug) already exists. Try changing the title.",
            )
        raise e
    
    # Update user storage
    current_user.storage_used_bytes += file_size
    await db.flush()
    
    # Invalidate cached stats
    from app.services.cache import cache_service
    cache_service.invalidate_on_upload()
    
    return ResourceUploadResponse(
        id=resource.id,
        slug=resource.slug,
        title=resource.title,
        file_name=resource.file_name,
        file_size=resource.file_size,
        moderation_status=resource.moderation_status,
        message="Resource uploaded successfully"
    )


@router.get("/{resource_id}/preview")
async def preview_resource(
    resource_id: str,
    password: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream a resource file for preview (inline)."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Check visibility
    if resource.visibility == "private":
        if not current_user or (resource.uploader_id != current_user.id and not current_user.is_moderator):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Check password
    if resource.is_password_protected:
        if not password or not security_manager.verify_password(password, resource.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password required or incorrect")
    
    # Stream file
    try:
        file_stream = telegram_service.stream_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id,
        )
        
        return StreamingResponse(
            file_stream,
            media_type=resource.mime_type or "application/octet-stream",
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{resource.file_name}",
                "Content-Length": str(resource.file_size),
            }
        )
    except Exception as e:
        logger.error(f"Preview error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to stream file")


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: str,
    password: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a resource file."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Check visibility
    if resource.visibility == "private":
        if not current_user or (resource.uploader_id != current_user.id and not current_user.is_moderator):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Check password
    if resource.is_password_protected:
        if not password or not security_manager.verify_password(password, resource.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password required or incorrect")
    
    # Download from Telegram
    try:
        file_bytes = await telegram_service.download_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to download file: {str(e)}")
    
    # Log download
    download_log = Download(
        user_id=current_user.id if current_user else None,
        resource_id=resource.id,
    )
    db.add(download_log)
    
    # Increment download count
    resource.downloads += 1
    await db.flush()
    
    # Return file
    from io import BytesIO
    file_stream = BytesIO(file_bytes)
    
    return StreamingResponse(
        file_stream,
        media_type=resource.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{resource.file_name}"'
        }
    )


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get resource details by ID."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Check visibility
    if resource.visibility == "private":
        if not current_user or (resource.uploader_id != current_user.id and not current_user.is_moderator):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Increment view count (unique by cookie)
    cookie_name = f"viewed_{resource.id}"
    if not request.cookies.get(cookie_name):
        resource.views += 1
        await db.flush()
        response.set_cookie(key=cookie_name, value="true", max_age=3600, httponly=True, samesite="lax")
    
    return resource


@router.get("/slug/{slug}", response_model=ResourceResponse)
async def get_resource_by_slug(
    slug: str,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get resource details by slug."""
    result = await db.execute(
        select(Resource).where(Resource.slug == slug, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Check visibility
    if resource.visibility == "private":
        if not current_user or (resource.uploader_id != current_user.id and not current_user.is_moderator):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Increment view count
    cookie_name = f"viewed_{resource.id}"
    if not request.cookies.get(cookie_name):
        resource.views += 1
        await db.flush()
        response.set_cookie(key=cookie_name, value="true", max_age=3600, httponly=True, samesite="lax")
    
    return resource


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: str,
    data: ResourceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update resource metadata."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Check ownership
    if resource.uploader_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resource, field, value)
    
    await db.flush()
    
    return resource


@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a resource."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Check ownership
    if resource.uploader_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Soft delete
    resource.is_deleted = True
    resource.deleted_at = datetime.now(timezone.utc)
    resource.deleted_by_id = current_user.id
    
    # Mangle unique fields
    timestamp = int(datetime.now().timestamp())
    resource.slug = f"{resource.slug}_deleted_{timestamp}"
    resource.title = f"{resource.title} [DELETED]"
    
    # Update user storage
    if resource.uploader_id:
        uploader_result = await db.execute(select(User).where(User.id == resource.uploader_id))
        uploader = uploader_result.scalar_one_or_none()
        if uploader:
            uploader.storage_used_bytes = max(0, uploader.storage_used_bytes - resource.file_size)
    
    await db.flush()
    
    # Invalidate cached stats
    from app.services.cache import cache_service
    cache_service.invalidate_on_delete()
    
    return {"message": "Resource deleted successfully"}


@router.get("/", response_model=ResourceListResponse)
async def list_resources(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    course_code: Optional[str] = None,
    department: Optional[str] = None,
    uploader_id: Optional[str] = Query(None, description="Filter by uploader user ID"),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List resources with pagination."""
    filters = [Resource.is_deleted == False]
    
    if uploader_id:
        is_owner = current_user and str(current_user.id) == uploader_id
        is_moderator = current_user and current_user.is_moderator
        
        filters.append(Resource.uploader_id == uploader_id)
        
        if not is_owner and not is_moderator:
            filters.append(Resource.visibility == "public")
    else:
        filters.append(Resource.visibility == "public")
    
    if course_code:
        filters.append(Resource.course_code == course_code.upper())
    
    # Count
    count_result = await db.execute(select(func.count()).select_from(Resource).where(and_(*filters)))
    total = count_result.scalar()
    
    # Fetch page
    result = await db.execute(
        select(Resource)
        .where(and_(*filters))
        .order_by(Resource.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    resources = result.scalars().all()
    
    pages = (total + size - 1) // size if total > 0 else 0
    
    return ResourceListResponse(
        results=resources,
        total=total,
        page=page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
    )
