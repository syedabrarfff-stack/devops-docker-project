"""
JARVIS Market Intelligence Engine — Daily market case study and opportunity generator.

Generates rotating market reports, Apollo market studies, and trending opportunity scans
to feed the JARVIS sales intelligence pipeline.

Scheduled to run at 04:00 UTC (09:30 IST) daily via APScheduler.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)


class MarketIntelligenceEngine:
    """
    Generates daily market intelligence reports, Apollo market studies,
    and trending opportunity analyses for the JARVIS sales engine.
    """

    DAILY_RESEARCH_TOPICS = [
        "Apollo.io AI prospecting market trends 2025",
        "HubSpot CRM adoption SMB market",
        "AI automation ROI case studies UK UAE",
        "SaaS operational automation pricing benchmarks",
        "Digital agency AI transformation",
        "E-commerce automation tools comparison",
        "Cloud DevOps market demand analysis",
    ]

    # ------------------------------------------------------------------
    # Daily market report
    # ------------------------------------------------------------------

    async def generate_daily_market_report(self, tenant_id: UUID) -> dict:
        """
        Picks today's research topic (rotates through DAILY_RESEARCH_TOPICS).
        Uses ai_router (task_type=RESEARCH) to generate a 500-word market case study.
        Structure: executive_summary, market_size, key_trends (list),
                   opportunity_for_aliyar (how we sell into this),
                   target_companies (3 example ICP companies to prospect),
                   recommended_service_package, confidence_score.
        Returns full report dict.
        """
        today = date.today()
        topic_index = today.timetuple().tm_yday % len(self.DAILY_RESEARCH_TOPICS)
        topic = self.DAILY_RESEARCH_TOPICS[topic_index]

        logger.info("[MarketIntelligence] Generating daily report for topic: %s", topic)

        prompt = f"""You are the Market Intelligence Director for Aliyar Solutions, a global AI and cloud infrastructure company.

Generate a comprehensive 500-word market intelligence report on: "{topic}"

The report must be structured as valid JSON with these exact fields:
{{
  "topic": "{topic}",
  "date": "{today.isoformat()}",
  "executive_summary": "2-3 sentence high-level summary of the market opportunity",
  "market_size": "Specific market size with year (e.g., '$4.2B by 2026')",
  "key_trends": ["trend 1", "trend 2", "trend 3", "trend 4"],
  "opportunity_for_aliyar": "How Aliyar Solutions can position and sell into this market segment",
  "target_companies": [
    {{"name": "Company X", "country": "UK", "why": "reason they need our service"}},
    {{"name": "Company Y", "country": "UAE", "why": "reason"}},
    {{"name": "Company Z", "country": "USA", "why": "reason"}}
  ],
  "recommended_service_package": "Specific Aliyar service package and monthly retainer price",
  "outreach_angle": "The specific pain point angle to lead with in cold outreach",
  "confidence_score": 0.85
}}

