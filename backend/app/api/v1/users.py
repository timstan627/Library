"""
Users API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import security_manager
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, PasswordChangeRequest
from app.api.v1.deps import get_current_active_user

router = APIRouter(redirect_slashes=False)


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update current user profile."""
    if data.display_name is not None:
        current_user.display_name = data.display_name
    
    if data.avatar_url is not None:
        current_user.avatar_url = data.avatar_url
    
    await current_user.save()
    
    return current_user


@router.post("/me/change-password")
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Change current user password."""
    if not security_manager.verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    current_user.password_hash = security_manager.hash_password(data.new_password)
    await current_user.save()
    
    return {"message": "Password changed successfully"}


@router.get("/me/storage")
async def get_storage_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get user storage information."""
    return {
        "quota_bytes": current_user.storage_quota_bytes,
        "used_bytes": current_user.storage_used_bytes,
        "remaining_bytes": current_user.storage_remaining_bytes,
        "usage_percent": current_user.storage_usage_percent,
        "quota_mb": round(current_user.storage_quota_bytes / (1024 * 1024), 2),
        "used_mb": round(current_user.storage_used_bytes / (1024 * 1024), 2),
    }
