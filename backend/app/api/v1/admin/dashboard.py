from fastapi import APIRouter, Depends
from datetime import datetime, timedelta, timezone
from app.api.v1.deps import require_admin
from app.models.user import User
from app.models.resource import Resource

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_stats(
    current_user: User = Depends(require_admin),
):
    """Get admin dashboard statistics."""
    
    # Counts
    total_users = await User.count()
    total_resources = await Resource.count()
    
    # Aggregations
    # Total downloads
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$downloads"}}}
    ]
    downloads_result = await Resource.aggregate(pipeline).to_list(1)
    total_downloads = downloads_result[0]["total"] if downloads_result else 0
    
    # Total storage
    pipeline_storage = [
        {"$group": {"_id": None, "total": {"$sum": "$file_size"}}}
    ]
    storage_result = await Resource.aggregate(pipeline_storage).to_list(1)
    total_storage_bytes = storage_result[0]["total"] if storage_result else 0
    
    # New in last 7 days
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    new_users_7d = await User.find(User.created_at >= seven_days_ago).count()
    new_resources_7d = await Resource.find(Resource.created_at >= seven_days_ago).count()
    
    # Pending items (approximated or real)
    pending_moderation = await Resource.find(Resource.moderation_status == "pending").count()
    
    return {
        "total_users": total_users,
        "total_resources": total_resources,
        "total_downloads": total_downloads,
        "total_storage_bytes": total_storage_bytes,
        "pending_reports": 0, # Implement if reports exist
        "pending_moderation": pending_moderation,
        "new_users_7d": new_users_7d,
        "new_resources_7d": new_resources_7d,
    }
