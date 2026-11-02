"""
Database Models (SQLAlchemy)
"""
from app.models.user import User, Session, APIKey
from app.models.department import Department
from app.models.course import Course
from app.models.resource import Resource
from app.models.collection import Collection, CollectionItem
from app.models.rating import Rating
from app.models.download import Download
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.models.settings import AppSetting
from app.models.catalog import CatalogShelf
from app.models.base import TimestampMixin

__all__ = [
    "User",
    "Session",
    "APIKey",
    "Department",
    "Course",
    "Resource",
    "Collection",
    "CollectionItem",
    "Rating",
    "Download",
    "Report",
    "AuditLog",
    "AppSetting",
    "CatalogShelf",
    "TimestampMixin",
]