Base this on real market data, trends, and Aliyar's ICP: companies with 5-200 employees in UK, UAE, USA, Australia, Canada needing AI automation, DevOps, or CRM infrastructure."""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.RESEARCH,
            )

            raw = (response.content or "").strip()
            # Extract JSON from response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                report = json.loads(raw[start:end])
            else:
                raise ValueError("No JSON object found in response")

            report["generated_at"] = datetime.now(UTC).isoformat()
            return report

        except Exception as exc:
            logger.error("[MarketIntelligence] Report generation failed: %s", exc)
            return self._fallback_report(topic, today.isoformat())

    # ------------------------------------------------------------------
    # Apollo market study
    # ------------------------------------------------------------------

    async def generate_apollo_market_study(self, tenant_id: UUID) -> dict:
        """
        Deep study of Apollo.io's market positioning.
        Identifies which prospect segments are actively using Apollo.
        Recommends how Aliyar Solutions can position against Apollo users.
        Returns: market_analysis, prospect_segments, positioning_strategy,
                 outreach_angle, sample_email_hook.
        """
        logger.info("[MarketIntelligence] Generating Apollo market study")

        prompt = """You are the Strategy Director for Aliyar Solutions.

Generate a deep market intelligence study on Apollo.io's user base and market positioning.

Output as valid JSON:
{
  "market_analysis": "200-word analysis of Apollo.io's market position and who uses it",
  "prospect_segments": [
    {
      "segment": "Segment name (e.g., SaaS sales teams)",
      "company_size": "5-50 employees",
      "geography": "USA/UK/Australia",
      "pain_after_apollo": "What they still can't solve with Apollo alone",
      "our_pitch": "How Aliyar fills the gap"
    }
  ],
  "positioning_strategy": "How Aliyar Solutions complements or competes with Apollo users' stack",
  "outreach_angles": [
    "Angle 1: Lead with their Apollo frustration...",
    "Angle 2: Position as the operational layer above Apollo...",
    "Angle 3: Show ROI comparison..."
  ],
  "sample_email_hook": "Subject line and first 2 sentences of an outreach email targeting Apollo users",
  "recommended_services": ["AI Lead Generation ($3,500/mo)", "CRM Architecture ($2,500/mo)"],
  "confidence_score": 0.82
}

Focus on companies in UK, UAE, USA, Australia that are currently using Apollo.io but lack the infrastructure to properly execute on their leads."""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.STRATEGY,
            )

            raw = (response.content or "").strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                study = json.loads(raw[start:end])
            else:
                raise ValueError("No JSON in response")

            study["generated_at"] = datetime.now(UTC).isoformat()
            return study

        except Exception as exc:
            logger.error("[MarketIntelligence] Apollo study failed: %s", exc)
            return {
                "market_analysis": "Apollo.io serves over 160,000 companies for sales intelligence.",
                "prospect_segments": [],
                "positioning_strategy": "Position as operational execution layer.",
                "outreach_angles": ["Focus on post-Apollo execution gaps"],
                "sample_email_hook": "Are you getting leads from Apollo but struggling to close them?",
                "error": str(exc),
                "generated_at": datetime.now(UTC).isoformat(),
            }

    # ------------------------------------------------------------------
    # Trending opportunities scanner
    # ------------------------------------------------------------------

    async def identify_trending_opportunities(self, tenant_id: UUID) -> list[dict]:
        """
        Scans for trending pain points in target markets.
        Uses AI to identify what problems are being discussed right now.
        Returns list of opportunities: {pain_point, market_size, urgency,
                                        our_service, pricing_range, prospect_profile}
        """
        logger.info("[MarketIntelligence] Scanning for trending opportunities")

        today = date.today().isoformat()
        prompt = f"""You are the Market Intelligence AI for Aliyar Solutions, scanning as of {today}.

Identify 5 trending operational pain points that companies (5-200 employees) in UK, UAE, USA, Australia are actively facing right now.

Return as valid JSON array:
[
  {{
    "pain_point": "Specific problem companies are experiencing",
    "market_size": "Number of potential companies affected",
    "urgency": "high|medium|low",
    "trigger_event": "What's driving this pain right now (regulation, technology shift, market pressure)",
    "our_service": "Which Aliyar Solutions service solves this",
    "pricing_range": "$X,XXX–$Y,XXX/month",
    "prospect_profile": {{
      "industry": "industry name",
      "size": "employee range",
      "countries": ["UK", "UAE"],
      "decision_maker": "CTO|CEO|Operations Director"
    }},
    "outreach_hook": "One sentence that immediately resonates with this prospect"
  }}
]

Focus on real, current problems: AI adoption gaps, post-pandemic scaling, regulatory compliance, e-commerce growth pains, DevOps talent shortage."""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.RESEARCH,
            )

            raw = (response.content or "").strip()
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                opportunities = json.loads(raw[start:end])
                return opportunities if isinstance(opportunities, list) else []
            raise ValueError("No JSON array in response")

        except Exception as exc:
            logger.error("[MarketIntelligence] Opportunity scan failed: %s", exc)
            return [
                {
                    "pain_point": "Manual lead follow-up burning sales team capacity",
                    "market_size": "~45,000 SMBs in UK/UAE",
                    "urgency": "high",
                    "trigger_event": "AI tools now accessible at SMB price points",
                    "our_service": "AI Lead Generation + CRM Architecture",
                    "pricing_range": "$3,000–$5,000/month",
                    "prospect_profile": {
                        "industry": "Professional Services",
                        "size": "10-100 employees",
                        "countries": ["UK", "UAE"],
                        "decision_maker": "CEO",
                    },
                    "outreach_hook": "Your competitors are already automating follow-up — are you?",
                }
            ]

    # ------------------------------------------------------------------
    # Write GitHub intelligence package
    # ------------------------------------------------------------------

    async def write_github_intelligence_package(self, tenant_id: UUID, output_dir: str) -> dict:
        """
        Generates full intelligence package and writes to files:
        - market_report_YYYY-MM-DD.md
        - trending_opportunities.json
        - apollo_market_study.md
        Writes to output_dir (the jarvis-data/intelligence/ path).
        Returns: files_written list, total_insights count.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files_written = []
        total_insights = 0

        today = date.today().isoformat()

        # 1. Daily market report
        try:
            report = await self.generate_daily_market_report(tenant_id)
            report_file = output_path / f"market_report_{today}.md"
            md_content = _dict_to_markdown(report, "Daily Market Intelligence Report")
            report_file.write_text(md_content, encoding="utf-8")
            files_written.append(str(report_file))
            total_insights += len(report.get("key_trends", []))
            logger.info("[MarketIntelligence] Wrote market report: %s", report_file)
        except Exception as exc:
            logger.error("[MarketIntelligence] Market report write error: %s", exc)

        # 2. Trending opportunities
        try:
            opportunities = await self.identify_trending_opportunities(tenant_id)
            opps_file = output_path / "trending_opportunities.json"
            opps_file.write_text(
                json.dumps(opportunities, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            files_written.append(str(opps_file))
            total_insights += len(opportunities)
            logger.info("[MarketIntelligence] Wrote opportunities: %s", opps_file)
        except Exception as exc:
            logger.error("[MarketIntelligence] Opportunities write error: %s", exc)

        # 3. Apollo market study
        try:
            apollo_study = await self.generate_apollo_market_study(tenant_id)
            apollo_file = output_path / "apollo_market_study.md"
            md_content = _dict_to_markdown(apollo_study, "Apollo.io Market Intelligence Study")
            apollo_file.write_text(md_content, encoding="utf-8")
            files_written.append(str(apollo_file))
            total_insights += len(apollo_study.get("outreach_angles", []))
            logger.info("[MarketIntelligence] Wrote Apollo study: %s", apollo_file)
        except Exception as exc:
            logger.error("[MarketIntelligence] Apollo study write error: %s", exc)

        return {
            "files_written": files_written,
            "total_insights": total_insights,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_report(self, topic: str, date_str: str) -> dict:
        return {
            "topic": topic,
            "date": date_str,
            "executive_summary": f"Market analysis for {topic}. Data generation encountered an error — manual review recommended.",
            "market_size": "Data unavailable",
            "key_trends": ["AI adoption accelerating", "SMB automation demand rising"],
            "opportunity_for_aliyar": "Position as enterprise-grade solution at SMB price point.",
            "target_companies": [],
            "recommended_service_package": "AI Automation Stack — $3,500/month",
            "outreach_angle": "Replace manual processes with intelligent operations",
            "confidence_score": 0.3,
            "fallback": True,
            "generated_at": datetime.now(UTC).isoformat(),
        }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _dict_to_markdown(data: dict, title: str) -> str:
    """Convert a dict to readable markdown."""
    lines = [f"# {title}", f"\n_Generated: {data.get('generated_at', 'N/A')}_\n", "---\n"]

    for key, value in data.items():
        if key in ("generated_at",):
            continue
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            lines.append(f"\n## {label}")
            for item in value:
                if isinstance(item, dict):
                    for k, v in item.items():
                        lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
                    lines.append("")
                else:
                    lines.append(f"- {item}")
        elif isinstance(value, dict):
            lines.append(f"\n## {label}")
            for k, v in value.items():
                lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
        else:
            lines.append(f"\n## {label}\n{value}")

    return "\n".join(lines)


market_intelligence_engine = MarketIntelligenceEngine()
