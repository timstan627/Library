"""
Student Resource Library - FastAPI Application (SQLAlchemy)
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.database import init_db, close_db, seed_default_admin, AsyncSessionLocal
from app.core.middleware import RateLimitMiddleware, RequestTimingMiddleware, SecurityHeadersMiddleware
from app.api.v1 import api_router

# Configure logging — clean, readable output
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Suppress noisy library logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyrogram.connection").setLevel(logging.WARNING)
logging.getLogger("pyrogram.session").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)  # Suppress per-query DEBUG spam
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logger = logging.getLogger(__name__)


async def _fetch_public_stats() -> dict:
    """Query function for homepage public stats (SQLAlchemy)."""
    from sqlalchemy import select, func
    from app.models.user import User
    from app.models.resource import Resource
    from app.models.download import Download
    from app.models.course import Course
    
    async with AsyncSessionLocal() as db:
        total_resources = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.is_deleted == False, Resource.visibility == "public")
        )).scalar()
        total_users = (await db.execute(
            select(func.count()).select_from(User).where(User.is_active == True, User.is_banned == False)
        )).scalar()
        total_downloads = (await db.execute(
            select(func.count()).select_from(Download)
        )).scalar()
        total_courses = (await db.execute(
            select(func.count()).select_from(Course).where(Course.is_active == True)
        )).scalar()
    
    return {
        "resources": total_resources,
        "users": total_users,
        "downloads": total_downloads,
        "courses": total_courses,
    }


async def _fetch_admin_dashboard_full() -> dict:
    """Query function for admin dashboard (admin.py route)."""
    from sqlalchemy import select, func
    from app.models.user import User
    from app.models.resource import Resource
    from app.models.download import Download
    from app.models.report import Report
    from datetime import datetime, timezone, timedelta
    
    async with AsyncSessionLocal() as db:
        total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
        total_resources = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.is_deleted == False)
        )).scalar()
        total_downloads = (await db.execute(select(func.count()).select_from(Download))).scalar()
        
        total_storage = (await db.execute(
            select(func.coalesce(func.sum(Resource.file_size), 0)).where(Resource.is_deleted == False)
        )).scalar()
        
        pending_reports = 0
        try:
            pending_reports = (await db.execute(
                select(func.count()).select_from(Report).where(Report.status == "pending")
            )).scalar()
        except Exception:
            pass
        
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        new_users = (await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= week_ago)
        )).scalar()
        new_resources = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.is_deleted == False, Resource.created_at >= week_ago)
        )).scalar()
    
    return {
        "total_users": total_users,
        "total_resources": total_resources,
        "total_downloads": total_downloads,
        "total_storage_bytes": total_storage,
        "total_storage_gb": round(total_storage / (1024 * 1024 * 1024), 2),
        "total_storage_mb": round(total_storage / (1024 * 1024), 2),
        "pending_reports": pending_reports,
        "new_users_7d": new_users,
        "new_resources_7d": new_resources,
    }


async def _fetch_admin_dashboard_lite() -> dict:
    """Query function for admin dashboard (admin/dashboard.py route)."""
    from sqlalchemy import select, func
    from app.models.user import User
    from app.models.resource import Resource
    from datetime import datetime, timezone, timedelta
    
    async with AsyncSessionLocal() as db:
        total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
        total_resources = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.is_deleted == False)
        )).scalar()
        
        # Downloads and storage from SQL aggregation
        total_downloads = (await db.execute(
            select(func.coalesce(func.sum(Resource.downloads), 0)).where(Resource.is_deleted == False)
        )).scalar()
        total_storage_bytes = (await db.execute(
            select(func.coalesce(func.sum(Resource.file_size), 0)).where(Resource.is_deleted == False)
        )).scalar()
        
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        new_users_7d = (await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= seven_days_ago)
        )).scalar()
        new_resources_7d = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.created_at >= seven_days_ago, Resource.is_deleted == False)
        )).scalar()
        
        pending_moderation = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.moderation_status == "pending", Resource.is_deleted == False)
        )).scalar()
    
    return {
        "total_users": total_users,
        "total_resources": total_resources,
        "total_downloads": total_downloads,
        "total_storage_bytes": total_storage_bytes,
        "pending_reports": 0,
        "pending_moderation": pending_moderation,
        "new_users_7d": new_users_7d,
        "new_resources_7d": new_resources_7d,
    }


async def _fetch_moderation_stats() -> dict:
    """Query function for moderation stats."""
    from sqlalchemy import select, func
    from app.models.resource import Resource
    
    async with AsyncSessionLocal() as db:
        pending = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.moderation_status == "pending", Resource.is_deleted == False)
        )).scalar()
        approved = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.moderation_status == "approved", Resource.is_deleted == False)
        )).scalar()
        rejected = (await db.execute(
            select(func.count()).select_from(Resource).where(Resource.moderation_status == "rejected", Resource.is_deleted == False)
        )).scalar()
    
    return {
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "total": pending + approved + rejected,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Student Resource Library...")
    await init_db()
    logger.info("Database initialized")
    await seed_default_admin()
    logger.info("Default admin seeded")
    
    # Connect Telegram Bot
    from app.services.telegram import telegram_service
    await telegram_service.connect()
    
    # Register stats queries and start background refresh
    from app.services.cache import cache_service
    cache_service.register_stats("public_stats", _fetch_public_stats, ttl=60)
    cache_service.register_stats("admin_dashboard_full", _fetch_admin_dashboard_full, ttl=30)
    cache_service.register_stats("admin_dashboard_lite", _fetch_admin_dashboard_lite, ttl=30)
    cache_service.register_stats("moderation_stats", _fetch_moderation_stats, ttl=30)
    await cache_service.start()
    logger.info("StatsEngine started with background refresh")
    
    # Start scheduled midnight DB backup to Telegram
    from app.tasks.scheduled_backup import start_backup_scheduler, stop_backup_scheduler
    start_backup_scheduler()
    logger.info("Scheduled backup task started (midnight IST)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    stop_backup_scheduler()
    await cache_service.stop()
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Enterprise-grade Student Resource Library with Telegram Storage",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# CORS middleware
allowed_origins = [
    settings.app_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Request timing middleware
app.add_middleware(RequestTimingMiddleware)

# Rate limiting middleware
if settings.enable_rate_limiting:
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)


# HTTPException handler with CORS headers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    origin = request.headers.get("origin")
    headers = dict(exc.headers or {})
    if origin:
        headers.update({
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        })
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    origin = request.headers.get("origin")
    headers = {}
    if origin:
        headers.update({
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        })
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
        headers=headers,
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "app": settings.app_name}


# Prometheus metrics (debug only)
if settings.debug:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    return {"name": settings.app_name, "version": "1.0.0", "docs": "/docs" if settings.debug else "Disabled"}


# Public stats endpoint for home page live counts (cached 60s)
@app.get("/api/v1/stats", tags=["Public"])
async def get_public_stats():
    from app.services.cache import cache_service
    data = await cache_service.get_stats("public_stats")
    if data:
        return data
    return await _fetch_public_stats()
