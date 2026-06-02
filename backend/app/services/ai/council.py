from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.council import AICouncilMemberWeight, AICouncilSession
from app.middleware import observe_ai_latency, record_ai_cost, record_council_session
from app.services.ai.base_provider import Message
from app.services.ai.cost_tracker import estimate_cost
from app.services.ai.router import JARVIS_SYSTEM_PROMPT, ai_router

logger = logging.getLogger(__name__)

COUNCIL_MEMBERS = [
    {"id": "strategist", "provider": "anthropic", "model": "claude-opus-4-8", "weight": 0.25, "specialty": "strategy"},
    {"id": "engineer", "provider": "bedrock", "model": "claude-sonnet-4-6", "weight": 0.25, "specialty": "architecture"},
    {"id": "analyst", "provider": "openai", "model": "gpt-4o", "weight": 0.15, "specialty": "analysis"},
    {"id": "scout", "provider": "google", "model": "gemini-1.5-pro", "weight": 0.10, "specialty": "research"},
    {"id": "speedster", "provider": "groq", "model": "llama-3.3-70b", "weight": 0.08, "specialty": "fast"},
    {"id": "contrarian", "provider": "mistral", "model": "mistral-large", "weight": 0.07, "specialty": "critique"},
    {"id": "economist", "provider": "zhipuai", "model": "glm-4", "weight": 0.05, "specialty": "economics"},
    {"id": "innovator", "provider": "minimax", "model": "abab6.5s", "weight": 0.05, "specialty": "creative"},
]

MODEL_CALL_OVERRIDES = {
    ("anthropic", "claude-opus-4-8"): "claude-opus-4-7",
    ("bedrock", "claude-sonnet-4-6"): "global.anthropic.claude-sonnet-4-6",
    ("google", "gemini-1.5-pro"): "gemini-pro-latest",
    ("groq", "llama-3.3-70b"): "llama-3.3-70b-versatile",
    ("mistral", "mistral-large"): "mistral-large-latest",
    ("zhipuai", "glm-4"): "glm-4",
    ("minimax", "abab6.5s"): "MiniMax-Text-01",
}


@dataclass
class CouncilResult:
    decision: str
    score: float
    reasoning: str
    member_votes: list[dict[str, Any]]
    session_id: str
    quorum_met: bool
    responses_count: int
    duration_ms: int
    winner_model: str | None
    cost_estimate_usd: float

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


