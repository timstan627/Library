"""
Audit Log Model (SQLAlchemy)
"""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    """Audit trail for administrative actions."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_target", "target_type", "target_id"),
    )
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    actor = relationship("User", lazy="selectin")
    
    @property
    def details(self) -> dict:
        import json
        if self.details_json:
            try:
                return json.loads(self.details_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @details.setter
    def details(self, value: dict):
        import json
        self.details_json = json.dumps(value) if value else None
