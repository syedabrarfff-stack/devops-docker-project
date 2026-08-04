"""
Stripe webhook — the other half of billing. Verifies the signature, then
delegates to billing_service to update Subscription/Clinic state.
"""

import logging

import stripe
from fastapi import APIRouter, HTTPException, Request

from app.config.settings import get_settings
from app.core.database import get_db_context
from app.services.billing_service import handle_stripe_event

logger = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])
settings = get_settings()


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        logger.error("Rejected Stripe webhook: STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=503, detail="Billing webhook not configured")

    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning(f"Rejected Stripe webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    async with get_db_context() as db:
        await handle_stripe_event(db, event)

    return {"status": "ok"}
