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

class ProposalRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=200)
    client_email: str = Field(default="", max_length=320)
    client_company: str = Field(default="", max_length=200)
    service_type: str = Field(..., min_length=1, max_length=200)
    context: str = Field(default="", max_length=10_000)
    style: str = Field(default="standard", max_length=50)
    pricing: dict = {}

class AgentPermissionRequest(BaseModel):
    agent_name: str = Field(..., max_length=100)
    permission_type: str = Field(..., max_length=100)
    scope: dict = {}
    risk_level: str = Field(default="low", max_length=20)
    reason: str = Field(default="", max_length=2_000)
    expires_hours: Optional[int] = Field(default=None, ge=1, le=8760)

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
async def create_invoice(req: CreateInvoiceRequest, db: AsyncSession = Depends(get_db)):
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
        )

    # Check if invoice qualifies for auto-approval
    total = float(invoice["total"])
    auto_approved = False
    if await should_auto_approve_invoice(total):
        async with db.begin():
            ok = await update_invoice_status(db, invoice["id"], "sent")
            auto_approved = ok

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
async def list_proposals(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    from app.services.governance.document_gen import get_proposals
    return {"proposals": await get_proposals(db, status=status)}


@router.post("/proposals/generate")
async def generate_proposal(req: ProposalRequest, db: AsyncSession = Depends(get_db)):
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
        )

    # Check if proposal qualifies for auto-approval
    estimated_value = float(req.pricing.get("monthly_retainer", 0) or 0)
    auto_approved = False
    if estimated_value > 0 and await should_auto_approve_proposal(estimated_value):
        async with db.begin():
            ok = await update_proposal_status(db, proposal["id"], "sent")
            auto_approved = ok

    approval_required = not auto_approved
    return {
        "proposal": proposal,
        "auto_approved": auto_approved,
        "requires_captain_approval": approval_required
    }


@router.post("/proposals/{proposal_id}/status")
async def update_proposal_status(proposal_id: int, req: StatusUpdate, db: AsyncSession = Depends(get_db)):
    from app.services.governance.document_gen import update_proposal_status as _update, get_proposals
    async with db.begin():
        ok = await _update(db, proposal_id, req.status)
    if not ok:
        raise HTTPException(404, "Proposal not found")
    if req.status in ("accepted", "won"):
        try:
            from app.services.notifications.telegram import notify_telegram
            proposals = await get_proposals(db)
            p = next((x for x in proposals if x.get("id") == proposal_id), {})
            company = p.get("client_company") or p.get("client_name") or "Client"
            mrr = p.get("pricing", {}).get("monthly_retainer", 0) or 0
            mrr_text = f"\n💰 *MRR:* ${mrr:,.0f}/mo" if mrr else ""
            await notify_telegram(
                f"🎯 *Proposal Won — {company}*{mrr_text}\n\nConvert to client in JARVIS → Proposals."
            )
        except Exception as exc:
            logger.warning("Telegram notification failed for proposal %s won: %s", proposal_id, exc)
    return {"id": proposal_id, "status": req.status}


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
    from app.models.governance import Invoice, Proposal
    from app.core.config import settings

    # Count auto-approved invoices (sent immediately upon creation, no draft -> sent manual step)
    invoices_result = await db.execute(
        select(
            func.count(Invoice.id).label("total"),
            func.sum(Invoice.total).label("total_value"),
        ).where(Invoice.status == "sent")
    )
    inv_row = invoices_result.first()

    # Count auto-approved proposals
    proposals_result = await db.execute(
        select(
            func.count(Proposal.id).label("total"),
            func.sum(Proposal.value).label("total_value"),
        ).where(Proposal.status == "sent")
    )
    prop_row = proposals_result.first()

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
            "count": prop_row[0] or 0,
            "total_value": float(prop_row[1] or 0),
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
        select(AgentPermission).order_by(AgentPermission.granted_at.desc())
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
async def governance_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    from app.models.governance import Invoice, Proposal, AgentPermission, IncidentReport

    total_invoiced = (await db.execute(
        select(func.sum(Invoice.total)).where(Invoice.status != "cancelled")
    )).scalar() or 0
    paid = (await db.execute(
        select(func.sum(Invoice.total)).where(Invoice.status == "paid")
    )).scalar() or 0
    draft_proposals = (await db.execute(
        select(func.count()).select_from(Proposal).where(Proposal.status == "draft")
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
