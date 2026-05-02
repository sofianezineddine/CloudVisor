"""Circuit breaker pattern for cloud API resilience."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CircuitState(Enum):
    """States of the circuit breaker."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failing, requests are rejected immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerMetrics:
    """Metrics tracked by the circuit breaker."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    state_changed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def error_rate(self) -> float:
        """Calculate current error rate (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def success_rate(self) -> float:
        """Calculate current success rate (0.0 to 1.0)."""
        return 1.0 - self.error_rate


class CircuitBreaker:
    """
    Circuit breaker for cloud API calls.

    Prevents cascading failures by stopping requests when error rate exceeds threshold.
    Automatically transitions between CLOSED → OPEN → HALF_OPEN → CLOSED states.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: float = 0.5,  # 50% error rate
        failure_window_seconds: int = 300,  # 5 minutes
        recovery_timeout_seconds: int = 60,  # 1 minute before trying again
        min_requests_for_threshold: int = 10,  # Need at least 10 requests to trigger
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name of the circuit breaker (for logging)
            failure_threshold: Error rate threshold (0.0-1.0) to open circuit
            failure_window_seconds: Time window for calculating error rate
            recovery_timeout_seconds: Time to wait before transitioning to HALF_OPEN
            min_requests_for_threshold: Minimum requests needed before checking threshold
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.failure_window_seconds = failure_window_seconds
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.min_requests_for_threshold = min_requests_for_threshold

        self._state = CircuitState.CLOSED
        self._metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics."""
        return self._metrics

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: Any exception raised by func
        """
        async with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.OPEN:
                self._metrics.rejected_requests += 1
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Error rate: {self._metrics.error_rate:.1%}. "
                    f"Requests rejected until recovery timeout."
                )

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise

    def _check_state_transition(self) -> None:
        """Check if state should transition based on metrics and time."""
        now = datetime.utcnow()
        time_in_state = (now - self._metrics.state_changed_at).total_seconds()

        if self._state == CircuitState.CLOSED:
            # Check if we should open the circuit
            if (
                self._metrics.total_requests >= self.min_requests_for_threshold
                and self._metrics.error_rate >= self.failure_threshold
            ):
                self._transition_to(CircuitState.OPEN, now)
                logger.warning(
                    f"Circuit breaker '{self.name}' opened. "
                    f"Error rate: {self._metrics.error_rate:.1%} "
                    f"({self._metrics.failed_requests}/{self._metrics.total_requests} requests)"
                )

        elif self._state == CircuitState.OPEN:
            # Check if we should try recovery
            if time_in_state >= self.recovery_timeout_seconds:
                self._transition_to(CircuitState.HALF_OPEN, now)
                logger.info(
                    f"Circuit breaker '{self.name}' transitioning to HALF_OPEN. "
                    f"Testing recovery..."
                )

        elif self._state == CircuitState.HALF_OPEN:
            # In HALF_OPEN, we allow requests through. If they succeed, close.
            # If they fail, reopen. This is handled in _record_success/_record_failure.
            pass

    def _transition_to(self, new_state: CircuitState, now: datetime) -> None:
        """Transition to a new state and reset metrics."""
        old_state = self._state
        self._state = new_state
        self._metrics.state_changed_at = now

        # Reset metrics on state change
        if new_state == CircuitState.HALF_OPEN:
            # Keep some metrics for diagnostics, but reset counters for recovery test
            self._metrics.total_requests = 0
            self._metrics.successful_requests = 0
            self._metrics.failed_requests = 0
            self._metrics.rejected_requests = 0

        logger.info(f"Circuit breaker '{self.name}': {old_state.value} → {new_state.value}")

    async def _record_success(self) -> None:
        """Record a successful request."""
        async with self._lock:
            self._metrics.total_requests += 1
            self._metrics.successful_requests += 1
            self._metrics.last_success_time = datetime.utcnow()

            # If in HALF_OPEN and we got a success, close the circuit
            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.CLOSED, datetime.utcnow())
                logger.info(
                    f"Circuit breaker '{self.name}' recovered and closed. "
                    f"Service is healthy again."
                )

    async def _record_failure(self) -> None:
        """Record a failed request."""
        async with self._lock:
            self._metrics.total_requests += 1
            self._metrics.failed_requests += 1
            self._metrics.last_failure_time = datetime.utcnow()

            # If in HALF_OPEN and we got a failure, reopen the circuit
            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN, datetime.utcnow())
                logger.warning(
                    f"Circuit breaker '{self.name}' recovery failed. "
                    f"Reopening circuit. Service still unhealthy."
                )

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._metrics = CircuitBreakerMetrics()
        logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")

    def get_status(self) -> dict[str, Any]:
        """Get current status for monitoring/debugging."""
        return {
            "name": self.name,
            "state": self._state.value,
            "error_rate": f"{self._metrics.error_rate:.1%}",
            "success_rate": f"{self._metrics.success_rate:.1%}",
            "total_requests": self._metrics.total_requests,
            "successful_requests": self._metrics.successful_requests,
            "failed_requests": self._metrics.failed_requests,
            "rejected_requests": self._metrics.rejected_requests,
            "last_failure_time": self._metrics.last_failure_time.isoformat()
            if self._metrics.last_failure_time
            else None,
            "last_success_time": self._metrics.last_success_time.isoformat()
            if self._metrics.last_success_time
            else None,
            "state_changed_at": self._metrics.state_changed_at.isoformat(),
        }


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open and request is rejected."""

    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        name: str,
        failure_threshold: float = 0.5,
        failure_window_seconds: int = 300,
        recovery_timeout_seconds: int = 60,
        min_requests_for_threshold: int = 10,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker by name."""
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    failure_window_seconds=failure_window_seconds,
                    recovery_timeout_seconds=recovery_timeout_seconds,
                    min_requests_for_threshold=min_requests_for_threshold,
                )
            return self._breakers[name]

    async def get(self, name: str) -> CircuitBreaker | None:
        """Get a circuit breaker by name."""
        async with self._lock:
            return self._breakers.get(name)

    async def get_all_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers."""
        async with self._lock:
            return {name: breaker.get_status() for name, breaker in self._breakers.items()}

    async def reset(self, name: str) -> None:
        """Reset a specific circuit breaker."""
        async with self._lock:
            if name in self._breakers:
                self._breakers[name].reset()

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        async with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()


# Global registry
_circuit_breaker_registry = CircuitBreakerRegistry()


async def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    return _circuit_breaker_registry