class IntelligenceCouncil:
    async def convene(self, question: str, context: dict, council_type: str = "standard", tenant_id=None) -> CouncilResult:
        tenant_uuid = _tenant_uuid(tenant_id)
        started = time.monotonic()
        weights = await self._ensure_member_weights(tenant_uuid)

        tasks = [
            self._ask_member(
                member=member,
                weight=weights.get(member["id"], float(member["weight"])),
                question=question,
                context=context or {},
                council_type=council_type or "standard",
            )
            for member in COUNCIL_MEMBERS
        ]
        member_votes = await asyncio.gather(*tasks)

        responses = [vote for vote in member_votes if vote.get("responded")]
        responses_count = len(responses)
        quorum_met = responses_count >= 5
        score = round(sum(float(vote.get("weight_used", 0.0)) * float(vote.get("vote_score", 0.0)) for vote in member_votes), 2)

        if not quorum_met:
            decision = "CAPTAIN_REVIEW"
        elif score >= 80:
            decision = "APPROVE"
        elif score >= 60:
            decision = "CAPTAIN_REVIEW"
        else:
            decision = "REJECT"

        reasoning = _aggregate_reasoning(member_votes, quorum_met)
        winner_model = _winner_model(member_votes)
        cost_estimate_usd = round(sum(float(vote.get("cost_estimate_usd", 0.0)) for vote in member_votes), 6)
        duration_ms = int((time.monotonic() - started) * 1000)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                council_session = AICouncilSession(
                    tenant_id=tenant_uuid,
                    question=question,
                    context_json=context or {},
                    council_type=council_type or "standard",
                    votes_json=member_votes,
                    result=decision,
                    consensus_score=score,
                    winner_model=winner_model,
                    reasoning=reasoning,
                    quorum_met=quorum_met,
                    responses_count=responses_count,
                    duration_ms=duration_ms,
                    cost_estimate_usd=cost_estimate_usd,
                )
                session.add(council_session)
                await session.flush()
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="ai_council_convened",
                        entity_type="ai_council_session",
                        entity_id=council_session.id,
                        actor="IntelligenceCouncil",
                        after_json={
                            "question": question,
                            "decision": decision,
                            "score": score,
                            "responses_count": responses_count,
                            "quorum_met": quorum_met,
                        },
                        details={"council_session_id": str(council_session.id), "decision": decision},
                    )
                )
                await session.refresh(council_session)
                session_id = str(council_session.id)

        record_council_session(decision)
        return CouncilResult(
            decision=decision,
            score=score,
            reasoning=reasoning,
            member_votes=member_votes,
            session_id=session_id,
            quorum_met=quorum_met,
            responses_count=responses_count,
            duration_ms=duration_ms,
            winner_model=winner_model,
            cost_estimate_usd=cost_estimate_usd,
        )

    async def adjust_weights_monthly(self, tenant_id=None) -> None:
        tenant_uuid = _tenant_uuid(tenant_id)
        cutoff = datetime.now(UTC) - timedelta(days=35)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                weight_rows = await self._weight_rows(session, tenant_uuid)
                weights = {row.member_id: row for row in weight_rows}

                sessions = (
                    await session.execute(
                        select(AICouncilSession)
                        .where(AICouncilSession.tenant_id == tenant_uuid, AICouncilSession.created_at >= cutoff)
                        .order_by(AICouncilSession.created_at.desc())
                    )
                ).scalars().all()
                audit_rows = (
                    await session.execute(
                        select(AuditLog).where(AuditLog.tenant_id == tenant_uuid, AuditLog.created_at >= cutoff)
                    )
                ).scalars().all()
                outcomes = _extract_outcomes(audit_rows)

                for council_session in sessions:
                    outcome = outcomes.get(str(council_session.id))
                    if outcome is None:
                        continue
                    for vote in council_session.votes_json or []:
                        if not vote.get("responded"):
                            continue
                        row = weights.get(vote.get("member_id"))
                        if not row:
                            continue
                        predicted_success = float(vote.get("vote_score", 0)) >= 60
                        if predicted_success == outcome:
                            row.weight = min(0.35, float(row.weight) + 0.02)
                            row.correct_predictions += 1
                        else:
                            row.weight = max(0.03, float(row.weight) - 0.01)
                            row.wrong_predictions += 1
                        row.last_adjusted_at = datetime.now(UTC)

                _normalize_weights(list(weights.values()))
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="ai_council_weights_adjusted",
                        entity_type="ai_council_member_weights",
                        actor="IntelligenceCouncil",
                        after_json={
                            row.member_id: {
                                "weight": row.weight,
                                "correct_predictions": row.correct_predictions,
                                "wrong_predictions": row.wrong_predictions,
                            }
                            for row in weights.values()
                        },
                        details={"members": len(weights)},
                    )
                )

    async def recent_sessions(self, tenant_id=None, limit: int = 25) -> list[dict[str, Any]]:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(AICouncilSession)
                        .where(AICouncilSession.tenant_id == tenant_uuid)
                        .order_by(AICouncilSession.created_at.desc())
                        .limit(max(1, min(int(limit or 25), 100)))
                    )
                ).scalars().all()
                return [_serialize_session(row) for row in rows]

    async def health(self, tenant_id=None) -> dict[str, Any]:
        weights = {}
        if tenant_id or settings.JARVIS_DEFAULT_TENANT_ID:
            weights = await self._ensure_member_weights(_tenant_uuid(tenant_id))
        provider_status = ai_router.get_provider_status()
        return {
            "members_total": len(COUNCIL_MEMBERS),
            "quorum_required": 5,
            "decision_thresholds": {"approve": 80, "captain_review": 60, "reject_below": 60},
            "members": [
                {
                    **member,
                    "weight": weights.get(member["id"], member["weight"]),
                    "available": provider_status.get(member["provider"], {}).get("available", False),
                    "provider_models": provider_status.get(member["provider"], {}).get("models", []),
                }
                for member in COUNCIL_MEMBERS
            ],
        }

    async def _ensure_member_weights(self, tenant_id: uuid.UUID) -> dict[str, float]:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_id))
                rows = await self._weight_rows(session, tenant_id)
                existing = {row.member_id: row for row in rows}
                for member in COUNCIL_MEMBERS:
                    if member["id"] not in existing:
                        row = AICouncilMemberWeight(
                            tenant_id=tenant_id,
                            member_id=member["id"],
                            provider=member["provider"],
                            model=member["model"],
                            specialty=member["specialty"],
                            weight=float(member["weight"]),
                        )
                        session.add(row)
                        existing[member["id"]] = row
                await session.flush()
                return {member_id: float(row.weight) for member_id, row in existing.items()}

    async def _weight_rows(self, session, tenant_id: uuid.UUID) -> list[AICouncilMemberWeight]:
        return list(
            (
                await session.execute(
                    select(AICouncilMemberWeight).where(AICouncilMemberWeight.tenant_id == tenant_id)
                )
            ).scalars().all()
        )

    async def _ask_member(self, member: dict[str, Any], weight: float, question: str, context: dict, council_type: str) -> dict:
        provider = ai_router._providers.get(member["provider"])
        base_vote = {
            "member_id": member["id"],
            "provider": member["provider"],
            "model": member["model"],
            "model_invoked": _model_for_call(member),
            "specialty": member["specialty"],
            "weight": round(float(weight), 4),
            "weight_used": 0.0,
            "vote_score": 0.0,
            "confidence": 0.0,
            "recommendation": "CAPTAIN_REVIEW",
            "reasoning": "",
            "risks": [],
            "evidence": [],
            "responded": False,
            "timeout": False,
            "error": None,
            "tokens_used": 0,
            "latency_ms": 0,
            "cost_estimate_usd": 0.0,
        }
        if not provider or not provider.is_available():
            return {**base_vote, "error": "provider_unavailable"}

        messages = [
            Message(
                role="user",
                content=_member_prompt(member, question, context, council_type),
            )
        ]
        started = time.monotonic()
        try:
            response = await asyncio.wait_for(
                provider.chat(
                    messages=messages,
                    model_id=base_vote["model_invoked"],
                    system_prompt=_council_system_prompt(member),
                    max_tokens=900,
                ),
                timeout=30,
            )
        except asyncio.TimeoutError:
            return {**base_vote, "timeout": True, "error": "timeout"}
        except Exception as exc:
            return {**base_vote, "error": str(exc)}

        latency_ms = int((time.monotonic() - started) * 1000)
        if response.error:
            return {**base_vote, "latency_ms": latency_ms, "error": response.error}

        parsed = _parse_vote(response.content)
        vote_score = _bounded_float(parsed.get("vote_score"), default=60)
        cost = response.cost_estimate_usd or estimate_cost(member["provider"], response.model, response.tokens_used)
        observe_ai_latency(member["provider"], response.model or base_vote["model_invoked"], latency_ms)
        record_ai_cost(member["provider"], response.model or base_vote["model_invoked"], "council", float(cost or 0.0))
        return {
            **base_vote,
            "model_invoked": response.model or base_vote["model_invoked"],
            "weight_used": round(float(weight), 4),
            "vote_score": vote_score,
            "confidence": _bounded_float(parsed.get("confidence"), default=70),
            "recommendation": str(parsed.get("recommendation") or _recommendation_from_score(vote_score)).upper(),
            "reasoning": str(parsed.get("reasoning") or response.content).strip()[:4000],
            "risks": _as_string_list(parsed.get("risks")),
            "evidence": _as_string_list(parsed.get("evidence")),
            "responded": True,
            "tokens_used": int(response.tokens_used or 0),
            "latency_ms": latency_ms,
            "cost_estimate_usd": float(cost or 0.0),
        }


