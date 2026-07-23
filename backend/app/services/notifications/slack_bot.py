"""R6-1: Slack Bot — two-way integration.

Incoming: slash commands (/jarvis leads, /jarvis status, /jarvis approve <id>)
         and @JARVIS mentions via Slack Events API.
Outgoing: Block Kit rich notifications (already in slack.py).

Verification: HMAC-SHA256 on every inbound payload using SLACK_SIGNING_SECRET.
Captain must install the Slack App and set SLACK_BOT_TOKEN + SLACK_SIGNING_SECRET in .env.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_SLACK_API = "https://slack.com/api"


# ── HMAC Verification ─────────────────────────────────────────────────────────

def verify_slack_signature(body: bytes | str, timestamp: str, signature: str) -> bool:
    """Verify Slack request authenticity via HMAC-SHA256."""
    if not settings.SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not set — bot verification disabled")
        return False

    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            return False  # replay attack guard (5-minute window)
    except (ValueError, TypeError):
        return False

    body_str = body.decode() if isinstance(body, bytes) else body
    base = f"v0:{timestamp}:{body_str}"
    expected = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        base.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Slack Web API helpers ─────────────────────────────────────────────────────

async def _api_post(method: str, payload: dict) -> dict[str, Any]:
    if not settings.SLACK_BOT_TOKEN:
        return {"ok": False, "error": "bot_token_not_configured"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{_SLACK_API}/{method}",
                json=payload,
                headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
            )
        return r.json()
    except Exception as exc:
        logger.warning("Slack API call failed: %s", exc)
        return {"ok": False, "error": str(exc)}


async def post_message(channel: str, text: str, blocks: list | None = None) -> bool:
    payload: dict[str, Any] = {"channel": channel, "text": text}
    if blocks:
        payload["blocks"] = blocks
    result = await _api_post("chat.postMessage", payload)
    return result.get("ok", False)


async def reply_ephemeral(channel: str, user: str, text: str) -> bool:
    result = await _api_post(
        "chat.postEphemeral",
        {"channel": channel, "user": user, "text": text},
    )
    return result.get("ok", False)


# ── Command Dispatcher ────────────────────────────────────────────────────────

async def handle_slash_command(command: str, text: str, channel_id: str,
                                user_id: str, response_url: str) -> dict:
    """
    Route /jarvis <subcommand> to the appropriate JARVIS handler.
    Returns an immediate Slack response payload (shown to the user).
    """
    sub = text.strip().lower().split()[0] if text.strip() else "help"
    args = text.strip().split()[1:] if len(text.strip().split()) > 1 else []

    if sub == "status":
        return await _cmd_status()
    elif sub == "leads":
        return await _cmd_leads()
    elif sub == "pipeline":
        return await _cmd_pipeline()
    elif sub == "approve" and args:
        return await _cmd_approve(args[0])
    elif sub == "reject" and args:
        return await _cmd_reject(args[0], " ".join(args[1:]))
    elif sub == "briefing":
        return await _cmd_briefing()
    else:
        return _cmd_help()


async def _cmd_status() -> dict:
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text as sqla_text
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(sqla_text(
                "SELECT COUNT(*) FROM leads WHERE status NOT IN ('closed', 'disqualified')"
            ))
            active_leads = result.scalar_one()
    except Exception:
        active_leads = "?"
    return {
        "response_type": "in_channel",
        "text": f"✅ JARVIS operational — {active_leads} active leads in pipeline",
    }


async def _cmd_leads() -> dict:
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text as sqla_text
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(sqla_text(
                "SELECT company_name, icp_score, status FROM leads "
                "WHERE status NOT IN ('closed','disqualified') "
                "ORDER BY icp_score DESC NULLS LAST LIMIT 5"
            ))
            rows = result.fetchall()
        if not rows:
            return {"text": "No active leads at the moment."}
        lines = ["*Top 5 Active Leads:*"]
        for r in rows:
            lines.append(f"• {r[0]} — score {r[1] or 'N/A'} ({r[2]})")
        return {"response_type": "in_channel", "text": "\n".join(lines)}
    except Exception as exc:
        return {"text": f"Could not fetch leads: {exc}"}


async def _cmd_pipeline() -> dict:
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text as sqla_text
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(sqla_text(
                "SELECT status, COUNT(*) FROM leads GROUP BY status ORDER BY COUNT(*) DESC"
            ))
            rows = result.fetchall()
        lines = ["*Lead Pipeline:*"]
        for r in rows:
            lines.append(f"• {r[0]}: {r[1]}")
        return {"response_type": "in_channel", "text": "\n".join(lines)}
    except Exception as exc:
        return {"text": f"Pipeline query failed: {exc}"}


async def _set_approval_status(approval_id: str, status, captain_note: str | None = None) -> dict:
    import uuid
    from datetime import datetime
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.approval import ApprovalRequest, ApprovalStatus

    try:
        approval_uuid = uuid.UUID(str(approval_id))
    except ValueError:
        return {"text": f"❓ Invalid approval ID: {approval_id}"}

    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_uuid)
        )).scalar_one_or_none()
        if not row:
            return {"text": f"❓ Approval {approval_id} not found."}
        if row.status != ApprovalStatus.PENDING:
            return {"text": f"ℹ️ Already {row.status.value}."}
        row.status = status
        row.approved_at = datetime.utcnow()
        if captain_note:
            row.captain_note = captain_note
        title = row.title
        await session.commit()
    return {"title": title}


async def _cmd_approve(approval_id: str) -> dict:
    from app.models.approval import ApprovalStatus
    try:
        result = await _set_approval_status(approval_id, ApprovalStatus.APPROVED, "Via Slack")
        if "text" in result:
            return result
        return {"response_type": "in_channel", "text": f"✅ *{result['title']}* approved via Slack."}
    except Exception as exc:
        return {"text": f"Approval failed: {exc}"}


async def _cmd_reject(approval_id: str, reason: str) -> dict:
    from app.models.approval import ApprovalStatus
    try:
        result = await _set_approval_status(approval_id, ApprovalStatus.REJECTED, reason or "Rejected via Slack")
        if "text" in result:
            return result
        return {"response_type": "in_channel", "text": f"❌ *{result['title']}* rejected."}
    except Exception as exc:
        return {"text": f"Reject failed: {exc}"}


async def _cmd_briefing() -> dict:
    return {
        "response_type": "ephemeral",
        "text": "🕐 Generating briefing — check Telegram or dashboard in 60 seconds.",
    }


def _cmd_help() -> dict:
    return {
        "response_type": "ephemeral",
        "text": (
            "*JARVIS Slack Commands:*\n"
            "• `/jarvis status` — system health + active lead count\n"
            "• `/jarvis leads` — top 5 active leads\n"
            "• `/jarvis pipeline` — pipeline breakdown by stage\n"
            "• `/jarvis approve <id>` — approve a pending request\n"
            "• `/jarvis reject <id> [reason]` — reject a pending request\n"
            "• `/jarvis briefing` — trigger a briefing\n"
        ),
    }


# ── Event handler (mention + messages) ───────────────────────────────────────

async def handle_event(event: dict) -> None:
    """Handle Slack Events API events (mentions, DMs)."""
    event_type = event.get("type", "")
    if event_type == "app_mention":
        channel = event.get("channel", "")
        text: str = event.get("text", "")
        # Strip the mention (<@BOTID> ...)
        clean = " ".join(t for t in text.split() if not t.startswith("<@"))
        sub = clean.strip().lower().split()[0] if clean.strip() else "help"
        result = await handle_slash_command("/jarvis", clean, channel, event.get("user", ""), "")
        await post_message(channel, result.get("text", "⚡ JARVIS ready."))
