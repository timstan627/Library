"""
Rating Schemas
"""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RatingCreate(BaseModel):
    """Schema for creating a rating."""
    value: int = Field(0, ge=0, le=5)
    review: Optional[str] = Field(None, max_length=1000)


class RatingResponse(BaseModel):
    """Schema for rating response."""
    id: uuid.UUID
    user_id: uuid.UUID
    resource_id: uuid.UUID
    value: int
    review: Optional[str]
    created_at: datetime
    user_name: Optional[str] = None
    
    class Config:
        from_attributes = True
