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
    """
    from app.core.config import settings

    # Company bank details (would be in config in production)
    bank_details = {
        "account_name": "Aliyar Solutions Inc.",
        "account_number": "****1234",  # Masked
        "routing_number": "****5678",  # Masked
        "swift_code": "CHUSUS33",
        "beneficiary_bank": "JP Morgan Chase",
        "description": f"Invoice {invoice_number}",
    }

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
        "created_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }
