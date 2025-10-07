"""Rate limiting using token bucket algorithm with Redis or in-memory fallback."""

import time
from typing import Optional
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class TokenBucket:
    """In-memory token bucket for rate limiting."""
    
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    lock: Lock = field(default_factory=Lock, init=False)
    
    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.time()
    
    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            bool: True if tokens were consumed, False if insufficient
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_time(self, tokens: int = 1) -> float:
        """
        Calculate time to wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            float: Seconds to wait
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                return 0.0
            shortage = tokens - self.tokens
            return shortage / self.refill_rate


class RateLimiter:
    """
    Rate limiter with Redis support and in-memory fallback.
    
    Uses token bucket algorithm with jitter to prevent thundering herd.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 10,
        redis_client: Optional[Any] = None,
        key_prefix: str = "rate_limit"
    ):
        self.requests_per_minute = requests_per_minute
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        
        # In-memory fallback
        refill_rate = requests_per_minute / 60.0  # tokens per second
        self.local_bucket = TokenBucket(
            capacity=requests_per_minute,
            refill_rate=refill_rate
        )
    
    def acquire(self, key: str = "default", tokens: int = 1) -> bool:
        """
        Try to acquire tokens for rate limiting.
        
        Args:
            key: Identifier for the rate limit bucket
            tokens: Number of tokens to consume
            
        Returns:
            bool: True if acquired, False if rate limited
        """
        # For MVP, use local bucket only
        # TODO: Implement Redis-based rate limiting when REDIS_ENABLED=true
        return self.local_bucket.consume(tokens)
    
    def wait_time(self, key: str = "default", tokens: int = 1) -> float:
        """
        Get time to wait before tokens are available.
        
        Args:
            key: Identifier for the rate limit bucket
            tokens: Number of tokens needed
            
        Returns:
            float: Seconds to wait
        """
        return self.local_bucket.wait_time(tokens)
    
    def add_jitter(self, base_delay: float, max_jitter: float = 0.1) -> float:
        """
        Add random jitter to a delay to prevent thundering herd.
        
        Uses secrets module for cryptographic-grade randomness.
        
        Args:
            base_delay: Base delay in seconds
            max_jitter: Maximum jitter as fraction of base_delay
            
        Returns:
            float: Delay with jitter added
        """
        import secrets
        # Generate cryptographically secure random float
        random_bytes = secrets.randbits(32)
        normalized = random_bytes / (2**32)  # Convert to 0-1 range
        jitter = normalized * base_delay * max_jitter
        return base_delay + jitter

