"""
Layer 2 — Council Intelligence Loop (Milestone Engine)

For every milestone a DIO submits:
1. Generate milestone PDF (ReportLab)
2. Submit to AI Council for review and scoring
3. Council generates improvement PDF with specific recommendations
4. Send improvement PDF back to DIO
5. DIO implements improvements
6. Council scores implementation → closes loop
"""
from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.department_intelligence import (
    DepartmentIntelligenceOfficer,
    DepartmentMilestone,
    MilestoneStatus,
)
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.council import intelligence_council
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)


class MilestoneEngine:
    """
    Drives the full Council Intelligence Loop for department milestones.
    DIO submits → PDF → Council reviews → improvement PDF → DIO implements → loop closes.
    """

    async def run_milestone_council_loop(
        self, tenant_id: str, milestone_id: str
    ) -> dict[str, Any]:
        """Execute the full Council review loop for a milestone."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))

            milestone = await db.get(DepartmentMilestone, uuid.UUID(milestone_id))
            if not milestone:
                raise ValueError(f"Milestone {milestone_id} not found")

            # Step 1: Generate milestone PDF
            pdf_bytes = await self._generate_milestone_pdf(milestone)
            milestone.milestone_pdf_url = f"/pdfs/milestones/{milestone_id}.pdf"
            milestone.status = MilestoneStatus.IN_REVIEW.value
            await db.commit()

            # Step 2: Council review
            council_question = self._build_council_question(milestone)
            council_context = self._build_council_context(milestone)

            council_result = await intelligence_council.convene(
                question=council_question,
                context=council_context,
                council_type="milestone_review",
                tenant_id=tenant_id,
            )

            # Step 3: Generate improvement PDF from Council findings
            improvement_pdf_bytes = await self._generate_improvement_pdf(
                milestone, council_result
            )

            # Step 4: Persist Council results
            async with AsyncSessionLocal() as db2:
                await set_tenant_context(db2, str(tenant_uuid))
                m = await db2.get(DepartmentMilestone, uuid.UUID(milestone_id))
                if m:
                    m.council_session_id = uuid.UUID(council_result.session_id)
                    m.council_score = council_result.score
                    m.council_verdict = council_result.decision
                    m.council_recommendations = await self._extract_recommendations(
                        council_result.reasoning
                    )
                    m.improvement_pdf_url = f"/pdfs/improvements/{milestone_id}_improvement.pdf"
                    m.status = (
                        MilestoneStatus.IMPROVING.value
                        if council_result.decision in ("CAPTAIN_REVIEW", "REJECT")
                        else MilestoneStatus.COUNCIL_QUEUE.value
                    )

                    # Update DIO improvement count
                    dio = await db2.get(DepartmentIntelligenceOfficer, m.dio_id)
                    if dio:
                        dio.improvements_received = (dio.improvements_received or 0) + 1

                    await db2.commit()

        logger.info(
            "Council loop completed: milestone=%s | score=%.1f | verdict=%s",
            milestone_id,
            council_result.score,
            council_result.decision,
        )

        return {
            "milestone_id": milestone_id,
            "council_session_id": council_result.session_id,
            "council_score": council_result.score,
            "council_verdict": council_result.decision,
            "recommendations_count": len(m.council_recommendations) if m else 0,
            "milestone_pdf_url": f"/pdfs/milestones/{milestone_id}.pdf",
            "improvement_pdf_url": f"/pdfs/improvements/{milestone_id}_improvement.pdf",
            "status": m.status if m else None,
        }

    async def run_bulk_milestone_review(self, tenant_id: str) -> dict[str, Any]:
        """Process all pending milestones awaiting Council review."""
        tenant_uuid = uuid.UUID(str(tenant_id))
        processed = 0
        failed = 0

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            pending = (
                await db.execute(
                    select(DepartmentMilestone)
                    .where(
                        DepartmentMilestone.tenant_id == tenant_uuid,
                        DepartmentMilestone.status == MilestoneStatus.ACHIEVED.value,
                    )
                    .order_by(DepartmentMilestone.impact_score.desc())
                    .limit(10)
                )
            ).scalars().all()
            milestone_ids = [str(m.id) for m in pending]

        for mid in milestone_ids:
            try:
                await self.run_milestone_council_loop(tenant_id, mid)
                processed += 1
            except Exception as exc:
                logger.warning("Milestone council loop failed: %s | %s", mid, exc)
                failed += 1

        return {
            "processed": processed,
            "failed": failed,
            "total": len(milestone_ids),
            "tenant_id": str(tenant_uuid),
        }

    async def generate_department_milestone_report(
        self, tenant_id: str, department_code: str | None = None
    ) -> dict[str, Any]:
        """Generate a comprehensive milestone performance report for a department."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            query = (
                select(DepartmentMilestone)
                .where(DepartmentMilestone.tenant_id == tenant_uuid)
                .order_by(DepartmentMilestone.created_at.desc())
                .limit(100)
            )
            if department_code:
                query = query.where(DepartmentMilestone.department_code == department_code)

            milestones = (await db.execute(query)).scalars().all()

        total = len(milestones)
        implemented = sum(1 for m in milestones if m.status == MilestoneStatus.IMPLEMENTED.value)
        avg_council_score = (
            sum(m.council_score or 0 for m in milestones if m.council_score) /
            max(1, sum(1 for m in milestones if m.council_score))
        )
        avg_impact = sum(m.impact_score or 0 for m in milestones) / max(1, total)

        return {
            "tenant_id": str(tenant_uuid),
            "department_code": department_code,
            "total_milestones": total,
            "implemented": implemented,
            "implementation_rate": round(implemented / max(1, total) * 100, 1),
            "avg_council_score": round(avg_council_score, 1),
            "avg_impact_score": round(avg_impact, 1),
            "by_status": self._count_by_status(milestones),
            "by_type": self._count_by_type(milestones),
            "top_milestones": [
                {
                    "id": str(m.id),
                    "title": m.title,
                    "department_code": m.department_code,
                    "impact_score": m.impact_score,
                    "council_score": m.council_score,
                    "status": m.status,
                }
                for m in sorted(milestones, key=lambda x: x.impact_score or 0, reverse=True)[:5]
            ],
        }

    async def _generate_milestone_pdf(self, milestone: DepartmentMilestone) -> bytes:
        """Generate a professional PDF for the milestone submission."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                HRFlowable,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("Title", parent=styles["Heading1"],
                                          fontSize=20, textColor=colors.HexColor("#1a1a2e"),
                                          spaceAfter=6)
            subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"],
                                             fontSize=11, textColor=colors.HexColor("#4a4a8a"),
                                             spaceAfter=12)
            body_style = ParagraphStyle("Body", parent=styles["Normal"],
                                         fontSize=10, leading=14, spaceAfter=8)
            section_style = ParagraphStyle("Section", parent=styles["Heading2"],
                                            fontSize=13, textColor=colors.HexColor("#2c3e50"),
                                            spaceBefore=12, spaceAfter=6)

            elements = []

            # Header
            elements.append(Paragraph("ALIYAR SOLUTIONS", title_style))
            elements.append(Paragraph(
                f"Department Intelligence Report — {milestone.department_code.upper()}",
                subtitle_style
            ))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
            elements.append(Spacer(1, 0.3*cm))

            # Metadata table
            meta_data = [
                ["Milestone ID", str(milestone.id)[:16] + "..."],
                ["Department", milestone.department_code.upper()],
                ["Type", milestone.milestone_type.upper()],
                ["Submitted", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
                ["Impact Score", f"{milestone.impact_score:.1f}/100"],
            ]
            meta_table = Table(meta_data, colWidths=[5*cm, 11*cm])
            meta_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f8")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccccdd")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(meta_table)
            elements.append(Spacer(1, 0.5*cm))

            # Title & description
            elements.append(Paragraph("MILESTONE TITLE", section_style))
            elements.append(Paragraph(milestone.title, body_style))
            elements.append(Spacer(1, 0.3*cm))

            elements.append(Paragraph("DESCRIPTION", section_style))
            elements.append(Paragraph(milestone.description[:2000], body_style))
            elements.append(Spacer(1, 0.3*cm))

            # Metrics
            if milestone.metrics:
                elements.append(Paragraph("KEY METRICS", section_style))
                metric_rows = [["Metric", "Value"]]
                for k, v in milestone.metrics.items():
                    metric_rows.append([str(k).replace("_", " ").title(), str(v)])
                metric_table = Table(metric_rows, colWidths=[8*cm, 8*cm])
                metric_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccccdd")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f8fc")]),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]))
                elements.append(metric_table)

            # Footer
            elements.append(Spacer(1, cm))
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#ccccdd")))
            elements.append(Paragraph(
                f"JARVIS Intelligence System | Aliyar Solutions | {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8,
                               textColor=colors.grey, alignment=1)
            ))

            doc.build(elements)
            return buf.getvalue()

        except ImportError:
            logger.warning("ReportLab not installed — returning empty PDF placeholder")
            return b"%PDF-1.4 placeholder"

    async def _generate_improvement_pdf(
        self, milestone: DepartmentMilestone, council_result: Any
    ) -> bytes:
        """Generate Council improvement recommendations PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle("Title", parent=styles["Heading1"],
                                          fontSize=18, textColor=colors.HexColor("#2c3e50"),
                                          spaceAfter=6)
            section_style = ParagraphStyle("Section", parent=styles["Heading2"],
                                            fontSize=13, textColor=colors.HexColor("#1a1a2e"),
                                            spaceBefore=10, spaceAfter=6)
            body_style = ParagraphStyle("Body", parent=styles["Normal"],
                                         fontSize=10, leading=14, spaceAfter=8)
            verdict_color = (
                colors.HexColor("#27ae60") if council_result.decision == "APPROVE"
                else colors.HexColor("#e74c3c")
            )
            verdict_style = ParagraphStyle("Verdict", parent=styles["Heading1"],
                                            fontSize=16, textColor=verdict_color, spaceAfter=8)

            elements = []
            elements.append(Paragraph("ALIYAR SOLUTIONS — COUNCIL IMPROVEMENT DIRECTIVE", title_style))
            elements.append(Paragraph(
                f"Milestone: {milestone.title[:80]}",
                ParagraphStyle("Sub", parent=styles["Normal"], fontSize=11,
                               textColor=colors.HexColor("#666699"), spaceAfter=8)
            ))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
            elements.append(Spacer(1, 0.4*cm))

            elements.append(Paragraph("COUNCIL VERDICT", section_style))
            elements.append(Paragraph(f"Decision: {council_result.decision}", verdict_style))
            elements.append(Paragraph(
                f"Consensus Score: {council_result.score:.1f}/100 | "
                f"Council Members: {council_result.responses_count} | "
                f"Quorum Met: {'YES' if council_result.quorum_met else 'NO'}",
                body_style
            ))
            elements.append(Spacer(1, 0.3*cm))

            elements.append(Paragraph("COUNCIL ANALYSIS & REASONING", section_style))
            elements.append(Paragraph(council_result.reasoning[:3000], body_style))
            elements.append(Spacer(1, 0.3*cm))

            elements.append(Paragraph("IMPLEMENTATION DIRECTIVE", section_style))
            elements.append(Paragraph(
                "The Department Intelligence Officer is directed to review the above Council findings "
                "and implement all recommendations within 72 hours. Progress must be reported back "
                "to the Council through the JARVIS milestone system.",
                body_style
            ))

            elements.append(Spacer(1, cm))
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#ccccdd")))
            elements.append(Paragraph(
                f"AI Council | JARVIS Intelligence System | Aliyar Solutions | {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8,
                               textColor=colors.grey, alignment=1)
            ))

            doc.build(elements)
            return buf.getvalue()

        except ImportError:
            return b"%PDF-1.4 improvement-placeholder"

    def _build_council_question(self, milestone: DepartmentMilestone) -> str:
        return (
            f"Evaluate this milestone from the {milestone.department_code.upper()} department "
            f"at Aliyar Solutions:\n\n"
            f"Title: {milestone.title}\n\n"
            f"Description: {milestone.description[:500]}\n\n"
            f"Type: {milestone.milestone_type}\n"
            f"Impact Score (self-assessed): {milestone.impact_score:.1f}/100\n\n"
            f"Provide: (1) validation score, (2) quality assessment, "
            f"(3) specific improvement recommendations, (4) implementation priority."
        )

    def _build_council_context(self, milestone: DepartmentMilestone) -> dict:
        return {
            "milestone_id": str(milestone.id),
            "department": milestone.department_code,
            "type": milestone.milestone_type,
            "metrics": milestone.metrics or {},
            "company": "Aliyar Solutions",
            "review_purpose": "milestone_quality_improvement",
        }

    async def _extract_recommendations(self, reasoning: str) -> list[str]:
        """Extract structured recommendations from Council reasoning."""
        prompt = f"""Extract the top 5 specific, actionable improvement recommendations from this Council analysis.
Return as a JSON array of strings. Each string should be one clear action item.
Return only valid JSON, no markdown.

Analysis: {reasoning[:2000]}"""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.FAST,
            )
            items = json.loads(response.content.strip())
            return items if isinstance(items, list) else [str(reasoning[:200])]
        except Exception:
            return [reasoning[:200]]

    def _count_by_status(self, milestones: list) -> dict:
        counts: dict = {}
        for m in milestones:
            counts[m.status] = counts.get(m.status, 0) + 1
        return counts

    def _count_by_type(self, milestones: list) -> dict:
        counts: dict = {}
        for m in milestones:
            counts[m.milestone_type] = counts.get(m.milestone_type, 0) + 1
        return counts


milestone_engine = MilestoneEngine()
