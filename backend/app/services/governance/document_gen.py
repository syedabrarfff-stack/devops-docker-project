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
from app.models.governance import Contract, Invoice, Proposal, ContractTemplate
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

    # Resolve the appropriate team member for this service type
    author_name = "Aliyar Solutions Team"
    author_title = ""
    author_signature = "Aliyar Solutions"
    try:
        from app.services.team.team_service import get_member_for_service
        member = await get_member_for_service(db, service_type.lower().replace(" ", "_"))
        if member:
            author_name = member.name
            author_title = member.proposal_title or member.role
            author_signature = member.email_signature
    except Exception as e:
        logger.warning(f"Team member lookup for proposal failed: {e}")

    pricing_str = json.dumps(pricing, indent=2)
    proposal_prompt = PROPOSAL_PROMPT + (
        f"\n\nAUTHOR: This proposal is prepared and signed by {author_name}"
        + (f", {author_title}" if author_title else "")
        + f".\nClose the proposal with:\n\nWarm regards,\n{author_signature}"
    )
    prompt = proposal_prompt.format(
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
        content = (
            f"[Proposal for {client_name} at {client_company} — {service_type}]\n\n"
            f"AI generation unavailable. Please draft manually.\n\n"
            f"Warm regards,\n{author_signature}"
        )

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
    result = _serialize_proposal(proposal)
    result["author"] = {"name": author_name, "title": author_title}
    return result


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


async def get_invoices(db: AsyncSession, status: str | None = None, tenant_id=None) -> list[dict]:
    q = select(Invoice).order_by(Invoice.created_at.desc())
    if status:
        q = q.where(Invoice.status == status)
    if tenant_id is not None:
        import uuid as _uuid
        q = q.where(Invoice.tenant_id == _uuid.UUID(str(tenant_id)))
    result = await db.execute(q)
    return [_serialize_invoice(i) for i in result.scalars().all()]


async def get_proposals(db: AsyncSession, status: str | None = None) -> list[dict]:
    q = select(Proposal).order_by(Proposal.created_at.desc())
    if status:
        q = q.where(Proposal.status == status)
    result = await db.execute(q)
    return [_serialize_proposal(p) for p in result.scalars().all()]


async def update_invoice_status(db: AsyncSession, invoice_id, new_status: str) -> bool:
    import uuid as _uuid
    try:
        _id = _uuid.UUID(str(invoice_id))
    except (ValueError, AttributeError):
        return False
    result = await db.execute(select(Invoice).where(Invoice.id == _id))
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
        "lead_id": str(p.lead_id) if getattr(p, "lead_id", None) else None,
        "package_tier": getattr(p, "package_tier", None),
        "invoice_number": getattr(p, "invoice_number", None),
        "proposal_style": p.proposal_style,
        "pricing": p.pricing,
        "content": p.content,
        "pdf_path": getattr(p, "pdf_path", None),
        "pdf_url": getattr(p, "pdf_url", None),
        "ai_generated": p.ai_generated,
        "status": p.status,
        "approved_at": p.approved_at.isoformat() if getattr(p, "approved_at", None) else None,
        "sent_at": p.sent_at.isoformat() if p.sent_at else None,
        "viewed_at": p.viewed_at.isoformat() if p.viewed_at else None,
        "responded_at": p.responded_at.isoformat() if p.responded_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


CONTRACT_PROMPT = """You are a senior legal drafter at Aliyar Solutions, a technology services company.
Generate a professional service agreement between Aliyar Solutions and the client below.

CLIENT: {client_name} ({client_company})
SERVICE TYPE: {service_type}
SCOPE: {scope}
PRICING: {pricing}
EFFECTIVE DATE: {effective_date}

The agreement must include the following sections, numbered and clearly titled:

1. PARTIES — Full legal names and addresses (use "Aliyar Solutions" and "{client_company}")
2. SERVICES — Specific scope of work based on the service type and scope above
3. FEES AND PAYMENT TERMS — Exact amounts from pricing, payment schedule, late payment terms (1.5%/month)
4. INTELLECTUAL PROPERTY — Work product ownership (client owns deliverables; Aliyar retains underlying IP)
5. CONFIDENTIALITY — Mutual NDA clause, 3-year term
6. TERM AND TERMINATION — Contract duration, 30-day written notice clause, survival of obligations
7. LIMITATION OF LIABILITY — Cap at total fees paid in 3 months; no consequential damages
8. INDEMNIFICATION — Each party indemnifies the other for their own negligence
9. GOVERNING LAW — Applicable jurisdiction (use international arbitration for cross-border)
10. ENTIRE AGREEMENT — Merger clause, amendment requires written consent

Tone: Formal, legally clear, professional. Do NOT use placeholder brackets like [INSERT].
Use the actual details provided above throughout.
Close with a SIGNATURES section showing two signature blocks:
- Aliyar Solutions — signed by Syed Abrar, CEO
- {client_company} — signed by {client_name}
Include date lines under each signature."""


async def generate_contract(
    db: AsyncSession,
    proposal_id: int | None,
    client_name: str,
    client_email: str,
    client_company: str,
    service_type: str,
    scope: str,
    pricing: dict,
) -> dict:
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import TaskType

    effective_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    pricing_str = json.dumps(pricing, indent=2)
    prompt = CONTRACT_PROMPT.format(
        client_name=client_name,
        client_company=client_company,
        service_type=service_type,
        scope=scope or "As discussed and agreed between the parties.",
        pricing=pricing_str,
        effective_date=effective_date,
    )
    messages = [Message(role="user", content=prompt)]

    try:
        response, _ = await ai_router.chat(
            messages,
            task_type=TaskType.STRATEGY,
            max_tokens=3000,
        )
        content = response.content.strip()
    except Exception as e:
        logger.warning("Contract generation AI failed: %s", e)
        content = (
            f"SERVICE AGREEMENT\n\n"
            f"This Service Agreement is entered into as of {effective_date} between "
            f"Aliyar Solutions and {client_company}.\n\n"
            f"SERVICE TYPE: {service_type}\n"
            f"PRICING: {pricing_str}\n\n"
            "[AI generation unavailable. Please complete this agreement manually.]\n\n"
            f"Signed:\nSyed Abrar, CEO — Aliyar Solutions\n\n"
            f"{client_name} — {client_company}"
        )

    contract = Contract(
        proposal_id=proposal_id,
        client_name=client_name,
        client_email=client_email,
        client_company=client_company,
        service_type=service_type,
        scope=scope,
        pricing=pricing,
        content=content,
        ai_generated=True,
        status="draft",
    )
    db.add(contract)
    await db.flush()
    return _serialize_contract(contract)


async def get_contracts(db: AsyncSession, status: str | None = None) -> list[dict]:
    q = select(Contract).order_by(Contract.created_at.desc()).limit(200)
    if status:
        q = q.where(Contract.status == status)
    result = await db.execute(q)
    return [_serialize_contract(c) for c in result.scalars().all()]


async def update_contract_status(db: AsyncSession, contract_id: int, new_status: str) -> bool:
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        return False
    contract.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == "sent":
        contract.sent_at = now
    elif new_status == "signed":
        contract.signed_at = now
    return True


def _serialize_contract(c: Contract) -> dict:
    return {
        "id": c.id,
        "proposal_id": c.proposal_id,
        "client_name": c.client_name,
        "client_email": c.client_email,
        "client_company": c.client_company,
        "service_type": c.service_type,
        "scope": c.scope,
        "pricing": c.pricing,
        "content": c.content,
        "pdf_path": c.pdf_path,
        "pdf_url": c.pdf_url,
        "ai_generated": c.ai_generated,
        "status": c.status,
        "sent_at": c.sent_at.isoformat() if c.sent_at else None,
        "signed_at": c.signed_at.isoformat() if c.signed_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
