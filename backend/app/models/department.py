"""
Department Model - Academic department configuration
"""
from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


class Department(Document):
    """Academic department model for categorizing courses and resources."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Department name")
    code: str = Field(..., min_length=1, max_length=20, description="Short department code")
    description: Optional[str] = Field(None, max_length=1000)
    is_active: bool = Field(default=True, description="Whether department is visible in dropdowns")
    display_order: int = Field(default=0, description="Order for displaying in lists")
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "departments"
        indexes = [
            "code",
            "is_active",
            "display_order",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Computer Science",
                "code": "CS",
                "description": "Department of Computer Science and Engineering",
                "is_active": True,
                "display_order": 1
            }
        }
