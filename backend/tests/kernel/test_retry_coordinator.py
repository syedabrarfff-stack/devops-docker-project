"""Tests for K1-6: RetryCoordinator — circuit breakers, backoff, escalation."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from app.services.kernel.retry_coordinator import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    MaxRetriesExceededError,
    RetryCoordinator,
)


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_closed_on_success(self):
        cb = CircuitBreaker(name="test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_half_open_after_cooldown(self):
        import time
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_seconds=0.01)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        # allow_request transitions to HALF_OPEN
        assert cb.allow_request() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_jitter_is_non_negative(self):
        coord = RetryCoordinator()
        for _ in range(100):
            delay = coord._jittered_delay(3, 1.0, 30.0)
            assert delay >= 0
            assert delay <= 30.0


class TestRetryCoordinator:
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        coord = RetryCoordinator()
        fn = AsyncMock(return_value="ok")
        result = await coord.execute("svc", fn, max_retries=2)
        assert result == "ok"
        assert fn.await_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        coord = RetryCoordinator()
        fn = AsyncMock(side_effect=[ValueError("fail"), ValueError("fail"), "ok"])

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await coord.execute("svc", fn, max_retries=2)

        assert result == "ok"
        assert fn.await_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        coord = RetryCoordinator()
        fn = AsyncMock(side_effect=RuntimeError("always fails"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MaxRetriesExceededError):
                await coord.execute("svc", fn, max_retries=2)

        assert fn.await_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_circuit_opens_and_fast_fails(self):
        coord = RetryCoordinator()
        cb = coord._get_breaker("svc")
        # threshold=3: the circuit opens exactly when max_retries=2 exhausts
        # (3 total attempts = 3 failures = threshold)
        cb.failure_threshold = 3

        fn = AsyncMock(side_effect=RuntimeError("fail"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MaxRetriesExceededError):
                await coord.execute("svc", fn, max_retries=2)

        # Circuit is now OPEN — next call fast-fails without invoking fn2
        fn2 = AsyncMock(return_value="should not reach")
        with pytest.raises(CircuitOpenError):
            await coord.execute("svc", fn2, max_retries=0)

        fn2.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_breaker_status(self):
        coord = RetryCoordinator()
        _ = coord._get_breaker("api1")
        _ = coord._get_breaker("api2")
        status = coord.breaker_status()
        assert "api1" in status
        assert "api2" in status
        assert status["api1"]["state"] == "CLOSED"

    def test_reset_clears_breaker(self):
        coord = RetryCoordinator()
        cb = coord._get_breaker("svc")
        cb.failure_threshold = 1
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        coord.reset("svc")
        assert cb.state == CircuitState.CLOSED
