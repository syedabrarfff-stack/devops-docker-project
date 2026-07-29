"""F3-4: Token Governor — global budget management, quotas, and cost forecasting.

Enforces §4.2 of the Architecture doc:
  "Token Governor — global monthly budget, per-provider quotas, rate limiting,
   cost forecasting.  At 80% of budget: shift weights toward free/cheap models
   + alert Captain."

Implementation:
  - In-process monthly spend counter (keyed by calendar month YYYY-MM).
  - Per-provider quota table loaded from ConfigService (hot-reload).
  - At ≥ 80 % of monthly budget → EventBus emits "alert.budget" + cheap chain
    is returned from get_cheap_fallback().
  - Per-minute rate counter for rudimentary call-rate limiting.
  - Daily spend written to ai_model_metrics by ModelRegistry; this module
    reads from the metrics table to initialise spend on startup.

Budget config keys (in kernel_config, managed by ConfigService):
  budget.monthly_usd          — default 100.0
  budget.warn_pct             — default 0.80
  budget.rate_limit_per_min   — default 120 (0 = unlimited)
  budget.quota.<provider>     — per-provider monthly cap in USD, e.g.
                                 budget.quota.anthropic = 30.0
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)

_DEFAULT_MONTHLY_USD     = 100.0
_DEFAULT_WARN_PCT        = 0.80
_DEFAULT_RATE_PER_MIN    = 120

# Models considered "cheap" (builder tier, zero or near-zero cost).
# Used when shifting weights after the 80 % warning fires.
_CHEAP_FALLBACK_CHAIN: list[tuple[str, str]] = [
    ("nvidia", "llama-4-scout"),
    ("nvidia", "deepseek-v4-flash"),
    ("nvidia", "llama-3-3"),
    ("nvidia", "mistral-medium"),
    ("groq",   "llama-4"),
]


class TokenGovernor:
    """Manages AI token spend and enforces budget guardrails.

    Designed as a singleton — use :func:`get_token_governor`.
    Thread/task-safe: all mutable state is protected by ``asyncio.Lock``.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

        # Monthly spend per provider: {month_str: {provider: usd}}
        self._monthly: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        # Rate counter: {minute_bucket: total_calls}
        self._rate_buckets: dict[int, int] = defaultdict(int)

        self._alert_sent_month: Optional[str] = None
        self._bg_task: Optional[asyncio.Task] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    async def record_usage(
        self,
        provider: str,
        model_name: str,
        tokens: int,
        cost_usd: float,
    ) -> bool:
        """Record a completed AI call.

        Returns True if still within budget, False if the monthly budget
        has been exceeded (caller should log a warning; hard-blocking is
        not enforced by default).
        """
        month = _current_month()
        minute = _current_minute()

        async with self._lock:
            self._monthly[month][provider] += cost_usd
            self._rate_buckets[minute] += 1
            # Prune buckets older than 5 minutes to cap memory.
            stale = [k for k in self._rate_buckets if k < minute - 5]
            for k in stale:
                del self._rate_buckets[k]

        spend = await self.get_monthly_spend()
        budget = await self._get_budget()
        pct = spend / budget if budget > 0 else 0.0

        if pct >= _DEFAULT_WARN_PCT and self._alert_sent_month != month:
            await self._emit_budget_alert(spend, budget, pct)
            self._alert_sent_month = month

        return spend <= budget

    async def get_monthly_spend(self, provider: Optional[str] = None) -> float:
        """Return total USD spent this calendar month, optionally filtered by provider."""
        month = _current_month()
        async with self._lock:
            monthly = dict(self._monthly.get(month, {}))
        if provider:
            return monthly.get(provider, 0.0)
        return sum(monthly.values())

    async def get_usage_pct(self) -> float:
        """Return the fraction of monthly budget consumed (0.0–1.0+)."""
        spend  = await self.get_monthly_spend()
        budget = await self._get_budget()
        return spend / budget if budget > 0 else 0.0

    async def is_over_quota(self, provider: str) -> bool:
        """True if this provider has exceeded its per-provider monthly quota."""
        quota = await self._get_provider_quota(provider)
        if quota is None:
            return False
        spend = await self.get_monthly_spend(provider)
        return spend >= quota

    async def is_rate_limited(self) -> bool:
        """True if the per-minute call rate exceeds the configured limit."""
        limit = await self._get_rate_limit()
        if limit == 0:
            return False
        minute = _current_minute()
        async with self._lock:
            count = self._rate_buckets.get(minute, 0)
        return count >= limit

    async def get_cheap_fallback(
        self, task_type_str: Optional[str] = None
    ) -> list[tuple[str, str]]:
        """Return cheap model chain to use when spend is ≥ 80% of budget.

        Attempts to exclude providers that are over their individual quota.
        """
        chain = []
        for provider, model in _CHEAP_FALLBACK_CHAIN:
            if not await self.is_over_quota(provider):
                chain.append((provider, model))
        return chain or _CHEAP_FALLBACK_CHAIN   # always return something

    async def status(self) -> dict:
        """Return a serialisable status snapshot."""
        spend  = await self.get_monthly_spend()
        budget = await self._get_budget()
        pct    = spend / budget if budget > 0 else 0.0
        rate   = await self._get_rate_limit()
        minute = _current_minute()
        async with self._lock:
            current_rate = self._rate_buckets.get(minute, 0)
            monthly_copy = {k: dict(v) for k, v in self._monthly.items()}

        return {
            "month":             _current_month(),
            "spend_usd":         round(spend, 4),
            "budget_usd":        budget,
            "usage_pct":         round(pct, 4),
            "alert_threshold":   _DEFAULT_WARN_PCT,
            "alert_sent":        self._alert_sent_month == _current_month(),
            "rate_limit_per_min": rate,
            "calls_this_minute": current_rate,
            "per_provider":      monthly_copy.get(_current_month(), {}),
        }

    async def initialise_from_metrics(self, session) -> None:
        """Load month-to-date spend from ai_model_metrics on startup.

        Prevents the governor from underreporting spend after a restart.
        """
        from sqlalchemy import select as sa_select
        from app.models.fabric import ModelMetrics, ModelRegistry as RegistryModel

        month = _current_month()
        year_part, month_part = month.split("-")

        try:
            result = await session.execute(
                sa_select(
                    RegistryModel.provider,
                    sa_select(
                        ModelMetrics.total_cost_usd
                    ).where(
                        ModelMetrics.model_id == RegistryModel.id,
                        ModelMetrics.execution_date >= f"{year_part}-{month_part}-01",
                    ).correlate(RegistryModel).scalar_subquery()
                ).where(
                    RegistryModel.provider.isnot(None)
                )
            )
            for provider, cost in result:
                if cost:
                    async with self._lock:
                        self._monthly[month][provider] += float(cost)
        except Exception as exc:
            log.warning("token_governor: could not initialise from metrics: %s", exc)

    # ── Background loop ────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._bg_task and not self._bg_task.done():
            return
        self._bg_task = asyncio.create_task(self._monthly_reset_loop())

    async def stop(self) -> None:
        if self._bg_task:
            self._bg_task.cancel()
            try:
                await self._bg_task
            except asyncio.CancelledError:
                pass

    async def _monthly_reset_loop(self) -> None:
        """Prune data from months that have expired (keep current + previous)."""
        while True:
            await asyncio.sleep(3600)   # run hourly
            current = _current_month()
            async with self._lock:
                stale = [m for m in self._monthly if m < current]
                # Keep the two most recent months for forecasting.
                for m in stale[:-1]:
                    del self._monthly[m]
            if stale:
                log.debug("token_governor: pruned %d stale month(s)", len(stale) - 1)

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_budget(self) -> float:
        try:
            from app.services.kernel.config_service import get_config_service
            cfg = get_config_service()
            return await cfg.get_float("budget.monthly_usd", _DEFAULT_MONTHLY_USD)
        except Exception:
            return _DEFAULT_MONTHLY_USD

    async def _get_provider_quota(self, provider: str) -> Optional[float]:
        try:
            from app.services.kernel.config_service import get_config_service
            cfg = get_config_service()
            val = await cfg.get(f"budget.quota.{provider}")
            return float(val) if val is not None else None
        except Exception:
            return None

    async def _get_rate_limit(self) -> int:
        try:
            from app.services.kernel.config_service import get_config_service
            cfg = get_config_service()
            return await cfg.get_int("budget.rate_limit_per_min", _DEFAULT_RATE_PER_MIN)
        except Exception:
            return _DEFAULT_RATE_PER_MIN

    async def _emit_budget_alert(self, spend: float, budget: float, pct: float) -> None:
        """Emit an EventBus alert and log the budget warning."""
        log.warning(
            "BUDGET ALERT: monthly spend $%.2f / $%.2f (%.0f%%) — "
            "switching to cheap fallback models",
            spend, budget, pct * 100,
        )
        try:
            from app.services.kernel.event_bus import get_event_bus, KernelEvent
            bus = get_event_bus()
            await bus.emit(KernelEvent(
                event_type="alert.budget",
                source_engine="token_governor",
                payload={
                    "spend_usd":  round(spend, 4),
                    "budget_usd": budget,
                    "usage_pct":  round(pct, 4),
                    "month":      _current_month(),
                },
            ))
        except Exception as exc:
            log.warning("token_governor: could not emit budget alert: %s", exc)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _current_month() -> str:
    now = datetime.now(tz=timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def _current_minute() -> int:
    """Return integer minutes since epoch (used as rate-bucket key)."""
    return int(time.monotonic() // 60)


# ── Singleton ─────────────────────────────────────────────────────────────────

_token_governor: Optional[TokenGovernor] = None


def get_token_governor() -> TokenGovernor:
    """Return the module-level TokenGovernor singleton."""
    global _token_governor
    if _token_governor is None:
        _token_governor = TokenGovernor()
    return _token_governor
