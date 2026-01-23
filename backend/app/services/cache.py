"""
Redis Cache Service for File Downloads
"""
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CacheService:
    """In-memory caching service."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self) -> bool:
        """Mock connect."""
        return True
    
    async def disconnect(self):
        """Mock disconnect."""
        pass
    
    def _generate_key(self, file_id: str, message_id: int) -> str:
        """Generate cache key for a file."""
        return f"file:{file_id}:{message_id}"
    
    async def get_file(self, file_id: str, message_id: int) -> Optional[bytes]:
        """Get cached file content."""
        key = self._generate_key(file_id, message_id)
        if key in self._cache:
            entry = self._cache[key]
            if entry["expiry"] > time.time():
                logger.debug(f"Cache HIT for {file_id}")
                return entry["data"]
            else:
                del self._cache[key]
        
        logger.debug(f"Cache MISS for {file_id}")
        return None
    
    async def set_file(
        self,
        file_id: str,
        message_id: int,
        content: bytes,
        ttl: int = 3600,
    ) -> bool:
        """Cache file content."""
        key = self._generate_key(file_id, message_id)
        self._cache[key] = {
            "data": content,
            "expiry": time.time() + ttl
        }
        logger.debug(f"Cached file {file_id} in-memory")
        return True
    
    async def delete_file(self, file_id: str, message_id: int) -> bool:
        """Delete cached file."""
        key = self._generate_key(file_id, message_id)
        if key in self._cache:
            del self._cache[key]
        return True
    
    async def get(self, key: str) -> Optional[Any]:
        """Generic get."""
        if key in self._cache:
            entry = self._cache[key]
            if entry["expiry"] > time.time():
                return entry["data"]
            del self._cache[key]
        return None
        
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Generic set."""
        self._cache[key] = {
            "data": value,
            "expiry": time.time() + ttl
        }


# Global cache instance
cache_service = CacheService()
