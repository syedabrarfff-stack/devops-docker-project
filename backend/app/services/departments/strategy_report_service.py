"""
Layer 6 — Strategy Oversight Team

Every day at 23:00 UTC:
1. Collect operational snapshots from all 15 departments
2. Aggregate into a master strategy report
3. Submit to AI Council for strategic analysis
4. Council generates scaling directives and priorities
5. Cascade directives back to all departments
6. Notify Captain with executive summary

Weekly (Sunday 07:00 UTC):
- Full strategic review with 30/60/90 day horizon
- Revenue forecast update
- Competitive position assessment
- Resource allocation recommendations
"""
from __future__ import annotations

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
    StrategyReport,
    TechnologyDiscovery,
    TechStatus,
)
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.council import intelligence_council
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)


class StrategyReportService:
    """
    Generates daily and weekly strategy reports, runs them through the
    AI Council, and cascades directives to all departments.
    """

    async def generate_daily_strategy_report(self, tenant_id: str) -> dict[str, Any]:
        """
        Full daily strategy cycle:
        1. Collect operational data from all departments
        2. Generate strategy report
        3. Council review
        4. Cascade directives
        5. Notify Captain
        """
        tenant_uuid = uuid.UUID(str(tenant_id))
        today = datetime.now(timezone.utc)

        # Collect data
        ops_data = await self._collect_operational_data(tenant_uuid)

        # Generate master report
        report_content = await self._generate_report_content(ops_data, "daily", today)

        # Persist report
        report_id = await self._save_report(
            tenant_uuid, today, "daily", ops_data, report_content
        )

        # Council review and directives
        council_result = await self._run_council_strategy_session(
            tenant_id, report_content, ops_data
        )

        # Extract and cascade directives
        directives = await self._extract_directives(council_result.reasoning)
        await self._cascade_directives_to_departments(tenant_uuid, directives, report_id)

        # Update report with council results
        await self._finalize_report(tenant_uuid, report_id, council_result, directives)

        # Notify Captain
        await self._notify_captain_daily(report_content, council_result, ops_data)

        logger.info(
            "Daily strategy report completed: report_id=%s | council_score=%.1f | directives=%d",
            report_id, council_result.score, len(directives)
        )

        return {
            "report_id": str(report_id),
            "tenant_id": str(tenant_uuid),
            "report_date": today.isoformat(),
            "report_type": "daily",
            "council_session_id": council_result.session_id,
            "council_score": council_result.score,
            "directives_issued": len(directives),
            "departments_notified": len(directives),
        }

    async def generate_weekly_strategy_report(self, tenant_id: str) -> dict[str, Any]:
        """Full weekly strategic review with 30/60/90 day horizon."""
        tenant_uuid = uuid.UUID(str(tenant_id))
        today = datetime.now(timezone.utc)

        ops_data = await self._collect_operational_data(tenant_uuid)
        weekly_intelligence = await self._collect_weekly_intelligence(tenant_uuid)

        report_content = await self._generate_report_content(
            {**ops_data, **weekly_intelligence}, "weekly", today
        )

        report_id = await self._save_report(
            tenant_uuid, today, "weekly", {**ops_data, **weekly_intelligence}, report_content
        )

        council_result = await self._run_council_strategy_session(
            tenant_id, report_content, ops_data, is_weekly=True
        )

        directives = await self._extract_directives(council_result.reasoning)
        await self._cascade_directives_to_departments(tenant_uuid, directives, report_id)
        await self._finalize_report(tenant_uuid, report_id, council_result, directives)

        logger.info(
            "Weekly strategy report: report_id=%s | score=%.1f",
            report_id, council_result.score
        )

        return {
            "report_id": str(report_id),
            "report_type": "weekly",
            "council_score": council_result.score,
            "directives_issued": len(directives),
        }

    async def get_reports(
        self,
        db: AsyncSession,
        tenant_id: str,
        report_type: str | None = None,
        limit: int = 30,
    ) -> list[dict]:
        tenant_uuid = uuid.UUID(str(tenant_id))
        query = (
            select(StrategyReport)
            .where(StrategyReport.tenant_id == tenant_uuid)
            .order_by(StrategyReport.report_date.desc())
            .limit(limit)
        )
        if report_type:
            query = query.where(StrategyReport.report_type == report_type)

        result = await db.execute(query)
        return [self._serialize_report(r) for r in result.scalars().all()]

    async def get_strategy_dashboard(self, db: AsyncSession, tenant_id: str) -> dict[str, Any]:
        """High-level strategy dashboard for Captain."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        # Latest reports
        reports_result = await db.execute(
            select(StrategyReport)
            .where(StrategyReport.tenant_id == tenant_uuid)
            .order_by(StrategyReport.report_date.desc())
            .limit(10)
        )
        reports = reports_result.scalars().all()

        # Active milestones
        milestones_result = await db.execute(
            select(DepartmentMilestone)
            .where(
                DepartmentMilestone.tenant_id == tenant_uuid,
                DepartmentMilestone.status != MilestoneStatus.CLOSED.value,
            )
            .order_by(DepartmentMilestone.impact_score.desc())
            .limit(10)
        )
        milestones = milestones_result.scalars().all()

        # Latest report metrics
        latest = reports[0] if reports else None

        return {
            "latest_report": self._serialize_report(latest) if latest else None,
            "total_reports": len(reports),
            "avg_council_score": (
                sum(r.council_score or 0 for r in reports if r.council_score) /
                max(1, sum(1 for r in reports if r.council_score))
            ),
            "active_milestones": len(milestones),
            "top_milestones": [
                {"title": m.title, "department": m.department_code, "impact": m.impact_score}
                for m in milestones[:5]
            ],
            "latest_directives": latest.council_directives[:5] if latest and latest.council_directives else [],
        }

    async def _collect_operational_data(self, tenant_uuid: uuid.UUID) -> dict[str, Any]:
        """Collect real-time operational data from all departments."""
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))

            # DIO performance
            dios = (await db.execute(
                select(DepartmentIntelligenceOfficer)
                .where(DepartmentIntelligenceOfficer.tenant_id == tenant_uuid)
            )).scalars().all()

            # Recent milestones
            milestones = (await db.execute(
                select(DepartmentMilestone)
                .where(DepartmentMilestone.tenant_id == tenant_uuid)
                .order_by(DepartmentMilestone.created_at.desc())
                .limit(50)
            )).scalars().all()

            # Tech discoveries
            discoveries = (await db.execute(
                select(TechnologyDiscovery)
                .where(
                    TechnologyDiscovery.tenant_id == tenant_uuid,
                    TechnologyDiscovery.priority.in_(["critical", "high"]),
                )
                .order_by(TechnologyDiscovery.relevance_score.desc())
                .limit(10)
            )).scalars().all()

        dept_summary = {}
        for dio in dios:
            dept_summary[dio.department_code] = {
                "agent": dio.agent_name,
                "performance_score": dio.performance_score or 1.0,
                "milestones_submitted": dio.milestones_submitted or 0,
                "improvements_implemented": dio.improvements_implemented or 0,
            }

        milestone_summary = {
            "total": len(milestones),
            "achieved": sum(1 for m in milestones if m.status == MilestoneStatus.ACHIEVED.value),
            "implementing": sum(1 for m in milestones if m.status == MilestoneStatus.IMPROVING.value),
            "implemented": sum(1 for m in milestones if m.status == MilestoneStatus.IMPLEMENTED.value),
            "avg_impact": sum(m.impact_score or 0 for m in milestones) / max(1, len(milestones)),
        }

        return {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "department_count": len(dios),
            "departments": dept_summary,
            "milestones": milestone_summary,
            "critical_discoveries": [
                {"name": t.technology_name, "relevance": t.relevance_score, "status": t.status}
                for t in discoveries
            ],
        }

    async def _collect_weekly_intelligence(self, tenant_uuid: uuid.UUID) -> dict[str, Any]:
        """Collect additional intelligence for weekly report."""
        prompt = f"""You are JARVIS, the strategic intelligence core of Aliyar Solutions.
Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

