"""
Public website statistics schemas.
"""
from pydantic import BaseModel


class PublicStatsResponse(BaseModel):
    """Homepage live counts (public, cached 60s)."""
    resources: int
    users: int
    downloads: int
    courses: int
