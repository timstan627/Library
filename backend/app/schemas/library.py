"""
Library Schemas - Personal collections
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    """Schema for creating a collection."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    emoji: str = Field(default="📁", max_length=10)
    color: str = Field(default="#6366f1", max_length=7)


class CollectionUpdate(BaseModel):
    """Schema for updating a collection."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    emoji: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, max_length=7)


class CollectionItemAdd(BaseModel):
    """Schema for adding resources to a collection."""
    resource_ids: List[str] = Field(..., min_length=1, max_length=100)


class CollectionReorder(BaseModel):
    """List of resource IDs in the new order."""
    resource_ids: List[str] = Field(..., max_length=500)


class CollectionItemResponse(BaseModel):
    """A single item inside a collection (resource details flattened)."""
    id: str
    resource_id: str
    sort_order: int
    added_at: datetime
    title: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_extension: Optional[str] = None
    mime_type: Optional[str] = None
    visibility: Optional[str] = None
    slug: Optional[str] = None

    class Config:
        from_attributes = True


class CollectionResponse(BaseModel):
    """Schema for collection responses."""
    id: str
    name: str
    description: Optional[str] = None
    emoji: str
    color: str
    sort_order: int
    item_count: int = 0
    total_size: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionDetailResponse(CollectionResponse):
    """Collection with its ordered items."""
    items: List[CollectionItemResponse] = []
