"""
Database Configuration (SQLite via SQLAlchemy + aiosqlite)
Single-file database with resilience: auto-recovery from missing/corrupt files,
backup restoration support, and health monitoring.
"""
import os
import shutil
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, func, event, text as db_text

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database file paths
DB_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_PATH = DB_DIR / "student_library.db"
DB_BACKUP_PATH = DB_DIR / "student_library_backup.db"
DB_CORRUPT_DIR = DB_DIR / "corrupt_backups"
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


def _validate_sqlite_file(path: Path) -> bool:
    """
    Validate that a file is a proper SQLite database with expected tables.
    Returns True if valid, False if corrupt/invalid.
    """
    if not path.exists():
        return False

    # Check minimum file size (SQLite header = 100 bytes)
    if path.stat().st_size < 100:
        logger.warning(f"DB file too small ({path.stat().st_size} bytes): {path}")
        return False

    try:
        # Check SQLite magic header bytes
        with open(path, 'rb') as f:
            header = f.read(16)
            if not header.startswith(b'SQLite format 3'):
                logger.warning(f"Invalid SQLite header in: {path}")
                return False

        # Try connecting and running an integrity check
        conn = sqlite3.connect(str(path))
        cursor = conn.cursor()

        # Quick integrity check (not full, much faster)
        cursor.execute("PRAGMA quick_check")
        result = cursor.fetchone()
        if result[0] != 'ok':
            logger.error(f"SQLite integrity check FAILED for: {path} — {result}")
            conn.close()
            return False

        conn.close()
        logger.info(f"SQLite validation PASSED for: {path} ({path.stat().st_size / 1024:.1f} KB)")
        return True

    except sqlite3.DatabaseError as e:
        logger.error(f"SQLite validation ERROR for {path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error validating {path}: {e}")
        return False


