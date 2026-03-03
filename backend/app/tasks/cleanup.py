"""
Cleanup Tasks (SQLAlchemy)
"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete as sql_delete

from app.core.database import AsyncSessionLocal
from app.models.user import Session
from app.models.resource import Resource

logger = logging.getLogger(__name__)


async def cleanup_expired_sessions():
    """Remove expired and revoked sessions."""
    logger.info("Starting session cleanup...")
    try:
        async with AsyncSessionLocal() as db:
            # Delete expired sessions
            result = await db.execute(
                sql_delete(Session).where(Session.expires_at < datetime.now(timezone.utc))
            )
            expired_count = result.rowcount
            logger.info(f"Deleted {expired_count} expired sessions")
            
            # Delete revoked sessions older than 7 days
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            result = await db.execute(
                sql_delete(Session).where(Session.is_revoked == True, Session.created_at < week_ago)
            )
            revoked_count = result.rowcount
            logger.info(f"Deleted {revoked_count} old revoked sessions")
            
            await db.commit()
        
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")


async def cleanup_soft_deleted_resources():
    """Permanently delete resources soft-deleted more than 30 days ago."""
    logger.info("Starting resource cleanup...")
    try:
        month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                sql_delete(Resource).where(
                    Resource.is_deleted == True,
                    Resource.deleted_at < month_ago,
                )
            )
            count = result.rowcount
            await db.commit()
            
        logger.info(f"Permanently deleted {count} old soft-deleted resources")
        
    except Exception as e:
        logger.error(f"Error during resource cleanup: {e}")
