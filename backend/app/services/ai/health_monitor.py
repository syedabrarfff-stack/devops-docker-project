"""
AI Provider Health Monitor — circuit breaker, latency tracking, failover state.

Circuit breaker states:
  CLOSED   → provider healthy, use normally
  OPEN     → provider failed too many times, skip for COOLDOWN_SECONDS
  HALF_OPEN → cooldown expired, allow one probe request
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3        # consecutive failures before OPEN
COOLDOWN_SECONDS = 300       # 5 minutes before HALF_OPEN probe
LATENCY_WARN_MS = 8000       # 8s — warn but don't trip circuit
LATENCY_TRIP_MS = 20000      # 20s — count as failure for circuit breaker


@dataclass
class ProviderHealth:
    provider: str
    state: str = "CLOSED"           # CLOSED | OPEN | HALF_OPEN
    consecutive_failures: int = 0
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_failure_at: Optional[float] = None
    last_success_at: Optional[float] = None
    last_latency_ms: int = 0
    avg_latency_ms: float = 0.0
    _latency_window: list = field(default_factory=list)

    def record_success(self, latency_ms: int):
        self.total_requests += 1
        self.last_latency_ms = latency_ms
        self._latency_window.append(latency_ms)
        if len(self._latency_window) > 20:
            self._latency_window.pop(0)
        self.avg_latency_ms = sum(self._latency_window) / len(self._latency_window)

        if latency_ms >= LATENCY_TRIP_MS:
            # Technically succeeded but took so long it counts as a failure
            logger.warning(
                "[health] %s: latency %dms >= %dms trip threshold — counting as failure",
                self.provider, latency_ms, LATENCY_TRIP_MS,
            )
            self.total_failures += 1
            self.consecutive_failures += 1
            self.last_failure_at = time.time()
            if self.consecutive_failures >= FAILURE_THRESHOLD:
                if self.state != "OPEN":
                    logger.warning("[health] %s: circuit OPEN (latency)", self.provider)
                self.state = "OPEN"
            return

        if latency_ms >= LATENCY_WARN_MS:
            logger.warning("[health] %s: high latency %dms", self.provider, latency_ms)

        self.total_successes += 1
        self.consecutive_failures = 0
        self.last_success_at = time.time()
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("[health] %s: circuit CLOSED (recovered)", self.provider)

    def record_failure(self, latency_ms: int = 0):
        self.total_requests += 1
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_failure_at = time.time()
        if self.consecutive_failures >= FAILURE_THRESHOLD:
            if self.state != "OPEN":
                logger.warning(f"[health] {self.provider}: circuit OPEN after {self.consecutive_failures} failures")
            self.state = "OPEN"

    def is_available(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "HALF_OPEN":
            return True
        if self.state == "OPEN":
            if self.last_failure_at and (time.time() - self.last_failure_at) > COOLDOWN_SECONDS:
                self.state = "HALF_OPEN"
                logger.info(f"[health] {self.provider}: circuit HALF_OPEN (probing)")
                return True
            return False
        return True

    def to_dict(self) -> dict:
        uptime = (
            round(self.total_successes / self.total_requests * 100, 1)
            if self.total_requests > 0 else 100.0
        )
        return {
            "provider": self.provider,
            "state": self.state,
            "available": self.is_available(),
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "uptime_pct": uptime,
            "last_latency_ms": self.last_latency_ms,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "last_failure_at": self.last_failure_at,
            "last_success_at": self.last_success_at,
        }


class AIHealthMonitor:
    """In-memory circuit breaker registry for all AI providers."""

    def __init__(self):
        self._providers: Dict[str, ProviderHealth] = {}

    def get(self, provider: str) -> ProviderHealth:
        if provider not in self._providers:
            self._providers[provider] = ProviderHealth(provider=provider)
        return self._providers[provider]

    def is_available(self, provider: str) -> bool:
        return self.get(provider).is_available()

    def record_success(self, provider: str, latency_ms: int):
        self.get(provider).record_success(latency_ms)

    def record_failure(self, provider: str, latency_ms: int = 0):
        self.get(provider).record_failure(latency_ms)

    def reset(self, provider: str):
        """Manually reset a provider's circuit (Captain override)."""
        h = self.get(provider)
        h.state = "CLOSED"
        h.consecutive_failures = 0
        logger.info(f"[health] {provider}: circuit manually reset by Captain")

    def all_status(self) -> list:
        return [h.to_dict() for h in self._providers.values()]

    def healthy_providers(self) -> list[str]:
        return [p for p, h in self._providers.items() if h.is_available()]


# Singleton — shared across all requests in this process
health_monitor = AIHealthMonitor()
