"""
Background Tasks Initialization
"""
# Standard async tasks (called via BackgroundTasks)
from app.tasks.cleanup import cleanup_expired_sessions, cleanup_soft_deleted_resources
from app.tasks.analytics import aggregate_daily_stats
