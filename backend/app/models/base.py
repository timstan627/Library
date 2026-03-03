"""
Base Model Mixins (SQLAlchemy)
"""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )
