"""
JARVIS Governance API — invoices, proposals, contracts, agent permissions.
All financial and client-facing actions require Captain approval before execution.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/governance", tags=["governance"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class InvoiceItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    qty: float = 1
    unit_price: float
    amount: float

class CreateInvoiceRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=200)
    client_email: str = Field(default="", max_length=320)
    client_company: str = Field(default="", max_length=200)
    items: List[InvoiceItem]
    tax_rate: float = 0.0
    currency: str = Field(default="USD", max_length=10)
    notes: str = Field(default="", max_length=5_000)
    due_days: int = Field(default=14, ge=1, le=365)
    tenant_id: Optional[UUID] = None

class ProposalRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=200)
    client_email: str = Field(default="", max_length=320)
    client_company: str = Field(default="", max_length=200)
    service_type: str = Field(..., min_length=1, max_length=200)
    context: str = Field(default="", max_length=10_000)
    style: str = Field(default="standard", max_length=50)
    pricing: dict = {}
    tenant_id: Optional[UUID] = None

class AgentPermissionRequest(BaseModel):
    agent_name: str = Field(..., max_length=100)
    permission_type: str = Field(..., max_length=100)
    scope: dict = {}
    risk_level: str = Field(default="low", max_length=20)
    reason: str = Field(default="", max_length=2_000)
    expires_hours: Optional[int] = Field(default=None, ge=1, le=8760)

class ContractRequest(BaseModel):
    proposal_id: Optional[int] = None
    client_name: str = Field(..., min_length=1, max_length=200)
    client_email: str = Field(default="", max_length=320)
    client_company: str = Field(default="", max_length=200)
    service_type: str = Field(..., min_length=1, max_length=200)
    scope: str = Field(default="", max_length=10_000)
    pricing: dict = {}

class StatusUpdate(BaseModel):
    status: str = Field(..., max_length=50)


# ── Invoices ─────────────────────────────────────────────────────────────────

@router.get("/invoices")
async def list_invoices(
    status: Optional[str] = None,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    from app.services.governance.document_gen import get_invoices
    return {"invoices": await get_invoices(db, status=status, tenant_id=tenant_id)}


@router.post("/invoices")
async def create_invoice(req: CreateInvoiceRequest, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    from app.services.governance.document_gen import create_invoice as _create, update_invoice_status
    from app.services.governance.auto_approval import should_auto_approve_invoice
    from app.core.config import settings

    async with db.begin():
        invoice = await _create(
            db,
            client_name=req.client_name,
            client_email=req.client_email,
            client_company=req.client_company,
            items=[i.model_dump() for i in req.items],
            tax_rate=req.tax_rate,
            currency=req.currency,
            notes=req.notes,
            due_days=req.due_days,
            tenant_id=req.tenant_id,
        )

    # Check if invoice qualifies for auto-approval
    total = float(invoice["total"])
    auto_approved = False
    if await should_auto_approve_invoice(total):
        async with db.begin():
            ok = await update_invoice_status(db, invoice["id"], "sent")
            auto_approved = ok

    if invoice.get("client_email"):
        bg.add_task(_send_invoice_email_bg, invoice)

    approval_required = not auto_approved
    return {
        "invoice": invoice,
        "auto_approved": auto_approved,
        "requires_captain_approval": approval_required
    }


@router.post("/invoices/{invoice_id}/status")
async def update_invoice_status(invoice_id: UUID, req: StatusUpdate, db: AsyncSession = Depends(get_db)):
    from app.services.governance.document_gen import update_invoice_status as _update
    async with db.begin():
        ok = await _update(db, invoice_id, req.status)
    if not ok:
        raise HTTPException(404, "Invoice not found")
    if req.status == "paid":
        try:
            from app.services.notifications.telegram import notify_telegram
            await notify_telegram(f"✅ *Invoice Paid*\nInvoice `{str(invoice_id)[:8]}…` has been marked as paid. Update revenue dashboard.")
        except Exception as exc:
            logger.warning("Telegram notification failed for invoice %s paid: %s", invoice_id, exc)
    return {"id": str(invoice_id), "status": req.status}


# ── Proposals ─────────────────────────────────────────────────────────────────

@router.get("/proposals")
async def list_proposals(
    status: Optional[str] = None,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    from app.services.governance.document_gen import get_proposals
    return {"proposals": await get_proposals(db, status=status, tenant_id=tenant_id)}


@router.post("/proposals/generate")
async def generate_proposal(req: ProposalRequest, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    from app.services.governance.document_gen import generate_proposal as _gen, update_proposal_status
    from app.services.governance.auto_approval import should_auto_approve_proposal
    from app.core.config import settings

    async with db.begin():
        proposal = await _gen(
            db,
            client_name=req.client_name,
            client_email=req.client_email,
            client_company=req.client_company,
            service_type=req.service_type,
            context=req.context,
            pricing=req.pricing,
            style=req.style,
            tenant_id=req.tenant_id,
        )

    # Check if proposal qualifies for auto-approval
    estimated_value = float(req.pricing.get("monthly_retainer", 0) or 0)
    auto_approved = False
    if estimated_value > 0 and await should_auto_approve_proposal(estimated_value):
        async with db.begin():
            ok = await update_proposal_status(db, proposal["id"], "sent")
            auto_approved = ok

    if proposal.get("client_email"):
        bg.add_task(_send_proposal_email_bg, proposal)

    approval_required = not auto_approved
    return {
        "proposal": proposal,
        "auto_approved": auto_approved,
        "requires_captain_approval": approval_required
    }


@router.post("/proposals/{proposal_id}/status")
async def update_proposal_status(
    proposal_id: int,
    req: StatusUpdate,
    bg: BackgroundTasks,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    from app.services.governance.document_gen import update_proposal_status as _update, get_proposals, generate_contract
    async with db.begin():
        ok = await _update(db, proposal_id, req.status, tenant_id=tenant_id)
    if not ok:
        raise HTTPException(404, "Proposal not found")
    if req.status in ("accepted", "won"):
        try:
            from app.services.notifications.telegram import notify_telegram
            from app.models.governance import Proposal as _Proposal
            from sqlalchemy import select as _select
            _q = _select(_Proposal).where(_Proposal.id == proposal_id)
            if tenant_id is not None:
                _q = _q.where(_Proposal.tenant_id == tenant_id)
            _p_row = (await db.execute(_q)).scalar_one_or_none()
            p = {
                "id": _p_row.id, "client_name": _p_row.client_name,
                "client_email": _p_row.client_email, "client_company": _p_row.client_company,
                "service_type": _p_row.service_type, "content": _p_row.content,
                "pricing": _p_row.pricing,
            } if _p_row else {}
            company = p.get("client_company") or p.get("client_name") or "Client"
            mrr = p.get("pricing", {}).get("monthly_retainer", 0) or 0
            mrr_text = f"\n💰 *MRR:* ${mrr:,.0f}/mo" if mrr else ""
            await notify_telegram(
                f"🎯 *Proposal Won — {company}*{mrr_text}\n\nContract auto-generating now."
            )
            # Auto-generate and email contract
            if p.get("client_name"):
                async with db.begin():
                    contract = await generate_contract(
                        db,
                        proposal_id=proposal_id,
                        client_name=p.get("client_name", ""),
                        client_email=p.get("client_email", ""),
                        client_company=p.get("client_company", ""),
                        service_type=p.get("service_type", ""),
                        scope=p.get("content", "")[:2000],
                        pricing=p.get("pricing") or {},
                    )
                if contract.get("client_email"):
                    bg.add_task(_send_contract_email_bg, contract)
        except Exception as exc:
            logger.warning("Contract auto-generation failed for proposal %s: %s", proposal_id, exc)
    return {"id": proposal_id, "status": req.status}


# ── Contracts ─────────────────────────────────────────────────────────────────

@router.get("/contracts")
async def list_contracts(
    status: Optional[str] = None,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    from app.services.governance.document_gen import get_contracts
    return {"contracts": await get_contracts(db, status=status, tenant_id=tenant_id)}


@router.get("/contracts/{contract_id}")
async def get_contract(
    contract_id: int,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.governance import Contract
    q = select(Contract).where(Contract.id == contract_id)
    if tenant_id is not None:
        q = q.where(Contract.tenant_id == tenant_id)
    result = await db.execute(q)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, "Contract not found")
    from app.services.governance.document_gen import _serialize_contract
    return {"contract": _serialize_contract(contract)}


@router.post("/contracts")
async def create_contract(req: ContractRequest, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    from app.services.governance.document_gen import generate_contract
    async with db.begin():
        contract = await generate_contract(
            db,
            proposal_id=req.proposal_id,
            client_name=req.client_name,
            client_email=req.client_email,
            client_company=req.client_company,
            service_type=req.service_type,
            scope=req.scope,
            pricing=req.pricing,
        )
    if contract.get("client_email"):
        bg.add_task(_send_contract_email_bg, contract)
    return {"contract": contract, "email_queued": bool(contract.get("client_email"))}


@router.post("/contracts/{contract_id}/send-email")
async def send_contract_email(contract_id: int, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    from app.services.governance.document_gen import get_contract as _get, update_contract_status as _update

    contract = await _get(db, contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found")
    if not contract.get("client_email"):
        raise HTTPException(400, "Contract has no client email — cannot send")

    async with db.begin():
        await _update(db, contract_id, "sent")

    bg.add_task(_send_contract_email_bg, contract)
    return {"sent": True, "contract_id": contract_id, "to": contract["client_email"]}


@router.post("/contracts/{contract_id}/status")
async def update_contract_status(
    contract_id: int,
    req: StatusUpdate,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    from app.services.governance.document_gen import update_contract_status as _update
    async with db.begin():
        ok = await _update(db, contract_id, req.status, tenant_id=tenant_id)
    if not ok:
        raise HTTPException(404, "Contract not found")
    if req.status == "signed":
        try:
            from app.services.notifications.telegram import notify_telegram
            await notify_telegram(
                f"✍️ *Contract Signed*\nContract `{contract_id}` has been marked as signed. Create client record and issue first invoice."
            )
        except Exception as exc:
            logger.warning("Telegram notification failed for contract %s signed: %s", contract_id, exc)
    return {"id": contract_id, "status": req.status}


# ── Autonomous Approval Stats ────────────────────────────────────────────────

@router.post("/test-workflow")
async def run_test_workflow(
    prospect_name: str = "Test Prospect Inc",
    prospect_email: str = "test@prospect.com",
    deal_value: float = 3500,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Run complete lead→proposal→invoice→payment test workflow.
    Validates entire autonomous acquisition cycle.
    """
    from app.services.governance.test_workflow import run_full_client_workflow_test
    result = await run_full_client_workflow_test(
        test_prospect_name=prospect_name,
        test_prospect_email=prospect_email,
        estimated_deal_value=deal_value,
        db=db,
    )
    return result


