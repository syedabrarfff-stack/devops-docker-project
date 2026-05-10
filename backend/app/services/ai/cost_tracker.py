"""
AI Cost Tracker — per-model USD rate table, daily aggregation, surge detection.
All rates are approximate and based on publicly published pricing.
"""
import logging
from datetime import datetime, date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.ai_audit import AIRequestLog

logger = logging.getLogger(__name__)

# ─── Cost table (USD per 1,000 tokens — blended input+output estimate) ────────
# Format: (provider, model_substring) -> cost_per_1k_tokens
COST_TABLE: list[tuple[str, str, float]] = [
    # Anthropic
    ("anthropic", "claude-opus",    0.045),   # ~$15 input + $75 output / 1M avg
    ("anthropic", "claude-sonnet",  0.009),   # ~$3 input + $15 output / 1M avg
    ("anthropic", "claude-haiku",   0.001),
    # OpenAI
    ("openai",    "gpt-4o",         0.007),   # $2.5 input + $10 output / 1M avg
    ("openai",    "gpt-4o-mini",    0.0004),
    ("openai",    "o1",             0.030),
    ("openai",    "o3",             0.060),
    # DeepSeek
    ("deepseek",  "deepseek-r2",    0.0015),
    ("deepseek",  "deepseek",       0.0007),  # ~$0.27/$1.1 per 1M
    # Google
    ("google",    "gemini",         0.002),   # ~$1.25/$5 per 1M
    # Groq (ultra-fast, low cost)
    ("groq",      "llama-4",        0.0008),
    ("groq",      "llama-3",        0.0006),
    ("groq",      "",               0.0005),
    # ZhipuAI / GLM
    ("zhipuai",   "glm-4-plus",     0.001),
    ("zhipuai",   "",               0.0005),
    # Moonshot / Kimi
    ("moonshot",  "",               0.012),   # $12/1M tokens
    # Qwen / DashScope
    ("qwen",      "",               0.0006),
    # MiniMax
    ("minimax",   "",               0.002),
    # NVIDIA NIM
    ("nvidia",    "",               0.001),
    # Mistral
    ("mistral",   "large",          0.003),
    ("mistral",   "",               0.001),
]

# Daily cost surge threshold (USD) — alert Captain if exceeded
DAILY_SURGE_THRESHOLD_USD = 50.0


def estimate_cost(provider: str, model_id: str, tokens: int) -> float:
    """Return estimated USD cost for a given call."""
    for p, m, rate in COST_TABLE:
        if provider == p and m in model_id:
            return round(tokens / 1000 * rate, 6)
    return round(tokens / 1000 * 0.001, 6)  # fallback: $0.001/1K


async def log_request(
    db: AsyncSession,
    provider: str,
    model: str,
    task_type: str,
    tokens_used: int,
    latency_ms: int,
    success: bool,
    error_message: Optional[str] = None,
    session_id: Optional[str] = None,
) -> AIRequestLog:
    cost = estimate_cost(provider, model, tokens_used)
    entry = AIRequestLog(
        provider=provider,
        model=model,
        task_type=task_type,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        cost_estimate_usd=cost,
        success=success,
        error_message=error_message,
        session_id=session_id,
    )
    db.add(entry)
    await db.commit()
    return entry


async def get_daily_cost(db: AsyncSession, for_date: Optional[date] = None) -> dict:
    target = for_date or date.today()
    start = datetime.combine(target, datetime.min.time())
    end = datetime.combine(target, datetime.max.time())

    result = await db.execute(
        select(
            AIRequestLog.provider,
            func.sum(AIRequestLog.cost_estimate_usd).label("total_cost"),
            func.sum(AIRequestLog.tokens_used).label("total_tokens"),
            func.count().label("total_requests"),
            func.avg(AIRequestLog.latency_ms).label("avg_latency"),
        )
        .where(AIRequestLog.created_at.between(start, end))
        .group_by(AIRequestLog.provider)
    )
    rows = result.fetchall()

    breakdown = {r.provider: {
        "cost_usd": round(r.total_cost or 0, 4),
        "tokens": int(r.total_tokens or 0),
        "requests": int(r.total_requests),
        "avg_latency_ms": int(r.avg_latency or 0),
    } for r in rows}

    total = sum(v["cost_usd"] for v in breakdown.values())
    return {
        "date": target.isoformat(),
        "total_cost_usd": round(total, 4),
        "surge_alert": total > DAILY_SURGE_THRESHOLD_USD,
        "surge_threshold_usd": DAILY_SURGE_THRESHOLD_USD,
        "by_provider": breakdown,
    }


async def get_audit_log(db: AsyncSession, limit: int = 100, provider: Optional[str] = None) -> list:
    q = select(AIRequestLog).order_by(AIRequestLog.created_at.desc()).limit(limit)
    if provider:
        q = q.where(AIRequestLog.provider == provider)
    result = await db.execute(q)
    rows = result.scalars().all()
    return [{
        "id": r.id,
        "provider": r.provider,
        "model": r.model,
        "task_type": r.task_type,
        "tokens_used": r.tokens_used,
        "latency_ms": r.latency_ms,
        "cost_estimate_usd": r.cost_estimate_usd,
        "success": r.success,
        "error_message": r.error_message,
        "created_at": r.created_at.isoformat(),
    } for r in rows]


async def get_cost_summary(db: AsyncSession, days: int = 7) -> dict:
    """Rolling N-day cost summary."""
    from datetime import timedelta
    summaries = []
    for i in range(days - 1, -1, -1):
        d = date.today() - timedelta(days=i)
        day_summary = await get_daily_cost(db, d)
        summaries.append({"date": d.isoformat(), "cost_usd": day_summary["total_cost_usd"]})
    total_7d = sum(s["cost_usd"] for s in summaries)
    return {
        "days": days,
        "total_cost_usd": round(total_7d, 4),
        "daily": summaries,
        "avg_daily_usd": round(total_7d / days, 4),
    }
