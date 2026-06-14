"""
Auto-approval logic — integrates autonomous governance engine with business workflows.
Tier-2 actions auto-execute with Captain notification.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.services.governance.autonomous_governance import autonomous_governance

logger = logging.getLogger(__name__)


async def should_auto_approve_proposal(amount_usd: float) -> bool:
    """Check if proposal meets auto-approval criteria."""
    if not settings.AUTO_APPROVE_PROPOSAL_THRESHOLD_USD:
        return False
    return amount_usd <= settings.AUTO_APPROVE_PROPOSAL_THRESHOLD_USD


async def should_auto_approve_invoice(amount_usd: float) -> bool:
    """Check if invoice meets auto-approval criteria."""
    if not settings.AUTO_APPROVE_INVOICE_THRESHOLD_USD:
        return False
    return amount_usd <= settings.AUTO_APPROVE_INVOICE_THRESHOLD_USD


async def should_auto_send_outreach(
    quality_score: float = None,
    is_warm_lead: bool = False,
) -> bool:
    """Check if outreach meets auto-send criteria."""
    if settings.OUTREACH_PAUSED:
        return False
    if not settings.AUTO_SEND_OUTREACH:
        return False

    if settings.AUTO_SEND_OUTREACH_WARM_LEADS_ONLY and not is_warm_lead:
        return False

    if quality_score is not None:
        if quality_score < settings.AUTO_SEND_OUTREACH_MIN_QUALITY_SCORE:
            return False

    return True


async def auto_approve_proposal(
    proposal_id: str,
    client_name: str,
    amount_usd: float,
    tenant_id: UUID,
) -> dict[str, Any]:
    """Queue Tier-2 proposal auto-approval and notify Captain."""
    evaluation = autonomous_governance.evaluate_action(
        "send_proposal_under_5k",
        {"proposal_id": proposal_id, "client": client_name, "amount": amount_usd},
        tenant_id,
    )

    if evaluation["tier"] > 2:
        # If amount exceeded threshold or other factors, escalate to Tier-3
        logger.info("Proposal %s escalated to Tier-3 (amount: $%.2f)", proposal_id, amount_usd)
        return await autonomous_governance.queue_tier3_action(
            "send_proposal_over_5k",
            {"proposal_id": proposal_id, "client": client_name, "amount": amount_usd},
            tenant_id,
        )

    result = await autonomous_governance.queue_tier2_action(
        "send_proposal_under_5k",
        {"proposal_id": proposal_id, "client": client_name, "amount": amount_usd},
        tenant_id,
    )
    logger.info("Proposal %s queued for auto-send (Tier-2) — Captain notified", proposal_id)
    return result


async def auto_approve_invoice(
    invoice_id: str,
    invoice_number: str,
    amount_usd: float,
    tenant_id: UUID,
) -> dict[str, Any]:
    """Queue Tier-2 invoice auto-marking as sent and notify Captain."""
    evaluation = autonomous_governance.evaluate_action(
        "generate_invoice_draft",
        {"invoice_id": invoice_id, "invoice_number": invoice_number, "amount": amount_usd},
        tenant_id,
    )

    if evaluation["tier"] > 2:
        logger.info("Invoice %s escalated to Tier-3 (amount: $%.2f)", invoice_number, amount_usd)
        return await autonomous_governance.queue_tier3_action(
            "approve_invoice",
            {"invoice_id": invoice_id, "invoice_number": invoice_number, "amount": amount_usd},
            tenant_id,
        )

    result = await autonomous_governance.queue_tier2_action(
        "generate_invoice_draft",
        {"invoice_id": invoice_id, "invoice_number": invoice_number, "amount": amount_usd},
        tenant_id,
    )
    logger.info("Invoice %s queued for auto-send (Tier-2) — Captain notified", invoice_number)
    return result


async def auto_approve_outreach(
    lead_id: str,
    lead_email: str,
    quality_score: float = None,
    tenant_id: UUID = None,
) -> dict[str, Any]:
    """Queue Tier-2 outreach auto-send and notify Captain."""
    result = await autonomous_governance.queue_tier2_action(
        "send_outreach_email",
        {"lead_id": lead_id, "lead_email": lead_email, "quality_score": quality_score},
        tenant_id,
    )
    logger.info("Outreach to %s queued for auto-send (Tier-2)", lead_email)
    return result
