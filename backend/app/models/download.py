"""
Download Model (SQLAlchemy)
"""
from uuid import uuid4
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Download(Base, TimestampMixin):
    """Download log record."""
    __tablename__ = "downloads"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True, index=True)
    resource_id: Mapped[str] = mapped_column(String, ForeignKey("resources.id"), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", lazy="selectin")
    resource = relationship("Resource", lazy="selectin")
