"""
Autonomous outreach engine — sends emails to qualified leads without Captain review.
Implements lead qualification → outreach email → proposal follow-up chain.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


async def should_send_outreach(
    lead_quality_score: float,
    lead_status: str,
    domain_age_days: int,
    min_quality_threshold: float = 0.70,
) -> tuple[bool, str]:
    """
    Determine if lead qualifies for auto-outreach.
    Returns (should_send, reason).
    """
    if lead_status not in ("qualified", "hot", "active"):
        return False, f"Lead status '{lead_status}' not eligible for auto-outreach"

    if lead_quality_score < min_quality_threshold:
        return False, f"Quality score {lead_quality_score:.2f} below threshold {min_quality_threshold}"

    if domain_age_days < 365:
        return False, f"Domain age {domain_age_days} days < 365 day minimum"

    return True, "Lead qualifies for auto-outreach"


async def generate_outreach_email(
    lead_name: str,
    lead_company: str,
    lead_email: str,
    context: str = "",
) -> dict[str, Any]:
    """
    Generate personalized outreach email for qualified lead.
    Uses AI to create contextual, non-generic messaging.
    """
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import TaskType, Message

    prompt = f"""You are JARVIS, the operational AI for Aliyar Solutions.

Generate a brief, personalized cold email to {lead_name} at {lead_company}.

Context: {context or 'They operate a technology-enabled business'}

Email should:
1. Open with a specific observation about their business (not generic)
2. Present ONE concrete problem we solve (not feature dump)
3. Show social proof or relevant experience
4. Close with a specific next step (15-min call)
5. Be 3-4 sentences max
6. Sound like a real person, not a bot

Subject line MUST be under 50 chars, personal, not promotional.

Return format:
SUBJECT: [subject line]

