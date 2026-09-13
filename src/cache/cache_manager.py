"""Multi-tier cache manager with Redis integration and in-memory LRU/TTL fallback."""
from __future__ import annotations

import hashlib
import json
import time
import threading
from typing import Dict, Any, Optional, List, Tuple

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("cache_manager")

class CacheManager:
    """Provides high-performance query and embedding caching with TTL expiration."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_client = None
        self._redis_available = False
        self._lock = threading.Lock()

        # In-memory fallback cache stores: {key: (data_dict, expire_timestamp)}
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0

        self._init_redis()

    def _init_redis(self) -> None:
        """Attempts connection to Redis backend."""
        try:
            import redis
            client = redis.from_url(self.redis_url, socket_timeout=1.0)
            client.ping()
            self._redis_client = client
            self._redis_available = True
            logger.info(f"Connected to Redis cache backend at: {self.redis_url}")
        except Exception as e:
            logger.info(f"Redis unavailable ({e}). Using in-memory thread-safe cache fallback.")
            self._redis_client = None
            self._redis_available = False

    def _hash_key(self, prefix: str, raw_key: str, namespace: str = "default") -> str:
        """Generates deterministic SHA-256 cache key."""
        hashed = hashlib.sha256(raw_key.strip().lower().encode("utf-8")).hexdigest()
        return f"docuchat:{namespace}:{prefix}:{hashed}"

    def get_query(self, query: str, namespace: str = "default") -> Optional[Dict[str, Any]]:
        """Retrieves cached response object for a given query string."""
        cache_key = self._hash_key("query", query, namespace)

        if self._redis_available and self._redis_client:
            try:
                val = self._redis_client.get(cache_key)
                if val:
                    self._hits += 1
                    logger.info(f"Redis query cache hit for: '{query[:40]}...'")
                    return json.loads(val.decode("utf-8"))
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # In-memory check
        with self._lock:
            if cache_key in self._memory_cache:
                data, expire_at = self._memory_cache[cache_key]
                if time.time() < expire_at:
                    self._hits += 1
                    logger.info(f"In-memory query cache hit for: '{query[:40]}...'")
                    return data
                else:
                    # Expired entry
                    del self._memory_cache[cache_key]

            self._misses += 1
            return None

    def set_query(
        self,
        query: str,
        response_data: Dict[str, Any],
        ttl_seconds: int = 3600,
        namespace: str = "default"
    ) -> None:
        """Caches query response with a specified Time-To-Live (TTL)."""
        cache_key = self._hash_key("query", query, namespace)

        if self._redis_available and self._redis_client:
            try:
                self._redis_client.setex(cache_key, ttl_seconds, json.dumps(response_data))
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # In-memory write
        with self._lock:
            # Enforce max in-memory capacity (10,000 items)
            if len(self._memory_cache) > 10_000:
                # Evict oldest 1,000 items
                keys_to_remove = list(self._memory_cache.keys())[:1000]
                for k in keys_to_remove:
                    self._memory_cache.pop(k, None)

            self._memory_cache[cache_key] = (response_data, time.time() + ttl_seconds)

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Retrieves cached embedding vector for a piece of text."""
        cache_key = self._hash_key("emb", text, "embeddings")

        if self._redis_available and self._redis_client:
            try:
                val = self._redis_client.get(cache_key)
                if val:
                    return json.loads(val.decode("utf-8"))
            except Exception:
                pass

        with self._lock:
            if cache_key in self._memory_cache:
                vector, expire_at = self._memory_cache[cache_key]
                if time.time() < expire_at:
                    return vector
                del self._memory_cache[cache_key]
        return None

    def set_embedding(self, text: str, vector: List[float], ttl_seconds: int = 86400) -> None:
        """Stores embedding vector in cache."""
        cache_key = self._hash_key("emb", text, "embeddings")

        if self._redis_available and self._redis_client:
            try:
                self._redis_client.setex(cache_key, ttl_seconds, json.dumps(vector))
                return
            except Exception:
                pass

        with self._lock:
            self._memory_cache[cache_key] = (vector, time.time() + ttl_seconds)

    def get_stats(self) -> Dict[str, Any]:
        """Returns cache efficiency metrics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total > 0 else 0.0
        return {
            "backend": "redis" if self._redis_available else "in_memory",
            "hits": self._hits,
            "misses": self._misses,
            "total_lookups": total,
            "hit_rate": round(hit_rate, 3),
            "memory_keys_count": len(self._memory_cache),
        }

    def clear(self) -> None:
        """Clears all in-memory cache entries and counters."""
        with self._lock:
            self._memory_cache.clear()
            self._hits = 0
            self._misses = 0

# Global cache manager instance
cache_manager = CacheManager()
