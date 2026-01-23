"""
Rating Documents (MongoDB)
"""
from typing import Optional
from uuid import UUID, uuid4
from beanie import Document, Link, Indexed
from pydantic import Field
from pymongo import IndexModel, ASCENDING

from app.models.base import TimestampMixin
from app.models.user import User
from app.models.resource import Resource

class Rating(Document, TimestampMixin):
    """User rating document."""
    
    id: UUID = Field(default_factory=uuid4)
    user: Link[User]
    resource: Link[Resource]
    value: int
    review: Optional[str] = None
    
    class Settings:
        name = "ratings"
        indexes = [
            IndexModel([("user", ASCENDING), ("resource", ASCENDING)]), # Removed unique validation
            "resource",
            "value"
        ]

    @property
    def user_id(self) -> UUID:
        return self.user.ref.id if hasattr(self.user, "ref") else self.user.id

    @property
    def resource_id(self) -> UUID:
        return self.resource.ref.id if hasattr(self.resource, "ref") else self.resource.id

    @property
    def user_name(self) -> Optional[str]:
        if self.user and hasattr(self.user, "display_name"):
            return self.user.display_name
        return None
