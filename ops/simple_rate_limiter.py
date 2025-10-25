#!/usr/bin/env python3
"""
Simple Custom Rate Limiter for FastAPI
Fallback implementation when slowapi doesn't work
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request


class SimpleRateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests: dict[str, list] = defaultdict(list)
        self.cleanup_interval = 60  # Clean up every minute
        self.last_cleanup = time.time()
    
    def _cleanup_old_requests(self):
        """Remove requests older than 1 minute."""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            for ip in list(self.requests.keys()):
                self.requests[ip] = [
                    req_time for req_time in self.requests[ip] 
                    if now - req_time < 60
                ]
                if not self.requests[ip]:
                    del self.requests[ip]
            self.last_cleanup = now
    
    def is_allowed(self, ip: str, limit: int = 5) -> tuple[bool, str]:
        """Check if request is allowed based on rate limit."""
        self._cleanup_old_requests()
        
        now = time.time()
        recent_requests = [
            req_time for req_time in self.requests[ip]
            if now - req_time < 60
        ]
        
        if len(recent_requests) >= limit:
            return False, f"Rate limit exceeded: {len(recent_requests)}/{limit} requests per minute"
        
        self.requests[ip].append(now)
        return True, "Allowed"
    
    def get_status(self, ip: str) -> dict[str, int]:
        """Get current rate limit status for an IP."""
        self._cleanup_old_requests()
        now = time.time()
        recent_requests = [
            req_time for req_time in self.requests[ip]
            if now - req_time < 60
        ]
        return {
            "requests_last_minute": len(recent_requests),
            "total_ips_tracked": len(self.requests)
        }


# Global rate limiter instance
rate_limiter = SimpleRateLimiter()


def check_rate_limit(request: Request, limit: int = 5) -> None:
    """Check rate limit and raise exception if exceeded."""
    client_ip = request.client.host if request.client else "unknown"
    
    is_allowed, message = rate_limiter.is_allowed(client_ip, limit)
    
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": message,
                "retry_after": 60
            }
        )


def get_rate_limit_status(request: Request) -> dict[str, int]:
    """Get rate limit status for an IP."""
    client_ip = request.client.host if request.client else "unknown"
    return rate_limiter.get_status(client_ip)
