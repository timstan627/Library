"""
Pydantic schemas for Moderation/Approval workflow
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ModerationAction(BaseModel):
    """Schema for approving/rejecting a resource."""
    action: str = Field(..., description="approve or reject")
    rejection_reason: Optional[str] = Field(None, max_length=500)


class ResourceModerationStatus(BaseModel):
    """Schema for resource moderation details."""
    resource_id: str
    title: str
    status: str
    uploader_name: Optional[str]
    uploader_email: Optional[str]
    uploaded_at: datetime
    moderated_by: Optional[str] = None
    moderated_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserPromotionRequest(BaseModel):
    """Schema for promoting a user to trusted status."""
    is_trusted: bool
    reason: Optional[str] = Field(None, max_length=500)


class ModerationExemptRequest(BaseModel):
    """Schema for toggling a user's moderation exemption."""
    moderation_exempt: bool


class UserPromotionResponse(BaseModel):
    """Schema for user promotion response."""
    user_id: str
    email: str
    is_trusted: bool
    promoted_at: Optional[datetime]
    promoted_by: Optional[str]
    # Additive display fields consumed by the admin users page. Defaults keep
    # the shape valid wherever a display lookup is not performed.
    display_name: Optional[str] = None
    role: Optional[str] = None  # 'admin' | 'moderator' | 'user' (listing convention)
    # Per-user upload moderation bypass (admin toggle); admins/moderators
    # always bypass regardless of this flag.
    moderation_exempt: bool = False
    upload_count: int = 0
    approved_count: int = 0

    class Config:
        from_attributes = True
