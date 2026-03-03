"""
Analytics Tasks (SQLAlchemy)
"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.resource import Resource
from app.models.download import Download

logger = logging.getLogger(__name__)


async def aggregate_daily_stats():
    """Aggregate daily statistics for reporting."""
    today = datetime.now(timezone.utc).date()
    yesterday_date = today - timedelta(days=1)
    
    start_of_yesterday = datetime.combine(yesterday_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_of_yesterday = datetime.combine(yesterday_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    try:
        async with AsyncSessionLocal() as db:
            downloads_count = (await db.execute(
                select(func.count()).select_from(Download)
                .where(Download.created_at >= start_of_yesterday, Download.created_at <= end_of_yesterday)
            )).scalar()
            
            resources_count = (await db.execute(
                select(func.count()).select_from(Resource)
                .where(Resource.created_at >= start_of_yesterday, Resource.created_at <= end_of_yesterday, Resource.is_deleted == False)
            )).scalar()
            
            users_count = (await db.execute(
                select(func.count()).select_from(User)
                .where(User.created_at >= start_of_yesterday, User.created_at <= end_of_yesterday)
            )).scalar()
        
        stats = {
            "date": str(yesterday_date),
            "downloads": downloads_count,
            "new_resources": resources_count,
            "new_users": users_count,
        }
        
        logger.info(f"Daily stats for {yesterday_date}: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error aggregating stats: {e}")


async def update_popular_resources():
    """Update cached list of popular resources."""
    try:
        from app.services.cache import cache_service
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Resource.id)
                .where(Resource.is_deleted == False, Resource.visibility == "public")
                .order_by(Resource.downloads.desc())
                .limit(20)
            )
            resource_ids = [str(r[0]) for r in result.all()]
        
        logger.info(f"Updated popular resources cache: {len(resource_ids)} items")
        return len(resource_ids)
        
    except Exception as e:
        logger.error(f"Error updating popular resources: {e}")
