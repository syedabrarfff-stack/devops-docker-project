"""
JARVIS Telegram Bot — webhook-based command handler.
Register webhook: POST /api/v1/telegram/webhook/register
Receive updates: POST /api/v1/telegram/webhook  (registered with Telegram)

Commands:
  /start      — greet + menu
  /status     — system status
  /leads      — top 5 unscored leads
  /briefing   — morning briefing
  /approve ID — approve pending request
  /reject  ID — reject pending request
  /queue      — task queue stats
  /help       — command list
"""
import logging
import httpx
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}" if settings.TELEGRAM_BOT_TOKEN else ""

HELP_TEXT = """🤖 *JARVIS Command Menu*

/status — System health & AI providers
/leads — Top 5 leads awaiting scoring
/briefing — AI morning briefing
/approve <id> — Approve a pending request
/reject <id> — Reject a pending request
/queue — Task queue statistics
/help — This menu

You can also just *type anything* — JARVIS will respond with AI.
"""


async def _api(method: str, **kwargs) -> dict:
    if not BASE:
        return {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{BASE}/{method}", json=kwargs)
            return r.json()
    except Exception as e:
        logger.warning(f"Telegram API {method} failed: {e}")
        return {}


async def send_message(chat_id: str, text: str,
                       parse_mode: str = "Markdown",
                       reply_markup: Optional[dict] = None) -> bool:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    r = await _api("sendMessage", **payload)
    return r.get("ok", False)


async def handle_command(chat_id: str, cmd: str, args: list[str]) -> None:
    """Handle incoming Telegram command."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        if cmd == "start" or cmd == "help":
            await send_message(chat_id, HELP_TEXT)
        elif cmd == "status":
            await _handle_status(chat_id)
        elif cmd == "leads":
            await _handle_leads(chat_id, db)
        elif cmd == "briefing":
            await _handle_briefing(chat_id, db)
        elif cmd == "queue":
            await _handle_queue(chat_id, db)
        elif cmd == "approve" and args:
            try:
                aid = int(args[0])
                await _handle_approval_callback(chat_id, aid, "approve", db)
            except (ValueError, IndexError):
                await send_message(chat_id, "Usage: /approve <id>")
        elif cmd == "reject" and args:
            try:
                aid = int(args[0])
                await _handle_approval_callback(chat_id, aid, "reject", db)
            except (ValueError, IndexError):
                await send_message(chat_id, "Usage: /reject <id>")
        else:
            await send_message(chat_id, "Unknown command. Try /help")


async def handle_text_message(chat_id: str, text: str) -> None:
    """Handle incoming free-form text message."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await _handle_chat(chat_id, text, db)


async def answer_callback(callback_id: str, text: str = "") -> None:
    await _api("answerCallbackQuery", callback_query_id=callback_id, text=text)


async def set_webhook(url: str) -> dict:
    return await _api("setWebhook", url=url,
                      allowed_updates=["message", "callback_query"])


async def delete_webhook() -> dict:
    return await _api("deleteWebhook")


async def get_webhook_info() -> dict:
    return await _api("getWebhookInfo")


def _approval_keyboard(approval_id: int) -> dict:
    return {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve:{approval_id}"},
            {"text": "❌ Reject",  "callback_data": f"reject:{approval_id}"},
        ]]
    }


async def handle_update(update: dict, db) -> None:
    """Route incoming Telegram update to the right handler."""
    chat_id = str(settings.TELEGRAM_CHAT_ID or "")

    # Callback query (inline button press)
    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data", "")
        cq_chat = str(cq["message"]["chat"]["id"])
        await answer_callback(cq["id"])
        if data.startswith("approve:") or data.startswith("reject:"):
            action, aid = data.split(":", 1)
            await _handle_approval_callback(cq_chat, int(aid), action, db)
        return

    # Text message
    msg = update.get("message", {})
    text = msg.get("text", "").strip()
    sender_chat = str(msg.get("chat", {}).get("id", ""))
    if not text or not sender_chat:
        return

    cmd = text.split()[0].lower().lstrip("/")

    if cmd == "start" or cmd == "help":
        await send_message(sender_chat, HELP_TEXT)
    elif cmd == "status":
        await _handle_status(sender_chat)
    elif cmd == "leads":
        await _handle_leads(sender_chat, db)
    elif cmd == "briefing":
        await _handle_briefing(sender_chat, db)
    elif cmd == "approve" and len(text.split()) > 1:
        try:
            aid = int(text.split()[1])
            await _handle_approval_callback(sender_chat, aid, "approve", db)
        except ValueError:
            await send_message(sender_chat, "Usage: /approve <id>")
    elif cmd == "reject" and len(text.split()) > 1:
        try:
            aid = int(text.split()[1])
            await _handle_approval_callback(sender_chat, aid, "reject", db)
        except ValueError:
            await send_message(sender_chat, "Usage: /reject <id>")
    elif cmd == "queue":
        await _handle_queue(sender_chat, db)
    else:
        # Free-form JARVIS chat
        await _handle_chat(sender_chat, text, db)


