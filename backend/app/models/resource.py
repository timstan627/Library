"""
Resource Documents (MongoDB)
"""
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from beanie import Document, Link
from pydantic import Field
from pymongo import IndexModel

from app.models.base import TimestampMixin
from app.models.user import User
from app.models.department import Department
from app.models.course import Course

class Resource(Document, TimestampMixin):
    """Resource (file) document."""
    
    id: UUID = Field(default_factory=uuid4)
    
    # Metadata
    title: str
    slug: str = Field(..., description="URL-friendly slug")
    description: Optional[str] = None
    
    # Academic - Enhanced with links to Department and Course  
    # Made optional to handle legacy data where these were strings
    department_id: Optional[Link[Department]] = Field(None, description="Department link")
    course_id: Optional[Link[Course]] = Field(None, description="Course link")
    
    # Legacy fields (keep for backward compatibility with old data)
    course_code: str
    semester: Optional[str] = None
    branch: Optional[str] = None
    
    # Tags
    tags: List[str] = []
    
    # File Info
    file_name: str
    file_size: int
    mime_type: str
    file_hash: str
    file_extension: str
    
    # Telegram Storage
    telegram_file_id: str
    telegram_message_id: int
    telegram_channel_id: int
    backup_telegram_file_id: Optional[str] = None
    backup_telegram_message_id: Optional[int] = None
    
    # Thumbnail
    thumbnail_file_id: Optional[str] = None
    
    # Owner
    uploader: Optional[Link[User]] = None
    
    # Access
    visibility: str = "public" # public, unlisted, private
    password_hash: Optional[str] = None
    
    # Stats
    downloads: int = 0
    views: int = 0
    rating_sum: int = 0
    rating_count: int = 0
    
    # Moderation - Enhanced workflow
    moderation_status: str = Field(default="pending", description="pending, approved, rejected")
    moderated_by: Optional[Link[User]] = Field(None, description="Admin who moderated")
    moderated_at: Optional[datetime] = Field(None, description="When moderation occurred")
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection")
    is_flagged: bool = False
    
    # Soft delete
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[Link[User]] = None
    
    class Settings:
        name = "resources"
        indexes = [
            IndexModel([("slug", 1)], unique=True),
            IndexModel([("file_hash", 1)]), # unique=False to allow different users to upload same file
            IndexModel([("course_code", 1)]),
            IndexModel([("department", 1)]),
            IndexModel([("title", "text"), ("description", "text")]),
            "created_at",
            "downloads",
        ]

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
        return bool(self.password_hash)

    @property
    def uploader_id(self) -> Optional[UUID]:
        if self.uploader:
            # Check if it's a DBRef (Link) or User object
            if hasattr(self.uploader, "ref"):
                return self.uploader.ref.id
            if hasattr(self.uploader, "id"):
                return self.uploader.id
        return None

    @property
    def uploader_name(self) -> Optional[str]:
        if self.uploader and hasattr(self.uploader, "display_name"):
            return self.uploader.display_name
        return None
