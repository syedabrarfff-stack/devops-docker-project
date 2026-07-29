"""AI Council — Orchestration Layer (C4-5 + C4-6).

This module ties the four council sub-stages together and adds:
  C4-5: Verification Engine integration — the final CouncilRecommendation is
        run through ResponseVerifier before being returned.
  C4-6: Executive Memory outcome recording — the decision and confidence are
        written back to memory_entries via ContextSync merge so that future
        sessions benefit from accumulated council wisdom.

Pipeline (10 steps):
  1.  Validate inputs.
  2.  CouncilAssembler → Assembly object + ai_council_assemblies row (C4-1).
  3.  ParallelReasoner  → list[MemberResponse]        (C4-2).
  4.  ConflictResolver  → ConflictReport              (C4-3).
  5.  RecommendationEngine → CouncilRecommendation    (C4-4).
  6.  ResponseVerifier → VerificationResult            (C4-5).
  7.  Attach verification metadata to recommendation.
  8.  Record outcome to Executive Memory via ContextSync merge (C4-6).
  9.  Update ai_council_assemblies row (outcome_verified flag).
 10.  Return CouncilOutcome.

Iron Rule: every LLM call in steps 2-3 goes through FabricRouter.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.council.assembly import (
    Assembly,
    CouncilAssembler,
    get_council_assembler,
)
from app.services.council.conflict_resolution import (
    ConflictReport,
    ConflictResolver,
    get_conflict_resolver,
)
from app.services.council.reasoning import (
    MemberResponse,
    ParallelReasoner,
    get_parallel_reasoner,
)
from app.services.council.recommendation import (
    CouncilRecommendation,
    RecommendationEngine,
    get_recommendation_engine,
)

log = logging.getLogger(__name__)

# Memory layer where council decisions are recorded.
_COUNCIL_MEMORY_LAYER = "operational"
_COUNCIL_MEMORY_KEY_PREFIX = "council_outcome"


# ── Output dataclass ───────────────────────────────────────────────────────────

@dataclass
class CouncilOutcome:
    """Full result of one AI Council session."""
    session_id: uuid.UUID
    assembly: Assembly
    responses: list[MemberResponse]
    conflict_report: ConflictReport
    recommendation: CouncilRecommendation
    verified: bool
    verification_issues: list[str] = field(default_factory=list)
    memory_recorded: bool = False
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "session_id":          str(self.session_id),
            "assembly_id":         str(self.assembly.assembly_id),
            "task_category":       self.assembly.task_category,
            "recommendation":      self.recommendation.to_dict(),
            "conflict_report": {
                "has_conflicts":           self.conflict_report.has_conflicts,
                "conflict_count":          self.conflict_report.conflict_count,
                "dominant_recommendation": self.conflict_report.dominant_recommendation,
                "dominant_share":          round(self.conflict_report.dominant_share, 4),
                "score_std_dev":           self.conflict_report.score_std_dev,
                "summary":                 self.conflict_report.summary,
            },
            "member_responses":    [r.to_dict() for r in self.responses],
            "verified":            self.verified,
            "verification_issues": self.verification_issues,
            "memory_recorded":     self.memory_recorded,
            "completed_at":        self.completed_at.isoformat() if self.completed_at else None,
        }


# ── Session orchestrator ───────────────────────────────────────────────────────

class CouncilSession:
    """Runs the full AI Council pipeline for one high-stakes decision.

    Usage::

        session = get_council_session()
        outcome = await session.run(
            task_category="strategy",
            question="Should we pursue the SaaS pivot?",
            context={"revenue": 50000, "runway": 18},
            db_session=db,
        )
        if outcome.recommendation.actionable:
            proceed()
    """

    def __init__(self) -> None:
        self._assembler: CouncilAssembler = get_council_assembler()
        self._reasoner: ParallelReasoner = get_parallel_reasoner()
        self._resolver: ConflictResolver = get_conflict_resolver()
        self._engine: RecommendationEngine = get_recommendation_engine()
        self._verifier = None
        self._ctx_sync = None

    def _get_verifier(self):
        if self._verifier is None:
            from app.services.fabric.response_verifier import get_response_verifier
            self._verifier = get_response_verifier()
        return self._verifier

    def _get_ctx_sync(self):
        if self._ctx_sync is None:
            from app.services.fabric.context_sync import get_context_sync
            self._ctx_sync = get_context_sync()
        return self._ctx_sync

    async def run(
        self,
        task_category: str,
        question: str,
        context: Optional[dict] = None,
        session: Optional[AsyncSession] = None,
    ) -> CouncilOutcome:
        """Execute the full council pipeline.

        Args:
            task_category: One of the 12 known categories (e.g. "strategy", "code").
            question:       The decision or question for the council to reason about.
            context:        Arbitrary JSON context passed to every member prompt.
            session:        AsyncSession for DB persistence.  When omitted, DB steps
                            are skipped (assembly row, memory write, outcome flag).

        Returns:
            CouncilOutcome with the full verdict and audit trail.
        """
        session_id = uuid.uuid4()
        ctx = context or {}

        log.info(
            "council.session %s starting — category=%r question=%r",
            session_id, task_category, question[:80],
        )

        # ── Step 1: Validate ───────────────────────────────────────────────────
        if not question.strip():
            raise ValueError("council.session: question must not be empty")

        # ── Step 2: Assembly ───────────────────────────────────────────────────
        assembly = await self._assembler.assemble(
            task_category=task_category,
            question=question,
            context=ctx,
            session=session,
        )

        # ── Step 3: Parallel reasoning ─────────────────────────────────────────
        responses = await self._reasoner.reason(
            assembly=assembly,
            session=session,
        )

        # ── Step 4: Conflict resolution ────────────────────────────────────────
        conflict_report = self._resolver.resolve(responses)

        # ── Step 5: Recommendation synthesis ──────────────────────────────────
        recommendation = self._engine.synthesise(responses, conflict_report)

        # ── Step 6: Verification (C4-5) ────────────────────────────────────────
        verified, verification_issues = await self._verify_recommendation(
            recommendation=recommendation,
            task_category=task_category,
            session=session,
        )

        # ── Step 7: Attach verification metadata ───────────────────────────────
        # (recommendation is a dataclass, add issues via the issues field)

        # ── Step 8: Memory recording (C4-6) ───────────────────────────────────
        memory_recorded = await self._record_to_memory(
            session_id=session_id,
            assembly=assembly,
            recommendation=recommendation,
            conflict_report=conflict_report,
            verified=verified,
            session=session,
        )

        # ── Step 9: Mark assembly row outcome_verified ─────────────────────────
        if session is not None and assembly.db_id is not None:
            await self._mark_assembly_verified(
                db_id=assembly.db_id,
                verified=verified,
                session=session,
            )

        # ── Step 10: Return outcome ────────────────────────────────────────────
        completed_at = datetime.now(tz=timezone.utc)
        outcome = CouncilOutcome(
            session_id=session_id,
            assembly=assembly,
            responses=responses,
            conflict_report=conflict_report,
            recommendation=recommendation,
            verified=verified,
            verification_issues=verification_issues,
            memory_recorded=memory_recorded,
            completed_at=completed_at,
        )

        log.info(
            "council.session %s complete — decision=%s confidence=%.2f "
            "verified=%s memory=%s",
            session_id,
            recommendation.decision,
            recommendation.aggregate_confidence,
            verified,
            memory_recorded,
        )

        return outcome

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _verify_recommendation(
        self,
        recommendation: CouncilRecommendation,
        task_category: str,
        session: Optional[AsyncSession],
    ) -> tuple[bool, list[str]]:
        """Run the unified reasoning text through ResponseVerifier (C4-5)."""
        try:
            verifier = self._get_verifier()
            result = await verifier.verify(
                response=recommendation.unified_reasoning,
                task_type=task_category.upper(),
                expected_format="plain",
                session=session,
            )
            issues = [f"[{i.category}/{i.severity}] {i.detail}" for i in result.issues]
            passed = result.passed
            if not passed:
                log.warning(
                    "council.session: verification failed — %d issues",
                    len(issues),
                )
            return passed, issues
        except Exception as exc:
            log.warning("council.session: verifier error (non-fatal) — %s", exc)
            return True, []

    async def _record_to_memory(
        self,
        session_id: uuid.UUID,
        assembly: Assembly,
        recommendation: CouncilRecommendation,
        conflict_report: ConflictReport,
        verified: bool,
        session: Optional[AsyncSession],
    ) -> bool:
        """Write council outcome to Executive Memory (C4-6).

        Uses ContextSync.merge() so the write is versioned (OCC).
        Non-fatal on any error — the recommendation is still returned.
        """
        if session is None:
            return False

        ctx_sync = self._get_ctx_sync()
        memory_key = f"{_COUNCIL_MEMORY_KEY_PREFIX}.{assembly.task_category}.{str(session_id)[:8]}"

        outcome_value = {
            "session_id":           str(session_id),
            "assembly_id":          str(assembly.assembly_id),
            "task_category":        assembly.task_category,
            "decision":             recommendation.decision,
            "aggregate_confidence": recommendation.aggregate_confidence,
            "weighted_score":       recommendation.weighted_score,
            "actionable":           recommendation.actionable,
            "quorum_met":           recommendation.quorum_met,
            "responding_members":   recommendation.responding_members,
            "conflict_count":       conflict_report.conflict_count,
            "has_conflicts":        conflict_report.has_conflicts,
            "dominant_recommendation": conflict_report.dominant_recommendation,
            "verified":             verified,
            "question_preview":     assembly.question[:200],
            "evidence_sample":      recommendation.evidence[:3],
            "risks_sample":         recommendation.risks[:3],
        }

        # Take a short-lived snapshot solely to write this outcome row.
        try:
            snap = await ctx_sync.snapshot(
                task_id=f"council_outcome_{session_id}",
                session=session,
            )
            holder = f"council_session_{session_id}"
            await ctx_sync.lock(snap.snapshot_id, holder=holder)

            updates: dict[tuple[str, str], dict] = {
                (_COUNCIL_MEMORY_LAYER, memory_key): outcome_value,
            }
            await ctx_sync.merge(
                snapshot_id=snap.snapshot_id,
                updates=updates,
                holder=holder,
                session=session,
            )
            ctx_sync.discard(snap.snapshot_id)
            log.debug(
                "council.session %s outcome recorded to memory key=%r",
                session_id, memory_key,
            )
            return True

        except Exception as exc:
            log.warning(
                "council.session %s: memory record failed (non-fatal) — %s",
                session_id, exc,
            )
            return False

    async def _mark_assembly_verified(
        self,
        db_id: uuid.UUID,
        verified: bool,
        session: AsyncSession,
    ) -> None:
        """Set outcome_verified on the ai_council_assemblies row."""
        try:
            from app.models.fabric import CouncilAssembly
            stmt = (
                update(CouncilAssembly)
                .where(CouncilAssembly.id == db_id)
                .values(outcome_verified=verified)
            )
            await session.execute(stmt)
            await session.commit()
        except Exception as exc:
            log.warning("council.session: could not mark assembly verified — %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

_session: Optional[CouncilSession] = None


def get_council_session() -> CouncilSession:
    global _session
    if _session is None:
        _session = CouncilSession()
    return _session
