"""F3-2: Model Registry — database-backed AI model catalogue with live health tracking.

Extends the existing AI router (app/services/ai/router.py) by persisting every
provider/model combination in `ai_model_registry` and maintaining per-day metrics
in `ai_model_metrics`.  The registry is the single authoritative source of model
status and performance data for the Intelligent Router (F3-3).

Key responsibilities:
  1. Seed  — on startup, upsert every (provider, model) from the existing
             ROUTING_TABLE into ai_model_registry with its role and cost.
  2. Cache — maintain an in-process dict for sub-millisecond lookups.
  3. Update — accept latency/cost/success reports from call-path, update rolling
              statistics, persist daily aggregates to ai_model_metrics.
  4. Health — background loop marks models DEGRADED (error_rate > 0.3) or
              UNAVAILABLE (error_rate > 0.7 or 5+ consecutive failures).
  5. Query  — list_by_role / list_active / get_fallback_chain for F3-3.
"""
from __future__ import annotations

import asyncio
import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.services.ai.cost_tracker import COST_TABLE

log = logging.getLogger(__name__)

# Role tags aligned with §4.3 of the Architecture doc.
ROLE_BUILDER  = "builder"
ROLE_REVIEWER = "reviewer"

# Error-rate thresholds for automatic status transitions.
_DEGRADED_THRESHOLD    = 0.30   # error_rate ≥ 30 % → DEGRADED
_UNAVAILABLE_THRESHOLD = 0.70   # error_rate ≥ 70 % → UNAVAILABLE
_CONSECUTIVE_FAIL_CAP  = 5      # 5 consecutive fails → UNAVAILABLE regardless

# Health-check loop interval in seconds.
_HEALTH_LOOP_INTERVAL = 60

# ── Seed catalogue: which providers are "builders" vs "reviewers" ──────────────
_BUILDER_PROVIDERS  = {"nvidia", "groq", "deepseek", "google", "zhipuai",
                       "qwen", "moonshot", "minimax", "mistral"}
_REVIEWER_PROVIDERS = {"anthropic", "openai", "openrouter", "bedrock"}

# ── Full model seed list derived from the existing ROUTING_TABLE ───────────────
# Format: (provider, model_key, role)
_SEED_MODELS: list[tuple[str, str, str]] = [
    # NIM builders
    ("nvidia", "deepseek-v4-pro",    ROLE_BUILDER),
    ("nvidia", "deepseek-v4-flash",  ROLE_BUILDER),
    ("nvidia", "qwen-coder",         ROLE_BUILDER),
    ("nvidia", "llama-4-maverick",   ROLE_BUILDER),
    ("nvidia", "llama-4-scout",      ROLE_BUILDER),
    ("nvidia", "llama-3-3",          ROLE_BUILDER),
    ("nvidia", "kimi-k2",            ROLE_BUILDER),
    ("nvidia", "mistral-medium",     ROLE_BUILDER),
    # Reviewers / premium
    ("anthropic", "claude-sonnet",   ROLE_REVIEWER),
    ("anthropic", "claude-haiku",    ROLE_REVIEWER),
    ("bedrock",   "claude-sonnet-4-6", ROLE_REVIEWER),
    ("openai",    "gpt-4o",          ROLE_REVIEWER),
    ("openai",    "gpt-4o-mini",     ROLE_REVIEWER),
    ("openrouter","deepseek-v4-pro", ROLE_REVIEWER),
    ("openrouter","llama-90b",       ROLE_REVIEWER),
    # Supporting builders
    ("google",    "gemini-pro",      ROLE_BUILDER),
    ("groq",      "llama-4",         ROLE_BUILDER),
    ("deepseek",  "deepseek-r2",     ROLE_BUILDER),
    ("mistral",   "mistral-large",   ROLE_BUILDER),
    ("zhipuai",   "glm-5-1",         ROLE_BUILDER),
]


