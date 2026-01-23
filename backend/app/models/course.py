"""
Course Model - Academic course configuration
"""
from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Link
from pydantic import Field
from pymongo import IndexModel, ASCENDING

from app.models.department import Department


class Course(Document):
    """Academic course model linked to departments."""
    
    department: Link[Department] = Field(..., description="Department this course belongs to")
    name: str = Field(..., min_length=1, max_length=200, description="Course name")
    code: str = Field(..., min_length=1, max_length=20, description="Course code")
    description: Optional[str] = Field(None, max_length=1000)
    semester: Optional[int] = Field(None, ge=1, le=8, description="Recommended semester")
    credits: Optional[int] = Field(None, ge=1, le=10, description="Course credits")
    is_active: bool = Field(default=True, description="Whether course is visible in dropdowns")
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "courses"
        indexes = [
            IndexModel([("code", ASCENDING)], unique=True),
            "department",
            "is_active",
            IndexModel([("department", ASCENDING), ("semester", ASCENDING)]),
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "department": "department_id",
                "name": "Data Structures and Algorithms",
                "code": "CS201",
                "description": "Introduction to fundamental data structures and algorithms",
                "semester": 3,
                "credits": 4,
                "is_active": True
            }
        }