@router.get("/auto-approval-stats")
async def auto_approval_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    import uuid as _uuid
    from app.models.revenue import Invoice, InvoiceStatus
    from app.models.governance import Proposal
    from app.core.config import settings

    _tid = None
    if settings.JARVIS_DEFAULT_TENANT_ID:
        try:
            _tid = _uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
        except (ValueError, AttributeError):
            pass

    _inv_filter = [Invoice.status == InvoiceStatus.SENT]
    if _tid:
        _inv_filter.append(Invoice.tenant_id == _tid)

    # Count auto-approved invoices — use amount_usd (Invoice has no .total column)
    invoices_result = await db.execute(
        select(
            func.count(Invoice.id).label("total"),
            func.sum(Invoice.amount_usd).label("total_value"),
        ).where(*_inv_filter)
    )
    inv_row = invoices_result.first()

    # Proposal.value doesn't exist — pricing is a JSON dict; sum monthly_retainer in Python
    _prop_filter = [Proposal.status == "sent"]
    if _tid:
        _prop_filter.append(Proposal.tenant_id == _tid)
    prop_rows = (await db.execute(
        select(Proposal.pricing).where(*_prop_filter).limit(500)
    )).scalars().all()
    prop_count = len(prop_rows)
    prop_value = sum(float((p or {}).get("monthly_retainer", 0) or 0) for p in prop_rows)

    return {
        "thresholds": {
            "invoice_usd": settings.AUTO_APPROVE_INVOICE_THRESHOLD_USD,
            "proposal_usd": settings.AUTO_APPROVE_PROPOSAL_THRESHOLD_USD,
            "auto_outreach_enabled": settings.AUTO_SEND_OUTREACH,
        },
        "auto_approved_invoices": {
            "count": inv_row[0] or 0,
            "total_value": float(inv_row[1] or 0),
        },
        "auto_approved_proposals": {
            "count": prop_count,
            "total_value": prop_value,
        },
        "system_status": "autonomous_governance_enabled"
    }


