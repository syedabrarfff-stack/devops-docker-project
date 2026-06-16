from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.revenue import Invoice, InvoiceStatus
from app.services.governance.invoice_engine import invoice_engine

router = APIRouter(prefix="/invoices", tags=["invoices"])


class InvoiceGenerateRequest(BaseModel):
    client_id: UUID
    amount_usd: float = Field(gt=0)
    description: str = Field(min_length=3, max_length=1000)
    due_days: int = Field(default=14, ge=1, le=90)
    tenant_id: Optional[UUID] = None


class InvoiceTenantRequest(BaseModel):
    tenant_id: Optional[UUID] = None


class InvoicePaymentRequest(BaseModel):
    amount: float = Field(gt=0)
    tenant_id: Optional[UUID] = None


@router.get("/")
async def list_invoices(
    request: Request,
    tenant_id: Optional[UUID] = None,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    """List invoices for a tenant, newest first."""
    tid = _resolve_tenant_id(request, tenant_id)
    async with AsyncSessionLocal() as session:
        q = (
            select(Invoice)
            .where(Invoice.tenant_id == tid)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        if status:
            try:
                q = q.where(Invoice.status == InvoiceStatus(status.upper()))
            except ValueError:
                pass
        rows = (await session.execute(q)).scalars().all()
    return {"invoices": [_serialize_invoice(inv) for inv in rows], "total": len(rows)}


@router.post("/generate")
async def generate_invoice(request: Request, body: InvoiceGenerateRequest):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        invoice = await invoice_engine.generate(
            client_id=body.client_id,
            amount_usd=body.amount_usd,
            description=body.description,
            due_days=body.due_days,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc
    return {"invoice": _serialize_invoice(invoice)}


@router.post("/{invoice_id}/send")
async def send_invoice(invoice_id: UUID, request: Request, body: InvoiceTenantRequest | None = None):
    tenant_id = _resolve_tenant_id(request, body.tenant_id if body else None)
    try:
        sent = await invoice_engine.send_invoice(invoice_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc
    return {"invoice_id": str(invoice_id), "sent": sent}


@router.post("/{invoice_id}/pay")
async def record_invoice_payment(invoice_id: UUID, request: Request, body: InvoicePaymentRequest):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        invoice = await invoice_engine.record_payment(invoice_id, amount=body.amount, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc
    try:
        from app.services.notifications.telegram import notify_telegram
        inv_num = invoice.invoice_number or str(invoice_id)[:8]
        amt = body.amount or 0
        client = invoice.client_company or invoice.client_name or "Client"
        await notify_telegram(
            f"✅ *Payment Received — {client}*\n"
            f"*Invoice:* `{inv_num}`\n"
            f"*Amount:* ${amt:,.0f}\n\n"
            "Revenue dashboard updated."
        )
    except Exception:
        pass
    return {"invoice": _serialize_invoice(invoice), "payment_recorded": True}


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID]) -> UUID:
    from app.core.config import settings

    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc


def _serialize_invoice(invoice: Invoice) -> dict:
    status = invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status)
    return {
        "id": str(invoice.id),
        "tenant_id": str(invoice.tenant_id),
        "client_id": str(invoice.client_id) if invoice.client_id else None,
        "invoice_number": invoice.invoice_number,
        "description": invoice.description,
        "amount_usd": invoice.amount_usd,
        "paid_amount_usd": invoice.paid_amount_usd,
        "total": invoice.total,
        "currency": invoice.currency,
        "status": status.lower(),
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "sent_at": invoice.sent_at.isoformat() if invoice.sent_at else None,
        "pdf_url": invoice.pdf_url,
        "client_name": invoice.client_name,
        "client_email": invoice.client_email,
        "client_company": invoice.client_company,
        "reminder_count": invoice.reminder_count,
    }
