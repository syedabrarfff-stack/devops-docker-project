"""
JARVIS Founder Dependency Engine — Measures and reduces Captain's operational dependency.
Goal: reduce dependency from 100 → <20 through automation and autonomous operation.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TARGET_DEPENDENCY_SCORE = 20.0
CRITICAL_THRESHOLD = 80.0
HIGH_THRESHOLD = 60.0

SCHEDULED_JOB_COUNT = 33  # All 33 JARVIS scheduled jobs
ACTIVE_ROUTE_COUNT = 57   # All 57 API route modules


def _coerce_tenant_id(tenant_id: Any) -> UUID:
    if tenant_id is None:
        return SYSTEM_TENANT_ID
    if isinstance(tenant_id, UUID):
        return tenant_id
    return UUID(str(tenant_id))


class FounderDependencyEngine:
    """Tracks how much the company depends on Captain and drives autonomy improvements."""

    async def compute_dependency_score(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import DependencyScore
        tid = _coerce_tenant_id(tenant_id)

        pending_approvals = 0
        total_approvals_30d = 0
        active_clients = 0
        mrr = 0.0
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)

            try:
                from app.models.approval import ApprovalRequest, ApprovalStatus
                pending_result = await db.execute(
                    select(func.count()).select_from(ApprovalRequest).where(
                        ApprovalRequest.tenant_id == tid,
                        ApprovalRequest.status == ApprovalStatus.PENDING,
                    )
                )
                pending_approvals = pending_result.scalar() or 0

                total_result = await db.execute(
                    select(func.count()).select_from(ApprovalRequest).where(
                        ApprovalRequest.tenant_id == tid,
                        ApprovalRequest.created_at >= cutoff,
                    )
                )
                total_approvals_30d = total_result.scalar() or 0
            except Exception as exc:
                logger.debug("Approval query failed: %s", exc)

            try:
                from app.models.revenue import Client, ClientStatus
                client_result = await db.execute(
                    select(func.count(), func.sum(Client.mrr_usd)).select_from(Client).where(
                        Client.tenant_id == tid,
                        Client.status == ClientStatus.ACTIVE,
                    )
                )
                row = client_result.first()
                active_clients = row[0] or 0
                mrr = row[1] or 0.0
            except Exception as exc:
                logger.debug("Client query failed: %s", exc)

            # ── Sub-score computations ────────────────────────────────────────
            # Approval dependency: how many decisions require Captain
            approval_dependency = min(100.0, (pending_approvals / max(total_approvals_30d, 1)) * 100)

            # Revenue dependency: decreases as revenue grows
            revenue_dependency = max(0.0, 100.0 - min(100.0, mrr / 100))

            # Client dependency: each client reduces dependency
            client_dependency = max(0.0, 100.0 - min(100.0, active_clients * 20.0))

            # Decision dependency: JARVIS handles scheduling, outreach, scoring autonomously
            # Reduced by automation coverage — 33 jobs run without Captain
            automation_coverage_pct = min(100.0, (SCHEDULED_JOB_COUNT / 50) * 100)
            decision_dependency = max(20.0, 85.0 - (automation_coverage_pct * 0.5))

            # Operational dependency: 1 - automation_coverage
            operational_dependency = max(0.0, 100.0 - automation_coverage_pct)

            # Weighted overall score
            overall = (
                approval_dependency * 0.25
                + revenue_dependency * 0.20
                + client_dependency * 0.20
                + decision_dependency * 0.20
                + operational_dependency * 0.15
            )

            # ── Generate opportunities ────────────────────────────────────────
            automation_opportunities = [
                "Auto-approve proposals <$2,000 after 48-hour Captain review window",
                "Auto-generate and send SOPs when >3 similar delivery lessons accumulated",
                "Auto-activate outreach sequences without per-email Captain review",
                "Auto-close WON leads when Stripe payment confirmed",
                "Auto-onboard new clients via AIONX pipeline without manual intervention",
            ]
            delegation_opportunities = [
                "Delegate client status reports to Olivia Bennett (auto-generated weekly)",
                "Delegate technical proposal drafts to JARVIS — Captain reviews only final version",
                "Delegate lead scoring decisions below score 40 to automated disqualification",
            ]
            single_point_alerts = []
            if approval_dependency > 80:
                single_point_alerts.append(f"CRITICAL: {pending_approvals} approvals blocked waiting for Captain. Business stalled.")
            if revenue_dependency > 95:
                single_point_alerts.append("CRITICAL: Zero revenue — company survival depends entirely on Captain generating first client.")
            if client_dependency > 80:
                single_point_alerts.append("HIGH: Fewer than 2 clients. Single churn event = 100% revenue loss.")

            # Trend vs previous
            prev_result = await db.execute(
                select(DependencyScore).where(
                    DependencyScore.tenant_id == tid
                ).order_by(DependencyScore.snapshot_date.desc()).limit(1)
            )
            prev = prev_result.scalar_one_or_none()
            trend = "stable"
            if prev and prev.overall_dependency_score is not None:
                if overall < prev.overall_dependency_score - 2:
                    trend = "improving"
                elif overall > prev.overall_dependency_score + 2:
                    trend = "worsening"

            score_row = DependencyScore(
                tenant_id=tid,
                snapshot_date=datetime.now(timezone.utc),
                overall_dependency_score=round(overall, 2),
                approval_dependency=round(approval_dependency, 2),
                revenue_dependency=round(revenue_dependency, 2),
                client_dependency=round(client_dependency, 2),
                decision_dependency=round(decision_dependency, 2),
                operational_dependency=round(operational_dependency, 2),
                automation_coverage_pct=round(automation_coverage_pct, 2),
                pending_approval_count=pending_approvals,
                automation_opportunities=automation_opportunities,
                delegation_opportunities=delegation_opportunities,
                single_point_alerts=single_point_alerts,
                target_score=TARGET_DEPENDENCY_SCORE,
                trend=trend,
            )
            db.add(score_row)
            await db.commit()

        def _status(score: float) -> str:
            if score > CRITICAL_THRESHOLD:
                return "critical"
            if score > HIGH_THRESHOLD:
                return "high"
            if score <= TARGET_DEPENDENCY_SCORE:
                return "target_met"
            return "normal"

        return {
            "overall_dependency_score": round(overall, 2),
            "status": _status(overall),
            "target": TARGET_DEPENDENCY_SCORE,
            "gap_to_target": round(max(0, overall - TARGET_DEPENDENCY_SCORE), 2),
            "trend": trend,
            "sub_scores": {
                "approval_dependency": round(approval_dependency, 2),
                "revenue_dependency": round(revenue_dependency, 2),
                "client_dependency": round(client_dependency, 2),
                "decision_dependency": round(decision_dependency, 2),
                "operational_dependency": round(operational_dependency, 2),
            },
            "automation_coverage_pct": round(automation_coverage_pct, 2),
            "automation_opportunities": automation_opportunities,
            "delegation_opportunities": delegation_opportunities,
            "single_point_alerts": single_point_alerts,
        }

    async def get_dependency_report(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import DependencyScore
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(DependencyScore).where(
                    DependencyScore.tenant_id == tid
                ).order_by(DependencyScore.snapshot_date.desc()).limit(12)
            )
            rows = result.scalars().all()

        if not rows:
            return {"status": "no_data", "message": "Run /founder/assess first"}

        latest = rows[0]
        history = [
            {
                "date": r.snapshot_date.isoformat() if r.snapshot_date else None,
                "overall_dependency_score": r.overall_dependency_score,
                "trend": r.trend,
            }
            for r in rows
        ]

        return {
            "latest": {
                "overall_dependency_score": latest.overall_dependency_score,
                "status": "critical" if (latest.overall_dependency_score or 0) > CRITICAL_THRESHOLD else "normal",
                "target": TARGET_DEPENDENCY_SCORE,
                "approval_dependency": latest.approval_dependency,
                "revenue_dependency": latest.revenue_dependency,
                "client_dependency": latest.client_dependency,
                "decision_dependency": latest.decision_dependency,
                "operational_dependency": latest.operational_dependency,
                "automation_coverage_pct": latest.automation_coverage_pct,
                "single_point_alerts": latest.single_point_alerts,
                "automation_opportunities": latest.automation_opportunities,
                "delegation_opportunities": latest.delegation_opportunities,
                "trend": latest.trend,
            },
            "history": history,
            "action_items": latest.automation_opportunities[:3] if latest.automation_opportunities else [],
        }

    async def run_weekly_assessment(self, tenant_id: Any) -> dict:
        tid = _coerce_tenant_id(tenant_id)
        result = await self.compute_dependency_score(tid)
        score = result["overall_dependency_score"]
        if score > CRITICAL_THRESHOLD:
            msg = f"🚨 Founder Dependency CRITICAL: {score:.0f}/100. Company is fully Captain-dependent. Immediate autonomy expansion required."
            try:
                from app.services.notifications import notify_telegram
                await notify_telegram(msg)
            except Exception as exc:
                logger.warning("Failed to send founder dependency alert: %s", exc)
        return result


founder_dependency_engine = FounderDependencyEngine()