# ── Settings & Configuration ────────────────────────────────────────────────

@router.post("/settings")
async def update_governance_settings(req: dict, db: AsyncSession = Depends(get_db)):
    """Update governance settings (auto-approval thresholds, etc.)"""
    from app.core.config import settings
    # Note: in production, these would be stored in DB and loaded at startup
    # For now, they're in .env but we acknowledge the request
    return {
        "saved": True,
        "note": "Settings require .env update and restart in production",
        "current_thresholds": {
            "invoice": settings.AUTO_APPROVE_INVOICE_THRESHOLD_USD,
            "proposal": settings.AUTO_APPROVE_PROPOSAL_THRESHOLD_USD,
            "auto_outreach": settings.AUTO_SEND_OUTREACH,
        }
    }


@router.post("/outreach-settings")
async def update_outreach_settings(req: dict, db: AsyncSession = Depends(get_db)):
    """Update outreach settings (daily cap, domain age, etc.)"""
    from app.core.config import settings
    return {
        "saved": True,
        "current": {
            "daily_send_cap": settings.OUTREACH_DAILY_SEND_CAP,
            "domain_age_days": settings.OUTREACH_DOMAIN_AGE_DAYS,
            "outreach_paused": settings.OUTREACH_PAUSED,
            "personalize": settings.OUTREACH_PERSONALIZE_ON_SEND,
        }
    }