BODY: [email body]"""

    try:
        response = await ai_router.execute(
            task_type=TaskType.OUTREACH,
            prompt=prompt,
            model_preference="claude",
            timeout_sec=10,
        )

        content = response.content if hasattr(response, 'content') else str(response)

        # Parse response
        lines = content.split('\n')
        subject = ""
        body = ""
        in_body = False

        for line in lines:
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                in_body = True
            elif in_body:
                body += line + "\n"

        return {
            "success": True,
            "subject": subject or f"Quick question about {lead_company}",
            "body": body.strip() or f"Hi {lead_name},\n\nWould love to chat about how we help companies like {lead_company} streamline operations.\n\nAvailable for a 15-min call this week?\n\nCheers",
            "lead_email": lead_email,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("Outreach email generation failed: %s", exc)
        # Fallback to template
        return {
            "success": False,
            "subject": f"Quick question about {lead_company}",
            "body": f"Hi {lead_name},\n\nWould love to chat about how we help companies streamline operations.\n\nAvailable for 15 minutes this week?\n\nCheers",
            "lead_email": lead_email,
            "error": str(exc),
            "is_fallback": True,
        }


async def send_outreach_email(
    lead_id: UUID,
    lead_name: str,
    lead_email: str,
    subject: str,
    body: str,
    tenant_id: UUID = None,
    db = None,
) -> dict[str, Any]:
    """
    Send outreach email via SES.
    Returns delivery status.
    """
    from app.core.config import settings
    from app.services.notifications import notify_business_event
    import httpx

    if not settings.SES_FROM_EMAIL:
        logger.warning("SES not configured — outreach email not sent")
        return {
            "success": False,
            "error": "SES not configured",
            "lead_id": str(lead_id),
        }

    try:
        # Send via SES
        from app.services.outreach.email_transport import send_outbound_email
        await send_outbound_email(
            to=lead_email,
            subject=subject,
            body=body,
            reply_to=settings.SES_REPLY_TO_EMAIL or settings.SES_FROM_EMAIL,
        )

        logger.info("Outreach email sent to %s (%s)", lead_name, lead_email)

        # Log outreach event
        if db:
            try:
                from sqlalchemy import text
                from app.core.database import set_tenant_context
                await set_tenant_context(db, str(tenant_id))
                await db.execute(
                    text("""
                        INSERT INTO outreach_log (lead_id, lead_email, subject, sent_at, status)
                        VALUES (:lead_id, :email, :subject, :sent_at, :status)
                    """),
                    {
                        "lead_id": str(lead_id),
                        "email": lead_email,
                        "subject": subject,
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                        "status": "sent",
                    },
                )
                await db.commit()
            except Exception as e:
                logger.debug("Outreach log insert failed: %s", e)

        return {
            "success": True,
            "lead_id": str(lead_id),
            "lead_email": lead_email,
            "subject": subject,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "delivered",
        }

    except Exception as exc:
        logger.error("Outreach email delivery failed for %s: %s", lead_email, exc)
        return {
            "success": False,
            "lead_id": str(lead_id),
            "lead_email": lead_email,
            "error": str(exc),
            "status": "failed",
        }


async def trigger_auto_outreach_for_lead(
    lead_id: UUID,
    lead_data: dict[str, Any],
    db = None,
) -> dict[str, Any]:
    """
    Main trigger: when lead qualifies, auto-generate and send outreach email.
    """
    from app.core.config import settings

    lead_name = lead_data.get("name", "Prospect")
    lead_email = lead_data.get("email", "")
    lead_company = lead_data.get("company", "")
    lead_quality = lead_data.get("quality_score", 0.75)
    lead_status = lead_data.get("status", "qualified")
    domain_age = lead_data.get("domain_age_days", 400)
    context = lead_data.get("context", "")

    if not lead_email:
        return {
            "success": False,
            "reason": "No email address for lead",
            "lead_id": str(lead_id),
        }

    # Check eligibility
    should_send, reason = await should_send_outreach(
        lead_quality_score=lead_quality,
        lead_status=lead_status,
        domain_age_days=domain_age,
        min_quality_threshold=settings.AUTO_SEND_OUTREACH_MIN_QUALITY_SCORE,
    )

    if not should_send:
        logger.info("Outreach not sent to %s: %s", lead_email, reason)
        return {
            "success": False,
            "reason": reason,
            "lead_id": str(lead_id),
        }

    if not settings.AUTO_SEND_OUTREACH or settings.OUTREACH_PAUSED:
        logger.info("Auto-outreach disabled or paused, skipping %s", lead_email)
        return {
            "success": False,
            "reason": "Auto-outreach disabled or paused globally",
            "lead_id": str(lead_id),
        }

    # Generate email
    email_data = await generate_outreach_email(
        lead_name=lead_name,
        lead_company=lead_company,
        lead_email=lead_email,
        context=context,
    )

    if not email_data["success"] and not email_data.get("is_fallback"):
        logger.error("Email generation failed, not sending: %s", email_data.get("error"))
        return {
            "success": False,
            "reason": "Email generation failed",
            "lead_id": str(lead_id),
        }

    # Send email
    send_result = await send_outreach_email(
        lead_id=lead_id,
        lead_name=lead_name,
        lead_email=lead_email,
        subject=email_data["subject"],
        body=email_data["body"],
        tenant_id=lead_data.get("tenant_id"),
        db=db,
    )

    if send_result["success"]:
        logger.info("Auto-outreach sent to %s — lead %s", lead_email, lead_id)
        # Notify n8n + Telegram on successful outreach
        try:
            from app.services.notifications.n8n import on_outreach_sent
            from app.services.notifications.telegram import notify_telegram
            persona = email_data.get("persona", "team")
            await on_outreach_sent(
                lead_id=str(lead_id),
                company=lead_data.get("company_name", ""),
                email=lead_email,
                subject=email_data.get("subject", ""),
                persona=persona,
            )
            await notify_telegram(
                f"📧 *Outreach Sent*\n\n"
                f"Company: {lead_data.get('company_name', 'Unknown')}\n"
                f"Email: `{lead_email}`\n"
                f"Subject: {email_data.get('subject', '')[:60]}"
            )
        except Exception as exc:
            logger.warning("Post-outreach notification failed for lead %s (%s): %s", lead_id, lead_email, exc)

    return {
        "success": send_result["success"],
        "lead_id": str(lead_id),
        "lead_email": lead_email,
        "subject": email_data.get("subject", ""),
        "status": send_result.get("status", "failed"),
        "error": send_result.get("error"),
    }
