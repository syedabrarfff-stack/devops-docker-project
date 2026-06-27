from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import string
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.governance import Proposal
from app.models.lead import Lead
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router
from app.services.intelligence.jarvis_authority import request_captain_approval
from app.services.notifications import notify_business_event

logger = logging.getLogger(__name__)

PACKAGE_CATALOG = {
    "STARTER": {
        "label": "Starter Operating Upgrade",
        "price": "$2,500 setup + $750/month",
        "features": [
            "Lead and customer workflow review",
            "One high-value automation path",
            "Operational dashboard foundation",
            "Email and follow-up process improvement",
        ],
    },
    "GROWTH": {
        "label": "Growth Automation System",
        "price": "$6,500 setup + $2,500/month",
        "features": [
            "End-to-end customer intake and follow-up system",
            "CRM pipeline setup and handoff automation",
            "Dashboard, alerts, and weekly performance reporting",
            "Team workflow documentation and support",
        ],
    },
    "ENTERPRISE": {
        "label": "Enterprise Intelligence Platform",
        "price": "$15,000 setup + $6,000/month",
        "features": [
            "Custom operating system for sales, delivery, and reporting",
            "Cloud infrastructure, observability, and recovery planning",
            "Executive reporting and governance controls",
            "Dedicated implementation roadmap and support cadence",
        ],
    },
}


