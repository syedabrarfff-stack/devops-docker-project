"""C4-1: Council Assembly Engine — select the right models per task category.

Responsibilities:
  1. Map task_category → ordered list of council member IDs.
  2. Filter by ModelRegistry availability (skip UNAVAILABLE providers).
  3. Persist an `ai_council_assemblies` row so every high-stakes session
     is auditable and feeds the Routing Optimizer (O5-1).
  4. Return an `Assembly` value object consumed by the reasoning stage.

Only the models THIS task needs are assembled — never the full roster.
This keeps cost low and relevance high (§4.4 of Architecture doc).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# ── Council member catalogue ───────────────────────────────────────────────────
# Each entry: (provider, model_name, specialty, default_weight)
# Providers / model_names must exist in the ModelRegistry seed list (F3-2).

_MEMBER_CATALOGUE: dict[str, tuple[str, str, str, float]] = {
    "strategist":  ("anthropic",   "claude-sonnet",     "strategy",    0.28),
    "engineer":    ("bedrock",     "claude-sonnet-4-6", "architecture",0.22),
    "analyst":     ("openai",      "gpt-4o",            "analysis",    0.18),
    "scout":       ("google",      "gemini-pro",        "research",    0.12),
    "speedster":   ("groq",        "llama-4",           "fast",        0.08),
    "contrarian":  ("openrouter",  "deepseek-v4-pro",   "critique",    0.07),
    "economist":   ("openai",      "gpt-4o-mini",       "economics",   0.05),
    # E7-6: Engineering Organization department leads — reuse the same
    # premium models as strategist/engineer above (no new provider/model
    # combos), just distinct specialties/weights for engineering_review.
    "platform_lead":     ("bedrock",   "claude-sonnet-4-6", "platform_architecture",   0.30),
    "backend_lead":      ("anthropic", "claude-sonnet",     "backend_engineering",     0.25),
    "security_lead":     ("anthropic", "claude-sonnet",     "security_review",         0.25),
    "architecture_lead": ("bedrock",   "claude-sonnet-4-6", "cross_department_design", 0.20),
}

# Task category → ordered member IDs (most important first).
# The reasoning stage calls them in parallel; order only matters for tie-breaking.
_CATEGORY_MEMBERS: dict[str, list[str]] = {
    "strategy":    ["strategist", "analyst", "contrarian"],
    "reasoning":   ["strategist", "engineer", "contrarian"],
    "analysis":    ["analyst",    "strategist", "scout"],
    "code":        ["engineer",   "contrarian", "speedster"],
    "research":    ["scout",      "analyst",    "speedster"],
    "sales":       ["strategist", "analyst",    "economist"],
    "financial":   ["analyst",    "strategist", "economist"],
    "legal":       ["strategist", "contrarian", "analyst"],
    "security":    ["engineer",   "contrarian", "analyst"],
    "fast":        ["speedster",  "contrarian"],
    "general":     ["strategist", "engineer",   "analyst"],
    "long_context":["scout",      "strategist", "analyst"],
    # E7-6: cross-department engineering decisions — peer review / conflict
    # resolution for the Engineering Organization. Reuses the SAME
    # assembly/reasoning/conflict-resolution/recommendation pipeline as
    # every other category above — no parallel council.
    "engineering_review": ["architecture_lead", "security_lead", "platform_lead", "backend_lead"],
}

# Minimum members required before a quorum is meaningful.
_MIN_QUORUM = 2
# Actionable confidence threshold (0–1 scale).
CONFIDENCE_THRESHOLD = 0.75


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class CouncilMember:
    """One selected council participant."""
    member_id: str
    provider: str
    model_name: str
    specialty: str
    weight: float
    registry_id: Optional[uuid.UUID] = None


@dataclass
class Assembly:
    """Result of the assembly stage — passed to reasoning, conflict, and recommendation."""
    assembly_id: uuid.UUID
    task_category: str
    question: str
    context: dict
    members: list[CouncilMember]
    assembled_at: datetime
    db_id: Optional[uuid.UUID] = None   # ai_council_assemblies PK
    context_snapshot_id: Optional[str] = None

    @property
    def member_ids(self) -> list[str]:
        return [m.member_id for m in self.members]

    @property
    def registry_ids(self) -> list[uuid.UUID]:
        return [m.registry_id for m in self.members if m.registry_id]


# ── Assembler ─────────────────────────────────────────────────────────────────

class CouncilAssembler:
    """Selects and assembles the council for one high-stakes decision.

    Filters out UNAVAILABLE providers using the ModelRegistry in-process
    cache (sub-millisecond, no DB hit).
    """

    def __init__(self) -> None:
        self._registry = None

    def _get_registry(self):
        if self._registry is None:
            from app.services.fabric.model_registry import get_model_registry
            self._registry = get_model_registry()
        return self._registry

    async def assemble(
        self,
        task_category: str,
        question: str,
        context: dict,
        session: Optional[AsyncSession] = None,
    ) -> Assembly:
        """Select council members and persist the assembly record.

        Args:
            task_category: Task type string (e.g. "strategy", "code").
            question:       The decision / question the council will reason about.
            context:        Arbitrary JSON context shared with all members.
            session:        AsyncSession for persisting ai_council_assemblies row.
                            If None, the row is skipped (useful in tests).

        Returns:
            Assembly ready for the parallel reasoning stage.
        """
        cat = task_category.lower().strip()
        member_ids = _CATEGORY_MEMBERS.get(cat, _CATEGORY_MEMBERS["general"])

        registry = self._get_registry()
        selected: list[CouncilMember] = []

        for mid in member_ids:
            catalogue_entry = _MEMBER_CATALOGUE.get(mid)
            if catalogue_entry is None:
                log.warning("council.assembly: unknown member_id %r — skipping", mid)
                continue

            provider, model_name, specialty, default_weight = catalogue_entry

            # Skip if the ModelRegistry knows this model is UNAVAILABLE.
            entry = registry.get(provider, model_name)
            if entry is not None and entry.status == "unavailable":
                log.info(
                    "council.assembly: member %r (%s/%s) is UNAVAILABLE — skipping",
                    mid, provider, model_name,
                )
                continue

            selected.append(CouncilMember(
                member_id=mid,
                provider=provider,
                model_name=model_name,
                specialty=specialty,
                weight=float(entry.availability_pct / 100.0 * default_weight)
                       if entry else default_weight,
                registry_id=entry.id if entry else None,
            ))

        if not selected:
            log.warning(
                "council.assembly: all preferred members unavailable for %r — "
                "using full catalogue fallback", cat
            )
            for mid, (provider, model_name, specialty, weight) in _MEMBER_CATALOGUE.items():
                entry = registry.get(provider, model_name)
                if entry is None or entry.status != "unavailable":
                    selected.append(CouncilMember(
                        member_id=mid, provider=provider, model_name=model_name,
                        specialty=specialty, weight=weight,
                        registry_id=entry.id if entry else None,
                    ))

        # Normalise weights so they sum to 1.0.
        _normalise_weights(selected)

        assembly_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc)

        # Persist to ai_council_assemblies.
        db_id: Optional[uuid.UUID] = None
        if session is not None:
            try:
                db_id = await _persist_assembly(
                    session=session,
                    assembly_id=assembly_id,
                    task_category=cat,
                    members=selected,
                    context=context,
                    now=now,
                )
            except Exception as exc:
                log.warning("council.assembly: DB persist failed (non-fatal) — %s", exc)

        log.info(
            "council assembled %s for task=%r — %d members: %s",
            assembly_id, cat, len(selected), [m.member_id for m in selected],
        )

        return Assembly(
            assembly_id=assembly_id,
            task_category=cat,
            question=question,
            context=context,
            members=selected,
            assembled_at=now,
            db_id=db_id,
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalise_weights(members: list[CouncilMember]) -> None:
    total = sum(m.weight for m in members)
    if total <= 0:
        for m in members:
            m.weight = 1.0 / len(members) if members else 0.0
        return
    for m in members:
        m.weight = round(m.weight / total, 4)


async def _persist_assembly(
    session: AsyncSession,
    assembly_id: uuid.UUID,
    task_category: str,
    members: list[CouncilMember],
    context: dict,
    now: datetime,
) -> uuid.UUID:
    from app.models.fabric import CouncilAssembly

    row = CouncilAssembly(
        id=assembly_id,
        task_category=task_category,
        selected_models=[m.registry_id for m in members if m.registry_id],
        task_context={
            "member_ids": [m.member_id for m in members],
            "providers":  [m.provider  for m in members],
            "weights":    {m.member_id: m.weight for m in members},
            **({} if not context else {"user_context": context}),
        },
        assembled_at=now,
        outcome_verified=False,
    )
    session.add(row)
    await session.flush()   # get the row ID without committing
    return row.id


# ── Singleton ─────────────────────────────────────────────────────────────────

_assembler: Optional[CouncilAssembler] = None


def get_council_assembler() -> CouncilAssembler:
    global _assembler
    if _assembler is None:
        _assembler = CouncilAssembler()
    return _assembler
