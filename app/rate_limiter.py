import threading
import time
from typing import Deque
from collections import deque

from fastapi import HTTPException

from .config import GLOBAL_RATE_LIMIT_PER_MINUTE


class GlobalRateLimiter:
    def __init__(self, max_per_minute: int) -> None:
        self.max_per_minute = max_per_minute
        self._lock = threading.Lock()
        self._timestamps: Deque[float] = deque()

    def acquire(self) -> None:
        now = time.time()
        one_minute_ago = now - 60
        with self._lock:
            while self._timestamps and self._timestamps[0] < one_minute_ago:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.max_per_minute:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
            self._timestamps.append(now)


global_rate_limiter = GlobalRateLimiter(GLOBAL_RATE_LIMIT_PER_MINUTE)


def rate_limit_dependency() -> None:
    global_rate_limiter.acquire()


