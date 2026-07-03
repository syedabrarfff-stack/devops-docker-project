"""C4-2: Parallel Reasoning Orchestrator.

All members reason INDEPENDENTLY on the SAME context snapshot.  No member
sees another's answer before submitting their own — this prevents anchoring
and ensures genuine diversity of reasoning.

Flow per member:
  1. Build a council-specific prompt (role, question, shared context).
  2. Call FabricRouter.chat() — enforces §4.1 Iron Rule.
  3. Parse the JSON vote from the response.
  4. Return a MemberResponse regardless of success/failure.

All members run in parallel via asyncio.gather with individual timeouts.
The reasoning stage also holds the ContextSync advisory lock for the
duration so no other task mutates the memory snapshot mid-reasoning.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.services.council.assembly import Assembly, CouncilMember

log = logging.getLogger(__name__)

# Per-member reasoning timeout (seconds).
_MEMBER_TIMEOUT = 45.0

# Member prompt format — structured JSON output.
_MEMBER_PROMPT_TEMPLATE = """\
Council session {assembly_id}
Your role: {member_id} / {specialty}
Task category: {task_category}

QUESTION:
{question}

CONTEXT:
{context_json}

Instructions:
You are an independent council member. Reason from your specialty perspective.
Return ONLY valid JSON with these exact keys:
  "vote_score":       integer 0-100 (your confidence the recommended action should proceed)
  "recommendation":   one of "APPROVE", "CAPTAIN_REVIEW", "REJECT"
  "confidence":       integer 0-100 (how certain you are of your assessment)
  "reasoning":        string (your concise analysis, ≤500 chars)
  "risks":            list of strings (top 3 risks)
  "evidence":         list of strings (supporting points for your position)

Do not reference other council members. Reason independently.
"""


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class MemberResponse:
    """One council member's reasoning result."""
    member_id: str
    provider: str
    model_name: str
    specialty: str
    weight: float
    vote_score: float       # 0–100
    confidence: float       # 0–100
    recommendation: str     # APPROVE | CAPTAIN_REVIEW | REJECT
    reasoning: str
    risks: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    responded: bool = False
    tokens_used: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "member_id":      self.member_id,
            "provider":       self.provider,
            "model_name":     self.model_name,
            "specialty":      self.specialty,
            "weight":         self.weight,
            "vote_score":     self.vote_score,
            "confidence":     self.confidence,
            "recommendation": self.recommendation,
            "reasoning":      self.reasoning,
            "risks":          self.risks,
            "evidence":       self.evidence,
            "responded":      self.responded,
            "tokens_used":    self.tokens_used,
            "latency_ms":     self.latency_ms,
            "cost_usd":       self.cost_usd,
            "error":          self.error,
        }


# ── Orchestrator ───────────────────────────────────────────────────────────────

