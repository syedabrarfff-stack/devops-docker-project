"""
n8n Automation Webhook Bridge — triggers external automation workflows
from JARVIS business events (lead qualified, proposal sent, invoice paid, etc.)

n8n base: https://automation.aliyarsolutions.com
Webhook base: https://automation.aliyarsolutions.com/webhook
"""
import logging
import httpx
from typing import Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


async def trigger_webhook(path: str, payload: dict[str, Any], timeout: int = 15) -> bool:
    """POST to an n8n webhook endpoint. path = webhook path after /webhook/"""
    if not settings.N8N_WEBHOOK_URL:
        return False
    url = f"{settings.N8N_WEBHOOK_URL}/{path.lstrip('/')}"
    try:
        headers = {}
        if settings.N8N_API_KEY:
            headers["X-N8N-API-KEY"] = settings.N8N_API_KEY
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code < 300:
                logger.info("n8n webhook triggered: %s → %s", path, r.status_code)
                return True
            logger.warning("n8n webhook %s returned %s", path, r.status_code)
            return False
    except Exception as e:
        logger.warning("n8n webhook %s failed: %s", path, e)
        return False


async def on_lead_qualified(lead_id: str, company: str, email: str,
                             quality_score: float, service: Optional[str] = None) -> bool:
    return await trigger_webhook("jarvis/lead-qualified", {
        "lead_id": lead_id,
        "company": company,
        "email": email,
        "quality_score": quality_score,
        "service": service,
        "source": "jarvis",
    })


async def on_proposal_sent(proposal_id: str, client_name: str, email: str,
                            value_usd: float, auto_approved: bool = False) -> bool:
    return await trigger_webhook("jarvis/proposal-sent", {
        "proposal_id": proposal_id,
        "client_name": client_name,
        "email": email,
        "value_usd": value_usd,
        "auto_approved": auto_approved,
        "source": "jarvis",
    })


async def on_invoice_paid(invoice_id: str, invoice_number: str,
                           client_name: str, amount_usd: float,
                           payment_method: str) -> bool:
    return await trigger_webhook("jarvis/invoice-paid", {
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "client_name": client_name,
        "amount_usd": amount_usd,
        "payment_method": payment_method,
        "source": "jarvis",
    })


async def on_outreach_sent(lead_id: str, company: str, email: str,
                            subject: str, persona: str) -> bool:
    return await trigger_webhook("jarvis/outreach-sent", {
        "lead_id": lead_id,
        "company": company,
        "email": email,
        "subject": subject,
        "persona": persona,
        "source": "jarvis",
    })


async def on_captain_alert(alert_type: str, title: str, message: str,
                            severity: str = "high") -> bool:
    return await trigger_webhook("jarvis/captain-alert", {
        "alert_type": alert_type,
        "title": title,
        "message": message,
        "severity": severity,
        "source": "jarvis",
    })
