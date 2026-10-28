"""
Password Reset API endpoint (SQLAlchemy)
"""
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import security_manager
from app.models.user import User, Session

router = APIRouter()

# In-memory token storage — only SHA-256 digests are kept, so a memory read
# can't be replayed as a valid reset link. The raw token exists solely in the
# email delivered to the account owner.
password_reset_tokens: dict[str, tuple[str, datetime]] = {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


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
        
        password_reset_tokens[_hash_token(token)] = (str(user.id), expires_at)
        
        from app.services.email import email_service
        background_tasks.add_task(email_service.send_reset_password_email, user.email, token)
    
    return {"message": "If an account exists, a reset link will be sent."}


@router.post("/reset-password")
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using token."""
    token_hash = _hash_token(data.token)
    if token_hash not in password_reset_tokens:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    
    user_id, expires_at = password_reset_tokens[token_hash]
    
    if datetime.now(timezone.utc) > expires_at:
        del password_reset_tokens[token_hash]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or user.is_banned:
        # Banned accounts can't complete a reset to regain access
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    
    user.password_hash = security_manager.hash_password(data.new_password)
    
    # New password invalidates every existing session
    await db.execute(delete(Session).where(Session.user_id == user.id))
    await db.flush()
    
    del password_reset_tokens[token_hash]
    
    return {"message": "Password reset successfully"}
