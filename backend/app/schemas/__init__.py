"""
Pydantic Schemas for API Request/Response Validation
"""
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    TokenResponse,
    MFASetupResponse,
    MFAVerifyRequest,
)
from app.schemas.resource import (
    ResourceCreate,
    ResourceResponse,
    ResourceUpdate,
    ResourceListResponse,
    ResourceUploadResponse,
)
from app.schemas.rating import (
    RatingCreate,
    RatingResponse,
)
from app.schemas.search import (
    SearchResponse,
)

__all__ = [
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    "TokenResponse",
    "MFASetupResponse",
    "MFAVerifyRequest",
    # Resource
    "ResourceCreate",
    "ResourceResponse",
    "ResourceUpdate",
    "ResourceListResponse",
    "ResourceUploadResponse",
    # Rating
    "RatingCreate",
    "RatingResponse",
    # Search
    "SearchResponse",
]
