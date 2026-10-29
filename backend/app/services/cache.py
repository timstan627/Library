"""
Custom In-Memory Stats & Cache Engine
Zero-dependency replacement for Redis (single-process design — see docs):
- StatsEngine: TTL-based stat caching with background refresh, event
  invalidation, and per-key single-flight (concurrent misses share one fetch)
"""
import asyncio
import json
import logging
import time
from typing import Optional, Any, Dict, Callable, Awaitable

logger = logging.getLogger(__name__)


# ============================================================
# Stats Engine (TTL caching + background refresh + single-flight)
# ============================================================

class StatsEntry:
    """A cached stats result with TTL."""
    __slots__ = ('data', 'expires_at', 'ttl', 'is_stale')
    
    def __init__(self, data: dict, ttl: int):
        self.data = data
        self.ttl = ttl
        self.expires_at = time.monotonic() + ttl
        self.is_stale = False
    
    @property
    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at
    
    @property
    def expires_soon(self) -> bool:
        """Returns True if expires within 5 seconds."""
        return time.monotonic() > (self.expires_at - 5)


class StatsEngine:
    """
    Fast in-memory stats with background refresh.
    
    Usage:
        engine.register("public_stats", fetch_public_stats, ttl=60)
        data = await engine.get("public_stats")  # <1ms on cache hit
        engine.invalidate("public_stats")  # Mark stale after writes
    """
    
    def __init__(self):
        self._cache: Dict[str, StatsEntry] = {}
        self._query_fns: Dict[str, Callable[[], Awaitable[dict]]] = {}
        self._ttls: Dict[str, int] = {}
        # Single-flight: one in-flight fetch per key; concurrent misses await
        # the same task instead of stampeding the DB with duplicate queries.
        self._inflight: Dict[str, asyncio.Task] = {}
        self._refresh_task: Optional[asyncio.Task] = None
        self._running = False
        self._hits = 0
        self._misses = 0
        self._refreshes = 0
    
    def register(self, key: str, query_fn: Callable[[], Awaitable[dict]], ttl: int = 30):
        """Register a stats key with its DB query function and TTL."""
        self._query_fns[key] = query_fn
        self._ttls[key] = ttl
        logger.info(f"Stats registered: {key} (TTL: {ttl}s)")
    
    async def get(self, key: str, **kwargs) -> Optional[dict]:
        """
        Get cached stats. Returns cached value if fresh, otherwise fetches
        from DB and caches.

        Single-flight: if another coroutine is already fetching this key,
        await its task instead of issuing a duplicate DB query.
        """
        entry = self._cache.get(key)

        # Cache HIT (not expired, not stale)
        if entry and not entry.is_expired and not entry.is_stale:
            self._hits += 1
            return entry.data

        # Cache MISS
        self._misses += 1
        query_fn = self._query_fns.get(key)
        if not query_fn:
            logger.warning(f"No query function registered for stats key: {key}")
            return None

        # Join an in-flight fetch for the same key, if any
        existing = self._inflight.get(key)
        if existing is not None and not existing.done():
            try:
                return await asyncio.shield(existing)
            except asyncio.CancelledError:
                # Caller cancelled; the shared fetch continues for others
                if key in self._inflight and self._inflight[key] is existing:
                    pass
                raise
            except Exception:
                # Shared fetch failed — fall back to stale below
                entry = self._cache.get(key)
                return entry.data if entry else None

        task = asyncio.create_task(query_fn() if not kwargs else query_fn(**kwargs))
        self._inflight[key] = task
        try:
            data = await task
            ttl = self._ttls.get(key, 30)
            self._cache[key] = StatsEntry(data, ttl)
            return data
        except Exception as e:
            logger.error(f"Stats query failed for {key}: {e}")
            # Return stale data if available
            entry = self._cache.get(key)
            if entry:
                return entry.data
            return None
        finally:
            self._inflight.pop(key, None)
    
    def invalidate(self, *keys: str):
        """Mark one or more stats keys as stale (will be refreshed on next access or background cycle)."""
        for key in keys:
            entry = self._cache.get(key)
            if entry:
                entry.is_stale = True
                logger.debug(f"Stats invalidated: {key}")
    
    def invalidate_prefix(self, prefix: str):
        """Invalidate all keys starting with a prefix."""
        for key in list(self._cache.keys()):
            if key.startswith(prefix):
                self._cache[key].is_stale = True
        logger.debug(f"Stats invalidated prefix: {prefix}*")
    
    async def _refresh_loop(self):
        """Background task: refresh stale/expiring stats every 15s."""
        while self._running:
            try:
                await asyncio.sleep(15)
                refreshed = 0
                for key in list(self._query_fns.keys()):
                    entry = self._cache.get(key)
                    # Refresh if stale, expired, or expiring soon
                    if not entry or entry.is_expired or entry.is_stale or entry.expires_soon:
                        query_fn = self._query_fns[key]
                        try:
                            data = await query_fn()
                            ttl = self._ttls.get(key, 30)
                            self._cache[key] = StatsEntry(data, ttl)
                            refreshed += 1
                        except Exception as e:
                            logger.error(f"Background refresh failed for {key}: {e}")
                
                if refreshed > 0:
                    self._refreshes += refreshed
                    logger.debug(f"Background refresh: {refreshed} stats updated")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stats refresh loop error: {e}")
    
    async def start(self):
        """Start the background refresh task."""
        if self._running:
            return
        self._running = True
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info("StatsEngine background refresh started")
    
    async def stop(self):
        """Stop the background refresh task."""
        self._running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("StatsEngine background refresh stopped")
    
    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        entries_info = {}
        now = time.monotonic()
        for key, entry in self._cache.items():
            entries_info[key] = {
                "stale": entry.is_stale,
                "expires_in": max(0, round(entry.expires_at - now, 1)),
                "ttl": entry.ttl,
            }
        return {
            "registered_keys": list(self._query_fns.keys()),
            "cached_keys": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
            "background_refreshes": self._refreshes,
            "entries": entries_info,
        }


