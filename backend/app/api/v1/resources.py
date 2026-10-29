"""
Resources API Routes - Upload, Download, Management (SQLAlchemy)
"""
import re
import time
import hashlib
import mimetypes
from urllib.parse import quote
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_, update as sql_update
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
from app.services.download_manager import download_manager, FileNotFoundInTelegram

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


def _ensure_viewable(resource: Resource, current_user: Optional[User]) -> bool:
    """Raise 404/403 unless the caller may view this resource.

    - Pending/rejected resources are visible only to their owner and the
      moderation team until approved — existence is hidden from everyone
      else, matching the public search index (search.py).
    - Private resources stay owner/moderator-only.
    Returns True when the caller is owner or moderator (password bypass).
    """
    is_owner = current_user is not None and resource.uploader_id == current_user.id
    is_mod = current_user is not None and current_user.is_moderator

    if resource.moderation_status != "approved" and not (is_owner or is_mod):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )
    if resource.visibility == "private" and not (is_owner or is_mod):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This resource is private"
        )
    return is_owner or is_mod


def _content_disposition(file_name: Optional[str], inline: bool) -> str:
    """RFC 6266/5987 Content-Disposition built from a client-supplied filename.

    Control characters, CR/LF and quotes are stripped (header-injection
    safety); non-ASCII rides in the RFC 5987 parameter with an ASCII fallback.
    """
    name = (file_name or "download").replace("\x00", "")
    ascii_name = "".join(
        ch for ch in name if 32 <= ord(ch) < 127 and ch not in '"\\'
    ).strip() or "download"
    utf8_name = "".join(ch for ch in name if ord(ch) >= 32)
    disposition = "inline" if inline else "attachment"
    return f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(utf8_name)}"

# In-memory view deduplication: tracks {hash: timestamp} to prevent
# the same visitor from incrementing views on repeated page loads.
# Each entry expires after 1 hour (3600 seconds).
_view_tracker: dict[str, float] = {}
_VIEW_TTL = 3600  # 1 hour