def _member_prompt(member: dict, question: str, context: dict, council_type: str) -> str:
    return (
        f"Council type: {council_type}\n"
        f"Your role: {member['id']} / {member['specialty']}\n\n"
        f"Question:\n{question}\n\n"
        f"Context JSON:\n{json.dumps(context or {}, default=str, indent=2)[:6000]}\n\n"
        "Return strict JSON only with keys: vote_score (0-100), recommendation "
        "(APPROVE, CAPTAIN_REVIEW, or REJECT), confidence (0-100), reasoning, risks, evidence. "
        "Be independent and do not assume the other members agree."
    )


def _council_system_prompt(member: dict) -> str:
    return (
        f"{JARVIS_SYSTEM_PROMPT}\n\n"
        "You are one independent member of the JARVIS Intelligence Council. "
        f"Council member: {member['id']}. Specialty: {member['specialty']}. "
        "Evaluate the decision with evidence, risk, and business impact. "
        "Never write client-facing copy here; this is internal Captain-only governance."
    )


def _model_for_call(member: dict) -> str:
    return MODEL_CALL_OVERRIDES.get((member["provider"], member["model"]), member["model"])


def _parse_vote(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    score = 80 if re.search(r"\bapprove\b", text, re.I) else 45 if re.search(r"\breject|block\b", text, re.I) else 65
    return {"vote_score": score, "recommendation": _recommendation_from_score(score), "reasoning": text}


def _bounded_float(value, default: float) -> float:
    try:
        return round(max(0.0, min(100.0, float(value))), 2)
    except (TypeError, ValueError):
        return float(default)


def _recommendation_from_score(score: float) -> str:
    if score >= 80:
        return "APPROVE"
    if score >= 60:
        return "CAPTAIN_REVIEW"
    return "REJECT"


def _as_string_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item)[:500] for item in value]
    if value:
        return [str(value)[:500]]
    return []


