"""
Admin API Package
Contains all administrative endpoints for the Student Library system.
"""

from fastapi import APIRouter

router = APIRouter()

# Import all admin routers
from app.api.v1.admin.departments import router as departments_router
from app.api.v1.admin.courses import router as courses_router
from app.api.v1.admin.moderation import router as moderation_router
from app.api.v1.admin.users import router as users_router
from app.api.v1.admin.resources import router as resources_router

# Include all sub-routers
router.include_router(departments_router, prefix="/departments", tags=["Admin - Departments"])
router.include_router(courses_router, prefix="/courses", tags=["Admin - Courses"])
router.include_router(moderation_router, prefix="/moderation", tags=["Admin - Moderation"])
router.include_router(users_router, prefix="/users", tags=["Admin - Users"])
router.include_router(resources_router, prefix="/resources", tags=["Admin - Resources"])

__all__ = ["router"]

