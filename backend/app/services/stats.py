"""
Stats query functions for the StatsEngine cache.

Each fetcher opens its own session (they run in the background refresh loop,
outside any request scope) and is registered in main.lifespan with a TTL.
Response shapes are API contract — the admin dashboard and the public home
page read them verbatim.
"""
import logging
from datetime import datetime, timezone, timedelta

from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def fetch_public_stats() -> dict:
    """Homepage live counts (public, cached 60s)."""
    from sqlalchemy import select, func
    from app.models.user import User
    from app.models.resource import Resource
    from app.models.download import Download
    from app.models.course import Course

    async with AsyncSessionLocal() as db:
        total_resources = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.is_deleted == False, Resource.visibility == "public")
        )).scalar()
        total_users = (await db.execute(
            select(func.count()).select_from(User).where(User.is_active == True, User.is_banned == False)
        )).scalar()
        total_downloads = (await db.execute(
            select(func.count()).select_from(Download)
        )).scalar()
        total_courses = (await db.execute(
            select(func.count()).select_from(Course).where(Course.is_active == True)
        )).scalar()

    return {
        "resources": total_resources,
        "users": total_users,
        "downloads": total_downloads,
        "courses": total_courses,
    }


async def fetch_admin_dashboard() -> dict:
    """Admin dashboard aggregates (admin-only, cached 30s).

    Note: `total_downloads` is the sum of per-resource counters, not the
    row count of the Download log (deleted resources drop out either way).
    """
    from sqlalchemy import select, func
    from app.models.user import User
    from app.models.resource import Resource
    from app.models.report import Report

    async with AsyncSessionLocal() as db:
        total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
        total_resources = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.is_deleted == False)
        )).scalar()

        total_downloads = (await db.execute(
            select(func.coalesce(func.sum(Resource.downloads), 0)).where(Resource.is_deleted == False)
        )).scalar()
        total_storage_bytes = (await db.execute(
            select(func.coalesce(func.sum(Resource.file_size), 0)).where(Resource.is_deleted == False)
        )).scalar()

        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        new_users_7d = (await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= week_ago)
        )).scalar()
        new_resources_7d = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.created_at >= week_ago, Resource.is_deleted == False)
        )).scalar()

        pending_moderation = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.moderation_status == "pending", Resource.is_deleted == False)
        )).scalar()
        pending_reports = (await db.execute(
            select(func.count()).select_from(Report).where(Report.status == "pending")
        )).scalar()

    return {
        "total_users": total_users,
        "total_resources": total_resources,
        "total_downloads": total_downloads,
        "total_storage_bytes": total_storage_bytes,
        "pending_reports": pending_reports,
        "pending_moderation": pending_moderation,
        "new_users_7d": new_users_7d,
        "new_resources_7d": new_resources_7d,
    }


async def fetch_moderation_stats() -> dict:
    """Moderation queue counters (cached 30s)."""
    from sqlalchemy import select, func
    from app.models.resource import Resource

    async with AsyncSessionLocal() as db:
        pending = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.moderation_status == "pending", Resource.is_deleted == False)
        )).scalar()
        approved = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.moderation_status == "approved", Resource.is_deleted == False)
        )).scalar()
        rejected = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.moderation_status == "rejected", Resource.is_deleted == False)
        )).scalar()

    return {
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "total": pending + approved + rejected,
    }


def register_all(cache_service) -> None:
    """Register every stats key with the cache service (called at startup)."""
    cache_service.register_stats("public_stats", fetch_public_stats, ttl=60)
    cache_service.register_stats("admin_dashboard_lite", fetch_admin_dashboard, ttl=30)
    cache_service.register_stats("moderation_stats", fetch_moderation_stats, ttl=30)
