"""
Search Schemas
"""
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.resource import ResourceResponse, ResourceSummary


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


class ResourceSummaryListResponse(BaseModel):
    """Paginated-safe list of public resource summaries (popular/recent)."""
    results: List[ResourceSummary]
