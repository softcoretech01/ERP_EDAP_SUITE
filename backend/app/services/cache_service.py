import logging
import json
from typing import Any, Optional
import redis.asyncio as redis
from ..core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.memory_cache = {}
        self.redis_client = None
        self._init_redis()

    def _init_redis(self):
        try:
            # Check if redis is configured
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            logger.info("CacheService: Redis Level 2 cache initialized.")
        except Exception as e:
            logger.warning(f"CacheService: Redis init failed ({e}). Falling back to Level 1 Memory Cache.")
            self.redis_client = None

    async def get(self, key: str) -> Optional[Any]:
        # 1. Check Level 1 (Memory)
        if key in self.memory_cache:
            return self.memory_cache[key]
            
        # 2. Check Level 2 (Redis)
        if self.redis_client:
            try:
                val = await self.redis_client.get(key)
                if val:
                    parsed = json.loads(val)
                    self.memory_cache[key] = parsed  # Backfill memory
                    return parsed
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                logger.warning("Disabling Redis cache due to connection failure.")
                self.redis_client = None
                
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        # 1. Set Level 1
        self.memory_cache[key] = value
        
        # 2. Set Level 2
        if self.redis_client:
            try:
                await self.redis_client.setex(key, ttl_seconds, json.dumps(value))
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                logger.warning("Disabling Redis cache due to connection failure.")
                self.redis_client = None

    async def invalidate(self, key: str):
        if key in self.memory_cache:
            del self.memory_cache[key]
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
            except Exception:
                pass

    async def clear_all(self):
        self.memory_cache.clear()
        if self.redis_client:
            try:
                await self.redis_client.flushdb()
            except Exception:
                pass

cache_service = CacheService()