class ProposalGenerator:
    async def generate(self, lead: Lead, package_tier: str, tenant_id) -> str:
        proposal = await self._generate_record(lead, package_tier, tenant_id)
        return str(proposal.pdf_url or proposal.pdf_path)

    async def submit_for_approval(self, proposal_id, tenant_id) -> dict:
        tenant_uuid = uuid.UUID(str(tenant_id))
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                proposal = await session.scalar(
                    select(Proposal).where(Proposal.tenant_id == tenant_uuid, Proposal.id == int(proposal_id))
                )
                if not proposal:
                    raise ValueError("Proposal not found")
                proposal.status = "pending_approval"
                approval = await request_captain_approval(
                    session,
                    action="pricing_decision",
                    title=f"Approve proposal: {proposal.client_company or proposal.client_name}",
                    summary=(
                        f"{proposal.package_tier or 'Selected'} package proposal is ready. "
                        f"PDF: {proposal.pdf_url or proposal.pdf_path}"
                    ),
                    payload={
                        "tenant_id": str(tenant_uuid),
                        "proposal_id": proposal.id,
                        "lead_id": str(proposal.lead_id) if proposal.lead_id else None,
                        "pdf_url": proposal.pdf_url,
                        "pdf_path": proposal.pdf_path,
                        "package_tier": proposal.package_tier,
                        "invoice_number": proposal.invoice_number,
                    },
                    risk_level="MEDIUM",
                    estimated_cost=(proposal.pricing or {}).get("price"),
                    benefits="Proposal can move a qualified prospect toward a paid discovery or implementation call.",
                    risks="Pricing and commercial commitments must stay aligned with Captain-approved scope.",
                    tenant_id=tenant_uuid,
                )
                await self._audit(
                    session,
                    tenant_uuid,
                    "proposal_submitted_for_approval",
                    proposal.id,
                    {"approval": approval, "pdf_url": proposal.pdf_url, "pdf_path": proposal.pdf_path},
                )

        await notify_business_event(
            "proposal_ready",
            f"Proposal ready: {proposal.client_company or proposal.client_name}",
            f"Captain approval requested for {proposal.package_tier}. PDF: {proposal.pdf_url or proposal.pdf_path}",
        )
        return approval

    async def send(self, proposal_id, tenant_id) -> dict:
        tenant_uuid = uuid.UUID(str(tenant_id))
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                proposal = await session.scalar(
                    select(Proposal).where(Proposal.tenant_id == tenant_uuid, Proposal.id == int(proposal_id))
                )
                if not proposal:
                    raise ValueError("Proposal not found")
                if proposal.status not in {"approved", "sent"}:
                    raise PermissionError("Proposal must be approved before sending")
                if not proposal.client_email:
                    raise ValueError("Proposal has no client email")

                from app.services.outreach.gmail import send_client_email

                sent, error, method = await send_client_email(
                    session,
                    to=proposal.client_email,
                    subject=f"Proposal for {proposal.client_company or proposal.client_name}",
                    body=_proposal_email_text(proposal),
                )
                if not sent:
                    raise RuntimeError(f"Executive email send failed: {error}")
                proposal.status = "sent"
                proposal.sent_at = datetime.now(UTC)
                await self._audit(
                    session,
                    tenant_uuid,
                    "proposal_sent",
                    proposal.id,
                    {"client_email": proposal.client_email, "pdf_url": proposal.pdf_url, "pdf_path": proposal.pdf_path, "method": method},
                )
        return {"sent": True, "proposal_id": int(proposal_id)}

    async def _generate_record(self, lead: Lead, package_tier: str, tenant_id) -> Proposal:
        tenant_uuid = uuid.UUID(str(tenant_id))
        tier = _normalize_tier(package_tier)
        invoice_number = _next_invoice_number()
        sections = await _generate_sections(lead, tier, invoice_number)
        pdf_path, pdf_url = await _render_and_store_pdf(lead, tier, invoice_number, sections)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                proposal = Proposal(
                    tenant_id=tenant_uuid,
                    lead_id=lead.id,
                    title=f"Proposal for {lead.company_name or lead.company or 'Prospect'}",
                    client_name=lead.contact_name,
                    client_email=lead.email or lead.contact_email,
                    client_company=lead.company_name or lead.company,
                    service_type=lead.opportunity_type or _service_from_industry(lead),
                    package_tier=tier,
                    invoice_number=invoice_number,
                    proposal_style="vnext_pdf",
                    scope="\n".join(sections["solution"]),
                    timeline="4-week onboarding plan",
                    pricing={"tier": tier, "price": PACKAGE_CATALOG[tier]["price"]},
                    content=json.dumps(sections),
                    pdf_path=str(pdf_path),
                    pdf_url=pdf_url,
                    ai_generated=True,
                    status="draft",
                )
                session.add(proposal)
                await session.flush()
                await self._audit(
                    session,
                    tenant_uuid,
                    "proposal_pdf_generated",
                    proposal.id,
                    {
                        "lead_id": str(lead.id),
                        "package_tier": tier,
                        "invoice_number": invoice_number,
                        "pdf_path": str(pdf_path),
                        "pdf_url": pdf_url,
                    },
                )
                await session.refresh(proposal)
                return proposal

    async def _audit(
        self,
        session,
        tenant_id: uuid.UUID,
        action: str,
        proposal_id: int,
        payload: dict[str, Any],
    ) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action=action,
                entity_type="proposal",
                entity_id=None,
                actor="ProposalGenerator",
                after_json={"proposal_id": proposal_id, **payload},
                details={"proposal_id": proposal_id, **payload},
            )
        )


async def _generate_sections(lead: Lead, tier: str, invoice_number: str) -> dict[str, Any]:
    prompt = _proposal_prompt(lead, tier, invoice_number)
    try:
        response, _ = await ai_router.chat(
            [Message(role="user", content=prompt)],
            task_type=TaskType.SALES,
            force_provider="anthropic",
            force_model="claude-opus-4-7",
            max_tokens=2200,
        )
        if response.error or response.demo or not response.content:
            return _fallback_sections(lead, tier, invoice_number)
        parsed = _parse_sections(response.content)
        return parsed or _fallback_sections(lead, tier, invoice_number)
    except Exception as exc:
        logger.warning("Proposal content generation failed: %s", exc)
        return _fallback_sections(lead, tier, invoice_number)


