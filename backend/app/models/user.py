"""
User Models (SQLAlchemy) — User, Session, APIKey
"""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, List
from sqlalchemy import String, Boolean, Integer, BigInteger, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    """User account."""
    __tablename__ = "users"
    
    # Identity
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Role & Permissions
    role: Mapped[str] = mapped_column(String(20), default="student")  # student, moderator, admin
    
    # Trusted Contributor
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    promoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    promoted_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # MFA
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Storage
    storage_quota_bytes: Mapped[int] = mapped_column(BigInteger, default=109_951_162_777_600)  # 100TB
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Activity
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships — lazy="raise": these must never be implicitly loaded
    # (an auth request eager-loading a user's entire resource list and every
    # session was a per-request tax). Any future use needs an explicit
    # selectinload/join at the query site.
    sessions = relationship("Session", back_populates="user", lazy="raise")
    resources = relationship("Resource", back_populates="uploader", foreign_keys="Resource.uploader_id", lazy="raise")
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan", lazy="raise")
    
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
    
    @property
    def is_moderator(self) -> bool:
        return self.role in ("admin", "moderator")
    
    @property
    def can_auto_approve(self) -> bool:
        return self.is_admin or self.is_moderator or self.is_trusted
    
    @property
    def storage_remaining_bytes(self) -> int:
        return max(0, self.storage_quota_bytes - self.storage_used_bytes)
    
    @property
    def storage_usage_percent(self) -> float:
        if self.storage_quota_bytes == 0:
            return 0.0
        return round((self.storage_used_bytes / self.storage_quota_bytes) * 100, 2)


class Session(Base, TimestampMixin):
    """User session."""
    __tablename__ = "sessions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions", lazy="raise")


class APIKey(Base, TimestampMixin):
    """API Key."""
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list stored as text
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
