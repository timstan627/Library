"""
Password Reset API endpoint
"""
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field

from app.core.security import security_manager
from app.models.user import User

router = APIRouter()


# In-memory token storage (use Redis in production)
password_reset_tokens: dict[str, tuple[str, datetime]] = {}


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


@router.post("/forgot-password")
async def forgot_password(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
):
    """Request password reset email."""
    # Always return success to prevent email enumeration
    user = await User.find_one(User.email == data.email.lower())
    
    if user and user.is_active and not user.is_banned:
        # Generate reset token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Store token (in production, use Redis with TTL)
        password_reset_tokens[token] = (str(user.id), expires_at)
        
        # Send Email
        from app.services.email import email_service
        background_tasks.add_task(email_service.send_reset_password_email, user.email, token)
        
        # For development, log the token
        import logging
        logging.info(f"Password reset token for {user.email}: {token}")
    
    return {"message": "If an account exists, a reset link will be sent."}


@router.post("/reset-password")
async def reset_password(
    data: PasswordResetConfirm,
):
    """Reset password using token."""
    # Validate token
    if data.token not in password_reset_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    user_id, expires_at = password_reset_tokens[data.token]
    
    if datetime.now(timezone.utc) > expires_at:
        del password_reset_tokens[data.token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )
    
    # Get user
    try:
        user_uuid = uuid.UUID(user_id)
        user = await User.find_one(User.id == user_uuid)
    except ValueError:
        user = None
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )
    
    # Update password
    user.password_hash = security_manager.hash_password(data.new_password)
    await user.save()
    
    # Remove used token
    del password_reset_tokens[data.token]
    
    return {"message": "Password reset successfully"}
