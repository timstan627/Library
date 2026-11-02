"""
Pydantic schemas for runtime site settings.
"""
from pydantic import BaseModel


class ModerationAutoApproveResponse(BaseModel):
    """Current global moderation policy."""
    auto_approve_moderation: bool
