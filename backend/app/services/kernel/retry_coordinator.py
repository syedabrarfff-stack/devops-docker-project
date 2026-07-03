"""K1-6: JARVIS Retry Coordinator — circuit breakers, backoff+jitter, escalation.

Every service that calls an external system (AI models, external APIs, AWS)
MUST wrap those calls through this coordinator instead of implementing its own
retry logic. This gives the Kernel unified visibility into failure patterns
and a single lever for circuit breaker state.

Circuit breaker states:
  CLOSED   — normal operation; requests flow through
  OPEN     — failure threshold exceeded; requests fail fast without attempting
  HALF_OPEN — cooldown expired; one probe request allowed to test recovery

Backoff strategy: exponential with full jitter
  delay = min(cap, base * 2^attempt) * random(0, 1)

Usage:
    coordinator = RetryCoordinator()
    result = await coordinator.execute(
        name="openai",
        fn=call_openai,
        max_retries=3,
    )
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

from app.services.kernel.event_bus import get_event_bus

log = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreaker:
    """Per-service circuit breaker state."""
    name: str
    failure_threshold: int = 5          # open after N consecutive failures
    recovery_timeout_seconds: float = 60.0  # wait before HALF_OPEN probe
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: Optional[float] = None   # time.monotonic() when OPEN

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
                log.error(
                    "CircuitBreaker[%s]: OPEN after %d consecutive failures",
                    self.name,
                    self.failure_count,
                )

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - (self.opened_at or 0)
            if elapsed >= self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                log.info("CircuitBreaker[%s]: HALF_OPEN — allowing probe", self.name)
                return True
            return False
        # HALF_OPEN — allow single probe
        return True


class CircuitOpenError(Exception):
    """Raised when a circuit is OPEN and requests are being fast-failed."""


class MaxRetriesExceededError(Exception):
    """Raised after all retry attempts are exhausted."""


class RetryCoordinator:
    """Process-level retry coordinator with per-service circuit breakers.

    Thread/coroutine safe for reading; circuit state updates are best-effort
    (no explicit lock) since the state machine is forgiving of occasional
    concurrent false positives.
    """

    _DEFAULT_BASE_DELAY = 1.0       # seconds
    _DEFAULT_MAX_DELAY = 30.0       # cap on exponential growth
    _DEFAULT_MAX_RETRIES = 3

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def _get_breaker(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name)
        return self._breakers[name]

    def _jittered_delay(self, attempt: int, base: float, cap: float) -> float:
        """Full-jitter exponential backoff: random(0, min(cap, base * 2^attempt))."""
        ceiling = min(cap, base * (2 ** attempt))
        return random.uniform(0, ceiling)

    async def execute(
        self,
        name: str,
        fn: Callable[[], Coroutine[Any, Any, Any]],
        max_retries: int = _DEFAULT_MAX_RETRIES,
        base_delay: float = _DEFAULT_BASE_DELAY,
        max_delay: float = _DEFAULT_MAX_DELAY,
        escalate_after: Optional[int] = None,
    ) -> Any:
        """Execute `fn` with retry + circuit breaker protection.

        Args:
            name:           Service name (e.g. "openai", "stripe", "postgres")
            fn:             Zero-arg async callable to execute.
            max_retries:    Maximum retry attempts (0 = try once, no retries).
            base_delay:     Base delay for exponential backoff (seconds).
            max_delay:      Cap on computed delay (seconds).
            escalate_after: If provided and all retries fail, publish
                            'alert.escalation' event after this many failures.
        """
        breaker = self._get_breaker(name)
        last_exc: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            if not breaker.allow_request():
                log.warning(
                    "RetryCoordinator[%s]: circuit OPEN — fast-failing (attempt %d/%d)",
                    name, attempt + 1, max_retries + 1,
                )
                raise CircuitOpenError(
                    f"Circuit breaker for '{name}' is OPEN. "
                    f"Will retry after {breaker.recovery_timeout_seconds}s cooldown."
                )

            try:
                result = await fn()
                breaker.record_success()
                if attempt > 0:
                    log.info(
                        "RetryCoordinator[%s]: succeeded after %d retries",
                        name, attempt,
                    )
                return result

            except Exception as exc:
                last_exc = exc
                breaker.record_failure()
                log.warning(
                    "RetryCoordinator[%s]: attempt %d/%d failed: %s",
                    name, attempt + 1, max_retries + 1, exc,
                )

                if attempt < max_retries:
                    delay = self._jittered_delay(attempt, base_delay, max_delay)
                    log.debug(
                        "RetryCoordinator[%s]: backing off %.2fs", name, delay
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted
        if escalate_after is not None and breaker.failure_count >= escalate_after:
            await self._escalate(name, last_exc)

        raise MaxRetriesExceededError(
            f"All {max_retries + 1} attempts for '{name}' failed. "
            f"Last error: {last_exc}"
        ) from last_exc

    async def _escalate(self, service_name: str, error: Optional[Exception]) -> None:
        """Publish escalation event to Event Bus (Captain will be notified)."""
        try:
            bus = get_event_bus()
            await bus.emit(
                "alert.escalation",
                payload={
                    "service": service_name,
                    "error": str(error),
                    "circuit_state": self._breakers.get(
                        service_name, CircuitBreaker(service_name)
                    ).state.value,
                },
                source_engine="retry_coordinator",
            )
        except Exception as exc:
            log.error("RetryCoordinator: escalation event failed: %s", exc)

    def breaker_status(self) -> dict[str, dict]:
        """Return all circuit breaker states (for Health Aggregator)."""
        return {
            name: {
                "state": b.state.value,
                "failure_count": b.failure_count,
                "opened_at": b.opened_at,
            }
            for name, b in self._breakers.items()
        }

    def reset(self, name: str) -> None:
        """Manually reset a circuit breaker (for override commands)."""
        if name in self._breakers:
            self._breakers[name].record_success()
            log.info("RetryCoordinator[%s]: manually reset", name)


# Module-level singleton
_coordinator: RetryCoordinator | None = None


def get_retry_coordinator() -> RetryCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = RetryCoordinator()
    return _coordinator
