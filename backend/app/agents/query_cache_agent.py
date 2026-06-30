import hashlib
import json
import logging
from typing import Dict, Any, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class QueryCacheAgent:
    def __init__(self):
        self.redis_client = None
        self.in_memory_cache: Dict[str, str] = {}
        self.redis_enabled = False
        
        try:
            import redis
            # Attempt to connect to Redis
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=0,
                socket_timeout=2.0
            )
            # Ping to verify connection
            self.redis_client.ping()
            self.redis_enabled = True
            logger.info("QueryCacheAgent: Successfully connected to Redis.")
        except Exception as e:
            logger.warning(f"QueryCacheAgent: Redis is unavailable ({e}). Falling back to In-Memory cache.")
            self.redis_client = None
            self.redis_enabled = False

    def _get_hash(self, tenant_id: int, query: str) -> str:
        # Preprocess query to reduce variations
        normalized = query.strip().lower()
        key_str = f"tenant:{tenant_id}:query:{normalized}"
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    async def get(self, tenant_id: int, query: str) -> Optional[Dict[str, Any]]:
        query_hash = self._get_hash(tenant_id, query)
        
        if self.redis_enabled and self.redis_client:
            try:
                cached_data = self.redis_client.get(query_hash)
                if cached_data:
                    logger.info(f"QueryCacheAgent: Cache hit (Redis) for: {query}")
                    return json.loads(cached_data.decode("utf-8"))
            except Exception as e:
                logger.error(f"QueryCacheAgent Redis get failed: {e}")
        
        # In-memory fallback
        if query_hash in self.in_memory_cache:
            logger.info(f"QueryCacheAgent: Cache hit (In-Memory) for: {query}")
            return json.loads(self.in_memory_cache[query_hash])
            
        return None

    async def set(self, tenant_id: int, query: str, sql: str, result: Any, expire_seconds: int = 3600):
        query_hash = self._get_hash(tenant_id, query)
        cache_value = {
            "query": query,
            "sql": sql,
            "result": result
        }
        serialized = json.dumps(cache_value)
        
        if self.redis_enabled and self.redis_client:
            try:
                self.redis_client.setex(query_hash, expire_seconds, serialized)
                logger.info(f"QueryCacheAgent: Saved result in Redis for: {query}")
                return
            except Exception as e:
                logger.error(f"QueryCacheAgent Redis set failed: {e}")
                
        # Store in in-memory dict
        self.in_memory_cache[query_hash] = serialized
        logger.info(f"QueryCacheAgent: Saved result in In-Memory Cache for: {query}")

    async def invalidate_tenant_cache(self, tenant_id: int):
        # Clears all keys for a tenant
        if self.redis_enabled and self.redis_client:
            try:
                # Find keys matching tenant prefix
                pattern = f"tenant:{tenant_id}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                logger.info(f"QueryCacheAgent: Invalidated Redis cache for tenant {tenant_id}.")
            except Exception as e:
                logger.error(f"QueryCacheAgent Redis invalidate failed: {e}")
                
        # In-memory clear
        keys_to_del = [k for k in self.in_memory_cache.keys() if k.startswith(hashlib.sha256(f"tenant:{tenant_id}:".encode()).hexdigest()[:10])]
        for k in keys_to_del:
            self.in_memory_cache.pop(k, None)
        logger.info(f"QueryCacheAgent: Invalidated In-Memory cache for tenant {tenant_id}.")

query_cache_agent = QueryCacheAgent()
