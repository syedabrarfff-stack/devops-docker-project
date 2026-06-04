from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Iterable

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.economics import AICostLedger
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.cost_tracker import estimate_cost

logger = logging.getLogger(__name__)

CLAUDE_PROVIDERS = {"anthropic", "bedrock"}
CLAUDE_STRATEGIC_TASKS = {
    TaskType.ANALYSIS.value,
    TaskType.STRATEGY.value,
    TaskType.REASONING.value,
    TaskType.CODE.value,
    TaskType.LONG_CONTEXT.value,
}
CLAUDE_BLOCKED_TASKS = {
    TaskType.FAST.value,
    TaskType.GENERAL.value,
    TaskType.MATH.value,
    TaskType.MULTILINGUAL.value,
    TaskType.REALTIME.value,
    TaskType.MULTIMODAL.value,
    TaskType.SALES.value,
}
CLAUDE_ESCALATION_MARKERS = (
    "architecture",
    "system design",
    "critical decision",
    "council",
    "high impact",
    "root cause",
    "security incident",
    "production incident",
    "long context",
    "full document",
    "complex coding",
)


@dataclass(frozen=True)
class ClaudeBudgetDecision:
    allowed: bool
    reason: str
    spent_today_usd: float = 0.0
    spent_window_usd: float = 0.0
    daily_limit_usd: float = 0.0
    usable_budget_usd: float = 0.0
    reserve_usd: float = 0.0
    projected_call_usd: float = 0.0


async def should_use_claude(
    *,
    task_type: str,
    provider: str,
    model_id: str,
    messages: Iterable[Message],
    system_prompt: str,
    max_tokens: int,
    forced: bool = False,
) -> ClaudeBudgetDecision:
    """Return whether a Claude-class provider may be used under Captain's cost policy."""
    if provider not in CLAUDE_PROVIDERS:
        return ClaudeBudgetDecision(True, "not_claude_provider")

    normalized_task = (task_type or TaskType.GENERAL.value).lower()
    strategic = _is_strategic_context(normalized_task, messages, system_prompt)
    if normalized_task in CLAUDE_BLOCKED_TASKS and not strategic:
        return ClaudeBudgetDecision(False, f"claude_reserved_not_for_{normalized_task}")
    if normalized_task not in CLAUDE_STRATEGIC_TASKS and not strategic:
        return ClaudeBudgetDecision(False, "claude_requires_strategic_context")

    projected = _projected_call_cost(provider, model_id, messages, system_prompt, max_tokens)
    try:
        spent_today, spent_window = await _claude_spend()
    except Exception as exc:
        logger.warning("Claude budget check failed closed: %s", exc)
        return ClaudeBudgetDecision(
            False,
            "claude_budget_check_unavailable",
            projected_call_usd=projected,
        )

    usable_budget = settings.CLAUDE_BUDGET_TOTAL_USD * (1.0 - settings.CLAUDE_RESERVE_RATIO)
    reserve = settings.CLAUDE_BUDGET_TOTAL_USD - usable_budget
    daily_limit = usable_budget / max(1, settings.CLAUDE_BUDGET_WINDOW_DAYS)

    if spent_window + projected > usable_budget:
        return ClaudeBudgetDecision(
            forced and strategic and (spent_window + projected) <= settings.CLAUDE_BUDGET_TOTAL_USD,
            "claude_emergency_reserve_only",
            spent_today,
            spent_window,
            daily_limit,
            usable_budget,
            reserve,
            projected,
        )

    if spent_today + projected > daily_limit and not forced:
        return ClaudeBudgetDecision(
            False,
            "claude_daily_burn_rate_exceeded",
            spent_today,
            spent_window,
            daily_limit,
            usable_budget,
            reserve,
            projected,
        )

    if projected > settings.CLAUDE_SINGLE_CALL_MAX_USD and not forced:
        return ClaudeBudgetDecision(
            False,
            "claude_single_call_limit_exceeded",
            spent_today,
            spent_window,
            daily_limit,
            usable_budget,
            reserve,
            projected,
        )

    return ClaudeBudgetDecision(
        True,
        "claude_budget_ok",
        spent_today,
        spent_window,
        daily_limit,
        usable_budget,
        reserve,
        projected,
    )


async def claude_governance_status() -> dict:
    spent_today, spent_window = await _claude_spend()
    usable_budget = settings.CLAUDE_BUDGET_TOTAL_USD * (1.0 - settings.CLAUDE_RESERVE_RATIO)
    reserve = settings.CLAUDE_BUDGET_TOTAL_USD - usable_budget
    daily_limit = usable_budget / max(1, settings.CLAUDE_BUDGET_WINDOW_DAYS)
    return {
        "provider": "anthropic_claude",
        "policy": "premium_strategic_resource",
        "budget_total_usd": round(settings.CLAUDE_BUDGET_TOTAL_USD, 4),
        "budget_window_days": settings.CLAUDE_BUDGET_WINDOW_DAYS,
        "reserve_usd": round(reserve, 4),
        "reserve_ratio": settings.CLAUDE_RESERVE_RATIO,
        "usable_budget_usd": round(usable_budget, 4),
        "daily_planned_limit_usd": round(daily_limit, 4),
        "single_call_limit_usd": round(settings.CLAUDE_SINGLE_CALL_MAX_USD, 4),
        "spent_today_usd": round(spent_today, 6),
        "spent_window_usd": round(spent_window, 6),
        "remaining_usable_usd": round(max(0.0, usable_budget - spent_window), 6),
        "normal_use_allowed": spent_today < daily_limit and spent_window < usable_budget,
        "strategic_tasks": sorted(CLAUDE_STRATEGIC_TASKS),
        "blocked_default_tasks": sorted(CLAUDE_BLOCKED_TASKS),
        "default_council": ["deepseek", "groq", "one_premium_only_when_needed"],
    }


def _is_strategic_context(task_type: str, messages: Iterable[Message], system_prompt: str) -> bool:
    if task_type in CLAUDE_STRATEGIC_TASKS:
        return True
    # Do not inspect the global JARVIS system prompt here: it naturally contains
    # words like "architecture" and "council", which would turn every small task
    # into a false Claude escalation. Only the actual request context counts.
    text = " ".join(message.content or "" for message in messages).lower()
    return any(marker in text for marker in CLAUDE_ESCALATION_MARKERS)


def _projected_call_cost(
    provider: str,
    model_id: str,
    messages: Iterable[Message],
    system_prompt: str,
    max_tokens: int,
) -> float:
    input_tokens = max(1, len((system_prompt or "") + " ".join(m.content or "" for m in messages)) // 4)
    projected_tokens = input_tokens + max(0, int(max_tokens or 0))
    return estimate_cost(provider, model_id, projected_tokens)


async def _claude_spend() -> tuple[float, float]:
    tenant_id = settings.JARVIS_DEFAULT_TENANT_ID or "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = today_start - timedelta(days=max(1, settings.CLAUDE_BUDGET_WINDOW_DAYS) - 1)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, tenant_id)
            today = await session.scalar(
                select(func.coalesce(func.sum(AICostLedger.cost_usd), 0.0)).where(
                    AICostLedger.provider == "anthropic",
                    AICostLedger.created_at >= today_start,
                    AICostLedger.created_at <= now,
                )
            )
            window = await session.scalar(
                select(func.coalesce(func.sum(AICostLedger.cost_usd), 0.0)).where(
                    AICostLedger.provider == "anthropic",
                    AICostLedger.created_at >= window_start,
                    AICostLedger.created_at <= now,
                )
            )
    return float(today or 0.0), float(window or 0.0)
