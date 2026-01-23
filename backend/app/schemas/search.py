"""
Search Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.resource import ResourceResponse


class SearchQuery(BaseModel):
    """Schema for search request."""
    q: Optional[str] = Field(None, max_length=200)
    course_code: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[str] = None
    branch: Optional[str] = None
    tags: Optional[List[str]] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    file_type: Optional[str] = None
    sort_by: str = Field(default="relevance", pattern="^(relevance|downloads|rating|recent)$")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class SearchResponse(BaseModel):
    """Schema for search response."""
    results: List[ResourceResponse]
    total: int
    page: int
    pages: int
    took_ms: int
    query: Optional[str] = None


class FilterOptions(BaseModel):
    """Schema for available filter options."""
    courses: List[str]
    departments: List[str]
    semesters: List[str]
    branches: List[str]
    tags: List[str]
    file_types: List[str]