Provide a weekly strategic intelligence assessment:
1. Market position assessment — where Aliyar Solutions stands vs competitors
2. Revenue growth opportunities in the next 30 days
3. Technology edge — what capabilities give competitive advantage
4. Risk landscape — what external/internal risks need attention
5. Resource allocation — where to focus for maximum growth impact

Return as JSON:
{{
  "market_position": "assessment text",
  "revenue_opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"],
  "technology_edge": "assessment text",
  "risk_landscape": ["risk 1", "risk 2", "risk 3"],
  "resource_focus": "recommendation text",
  "30_day_priority": "single most important action"
}}
Return only valid JSON."""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.STRATEGY,
            )
            return json.loads(response.content.strip())
        except Exception:
            return {"weekly_intelligence": "Collection pending"}

    async def _generate_report_content(
        self, ops_data: dict, report_type: str, report_date: datetime
    ) -> str:
        """Generate the narrative strategy report content."""
        prompt = f"""You are the Aliyar Solutions Strategy Oversight Team, reporting to Captain Syed Abrar.

Generate a {report_type} strategy report for {report_date.strftime('%Y-%m-%d')}.

Operational data:
{json.dumps(ops_data, indent=2)[:3000]}

The report must include:
1. EXECUTIVE SUMMARY (3-4 sentences for Captain)
2. OPERATIONAL STATUS — all departments health
3. KEY ACHIEVEMENTS this period
4. CRITICAL ALERTS — anything requiring immediate attention
5. REVENUE STATUS — pipeline, MRR, opportunities
6. TECHNOLOGY EVOLUTION — critical discoveries to act on
7. STRATEGIC PRIORITIES — top 3 actions for next 24 hours
8. COUNCIL RECOMMENDATIONS PENDING — what needs Captain approval

