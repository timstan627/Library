"""
Custom In-Memory Stats & Cache Engine
Zero-dependency replacement for Redis. Provides:
- StatsEngine: TTL-based counters with background refresh & event invalidation
- FileCache: LRU file byte cache with 500MB memory cap
- CacheService: Unified API for both
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Optional, Any, Dict, Callable, Awaitable
from collections import OrderedDict

logger = logging.getLogger(__name__)


# ============================================================
# File Cache (LRU with memory cap)
# ============================================================

class CacheEntry:
    """A single cache entry with expiration tracking."""
    __slots__ = ('value', 'expires_at', 'size_bytes')
    
    def __init__(self, value: bytes, ttl: int):
        self.value = value
        self.expires_at = time.monotonic() + ttl
        self.size_bytes = len(value)
    
    @property
    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class FileCache:
    """
    LRU file byte cache with TTL and memory cap.
    Used for Telegram downloaded files.
    """
    
    def __init__(self, max_memory_mb: int = 500):
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._max_bytes = max_memory_mb * 1024 * 1024
        self._current_bytes = 0
        self._hits = 0
        self._misses = 0
    
    async def get(self, key: str) -> Optional[bytes]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired:
                self._current_bytes -= entry.size_bytes
                del self._store[key]
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return entry.value
    
    async def set(self, key: str, value: bytes, ttl: int = 3600) -> bool:
        async with self._lock:
            if key in self._store:
                old = self._store[key]
                self._current_bytes -= old.size_bytes
                del self._store[key]
            
            entry = CacheEntry(value, ttl)
            
            # LRU eviction
            while self._current_bytes + entry.size_bytes > self._max_bytes and self._store:
                _, oldest = self._store.popitem(last=False)
                self._current_bytes -= oldest.size_bytes
            
            if entry.size_bytes > self._max_bytes:
                return False
            
            self._store[key] = entry
            self._current_bytes += entry.size_bytes
            return True
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            entry = self._store.pop(key, None)
            if entry:
                self._current_bytes -= entry.size_bytes
                return True
            return False
    
    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "entries": len(self._store),
            "memory_mb": round(self._current_bytes / (1024 * 1024), 2),
            "max_mb": self._max_bytes // (1024 * 1024),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
        }


# ============================================================
# Stats Engine (TTL counters + background refresh)
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
        self._lock = asyncio.Lock()
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
        Get cached stats. Returns cached value if fresh,
        otherwise fetches from DB and caches.
        """
        entry = self._cache.get(key)
        
        # Cache HIT (not expired, not stale)
        if entry and not entry.is_expired and not entry.is_stale:
            self._hits += 1
            return entry.data
        
        # Cache MISS — fetch from DB
        self._misses += 1
        query_fn = self._query_fns.get(key)
        if not query_fn:
            logger.warning(f"No query function registered for stats key: {key}")
            return None
        
        try:
            data = await query_fn(**kwargs) if kwargs else await query_fn()
            ttl = self._ttls.get(key, 30)
            self._cache[key] = StatsEntry(data, ttl)
            return data
        except Exception as e:
            logger.error(f"Stats query failed for {key}: {e}")
            # Return stale data if available
            if entry:
                return entry.data
            return None
    
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
# Unified CacheService (combines FileCache + StatsEngine)
# ============================================================

class CacheService:
    """
    Application-level cache service.
    - File cache: Telegram download bytes (LRU, 500MB cap)
    - Stats engine: DB query results (TTL, background refresh)
    """
    
    def __init__(self):
        self.files = FileCache(max_memory_mb=500)
        self.stats_engine = StatsEngine()
    
    # --- File Cache API (Telegram downloads) ---
    
    def _file_key(self, file_id: str, message_id: int) -> str:
        key_data = f"file:{file_id}:{message_id}"
        return f"tg:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get_file(self, file_id: str, message_id: int) -> Optional[bytes]:
        return await self.files.get(self._file_key(file_id, message_id))
    
    async def set_file(self, file_id: str, message_id: int, content: bytes, ttl: int = 3600) -> bool:
        return await self.files.set(self._file_key(file_id, message_id), content, ttl)
    
    async def delete_file(self, file_id: str, message_id: int) -> bool:
        return await self.files.delete(self._file_key(file_id, message_id))
    
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
        logger.info("CacheService started (FileCache + StatsEngine)")
    
    async def stop(self):
        """Stop background tasks."""
        await self.stats_engine.stop()
        logger.info("CacheService stopped")
    
    @property
    def cache_stats(self) -> Dict[str, Any]:
        return {
            "file_cache": self.files.stats,
            "stats_engine": self.stats_engine.stats,
        }


# Global instance
cache_service = CacheService()