def _has_expected_tables(path: Path) -> bool:
    """Check if the database has the expected application tables."""
    expected_tables = {'users', 'resources', 'downloads', 'ratings'}
    try:
        conn = sqlite3.connect(str(path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        found = expected_tables.intersection(tables)
        if len(found) >= 3:  # At least 3 of 4 core tables
            logger.info(f"DB has {len(found)}/{len(expected_tables)} expected tables: {found}")
            return True
        else:
            logger.warning(f"DB missing tables. Found: {tables}, Expected: {expected_tables}")
            return False
    except Exception as e:
        logger.error(f"Error checking tables: {e}")
        return False


def _quarantine_corrupt_db(path: Path, reason: str):
    """Move a corrupt database file to the corrupt_backups directory."""
    DB_CORRUPT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    quarantine_name = f"corrupt_{timestamp}_{path.name}"
    quarantine_path = DB_CORRUPT_DIR / quarantine_name
    try:
        shutil.move(str(path), str(quarantine_path))
        logger.warning(
            f"⚠️ Corrupt DB quarantined: {path.name} → corrupt_backups/{quarantine_name} "
            f"(Reason: {reason})"
        )
    except Exception as e:
        logger.error(f"Failed to quarantine corrupt DB: {e}")
        # If can't move, delete it
        try:
            path.unlink()
            logger.warning(f"Deleted corrupt DB instead: {path}")
        except Exception:
            pass


def _try_restore_backup() -> bool:
    """
    Check if a backup database exists and is valid.
    If so, copy it as the primary database.
    Returns True if backup was restored.
    """
    if not DB_BACKUP_PATH.exists():
        logger.info("No backup database found at: %s", DB_BACKUP_PATH)
        return False

    if _validate_sqlite_file(DB_BACKUP_PATH):
        if _has_expected_tables(DB_BACKUP_PATH):
            try:
                shutil.copy2(str(DB_BACKUP_PATH), str(DB_PATH))
                logger.info(
                    f"✅ Backup restored successfully! "
                    f"{DB_BACKUP_PATH.name} → {DB_PATH.name} "
                    f"({DB_BACKUP_PATH.stat().st_size / 1024:.1f} KB)"
                )
                return True
            except Exception as e:
                logger.error(f"Failed to restore backup: {e}")
                return False
        else:
            logger.warning(
                f"Backup exists but doesn't have expected tables. "
                f"It may be from a different application. Ignoring."
            )
            return False
    else:
        logger.warning(f"Backup file exists but is corrupt/invalid: {DB_BACKUP_PATH}")
        _quarantine_corrupt_db(DB_BACKUP_PATH, "Backup file failed validation")
        return False


def resolve_database() -> str:
    """
    Smart database resolution with full edge-case handling:
    
    1. If DB exists and is valid → use it
    2. If DB exists but is corrupt → quarantine it, try backup, else create fresh
    3. If DB is missing → try backup, else create fresh
    4. If backup exists but is corrupt → quarantine it too
    
    Returns: status message describing what happened
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Case 1: DB file exists
    if DB_PATH.exists():
        if _validate_sqlite_file(DB_PATH):
            return f"Database OK: {DB_PATH.name} ({DB_PATH.stat().st_size / 1024:.1f} KB)"
        else:
            # DB exists but is corrupt
            _quarantine_corrupt_db(DB_PATH, "Primary DB failed validation")

            # Try to restore from backup
            if _try_restore_backup():
                return "Primary DB was corrupt → restored from backup"
            else:
                return "Primary DB was corrupt, no valid backup → will create fresh database"

    # Case 2: DB file doesn't exist
    else:
        logger.warning(f"⚠️ Database file not found: {DB_PATH}")

        # Try to restore from backup
        if _try_restore_backup():
            return "Database was missing → restored from backup"
        else:
            return "Database missing, no backup → will create fresh database"


# Async engine + session
engine = create_async_engine(
    DB_URL,
    echo=False,  # Set True for SQL query logging
    connect_args={"check_same_thread": False},  # Required for SQLite
)

async_session = async_sessionmaker(engine, expire_on_commit=False)
AsyncSessionLocal = async_session  # Alias for standalone usage (stats queries, etc.)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async DB session with error handling."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            # Check if this is a DB corruption/missing error
            error_str = str(e).lower()
            if any(kw in error_str for kw in ['disk i/o error', 'database is locked',
                                                'no such table', 'corrupt', 'malformed']):
                logger.critical(f"🔴 DATABASE ERROR detected in request: {e}")
                logger.info("Database will be checked and recovered on next startup")
            raise


async def init_db():
    """
    Initialize database with full resilience:
    - Validates existing DB file
    - Restores from backup if primary is missing/corrupt
    - Creates fresh DB with all tables if no valid file found
    - Enables WAL mode and foreign keys
    """
    # Step 1: Resolve the database file (validate, restore, or prepare for creation)
    status = resolve_database()
    logger.info(f"📦 DB Resolution: {status}")

    # Step 2: Import all models so SQLAlchemy knows about them
    from app.models import user, resource, download, rating, report, audit_log, department, course  # noqa

    # Step 3: Create all tables (safe — only creates if missing)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        # Last resort: delete and recreate
        if DB_PATH.exists():
            _quarantine_corrupt_db(DB_PATH, f"Table creation failed: {e}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Fresh database created after table creation failure")

    # Step 4: Enable WAL mode for better concurrent performance
    try:
        async with engine.begin() as conn:
            await conn.execute(db_text("PRAGMA journal_mode=WAL"))
            await conn.execute(db_text("PRAGMA foreign_keys=ON"))
    except Exception as e:
        logger.warning(f"Could not set PRAGMA modes: {e}")

    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    logger.info(f"✅ SQLite database ready (WAL mode, foreign keys ON, {db_size / 1024:.1f} KB)")


async def close_db():
    """Dispose engine and close all connections."""
    await engine.dispose()
    logger.info("Database connections closed")


async def check_db_health() -> dict:
    """
    Runtime health check — call from API endpoint or background task.
    Returns dict with status, details, and any issues found.
    """
    health = {
        "status": "healthy",
        "file_exists": DB_PATH.exists(),
        "file_size": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "backup_exists": DB_BACKUP_PATH.exists(),
        "backup_size": DB_BACKUP_PATH.stat().st_size if DB_BACKUP_PATH.exists() else 0,
        "issues": [],
    }

    if not DB_PATH.exists():
        health["status"] = "critical"
        health["issues"].append("Database file is missing")
        return health

    if not _validate_sqlite_file(DB_PATH):
        health["status"] = "critical"
        health["issues"].append("Database file is corrupt")
        return health

    # Try a live query
    try:
        async with async_session() as session:
            result = await session.execute(db_text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            health["user_count"] = user_count
    except Exception as e:
        health["status"] = "degraded"
        health["issues"].append(f"Query failed: {str(e)}")

    return health


async def create_backup() -> dict:
    """
    Create a backup of the current database.
    Returns dict with status and file info.
    """
    if not DB_PATH.exists():
        return {"status": "error", "message": "No database to backup"}

    if not _validate_sqlite_file(DB_PATH):
        return {"status": "error", "message": "Current database is corrupt, cannot backup"}

    try:
        shutil.copy2(str(DB_PATH), str(DB_BACKUP_PATH))
        size = DB_BACKUP_PATH.stat().st_size
        logger.info(f"✅ Database backup created: {DB_BACKUP_PATH} ({size / 1024:.1f} KB)")
        return {
            "status": "success",
            "message": "Backup created successfully",
            "path": str(DB_BACKUP_PATH),
            "size": size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return {"status": "error", "message": f"Backup failed: {str(e)}"}


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
