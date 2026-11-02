"""
Runtime site settings — typed helpers over the AppSetting table.

Reads are cached in memory per key; this backend is defined as
single-process (the rate limiter/lockout/reset stores share that
constraint), so a write through `set_bool_setting` is immediately visible
to every request served by this instance and the cache never goes stale.
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import AppSetting

logger = logging.getLogger(__name__)

# In-memory mirror of the DB rows. Single-process backend — safe by design.
_bool_cache: dict[str, bool] = {}


async def get_bool_setting(db: AsyncSession, key: str, default: bool = False) -> bool:
    """Read a boolean setting (cached). Falls back to `default` when unset."""
    if key in _bool_cache:
        return _bool_cache[key]
    try:
        row = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
    except Exception:
        logger.exception("Failed to read app setting %r", key)
        return default
    if row is None:
        _bool_cache[key] = default
        return default
    value = (row.value or "").strip().lower() == "true"
    _bool_cache[key] = value
    return value


async def set_bool_setting(db: AsyncSession, key: str, value: bool, description: Optional[str] = None) -> None:
    """Write a boolean setting, refreshing the cache explicitly."""
    row = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
    if row is None:
        row = AppSetting(key=key, value="true" if value else "false", description=description)
        db.add(row)
    else:
        row.value = "true" if value else "false"
        if description is not None:
            row.description = description
    await db.commit()
    _bool_cache[key] = bool(value)


def clear_settings_cache() -> None:
    """Test hook — drop the in-memory mirror between tests."""
    _bool_cache.clear()
