"""
Wise transfer payment method — international, low-cost alternative to Stripe.
Uses httpx for REST API (no SDK dependency).
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

WISE_API_BASE = "https://api.wise.com/v1"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _wise_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.WISE_API_KEY or ''}",
        "Content-Type": "application/json",
    }


def _wise_configured() -> bool:
    return bool(settings.WISE_API_KEY and not settings.WISE_API_KEY.startswith("test_"))


async def create_wise_quote(
    amount_usd: float,
    target_currency: str = "USD",
) -> dict[str, Any]:
    """
    Get a Wise quote for international transfer.
    Returns exchange rate and fees.
    """
    if not _wise_configured():
        logger.warning("Wise not configured — set WISE_API_KEY in .env")
        return {
            "error": "Wise not configured",
            "amount": amount_usd,
            "currency": "USD",
        }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{WISE_API_BASE}/quotes",
                headers=_wise_headers(),
                json={
                    "source": "USD",
                    "target": target_currency,
                    "amount": amount_usd,
                    "type": "cheap",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "quote_id": data.get("id"),
                "source_amount": data.get("source", {}).get("value"),
                "target_amount": data.get("target", {}).get("value"),
                "target_currency": target_currency,
                "rate": data.get("rate"),
                "fee": data.get("fee"),
                "payOut": data.get("payOut"),
            }
    except Exception as exc:
        logger.error("Wise quote failed: %s", exc)
        return {"error": str(exc), "amount": amount_usd}


async def create_wise_transfer_request(
    invoice_id: str,
    invoice_number: str,
    amount_usd: float,
    client_name: str,
    client_email: str,
    recipient_details: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Create a Wise transfer request for invoice payment.
    Requires recipient bank details (or Wise will provide collection method).
    """
    if not _wise_configured():
        return {
            "error": "Wise not configured",
            "invoice_id": invoice_id,
        }

    logger.info("Wise transfer request initiated for invoice %s (amount: $%.2f)", invoice_number, amount_usd)

    return {
        "method": "wise_transfer",
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "amount_usd": amount_usd,
        "instructions": f"""
Wise Transfer Instructions for {client_name}:

1. Visit: https://wise.com
2. Send money
3. From: USD account
4. To: Your preferred currency & method
5. Amount: USD ${amount_usd:.2f}
6. Reference: Invoice {invoice_number}

Low fees | Real exchange rate | Fast & secure
""",
        "status": "pending_transfer",
        "currency": "USD",
        "estimated_delivery": "1-3 business days",
    }
