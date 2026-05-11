"""Unit tests for retry logic.

``retry_async`` is a decorator factory — usage:

    @retry_async(config=RetryConfig(...), retryable_exceptions=(TemporaryException,))
    async def my_func():
        ...

    result = await my_func()
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestRetryConfig:
    def test_default_values(self):
        from app.services.retry import RetryConfig
        cfg = RetryConfig()
        assert cfg.max_retries >= 1
        assert cfg.initial_delay_seconds > 0
        assert cfg.max_delay_seconds >= cfg.initial_delay_seconds

    def test_custom_values(self):
        from app.services.retry import RetryConfig
        cfg = RetryConfig(max_retries=3, initial_delay_seconds=2.0, max_delay_seconds=30.0)
        assert cfg.max_retries == 3
        assert cfg.initial_delay_seconds == 2.0
        assert cfg.max_delay_seconds == 30.0

    def test_calculate_delay_exponential(self):
        from app.services.retry import RetryConfig
        cfg = RetryConfig(
            max_retries=5,
            initial_delay_seconds=1.0,
            max_delay_seconds=60.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert cfg.calculate_delay(0) == 1.0
        assert cfg.calculate_delay(1) == 2.0
        assert cfg.calculate_delay(2) == 4.0

    def test_calculate_delay_capped(self):
        from app.services.retry import RetryConfig
        cfg = RetryConfig(
            max_retries=5,
            initial_delay_seconds=1.0,
            max_delay_seconds=5.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert cfg.calculate_delay(10) == 5.0


class TestRetryAsync:
    """Tests for the retry_async decorator factory."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        from app.services.retry import retry_async, RetryConfig
        call_count = 0

        @retry_async(config=RetryConfig(max_retries=3))
        async def fn():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await fn()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_temporary_error(self):
        from app.services.retry import retry_async, RetryConfig, TemporaryException
        call_count = 0

        @retry_async(
            config=RetryConfig(
                max_retries=5,
                initial_delay_seconds=0.001,
                max_delay_seconds=0.01,
            ),
            retryable_exceptions=(TemporaryException,),
        )
        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TemporaryException("transient")
            return "ok"

        result = await fn()
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        from app.services.retry import retry_async, RetryConfig, TemporaryException

        @retry_async(
            config=RetryConfig(
                max_retries=2,
                initial_delay_seconds=0.001,
                max_delay_seconds=0.01,
            ),
            retryable_exceptions=(TemporaryException,),
        )
        async def fn():
            raise TemporaryException("always fails")

        with pytest.raises(TemporaryException):
            await fn()

    @pytest.mark.asyncio
    async def test_does_not_retry_on_auth_error(self):
        from app.services.retry import retry_async, RetryConfig, TemporaryException
        call_count = 0

        @retry_async(
            config=RetryConfig(
                max_retries=5,
                initial_delay_seconds=0.001,
                max_delay_seconds=0.01,
            ),
            retryable_exceptions=(TemporaryException,),
        )
        async def fn():
            nonlocal call_count
            call_count += 1
            raise PermissionError("auth failed")

        with pytest.raises(PermissionError):
            await fn()
        # PermissionError is not in retryable_exceptions — no retries
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_uses_retry_after(self):
        from app.services.retry import retry_async, RetryConfig, RateLimitException
        call_count = 0

        @retry_async(
            config=RetryConfig(
                max_retries=3,
                initial_delay_seconds=0.001,
                max_delay_seconds=0.01,
            ),
            retryable_exceptions=(RateLimitException,),
        )
        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitException(retry_after_seconds=0.001)
            return "ok"

        result = await fn()
        assert result == "ok"
        assert call_count == 2
