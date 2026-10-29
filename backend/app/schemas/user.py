"""
User Schemas - Authentication and Profile
"""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=6)


class UserResponse(BaseModel):
    """Schema for user response."""
    id: uuid.UUID
    email: str
    email_verified: bool
    display_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    mfa_enabled: bool
    storage_quota_bytes: int
    storage_used_bytes: int
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    # Reject unknown fields (e.g. role, is_active) with 422 instead of
    # silently ignoring them — makes tamper attempts visible to clients.
    model_config = ConfigDict(extra="forbid")

    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900)  # 15 minutes in seconds
    requires_mfa: bool = False


class RefreshRequest(BaseModel):
    """Schema for token refresh."""
    refresh_token: str = Field(..., min_length=10)


class MFASetupResponse(BaseModel):
    """Schema for MFA setup response."""
    secret: str
    qr_code_base64: str
    provisioning_uri: str


class MFAVerifyRequest(BaseModel):
    """Schema for MFA verification."""
    code: str = Field(..., min_length=6, max_length=6)


class PasswordChangeRequest(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


def validate_password_strength(v: str) -> str:
    """Shared complexity rules for any user-chosen password.

    Register, change-password, and password-reset must all enforce the same
    bar — a reset link must not become the weak-password loophole.
    """
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    return v


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str = Field(..., min_length=10, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)
