"""
Hybrid Download Manager — Disk Cache + Streaming + Concurrency Limit

Replaces the naive "download entire file to RAM" approach with:
1. LRU disk cache (configurable max size, default 1GB)
2. asyncio.Semaphore to limit concurrent Telegram downloads
3. Stream-through: simultaneously cache to disk + stream to user
4. Automatic cleanup of old cached files (LRU eviction)

Memory usage: ~1MB per active download (chunk buffer) instead of N × file_size
"""
import os
import asyncio
import json
import time
import shutil
import logging
from pathlib import Path
from typing import Optional, AsyncIterator
from collections import OrderedDict

from app.core.config import settings

logger = logging.getLogger(__name__)


class DiskCacheEntry:
    """Metadata for a cached file on disk."""
    __slots__ = ('path', 'size', 'last_accessed', 'message_id', 'channel_id')

    def __init__(self, path: str, size: int, message_id: int, channel_id: int):
        self.path = path
        self.size = size
        self.last_accessed = time.time()
        self.message_id = message_id
        self.channel_id = channel_id


class DiskFileCache:
    """
    LRU file cache on disk with configurable max size.
    Files are stored in a cache directory and evicted when the total size exceeds the limit.
    """

    def __init__(self, cache_dir: str = None, max_size_mb: int = 1024):
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.cache_dir = Path(cache_dir) if cache_dir else base_dir / "file_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._index: OrderedDict[str, DiskCacheEntry] = OrderedDict()
        self._current_size = 0
        self._lock = asyncio.Lock()

        # Stats
        self._hits = 0
        self._misses = 0

        # Load existing cache from disk on startup
        self._load_existing_cache()

    def _cache_key(self, message_id: int, channel_id: int) -> str:
        return f"{channel_id}_{message_id}"

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / key

    def _load_existing_cache(self):
        """Scan cache directory and rebuild index from existing files."""
        try:
            for file_path in sorted(self.cache_dir.iterdir(), key=lambda p: p.stat().st_mtime):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    key = file_path.name
                    size = file_path.stat().st_size
                    # Parse key back to message_id and channel_id
                    parts = key.split('_', 1)
                    if len(parts) == 2:
                        try:
                            channel_id = int(parts[0])
                            message_id = int(parts[1])
                            entry = DiskCacheEntry(str(file_path), size, message_id, channel_id)
                            entry.last_accessed = file_path.stat().st_mtime
                            self._index[key] = entry
                            self._current_size += size
                        except ValueError:
                            continue

            logger.info(
                f"Disk cache loaded: {len(self._index)} files, "
                f"{self._current_size / (1024 * 1024):.1f} MB / "
                f"{self.max_size_bytes / (1024 * 1024):.0f} MB max"
            )
        except Exception as e:
            logger.warning(f"Error loading disk cache: {e}")

    async def get(self, message_id: int, channel_id: int) -> Optional[Path]:
        """
        Get cached file path if it exists.
        Returns the Path to the cached file, or None if not cached.
        """
        key = self._cache_key(message_id, channel_id)

        async with self._lock:
            if key in self._index:
                entry = self._index[key]
                cache_path = Path(entry.path)

                # Verify file still exists on disk
                if cache_path.exists():
                    # Move to end (most recently used)
                    self._index.move_to_end(key)
                    entry.last_accessed = time.time()
                    self._hits += 1
                    return cache_path
                else:
                    # File was deleted externally
                    self._current_size -= entry.size
                    del self._index[key]

            self._misses += 1
            return None

    async def put(self, message_id: int, channel_id: int, file_path: Path) -> bool:
        """
        Add a file to the disk cache by moving/copying it from a temp location.
        Returns True if cached successfully.
        """
        key = self._cache_key(message_id, channel_id)
        cache_path = self._cache_path(key)
        file_size = file_path.stat().st_size

        # Don't cache files larger than 25% of max cache size
        if file_size > self.max_size_bytes * 0.25:
            logger.info(f"File too large to cache ({file_size / (1024*1024):.1f} MB): {key}")
            return False

        async with self._lock:
            # Evict old entries if necessary
            while self._current_size + file_size > self.max_size_bytes and self._index:
                oldest_key, oldest_entry = next(iter(self._index.items()))
                try:
                    old_path = Path(oldest_entry.path)
                    if old_path.exists():
                        old_path.unlink()
                except Exception:
                    pass
                self._current_size -= oldest_entry.size
                del self._index[oldest_key]
                logger.debug(f"Cache evicted: {oldest_key}")

            # Copy file to cache
            try:
                shutil.copy2(str(file_path), str(cache_path))
                entry = DiskCacheEntry(str(cache_path), file_size, message_id, channel_id)
                self._index[key] = entry
                self._current_size += file_size
                logger.info(
                    f"Cached to disk: {key} ({file_size / 1024:.1f} KB) — "
                    f"Total: {self._current_size / (1024*1024):.1f} MB"
                )
                return True
            except Exception as e:
                logger.error(f"Failed to cache file: {e}")
                return False

    async def delete(self, message_id: int, channel_id: int):
        """Remove a file from the cache."""
        key = self._cache_key(message_id, channel_id)
        async with self._lock:
            if key in self._index:
                entry = self._index[key]
                try:
                    path = Path(entry.path)
                    if path.exists():
                        path.unlink()
                except Exception:
                    pass
                self._current_size -= entry.size
                del self._index[key]

    async def clear(self):
        """Clear entire cache."""
        async with self._lock:
            for entry in self._index.values():
                try:
                    Path(entry.path).unlink(missing_ok=True)
                except Exception:
                    pass
            self._index.clear()
            self._current_size = 0
            logger.info("Disk cache cleared")

    def stats(self) -> dict:
        total_requests = self._hits + self._misses
        return {
            "cached_files": len(self._index),
            "total_size_mb": round(self._current_size / (1024 * 1024), 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 0),
            "usage_percent": round(
                (self._current_size / self.max_size_bytes * 100) if self.max_size_bytes > 0 else 0, 1
            ),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(
                (self._hits / total_requests * 100) if total_requests > 0 else 0, 1
            ),
        }


