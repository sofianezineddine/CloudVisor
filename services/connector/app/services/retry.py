"""Exponential backoff retry logic with jitter."""

import asyncio
import logging
import random
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class RetryError(Exception):
    """Raised when all retries are exhausted."""

    def __init__(self, message: str, last_exception: Exception | None = None):
        super().__init__(message)
        self.last_exception = last_exception


def calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool,
) -> float:
    """Calculate delay for current retry attempt."""
    delay = min(base_delay * (exponential_base ** attempt), max_delay)
    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)  # Add 50-100% jitter
    return delay


async def retry_async(
    func: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    retry_config: RetryConfig | None = None,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
    **kwargs: Any,
) -> Any:
    """
    Execute async function with exponential backoff retry.

    Args:
        func: Async function to retry
        *args: Arguments to pass to func
        retry_config: Retry configuration (uses defaults if None)
        retryable_exceptions: Tuple of exceptions that trigger retry (all if None)
        **kwargs: Keyword arguments to pass to func
    """
    config = retry_config or RetryConfig()
    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            # Check if exception is retryable
            if retryable_exceptions and not isinstance(e, retryable_exceptions):
                raise

            # Don't retry on last attempt
            if attempt >= config.max_retries:
                break

            delay = calculate_delay(
                attempt,
                config.base_delay,
                config.max_delay,
                config.exponential_base,
                config.jitter,
            )

            logger.warning(
                f"Retry attempt {attempt + 1}/{config.max_retries} after {delay:.2f}s: {e}"
            )
            await asyncio.sleep(delay)

    raise RetryError(
        f"Exhausted {config.max_retries} retries",
        last_exception=last_exception,
    )
