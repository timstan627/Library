"""
API Dependencies - Authentication, Authorization, etc.
"""
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import security_manager
from app.models.user import User

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
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
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return None
    
    # Beanie find
    user = await User.find_one(User.id == user_uuid)
    
    return user


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> User:
    """Get current active user (required authentication)."""
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
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await User.find_one(User.id == user_uuid)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
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
    
    print(f"AUTH_DEBUG: User {user.email} (ID: {user.id}) role is '{user.role}'")
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


# Aliases for admin/moderator checks (consistent naming)
async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require admin role for endpoint access."""
    if current_user.role not in ['admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_moderator(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require moderator or admin role for endpoint access."""
    if current_user.role not in ['admin', 'moderator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )
    return current_user