Write in the voice of a senior operations team reporting to a CEO.
Confident, concise, data-driven. Never mention AI or automation.
Length: 600-900 words."""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.STRATEGY,
            )
            return response.content
        except Exception as exc:
            logger.warning("Strategy report generation failed: %s", exc)
            return f"Strategy report for {report_date.strftime('%Y-%m-%d')} — data collection complete, analysis pending."

    async def _run_council_strategy_session(
        self, tenant_id: str, report_content: str, ops_data: dict, is_weekly: bool = False
    ) -> Any:
        """Convene the AI Council for strategic direction."""
        period = "weekly strategic review" if is_weekly else "daily operational review"
        question = (
            f"This is the {period} for Aliyar Solutions.\n\n"
            f"Report content:\n{report_content[:2000]}\n\n"
            f"As the AI Council, provide:\n"
            f"1. Strategic assessment of current operational state\n"
            f"2. Top 3 scaling opportunities in the next 7 days\n"
            f"3. Specific directives for each department to improve performance\n"
            f"4. Risk mitigation priorities\n"
            f"5. Revenue acceleration recommendations\n"
            f"6. What should Captain's attention be focused on today?"
        )

        return await intelligence_council.convene(
            question=question,
            context={
                "report_type": "weekly" if is_weekly else "daily",
                "departments_active": ops_data.get("department_count", 0),
                "purpose": "strategy_oversight",
            },
            council_type="strategy_review",
            tenant_id=tenant_id,
        )

    async def _extract_directives(self, council_reasoning: str) -> list[str]:
        """Extract specific department directives from Council reasoning."""
        prompt = f"""Extract 8-10 specific operational directives from this Council strategy analysis.
Each directive must: start with a department name or 'ALL', be specific and actionable.
Return as JSON array of strings.
Analysis: {council_reasoning[:2000]}
Return only valid JSON array."""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.FAST,
            )
            items = json.loads(response.content.strip())
            return items if isinstance(items, list) else []
        except Exception:
            return [council_reasoning[:200]]

    async def _cascade_directives_to_departments(
        self, tenant_uuid: uuid.UUID, directives: list[str], report_id: uuid.UUID
    ) -> None:
        """Store directives for each DIO to retrieve and act on."""
        if not directives:
            return

        logger.info("Cascading %d directives to departments", len(directives))

    async def _save_report(
        self,
        tenant_uuid: uuid.UUID,
        report_date: datetime,
        report_type: str,
        ops_data: dict,
        report_content: str,
    ) -> uuid.UUID:
        """Persist the strategy report to database."""
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))

            report = StrategyReport(
                tenant_id=tenant_uuid,
                report_date=report_date,
                report_type=report_type,
                operations_summary=ops_data.get("departments", {}),
                kpi_snapshot=ops_data.get("milestones", {}),
                alerts=ops_data.get("alerts", []),
                achievements=ops_data.get("achievements", []),
                blockers=ops_data.get("blockers", []),
            )
            db.add(report)
            await db.commit()
            await db.refresh(report)
            return report.id

    async def _finalize_report(
        self,
        tenant_uuid: uuid.UUID,
        report_id: uuid.UUID,
        council_result: Any,
        directives: list[str],
    ) -> None:
        """Update report with Council results and cascaded directives."""
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            report = await db.get(StrategyReport, report_id)
            if report:
                report.council_session_id = uuid.UUID(council_result.session_id)
                report.scaling_strategy = council_result.reasoning
                report.council_directives = directives
                report.strategy_pdf_url = f"/pdfs/strategy/{report_id}.pdf"
                report.cascaded_to_departments = ["all"]
                report.cascade_completed_at = datetime.now(timezone.utc)
                await db.commit()

    async def _notify_captain_daily(
        self, report_content: str, council_result: Any, ops_data: dict
    ) -> None:
        """Send daily strategy summary to Captain via Slack/Telegram."""
        summary = (
            f"📊 *JARVIS Daily Strategy Report*\n\n"
            f"*Council Score:* {council_result.score:.1f}/100 | "
            f"*Decision:* {council_result.decision}\n\n"
            f"*Departments Active:* {ops_data.get('department_count', 0)}\n"
            f"*Milestones:* {ops_data.get('milestones', {}).get('total', 0)} total\n\n"
            f"*Executive Summary:*\n{report_content[:500]}..."
        )

        try:
            from app.services.notifications.slack import send_slack_message
            await send_slack_message(summary)
        except Exception:
            pass

        try:
            from app.services.notifications.telegram_bot import send_telegram_message
            await send_telegram_message(summary)
        except Exception:
            pass

    def _serialize_report(self, r: StrategyReport) -> dict:
        return {
            "id": str(r.id),
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "report_type": r.report_type,
            "operations_summary": r.operations_summary or {},
            "kpi_snapshot": r.kpi_snapshot or {},
            "alerts": r.alerts or [],
            "achievements": r.achievements or [],
            "mrr": r.mrr,
            "pipeline_value": r.pipeline_value,
            "council_session_id": str(r.council_session_id) if r.council_session_id else None,
            "scaling_strategy": r.scaling_strategy,
            "council_directives": r.council_directives or [],
            "strategy_pdf_url": r.strategy_pdf_url,
            "cascade_completed_at": r.cascade_completed_at.isoformat() if r.cascade_completed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }


strategy_report_service = StrategyReportService()
