"""
Course Model (SQLAlchemy)
"""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional
from sqlalchemy import String, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Course(Base, TimestampMixin):
    """Academic course model linked to departments."""
    __tablename__ = "courses"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    department_id: Mapped[str] = mapped_column(String, ForeignKey("departments.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    semester: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Relationships
    department = relationship("Department", back_populates="courses", lazy="selectin")
