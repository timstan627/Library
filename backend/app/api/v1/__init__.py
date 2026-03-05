"""
API Routes - Version 1
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.resources import router as resources_router
from app.api.v1.search import router as search_router
from app.api.v1.ratings import router as ratings_router
from app.api.v1.admin import router as admin_router
from app.api.v1.reports import router as reports_router
from app.api.v1.password_reset import router as password_reset_router



api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(password_reset_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(resources_router, prefix="/resources", tags=["Resources"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(ratings_router, prefix="/ratings", tags=["Ratings"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])

# Library (personal collections)
from app.api.v1.library import router as library_router
api_router.include_router(library_router, tags=["Library"])

# Public APIs (for forms/dropdowns)
from app.api.v1.departments import router as departments_router
from app.api.v1.courses import router as courses_router
api_router.include_router(departments_router, tags=["Departments"])
api_router.include_router(courses_router, tags=["Courses"])

# Admin APIs are already included via admin_router, no need to double-mount