# ============================================================
# Unified CacheService (stats engine facade)
# ============================================================

class CacheService:
    """
    Application-level cache service (stats engine facade).

    Historically this also held a 500MB in-memory file cache for Telegram
    downloads; that was dead code (its only caller was removed) and is gone.
    File content is served from the disk LRU cache in download_manager.
    """

    def __init__(self):
        self.stats_engine = StatsEngine()

    # --- Stats Engine API ---

    def register_stats(self, key: str, query_fn: Callable[[], Awaitable[dict]], ttl: int = 30):
        """Register a stats query."""
        self.stats_engine.register(key, query_fn, ttl)

    async def get_stats(self, key: str, **kwargs) -> Optional[dict]:
        """Get cached stats (returns dict, not bytes)."""
        return await self.stats_engine.get(key, **kwargs)

    def invalidate(self, *keys: str):
        """Invalidate stats keys."""
        self.stats_engine.invalidate(*keys)

    def invalidate_on_upload(self):
        """Call after a resource is uploaded."""
        self.stats_engine.invalidate(
            "public_stats", "admin_dashboard_full",
            "admin_dashboard_lite", "moderation_stats"
        )
        self.stats_engine.invalidate_prefix("user_storage:")

    def invalidate_on_moderation(self):
        """Call after approve/reject."""
        self.stats_engine.invalidate(
            "moderation_stats", "admin_dashboard_full",
            "admin_dashboard_lite", "public_stats"
        )

    def invalidate_on_delete(self):
        """Call after resource deletion."""
        self.stats_engine.invalidate(
            "public_stats", "admin_dashboard_full",
            "admin_dashboard_lite", "moderation_stats"
        )
        self.stats_engine.invalidate_prefix("user_storage:")

    def invalidate_on_user_change(self):
        """Call after user register/ban/unban."""
        self.stats_engine.invalidate(
            "public_stats", "admin_dashboard_full",
            "admin_dashboard_lite"
        )

    # --- Lifecycle ---

    async def start(self):
        """Start background tasks."""
        await self.stats_engine.start()
        logger.info("CacheService started (StatsEngine)")

    async def stop(self):
        """Stop background tasks."""
        await self.stats_engine.stop()
        logger.info("CacheService stopped")

    @property
    def cache_stats(self) -> Dict[str, Any]:
        return {
            "stats_engine": self.stats_engine.stats,
        }


# Global instance
cache_service = CacheService()
