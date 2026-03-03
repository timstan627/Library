from fastapi import APIRouter, Depends
from app.api.v1.deps import require_admin
from app.models.user import User
from app.services.cache import cache_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("")
async def get_dashboard_stats(
    current_user: User = Depends(require_admin),
):
    """Get admin dashboard statistics (served from StatsEngine cache)."""
    data = await cache_service.get_stats("admin_dashboard_lite")
    if data:
        return data
    
    # Fallback: should never reach here since main.py registers the query
    return {
        "total_users": 0,
        "total_resources": 0,
        "total_downloads": 0,
        "total_storage_bytes": 0,
        "pending_reports": 0,
        "pending_moderation": 0,
        "new_users_7d": 0,
        "new_resources_7d": 0,
    }


@router.get("/cache")
async def get_cache_stats(
    current_user: User = Depends(require_admin),
):
    """Get cache performance statistics (file cache + stats engine)."""
    return cache_service.cache_stats