def _proposal_prompt(lead: Lead, tier: str, invoice_number: str) -> str:
    pain_points = ", ".join(lead.pain_points or []) or "manual follow-up, slow customer response, and unclear operations"
    package = PACKAGE_CATALOG[tier]
    return f"""
Create text for a seven-page Aliyar Solutions proposal PDF.

Client:
- Company: {lead.company_name or lead.company or "the client"}
- Contact: {lead.contact_name or "decision maker"}
- Email: {lead.email or lead.contact_email or "unknown"}
- Industry: {lead.industry or "unknown"}
- Website: {lead.website or lead.company_website or "unknown"}
- Pain points: {pain_points}
- Opportunity: {lead.opportunity_type or "operations improvement"}

Package:
- Tier: {tier}
- Label: {package["label"]}
- Price: {package["price"]}
- Invoice reference: {invoice_number}

Return only JSON with these keys:
{{
  "executive_summary": ["paragraph 1", "paragraph 2", "paragraph 3"],
  "solution": ["bullet", "bullet", "bullet", "bullet"],
  "timeline": ["week 1 milestone", "week 2 milestone", "week 3 milestone", "week 4 milestone"],
  "investment_summary": ["paragraph", "paragraph"],
  "next_steps": ["step", "step", "step"],
  "about": ["paragraph", "paragraph"]
}}

Rules:
- Client-facing only.
- Say "Aliyar Solutions" or "our team"; never use first-person singular.
- Never mention AI, bots, Claude, prompts, or internal systems.
- Be specific to the client's visible pain points.
- Keep it premium, practical, and revenue-focused.
- Include a direct line that the demo is ready and can be shared if the client is interested.
""".strip()


def _parse_sections(text: str) -> dict[str, Any] | None:
    clean = text.strip()
    if "```" in clean:
        clean = next((part for part in clean.split("```") if "executive_summary" in part), clean)
        clean = clean.removeprefix("json").strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        clean = clean[start:end + 1]
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        return None
    required = ["executive_summary", "solution", "timeline", "investment_summary", "next_steps", "about"]
    if not all(isinstance(parsed.get(key), list) for key in required):
        return None
    return _clean_sections(parsed)


def _clean_sections(sections: dict[str, Any]) -> dict[str, Any]:
    blocked = ["AI", "bot", "Claude", "GPT", "prompt", "internal system"]
    cleaned = {}
    for key, values in sections.items():
        safe_values = []
        for value in values:
            text = str(value).strip()
            if any(term.lower() in text.lower() for term in blocked):
                continue
            safe_values.append(text.replace(" I ", " our team "))
        cleaned[key] = safe_values
    return cleaned


def _fallback_sections(lead: Lead, tier: str, invoice_number: str) -> dict[str, Any]:
    company = lead.company_name or lead.company or "your organization"
    pain = ", ".join(lead.pain_points or []) or "manual coordination, slow follow-up, and limited operational visibility"
    service = lead.opportunity_type or _service_from_industry(lead)
    return {
        "executive_summary": [
            f"{company} appears to have a clear opportunity to improve {pain}.",
            f"Aliyar Solutions proposes a focused {service} engagement that improves speed, consistency, and management visibility.",
            "The goal is to remove avoidable manual work, strengthen customer response, and create a system that can scale without adding operational noise.",
        ],
        "solution": [
            "Map the current customer and internal workflow from first inquiry through delivery.",
            "Identify the highest-value bottlenecks and replace them with reliable operating processes.",
            "Deploy dashboards and alerts so leadership can see work, risk, and outcomes clearly.",
            "Create a measured rollout plan with documented handoff, recovery, and support.",
        ],
        "timeline": [
            "Week 1: discovery, access review, workflow map, and implementation plan.",
            "Week 2: build the first operating workflow and dashboard foundation.",
            "Week 3: test the workflow, refine handoffs, and prepare team documentation.",
            "Week 4: launch, monitor, stabilize, and deliver final operating handover.",
        ],
        "investment_summary": [
            f"Selected package: {PACKAGE_CATALOG[tier]['label']} ({PACKAGE_CATALOG[tier]['price']}). Reference: {invoice_number}.",
            "Payment terms are 50% upfront and 50% on delivery, with monthly support billed in advance where applicable.",
        ],
        "next_steps": [
            "The demo is ready, and if you're interested, we can share it with you right away.",
            "Schedule a short working call to validate operational assumptions.",
            "Approve the project start date and begin the Week 1 discovery process.",
        ],
        "about": [
            "Aliyar Solutions builds operational technology systems for businesses that need stronger execution, better visibility, and scalable delivery.",
            "Our engineering, operations, and strategy teams focus on practical infrastructure that saves time, reduces errors, and protects revenue.",
        ],
    }