class ParallelReasoner:
    """Runs all selected council members in parallel, returns their responses."""

    def __init__(self) -> None:
        self._fabric = None
        self._ctx_sync = None

    def _get_fabric(self):
        if self._fabric is None:
            from app.services.fabric.router import get_fabric_router
            self._fabric = get_fabric_router()
        return self._fabric

    def _get_ctx_sync(self):
        if self._ctx_sync is None:
            from app.services.fabric.context_sync import get_context_sync
            self._ctx_sync = get_context_sync()
        return self._ctx_sync

    async def reason(
        self,
        assembly: Assembly,
        session=None,
    ) -> list[MemberResponse]:
        """Run all assembly members in parallel and collect responses.

        A ContextSync snapshot is acquired before reasoning begins and
        released (via discard) afterwards.  The snapshot_id is stored on
        the assembly object so the recommendation stage can merge outcomes.

        Args:
            assembly: The Assembly from C4-1.
            session:  Optional AsyncSession for ContextSync.snapshot().

        Returns:
            List of MemberResponse (one per member, including failures).
        """
        ctx_sync = self._get_ctx_sync()
        snapshot_id: Optional[str] = None

        # Acquire context snapshot if a DB session is available.
        if session is not None:
            try:
                snap = await ctx_sync.snapshot(
                    task_id=str(assembly.assembly_id),
                    session=session,
                )
                snapshot_id = snap.snapshot_id
                assembly.context_snapshot_id = snapshot_id
                log.debug(
                    "council.reasoning: context snapshot %s captured (%d entries)",
                    snapshot_id, len(snap.entries),
                )
            except Exception as exc:
                log.warning("council.reasoning: context snapshot failed — %s", exc)

        # Run all members in parallel.
        tasks = [
            self._ask_member(assembly=assembly, member=member)
            for member in assembly.members
        ]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        responses: list[MemberResponse] = []
        for item in raw:
            if isinstance(item, BaseException):
                log.warning("council.reasoning: member raised — %s", item)
            elif isinstance(item, MemberResponse):
                responses.append(item)

        # Release snapshot (discard = no merge; merge happens in C4-6).
        if snapshot_id:
            try:
                ctx_sync.discard(snapshot_id)
            except Exception:
                pass

        log.info(
            "council.reasoning: %d/%d members responded for assembly %s",
            sum(1 for r in responses if r.responded),
            len(assembly.members),
            assembly.assembly_id,
        )
        return responses

    async def _ask_member(
        self,
        assembly: Assembly,
        member: CouncilMember,
    ) -> MemberResponse:
        """Call one member via FabricRouter; parse the JSON vote."""
        base = MemberResponse(
            member_id=member.member_id,
            provider=member.provider,
            model_name=member.model_name,
            specialty=member.specialty,
            weight=member.weight,
            vote_score=50.0,
            confidence=50.0,
            recommendation="CAPTAIN_REVIEW",
            reasoning="",
        )

        prompt = _MEMBER_PROMPT_TEMPLATE.format(
            assembly_id=assembly.assembly_id,
            member_id=member.member_id,
            specialty=member.specialty,
            task_category=assembly.task_category,
            question=assembly.question,
            context_json=json.dumps(assembly.context or {}, default=str)[:3000],
        )

        messages = [{"role": "user", "content": prompt}]
        t0 = time.monotonic()
        fabric = self._get_fabric()

        try:
            result = await asyncio.wait_for(
                fabric.chat(
                    messages=messages,
                    task_type=assembly.task_category,
                    system_prompt=_COUNCIL_SYSTEM_PROMPT.format(
                        member_id=member.member_id,
                        specialty=member.specialty,
                    ),
                    max_tokens=700,
                    verify=False,   # verification runs on the final recommendation, not per-member
                    force_provider=member.provider,
                    force_model=member.model_name,
                ),
                timeout=_MEMBER_TIMEOUT,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)

            if result.error:
                base.error = result.error
                base.latency_ms = latency_ms
                return base

            parsed = _parse_json_vote(result.content)
            return MemberResponse(
                member_id=member.member_id,
                provider=result.provider or member.provider,
                model_name=result.model or member.model_name,
                specialty=member.specialty,
                weight=member.weight,
                vote_score=_clamp(parsed.get("vote_score", 50)),
                confidence=_clamp(parsed.get("confidence", 50)),
                recommendation=_normalise_rec(parsed.get("recommendation")),
                reasoning=str(parsed.get("reasoning", result.content or ""))[:800],
                risks=_as_str_list(parsed.get("risks")),
                evidence=_as_str_list(parsed.get("evidence")),
                responded=True,
                tokens_used=result.tokens_used,
                latency_ms=latency_ms,
                cost_usd=result.cost_estimate_usd,
            )

        except asyncio.TimeoutError:
            base.error = "timeout"
            base.latency_ms = int((time.monotonic() - t0) * 1000)
            return base
        except Exception as exc:
            base.error = str(exc)
            base.latency_ms = int((time.monotonic() - t0) * 1000)
            return base


# ── Helpers ────────────────────────────────────────────────────────────────────

_COUNCIL_SYSTEM_PROMPT = (
    "You are council member '{member_id}', specialty: {specialty}. "
    "You are one independent adviser to JARVIS — the executive intelligence core of Aliyar Solutions. "
    "Evaluate strictly from your specialty. Return ONLY valid JSON. No prose outside JSON."
)


def _parse_json_vote(content: str) -> dict:
    text = (content or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    # Heuristic fallback — infer from keywords.
    score = (80 if re.search(r"\bapprove\b", text, re.I)
             else 40 if re.search(r"\breject\b", text, re.I)
             else 60)
    return {
        "vote_score": score,
        "recommendation": _score_to_rec(score),
        "confidence": 50,
        "reasoning": text[:400],
    }


def _clamp(val, lo: float = 0.0, hi: float = 100.0) -> float:
    try:
        return round(max(lo, min(hi, float(val))), 2)
    except (TypeError, ValueError):
        return 50.0


def _normalise_rec(val) -> str:
    v = str(val or "").upper().strip()
    if v in {"APPROVE"}:
        return "APPROVE"
    if v in {"REJECT"}:
        return "REJECT"
    return "CAPTAIN_REVIEW"


def _score_to_rec(score: float) -> str:
    if score >= 75:
        return "APPROVE"
    if score >= 50:
        return "CAPTAIN_REVIEW"
    return "REJECT"


def _as_str_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(i)[:300] for i in val[:5]]
    return [str(val)[:300]] if val else []


# ── Singleton ─────────────────────────────────────────────────────────────────

_reasoner: Optional[ParallelReasoner] = None


def get_parallel_reasoner() -> ParallelReasoner:
    global _reasoner
    if _reasoner is None:
        _reasoner = ParallelReasoner()
    return _reasoner
