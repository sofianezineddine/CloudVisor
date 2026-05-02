"""Unit tests for the circuit breaker."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


class TestCircuitBreaker:
    def _make_breaker(self, failure_threshold=0.5, window_seconds=60, recovery_timeout=30):
        from app.services.circuit_breaker import CircuitBreaker
        return CircuitBreaker(
            name="test",
            failure_threshold=failure_threshold,
            window_seconds=window_seconds,
            recovery_timeout=recovery_timeout,
        )

    def test_initial_state_is_closed(self):
        cb = self._make_breaker()
        assert cb.state == "CLOSED"

    def test_record_success_stays_closed(self):
        cb = self._make_breaker()
        cb.record_success()
        assert cb.state == "CLOSED"

    def test_opens_after_threshold_failures(self):
        cb = self._make_breaker(failure_threshold=0.5, window_seconds=60)
        # Record enough failures to exceed threshold
        for _ in range(6):
            cb.record_failure()
        for _ in range(4):
            cb.record_success()
        # 6 failures / 10 total = 60% > 50% threshold
        assert cb.state == "OPEN"

    def test_open_circuit_raises(self):
        from app.services.circuit_breaker import CircuitBreakerOpenException
        cb = self._make_breaker(failure_threshold=0.1)
        for _ in range(10):
            cb.record_failure()
        assert cb.state == "OPEN"
        with pytest.raises(CircuitBreakerOpenException):
            cb.check()

    def test_closed_circuit_does_not_raise(self):
        cb = self._make_breaker()
        cb.check()  # should not raise

    def test_metrics_tracked(self):
        cb = self._make_breaker()
        cb.record_success()
        cb.record_success()
        cb.record_failure()
        assert cb.total_calls >= 3


class TestCircuitBreakerRegistry:
    def test_get_or_create(self):
        from app.services.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        cb1 = registry.get_or_create("svc-a")
        cb2 = registry.get_or_create("svc-a")
        assert cb1 is cb2

    def test_different_names_different_breakers(self):
        from app.services.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        cb1 = registry.get_or_create("svc-a")
        cb2 = registry.get_or_create("svc-b")
        assert cb1 is not cb2
