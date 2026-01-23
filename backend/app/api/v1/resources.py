"""
Resources API Routes - Upload, Download, Management
"""
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.security import security_manager
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

router = APIRouter()


def generate_slug(title: str, existing_check: bool = False) -> str:
    """Generate URL-friendly slug from title."""
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    
    # Add random suffix for uniqueness
    suffix = security_manager.generate_secure_token(4)
    return f"{slug[:50]}-{suffix}"


@router.get("/my", response_model=ResourceListResponse)
async def get_my_resources(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's own resources (all visibility levels).
    
    This endpoint ensures complete data isolation - users only see their own uploads.
    """
    filters = [
        Resource.is_deleted == False,
        Resource.uploader["$id"] == current_user.id,
    ]
    
    query = Resource.find(*filters).sort("-created_at")
    
    total = await query.count()
    resources = await query.skip((page - 1) * size).limit(size).to_list()
    
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
    tags: Optional[str] = Form(None),  # Comma-separated
    visibility: str = Form("public"),
    password: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
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
    
    # Check user storage quota
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
    
    # Check for duplicate (by hash + uploader + course)
    # Prevent accidental re-uploads of same file, same course by same user
    file_hash = security_manager.hash_file(file_bytes)
    existing_duplicate = await Resource.find_one(
        Resource.file_hash == file_hash,
        Resource.uploader.id == current_user.id,
        Resource.course_code == course_code,
        Resource.title == title,
        Resource.is_deleted == False
    )
    
    if existing_duplicate:
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
    tag_list = list(set(tag_list))[:10]  # Max 10 unique tags
    
    # Create resource
    try:
        resource = Resource(
            title=title.strip(),
            slug=generate_slug(title),
            description=description.strip() if description else None,
            course_code=course_code.upper().strip(),
            department=department.strip() if department else None,
            semester=semester.strip() if semester else None,
            branch=branch.strip() if branch else None,
            tags=tag_list,
            
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
            uploader=current_user, # Link field assignment
            
            # Access
            visibility=visibility,
            password_hash=security_manager.hash_password(password) if password else None,
            
            # Moderation (Auto-approve for admins/moderators)
            moderation_status="approved" if current_user.role in ["admin", "moderator"] else "pending",
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"RESOURCE VALIDATION ERROR: {e}")
        # print(e.errors()) # if pydantic
        raise e
    
    try:
        await resource.create()
    except Exception as e:
        # Catch MongoDB duplicate key error (E11000)
        if "E11000" in str(e):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This exact resource (file/slug) already exists. Try changing the title.",
            )
        
        import traceback
        traceback.print_exc()
        print(f"RESOURCE CREATE ERROR: {e}")
        raise e
    
    # Update user storage
    current_user.storage_used_bytes += file_size
    await current_user.save()
    
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
):
    """Stream a resource file for preview (inline)."""
    try:
        resource_uuid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invalid resource ID format")

    resource = await Resource.find_one(Resource.id == resource_uuid, Resource.is_deleted == False)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    uploader_id = resource.uploader.ref.id if resource.uploader else None
    
    # Check visibility
    if resource.visibility == "private":
        if not current_user or (uploader_id != current_user.id and not current_user.is_moderator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
    
    # Check password
    if resource.is_password_protected:
        if not password or not security_manager.verify_password(password, resource.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password required or incorrect",
            )
            
            
    # View count is handled by the page load (get_resource_by_slug)
    # or we can verify cookie here too, but simpler to just stream.
    
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
        print(f"PREVIEW ERROR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stream file",
        )


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: str,
    password: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Download a resource file."""
    print(f"DEBUG_DOWNLOAD: Requested ID '{resource_id}' (type: {type(resource_id)})")
    try:
        resource_uuid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invalid resource ID format")

    resource = await Resource.find_one(Resource.id == resource_uuid, Resource.is_deleted == False)
    
    if not resource:
        print(f"DEBUG_DOWNLOAD: Resource not found for ID {resource_id}")
        r_del = await Resource.find_one(Resource.id == resource_id)
        if r_del:
            print(f"DEBUG_DOWNLOAD: Resource FOUND but is_deleted={r_del.is_deleted}")
        else:
            print("DEBUG_DOWNLOAD: Resource strictly NOT FOUND in DB")
            
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    uploader_id = resource.uploader.ref.id if resource.uploader else None
    
    # Check visibility
    if resource.visibility == "private":
        if not current_user or (uploader_id != current_user.id and not current_user.is_moderator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
    
    # Check password
    if resource.is_password_protected:
        if not password or not security_manager.verify_password(password, resource.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password required or incorrect",
            )
    
    # Download from Telegram
    try:
        file_bytes = await telegram_service.download_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}",
        )
    
    # Log download
    download_log = Download(
        user=current_user,
        resource=resource,
    )
    await download_log.create()
    
    # Increment download count
    resource.downloads += 1
    await resource.save()
    
    # Return file as streaming response
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
    resource_id: uuid.UUID,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_current_user),
):
    """Get resource details by ID."""
    resource = await Resource.find_one(Resource.id == resource_id, Resource.is_deleted == False)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    # Check visibility
    # resource.uploader is a Link, might need fetch if lazy, but default Beanie config fetches on access if properly defined?
    # Actually Link behaves like a reference. We need to compare IDs.
    # user_id check: resource.uploader.id if using Link? Or ensure definition?
    # In resource model: uploader: Optional[Link[User]] = None
    
    uploader_id = resource.uploader.ref.id if resource.uploader else None
    
    if resource.visibility == "private":
        if not current_user or (uploader_id != current_user.id and not current_user.is_moderator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
    
    
    # Increment view count (Unique by cookie)
    cookie_name = f"viewed_{resource.id}"
    if not request.cookies.get(cookie_name):
        resource.views += 1
        await resource.save()
        response.set_cookie(key=cookie_name, value="true", max_age=3600)  # 1 hour
    
    
    return resource


@router.get("/slug/{slug}", response_model=ResourceResponse)
async def get_resource_by_slug(
    slug: str,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_current_user),
):
    """Get resource details by slug."""
    resource = await Resource.find_one(Resource.slug == slug, Resource.is_deleted == False)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    uploader_id = resource.uploader.ref.id if resource.uploader else None
    
    # Check visibility
    if resource.visibility == "private":
        if not current_user or (uploader_id != current_user.id and not current_user.is_moderator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
    
    # Increment view count (Unique by cookie)
    cookie_name = f"viewed_{resource.id}"
    if not request.cookies.get(cookie_name):
        resource.views += 1
        await resource.save()
        response.set_cookie(key=cookie_name, value="true", max_age=3600)  # 1 hour
    
    
    return resource


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: uuid.UUID,
    data: ResourceUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update resource metadata."""
    resource = await Resource.find_one(Resource.id == resource_id, Resource.is_deleted == False)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    uploader_id = resource.uploader.ref.id if resource.uploader else None
    
    # Check ownership
    if uploader_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resource, field, value)
    
    await resource.save()
    
    return resource


@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
):
    """Soft delete a resource."""
    resource = await Resource.find_one(Resource.id == resource_id, Resource.is_deleted == False)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    uploader_id = resource.uploader.ref.id if resource.uploader else None
    
    # Check ownership
    if uploader_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Soft delete
    resource.is_deleted = True
    resource.deleted_at = datetime.now(timezone.utc)
    resource.deleted_by = current_user
    
    # Mangle unique fields to allow re-upload
    # Note: Slug is unique index. File hash is NOT unique index in model (unique=False implied or explicit?), 
    # but we check for duplicates manually in upload.
    # Resource model: IndexModel([("slug", 1)], unique=True)
    timestamp = int(datetime.now().timestamp())
    resource.slug = f"{resource.slug}_deleted_{timestamp}"
    resource.title = f"{resource.title} [DELETED]"
    
    # Update user storage
    if resource.uploader:
        # Need to fetch uploader object because storage update is on User document
        uploader = await resource.uploader.fetch()
        if uploader:
            uploader.storage_used_bytes = max(0, uploader.storage_used_bytes - resource.file_size)
            await uploader.save()
    
    await resource.save()
    
    return {"message": "Resource deleted successfully"}


@router.get("/", response_model=ResourceListResponse)
async def list_resources(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    course_code: Optional[str] = None,
    department: Optional[str] = None,
    uploader_id: Optional[str] = Query(None, description="Filter by uploader user ID"),
    current_user: Optional[User] = Depends(get_current_user),
):
    """List resources with pagination.
    
    Access control:
    - If uploader_id is provided: shows that user's resources (owner sees all, others see public only)
    - If no uploader_id: shows public resources only
    - Admins/moderators: can see all resources when explicitly filtering by uploader_id
    """
    filters = [Resource.is_deleted == False]
    
    # Handle uploader_id filtering for data isolation
    if uploader_id:
        try:
            uploader_uuid = uuid.UUID(uploader_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid uploader_id format"
            )
        
        # Check if current user is viewing their own resources
        is_owner = current_user and str(current_user.id) == uploader_id
        is_moderator = current_user and current_user.is_moderator
        
        # Build uploader filter - match resources by uploader reference
        filters.append(Resource.uploader["$id"] == uploader_uuid)
        
        # Non-owners can only see public resources from that uploader
        if not is_owner and not is_moderator:
            filters.append(Resource.visibility == "public")
    else:
        # No uploader_id provided - only show public resources (browse mode)
        filters.append(Resource.visibility == "public")
    
    if course_code:
        filters.append(Resource.course_code == course_code.upper())
    if department:
        filters.append(Resource.department == department)
    
    query = Resource.find(*filters).sort("-created_at")
    
    total = await query.count()
    resources = await query.skip((page - 1) * size).limit(size).to_list()
    
    pages = (total + size - 1) // size if total > 0 else 0
    
    return ResourceListResponse(
        results=resources,
        total=total,
        page=page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
    )

