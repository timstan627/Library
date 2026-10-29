"""
Test configuration.

Isolation strategy:
- The real app binds its SQLite engine to `backend/student_library.db` at import
  time, so we patch `app.core.database` (engine + sessionmaker + paths) BEFORE
  importing `app.main`, pointing everything at a throwaway temp DB.
- One engine/session for the whole run (app.main binds `AsyncSessionLocal` by
  value at import); each test wipes all rows instead of recreating the engine.
- Telegram is never touched: upload/download paths are monkeypatched per test.
- Lifespan is not run (httpx ASGITransport), so fixtures create tables and any
  seed data explicitly.
"""
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

# ---------------------------------------------------------------------------
# Patch settings + DB layer BEFORE anything imports app.main
# ---------------------------------------------------------------------------
from app.core.config import settings

# Tests fire many requests quickly; the per-IP limiter would 429 them.
settings.enable_rate_limiting = False
# Deterministic secrets so tokens survive across fixtures within the run.
settings.secret_key = "test-secret-key"
settings.jwt_secret_key = "test-jwt-secret-key"
settings.hmac_secret_key = "test-hmac-secret-key"

import app.core.database as dbmod  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

_TMPDIR = tempfile.mkdtemp(prefix="srl_test_db_")
TEST_DB_PATH = Path(_TMPDIR) / "test.db"

dbmod.DB_PATH = TEST_DB_PATH
dbmod.DB_BACKUP_PATH = Path(_TMPDIR) / "test_backup.db"
dbmod.DB_CORRUPT_DIR = Path(_TMPDIR) / "corrupt"
dbmod.DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

