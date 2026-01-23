"""
Analytics Tasks
"""
import logging
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.resource import Resource
from app.models.download import Download
from app.services.cache import cache_service

logger = logging.getLogger(__name__)

async def aggregate_daily_stats():
    """Aggregate daily statistics for reporting."""
    today = datetime.now(timezone.utc).date()
    yesterday_date = today - timedelta(days=1)
    
    # Beanie doesnt support func.date directly in find(), 
    # we need to query by range for "yesterday"
    start_of_yesterday = datetime.combine(yesterday_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_of_yesterday = datetime.combine(yesterday_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    try:
        # Downloads yesterday
        downloads_count = await Download.find(
            Download.created_at >= start_of_yesterday,
            Download.created_at <= end_of_yesterday
        ).count()
        
        # New resources yesterday
        resources_count = await Resource.find(
            Resource.created_at >= start_of_yesterday,
            Resource.created_at <= end_of_yesterday,
            Resource.is_deleted == False
        ).count()
        
        # New users yesterday
        users_count = await User.find(
            User.created_at >= start_of_yesterday,
            User.created_at <= end_of_yesterday
        ).count()
        
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
        await cache_service.connect()
        
        # Get top 20 by downloads
        resources = await Resource.find(
            Resource.is_deleted == False,
            Resource.visibility == "public"
        ).sort("-downloads").limit(20).to_list()
        
        # Cache as list of IDs
        resource_ids = [str(r.id) for r in resources]
        await cache_service.set("popular_resources", resource_ids, ttl=3600)
        
        logger.info(f"Updated popular resources cache: {len(resource_ids)} items")
        return len(resource_ids)
        
    except Exception as e:
        logger.error(f"Error updating popular resources: {e}")
