"""
Student Resource Library - FastAPI Application
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.database import init_db, close_db, seed_default_admin
from app.core.middleware import RateLimitMiddleware, RequestTimingMiddleware
from app.api.v1 import api_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logger = logging.getLogger(__name__)


async def periodic_tasks_loop():
    """Simple loop for periodic background tasks (Celery-free)."""
    from app.tasks import cleanup_expired_sessions, cleanup_soft_deleted_resources, aggregate_daily_stats
    
    # Wait a bit before first run to let DB stabilize
    await asyncio.sleep(60)
    
    while True:
        try:
            logger.info("Running periodic background tasks...")
            await cleanup_expired_sessions()
            await cleanup_soft_deleted_resources()
            await aggregate_daily_stats()
            
            # Sleep for 24 hours
            await asyncio.sleep(86400)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic tasks loop: {e}")
            await asyncio.sleep(3600)  # Retry in an hour if crash


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
    
    # Start periodic tasks
    asyncio.create_task(periodic_tasks_loop())
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
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

# CORS middleware - Added FIRST so it executes LAST in the chain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request timing middleware
app.add_middleware(RequestTimingMiddleware)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)


# HTTPException handler with CORS headers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and ensure CORS headers are present."""
    origin = request.headers.get("origin", "*")
    headers = dict(exc.headers or {})
    if origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
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
    origin = request.headers.get("origin", "*")
    headers = {}
    if origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        headers.update({
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        })
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
        },
        headers=headers,
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.environment,
    }


# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Disabled",
    }


# Public stats endpoint for home page live counts
@app.get("/api/v1/stats", tags=["Public"])
async def get_public_stats():
    """Get public statistics for the home page (no auth required)."""
    from app.models.user import User
    from app.models.resource import Resource
    from app.models.download import Download
    from app.models.course import Course
    
    total_resources = await Resource.find(Resource.is_deleted == False, Resource.visibility == "public").count()
    total_users = await User.find(User.is_active == True, User.is_banned == False).count()
    total_downloads = await Download.count()
    total_courses = await Course.find(Course.is_active == True).count()
    
    return {
        "resources": total_resources,
        "users": total_users,
        "downloads": total_downloads,
        "courses": total_courses,
    }

