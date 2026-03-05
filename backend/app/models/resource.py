"""
Resource Model (SQLAlchemy)
"""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, List
from sqlalchemy import String, Boolean, Integer, BigInteger, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Resource(Base, TimestampMixin):
    """Resource (uploaded file) record."""
    __tablename__ = "resources"
    __table_args__ = (
        Index("ix_resources_course_code", "course_code"),
        Index("ix_resources_file_hash", "file_hash"),
        Index("ix_resources_created_at", "created_at"),
        Index("ix_resources_downloads", "downloads"),
    )
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    
    # Metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(600), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Academic
    department_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("departments.id"), nullable=True)
    course_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("courses.id"), nullable=True)
    course_code: Mapped[str] = mapped_column(String(50), nullable=False)
    semester: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Tags (stored as comma-separated string)
    tags_str: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # File Info
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Telegram Storage
    telegram_file_id: Mapped[str] = mapped_column(String(500), nullable=False)
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    backup_telegram_file_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    backup_telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Thumbnail
    thumbnail_file_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Owner
    uploader_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True, index=True)
    
    # Access
    visibility: Mapped[str] = mapped_column(String(20), default="public")  # public, unlisted, private, password
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Stats
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    rating_sum: Mapped[int] = mapped_column(Integer, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Moderation
    moderation_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    moderated_by_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    uploader = relationship("User", back_populates="resources", foreign_keys=[uploader_id], lazy="selectin")
    department = relationship("Department", lazy="selectin")
    course = relationship("Course", lazy="selectin")
    moderated_by = relationship("User", foreign_keys=[moderated_by_id], lazy="selectin")
    deleted_by = relationship("User", foreign_keys=[deleted_by_id], lazy="selectin")
    
    @property
    def tags(self) -> List[str]:
        if not self.tags_str:
            return []
        return [t.strip() for t in self.tags_str.split(",") if t.strip()]
    
    @tags.setter
    def tags(self, value: List[str]):
        self.tags_str = ",".join(value) if value else None
    
    @property
    def average_rating(self) -> Optional[float]:
        if self.rating_count == 0:
            return None
        return round(self.rating_sum / self.rating_count, 1)
    
    @property
    def file_size_mb(self) -> float:
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_public(self) -> bool:
        return self.visibility == "public" and not self.is_deleted
    
    @property
    def is_password_protected(self) -> bool:
        return self.visibility == "password" and bool(self.password_hash)
    
    @property
    def uploader_name(self) -> Optional[str]:
        if self.uploader and hasattr(self.uploader, "display_name"):
            return self.uploader.display_name
        return None
