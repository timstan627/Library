"""
User Documents (MongoDB)
"""
from datetime import datetime
from typing import Optional, List, Annotated
from uuid import UUID, uuid4
from beanie import Document, Link
from pydantic import Field, EmailStr
from pymongo import IndexModel

from app.models.base import TimestampMixin

class User(Document, TimestampMixin):
    """User account document."""
    
    # Identity
    id: UUID = Field(default_factory=uuid4)
    email: str = Field(..., description="User email address")
    email_verified: bool = False
    password_hash: str
    
    # Profile
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Role & Permissions
    role: str = "student" # student, moderator, admin
    
    # Trusted Contributor Status
    is_trusted: bool = Field(default=False, description="Auto-approve uploads for trusted users")
    promoted_at: Optional[datetime] = Field(None, description="When user was promoted to trusted")
    promoted_by: Optional[str] = Field(None, description="Admin ID who promoted the user")
    
    # MFA
    mfa_secret: Optional[str] = None
    mfa_enabled: bool = False
    
    # Storage
    storage_quota_bytes: int = 109_951_162_777_600 # 100TB (Unlimited)
    storage_used_bytes: int = 0
    
    # Status
    is_active: bool = True
    is_banned: bool = False
    ban_reason: Optional[str] = None
    
    # Activity
    last_login_at: Optional[datetime] = None
    
    class Settings:
        name = "users"
        indexes = [
            IndexModel([("email", 1)], unique=True),
            "created_at"
        ]
        
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
    
    @property
    def is_moderator(self) -> bool:
        return self.role in ("admin", "moderator")
    
    @property
    def can_auto_approve(self) -> bool:
        """Check if user's uploads should be auto-approved."""
        return self.is_admin or self.is_moderator or self.is_trusted
    
    @property
    def storage_remaining_bytes(self) -> int:
        return max(0, self.storage_quota_bytes - self.storage_used_bytes)
    
    @property
    def storage_usage_percent(self) -> float:
        if self.storage_quota_bytes == 0:
            return 0.0
        return round((self.storage_used_bytes / self.storage_quota_bytes) * 100, 2)


class Session(Document, TimestampMixin):
    """User session document."""
    
    id: UUID = Field(default_factory=uuid4)
    user: Link[User]
    refresh_token_hash: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime
    is_revoked: bool = False
    
    class Settings:
        name = "sessions"


class APIKey(Document, TimestampMixin):
    """API Key document."""
    
    id: UUID = Field(default_factory=uuid4)
    user: Link[User]
    name: str
    key_hash: str = Field(..., description="Hashed API key")
    scopes: List[str] = []
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    class Settings:
        name = "api_keys"
        indexes = [
            IndexModel([("key_hash", 1)], unique=True)
        ]