def _aggregate_reasoning(votes: list[dict], quorum_met: bool) -> str:
    header = "Quorum met." if quorum_met else "Quorum not met; Captain review required."
    lines = [header]
    for vote in votes:
        status = "responded" if vote.get("responded") else f"unavailable ({vote.get('error') or 'no response'})"
        lines.append(
            f"{vote['member_id']} [{vote['provider']}/{vote['model']}]: "
            f"{status}; score={vote.get('vote_score', 0)}; confidence={vote.get('confidence', 0)}. "
            f"{vote.get('reasoning', '')[:500]}"
        )
    return "\n".join(lines)


def _winner_model(votes: list[dict]) -> str | None:
    responded = [vote for vote in votes if vote.get("responded")]
    if not responded:
        return None
    winner = max(responded, key=lambda vote: float(vote.get("weight_used", 0)) * float(vote.get("vote_score", 0)))
    return f"{winner['provider']}/{winner.get('model_invoked') or winner['model']}"


def _extract_outcomes(audit_rows: list[AuditLog]) -> dict[str, bool]:
    outcomes: dict[str, bool] = {}
    for row in audit_rows:
        payload = row.after_json or row.details or {}
        session_id = payload.get("council_session_id")
        if not session_id:
            continue
        if "outcome_success" in payload:
            outcomes[str(session_id)] = bool(payload["outcome_success"])
        elif str(row.action or "").lower().endswith("_succeeded"):
            outcomes[str(session_id)] = True
        elif str(row.action or "").lower().endswith("_failed"):
            outcomes[str(session_id)] = False
    return outcomes


def _normalize_weights(rows: list[AICouncilMemberWeight]) -> None:
    if not rows:
        return
    total = sum(max(0.03, min(0.35, float(row.weight))) for row in rows)
    if total <= 0:
        return
    for row in rows:
        capped = max(0.03, min(0.35, float(row.weight)))
        row.weight = round(capped / total, 4)


def _serialize_session(row: AICouncilSession) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "question": row.question,
        "council_type": row.council_type,
        "context": row.context_json,
        "member_votes": row.votes_json,
        "decision": row.result,
        "score": row.consensus_score,
        "winner_model": row.winner_model,
        "reasoning": row.reasoning,
        "quorum_met": row.quorum_met,
        "responses_count": row.responses_count,
        "duration_ms": row.duration_ms,
        "cost_estimate_usd": row.cost_estimate_usd,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _tenant_uuid(tenant_id) -> uuid.UUID:
    resolved = tenant_id or settings.JARVIS_DEFAULT_TENANT_ID
    if not resolved:
        raise ValueError("tenant_id is required")
    return uuid.UUID(str(resolved))


intelligence_council = IntelligenceCouncil()
