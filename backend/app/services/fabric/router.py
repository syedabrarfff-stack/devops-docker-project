"""F3-3: Intelligent Fabric Router — task-profile → model selection → fallback chain.

This is the single entry point for ALL AI calls within JARVIS.  §4.1 of the
Architecture doc states: "No subsystem calls an LLM directly. Ever."

Every request flows through:

    caller → FabricRouter.chat(...)
                 │
                 ├─ 1. TokenGovernor  — check budget / rate limit
                 │        ↓ over budget → use cheap fallback chain
                 ├─ 2. ModelRegistry  — get ordered fallback chain for task_type
                 │        ↓ filter unavailable providers
                 ├─ 3. existing AIRouter.chat() — actual LLM call with circuit-breaker
                 │        ↓ on success
                 ├─ 4. ResponseVerifier — hallucination / policy / format check
                 │        ↓ on success
                 ├─ 5. ModelRegistry.record_call() — update metrics
                 │        ↓
                 └─ 6. TokenGovernor.record_usage() — track spend
                          ↓
                       return FabricResponse

If any provider in the chain fails, the next provider is tried automatically
(the existing AIRouter already handles this via ROUTING_TABLE, so we delegate
the retry loop to it while using our registry to filter the chain).

The FabricRouter does NOT replace the existing AIRouter — it wraps it.
The existing `router.chat()` method remains the actual transport layer.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from app.services.ai.base_provider import AIResponse, Message, TaskType
from app.services.fabric.model_registry import get_model_registry
from app.services.fabric.token_governor import get_token_governor
from app.services.fabric.response_verifier import get_response_verifier, VerificationResult

log = logging.getLogger(__name__)

# If the ResponseVerifier's confidence is below this threshold, we still
# return the response but set requires_review=True so callers can escalate.
_VERIFY_PASS_THRESHOLD = 0.70


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class FabricResponse:
    """Enriched response from the Intelligent Router.

    Extends the existing AIResponse with fabric-layer metadata:
    verification result, token governor status, and routing trace.
    """
    # Core response (forwarded from the underlying AIRouter).
    content: str
    model: str
    provider: str
    task_type: str
    tokens_used: int = 0
    latency_ms: int = 0
    cost_estimate_usd: float = 0.0
    error: Optional[str] = None

    # Fabric-layer enrichments.
    verification: Optional[VerificationResult] = None
    over_budget: bool = False
    rate_limited: bool = False
    fallback_chain_used: Optional[list[tuple[str, str]]] = None
    routing_trace: list[str] = field(default_factory=list)

    @property
    def passed_verification(self) -> bool:
        if self.verification is None:
            return True   # no verification requested
        return self.verification.passed

    @property
    def requires_review(self) -> bool:
        if self.verification is None:
            return False
        return self.verification.requires_review


# ── Core service ───────────────────────────────────────────────────────────────

class FabricRouter:
    """Intelligent routing layer for all JARVIS AI calls.

    Instantiate once as a module-level singleton via :func:`get_fabric_router`.
    """

    def __init__(self) -> None:
        self._registry  = get_model_registry()
        self._governor  = get_token_governor()
        self._verifier  = get_response_verifier()

        # Lazy import the existing AIRouter to avoid circular imports at module
        # load time (app/services/ai/router.py imports cost_tracker, etc.).
        self._ai_router = None

    def _get_ai_router(self):
        if self._ai_router is None:
            from app.services.ai.router import AIRouter
            self._ai_router = AIRouter()
        return self._ai_router

    # ── Primary chat interface ─────────────────────────────────────────────────

    async def chat(
        self,
        messages: list[Message] | list[dict],
        task_type: Optional[str | TaskType] = None,
        *,
        system_prompt: str = "",
        max_tokens: int = 2048,
        expected_format: Optional[str] = None,
        verify: bool = True,
        force_provider: Optional[str] = None,
        force_model: Optional[str] = None,
        db_session=None,
    ) -> FabricResponse:
        """Route a chat request through the full Fabric pipeline.

        Args:
            messages:        List of Message objects or dicts with role/content.
            task_type:       TaskType enum or string.  Auto-detected if None.
            system_prompt:   Override the default JARVIS system prompt.
            max_tokens:      Max tokens to generate.
            expected_format: "json", "markdown", or "plain" — enables format check.
            verify:          Run ResponseVerifier on the result (default True).
            force_provider:  Bypass routing and use this provider directly.
            force_model:     Model key to use when force_provider is set.
            db_session:      AsyncSession for PolicyEngine check in verifier.

        Returns:
            FabricResponse with content, verification result, and routing trace.
        """
        trace: list[str] = []
        t0 = time.monotonic()

        # ── 1. Normalise task type ─────────────────────────────────────────────
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type.lower())
            except ValueError:
                task_type = TaskType.GENERAL
        task_type = task_type or TaskType.GENERAL
        task_type_str = task_type.value
        trace.append(f"task_type={task_type_str}")

        # ── 2. Budget / rate gate ─────────────────────────────────────────────
        over_budget = False
        rate_limited = False
        fallback_chain: Optional[list[tuple[str, str]]] = None

        if await self._governor.is_rate_limited():
            log.warning("fabric_router: rate limit exceeded")
            rate_limited = True
            trace.append("rate_limited=true")

        usage_pct = await self._governor.get_usage_pct()
        if usage_pct >= 0.80:
            over_budget = True
            fallback_chain = await self._governor.get_cheap_fallback(task_type_str)
            trace.append(f"over_budget=true({usage_pct:.0%}) cheap_chain={len(fallback_chain)}")
        else:
            # Healthy budget: get ordered chain from Model Registry.
            chain = self._registry.get_fallback_chain(task_type_str)
            fallback_chain = chain or None
            trace.append(f"chain={len(chain or [])}_providers")

        # ── 3. Delegate to existing AIRouter ──────────────────────────────────
        ai_router = self._get_ai_router()
        from app.services.ai.router import JARVIS_SYSTEM_PROMPT
        sp = system_prompt or JARVIS_SYSTEM_PROMPT

        try:
            # If a specific fallback chain is desired and the first entry differs
            # from the routing table default, use force_provider/force_model for
            # the first attempt (subsequent fallbacks are handled by AIRouter).
            effective_provider = force_provider
            effective_model    = force_model

            if not effective_provider and fallback_chain:
                effective_provider, effective_model = fallback_chain[0]

            ai_response, tt_used = await ai_router.chat(
                messages=messages,
                task_type=task_type,
                force_provider=effective_provider,
                force_model=effective_model,
                system_prompt=sp,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            log.error("fabric_router: ai_router.chat failed — %s", exc)
            latency = int((time.monotonic() - t0) * 1000)
            return FabricResponse(
                content="",
                model="",
                provider="",
                task_type=task_type_str,
                latency_ms=latency,
                error=str(exc),
                over_budget=over_budget,
                rate_limited=rate_limited,
                fallback_chain_used=fallback_chain,
                routing_trace=trace,
            )

        latency_ms = int((time.monotonic() - t0) * 1000)
        trace.append(f"provider={ai_response.provider} model={ai_response.model} latency={latency_ms}ms")

        # ── 4. ResponseVerifier ───────────────────────────────────────────────
        verification: Optional[VerificationResult] = None
        if verify and ai_response.content:
            try:
                verification = await self._verifier.verify(
                    response=ai_response.content,
                    task_type=task_type_str,
                    expected_format=expected_format,
                    session=db_session,
                )
                trace.append(
                    f"verify={'pass' if verification.passed else 'fail'}"
                    f" confidence={verification.confidence:.2f}"
                )
            except Exception as exc:
                log.warning("fabric_router: verifier error (non-fatal) — %s", exc)

        # ── 5. Update Model Registry metrics ─────────────────────────────────
        success = ai_response.error is None
        if db_session is not None:
            try:
                await self._registry.record_call(
                    provider=ai_response.provider,
                    model_name=ai_response.model,
                    latency_ms=float(latency_ms),
                    success=success,
                    tokens=ai_response.tokens_used,
                    cost_usd=ai_response.cost_estimate_usd,
                    session=db_session,
                )
            except Exception as exc:
                log.warning("fabric_router: record_call error (non-fatal) — %s", exc)

        # ── 6. Token Governor — record spend ──────────────────────────────────
        await self._governor.record_usage(
            provider=ai_response.provider,
            model_name=ai_response.model,
            tokens=ai_response.tokens_used,
            cost_usd=ai_response.cost_estimate_usd,
        )

        return FabricResponse(
            content=ai_response.content,
            model=ai_response.model,
            provider=ai_response.provider,
            task_type=task_type_str,
            tokens_used=ai_response.tokens_used,
            latency_ms=latency_ms,
            cost_estimate_usd=ai_response.cost_estimate_usd,
            error=ai_response.error,
            verification=verification,
            over_budget=over_budget,
            rate_limited=rate_limited,
            fallback_chain_used=fallback_chain,
            routing_trace=trace,
        )

    # ── Convenience helpers ────────────────────────────────────────────────────

    async def status(self) -> dict:
        """Return fabric-level status for the Ops Dashboard."""
        budget_status  = await self._governor.status()
        registry_snap  = self._registry.snapshot()
        active_models  = len(self._registry.list_active())
        return {
            "active_models":  active_models,
            "total_models":   len(registry_snap),
            "budget":         budget_status,
            "model_registry": registry_snap,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_fabric_router: Optional[FabricRouter] = None


def get_fabric_router() -> FabricRouter:
    """Return the module-level FabricRouter singleton."""
    global _fabric_router
    if _fabric_router is None:
        _fabric_router = FabricRouter()
    return _fabric_router
