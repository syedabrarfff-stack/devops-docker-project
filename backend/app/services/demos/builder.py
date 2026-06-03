from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.demo import DemoPackage
from app.models.lead import Lead
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router
from app.services.notifications import notify_telegram


class DemoBuilder:
    async def generate(
        self,
        tenant_id: uuid.UUID | str,
        *,
        lead_id: uuid.UUID | str | None = None,
        industry: str | None = None,
        pain_points: list[str] | None = None,
        company_name: str | None = None,
    ) -> DemoPackage:
        tenant_uuid = _coerce_tenant_id(tenant_id)
        lead_uuid = uuid.UUID(str(lead_id)) if lead_id else None

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                lead = None
                if lead_uuid:
                    lead = await session.scalar(
                        select(Lead).where(Lead.tenant_id == tenant_uuid, Lead.id == lead_uuid)
                    )
                company = company_name or _lead_name(lead) if lead else company_name or "Prospect"
                resolved_industry = industry or (lead.industry if lead else None) or "business operations"
                resolved_pain_points = pain_points or (lead.pain_points if lead else []) or [
                    "manual follow-up",
                    "slow customer response",
                    "missed revenue from untracked work",
                ]

                script = await self._write_script(company, resolved_industry, resolved_pain_points, lead)
                roi_projection = _roi_projection(company, resolved_pain_points)
                demo = await self._upsert_demo(
                    session,
                    tenant_uuid,
                    lead_uuid,
                    company,
                    resolved_industry,
                    resolved_pain_points,
                    script,
                    roi_projection,
                )
                pdf_path = self._write_pdf(demo, company, resolved_industry, resolved_pain_points, script, roi_projection)
                demo.pdf_path = str(pdf_path)
                demo.status = "ready"
                demo.metadata_json = {
                    **(demo.metadata_json or {}),
                    "pdf_generated": True,
                    "pdf_link": _pdf_link(lead_uuid or demo.id),
                }
                if lead:
                    lead.enrichment_data = {
                        **(lead.enrichment_data or {}),
                        "demo_package_id": str(demo.id),
                        "demo_package_ready": True,
                        "demo_pdf_path": str(pdf_path),
                    }
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="demo_package_generated",
                        entity_type="lead",
                        entity_id=lead_uuid,
                        actor="DemoBuilder",
                        details={
                            "demo_id": str(demo.id),
                            "company": company,
                            "industry": resolved_industry,
                            "pdf_path": str(pdf_path),
                        },
                    )
                )

            await notify_telegram(
                f"Demo package ready for {company} - {_pdf_link(lead_uuid or demo.id)}"
            )
            return demo

    async def _write_script(
        self,
        company: str,
        industry: str,
        pain_points: list[str],
        lead: Lead | None,
    ) -> str:
        prompt = f"""
Create a personalized demo script for Aliyar Solutions.

Client: {company}
Industry: {industry}
Pain points: {', '.join(pain_points)}
Lead context: {lead.ai_analysis if lead else ''}

Structure:
1. Opening
2. Problem statement using their exact pain points
3. Solution walkthrough for their industry
4. ROI projection
5. Questions to ask on the call
6. Close and next step

Rules:
- Client-facing language must never mention AI, bots, Claude, prompts, model names, or internal systems.
- Do not reveal pricing.
- Sound human, specific, calm, and commercially useful.
- Speak as Aliyar Solutions or our specialist team.
""".strip()
        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.SALES,
                force_provider="nvidia",
                max_tokens=1800,
            )
            if response.content and not response.error and not response.demo:
                cleaned = _clean_client_text(response.content)
                if _is_client_safe(cleaned):
                    return cleaned
        except Exception:
            pass
        return _fallback_script(company, industry, pain_points)

    async def _upsert_demo(
        self,
        session,
        tenant_id: uuid.UUID,
        lead_id: uuid.UUID | None,
        company: str,
        industry: str,
        pain_points: list[str],
        script: str,
        roi_projection: str,
    ) -> DemoPackage:
        demo = None
        if lead_id:
            demo = await session.scalar(
                select(DemoPackage).where(DemoPackage.tenant_id == tenant_id, DemoPackage.lead_id == lead_id)
            )
        if not demo:
            demo = DemoPackage(
                tenant_id=tenant_id,
                lead_id=lead_id,
                company_name=company,
                industry=industry,
                pain_points=pain_points,
                demo_script=script,
                roi_projection=roi_projection,
                status="generating",
                metadata_json={},
            )
            session.add(demo)
        else:
            demo.company_name = company
            demo.industry = industry
            demo.pain_points = pain_points
            demo.demo_script = script
            demo.roi_projection = roi_projection
            demo.status = "generating"
        await session.flush()
        return demo

    def _write_pdf(
        self,
        demo: DemoPackage,
        company: str,
        industry: str,
        pain_points: list[str],
        script: str,
        roi_projection: str,
    ) -> Path:
        output_dir = Path("/data/demos")
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / f"demo_{_slug(company)}_{demo.id}.pdf"
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            rightMargin=0.72 * inch,
            leftMargin=0.72 * inch,
            topMargin=0.72 * inch,
            bottomMargin=0.72 * inch,
            title=f"Aliyar Solutions Demo - {company}",
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "JarvisTitle",
            parent=styles["Title"],
            textColor=colors.HexColor("#0f766e"),
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            spaceAfter=18,
        )
        heading_style = ParagraphStyle(
            "JarvisHeading",
            parent=styles["Heading1"],
            textColor=colors.HexColor("#111827"),
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=22,
            spaceAfter=10,
        )
        body_style = ParagraphStyle(
            "JarvisBody",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#1f2937"),
            fontSize=10.5,
            leading=15,
            spaceAfter=8,
        )
        story = [
            Paragraph("Aliyar Solutions", title_style),
            Paragraph(f"Personalized Demo Package for {company}", heading_style),
            Paragraph(f"Industry focus: {industry}", body_style),
            Paragraph("Prepared by Aliyar Solutions specialist team", body_style),
            PageBreak(),
        ]
        pages = [
            (
                "The Situation",
                "The visible opportunity is to remove manual coordination, improve response consistency, "
                "and give the team a cleaner operating flow before more revenue leaks through missed follow-up.",
            ),
            (
                "Pain Points To Validate",
                "<br/>".join(f"- {point}" for point in pain_points),
            ),
            (
                "Demo Walkthrough",
                script.replace("\n", "<br/>"),
            ),
            (
                "Expected Business Impact",
                roi_projection,
            ),
            (
                "Questions For The Call",
                "1. Where does the customer journey slow down today?<br/>"
                "2. Which manual task takes the most team time every week?<br/>"
                "3. Where do leads, bookings, or client updates currently get missed?<br/>"
                "4. What would make this project worth doing in the first 30 days?",
            ),
            (
                "Recommended Next Step",
                "A short working session should confirm the real bottleneck, choose the fastest service path, "
                "and define the demo outcome the client can judge without a long buying process.",
            ),
        ]
        for heading, body in pages:
            story.append(Paragraph(heading, heading_style))
            story.append(Paragraph(body, body_style))
            story.append(Spacer(1, 0.12 * inch))
            story.append(PageBreak())
        doc.build(story)
        return pdf_path


