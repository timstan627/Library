"""
Department Model (SQLAlchemy)
"""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional
from sqlalchemy import String, Boolean, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Department(Base, TimestampMixin):
    """Academic department model for categorizing courses and resources."""
    __tablename__ = "departments"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    courses = relationship("Course", back_populates="department", lazy="selectin")
