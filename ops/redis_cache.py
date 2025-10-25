"""Redis cache for JD signal extraction results."""

import json
import os

from schemas.models import JDSignals


class JDSignalCache:
    """Redis cache for JD parsing results to avoid redundant LLM calls."""
    
    def __init__(self, redis_url: str | None = None, ttl: int = 3600):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (defaults to env var REDIS_URL)
            ttl: Time-to-live in seconds (defaults to env var JD_CACHE_TTL)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.ttl = int(os.getenv("JD_CACHE_TTL", str(ttl)))
        self._client = None
        
    def _get_client(self):
        """Get Redis client with lazy initialization."""
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                self._client.ping()
            except Exception as e:
                from ops.logging import logger
                logger.warn(
                    stage="redis_cache",
                    msg=f"Redis connection failed, using no-op cache: {e}",
                    redis_url=self.redis_url
                )
                self._client = None
        return self._client
    
    def get(self, jd_hash: str) -> JDSignals | None:
        """
        Get cached JD signals by hash.
        
        Args:
            jd_hash: Hash of the JD text
            
        Returns:
            JDSignals if found in cache, None otherwise
        """
        client = self._get_client()
        if client is None:
            return None
            
        try:
            cached_data = client.get(f"jd_signals:{jd_hash}")
            if cached_data:
                data = json.loads(cached_data)
                return JDSignals(**data)
        except Exception as e:
            from ops.logging import logger
            logger.warn(
                stage="redis_cache",
                msg=f"Failed to get cached JD signals: {e}",
                jd_hash=jd_hash
            )
        return None
    
    def set(self, jd_hash: str, signals: JDSignals, ttl: int | None = None) -> bool:
        """
        Cache JD signals by hash.
        
        Args:
            jd_hash: Hash of the JD text
            signals: JDSignals object to cache
            ttl: Time-to-live override (uses instance default if None)
            
        Returns:
            True if successfully cached, False otherwise
        """
        client = self._get_client()
        if client is None:
            return False
            
        try:
            cache_ttl = ttl if ttl is not None else self.ttl
            data = signals.model_dump()
            client.setex(
                f"jd_signals:{jd_hash}",
                cache_ttl,
                json.dumps(data)
            )
            return True
        except Exception as e:
            from ops.logging import logger
            logger.warn(
                stage="redis_cache",
                msg=f"Failed to cache JD signals: {e}",
                jd_hash=jd_hash
            )
            return False
    
    def clear(self, jd_hash: str) -> bool:
        """
        Clear cached JD signals by hash.
        
        Args:
            jd_hash: Hash of the JD text
            
        Returns:
            True if successfully cleared, False otherwise
        """
        client = self._get_client()
        if client is None:
            return False
            
        try:
            return bool(client.delete(f"jd_signals:{jd_hash}"))
        except Exception as e:
            from ops.logging import logger
            logger.warn(
                stage="redis_cache",
                msg=f"Failed to clear cached JD signals: {e}",
                jd_hash=jd_hash
            )
            return False


# Global cache instance
_global_cache: JDSignalCache | None = None


def get_jd_cache() -> JDSignalCache:
    """Get global JD cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = JDSignalCache()
    return _global_cache
