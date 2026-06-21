"""
JARVIS Competitive Moat Engine — Measures and grows Aliyar Solutions' strategic defensibility.
7 moat dimensions. Competitive threat scoring. Strategic defense reports.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

SCHEDULED_JOB_COUNT = 33
ACTIVE_ROUTE_COUNT = 57
AIONX_ORGAN_COUNT = 31
INTELLIGENCE_ENGINE_COUNT = 33


def _coerce_tenant_id(tenant_id: Any) -> UUID:
    if tenant_id is None:
        return SYSTEM_TENANT_ID
    if isinstance(tenant_id, UUID):
        return tenant_id
    return UUID(str(tenant_id))


def _defensibility_label(score: float) -> str:
    if score >= 80:
        return "fortress"
    if score >= 60:
        return "strong"
    if score >= 40:
        return "building"
    return "vulnerable"


class MoatEngine:
    """Tracks and grows Aliyar Solutions' competitive moat across 7 strategic dimensions."""

    async def compute_moat_score(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import MoatMetrics
        tid = _coerce_tenant_id(tenant_id)

        lead_count = 0
        client_count = 0
        won_lead_count = 0
        replied_lead_count = 0
        delivery_lessons_count = 0
        knowledge_count = 0

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)

            try:
                from app.models.lead import Lead, LeadStatus
                lead_result = await db.execute(
                    select(func.count()).select_from(Lead).where(Lead.tenant_id == tid)
                )
                lead_count = lead_result.scalar() or 0

                won_result = await db.execute(
                    select(func.count()).select_from(Lead).where(
                        Lead.tenant_id == tid,
                        Lead.status == LeadStatus.WON,
                    )
                )
                won_lead_count = won_result.scalar() or 0

                replied_result = await db.execute(
                    select(func.count()).select_from(Lead).where(
                        Lead.tenant_id == tid,
                        Lead.status.in_([LeadStatus.REPLIED, LeadStatus.DEMO, LeadStatus.PROPOSAL, LeadStatus.WON]),
                    )
                )
                replied_lead_count = replied_result.scalar() or 0
            except Exception as exc:
                logger.debug("Lead query failed in moat engine: %s", exc)

            try:
                from app.models.revenue import Client, ClientStatus
                client_result = await db.execute(
                    select(func.count()).select_from(Client).where(
                        Client.tenant_id == tid,
                        Client.status == ClientStatus.ACTIVE,
                    )
                )
                client_count = client_result.scalar() or 0
            except Exception as exc:
                logger.debug("Client query failed in moat engine: %s", exc)

            try:
                from app.models.truth_resilience import DeliveryLesson
                dl_result = await db.execute(
                    select(func.count()).select_from(DeliveryLesson).where(DeliveryLesson.tenant_id == tid)
                )
                delivery_lessons_count = dl_result.scalar() or 0
            except Exception as exc:
                logger.debug("Delivery lesson query failed: %s", exc)

            try:
                from app.models.knowledge import KnowledgeBase, SOPDocument
                kb_result = await db.execute(
                    select(func.count()).select_from(KnowledgeBase).where(KnowledgeBase.tenant_id == tid)
                )
                knowledge_count = kb_result.scalar() or 0
            except Exception as exc:
                logger.debug("Knowledge query failed: %s", exc)

            # ── 7 Dimension Scores (0-100) ────────────────────────────────────
            # 1. Proprietary Data: grows with every lead and client touched
            proprietary_data_score = min(100.0, lead_count / 10 + client_count * 20)

            # 2. Case Studies: delivered projects = referenceable proof
            case_study_count = won_lead_count

            # 3. Delivery Intelligence: grows with every lesson extracted
            delivery_intelligence_score = min(100.0, delivery_lessons_count * 10 + INTELLIGENCE_ENGINE_COUNT * 1.5)

            # 4. Relationship Graph: network value from all engaged contacts
            relationship_graph_score = min(100.0, (client_count + replied_lead_count) * 5)

            # 5. Institutional Wisdom: knowledge base + SOPs
            institutional_wisdom_score = min(100.0, knowledge_count * 5 + AIONX_ORGAN_COUNT * 1.5)

            # 6. Automation Advantage: built-in system advantage (near-maximum already)
            automation_advantage_score = min(100.0, SCHEDULED_JOB_COUNT * 2 + ACTIVE_ROUTE_COUNT * 0.5)

            # 7. Operational Speed: baseline until benchmarks available
            operational_speed_score = 72.0  # Benchmark: 33 automated jobs running 24/7

            # Weighted moat score (equal weights across 7 dimensions)
            dimension_scores = [
                proprietary_data_score,
                min(100.0, case_study_count * 20),
                delivery_intelligence_score,
                relationship_graph_score,
                institutional_wisdom_score,
                automation_advantage_score,
                operational_speed_score,
            ]
            moat_score = sum(dimension_scores) / len(dimension_scores)
            competitive_threat_score = 100.0 - moat_score

            # ── Generate Analysis ─────────────────────────────────────────────
            threats = []
            strengths = []
            actions = []

            if case_study_count == 0:
                threats.append("Zero case studies — no social proof to close enterprise clients")
                actions.append("PRIORITY: Convert first client to completed project → extract case study immediately")
            elif case_study_count < 3:
                threats.append(f"Only {case_study_count} case study(ies) — limited credibility for large deals")
                actions.append("Build case study library: 1-page PDF per completed project with ROI metrics")

            if lead_count < 50:
                threats.append(f"Small proprietary database ({lead_count} leads) — limited targeting data")
                actions.append("Scale lead discovery: 48 leads/day pipeline generates 1,440 monthly")
            else:
                strengths.append(f"Growing proprietary lead database: {lead_count} leads enriched with AI signals")

            if delivery_lessons_count > 0:
                strengths.append(f"Delivery intelligence accumulating: {delivery_lessons_count} lessons in institutional memory")
            else:
                threats.append("No delivery lessons yet — first project will unlock this moat dimension")

            if automation_advantage_score >= 70:
                strengths.append(f"Automation advantage: {SCHEDULED_JOB_COUNT} scheduled intelligence jobs running 24/7")
                strengths.append(f"System scale: {AIONX_ORGAN_COUNT} AIONx organs + {INTELLIGENCE_ENGINE_COUNT} intelligence engines operational")

            if client_count >= 3:
                strengths.append(f"Relationship network: {client_count} active clients generating referral potential")
            else:
                actions.append("Build relationship graph: Each client relationship multiplies referral potential")

            if institutional_wisdom_score >= 50:
                strengths.append("Institutional wisdom layer active: knowledge base + AIONx memory compounding")

            actions.append("Publish monthly 'AI Operations Insights' to build thought leadership moat")
            actions.append("Create proprietary methodology document — 'The Aliyar Operating System'")

            metrics = MoatMetrics(
                tenant_id=tid,
                snapshot_date=datetime.now(timezone.utc),
                moat_score=round(moat_score, 2),
                proprietary_data_score=round(proprietary_data_score, 2),
                case_study_count=case_study_count,
                delivery_intelligence_score=round(delivery_intelligence_score, 2),
                relationship_graph_score=round(relationship_graph_score, 2),
                institutional_wisdom_score=round(institutional_wisdom_score, 2),
                automation_advantage_score=round(automation_advantage_score, 2),
                operational_speed_score=round(operational_speed_score, 2),
                competitive_threat_score=round(competitive_threat_score, 2),
                defensibility_report=self._render_report(moat_score, dimension_scores, threats, strengths),
                threats_identified=threats,
                strengths_identified=strengths,
                strategic_actions=actions,
            )
            db.add(metrics)
            await db.commit()

        return {
            "moat_score": round(moat_score, 2),
            "competitive_threat_score": round(competitive_threat_score, 2),
            "defensibility": _defensibility_label(moat_score),
            "dimensions": {
                "proprietary_data": round(proprietary_data_score, 2),
                "case_studies": round(min(100.0, case_study_count * 20), 2),
                "delivery_intelligence": round(delivery_intelligence_score, 2),
                "relationship_graph": round(relationship_graph_score, 2),
                "institutional_wisdom": round(institutional_wisdom_score, 2),
                "automation_advantage": round(automation_advantage_score, 2),
                "operational_speed": round(operational_speed_score, 2),
            },
            "case_study_count": case_study_count,
            "threats_identified": threats,
            "strengths_identified": strengths,
            "strategic_actions": actions,
        }

    def _render_report(self, moat_score: float, dims: list, threats: list, strengths: list) -> str:
        label = _defensibility_label(moat_score)
        lines = [
            f"COMPETITIVE MOAT REPORT — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            f"Moat Score: {moat_score:.1f}/100 | Defensibility: {label.upper()}",
            "",
            f"STRENGTHS ({len(strengths)}):",
        ]
        for s in strengths:
            lines.append(f"  ✓ {s}")
        lines += ["", f"THREATS ({len(threats)}):"]
        for t in threats:
            lines.append(f"  ✗ {t}")
        lines += ["", "STRATEGIC PRIORITY: Build case studies → grow relationship graph → compound institutional wisdom."]
        return "\n".join(lines)

    async def get_moat_report(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import MoatMetrics
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(MoatMetrics).where(MoatMetrics.tenant_id == tid).order_by(MoatMetrics.snapshot_date.desc()).limit(12)
            )
            rows = result.scalars().all()

        if not rows:
            return {"status": "no_data", "message": "Run /moat/scan first"}

        latest = rows[0]
        return {
            "latest": {
                "moat_score": latest.moat_score,
                "competitive_threat_score": latest.competitive_threat_score,
                "defensibility": _defensibility_label(latest.moat_score or 0),
                "dimensions": {
                    "proprietary_data": latest.proprietary_data_score,
                    "case_studies": min(100.0, (latest.case_study_count or 0) * 20),
                    "delivery_intelligence": latest.delivery_intelligence_score,
                    "relationship_graph": latest.relationship_graph_score,
                    "institutional_wisdom": latest.institutional_wisdom_score,
                    "automation_advantage": latest.automation_advantage_score,
                    "operational_speed": latest.operational_speed_score,
                },
                "case_study_count": latest.case_study_count,
                "defensibility_report": latest.defensibility_report,
                "threats_identified": latest.threats_identified,
                "strengths_identified": latest.strengths_identified,
                "strategic_actions": latest.strategic_actions,
                "snapshot_date": latest.snapshot_date.isoformat() if latest.snapshot_date else None,
            },
            "history": [
                {
                    "date": r.snapshot_date.isoformat() if r.snapshot_date else None,
                    "moat_score": r.moat_score,
                    "competitive_threat_score": r.competitive_threat_score,
                }
                for r in rows
            ],
        }

    async def run_weekly_moat_scan(self, tenant_id: Any) -> dict:
        result = await self.compute_moat_score(tenant_id)
        score = result["moat_score"]
        label = _defensibility_label(score)
        msg = f"🏰 Weekly Moat Scan | Score: {score:.0f}/100 ({label}) | Threat: {result['competitive_threat_score']:.0f}/100"
        try:
            from app.services.notifications import notify_telegram
            await notify_telegram(msg)
        except Exception as exc:
            logger.debug("Moat scan notification failed: %s", exc)
        return result


moat_engine = MoatEngine()
