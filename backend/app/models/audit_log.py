"""
Audit Log Model - Track admin actions for compliance
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from beanie import Document, Link
from pydantic import Field
from pymongo import IndexModel, DESCENDING

from app.models.user import User


class AuditLog(Document):
    """Audit trail for administrative actions."""
    
    action: str = Field(..., description="Action performed (e.g., 'promote_user', 'approve_resource')")
    actor: Link[User] = Field(..., description="User who performed the action")
    target_type: str = Field(..., description="Type of target entity (e.g., 'user', 'resource')")
    target_id: str = Field(..., description="ID of the target entity")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional action details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Optional fields for context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    class Settings:
        name = "audit_logs"
        indexes = [
            IndexModel([("timestamp", DESCENDING)]),
            "actor",
            "action",
            IndexModel([("target_type", 1), ("target_id", 1)]),
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "promote_user",
                "actor": "admin_user_id",
                "target_type": "user",
                "target_id": "user_id",
                "details": {
                    "old_status": False,
                    "new_status": True,
                    "reason": "Consistent high-quality uploads"
                }
            }
        }
