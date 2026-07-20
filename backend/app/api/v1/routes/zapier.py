"""R6-2 Route: Zapier / Make.com webhook gateway.

Inbound endpoints (Zapier/Make calls JARVIS):
  POST /api/v1/webhooks/zapier/lead        — new lead from web form
  POST /api/v1/webhooks/zapier/payment     — payment confirmed
  POST /api/v1/webhooks/make/trigger       — generic Make.com scenario trigger

Every endpoint requires a valid HMAC signature (X-Zapier-Signature /
X-Make-Signature) — verified unconditionally, not only when the header
happens to be present. verify_zapier_signature/verify_make_signature
themselves fail closed if ZAPIER_WEBHOOK_SECRET/MAKE_WEBHOOK_SECRET
aren't configured. (An earlier version of this file only checked the
signature `if sig` was present at all, so simply omitting the header
skipped verification entirely — on /zapier/payment that meant anyone
could mark an arbitrary invoice paid with one unauthenticated POST.)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Any

from app.services.integrations.zapier_gateway import (
    verify_zapier_signature,
    verify_make_signature,
    handle_inbound_lead,
    handle_inbound_payment,
    handle_generic_trigger,
)

router = APIRouter(prefix="/webhooks", tags=["Zapier / Make.com"])


# ── Inbound: Zapier → JARVIS ──────────────────────────────────────────────────

@router.post("/zapier/lead")
async def zapier_inbound_lead(request: Request):
    """Receive a new lead from a Zapier-connected form (Typeform, JotForm, Calendly, etc.)."""
    body = await request.body()
    sig = request.headers.get("X-Zapier-Signature", "")
    if not verify_zapier_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid Zapier signature")

    payload = await request.json()
    return await handle_inbound_lead(payload)


@router.post("/zapier/payment")
async def zapier_inbound_payment(request: Request):
    """Receive a payment confirmation from Zapier (Stripe, PayPal, Wise, etc.)."""
    body = await request.body()
    sig = request.headers.get("X-Zapier-Signature", "")
    if not verify_zapier_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid Zapier signature")

    payload = await request.json()
    return await handle_inbound_payment(payload)


@router.post("/make/trigger")
async def make_inbound_trigger(request: Request):
    """Receive a generic trigger from a Make.com scenario."""
    body = await request.body()
    sig = request.headers.get("X-Make-Signature", "")
    if not verify_make_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid Make.com signature")

    payload = await request.json()
    event_type = request.query_params.get("event", "generic")
    return await handle_generic_trigger("make", event_type, payload)


@router.post("/make/lead")
async def make_inbound_lead(request: Request):
    """Convenience alias — Make.com lead scenario."""
    body = await request.body()
    sig = request.headers.get("X-Make-Signature", "")
    if not verify_make_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid Make.com signature")

    payload = await request.json()
    return await handle_inbound_lead(payload)