def _cost_per_mtok(provider: str, model_key: str) -> float:
    """Look up cost per million tokens from the existing COST_TABLE."""
    for p, m, rate_per_1k in COST_TABLE:
        if provider == p and m in model_key:
            return round(rate_per_1k * 1000, 6)   # per-1k → per-1M
    return 1.0   # $1/Mtok default


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class ModelRegistryEntry:
    """In-process representation of one ai_model_registry row."""
    id: uuid.UUID
    provider: str
    model_name: str
    role: str
    status: str             # "active" | "degraded" | "unavailable"
    latency_p50: float
    latency_p95: float
    error_rate: float
    cost_per_mtok: float
    availability_pct: float
    last_health_check: Optional[datetime]

    # Rolling accumulators — not persisted, reset on reload.
    _call_count:      int   = field(default=0, compare=False, repr=False)
    _fail_count:      int   = field(default=0, compare=False, repr=False)
    _latency_samples: list  = field(default_factory=list, compare=False, repr=False)
    _consecutive_fails: int = field(default=0, compare=False, repr=False)

    def record(self, latency_ms: float, success: bool, tokens: int, cost: float) -> None:
        self._call_count += 1
        self._latency_samples.append(latency_ms)
        if not success:
            self._fail_count += 1
            self._consecutive_fails += 1
        else:
            self._consecutive_fails = 0

        # Keep rolling window at 100 samples.
        if len(self._latency_samples) > 100:
            self._latency_samples = self._latency_samples[-100:]

        # Refresh live metrics.
        if self._latency_samples:
            s = sorted(self._latency_samples)
            n = len(s)
            self.latency_p50 = s[int(n * 0.50)]
            self.latency_p95 = s[int(n * 0.95)]
        if self._call_count:
            self.error_rate = self._fail_count / self._call_count
            self.availability_pct = max(0.0, 100.0 - self.error_rate * 100)

        # Auto-transition status based on error rate + consecutive failures.
        if self._consecutive_fails >= _CONSECUTIVE_FAIL_CAP or self.error_rate >= _UNAVAILABLE_THRESHOLD:
            self.status = "unavailable"
        elif self.error_rate >= _DEGRADED_THRESHOLD:
            self.status = "degraded"
        else:
            self.status = "active"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "provider": self.provider,
            "model_name": self.model_name,
            "role": self.role,
            "status": self.status,
            "latency_p50": self.latency_p50,
            "latency_p95": self.latency_p95,
            "error_rate": round(self.error_rate, 4),
            "cost_per_mtok": self.cost_per_mtok,
            "availability_pct": round(self.availability_pct, 2),
            "last_health_check": (
                self.last_health_check.isoformat()
                if self.last_health_check else None
            ),
        }


# ── Core service ───────────────────────────────────────────────────────────────

