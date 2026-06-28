"""
Slack notification service — Block Kit rich messages.
"""
import time
import httpx
from app.core.config import settings

_ICON = "https://i.imgur.com/zL6sOmv.png"


def _divider() -> dict:
    return {"type": "divider"}


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _fields(*pairs) -> dict:
    return {
        "type": "section",
        "fields": [{"type": "mrkdwn", "text": f"*{k}*\n{v}"} for k, v in pairs],
    }


def _context(text: str) -> dict:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}


def _header(text: str) -> dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text, "emoji": True}}


async def _post(blocks: list, text: str = "JARVIS notification") -> bool:
    if not settings.SLACK_WEBHOOK_URL:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(settings.SLACK_WEBHOOK_URL, json={
                "text": text, "blocks": blocks,
                "icon_url": _ICON, "username": "JARVIS",
            })
        return r.status_code == 200
    except Exception:
        return False


async def notify_slack(message: str, color: str = "#00d4ff") -> bool:
    """Simple text notification (backwards-compatible)."""
    return await _post([_section(message)], text=message)


async def notify_lead_qualified(company: str, industry: str, country: str,
                                  score: int, tier: str, service: str, angle: str) -> bool:
    tier_emoji = {"A": "🔥", "B": "⭐", "C": "📋", "D": "📌"}.get(tier, "•")
    return await _post([
        _header(f"{tier_emoji} {tier}-Tier Lead: {company}"),
        _fields(
            ("Industry", industry or "Unknown"), ("Country", country or "Unknown"),
            ("Score", f"{score}/100"),           ("Tier", tier),
            ("Service", service or "AI automation"), ("Pitch Angle", angle or "—"),
        ),
        _context(f"JARVIS Lead Engine · {_ts()}"),
    ], text=f"{tier_emoji} New {tier}-Tier Lead: {company} ({score}/100)")


async def notify_approval_needed(approval_id: int, title: str, summary: str,
                                   risk: str, requested_by: str = "JARVIS") -> bool:
    risk_icons = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
    return await _post([
        _header("🔔 JARVIS Approval Required"),
        _section(f"*{title}*"),
        _section(summary[:300]),
        _fields(
            ("Risk Level", f"{risk_icons.get(risk, '⚪')} {risk.upper()}"),
            ("Approval #", str(approval_id)),
            ("Requested By", requested_by),
        ),
        _context(f"Open JARVIS dashboard to approve · {_ts()}"),
    ], text=f"Approval needed: {title}")


async def notify_outreach_sent(to_email: str, subject: str, company: str) -> bool:
    return await _post([
        _section(f"✅ *Outreach sent* to *{company}*"),
        _fields(("To", to_email), ("Subject", subject)),
        _context(f"JARVIS Outreach · {_ts()}"),
    ], text=f"Email sent to {company}")


async def notify_task_completed(task_id: int, title: str, assigned_to: str,
                                  result_preview: str = "") -> bool:
    return await _post([
        _section(f"✅ *Task #{task_id} completed* — _{assigned_to}_"),
        _section(f"*{title}*"),
        _section(result_preview[:200]) if result_preview else _divider(),
        _context(f"JARVIS Task Queue · {_ts()}"),
    ], text=f"Task completed: {title}")


async def notify_system_event(title: str, body: str, level: str = "info") -> bool:
    icons = {"info": "ℹ️", "warning": "⚠️", "error": "🔴", "success": "✅"}
    return await _post([
        _section(f"{icons.get(level, 'ℹ️')} *{title}*"),
        _section(body),
        _context(f"JARVIS System · {_ts()}"),
    ], text=title)


async def notify_business_event(event_type: str, title: str, summary: str) -> bool:
    icons = {
        “proposal_accepted”: “🎯”,
        “meeting_booked”: “📅”,
        “payment_received”: “✅”,
        “system_critical_error”: “🔴”,
    }
    return await _post([
        _header(f”{icons.get(event_type, '📢')} {title}”),
        _section(summary[:500]),
        _fields((“Event”, event_type), (“Source”, “JARVIS”)),
        _context(f”Aliyar Solutions Operations · {_ts()}”),
    ], text=title)


def _ts() -> str:
    import datetime
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
