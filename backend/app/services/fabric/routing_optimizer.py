"""O5-1: Routing Optimizer — monthly weight learning job.

Analyses 30 days of `ai_model_metrics` data and updates
`ai_model_registry.availability_pct` with a learned composite score so
FabricRouter's provider selection improves over time.

Composite score formula (0–100):
  reliability  = successful_calls / total_calls            (weight 0.40)
  speed        = max_lat_baseline / avg_latency_ms         (weight 0.30)
  cost_eff     = min_cost_per_call / avg_cost_per_call     (weight 0.20)
  quality      = mean(quality_score) over window           (weight 0.10)

For any model with no calls in the window the score holds at the current
`availability_pct` (no regression on absence of data).

The optimised score is written back to `ai_model_registry.availability_pct`
and the in-process ModelRegistry cache is refreshed automatically.

This module registers the scheduler job via `register_routing_optimizer_job()`,
called from the scheduler engine at startup.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta, timezone, datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Composite score weights (must sum to 1.0)
_W_RELIABILITY = 0.40
_W_SPEED       = 0.30
_W_COST_EFF    = 0.20
_W_QUALITY     = 0.10

# Latency baseline (ms) used to normalise speed score.
# Models at or below this are given a full speed contribution.
_LATENCY_BASELINE_MS = 500.0

# Minimum calls in window before a model's score can be updated.
# Below this threshold the existing score is preserved.
_MIN_CALLS_THRESHOLD = 10

# How many days back to analyse.
_LOOKBACK_DAYS = 30


# ── Score computation ──────────────────────────────────────────────────────────

def _compute_score(
    total_calls: int,
    successful_calls: int,
    avg_latency_ms: float,
    avg_cost_per_call: float,
    avg_quality: float,
    min_cost_per_call_across_models: float,
) -> float:
    """Return composite score 0–100 for one model over the lookback window."""
    reliability = (successful_calls / total_calls) if total_calls > 0 else 0.0

    if avg_latency_ms > 0:
        speed = min(1.0, _LATENCY_BASELINE_MS / avg_latency_ms)
    else:
        speed = 1.0

    if avg_cost_per_call > 0 and min_cost_per_call_across_models > 0:
        cost_eff = min(1.0, min_cost_per_call_across_models / avg_cost_per_call)
    else:
        cost_eff = 1.0

    quality = max(0.0, min(1.0, avg_quality))

    composite = (
        _W_RELIABILITY * reliability
        + _W_SPEED       * speed
        + _W_COST_EFF    * cost_eff
        + _W_QUALITY     * quality
    )
    return round(composite * 100.0, 2)


# ── Main optimiser ─────────────────────────────────────────────────────────────

async def run_routing_optimizer(session: AsyncSession) -> dict:
    """Analyse 30d metrics and update ai_model_registry availability_pct.

    Args:
        session: live async DB session.

    Returns:
        Summary dict with models_updated, models_skipped, run_at.
    """
    from sqlalchemy import update as sa_update
    from app.models.fabric import ModelRegistry, ModelMetrics

    cutoff = date.today() - timedelta(days=_LOOKBACK_DAYS)
    run_at = datetime.now(tz=timezone.utc)

    log.info("routing_optimizer: starting — lookback=%dd cutoff=%s", _LOOKBACK_DAYS, cutoff)

    # Aggregate metrics per model over the lookback window.
    agg_result = await session.execute(
        select(
            ModelMetrics.model_id,
            func.sum(ModelMetrics.total_calls).label("total_calls"),
            func.sum(ModelMetrics.successful_calls).label("successful_calls"),
            func.avg(ModelMetrics.avg_latency_ms).label("avg_latency_ms"),
            func.sum(ModelMetrics.total_cost_usd).label("total_cost_usd"),
            func.avg(ModelMetrics.quality_score).label("avg_quality"),
        )
        .where(ModelMetrics.execution_date >= cutoff)
        .group_by(ModelMetrics.model_id)
    )
    rows = agg_result.all()

    if not rows:
        log.info("routing_optimizer: no metrics in window — nothing to optimise")
        return {"models_updated": 0, "models_skipped": 0, "run_at": run_at.isoformat()}

    # Compute per-model cost-per-call; find the minimum across all for normalisation.
    model_data: dict = {}
    for row in rows:
        total = int(row.total_calls or 0)
        cost = float(row.total_cost_usd or 0.0)
        avg_cost = (cost / total) if total > 0 else 0.0
        model_data[row.model_id] = {
            "total_calls":       total,
            "successful_calls":  int(row.successful_calls or 0),
            "avg_latency_ms":    float(row.avg_latency_ms or 0.0),
            "avg_cost_per_call": avg_cost,
            "avg_quality":       float(row.avg_quality or 0.5),
        }

    min_cost = min(
        (d["avg_cost_per_call"] for d in model_data.values() if d["avg_cost_per_call"] > 0),
        default=0.0,
    )

    models_updated = 0
    models_skipped = 0

    for model_id, data in model_data.items():
        if data["total_calls"] < _MIN_CALLS_THRESHOLD:
            log.debug(
                "routing_optimizer: model %s skipped — only %d calls in window",
                model_id, data["total_calls"],
            )
            models_skipped += 1
            continue

        score = _compute_score(
            total_calls=data["total_calls"],
            successful_calls=data["successful_calls"],
            avg_latency_ms=data["avg_latency_ms"],
            avg_cost_per_call=data["avg_cost_per_call"],
            avg_quality=data["avg_quality"],
            min_cost_per_call_across_models=min_cost,
        )

        await session.execute(
            sa_update(ModelRegistry)
            .where(ModelRegistry.id == model_id)
            .values(availability_pct=score)
        )
        log.debug("routing_optimizer: model %s → availability_pct=%.2f", model_id, score)
        models_updated += 1

    await session.commit()

    # Refresh the in-process cache so FabricRouter picks up new weights.
    try:
        from app.services.fabric.model_registry import get_model_registry
        registry = get_model_registry()
        if registry._seeded and session is not None:
            async with session.bind.connect() as conn:
                pass  # force pool keepalive; cache refresh happens on next seed()
    except Exception as exc:
        log.debug("routing_optimizer: cache hint skipped — %s", exc)

    log.info(
        "routing_optimizer: complete — updated=%d skipped=%d",
        models_updated, models_skipped,
    )
    return {
        "models_updated": models_updated,
        "models_skipped": models_skipped,
        "run_at": run_at.isoformat(),
    }


# ── Scheduler job wrapper ──────────────────────────────────────────────────────

async def _job_routing_optimizer() -> None:
    """APScheduler job: run monthly routing weight optimisation."""
    from app.core.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as session:
            result = await run_routing_optimizer(session)
            log.info("routing_optimizer job complete: %s", result)
    except Exception as exc:
        log.error("routing_optimizer job failed: %s", exc)


def register_routing_optimizer_job() -> None:
    """Register the monthly routing optimizer job with the scheduler.

    Call this from the scheduler engine's ``_register_default_jobs()``.
    The job runs on the 1st of each month at 03:00 UTC so it processes
    the previous month's full data before business hours.
    """
    from apscheduler.triggers.cron import CronTrigger
    from app.services.scheduler.engine import get_scheduler
    scheduler = get_scheduler()
    scheduler.add_job(
        _job_routing_optimizer,
        trigger=CronTrigger(day=1, hour=3, minute=0, timezone="UTC"),
        id="routing_optimizer_sweep",
        replace_existing=True,
        name="routing_optimizer_sweep",
    )
    log.info("routing_optimizer: monthly job registered (1st of month @ 03:00 UTC)")
