"""
Pydantic schemas for admin-managed catalog shelves.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CatalogShelfBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    source_type: Literal["recent", "most_read", "most_downloaded", "top_rated", "tag", "branch", "subject"]
    # Required for tag/branch/subject, ignored (must be None) for built-ins.
    source_value: Optional[str] = None
    item_limit: int = Field(8, ge=1, le=48)
    position: int = Field(0, ge=0)
    is_active: bool = True


class CatalogShelfCreate(CatalogShelfBase):
    pass


class CatalogShelfUpdate(CatalogShelfBase):
    pass


class MoveDirectionRequest(BaseModel):
    direction: Literal["up", "down"]


class CatalogShelfResponse(CatalogShelfBase):
    id: str

    class Config:
        from_attributes = True


class ShelfItemPayload(BaseModel):
    """What the public payload exposes to the frontend (no admin internals)."""
    id: str
    title: str
    source_type: str
    source_value: Optional[str] = None
    item_limit: int
