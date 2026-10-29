"""
Collection model — Users organize their uploads into collections (personal library).
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Collection(Base):
    """A user-created collection for organizing resources."""
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emoji: Mapped[str] = mapped_column(String(10), default="📁")
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")  # Hex color
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    # user: never read implicitly (user_id is used); raise forces explicit
    # loading if that ever changes.
    # items: MUST stay loadable — delete_collection relies on the flush-time
    # cascade loading items, and item_count/total_size read them.
    user = relationship("User", back_populates="collections", lazy="raise")
    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan", lazy="selectin")

    @property
    def item_count(self) -> int:
        return len(self.items) if self.items else 0

    @property
    def total_size(self) -> int:
        """Total file size of all resources in this collection (bytes)."""
        if not self.items:
            return 0
        return sum(item.resource.file_size for item in self.items if item.resource)


class CollectionItem(Base):
    """A resource within a collection."""
    __tablename__ = "collection_items"
    __table_args__ = (
        UniqueConstraint("collection_id", "resource_id", name="uq_collection_resource"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    collection_id: Mapped[str] = mapped_column(String, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String, ForeignKey("resources.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    collection = relationship("Collection", back_populates="items")
    # Only accessed after an explicit selectinload (library detail) or via
    # total_size in handlers that eager-load it; raise keeps it that way.
    resource = relationship("Resource", lazy="raise")
