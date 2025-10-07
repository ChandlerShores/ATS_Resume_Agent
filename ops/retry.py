"""Retry logic with exponential backoff and jitter for resilient external calls."""

import random
import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

T = TypeVar("T")


def exponential_backoff_with_jitter(
    attempt: int, base_delay: float = 1.0, max_delay: float = 30.0, jitter_factor: float = 0.3
) -> float:
    """
    Calculate delay for exponential backoff with jitter.

    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter_factor: Amount of randomness (0.0 to 1.0)

    Returns:
        float: Delay in seconds with jitter applied
    """
    # Exponential backoff: base_delay * 2^attempt
    delay = min(base_delay * (2**attempt), max_delay)

    # Add jitter: random value between (1 - jitter_factor) and (1 + jitter_factor)
    jitter = random.uniform(1 - jitter_factor, 1 + jitter_factor)

    return delay * jitter


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None,
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback called on each retry with (exception, attempt)

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt >= max_retries:
                        # Out of retries, raise the exception
                        raise

                    # Calculate backoff delay
                    delay = exponential_backoff_with_jitter(attempt, base_delay, max_delay)

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt)

                    # Wait before retrying
                    time.sleep(delay)

            # Should never reach here, but raise last exception just in case
            if last_exception:
                raise last_exception

            raise RuntimeError("Retry logic error")

        return wrapper

    return decorator


class RetryableError(Exception):
    """Exception that should trigger a retry."""


class PermanentError(Exception):
    """Exception that should NOT trigger a retry (goes to DLQ immediately)."""
