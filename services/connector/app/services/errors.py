"""Connector service error handling."""


class ConnectorError(Exception):
    """Base error for connector service."""
    pass


class AuthError(ConnectorError):
    """Authentication error with cloud provider."""
    pass


class RateLimitError(ConnectorError):
    """Rate limit exceeded."""
    pass


class CloudAPIError(ConnectorError):
    """Cloud provider API error."""
    pass


class ErrorTracker:
    """Track and manage errors for an account."""

    def __init__(self):
        self._errors = []

    def record(self, error: Exception):
        self._errors.append(error)

    @property
    def count(self) -> int:
        return len(self._errors)

    def clear(self):
        self._errors.clear()


def with_retry(func, max_retries=3, base_delay=1.0):
    """Simple retry wrapper."""
    import time
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            time.sleep(base_delay * (2 ** attempt))
    raise last_error


def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay."""
    import random
    delay = min(base_delay * (2 ** attempt), max_delay)
    return delay * (0.5 + random.random() * 0.5)