async def _render_and_store_pdf(
    lead: Lead,
    tier: str,
    invoice_number: str,
    sections: dict[str, Any],
) -> tuple[Path, str]:
    output_dir = Path(os.getenv("JARVIS_PROPOSAL_DIR", "/data/proposals"))
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_company = _safe_slug(lead.company_name or lead.company or "prospect")
    pdf_path = output_dir / f"{invoice_number}_{safe_company}_{tier.lower()}.pdf"
    await asyncio.to_thread(_build_pdf, pdf_path, lead, tier, invoice_number, sections)
    pdf_url = await _upload_to_s3_if_enabled(pdf_path, invoice_number)
    return pdf_path, pdf_url


def _build_pdf(
    pdf_path: Path,
    lead: Lead,
    tier: str,
    invoice_number: str,
    sections: dict[str, Any],
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title = ParagraphStyle("JarvisTitle", parent=styles["Title"], fontSize=24, leading=30, textColor=colors.HexColor("#0F172A"))
    heading = ParagraphStyle("JarvisHeading", parent=styles["Heading1"], fontSize=17, leading=22, textColor=colors.HexColor("#0F766E"))
    body = ParagraphStyle("JarvisBody", parent=styles["BodyText"], fontSize=10.5, leading=15, textColor=colors.HexColor("#1F2937"))
    small = ParagraphStyle("JarvisSmall", parent=styles["BodyText"], fontSize=8.5, leading=12, textColor=colors.HexColor("#64748B"))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    company = lead.company_name or lead.company or "Prospect"
    story = [
        Paragraph("ALIYAR SOLUTIONS", small),
        Spacer(1, 0.35 * inch),
        Paragraph(f"Proposal for {company}", title),
        Spacer(1, 0.2 * inch),
        Paragraph(f"Prepared on {datetime.now(UTC).strftime('%B %d, %Y')}", body),
        Paragraph("Confidential business proposal", body),
        Spacer(1, 0.45 * inch),
        _key_value_table(
            [
                ("Package", f"{tier} - {PACKAGE_CATALOG[tier]['label']}"),
                ("Reference", invoice_number),
                ("Prepared for", company),
                ("Prepared by", "Aliyar Solutions Team"),
            ]
        ),
        PageBreak(),
        Paragraph("Executive Summary", heading),
        *_paragraphs(sections["executive_summary"], body),
        PageBreak(),
        Paragraph("Proposed Solution", heading),
        *_bullets(sections["solution"], body),
        PageBreak(),
        Paragraph("Package Details", heading),
        _package_table(tier),
        PageBreak(),
        Paragraph("Implementation Timeline", heading),
        *_bullets(sections["timeline"], body),
        PageBreak(),
        Paragraph("Investment Summary", heading),
        *_paragraphs(sections["investment_summary"], body),
        Spacer(1, 0.2 * inch),
        _key_value_table(
            [
                ("Payment terms", "50% upfront + 50% on delivery"),
                ("Validity", "Proposal valid for 14 days"),
                ("Next step", "Scope confirmation and discovery call"),
            ]
        ),
        Spacer(1, 0.25 * inch),
        Paragraph("Next Steps", heading),
        *_bullets(sections["next_steps"], body),
        PageBreak(),
        Paragraph("About Aliyar Solutions", heading),
        *_paragraphs(sections["about"], body),
    ]
    doc.build(story)


def _paragraphs(values: list[str], style) -> list:
    from reportlab.platypus import Paragraph, Spacer

    story = []
    for value in values:
        story.extend([Paragraph(_escape(value), style), Spacer(1, 10)])
    return story


def _bullets(values: list[str], style) -> list:
    from reportlab.platypus import Paragraph, Spacer

    story = []
    for value in values:
        story.extend([Paragraph(f"- {_escape(value)}", style), Spacer(1, 8)])
    return story


def _key_value_table(rows: list[tuple[str, str]]):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table(rows, colWidths=[120, 330])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E0F2FE")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#075985")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _package_table(tier: str):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    package = PACKAGE_CATALOG[tier]
    rows = [["Selected package", package["label"]], ["Investment", package["price"]]]
    rows.extend([["Included", feature] for feature in package["features"]])
    table = Table(rows, colWidths=[120, 330])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#CCFBF1")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


