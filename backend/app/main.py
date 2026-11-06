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
from app.core.database import init_db, close_db, seed_default_admin, check_db_health
from app.core.middleware import (
    RateLimitMiddleware,
    RequestTimingMiddleware,
    SecurityHeadersMiddleware,
    RequestIdMiddleware,
)
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
    from app.services import stats
    stats.register_all(cache_service)
    await cache_service.start()
    logger.info("StatsEngine started with background refresh")
    
    # Start scheduled midnight DB backup to Telegram
    from app.tasks.scheduled_backup import start_backup_scheduler, stop_backup_scheduler
    start_backup_scheduler()
    logger.info("Scheduled backup task started (midnight IST)")

    # Start daily maintenance (session expiry, soft-delete purge)
    from app.tasks.cleanup import start_cleanup_scheduler, stop_cleanup_scheduler
    start_cleanup_scheduler()
    logger.info("Daily cleanup task started")

    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await stop_backup_scheduler()
    await stop_cleanup_scheduler()
    await cache_service.stop()

    # Disconnect Telegram (closes the pyrogram client's network resources)
    from app.services.telegram import telegram_service
    await telegram_service.disconnect()

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

# Rate limiting middleware — registered BEFORE the CORS/header middleware on
# purpose: in Starlette the first-added middleware is the innermost one, so
# its 429 responses flow back out through CORS/security/request-id layers
# (headers applied), and CORS preflights are answered before reaching it
# (never counted against the limit).
if settings.enable_rate_limiting:
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)


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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


def _cors_headers_for(request: Request) -> dict:
    """Origin echo restricted to the same allowlist the CORS middleware uses.

    The CORS middleware doesn't run on exception-handler responses, so
    reflecting an arbitrary Origin with credentials here would let any site
    read authenticated error responses cross-origin.
    """
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") in {o.rstrip("/") for o in allowed_origins}:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}

# GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Request correlation id (X-Request-ID on every response)
app.add_middleware(RequestIdMiddleware)

# Request timing middleware
app.add_middleware(RequestTimingMiddleware)


# HTTPException handler with CORS headers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    headers = dict(exc.headers or {})
    headers.update(_cors_headers_for(request))
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None) or "unknown"
    logger.exception(f"Unhandled exception [request_id={request_id}]: {exc}")
    headers = _cors_headers_for(request)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__, "request_id": request_id},
        headers=headers,
    )


# Health check endpoint — exercises the database (503 when degraded/critical)
@app.get("/health", tags=["Health"])
async def health_check():
    full = await check_db_health()
    if full["status"] != "healthy":
        # Details (issue strings can embed paths) stay in server logs only
        logger.error(f"Health check degraded: {full['issues']}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "app": settings.app_name,
                     "database": {"status": full["status"]}},
        )
    return {"status": "healthy", "app": settings.app_name, "database": {"status": "healthy"}}


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
