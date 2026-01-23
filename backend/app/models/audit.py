"""
Audit Log Documents (MongoDB)
"""
from typing import Optional, Any, Dict
from uuid import UUID, uuid4
from beanie import Document, Link
from pydantic import Field

from app.models.base import TimestampMixin
from app.models.user import User

class AuditLog(Document, TimestampMixin):
    """System audit log."""
    
    id: UUID = Field(default_factory=uuid4)
    user: Optional[Link[User]] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    
    class Settings:
        name = "audit_logs"
        indexes = [
            "action",
            "created_at",
            "user"
        ]
