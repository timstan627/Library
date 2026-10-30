"""
Pydantic schemas for Department API
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    """Base schema for department."""
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=1000)
    display_order: int = Field(default=0, ge=0)


class DepartmentCreate(DepartmentBase):
    """Schema for creating a department."""
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    """Schema for updating a department."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=0)


class DepartmentResponse(DepartmentBase):
    """Schema for department response."""
    id: str
    is_active: bool
    course_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DepartmentListResponse(BaseModel):
    """Schema for paginated department list."""
    results: list[DepartmentResponse]
    total: int
    page: int
    page_size: int
    pages: int
