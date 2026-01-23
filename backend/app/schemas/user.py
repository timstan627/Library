"""
User Schemas - Authentication and Profile
"""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


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
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900)  # 15 minutes in seconds
    requires_mfa: bool = False


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
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