# ── Command handlers ──────────────────────────────────────────────────────────

async def _handle_status(chat_id: str) -> None:
    from app.services.ai.router import ai_router
    providers = ai_router.get_provider_status()
    available = [k for k, v in providers.items() if v["available"]]
    lines = [f"⚡ *JARVIS System Status*\n",
             f"AI Providers: {len(available)}/{len(providers)} online",
             f"Active: {', '.join(available[:5]) or 'demo mode'}"]
    await send_message(chat_id, "\n".join(lines))


async def _handle_leads(chat_id: str, db) -> None:
    from app.services.leads.engine import list_leads
    leads = await list_leads(db, min_score=0, limit=5)
    if not leads:
        await send_message(chat_id, "📋 No leads yet. Add leads from the dashboard.")
        return
    lines = ["📊 *Top Leads*\n"]
    for l in leads:
        lines.append(f"• *{l.company}* — {l.industry or '?'} ({l.country or '?'})\n"
                     f"  Score: {l.score} | Tier: {l.tier} | {l.status}")
    await send_message(chat_id, "\n".join(lines))


async def _handle_briefing(chat_id: str, db) -> None:
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import Message, TaskType
    from datetime import datetime
    now = datetime.now()
    prompt = (f"Give JARVIS morning briefing for Aliyar Solutions. "
              f"Today is {now.strftime('%A, %B %d %Y')}. "
              f"Be concise — max 200 words. Focus on priorities.")
    try:
        resp, _ = await ai_router.chat(
            [Message(role="user", content=prompt)],
            task_type=TaskType.FAST,
        )
        await send_message(chat_id, f"☀️ *Morning Briefing*\n\n{resp.content[:3000]}")
    except Exception as e:
        await send_message(chat_id, f"Briefing unavailable: {e}")


async def _handle_queue(chat_id: str, db) -> None:
    from app.services.tasks.queue import get_queue_stats
    stats = await get_queue_stats(db)
    lines = [
        "📋 *Task Queue Stats*\n",
        f"Queued:    {stats.get('queued', 0)}",
        f"Running:   {stats.get('running', 0)}",
        f"Completed: {stats.get('completed', 0)}",
        f"Failed:    {stats.get('failed', 0)}",
    ]
    await send_message(chat_id, "\n".join(lines))


async def _handle_approval_callback(chat_id: str, approval_id: int,
                                     action: str, db) -> None:
    from sqlalchemy import select
    from app.models.approval import ApprovalRequest
    from datetime import datetime
    row = (await db.execute(select(ApprovalRequest).where(ApprovalRequest.id == approval_id))).scalar_one_or_none()
    if not row:
        await send_message(chat_id, f"❓ Approval #{approval_id} not found.")
        return
    if row.status != "pending":
        await send_message(chat_id, f"ℹ️ Already {row.status}.")
        return
    row.status = "approved" if action == "approve" else "rejected"
    row.approved_at = datetime.utcnow()
    row.captain_note = f"Via Telegram bot"
    await db.flush()
    icon = "✅" if action == "approve" else "❌"
    await send_message(chat_id, f"{icon} *{row.status.upper()}*: {row.title}")


async def _handle_chat(chat_id: str, text: str, db) -> None:
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import Message, TaskType
    try:
        resp, _ = await ai_router.chat(
            [Message(role="user", content=text)],
            task_type=TaskType.FAST,
            system_prompt="You are JARVIS, AI assistant for Aliyar Solutions. Be concise (max 200 words).",
        )
        await send_message(chat_id, resp.content[:4000])
    except Exception as e:
        await send_message(chat_id, f"Error: {e}")


# ── Notification helpers ──────────────────────────────────────────────────────

async def notify_approval_request(approval_id: int, title: str,
                                   summary: str, risk: str) -> None:
    """Send approval request with inline keyboard to Captain."""
    chat_id = str(settings.TELEGRAM_CHAT_ID or "")
    if not chat_id:
        return
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(risk, "⚪")
    text = (f"🔔 *Approval Required* #{approval_id}\n\n"
            f"{risk_emoji} Risk: *{risk.upper()}*\n"
            f"*{title}*\n\n{summary[:300]}")
    await send_message(chat_id, text, reply_markup=_approval_keyboard(approval_id))
