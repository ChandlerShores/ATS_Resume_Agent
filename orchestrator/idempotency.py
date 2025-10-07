"""Idempotency management for job execution."""

import json
from typing import Optional, Dict, Any
from pathlib import Path
from ops.hashing import compute_idempotency_key


class IdempotencyCache:
    """
    Simple file-based idempotency cache.
    
    For production, this could be Redis-based.
    """
    
    def __init__(self, cache_dir: str = "out/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for a cache key."""
        return self.cache_dir / f"{key}.json"
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result.
        
        Args:
            key: Idempotency key
            
        Returns:
            Optional[Dict]: Cached result if exists, None otherwise
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def set(self, key: str, value: Dict[str, Any]):
        """
        Store result in cache.
        
        Args:
            key: Idempotency key
            value: Result to cache
        """
        cache_path = self._get_cache_path(key)
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(value, f, indent=2)
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Idempotency key
            
        Returns:
            bool: True if cached result exists
        """
        return self._get_cache_path(key).exists()
    
    def clear(self):
        """Clear all cached results."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()


class IdempotencyManager:
    """Manager for idempotent job execution."""
    
    def __init__(self, cache: Optional[IdempotencyCache] = None):
        self.cache = cache or IdempotencyCache()
    
    def compute_key(
        self,
        job_id: str,
        jd_hash: str,
        bullets: list,
        settings: dict
    ) -> str:
        """
        Compute idempotency key for a job.
        
        Args:
            job_id: Job identifier
            jd_hash: Hash of job description
            bullets: List of bullets
            settings: Job settings
            
        Returns:
            str: Idempotency key
        """
        return compute_idempotency_key(job_id, jd_hash, bullets, settings)
    
    def get_cached_result(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result for idempotency key.
        
        Args:
            key: Idempotency key
            
        Returns:
            Optional[Dict]: Cached result or None
        """
        return self.cache.get(key)
    
    def cache_result(self, key: str, result: Dict[str, Any]):
        """
        Cache a job result.
        
        Args:
            key: Idempotency key
            result: Job result to cache
        """
        self.cache.set(key, result)


# Global idempotency manager
idempotency_manager = IdempotencyManager()

