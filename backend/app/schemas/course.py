"""
Pydantic schemas for Course API
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CourseBase(BaseModel):
    """Base schema for course."""
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=1000)
    semester: Optional[int] = Field(None, ge=1, le=8)
    credits: Optional[int] = Field(None, ge=1, le=10)


class CourseCreate(CourseBase):
    """Schema for creating a course."""
    department_id: str = Field(..., description="Department ID this course belongs to")
    is_active: bool = True


class CourseUpdate(BaseModel):
    """Schema for updating a course."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=1000)
    department_id: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=8)
    credits: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None


class CourseResponse(CourseBase):
    """Schema for course response."""
    id: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None  # Populated from join
    is_active: bool
    resource_count: int = 0  # Batched count of resources bound to this course
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    """Schema for paginated course list."""
    results: list[CourseResponse]
    total: int
    page: int
    page_size: int
    pages: int
