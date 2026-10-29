"""
Rating Model (SQLAlchemy)
"""
from uuid import uuid4, UUID
from typing import Optional
from sqlalchemy import String, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Rating(Base, TimestampMixin):
    """User rating/review record."""
    __tablename__ = "ratings"
    __table_args__ = (
        # One rating row per (user, resource): without this, a concurrent
        # double-submit inserts two rows and double-counts the aggregates.
        Index(
            "uq_ratings_user_resource", "user_id", "resource_id", unique=True,
        ),
    )
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String, ForeignKey("resources.id"), nullable=False, index=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", lazy="selectin")  # user_name property (responses)
    resource = relationship("Resource", lazy="raise")  # never read implicitly
    
    @property
    def user_name(self) -> Optional[str]:
        if self.user and hasattr(self.user, "display_name"):
            return self.user.display_name
        return None
