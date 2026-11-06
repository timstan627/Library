"""
Resource Schemas - File upload and metadata
"""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


def normalize_course_code(value: str) -> str:
    """Canonical course-code normalization shared by every write path.

    Empty means "no course code". Any provided value must look like
    CS101, ECE2001, MATH1234. Raises ValueError on invalid input so the
    Pydantic validators and the multipart upload endpoint enforce the
    exact same rules (create/update can no longer drift).
    """
    v = value.strip()
    if not v:
        return ""
    if not re.match(r"^[A-Za-z]{2,6}\d{2,4}[A-Za-z]?$", v):
        raise ValueError("Invalid course code format (e.g., CS101, ECE2001)")
    return v.upper()


class ResourceCreate(BaseModel):
    """Schema for creating a resource."""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    course_code: str = Field("", max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    semester: Optional[str] = Field(None, max_length=20)
    branch: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = Field(default_factory=list, max_length=10)
    visibility: str = Field(default="public", pattern="^(public|unlisted|private)$")
    password: Optional[str] = Field(None, min_length=4, max_length=50)
    
    @field_validator("course_code")
    @classmethod
    def validate_course_code(cls, v: str) -> str:
        return normalize_course_code(v)
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        if v:
            # Clean and deduplicate tags
            tags = list(set(tag.lower().strip() for tag in v if tag.strip()))
            return tags[:10]  # Max 10 tags
        return []


class ResourceUpdate(BaseModel):
    """Schema for updating a resource."""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    course_code: Optional[str] = Field(None, max_length=20)
    # Department by name or code; resolved to department_id server-side.
    department: Optional[str] = Field(None, max_length=100)
    semester: Optional[str] = Field(None, max_length=20)
    branch: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = Field(None, max_length=10)
    visibility: Optional[str] = Field(None, pattern="^(public|unlisted|private|password)$")
    # Only valid when visibility is "password"; switching visibility away
    # from "password" clears the stored hash.
    password: Optional[str] = Field(None, min_length=4, max_length=50)

    @field_validator("course_code")
    @classmethod
    def validate_course_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Explicit empty string clears the course code; Omitted field (None)
        # leaves it unchanged. Any provided value must still look like a code.
        return normalize_course_code(v)


class ResourceResponse(BaseModel):
    """Schema for resource response."""
    id: uuid.UUID
    title: str
    slug: str
    description: Optional[str]
    course_code: str

    # Academic (department_name comes from a model property; `department` on
    # the ORM is a relationship object and must never be serialized directly)
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    course_id: Optional[str] = None
    semester: Optional[str] = None
    branch: Optional[str] = None
    tags: Optional[List[str]] = []

    # File info
    file_name: str
    file_size: int
    file_extension: str
    mime_type: str

    # Stats
    downloads: int
    views: int
    average_rating: Optional[float]
    rating_count: int
    
    # Access
    visibility: str
    is_password_protected: bool
    
    # Uploader info
    uploader_id: Optional[uuid.UUID] = None
    uploader_name: Optional[str] = None
    
    # Moderation
    moderation_status: str
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ResourceListResponse(BaseModel):
    """Schema for paginated resource list."""
    results: List[ResourceResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


class ResourceUploadResponse(BaseModel):
    """Schema for upload response."""
    id: uuid.UUID
    slug: str
    title: str
    file_name: str
    file_size: int
    moderation_status: str
    message: str = "Resource uploaded successfully"

    class Config:
        from_attributes = True


class ResourceDownloadResponse(BaseModel):
    """Schema for download URL response."""
    download_url: str
    expires_in: int
    file_name: str
    file_size: int


class ResourceSummary(BaseModel):
    """Safe public summary for cross-endpoint listings (popular/recent).

    Explicit allowlist: never serialize ORM rows directly — the ORM graph
    carries password_hash, telegram storage ids, file_hash, and the uploader
    relationship (email, mfa_secret).
    """
    id: str
    title: str
    slug: str
    course_code: str
    file_name: str
    file_size: int
    file_extension: str
    mime_type: str
    downloads: int = 0
    views: int = 0
    average_rating: Optional[float] = None
    rating_count: int = 0
    visibility: str
    created_at: datetime

    class Config:
        from_attributes = True
