"""
Password Reset API endpoint (SQLAlchemy)
"""
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import security_manager
from app.models.user import User

router = APIRouter()

# In-memory token storage
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
    db: AsyncSession = Depends(get_db),
):
    """Request password reset email."""
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()
    
    if user and user.is_active and not user.is_banned:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        password_reset_tokens[token] = (str(user.id), expires_at)
        
        from app.services.email import email_service
        background_tasks.add_task(email_service.send_reset_password_email, user.email, token)
        
        import logging
        logging.info(f"Password reset token for {user.email}: {token}")
    
    return {"message": "If an account exists, a reset link will be sent."}


@router.post("/reset-password")
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using token."""
    if data.token not in password_reset_tokens:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    
    user_id, expires_at = password_reset_tokens[data.token]
    
    if datetime.now(timezone.utc) > expires_at:
        del password_reset_tokens[data.token]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
    
    user.password_hash = security_manager.hash_password(data.new_password)
    await db.flush()
    
    del password_reset_tokens[data.token]
    
    return {"message": "Password reset successfully"}
