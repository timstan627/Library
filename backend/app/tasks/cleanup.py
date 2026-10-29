"""
Cleanup Tasks (SQLAlchemy)

Runs periodically from the app lifespan: expires sessions and purges
soft-deleted resources past their retention window.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete as sql_delete, or_, and_

from app.core.database import AsyncSessionLocal
from app.models.user import Session
from app.models.resource import Resource
from app.models.rating import Rating
from app.models.download import Download
from app.models.report import Report
from app.models.collection import CollectionItem

logger = logging.getLogger(__name__)

CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60  # daily
SOFT_DELETE_RETENTION_DAYS = 30
REVOKED_SESSION_RETENTION_DAYS = 7

_cleanup_task: asyncio.Task | None = None


async def cleanup_expired_sessions():
    """Remove expired and revoked sessions."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                sql_delete(Session).where(Session.expires_at < datetime.now(timezone.utc))
            )
            expired_count = result.rowcount

            week_ago = datetime.now(timezone.utc) - timedelta(days=REVOKED_SESSION_RETENTION_DAYS)
            result = await db.execute(
                sql_delete(Session).where(Session.is_revoked == True, Session.created_at < week_ago)  # noqa: E712
            )
            revoked_count = result.rowcount

            await db.commit()
        if expired_count or revoked_count:
            logger.info(f"Session cleanup: removed {expired_count} expired, {revoked_count} old revoked")
    except Exception:
        logger.exception("Session cleanup failed")


async def cleanup_soft_deleted_resources():
    """Permanently delete resources soft-deleted more than 30 days ago.

    Child rows (ratings, downloads, reports, collection items) are removed
    first: the child FKs have no ON DELETE CASCADE, so a bare parent DELETE
    would fail with an IntegrityError and the purge would silently no-op.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=SOFT_DELETE_RETENTION_DAYS)
        async with AsyncSessionLocal() as db:
            # Rows past retention: explicit deleted_at, or legacy rows with
            # no deleted_at stamp (fall back to updated_at).
            stale = select(Resource.id).where(
                Resource.is_deleted == True,  # noqa: E712
                or_(
                    Resource.deleted_at < cutoff,
                    and_(Resource.deleted_at.is_(None), Resource.updated_at < cutoff),
                ),
            )
            stale_ids = (await db.execute(stale)).scalars().all()
            if not stale_ids:
                return

            for model in (Rating, Download, Report, CollectionItem):
                result = await db.execute(
                    sql_delete(model).where(model.resource_id.in_(stale_ids))
                )
                removed_children = result.rowcount
                if removed_children:
                    logger.info(
                        f"Purged {removed_children} {model.__tablename__} rows for expired resources"
                    )

            result = await db.execute(sql_delete(Resource).where(Resource.id.in_(stale_ids)))
            await db.commit()
            logger.info(f"Permanently deleted {result.rowcount} expired soft-deleted resources")
    except Exception:
        logger.exception("Soft-deleted resource cleanup failed")


async def _cleanup_loop():
    """Daily maintenance loop: sessions + soft-delete purge."""
    logger.info("🧹 Periodic cleanup task started (daily)")
    while True:
        try:
            await cleanup_expired_sessions()
            await cleanup_soft_deleted_resources()
        except asyncio.CancelledError:
            logger.info("🧹 Cleanup task cancelled")
            raise
        except Exception:
            logger.exception("Cleanup loop iteration failed")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


def start_cleanup_scheduler() -> asyncio.Task:
    """Start the periodic cleanup loop; returns the task handle."""
    global _cleanup_task
    _cleanup_task = asyncio.create_task(_cleanup_loop())
    return _cleanup_task


async def stop_cleanup_scheduler():
    """Cancel the cleanup loop and wait for it to finish."""
    global _cleanup_task
    if _cleanup_task is not None:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
        _cleanup_task = None