# Single shared in-memory-ish connection: StaticPool keeps ONE aiosqlite
# connection for the whole run — required for the temp-file DB to behave
# deterministically across the app's many short-lived sessions.
dbmod.engine = create_async_engine(
    dbmod.DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
dbmod.async_session = async_sessionmaker(dbmod.engine, expire_on_commit=False)
dbmod.AsyncSessionLocal = dbmod.async_session

# Mirror the production per-connection pragmas (FK enforcement + WAL) so tests
# exercise the same constraints as the real engine.
from sqlalchemy import event  # noqa: E402


@event.listens_for(dbmod.engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


# ---------------------------------------------------------------------------
# Import the app only after the patch
# ---------------------------------------------------------------------------
from app.main import app as fastapi_app  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.resource import Resource  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.core.security import security_manager  # noqa: E402
from app.core.middleware import auth_rate_limiter  # noqa: E402
from app.api.v1 import resources as resources_module  # noqa: E402

# Tables wiped between tests, in FK-safe order.
_TABLES_IN_DELETE_ORDER = [
    "collection_items",
    "collections",
    "ratings",
    "downloads",
    "reports",
    "audit_logs",
    "sessions",
    "api_keys",
    "resources",
    "courses",
    "departments",
    "users",
]


async def _wipe_tables():
    async with dbmod.async_session() as session:
        for table in _TABLES_IN_DELETE_ORDER:
            await session.execute(delete(Base.metadata.tables[table]))
        await session.commit()


async def _create_tables():
    async with dbmod.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(autouse=True)
async def _db_isolated():
    """Create tables once, then give every test a clean, empty DB."""
    await _create_tables()
    await _wipe_tables()
    auth_rate_limiter.failed_attempts.clear()
    auth_rate_limiter.email_failures.clear()
    from app.api.v1.password_reset import password_reset_tokens, _email_requests  # noqa: E402
    password_reset_tokens.clear()
    _email_requests.clear()
    resources_module._view_tracker.clear()
    yield
    await _wipe_tables()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client bound to the FastAPI app (no lifespan).

    follow_redirects mirrors axios (the real frontend client), which follows
    FastAPI's trailing-slash 307s.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


# ---------------------------------------------------------------------------
# User factories
# ---------------------------------------------------------------------------
_next_user_seq = 0


async def make_user(
    role: str = "student",
    is_active: bool = True,
    is_banned: bool = False,
    email: str | None = None,
    password: str = "Passw0rd123",
    display_name: str | None = None,
    is_trusted: bool = False,
) -> User:
    global _next_user_seq
    _next_user_seq += 1
    email = email or f"user{_next_user_seq}@test.example"
    user = User(
        email=email.lower(),
        password_hash=security_manager.hash_password(password),
        display_name=display_name or f"User {_next_user_seq}",
        role=role,
        is_active=is_active,
        is_banned=is_banned,
        is_trusted=is_trusted,
    )
    async with dbmod.async_session() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


def login_payload(user: User, password: str = "Passw0rd123") -> dict:
    return {"email": user.email, "password": password}


async def auth_headers(client: AsyncClient, user: User, password: str = "Passw0rd123") -> dict:
    """Login through the API and return a Bearer header for `user`."""
    resp = await client.post("/api/v1/auth/login", json=login_payload(user, password))
    assert resp.status_code == 200, f"login failed for {user.email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def student_user():
    return await make_user(role="student")


@pytest_asyncio.fixture
async def admin_user():
    return await make_user(role="admin")


@pytest_asyncio.fixture
async def moderator_user():
    return await make_user(role="moderator")


@pytest_asyncio.fixture
async def trusted_user():
    return await make_user(role="student", is_trusted=True)


# ---------------------------------------------------------------------------
# Resource factory (DB-level; Telegram storage is faked)
# ---------------------------------------------------------------------------
async def make_resource(
    uploader: User,
    title: str = "Sample Notes",
    course_code: str = "CS101",
    visibility: str = "public",
    moderation_status: str = "approved",
    is_deleted: bool = False,
    tags: list[str] | None = None,
    file_size: int = 1024,
    **overrides,
) -> Resource:
    defaults = dict(
        title=title,
        slug=f"{title.lower().replace(' ', '-')}-testslug{resource_seq()}",
        course_code=course_code,
        file_name=f"{title.replace(' ', '_')}.pdf",
        file_size=file_size,
        mime_type="application/pdf",
        file_hash=f"hash-{resource_seq()}",
        file_extension="pdf",
        telegram_file_id=f"fake-file-id-{resource_seq()}",
        telegram_message_id=resource_seq(),
        telegram_channel_id=-100123,
        uploader_id=uploader.id,
        visibility=visibility,
        moderation_status=moderation_status,
        is_deleted=is_deleted,
        tags_str=",".join(tags) if tags else None,
    )
    defaults.update(overrides)
    resource = Resource(**defaults)
    async with dbmod.async_session() as session:
        session.add(resource)
        await session.commit()
        await session.refresh(resource)
    return resource


def resource_seq() -> int:
    """Monotonic counter for unique slugs/hashes inside factories."""
    global _next_user_seq
    _next_user_seq += 1
    return _next_user_seq


# ---------------------------------------------------------------------------
# Department / course factories
# ---------------------------------------------------------------------------
async def make_department(name: str = "Computer Science", code: str = "CSE", **overrides) -> "Department":
    from app.models.department import Department
    defaults = dict(name=name, code=code, description=None, display_order=0, is_active=True)
    defaults.update(overrides)
    department = Department(**defaults)
    async with dbmod.async_session() as session:
        session.add(department)
        await session.commit()
        await session.refresh(department)
    return department


# ---------------------------------------------------------------------------
# Telegram fakes
# ---------------------------------------------------------------------------
def fake_telegram_upload(monkeypatch, resources_ref=resources_module):
    """Patch resources.telegram_service.upload_file with a deterministic fake."""

    async def _upload(file_bytes: bytes, filename: str, caption: str = ""):
        return {
            "file_id": f"tg-file-{abs(hash(filename)) % 10**10}",
            "message_id": abs(hash(filename + caption)) % 10**9,
            "channel_id": -100123,
            "file_size": len(file_bytes),
            "file_name": filename,
            "mime_type": "application/octet-stream",
        }

    monkeypatch.setattr(resources_ref, "telegram_service", type("T", (), {"upload_file": staticmethod(_upload)})())


def fake_download_file(monkeypatch, resources_ref=resources_module, tmp_path: Path | None = None):
    """Patch download_manager.get_file to return a small real file on disk."""
    target = tmp_path or Path(_TMPDIR) / "fake_download.pdf"
    target.write_bytes(b"%PDF-1.4 fake content")

    async def _get_file(message_id: int, channel_id: int, file_id: str | None = None):
        return target

    monkeypatch.setattr(resources_ref, "download_manager", type("D", (), {"get_file": staticmethod(_get_file)})())
    return target


def reloaded(model_instance):
    """Re-fetch an instance in a fresh session (refresh fails on detached instances)."""
    from app.core.database import async_session

    async def _load():
        async with async_session() as session:
            return await session.get(type(model_instance), model_instance.id)

    return _load()
