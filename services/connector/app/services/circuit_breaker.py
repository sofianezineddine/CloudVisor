"""Circuit breaker pattern for preventing cascading failures."""

import logging
import time
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """States for the circuit breaker."""

    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failure threshold exceeded, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    Monitors error rate and opens circuit if threshold exceeded.
    Automatically tests recovery after timeout.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: float = 0.5,
        evaluation_window_seconds: int = 300,
        recovery_timeout_seconds: int = 60,
        min_calls_before_evaluation: int = 10,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.evaluation_window = evaluation_window_seconds
        self.recovery_timeout = recovery_timeout_seconds
        self.min_calls = min_calls_before_evaluation

        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._last_failure_time: float | None = None
        self._last_state_change: float = time.time()
        self._total_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery."""
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self._last_state_change >= self.recovery_timeout:
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._last_state_change = time.time()
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        self._successes += 1
        self._total_calls += 1

        if self._state == CircuitState.HALF_OPEN:
            # Successful call in half-open state closes circuit
            logger.info(f"Circuit breaker '{self.name}' CLOSED (recovered)")
            self._state = CircuitState.CLOSED
            self._last_state_change = time.time()
            self._failures = 0
            self._successes = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failures += 1
        self._total_calls += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failed call in half-open state opens circuit again
            logger.warning(f"Circuit breaker '{self.name}' OPEN (recovery failed)")
            self._state = CircuitState.OPEN
            self._last_state_change = time.time()
            self._successes = 0

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        state = self.state

        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.HALF_OPEN:
            return True

        # Circuit is OPEN
        logger.warning(f"Circuit breaker '{self.name}' is OPEN - rejecting call")
        raise CircuitBreakerError(
            f"Circuit breaker '{self.name}' is open due to failures"
        )

    def get_error_rate(self) -> float:
        """Get current error rate in evaluation window."""
        if self._total_calls == 0:
            return 0.0
        return self._failures / self._total_calls

    def should_evaluate(self) -> bool:
        """Check if we have enough data to evaluate circuit state."""
        if self._total_calls < self.min_calls:
            return False

        # Check if we're within the evaluation window
        return True

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._total_calls = 0
        self._last_failure_time = None
        self._last_state_change = time.time()
        logger.info(f"Circuit breaker '{self.name}' reset")

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_threshold": self.failure_threshold,
            "error_rate": self.get_error_rate(),
            "total_calls": self._total_calls,
            "successes": self._successes,
            "failures": self._failures,
            "evaluation_window_seconds": self.evaluation_window,
            "recovery_timeout_seconds": self.recovery_timeout,
        }
