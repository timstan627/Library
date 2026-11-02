"""
App Setting Model (SQLAlchemy) — runtime-editable site settings.
"""
from typing import Optional

from sqlalchemy import String, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class AppSetting(Base, TimestampMixin):
    """Runtime site setting.

    Boolean and simple string values are stored as raw strings in `value`
    ("true"/"false"). Read through `app.services.settings` helpers, which
    also cache reads in memory — this backend is single-process by design,
    so the cache is authoritative between writes.
    """
    __tablename__ = "app_settings"
    __table_args__ = (
        Index("ix_app_settings_key", "key", unique=True),
    )

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Known setting keys (write-time validation lives in services.settings)
    MODERATION_AUTO_APPROVE = "moderation_auto_approve"
    KNOWN_BOOL_KEYS = {MODERATION_AUTO_APPROVE}
