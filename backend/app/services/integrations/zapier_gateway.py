"""R6-2: Zapier / Make.com webhook gateway.

Inbound: Zapier/Make calls JARVIS webhooks (form submissions, payment events, etc.)
Outbound: JARVIS calls registered Zapier/Make webhooks on key JARVIS events.

Security: HMAC-SHA256 on inbound requests using ZAPIER_WEBHOOK_SECRET.
         Make.com uses MAKE_WEBHOOK_SECRET.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── HMAC verification ─────────────────────────────────────────────────────────

def verify_zapier_signature(body: bytes | str, signature: str) -> bool:
    if not settings.ZAPIER_WEBHOOK_SECRET:
        logger.warning("ZAPIER_WEBHOOK_SECRET not set — rejecting inbound Zapier webhook")
        return False  # fail closed, matches Stripe/Telegram webhook hardening
    body_bytes = body.encode() if isinstance(body, str) else body
    expected = hmac.new(
        settings.ZAPIER_WEBHOOK_SECRET.encode(), body_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))


def verify_make_signature(body: bytes | str, signature: str) -> bool:
    if not settings.MAKE_WEBHOOK_SECRET:
        logger.warning("MAKE_WEBHOOK_SECRET not set — rejecting inbound Make webhook")
        return False  # fail closed, matches Stripe/Telegram webhook hardening
    body_bytes = body.encode() if isinstance(body, str) else body
    expected = hmac.new(
        settings.MAKE_WEBHOOK_SECRET.encode(), body_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))


# ── Inbound event handlers ────────────────────────────────────────────────────

async def handle_inbound_lead(payload: dict) -> dict[str, Any]:
    """
    Inbound Zapier trigger: new lead from a web form, Typeform, Calendly, etc.
    Creates a lead in JARVIS and starts the scoring pipeline.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.lead import Lead, LeadStatus
    from app.services.leads.scoring import lead_scoring_engine
    import uuid

    company = payload.get("company_name") or payload.get("company") or "Unknown"
    email = payload.get("email") or payload.get("contact_email") or ""
    name = payload.get("name") or payload.get("contact_name") or ""
    source = payload.get("source") or "zapier"

    system_tenant = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    try:
        async with AsyncSessionLocal() as session:
            lead = Lead(
                tenant_id=system_tenant,
                company_name=company,
                contact_name=name,
                contact_email=email,
                source=source,
                status=LeadStatus.NEW,
                raw_data=payload,
            )
            session.add(lead)
            await session.flush()
            lead_id = lead.id
            await session.commit()

        await lead_scoring_engine.score_lead(lead_id)
        logger.info("[Zapier] Inbound lead created: %s (%s)", company, lead_id)
        return {"status": "created", "lead_id": str(lead_id), "company": company}
    except Exception as exc:
        logger.error("[Zapier] Inbound lead failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


async def handle_inbound_payment(payload: dict) -> dict[str, Any]:
    """
    Inbound Zapier trigger: payment confirmed from an external payment processor.
    Marks the invoice paid and triggers client onboarding flow.
    """
    invoice_ref = payload.get("invoice_ref") or payload.get("reference", "")
    amount = payload.get("amount") or payload.get("amount_paid", 0)
    currency = payload.get("currency", "USD")
    payer = payload.get("payer_email") or payload.get("email", "")

    logger.info("[Zapier] Payment received: %s %s %s", invoice_ref, amount, currency)

    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text as sqla_text
        async with AsyncSessionLocal() as session:
            result = await session.execute(sqla_text(
                "UPDATE invoices SET status='PAID', paid_at=NOW(), "
                "notes=COALESCE(notes,'') || :note "
                "WHERE invoice_number ILIKE :ref"
            ), {
                "ref": f"%{invoice_ref}%",
                "note": f" | Paid via Zapier webhook {datetime.now(UTC).date()}"
            })
            await session.commit()
            updated = result.rowcount

        from app.services.notifications.slack import notify_slack
        await notify_slack(
            f"💰 Payment received: {currency} {amount} from {payer} (ref: {invoice_ref})"
        )
        return {"status": "processed", "invoices_updated": updated}
    except Exception as exc:
        logger.error("[Zapier] Payment processing failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


async def handle_generic_trigger(source: str, event_type: str, payload: dict) -> dict[str, Any]:
    """
    Generic inbound webhook — logs event to memory for AI processing.
    Useful for Make.com scenarios and custom Zapier steps.
    """
    logger.info("[Webhook] %s/%s received", source, event_type)
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.memory.manager import store_memory

        async with AsyncSessionLocal() as session:
            await store_memory(
                session,
                content=str(payload)[:2000],
                memory_type="episodic",
                key=f"webhook.{source}.{event_type}.{datetime.now(UTC).date()}",
                importance=0.4,
                tags=["webhook", source, event_type],
            )
            await session.commit()
        return {"status": "logged", "source": source, "event": event_type}
    except Exception as exc:
        logger.warning("[Webhook] Generic handler error: %s", exc)
        return {"status": "logged_partial", "detail": str(exc)}


# ── Outbound: trigger Zapier/Make hooks from JARVIS events ───────────────────

class ZapierGateway:
    """Fires outbound webhooks to registered Zapier/Make.com endpoints."""

    async def trigger(self, hook_url: str, event_type: str, payload: dict) -> bool:
        """POST payload to a Zapier or Make.com webhook URL."""
        if not hook_url:
            return False
        data = {
            "event": event_type,
            "source": "JARVIS",
            "timestamp": datetime.now(UTC).isoformat(),
            **payload,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(hook_url, json=data)
            ok = r.status_code < 300
            if not ok:
                logger.warning("[ZapierGateway] Hook %s → %s", hook_url[:60], r.status_code)
            return ok
        except Exception as exc:
            logger.warning("[ZapierGateway] Trigger failed: %s", exc)
            return False

    async def on_lead_qualified(self, lead_id: str, company: str, score: int) -> None:
        url = getattr(settings, "ZAPIER_LEAD_QUALIFIED_HOOK", None)
        if url:
            await self.trigger(url, "lead.qualified", {
                "lead_id": lead_id, "company": company, "score": score
            })

    async def on_proposal_sent(self, proposal_id: str, company: str, value_usd: float) -> None:
        url = getattr(settings, "ZAPIER_PROPOSAL_SENT_HOOK", None)
        if url:
            await self.trigger(url, "proposal.sent", {
                "proposal_id": proposal_id, "company": company, "value_usd": value_usd
            })

    async def on_approval_created(self, approval_id: int, title: str) -> None:
        url = getattr(settings, "MAKE_APPROVAL_HOOK", None)
        if url:
            await self.trigger(url, "approval.created", {
                "approval_id": approval_id, "title": title
            })


zapier_gateway = ZapierGateway()
