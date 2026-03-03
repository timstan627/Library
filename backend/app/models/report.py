"""
Report Model (SQLAlchemy)
"""
from uuid import uuid4
from typing import Optional
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Report(Base, TimestampMixin):
    """Content report record."""
    __tablename__ = "reports"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    reporter_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String, ForeignKey("resources.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, resolved, dismissed
    resolved_by_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id], lazy="selectin")
    resource = relationship("Resource", lazy="selectin")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id], lazy="selectin")
