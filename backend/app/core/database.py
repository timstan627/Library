"""
Database Configuration (SQLite via SQLAlchemy + aiosqlite)
Single-file database for portability and easy backup/restore.
"""
import os
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, func, event
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database file path
DB_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_PATH = DB_DIR / "student_library.db"
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


# Async engine + session
engine = create_async_engine(
    DB_URL,
    echo=False,  # Set True for SQL query logging
    connect_args={"check_same_thread": False},  # Required for SQLite
)

async_session = async_sessionmaker(engine, expire_on_commit=False)
AsyncSessionLocal = async_session  # Alias for standalone usage (stats queries, etc.)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database: create file and all tables if needed."""
    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    is_new = not DB_PATH.exists()
    
    # Import all models so SQLAlchemy knows about them
    from app.models import user, resource, download, rating, report, audit_log, department, course  # noqa
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    if is_new:
        logger.info(f"New database created: {DB_PATH}")
    else:
        logger.info(f"Database loaded: {DB_PATH} ({DB_PATH.stat().st_size / 1024:.1f} KB)")
    
    # Enable WAL mode for better concurrent read performance
    async with engine.begin() as conn:
        await conn.execute(db_text("PRAGMA journal_mode=WAL"))
        await conn.execute(db_text("PRAGMA foreign_keys=ON"))
    
    logger.info("SQLite database initialized (WAL mode, foreign keys ON)")


async def close_db():
    """Dispose engine and close all connections."""
    await engine.dispose()
    logger.info("Database connections closed")


async def seed_default_admin():
    """Create default admin user if no users exist."""
    from app.models.user import User
    from app.core.security import security_manager
    from sqlalchemy import select
    
    async with async_session() as session:
        # Check if any users exist
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            return  # Users exist already
        
        # Create default admin
        admin = User(
            email="blasteranna1414@gmail.com",
            password_hash=security_manager.hash_password("Blaster1414&"),
            display_name="The Creater",
            role="admin",
            is_active=True,
            is_banned=False,
            email_verified=True,
            storage_quota_bytes=109_951_162_777_600,  # 100TB (Unlimited)
        )
        session.add(admin)
        await session.commit()
        logger.info(f"Default admin created: {admin.email}")


def get_db_path() -> Path:
    """Get the absolute path to the database file."""
    return DB_PATH


def get_db_size() -> int:
    """Get database file size in bytes."""
    if DB_PATH.exists():
        return DB_PATH.stat().st_size
    return 0


# Need to import text
from sqlalchemy import text as db_text
