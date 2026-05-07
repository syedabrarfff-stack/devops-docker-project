"""
JARVIS Governance — AI-powered document generation for invoices, proposals, and contracts.
All documents require Captain approval before execution.
"""
import json
import logging
import random
import string
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.governance import Invoice, Proposal, ContractTemplate
from app.services.ai.base_provider import Message

logger = logging.getLogger(__name__)

PROPOSAL_PROMPT = """You are JARVIS — the strategic AI of Aliyar Solutions, a premium AI automation and cloud consulting company.

Generate a high-converting, professional business proposal for the following client and context.

CLIENT: {client_name} at {client_company}
SERVICE: {service_type}
CONTEXT: {context}
STYLE: {style}
PRICING: {pricing}

Style guide:
- standard: professional, balanced, value-focused
- case_study: lead with results and social proof, then offer
- short_urgent: concise, urgent, action-oriented (max 300 words)
- social_proof: testimonials/results first, heavy proof, then pitch

Write a complete proposal that:
1. Opens with the client's specific pain point (not a generic intro)
2. Presents Aliyar Solutions' approach and unique value
3. Outlines the scope of work clearly
4. Shows the investment (pricing) with ROI framing
5. Closes with a clear next step

Tone: Premium, confident, business-focused. Never desperate or generic.
Write in first-person plural ("we", "our team").
Do NOT mention AI or automation tools by brand name.

Return the complete proposal as plain text (no markdown headers, just clean professional prose)."""


async def generate_proposal(
    db: AsyncSession,
    client_name: str,
    client_email: str,
    client_company: str,
    service_type: str,
    context: str,
    pricing: dict,
    style: str = "standard",
) -> dict:
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import TaskType

    pricing_str = json.dumps(pricing, indent=2)
    prompt = PROPOSAL_PROMPT.format(
        client_name=client_name,
        client_company=client_company,
        service_type=service_type,
        context=context,
        style=style,
        pricing=pricing_str,
    )
    messages = [Message(role="user", content=prompt)]

    try:
        response, _ = await ai_router.chat(
            messages,
            task_type=TaskType.STRATEGY,
            max_tokens=2500,
        )
        content = response.content.strip()
    except Exception as e:
        logger.warning(f"Proposal generation failed: {e}")
        content = f"[Proposal for {client_name} at {client_company} — {service_type}]\n\nAI generation unavailable. Please draft manually."

    title = f"{service_type} — {client_company}"
    proposal = Proposal(
        title=title,
        client_name=client_name,
        client_email=client_email,
        client_company=client_company,
        service_type=service_type,
        proposal_style=style,
        pricing=pricing,
        content=content,
        ai_generated=True,
        status="draft",
    )
    db.add(proposal)
    await db.flush()
    return _serialize_proposal(proposal)


def _next_invoice_number() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ALY-{ts}-{suffix}"


async def create_invoice(
    db: AsyncSession,
    client_name: str,
    client_email: str,
    client_company: str,
    items: list[dict],
    tax_rate: float = 0.0,
    currency: str = "USD",
    notes: str = "",
    due_days: int = 14,
) -> dict:
    subtotal = sum(float(i.get("amount", 0)) for i in items)
    tax_amount = subtotal * tax_rate / 100
    total = subtotal + tax_amount

    invoice = Invoice(
        invoice_number=_next_invoice_number(),
        client_name=client_name,
        client_email=client_email,
        client_company=client_company,
        items=items,
        subtotal=Decimal(str(round(subtotal, 2))),
        tax_rate=Decimal(str(tax_rate)),
        tax_amount=Decimal(str(round(tax_amount, 2))),
        total=Decimal(str(round(total, 2))),
        currency=currency,
        notes=notes,
        status="draft",
        due_date=datetime.now(timezone.utc) + timedelta(days=due_days),
    )
    db.add(invoice)
    await db.flush()
    return _serialize_invoice(invoice)


async def get_invoices(db: AsyncSession, status: str | None = None) -> list[dict]:
    q = select(Invoice).order_by(Invoice.created_at.desc())
    if status:
        q = q.where(Invoice.status == status)
    result = await db.execute(q)
    return [_serialize_invoice(i) for i in result.scalars().all()]


async def get_proposals(db: AsyncSession, status: str | None = None) -> list[dict]:
    q = select(Proposal).order_by(Proposal.created_at.desc())
    if status:
        q = q.where(Proposal.status == status)
    result = await db.execute(q)
    return [_serialize_proposal(p) for p in result.scalars().all()]


async def update_invoice_status(db: AsyncSession, invoice_id: int, new_status: str) -> bool:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        return False
    inv.status = new_status
    if new_status == "sent":
        inv.sent_at = datetime.now(timezone.utc)
    elif new_status == "paid":
        inv.paid_at = datetime.now(timezone.utc)
    return True


async def update_proposal_status(db: AsyncSession, proposal_id: int, new_status: str) -> bool:
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    prop = result.scalar_one_or_none()
    if not prop:
        return False
    prop.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == "sent":
        prop.sent_at = now
    elif new_status in ("accepted", "declined", "negotiating"):
        prop.responded_at = now
    return True


def _serialize_invoice(i: Invoice) -> dict:
    return {
        "id": i.id,
        "invoice_number": i.invoice_number,
        "client_name": i.client_name,
        "client_email": i.client_email,
        "client_company": i.client_company,
        "items": i.items or [],
        "subtotal": float(i.subtotal or 0),
        "tax_rate": float(i.tax_rate or 0),
        "tax_amount": float(i.tax_amount or 0),
        "total": float(i.total or 0),
        "currency": i.currency,
        "status": i.status,
        "notes": i.notes,
        "payment_link": i.payment_link,
        "due_date": i.due_date.isoformat() if i.due_date else None,
        "sent_at": i.sent_at.isoformat() if i.sent_at else None,
        "paid_at": i.paid_at.isoformat() if i.paid_at else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


def _serialize_proposal(p: Proposal) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "client_name": p.client_name,
        "client_email": p.client_email,
        "client_company": p.client_company,
        "service_type": p.service_type,
        "proposal_style": p.proposal_style,
        "pricing": p.pricing,
        "content": p.content,
        "ai_generated": p.ai_generated,
        "status": p.status,
        "sent_at": p.sent_at.isoformat() if p.sent_at else None,
        "viewed_at": p.viewed_at.isoformat() if p.viewed_at else None,
        "responded_at": p.responded_at.isoformat() if p.responded_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