class FileNotFoundInTelegram(Exception):
    """Raised when a file/message no longer exists in the Telegram channel."""
    pass


class DownloadManager:
    """
    Hybrid download manager combining:
    - Disk-based LRU file cache
    - Concurrency-limited Telegram downloads (asyncio.Semaphore)
    - Stream-through download (low memory footprint)
    """

    def __init__(
        self,
        max_concurrent_downloads: int = 5,
        cache_max_size_mb: int = 1024,
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ):
        self.semaphore = asyncio.Semaphore(max_concurrent_downloads)
        self.disk_cache = DiskFileCache(max_size_mb=cache_max_size_mb)
        self.chunk_size = chunk_size
        self._active_downloads = 0
        self._total_downloads = 0
        self._total_bytes_served = 0
        self._lock = asyncio.Lock()

    async def get_file(
        self,
        message_id: int,
        channel_id: int,
        file_id: Optional[str] = None,
    ) -> Path:
        """
        Get a file, either from disk cache or by downloading from Telegram.
        Returns the path to the file on disk.

        Raises:
            FileNotFoundInTelegram: If message was deleted or has no document
            Exception: For other errors (connection, download failures)
        """
        # Step 1: Try disk cache
        cached_path = await self.disk_cache.get(message_id, channel_id)
        if cached_path:
            logger.info(f"📁 Disk cache HIT: msg={message_id}")
            return cached_path

        # Step 2: Download from Telegram (with concurrency limit)
        logger.info(f"📥 Downloading from Telegram: msg={message_id} (waiting for slot...)")

        async with self.semaphore:
            # Double-check cache (another request may have cached it while we waited)
            cached_path = await self.disk_cache.get(message_id, channel_id)
            if cached_path:
                logger.info(f"📁 Disk cache HIT (after wait): msg={message_id}")
                return cached_path

            async with self._lock:
                self._active_downloads += 1

            try:
                from app.services.telegram import telegram_service
                import tempfile

                if not await telegram_service.connect():
                    raise Exception("Telegram client not connected — cannot download file")

                resolved_channel = channel_id or telegram_service.primary_channel

                # Get the message
                try:
                    message = await telegram_service.client.get_messages(
                        chat_id=resolved_channel,
                        message_ids=message_id,
                    )
                except Exception as e:
                    error_str = str(e).lower()
                    # Handle Pyrogram-specific errors for deleted/inaccessible messages
                    if "message" in error_str and ("not found" in error_str or "deleted" in error_str):
                        raise FileNotFoundInTelegram(
                            f"Message {message_id} was deleted from Telegram channel"
                        )
                    if "channel" in error_str and ("invalid" in error_str or "not found" in error_str):
                        raise FileNotFoundInTelegram(
                            f"Telegram channel {resolved_channel} is inaccessible"
                        )
                    raise  # Re-raise other Telegram errors

                # Handle None, empty message, or message without document
                if message is None:
                    raise FileNotFoundInTelegram(
                        f"Message {message_id} not found in Telegram channel {resolved_channel}"
                    )

                # Pyrogram returns an empty Message object for deleted messages
                if hasattr(message, 'empty') and message.empty:
                    raise FileNotFoundInTelegram(
                        f"Message {message_id} was deleted from Telegram channel"
                    )

                if not message.document and not message.photo and not message.video and not message.audio:
                    raise FileNotFoundInTelegram(
                        f"Message {message_id} exists but has no downloadable media"
                    )

                # Download to temp file (Pyrogram handles chunked download internally)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.download') as tmp:
                    tmp_path = Path(tmp.name)

                try:
                    await telegram_service.client.download_media(
                        message=message,
                        file_name=str(tmp_path),
                    )

                    if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                        raise Exception("Downloaded file is empty")

                    # Step 3: Cache the downloaded file
                    await self.disk_cache.put(message_id, resolved_channel, tmp_path)

                    # Return from cache (or the temp file if caching failed)
                    cached_path = await self.disk_cache.get(message_id, resolved_channel)
                    if cached_path:
                        # Clean up temp file since it's now in cache
                        try:
                            tmp_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        return cached_path
                    else:
                        # File was too large to cache, return temp path directly
                        # (caller needs to handle cleanup)
                        return tmp_path

                except Exception:
                    # Clean up temp file on error
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise

            finally:
                async with self._lock:
                    self._active_downloads -= 1
                    self._total_downloads += 1

                # Rate limiting cooldown
                await asyncio.sleep(0.5)

    async def stream_file(
        self,
        message_id: int,
        channel_id: int,
    ) -> AsyncIterator[bytes]:
        """
        Stream a file in chunks. Uses disk cache if available,
        otherwise downloads first then streams from disk.
        Memory: ~1MB per active stream (one chunk buffer).
        """
        # Get the file (from cache or download)
        file_path = await self.get_file(message_id, channel_id)

        # Stream from disk in chunks
        async for chunk in self._stream_from_disk(file_path):
            self._total_bytes_served += len(chunk)
            yield chunk

    async def _stream_from_disk(self, file_path: Path) -> AsyncIterator[bytes]:
        """Stream a file from disk in chunks (async generator)."""
        loop = asyncio.get_event_loop()

        def _read_chunks():
            """Generator that reads file in chunks."""
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk

        for chunk in _read_chunks():
            yield chunk
            # Yield control to event loop between chunks
            await asyncio.sleep(0)

    async def get_file_bytes(
        self,
        message_id: int,
        channel_id: int,
    ) -> bytes:
        """
        Get file as bytes (for backward compatibility).
        Reads from disk cache or downloads first.
        """
        file_path = await self.get_file(message_id, channel_id)
        with open(file_path, 'rb') as f:
            return f.read()

    def stats(self) -> dict:
        """Get download manager statistics."""
        cache_stats = self.disk_cache.stats()
        return {
            "active_downloads": self._active_downloads,
            "total_downloads": self._total_downloads,
            "total_bytes_served_mb": round(self._total_bytes_served / (1024 * 1024), 2),
            "semaphore_slots_available": self.semaphore._value,
            "disk_cache": cache_stats,
        }


# Global singleton
download_manager = DownloadManager(
    max_concurrent_downloads=5,
    cache_max_size_mb=1024,  # 1GB disk cache
    chunk_size=1024 * 1024,  # 1MB chunks
)
