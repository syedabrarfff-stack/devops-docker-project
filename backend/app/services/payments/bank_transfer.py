"""
Bank transfer payment method — alternative to Stripe for high-trust clients.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


async def create_bank_transfer_details(
    invoice_id: str,
    invoice_number: str,
    amount_usd: float,
    client_name: str,
    client_email: str,
) -> dict[str, Any]:
    """
    Generate bank transfer details for an invoice.
    Returns wire instruction details that can be sent to client.

    SECURITY: this used to return fabricated bank details ("****1234",
    "JP Morgan Chase") unconditionally — fictitious wire information that
    would have been sent to a real client if this endpoint were ever used.
    Now sourced from real BANK_* settings; returns an honest "not
    configured" status instead of fake data when they're unset.
    """
    from datetime import datetime, timezone

    from app.core.config import settings

    required = {
        "account_name": settings.BANK_ACCOUNT_NAME,
        "account_number": settings.BANK_ACCOUNT_NUMBER,
        "routing_number": settings.BANK_ROUTING_NUMBER,
        "swift_code": settings.BANK_SWIFT_CODE,
        "beneficiary_bank": settings.BANK_BENEFICIARY_BANK,
    }
    if not all(required.values()):
        logger.warning(
            "Bank transfer requested for invoice %s but BANK_* settings are not configured",
            invoice_number,
        )
        return {
            "method": "bank_transfer",
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "amount_usd": amount_usd,
            "currency": "USD",
            "status": "not_configured",
            "blocker_code": "bank_details_not_configured",
            "human_message": "Company bank transfer details are not configured yet.",
            "required_action": (
                "Set BANK_ACCOUNT_NAME, BANK_ACCOUNT_NUMBER, BANK_ROUTING_NUMBER, "
                "BANK_SWIFT_CODE, and BANK_BENEFICIARY_BANK before offering wire transfer "
                "to clients."
            ),
        }

    bank_details = {**required, "description": f"Invoice {invoice_number}"}

    logger.info("Bank transfer details generated for invoice %s (amount: $%.2f)", invoice_number, amount_usd)

    return {
        "method": "bank_transfer",
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "amount_usd": amount_usd,
        "currency": "USD",
        "bank_details": bank_details,
        "instructions": f"""
Wire Instructions for {client_name}:
Amount: USD ${amount_usd:.2f}
Reference: Invoice {invoice_number}

Beneficiary: {bank_details['account_name']}
Account: {bank_details['account_number']}
Routing: {bank_details['routing_number']}
SWIFT: {bank_details['swift_code']}
Bank: {bank_details['beneficiary_bank']}

Description: {bank_details['description']}
""",
        "status": "pending_wire",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
