"""
Celery Tasks Configuration and Background Tasks
"""
from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "student_library",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
    include=["app.tasks.cleanup", "app.tasks.analytics"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 min soft limit
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-deleted-files": {
        "task": "app.tasks.cleanup.cleanup_deleted_files",
        "schedule": 86400.0,  # Daily (in seconds)
    },
    "update-storage-quotas": {
        "task": "app.tasks.cleanup.update_storage_quotas",
        "schedule": 3600.0,  # Hourly
    },
    "aggregate-analytics": {
        "task": "app.tasks.analytics.aggregate_daily_stats",
        "schedule": 86400.0,  # Daily
    },
}
