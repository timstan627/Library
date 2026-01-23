"""
Download Documents (MongoDB)
"""
from typing import Optional
from uuid import UUID, uuid4
from beanie import Document, Link
from pydantic import Field

from app.models.base import TimestampMixin
from app.models.user import User
from app.models.resource import Resource

class Download(Document, TimestampMixin):
    """Download log document."""
    
    id: UUID = Field(default_factory=uuid4)
    user: Optional[Link[User]] = None
    resource: Link[Resource]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    class Settings:
        name = "downloads"
        indexes = [
            "created_at",
            "resource"
        ]
