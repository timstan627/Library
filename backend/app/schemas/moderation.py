"""
Pydantic schemas for Moderation/Approval workflow
"""
from datetime import datetime
from typing import List, Optional
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


class UserPromotionListResponse(BaseModel):
    """Paginated envelope for the trusted-contributor listing."""
    results: List[UserPromotionResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Admin listing envelopes (typed responses for the hand-built admin dicts)
# ---------------------------------------------------------------------------

class AdminUserListItem(BaseModel):
    """One row of the admin users listing."""
    id: str
    email: str
    display_name: Optional[str] = None
    role: str
    is_trusted: bool
    is_banned: bool
    moderation_exempt: bool = False
    upload_count: int = 0
    approved_count: int = 0
    created_at: Optional[datetime] = None


class AdminUserListResponse(BaseModel):
    """Paginated admin users listing envelope."""
    results: List[AdminUserListItem]
    total: int
    page: int
    page_size: int
    pages: int


class PendingResourceItem(BaseModel):
    """One row of the moderation pending queue."""
    id: str
    title: str
    slug: str
    course_code: str
    department_name: Optional[str] = None
    uploader_name: Optional[str] = None
    file_size: int
    created_at: Optional[datetime] = None


class PendingResourceListResponse(BaseModel):
    """Paginated moderation pending-queue envelope."""
    results: List[PendingResourceItem]
    total: int
    page: int
    page_size: int
    pages: int


class ModerationHistoryResponse(BaseModel):
    """Paginated moderation history envelope."""
    results: List[ResourceModerationStatus]
    total: int
    page: int
    page_size: int
    pages: int


class AdminAuditLogItem(BaseModel):
    """One row of the admin audit trail."""
    id: str
    action: str
    actor_name: Optional[str] = None
    actor_id: Optional[str] = None
    target_type: str
    target_id: str
    details: Optional[dict] = None
    timestamp: Optional[datetime] = None


class AdminAuditLogListResponse(BaseModel):
    """Paginated admin audit-trail envelope."""
    results: List[AdminAuditLogItem]
    total: int
    page: int
    page_size: int
    pages: int


class AdminResourceItem(BaseModel):
    """One row of the admin resources listing."""
    id: str
    title: str
    slug: str
    course_code: str
    file_name: str
    file_size: int
    downloads: int
    views: int
    visibility: str
    moderation_status: str
    created_at: Optional[datetime] = None


class AdminResourceListResponse(BaseModel):
    """Paginated admin resources listing envelope."""
    results: List[AdminResourceItem]
    total: int
    page: int
    page_size: int
    pages: int


class AdminReportItem(BaseModel):
    """One row of the admin reports listing."""
    id: str
    status: str
    reason: str
    details: Optional[str] = None
    resolution_note: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_by_name: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    resource_id: str
    resource_title: Optional[str] = None
    resource_slug: Optional[str] = None


class AdminReportListResponse(BaseModel):
    """Paginated admin reports listing envelope."""
    results: List[AdminReportItem]
    total: int
    page: int
    pages: int