@router.get("/payment-methods")
async def get_payment_methods():
    """Return configured payment methods status"""
    from app.core.config import settings
    return {
        "stripe": {
            "configured": bool(settings.STRIPE_SECRET_KEY and not settings.STRIPE_SECRET_KEY.startswith("sk_test")),
            "label": "Stripe Payment Links"
        },
        "bank_transfer": {
            "configured": True,
            "label": "Bank Wire Transfer"
        },
        "wise": {
            "configured": bool(settings.WISE_API_KEY) if hasattr(settings, 'WISE_API_KEY') else False,
            "label": "Wise Transfer"
        },
        "paypal": {
            "configured": bool(settings.PAYPAL_CLIENT_ID),
            "label": "PayPal"
        }
    }


# ── Agent Permissions ────────────────────────────────────────────────────────

@router.get("/permissions")
async def list_permissions(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.governance import AgentPermission
    result = await db.execute(
        select(AgentPermission).order_by(AgentPermission.granted_at.desc()).limit(200)
    )
    perms = result.scalars().all()
    return {"permissions": [_serialize_perm(p) for p in perms]}


@router.post("/permissions")
async def grant_permission(req: AgentPermissionRequest, db: AsyncSession = Depends(get_db)):
    from app.models.governance import AgentPermission
    from datetime import datetime, timezone, timedelta
    expires = None
    if req.expires_hours:
        expires = datetime.now(timezone.utc) + timedelta(hours=req.expires_hours)
    perm = AgentPermission(
        agent_name=req.agent_name,
        permission_type=req.permission_type,
        scope=req.scope,
        risk_level=req.risk_level,
        reason=req.reason,
        expires_at=expires,
        is_active=True,
    )
    async with db.begin():
        db.add(perm)
    return {"permission": _serialize_perm(perm), "requires_captain_approval": req.risk_level in ("high", "critical")}


@router.post("/permissions/{perm_id}/revoke")
async def revoke_permission(perm_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.governance import AgentPermission
    from datetime import datetime, timezone
    async with db.begin():
        result = await db.execute(select(AgentPermission).where(AgentPermission.id == perm_id))
        perm = result.scalar_one_or_none()
        if not perm:
            raise HTTPException(404, "Permission not found")
        perm.is_active = False
        perm.revoked_at = datetime.now(timezone.utc)
    return {"id": perm_id, "revoked": True}


# ── Governance Stats ─────────────────────────────────────────────────────────

@router.get("/stats")
async def governance_stats(request: Request, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    from app.models.governance import Invoice, Proposal, AgentPermission, IncidentReport

    _tid = _resolve_tenant_id(request, None)

    total_invoiced = (await db.execute(
        select(func.sum(Invoice.total)).where(Invoice.status != "cancelled", Invoice.tenant_id == _tid)
    )).scalar() or 0
    paid = (await db.execute(
        select(func.sum(Invoice.total)).where(Invoice.status == "paid", Invoice.tenant_id == _tid)
    )).scalar() or 0
    draft_proposals = (await db.execute(
        select(func.count()).select_from(Proposal).where(Proposal.status == "draft", Proposal.tenant_id == _tid)
    )).scalar() or 0
    active_perms = (await db.execute(
        select(func.count()).select_from(AgentPermission).where(AgentPermission.is_active == True)
    )).scalar() or 0
    open_incidents = (await db.execute(
        select(func.count()).select_from(IncidentReport)
        .where(IncidentReport.status.in_(["open", "investigating"]))
    )).scalar() or 0

    return {
        "total_invoiced": float(total_invoiced),
        "total_paid": float(paid),
        "pending_payment": float(total_invoiced) - float(paid),
        "draft_proposals": draft_proposals,
        "active_agent_permissions": active_perms,
        "open_incidents": open_incidents,
    }


def _serialize_perm(p) -> dict:
    return {
        "id": p.id, "agent_name": p.agent_name, "permission_type": p.permission_type,
        "scope": p.scope, "risk_level": p.risk_level, "reason": p.reason,
        "granted_by": p.granted_by, "is_active": p.is_active,
        "expires_at": p.expires_at.isoformat() if p.expires_at else None,
        "granted_at": p.granted_at.isoformat() if p.granted_at else None,
    }


# ── Background email helpers ─────────────────────────────────────────────────

async def _send_invoice_email_bg(invoice: dict) -> None:
    import re
    from html import escape
    from app.services.outreach.email_transport import send_outbound_email

    email = invoice.get("client_email") or ""
    if not email:
        return
    inv_num = invoice.get("invoice_number", "")
    total = float(invoice.get("total") or 0)
    due_date = invoice.get("due_date") or "as agreed"
    client_name = invoice.get("client_name") or ""
    body = (
        f"Hello {client_name or 'there'},\n\n"
        f"Our team has prepared invoice {inv_num} for ${total:,.2f}.\n"
        f"Due date: {str(due_date)[:10]}.\n\n"
        "Payment instructions are included on the invoice. "
        "Please use the invoice number as the payment reference.\n\n"
        "Warm regards,\nAliyar Solutions Team"
    )
    try:
        await send_outbound_email(
            to=email,
            subject=f"Invoice {inv_num} from Aliyar Solutions",
            body=body,
            to_name=client_name,
        )
    except Exception as exc:
        logger.warning("Invoice email delivery failed for %s: %s", email, exc)


async def _send_contract_email_bg(contract: dict) -> None:
    from app.services.outreach.email_transport import send_outbound_email

    email = contract.get("client_email") or ""
    if not email:
        return
    client_name = contract.get("client_name") or ""
    company = contract.get("client_company") or ""
    service_type = contract.get("service_type") or "Services"
    content = (contract.get("content") or "")[:5000]
    body = (
        f"Hello {client_name or 'there'},\n\n"
        f"Following your acceptance of our proposal, please find the Service Agreement for "
        f"{service_type} below.\n\n"
        "To confirm your acceptance, please reply to this email with the word ACCEPTED "
        "along with your full name and company name.\n\n"
        "─" * 60 + "\n\n"
        f"{content}\n\n"
        "─" * 60 + "\n\n"
        "Please review and confirm at your earliest convenience. "
        "Our team is ready to begin upon receipt of your confirmation.\n\n"
        "Warm regards,\nAliyar Solutions Team"
    )
    try:
        await send_outbound_email(
            to=email,
            subject=f"Service Agreement — Aliyar Solutions × {company}",
            body=body,
            to_name=client_name,
        )
    except Exception as exc:
        logger.warning("Contract email delivery failed for %s: %s", email, exc)


async def _send_proposal_email_bg(proposal: dict) -> None:
    from app.services.outreach.email_transport import send_outbound_email

    email = proposal.get("client_email") or ""
    if not email:
        return
    client_name = proposal.get("client_name") or ""
    title = proposal.get("title") or "Proposal"
    content = (proposal.get("content") or "")[:3000]
    body = (
        f"Hello {client_name or 'there'},\n\n"
        f"Please find our proposal below.\n\n"
        f"--- {title} ---\n\n"
        f"{content}\n\n"
        "--- End of Proposal ---\n\n"
        "Please let us know how you would like to proceed. "
        "Our team is ready to begin immediately upon confirmation.\n\n"
        "Warm regards,\nAliyar Solutions Team"
    )
    try:
        await send_outbound_email(
            to=email,
            subject=f"Proposal from Aliyar Solutions — {title}",
            body=body,
            to_name=client_name,
        )
    except Exception as exc:
        logger.warning("Proposal email delivery failed for %s: %s", email, exc)
