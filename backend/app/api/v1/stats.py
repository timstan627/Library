"""
Public API — website-wide live counters (cached 60s via the StatsEngine).

Lives in the versioned router (not on the app object) so the /api/v1 prefix
has a single source of truth.
"""
from fastapi import APIRouter

from app.schemas.stats import PublicStatsResponse

router = APIRouter()


@router.get("/stats", response_model=PublicStatsResponse, tags=["Public"])
async def get_public_stats():
    """Homepage live counts (cached 60s; falls back to a live query)."""
    from app.services.cache import cache_service
    from app.services.stats import fetch_public_stats

    data = await cache_service.get_stats("public_stats")
    if data:
        return data
    return await fetch_public_stats()