def _should_count_view(resource_id: str, request: Request) -> bool:
    """Check if this visit should count as a view (IP + User-Agent dedup)."""
    # Clean expired entries periodically (every ~100 checks)
    now = time.time()
    if len(_view_tracker) > 500:
        expired = [k for k, v in _view_tracker.items() if now - v > _VIEW_TTL]
        for k in expired:
            del _view_tracker[k]
    
    # Create a unique hash from resource_id + visitor IP + User-Agent
    client_ip = request.client.host if request.client else 'unknown'
    user_agent = request.headers.get('user-agent', 'unknown')
    key = hashlib.md5(f"{resource_id}:{client_ip}:{user_agent}".encode()).hexdigest()
    
    if key in _view_tracker and (now - _view_tracker[key]) < _VIEW_TTL:
        return False  # Already viewed within the TTL window
    
    _view_tracker[key] = now
    return True


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
    # Validate file size — read in chunks so an oversized body can't exhaust
    # memory, and answer 413 (not 400) when the cap is exceeded.
    max_bytes = settings.max_file_size_bytes
    chunks: list[bytes] = []
    file_size = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        file_size += len(chunk)
        if file_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB",
            )
        chunks.append(chunk)
    file_bytes = b"".join(chunks)
    
    # Validate visibility + password BEFORE any storage upload so a rejected
    # request can never leave an orphaned file in the Telegram channel.
    allowed_visibilities = {"public", "unlisted", "private", "password"}
    if visibility not in allowed_visibilities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid visibility. Must be one of: {', '.join(sorted(allowed_visibilities))}",
        )
    if visibility == "password" and not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for password-protected visibility",
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
    
    # Private visibility: no password needed (validated earlier)
    if visibility == "private":
        password = None
    
    # Determine moderation status:
    # - Private → auto-approved (only uploader sees it)
    # - Admin/moderator → auto-approved
    # - Everyone else → pending
    if visibility == "private":
        mod_status = "approved"
    elif current_user.role in ["admin", "moderator"]:
        mod_status = "approved"
    else:
        mod_status = "pending"

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
        # Server-derived MIME: the client-declared Content-Type is not
        # trusted (it is trivially spoofable and is what the preview
        # endpoint serves); the extension allowlist constrains this value.
        mime_type=mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream",
        file_hash=file_hash,
        file_extension=file_extension,

        # Uploader
        uploader_id=current_user.id,

        # Access
        visibility=visibility,
        password_hash=security_manager.hash_password(password) if password else None,

        # Moderation
        moderation_status=mod_status,
    )
    db.add(resource)
    try:
        await db.flush()
    except Exception as e:
        logger.exception("Resource creation error")
        if "UNIQUE" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This exact resource (file/slug) already exists. Try changing the title.",
            )
        raise
    await db.refresh(resource)

    # Update user storage atomically (concurrent uploads must not lose
    # increments).
    await db.execute(
        sql_update(User)
        .where(User.id == current_user.id)
        .values(storage_used_bytes=User.storage_used_bytes + file_size)
    )
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
    """Stream a resource file for preview (inline) via hybrid download manager."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Moderation + visibility gate: pending/rejected resources are hidden
    # (404) from everyone but their owner and the moderation team; private
    # resources remain owner/moderator-only.
    is_owner_or_admin = _ensure_viewable(resource, current_user)
    
    # Check password for password-protected resources
    if resource.visibility == "password" and not is_owner_or_admin:
        if not password or not security_manager.verify_password(password, resource.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password required or incorrect")
    
    # Eagerly resolve file (disk cache or Telegram download) BEFORE starting response
    # This ensures errors return proper HTTP status codes instead of network errors
    try:
        file_path = await download_manager.get_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id or 0,
        )
    except FileNotFoundInTelegram as e:
        logger.warning(f"File not found in Telegram for preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File is no longer available on the storage server. It may have been deleted."
        )
    except Exception as e:
        logger.error(f"Preview file resolution failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load file for preview")
    
    # Stream from resolved disk path
    from starlette.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        media_type=resource.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": _content_disposition(resource.file_name, inline=True),
        },
    )


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: str,
    password: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a resource file via hybrid download manager (disk cache + streaming)."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Moderation + visibility gate: pending/rejected resources are hidden
    # (404) from everyone but their owner and the moderation team; private
    # resources remain owner/moderator-only.
    is_owner_or_admin = _ensure_viewable(resource, current_user)
    
    # Check password for password-protected resources
    if resource.visibility == "password" and not is_owner_or_admin:
        if not password or not security_manager.verify_password(password, resource.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password required or incorrect")
    
    # Eagerly resolve file BEFORE starting response — prevents network errors
    try:
        file_path = await download_manager.get_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id or 0,
        )
    except FileNotFoundInTelegram as e:
        logger.warning(f"File not found in Telegram for download: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File is no longer available on the storage server. It may have been deleted."
        )
    except Exception as e:
        logger.error(f"Download file resolution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )
    
    # Log download
    download_log = Download(
        user_id=current_user.id if current_user else None,
        resource_id=resource.id,
    )
    db.add(download_log)

    # Increment download count atomically (concurrent downloads must not
    # lose increments).
    await db.execute(
        sql_update(Resource).where(Resource.id == resource.id).values(downloads=Resource.downloads + 1)
    )
    await db.flush()
    
    # Serve file from disk (efficient, low memory)
    from starlette.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        media_type=resource.mime_type,
        headers={
            "Content-Disposition": _content_disposition(resource.file_name, inline=False),
        },
    )


@router.get("/{resource_id}/preview-text")
async def preview_text_resource(
    resource_id: str,
    password: Optional[str] = Query(None),
    max_size: int = Query(default=102400, le=512000),  # Default 100KB, max 500KB
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the text content of a resource file for inline preview (no iframe needed)."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Only allow text-based MIME types
    text_types = ['text/', 'application/json', 'application/xml', 'application/csv']
    is_text = any(resource.mime_type and resource.mime_type.startswith(t) for t in text_types)
    if not is_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only text-based files can be previewed as text")
    
    # Moderation + visibility gate: pending/rejected resources are hidden
    # (404) from everyone but their owner and the moderation team; private
    # resources remain owner/moderator-only.
    is_owner_or_admin = _ensure_viewable(resource, current_user)
    
    # Check password for password-protected resources
    if resource.visibility == "password" and not is_owner_or_admin:
        if not password or not security_manager.verify_password(password, resource.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password required or incorrect")
    
    # Get the file
    try:
        file_path = await download_manager.get_file(
            message_id=resource.telegram_message_id,
            channel_id=resource.telegram_channel_id or 0,
        )
    except FileNotFoundInTelegram as e:
        logger.warning(f"Text preview — file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File is no longer available on the storage server."
        )
    except Exception as e:
        logger.error(f"Text preview file resolution failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load file")
    
    # Read text content (limited to max_size bytes)
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(max_size + 1)  # Read 1 extra byte to detect truncation
        
        truncated = len(content) > max_size
        if truncated:
            content = content[:max_size]
        
        # Count lines
        line_count = content.count('\n') + 1
        
        return {
            "content": content,
            "truncated": truncated,
            "file_name": resource.file_name,
            "mime_type": resource.mime_type,
            "line_count": line_count,
            "total_size": resource.file_size,
        }
    except Exception as e:
        logger.error(f"Failed to read text file: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to read file content")


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
    
    # Moderation + visibility gate (pending/rejected hidden, private owner-only)
    _ensure_viewable(resource, current_user)
    
    # Increment view count (deduplicated by IP + User-Agent, 1 hour window)
    # Atomic UPDATE: a read-modify-write `resource.views += 1` loses
    # increments under concurrent views. The execute() syncs the ORM state;
    # refresh to read the authoritative value for the response.
    if _should_count_view(resource.id, request):
        await db.execute(
            sql_update(Resource).where(Resource.id == resource.id).values(views=Resource.views + 1)
        )
        await db.refresh(resource, attribute_names=["views"])
        await db.commit()

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
    
    # Moderation + visibility gate (pending/rejected hidden, private owner-only)
    _ensure_viewable(resource, current_user)
    
    # Increment view count (deduplicated by IP + User-Agent, 1 hour window)
    # Atomic UPDATE (see get_resource).
    if _should_count_view(resource.id, request):
        await db.execute(
            sql_update(Resource).where(Resource.id == resource.id).values(views=Resource.views + 1)
        )
        await db.refresh(resource, attribute_names=["views"])
        await db.commit()

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
    
    # Close the moderation bypass: a private upload is auto-approved (only
    # the owner can see it), so a non-moderator flipping it to public/unlisted
    # must re-enter the moderation queue.
    new_visibility = update_data.get("visibility")
    if new_visibility and new_visibility != resource.visibility:
        if resource.moderation_status == "approved" and new_visibility != "private" and not current_user.is_moderator:
            update_data["moderation_status"] = "pending"
    
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
    
    # Update user storage atomically
    if resource.uploader_id:
        await db.execute(
            sql_update(User)
            .where(User.id == resource.uploader_id)
            .values(storage_used_bytes=func.max(0, User.storage_used_bytes - resource.file_size))
        )
    
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
            # Non-owners only see approved public + password resources
            filters.append(Resource.visibility.in_(["public", "password"]))
            filters.append(Resource.moderation_status == "approved")
        # Owner sees ALL their resources (public, unlisted, private, password)
    else:
        # Public browse: approved public + password-protected (with lock icon)
        # only — pending/rejected content stays out of listings
        filters.append(Resource.visibility.in_(["public", "password"]))
        filters.append(Resource.moderation_status == "approved")
    
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
