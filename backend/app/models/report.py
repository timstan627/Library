"""
Report Documents (MongoDB)
"""
from typing import Optional
from uuid import UUID, uuid4
from beanie import Document, Link
from pydantic import Field

from app.models.base import TimestampMixin
from app.models.user import User
from app.models.resource import Resource

class Report(Document, TimestampMixin):
    """Content report document."""
    
    id: UUID = Field(default_factory=uuid4)
    reporter: Link[User]
    resource: Link[Resource]
    reason: str
    details: Optional[str] = None
    status: str = "pending" # pending, resolved, dismissed
    resolved_by: Optional[Link[User]] = None
    resolution_note: Optional[str] = None
    
    class Settings:
        name = "reports"
        indexes = [
            "status",
            "created_at"
        ]
    
    @property
    def reporter_id(self) -> UUID:
        return self.reporter.ref.id if hasattr(self.reporter, "ref") else self.reporter.id
    
    @property
    def resource_id(self) -> UUID:
        return self.resource.ref.id if hasattr(self.resource, "ref") else self.resource.id
