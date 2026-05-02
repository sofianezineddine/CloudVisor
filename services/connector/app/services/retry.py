"""Retry logic with exponential backoff and jitter for cloud API calls."""

import asyncio
import logging
import random
from functools import wraps
from typing import Any, Callable, TypeVar, cast

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 5,
        initial_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts (not including initial attempt)
            initial_delay_seconds: Initial delay before first retry
            max_delay_seconds: Maximum delay between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.initial_delay_seconds = initial_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_delay * (base ^ attempt)
        delay = self.initial_delay_seconds * (self.exponential_base ** attempt)

        # Cap at max delay
        delay = min(delay, self.max_delay_seconds)

        # Add jitter: random value between 0 and delay
        if self.jitter:
            delay = delay * random.uniform(0.5, 1.0)

        return delay


class RetryableException(Exception):
    """Base exception for retryable errors."""

    pass


class RateLimitException(RetryableException):
    """Raised when rate limit (429) is encountered."""

    def __init__(self, retry_after_seconds: float | None = None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limited. Retry after: {retry_after_seconds}s")


class TemporaryException(RetryableException):
    """Raised for temporary errors (5xx, timeouts, connection errors)."""

    pass


def retry_async(
    config: RetryConfig | None = None,
    retryable_exceptions: tuple[type[Exception], ...] = (
        RetryableException,
        TimeoutError,
        ConnectionError,
    ),
) -> Callable[[F], F]:
    """
    Decorator for async functions to add retry logic with exponential backoff.

    Args:
        config: RetryConfig instance (uses defaults if None)
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorated async function
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except RateLimitException as e:
                    # Handle rate limit with Retry-After header
                    if attempt < config.max_retries:
                        delay = e.retry_after_seconds or config.calculate_delay(attempt)
                        logger.warning(
                            f"{func.__name__} rate limited. "
                            f"Retrying after {delay:.2f}s (attempt {attempt + 1}/{config.max_retries + 1})"
                        )
                        await asyncio.sleep(delay)
                        last_exception = e
                        continue
                    raise
                except retryable_exceptions as e:
                    if attempt < config.max_retries:
                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            f"{func.__name__} failed with {type(e).__name__}: {str(e)[:100]}. "
                            f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{config.max_retries + 1})"
                        )
                        await asyncio.sleep(delay)
                        last_exception = e
                        continue
                    raise
                except Exception as e:
                    # Non-retryable exception
                    logger.error(f"{func.__name__} failed with non-retryable error: {type(e).__name__}: {str(e)[:100]}")
                    raise

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed after {config.max_retries + 1} attempts")

        return cast(F, wrapper)

    return decorator


def retry_sync(
    config: RetryConfig | None = None,
    retryable_exceptions: tuple[type[Exception], ...] = (
        RetryableException,
        TimeoutError,
        ConnectionError,
    ),
) -> Callable[[F], F]:
    """
    Decorator for sync functions to add retry logic with exponential backoff.

    Args:
        config: RetryConfig instance (uses defaults if None)
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitException as e:
                    if attempt < config.max_retries:
                        delay = e.retry_after_seconds or config.calculate_delay(attempt)
                        logger.warning(
                            f"{func.__name__} rate limited. "
                            f"Retrying after {delay:.2f}s (attempt {attempt + 1}/{config.max_retries + 1})"
                        )
                        import time
                        time.sleep(delay)
                        last_exception = e
                        continue
                    raise
                except retryable_exceptions as e:
                    if attempt < config.max_retries:
                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            f"{func.__name__} failed with {type(e).__name__}: {str(e)[:100]}. "
                            f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{config.max_retries + 1})"
                        )
                        import time
                        time.sleep(delay)
                        last_exception = e
                        continue
                    raise
                except Exception as e:
                    logger.error(f"{func.__name__} failed with non-retryable error: {type(e).__name__}: {str(e)[:100]}")
                    raise

            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed after {config.max_retries + 1} attempts")

        return cast(F, wrapper)

    return decorator
