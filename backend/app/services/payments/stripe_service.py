"""
Stripe payment service — payment link creation, webhook processing, invoice sync.
Uses httpx directly (no stripe SDK dependency).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Optional
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

STRIPE_API_BASE = "https://api.stripe.com/v1"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def _configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY and not settings.STRIPE_SECRET_KEY.startswith("sk_test_placeholder"))


async def create_payment_link(
    invoice_number: str,
    amount_usd: float,
    description: str,
    client_name: str,
    invoice_id: str,
    currency: str = "usd",
) -> dict[str, Any]:
    """
    Creates a Stripe Payment Link for a given invoice.
    Returns {url, payment_link_id, price_id} or raises on failure.
    """
    if not _configured():
        return {"error": "Stripe not configured — set STRIPE_SECRET_KEY in .env"}

    amount_cents = int(round(amount_usd * 100))

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # 1. Create a one-time Price object
        price_resp = await client.post(
            f"{STRIPE_API_BASE}/prices",
            headers=_headers(),
            data={
                "unit_amount": str(amount_cents),
                "currency": currency,
                "product_data[name]": description[:500],
                "product_data[metadata][invoice_number]": invoice_number,
                "product_data[metadata][client]": client_name[:100],
            },
        )
        price_resp.raise_for_status()
        price = price_resp.json()
        price_id = price["id"]

        # 2. Create the Payment Link
        link_resp = await client.post(
            f"{STRIPE_API_BASE}/payment_links",
            headers=_headers(),
            data={
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "metadata[invoice_id]": invoice_id,
                "metadata[invoice_number]": invoice_number,
                "after_completion[type]": "hosted_confirmation",
                "after_completion[hosted_confirmation][custom_message]": (
                    f"Thank you for your payment, {client_name}. "
                    "Aliyar Solutions will confirm receipt within 24 hours."
                ),
            },
        )
        link_resp.raise_for_status()
        link = link_resp.json()

    logger.info("Stripe payment link created for invoice %s: %s", invoice_number, link["url"])
    return {
        "url": link["url"],
        "payment_link_id": link["id"],
        "price_id": price_id,
        "amount_cents": amount_cents,
        "currency": currency,
    }


def verify_webhook_signature(payload: bytes, sig_header: str) -> bool:
    """Verify Stripe webhook signature using STRIPE_WEBHOOK_SECRET."""
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — webhook signature not verified")
        return True  # permissive fallback; lock down once secret is set

    try:
        parts = {k: v for k, v in (item.split("=", 1) for item in sig_header.split(","))}
        timestamp = int(parts.get("t", 0))
        sig = parts.get("v1", "")

        # Reject webhooks older than 5 minutes (replay protection)
        if abs(time.time() - timestamp) > 300:
            logger.warning("Stripe webhook timestamp too old — possible replay attack")
            return False

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, sig)
    except Exception as exc:
        logger.warning("Stripe signature verification error: %s", exc)
        return False


async def process_webhook_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Process a verified Stripe webhook event.
    Handles: checkout.session.completed, payment_link.completed, payment_intent.succeeded
    Returns action taken.
    """
    event_type = event.get("type", "")
    data_obj = event.get("data", {}).get("object", {})

    if event_type in ("checkout.session.completed", "payment_link.completed"):
        invoice_id = (
            data_obj.get("metadata", {}).get("invoice_id")
            or data_obj.get("metadata", {}).get("invoice_number")
        )
        amount_paid = data_obj.get("amount_total", 0) / 100
        payment_status = data_obj.get("payment_status")

        if payment_status == "paid" and invoice_id:
            return await _mark_invoice_paid(invoice_id, amount_paid, "stripe", event.get("id"))

    elif event_type == "payment_intent.succeeded":
        amount_paid = data_obj.get("amount", 0) / 100
        invoice_id = data_obj.get("metadata", {}).get("invoice_id")
        if invoice_id:
            return await _mark_invoice_paid(invoice_id, amount_paid, "stripe", event.get("id"))

    return {"action": "ignored", "event_type": event_type}


async def _mark_invoice_paid(
    invoice_ref: str,
    amount: float,
    method: str,
    stripe_event_id: Optional[str],
) -> dict[str, Any]:
    """Mark an invoice as PAID in the database."""
    from app.core.database import AsyncSessionLocal
    from app.services.governance.invoice_engine import invoice_engine
    import uuid

    try:
        # invoice_ref may be UUID or invoice number
        try:
            invoice_id = uuid.UUID(invoice_ref)
        except ValueError:
            # It's an invoice number — look it up
            from app.models.revenue import Invoice
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Invoice).where(Invoice.invoice_number == invoice_ref)
                )
                inv = result.scalar_one_or_none()
                if not inv:
                    logger.warning("Stripe webhook: invoice %s not found", invoice_ref)
                    return {"action": "not_found", "invoice_ref": invoice_ref}
                invoice_id = inv.id

        result = await invoice_engine.record_payment(
            invoice_id=invoice_id,
            amount=amount,
            method=method,
        )
        logger.info(
            "Invoice %s marked PAID via Stripe (event: %s, amount: $%.2f)",
            invoice_ref, stripe_event_id, amount
        )

        # Notify Captain via Slack + Telegram + n8n
        try:
            from app.services.notifications.slack import notify_captain
            from app.services.notifications.telegram import notify_telegram
            from app.services.notifications.n8n import on_invoice_paid
            await notify_captain(
                title=f"💰 Payment received — ${amount:.2f}",
                body=f"Invoice {invoice_ref} paid via Stripe. Amount: ${amount:.2f}",
                level="info",
            )
            await notify_telegram(
                f"💰 *Payment Received*\n\nInvoice: `{invoice_ref}`\nAmount: *${amount:.2f}*\nMethod: Stripe"
            )
            await on_invoice_paid(
                invoice_id=str(invoice_id),
                invoice_number=invoice_ref,
                client_name="",
                amount_usd=amount,
                payment_method="stripe",
            )
        except Exception:
            pass

        return {"action": "invoice_marked_paid", "invoice_ref": invoice_ref, "amount": amount}

    except Exception as exc:
        logger.error("Failed to mark invoice %s as paid: %s", invoice_ref, exc)
        return {"action": "error", "error": str(exc)}
