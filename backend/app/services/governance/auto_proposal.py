"""
Auto-proposal trigger — generates proposals automatically when leads qualify.
Implements autonomous lead→proposal→payment workflow.
"""
from __future__ import annotations

import logging
from uuid import UUID

from app.services.governance.auto_approval import should_auto_approve_proposal

logger = logging.getLogger(__name__)


async def auto_generate_proposal_for_lead(
    lead_id: UUID,
    lead_name: str,
    lead_email: str,
    lead_company: str,
    estimated_deal_value: float,
    lead_context: str = "",
    db = None,
) -> dict:
    """
    Automatically generate proposal when lead qualifies.
    If estimated deal < threshold, proposal auto-sends.
    Otherwise, queues for Captain approval.
    """
    from app.services.governance.document_gen import generate_proposal as _gen_proposal, update_proposal_status
    from app.services.governance.auto_approval import auto_approve_proposal
    from app.core.database import AsyncSessionLocal

    _own_db = db is None
    if _own_db:
        db = AsyncSessionLocal()

    try:
        async with db.begin():
            proposal = await _gen_proposal(
                db,
                client_name=lead_name,
                client_email=lead_email,
                client_company=lead_company,
                service_type="Custom Operating System",
                context=lead_context or f"Lead from {lead_company} interested in automation and growth systems.",
                pricing={
                    "setup_fee": max(2500, int(estimated_deal_value * 0.15)),
                    "monthly_retainer": max(1500, int(estimated_deal_value / 6)),
                },
                style="standard",
            )

        # Check if it qualifies for auto-send
        monthly_retainer = float(proposal.get("pricing", {}).get("monthly_retainer", 0) or estimated_deal_value)

        auto_approved = False
        if await should_auto_approve_proposal(monthly_retainer):
            # Auto-approve and mark as sent
            async with db.begin():
                ok = await update_proposal_status(db, proposal["id"], "sent")
                auto_approved = ok

        logger.info(
            "Auto-proposal generated for lead %s (%s) — value: $%.2f, auto_approved: %s",
            lead_name, lead_email, monthly_retainer, auto_approved
        )

        return {
            "success": True,
            "proposal_id": proposal["id"],
            "client_name": lead_name,
            "estimated_value": monthly_retainer,
            "auto_approved": auto_approved,
            "status": "sent" if auto_approved else "pending_approval",
            "action": "auto_proposal_generated"
        }

    except Exception as exc:
        logger.error("Auto-proposal generation failed for lead %s: %s", lead_name, exc)
        return {
            "success": False,
            "lead_id": str(lead_id),
            "error": str(exc),
        }
    finally:
        if _own_db:
            await db.close()


async def handle_lead_qualification(
    lead_id: UUID,
    lead_data: dict,
    db = None,
) -> dict:
    """
    Hook: called when lead status changes to "qualified".
    Triggers auto-proposal generation.
    """
    return await auto_generate_proposal_for_lead(
        lead_id=lead_id,
        lead_name=lead_data.get("name", "Prospect"),
        lead_email=lead_data.get("email", ""),
        lead_company=lead_data.get("company", ""),
        estimated_deal_value=lead_data.get("estimated_value", 5000),
        lead_context=lead_data.get("context", ""),
        db=db,
    )