def _fallback_script(company: str, industry: str, pain_points: list[str]) -> str:
    pain = ", ".join(pain_points)
    return (
        f"Opening: Thank {company} for taking the time and explain that our team prepared a focused walkthrough "
        f"around the visible operational pressure in {industry}.\n\n"
        f"Problem statement: The main pattern to validate is {pain}. When that stays manual, response time slows, "
        "work gets missed, and growth becomes harder to manage without adding more people.\n\n"
        "Solution walkthrough: Show how Aliyar Solutions would map the current workflow, isolate the repeated steps, "
        "connect the right systems, and create a cleaner operating layer for customer communication, tracking, and reporting.\n\n"
        "ROI projection: Position the value around hours saved, fewer missed follow-ups, faster response time, and better conversion "
        "from the same lead volume.\n\n"
        "Close: Ask for the one bottleneck they most want removed in the next 30 days, then propose a short implementation plan."
    )


def _roi_projection(company: str, pain_points: list[str]) -> str:
    pain = pain_points[0] if pain_points else "manual coordination"
    return (
        f"For {company}, the first value case should focus on reducing time lost to {pain}, improving response speed, "
        "and recovering opportunities that currently fall through manual handoffs. The first measurable target is a "
        "30-day operational improvement: fewer missed follow-ups, faster customer response, and clearer visibility for management."
    )


def _clean_client_text(text: str) -> str:
    blocked = ["Claude", "GPT", "OpenAI", "NVIDIA", "Gemini", "bot", "prompt", "model"]
    cleaned = text
    for term in blocked:
        cleaned = re.sub(rf"\b{re.escape(term)}\b", "our specialist team", cleaned, flags=re.IGNORECASE)
    return cleaned


def _is_client_safe(text: str) -> bool:
    lowered = f" {text.lower()} "
    blocked_terms = [
        " i ",
        " i'm ",
        " i am ",
        " me ",
        " my ",
        " ai ",
        " bot ",
        " claude ",
        " prompt ",
        " gpt ",
        "[",
        "]",
    ]
    return not any(term in lowered for term in blocked_terms)


def _lead_name(lead: Lead | None) -> str:
    if not lead:
        return "Prospect"
    return lead.company_name or lead.company or lead.contact_name or lead.email or "Prospect"


def _slug(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return clean[:80] or "prospect"


def _pdf_link(identifier: uuid.UUID) -> str:
    base = settings.APP_BASE_URL.rstrip("/")
    return f"{base}/api/v1/demos/{identifier}/pdf"


def _coerce_tenant_id(tenant_id: uuid.UUID | str) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


demo_builder = DemoBuilder()