async def _upload_to_s3_if_enabled(pdf_path: Path, invoice_number: str) -> str:
    if not (settings.USE_AWS and settings.AWS_S3_BUCKET):
        return str(pdf_path)

    key = f"proposals/{invoice_number}/{pdf_path.name}"

    def _upload() -> str:
        import boto3

        client = boto3.client("s3", region_name=settings.AWS_REGION)
        client.upload_file(str(pdf_path), settings.AWS_S3_BUCKET, key)
        return f"s3://{settings.AWS_S3_BUCKET}/{key}"

    try:
        return await asyncio.to_thread(_upload)
    except Exception as exc:
        logger.warning("S3 proposal upload failed, using local path: %s", exc)
        return str(pdf_path)


def _proposal_email_html(proposal: Proposal) -> str:
    link = proposal.pdf_url or proposal.pdf_path or "the attached proposal"
    return (
        "<p>Hello,</p>"
        "<p>Thank you for the discussion so far. Our team has prepared the proposal and implementation path "
        "for your review.</p>"
        "<p>The demo is ready, and if you're interested, we can share it with you right away.</p>"
        f"<p>Proposal reference: <strong>{proposal.invoice_number}</strong><br>PDF: {link}</p>"
        "<p>If the scope looks aligned, the next step is a short call to confirm timeline, responsibilities, "
        "and rollout sequence.</p>"
        "<p>Joseph David<br>Executive Director<br>Aliyar Solutions</p>"
    )


def _proposal_email_text(proposal: Proposal) -> str:
    link = proposal.pdf_url or proposal.pdf_path or "the attached proposal"
    return (
        "Hello,\n\n"
        "Thank you for the discussion so far. Our team has prepared the proposal and implementation path for your review.\n\n"
        "The demo is ready, and if you're interested, we can share it with you right away.\n\n"
        f"Proposal reference: {proposal.invoice_number}\n"
        f"PDF: {link}\n\n"
        "If the scope looks aligned, the next step is a short call to confirm timeline, responsibilities, and rollout sequence.\n\n"
        "Joseph David\n"
        "Executive Director\n"
        "Aliyar Solutions"
    )


def _normalize_tier(package_tier: str) -> str:
    tier = (package_tier or "STARTER").upper().strip()
    if tier not in PACKAGE_CATALOG:
        raise ValueError("package_tier must be STARTER, GROWTH, or ENTERPRISE")
    return tier


def _service_from_industry(lead: Lead) -> str:
    industry = (lead.industry or "").lower()
    if "clinic" in industry or "health" in industry:
        return "appointment workflow and operations automation"
    if "saas" in industry or "software" in industry:
        return "sales pipeline and customer operations system"
    if "ecommerce" in industry or "retail" in industry:
        return "commerce operations and customer follow-up system"
    return "business operations automation"


def _next_invoice_number() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ALY-{timestamp}-{suffix}"


def _safe_slug(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-")[:60] or "prospect"


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


proposal_generator = ProposalGenerator()