class ModelRegistry:
    """Database-backed AI model registry with an in-process cache.

    Seeded automatically on first :meth:`seed` call.  Callers should
    use :func:`get_model_registry` to obtain the singleton, then call
    ``await registry.seed(session)`` once at application startup.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], ModelRegistryEntry] = {}
        self._seeded: bool = False
        self._bg_task: Optional[asyncio.Task] = None

    # ── Seeding ────────────────────────────────────────────────────────────────

    async def seed(self, session: AsyncSession) -> int:
        """Upsert all seed models into ai_model_registry.  Returns rows upserted."""
        from app.models.fabric import ModelRegistry as ModelRegistryModel

        count = 0
        for provider, model_name, role in _SEED_MODELS:
            cost = _cost_per_mtok(provider, model_name)
            # Check existing row.
            result = await session.execute(
                select(ModelRegistryModel).where(
                    ModelRegistryModel.provider == provider,
                    ModelRegistryModel.model_name == model_name,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = ModelRegistryModel(
                    provider=provider,
                    model_name=model_name,
                    role=role,
                    status="active",
                    cost_per_mtok=cost,
                    availability_pct=100.0,
                )
                session.add(row)
                count += 1
            # Always sync role and cost in case they drifted.
            row.role = role
            row.cost_per_mtok = cost

            # Update in-process cache.
            self._cache[(provider, model_name)] = ModelRegistryEntry(
                id=row.id if row.id else uuid.uuid4(),
                provider=provider,
                model_name=model_name,
                role=role,
                status=row.status or "active",
                latency_p50=float(row.latency_p50 or 0),
                latency_p95=float(row.latency_p95 or 0),
                error_rate=float(row.error_rate or 0),
                cost_per_mtok=cost,
                availability_pct=float(row.availability_pct or 100),
                last_health_check=row.last_health_check,
            )

        await session.commit()
        self._seeded = True
        log.info("model_registry seeded — %d new rows, %d total", count, len(self._cache))
        return count

    # ── Reads ──────────────────────────────────────────────────────────────────

    def get(self, provider: str, model_name: str) -> Optional[ModelRegistryEntry]:
        """Return a cached entry or None (sub-millisecond)."""
        return self._cache.get((provider, model_name))

    def list_active(self) -> list[ModelRegistryEntry]:
        """Return all entries whose status is 'active'."""
        return [e for e in self._cache.values() if e.status == "active"]

    def list_by_role(self, role: str) -> list[ModelRegistryEntry]:
        """Return entries filtered by role ('builder' or 'reviewer')."""
        return [e for e in self._cache.values() if e.role == role]

    def get_fallback_chain(self, task_type_str: str) -> list[tuple[str, str]]:
        """Return the ordered (provider, model_name) chain for a task type.

        Filters out UNAVAILABLE entries so the Intelligent Router never
        tries a dead provider.  Preserves original ROUTING_TABLE priority.
        """
        from app.services.ai.router import ROUTING_TABLE
        from app.services.ai.base_provider import TaskType

        try:
            tt = TaskType(task_type_str.lower())
        except ValueError:
            tt = TaskType.GENERAL

        chain = ROUTING_TABLE.get(tt, [])
        alive = []
        for provider, model_key in chain:
            entry = self._cache.get((provider, model_key))
            if entry is None or entry.status != "unavailable":
                alive.append((provider, model_key))
        return alive

    def snapshot(self) -> dict:
        """Return a serialisable dict of the full cache."""
        return {f"{e.provider}/{e.model_name}": e.to_dict()
                for e in self._cache.values()}

    # ── Writes ─────────────────────────────────────────────────────────────────

    async def record_call(
        self,
        provider: str,
        model_name: str,
        latency_ms: float,
        success: bool,
        tokens: int,
        cost_usd: float,
        session: AsyncSession,
    ) -> None:
        """Record one call result — update cache and daily metrics row."""
        from app.models.fabric import ModelRegistry as RegistryModel
        from app.models.fabric import ModelMetrics

        entry = self._cache.get((provider, model_name))
        if entry is None:
            return

        entry.record(latency_ms, success, tokens, cost_usd)
        today = date.today()

        # Upsert daily metric row.
        result = await session.execute(
            select(ModelMetrics).where(
                ModelMetrics.model_id == entry.id,
                ModelMetrics.execution_date == today,
            )
        )
        metric = result.scalar_one_or_none()
        if metric is None:
            metric = ModelMetrics(model_id=entry.id, execution_date=today)
            session.add(metric)

        metric.total_calls    = (metric.total_calls or 0) + 1
        metric.total_tokens   = (metric.total_tokens or 0) + tokens
        metric.total_cost_usd = float(metric.total_cost_usd or 0) + cost_usd
        if success:
            metric.successful_calls = (metric.successful_calls or 0) + 1
        else:
            metric.failed_calls = (metric.failed_calls or 0) + 1

        # Update running avg latency.
        prev_avg = float(metric.avg_latency_ms or 0)
        prev_n   = max(1, (metric.successful_calls or 0) + (metric.failed_calls or 0) - 1)
        metric.avg_latency_ms = (prev_avg * prev_n + latency_ms) / (prev_n + 1)

        # Sync live stats to registry row.
        await session.execute(
            update(RegistryModel)
            .where(RegistryModel.id == entry.id)
            .values(
                status=entry.status,
                latency_p50=entry.latency_p50,
                latency_p95=entry.latency_p95,
                error_rate=entry.error_rate,
                availability_pct=entry.availability_pct,
                last_health_check=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
            )
        )
        await session.commit()

    # ── Background loop ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start background health-check loop."""
        if self._bg_task and not self._bg_task.done():
            return
        self._bg_task = asyncio.create_task(self._health_loop())
        self._bg_task.add_done_callback(
            lambda t: log.warning("model_registry health loop exited: %s", t.exception())
            if not t.cancelled() and t.exception() else None
        )

    async def stop(self) -> None:
        if self._bg_task:
            self._bg_task.cancel()
            try:
                await self._bg_task
            except asyncio.CancelledError:
                pass

    async def _health_loop(self) -> None:
        """Every 60s: reload from DB and emit events for status changes."""
        while True:
            await asyncio.sleep(_HEALTH_LOOP_INTERVAL)
            try:
                async with AsyncSessionLocal() as session:
                    await self._reload_from_db(session)
            except Exception as exc:
                log.warning("model_registry reload error: %s", exc)

    async def _reload_from_db(self, session: AsyncSession) -> None:
        """Refresh cache entries from the database (without overwriting live counters)."""
        from app.models.fabric import ModelRegistry as RegistryModel

        result = await session.execute(select(RegistryModel))
        rows = result.scalars().all()
        for row in rows:
            key = (row.provider, row.model_name)
            entry = self._cache.get(key)
            if entry is None:
                # New model added to DB outside of seed — pick it up.
                self._cache[key] = ModelRegistryEntry(
                    id=row.id,
                    provider=row.provider,
                    model_name=row.model_name,
                    role=row.role,
                    status=row.status or "active",
                    latency_p50=float(row.latency_p50 or 0),
                    latency_p95=float(row.latency_p95 or 0),
                    error_rate=float(row.error_rate or 0),
                    cost_per_mtok=float(row.cost_per_mtok or 1.0),
                    availability_pct=float(row.availability_pct or 100),
                    last_health_check=row.last_health_check,
                )
            else:
                # Only update fields not managed by rolling accumulators.
                entry.last_health_check = row.last_health_check


# ── Singleton ─────────────────────────────────────────────────────────────────

_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Return the module-level ModelRegistry singleton."""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry
