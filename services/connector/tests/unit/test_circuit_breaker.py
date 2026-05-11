"""Unit tests for the circuit breaker.

Tests use the actual CircuitBreaker API:
  - ``await breaker.call(async_func)`` to execute through the breaker
  - ``breaker.state`` (CircuitState enum) to inspect state
  - ``breaker.get_status()`` for metrics dict
  - ``breaker.reset()`` to manually reset
  - ``CircuitBreakerOpenException`` raised when circuit is OPEN

The registry's ``get_or_create`` is async — tests must await it.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""

    def _make_breaker(
        self,
        failure_threshold: float = 0.5,
        failure_window_seconds: int = 300,
        recovery_timeout_seconds: int = 60,
        min_requests_for_threshold: int = 2,
    ):
        from app.services.circuit_breaker import CircuitBreaker
        return CircuitBreaker(
            name="test",
            failure_threshold=failure_threshold,
            failure_window_seconds=failure_window_seconds,
            recovery_timeout_seconds=recovery_timeout_seconds,
            min_requests_for_threshold=min_requests_for_threshold,
        )

    def test_initial_state_is_closed(self):
        from app.services.circuit_breaker import CircuitState
        cb = self._make_breaker()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call_stays_closed(self):
        from app.services.circuit_breaker import CircuitState
        cb = self._make_breaker()

        async def ok():
            return "ok"

        result = await cb.call(ok)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        """Circuit opens when error rate exceeds threshold after min_requests.

        The state transition check runs at the START of each call (before the
        request is counted). So after N failures, the circuit opens on the
        NEXT call attempt — not during the Nth failure itself.
        """
        from app.services.circuit_breaker import CircuitState, CircuitBreakerOpenException
        # min_requests=2, threshold=0.5 → opens after 2 failures / 2 total = 100%
        cb = self._make_breaker(failure_threshold=0.5, min_requests_for_threshold=2)

        async def fail():
            raise ValueError("boom")

        # Record 2 failures to meet min_requests threshold
        for _ in range(2):
            try:
                await cb.call(fail)
            except ValueError:
                pass

        # The circuit should now open on the next call attempt
        async def ok():
            return "ok"

        try:
            await cb.call(ok)
        except CircuitBreakerOpenException:
            pass  # Expected — circuit opened

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_raises_circuit_breaker_exception(self):
        from app.services.circuit_breaker import CircuitState, CircuitBreakerOpenException
        cb = self._make_breaker(failure_threshold=0.1, min_requests_for_threshold=1)

        async def fail():
            raise ValueError("boom")

        # One failure meets min_requests=1 at 100% error rate > 10% threshold
        try:
            await cb.call(fail)
        except ValueError:
            pass

        # Next call should trigger the open check and raise CircuitBreakerOpenException
        async def ok():
            return "ok"

        with pytest.raises(CircuitBreakerOpenException):
            await cb.call(ok)

    @pytest.mark.asyncio
    async def test_closed_circuit_does_not_raise_on_success(self):
        cb = self._make_breaker()

        async def ok():
            return 42

        result = await cb.call(ok)
        assert result == 42

    @pytest.mark.asyncio
    async def test_metrics_tracked(self):
        cb = self._make_breaker()

        async def ok():
            return "ok"

        async def fail():
            raise ValueError("boom")

        await cb.call(ok)
        await cb.call(ok)
        try:
            await cb.call(fail)
        except ValueError:
            pass

        status = cb.get_status()
        assert status["name"] == "test"
        assert "state" in status
        assert "error_rate" in status
        assert "total_requests" in status
        assert status["total_requests"] == 3

    def test_reset_clears_metrics(self):
        from app.services.circuit_breaker import CircuitState
        cb = self._make_breaker()
        # Manually corrupt state
        cb._metrics.failed_requests = 10
        cb._metrics.total_requests = 10
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._metrics.total_requests == 0
        assert cb._metrics.failed_requests == 0

    def test_get_status_returns_dict(self):
        cb = self._make_breaker()
        s = cb.get_status()
        assert isinstance(s, dict)
        assert s["name"] == "test"
        assert "state" in s
        assert "error_rate" in s
        assert "success_rate" in s


class TestCircuitBreakerRegistry:
    """Tests for the CircuitBreakerRegistry."""

    @pytest.mark.asyncio
    async def test_get_or_create_returns_same_instance(self):
        from app.services.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        cb1 = await registry.get_or_create("svc-a")
        cb2 = await registry.get_or_create("svc-a")
        assert cb1 is cb2

    @pytest.mark.asyncio
    async def test_different_names_different_breakers(self):
        from app.services.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        cb1 = await registry.get_or_create("svc-a")
        cb2 = await registry.get_or_create("svc-b")
        assert cb1 is not cb2

    @pytest.mark.asyncio
    async def test_get_returns_none_for_unknown(self):
        from app.services.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        result = await registry.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_status(self):
        from app.services.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        await registry.get_or_create("svc-x")
        await registry.get_or_create("svc-y")
        all_status = await registry.get_all_status()
        assert "svc-x" in all_status
        assert "svc-y" in all_status

    @pytest.mark.asyncio
    async def test_reset_specific_breaker(self):
        from app.services.circuit_breaker import CircuitBreakerRegistry, CircuitState
        registry = CircuitBreakerRegistry()
        cb = await registry.get_or_create("svc-reset")
        cb._metrics.failed_requests = 99
        await registry.reset("svc-reset")
        assert cb.state == CircuitState.CLOSED
        assert cb._metrics.failed_requests == 0
