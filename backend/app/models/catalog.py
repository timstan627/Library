"""
Catalog Shelf Model (SQLAlchemy) — admin-configured discovery shelf rows.
"""
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class CatalogShelf(Base, TimestampMixin):
    """A named discovery shelf row shown on the homepage and /browse.

    `source_type` selects where the items come from:
      - recent           → newest uploads (source_value unused)
      - most_read        → sort by views (source_value unused)
      - most_downloaded   → sort by downloads (source_value unused)
      - top_rated        → Bayesian top-rated (source_value unused)
      - tag              → all approved items tagged `source_value`
      - branch           → all approved items in branch `source_value`
      - subject          → all approved items in department `source_value`

    When any shelf row exists with is_active=True, the frontend renders
    shelves from this table only; an empty/failed read falls back to the
    built-in default shelf set.
    """
    __tablename__ = "catalog_shelves"
    __table_args__ = (
        Index("ix_catalog_shelves_position", "position"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    item_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
