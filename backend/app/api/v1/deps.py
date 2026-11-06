"""
API Dependencies - Authentication, Authorization, etc.
All database queries now use SQLAlchemy async sessions.
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import security_manager
from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user from JWT token (optional)."""
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = security_manager.verify_token(token, token_type="access")
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    # Banned/deactivated users are treated as anonymous everywhere the
    # optional dependency is used (read endpoints); the required dependency
    # rejects them with 403 below.
    if user and (user.is_banned or not user.is_active):
        return None
    
    return user


async def get_current_active_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current active user (required authentication)."""
    if not credentials:
        # RFC 9110: missing credentials → 401 with WWW-Authenticate, matching
        # the invalid/expired-token path below (never a bare 403, which the
        # frontend correctly interprets as a permissions error).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = security_manager.verify_token(token, token_type="access")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # A valid JWT for a deleted user is a stale credential, not a
        # missing resource — 401 tells the client to re-authenticate.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not active",
        )
    
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User is banned: {user.ban_reason or 'No reason provided'}",
        )
    
    logger.debug(f"Authenticated user {user.id} with role '{user.role}'")
    return user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current user and verify admin role."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_moderator_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current user and verify moderator role."""
    if not current_user.is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )
    return current_user


# Aliases — the canonical role checks live above; these names are kept
# because several routers import them (single implementation, no drift).
require_admin = get_admin_user
require_moderator = get_moderator_user


def ensure_resource_viewable(resource: Resource, current_user: Optional[User]) -> bool:
    """Raise 404/403 unless the caller may view this resource.

    - Pending/rejected resources are visible only to their owner and the
      moderation team until approved — existence is hidden from everyone
      else, matching the public search index (search.py).
    - Private resources stay owner/moderator-only.
    Returns True when the caller is owner or moderator (password bypass).

    Shared by the resource detail/preview/download routes and the ratings
    routes so visibility gating cannot drift between them.
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
