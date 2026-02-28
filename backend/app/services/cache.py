"""
Redis Cache Service for File Downloads
"""
import hashlib
import logging
from typing import Optional, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service for file downloads."""
    
    def __init__(self):
        self.redis_client: Optional[Any] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to Redis (Production) or FakeRedis (Development)."""
        if self._connected and self.redis_client:
            return True
        
        try:
            if settings.environment == "development" or not settings.redis_url:
                import fakeredis.aioredis as fake_redis
                self.redis_client = fake_redis.FakeRedis(decode_responses=False)
                logger.info("FakeRedis cache connected (Mocked for local dev)")
            else:
                import redis.asyncio as real_redis
                self.redis_client = real_redis.from_url(
                    settings.redis_url, 
                    decode_responses=False
                )
                logger.info(f"Redis connected to {settings.redis_url}")
                
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
    
    def _generate_key(self, file_id: str, message_id: int) -> str:
        """Generate cache key for a file."""
        key_data = f"file:{file_id}:{message_id}"
        return f"telegram:file:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get_file(self, file_id: str, message_id: int) -> Optional[bytes]:
        """Get cached file content."""
        if not await self.connect():
            return None
        
        try:
            key = self._generate_key(file_id, message_id)
            data = await self.redis_client.get(key)
            
            if data:
                logger.debug(f"Cache HIT for {file_id}")
                return data
            
            logger.debug(f"Cache MISS for {file_id}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set_file(
        self,
        file_id: str,
        message_id: int,
        content: bytes,
        ttl: int = 3600,  # 1 hour default
    ) -> bool:
        """Cache file content."""
        if not await self.connect():
            return False
        
        try:
            key = self._generate_key(file_id, message_id)
            await self.redis_client.setex(key, ttl, content)
            logger.debug(f"Cached file {file_id} (size: {len(content)} bytes, TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete_file(self, file_id: str, message_id: int) -> bool:
        """Delete cached file."""
        if not await self.connect():
            return False
        
        try:
            key = self._generate_key(file_id, message_id)
            await self.redis_client.delete(key)
            logger.debug(f"Deleted cache for {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False


# Global cache instance
cache_service = CacheService()
