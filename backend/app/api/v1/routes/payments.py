"""
Payment routes — Stripe payment link generation and webhook handler.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.auth import get_current_captain
from app.core.database import get_db
from app.services.payments.stripe_service import (
    create_payment_link,
    process_webhook_event,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])
webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class PaymentLinkRequest(BaseModel):
    currency: str = "usd"


@router.post("/invoices/{invoice_id}/payment-link")
async def generate_payment_link(
    invoice_id: str,
    req: PaymentLinkRequest = PaymentLinkRequest(),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_captain),
) -> dict[str, Any]:
    """Generate a Stripe Payment Link for an invoice and store the URL."""
    from app.models.revenue import Invoice
    from sqlalchemy import select
    import uuid

    try:
        inv_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")

    result = await db.execute(select(Invoice).where(Invoice.id == inv_uuid))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if inv.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")

    link_data = await create_payment_link(
        invoice_number=inv.invoice_number,
        amount_usd=float(inv.total),
        description=f"Invoice {inv.invoice_number} — Aliyar Solutions",
        client_name=inv.client_name or "Client",
        invoice_id=str(inv.id),
        currency=req.currency.lower(),
    )

    if "error" in link_data:
        logger.error("Stripe payment link creation failed for invoice %s: %s", invoice_id, link_data["error"])
        raise HTTPException(status_code=503, detail="Payment link generation failed")

    inv.payment_link = link_data["url"]
    await db.commit()

    logger.info("Payment link generated for invoice %s", inv.invoice_number)
    return {
        "invoice_id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "payment_url": link_data["url"],
        "payment_link_id": link_data["payment_link_id"],
        "amount_cents": link_data["amount_cents"],
        "currency": link_data["currency"],
    }


@router.post("/invoices/{invoice_id}/bank-transfer")
async def bank_transfer_details(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_captain),
) -> dict[str, Any]:
    """Get bank transfer details for an invoice (alternative payment method)."""
    from app.models.revenue import Invoice
    from app.services.payments.bank_transfer import create_bank_transfer_details
    from sqlalchemy import select
    import uuid

    try:
        inv_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")

    result = await db.execute(select(Invoice).where(Invoice.id == inv_uuid))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    details = await create_bank_transfer_details(
        invoice_id=str(inv.id),
        invoice_number=inv.invoice_number,
        amount_usd=float(inv.total),
        client_name=inv.client_name or "Client",
        client_email=inv.client_email or "",
    )
    return details


@router.post("/invoices/{invoice_id}/wise-transfer")
async def wise_transfer_details(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_captain),
) -> dict[str, Any]:
    """Get Wise transfer details for an invoice (international alternative)."""
    from app.models.revenue import Invoice
    from app.services.payments.wise_transfer import create_wise_transfer_request
    from sqlalchemy import select
    import uuid

    try:
        inv_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")

    result = await db.execute(select(Invoice).where(Invoice.id == inv_uuid))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    details = await create_wise_transfer_request(
        invoice_id=str(inv.id),
        invoice_number=inv.invoice_number,
        amount_usd=float(inv.total),
        client_name=inv.client_name or "Client",
        client_email=inv.client_email or "",
    )
    return details


@webhook_router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
) -> dict[str, Any]:
    """
    Public Stripe webhook endpoint — signature-verified, no auth required.
    Stripe sends events here when payment status changes.
    """
    payload = await request.body()

    if not verify_webhook_signature(payload, stripe_signature or ""):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    try:
        event = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    result = await process_webhook_event(event)
    return {"received": True, "result": result}
