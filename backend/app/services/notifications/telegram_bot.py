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

*Pipeline & Leads*
/leads — Top 5 leads by score
/pipeline — Full pipeline breakdown by stage
/scout — Trigger lead discovery now

*AUTOPILOT Drafts*
/drafts — List pending email drafts
/draft <id> — View a specific draft
/approve\\_draft <id> — Approve & send
/reject\\_draft <id> — Reject a draft
/approve\\_all — Approve ALL pending drafts

*Governance*
/approve <id> — Approve a governance request
/reject <id> — Reject a governance request

*System*
/status — Full system health report
/heal — Run self-healing cycle
/nexus — NEXUS heartbeat pulse
/revenue — Quick revenue snapshot
/queue — Task queue stats
/briefing — AI morning briefing
/help — This menu

Type anything to chat with JARVIS.
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
        if cmd in ("start", "help"):
            await send_message(chat_id, HELP_TEXT)
        elif cmd == "status":
            await _handle_status(chat_id)
        elif cmd == "nexus":
            await _handle_nexus_pulse(chat_id, db)
        elif cmd == "leads":
            await _handle_leads(chat_id, db)
        elif cmd == "briefing":
            await _handle_briefing(chat_id, db)
        elif cmd == "heal":
            await _handle_self_heal(chat_id)
        elif cmd == "queue":
            await _handle_queue(chat_id, db)
        elif cmd == "drafts":
            await _handle_list_drafts(chat_id)
        elif cmd == "draft" and args:
            await _handle_view_draft(chat_id, args[0])
        elif cmd == "approve_draft" and args:
            await _handle_autopilot_draft_action(chat_id, args[0], "approve")
        elif cmd == "reject_draft" and args:
            await _handle_autopilot_draft_action(chat_id, args[0], "reject")
        elif cmd == "approve_all":
            await _handle_approve_all(chat_id)
        elif cmd == "revenue":
            await _handle_revenue(chat_id, db)
        elif cmd == "pipeline":
            await _handle_pipeline(chat_id, db)
        elif cmd == "scout":
            await _handle_scout(chat_id)
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
    # Callback query (inline button press)
    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data", "")
        cq_chat = str(cq["message"]["chat"]["id"])
        await answer_callback(cq["id"])
        if data == "approve_all_drafts:confirm":
            await _handle_approve_all_confirmed(cq_chat)
        elif data.startswith("approve_draft:") or data.startswith("reject_draft:"):
            action, draft_id = data.split(":", 1)
            act = "approve" if action == "approve_draft" else "reject"
            await _handle_autopilot_draft_action(cq_chat, draft_id, act)
        elif data.startswith("approve:") or data.startswith("reject:"):
            action, aid = data.split(":", 1)
            await _handle_approval_callback(cq_chat, int(aid), action, db)
        return

    # Text message
    msg = update.get("message", {})
    text = msg.get("text", "").strip()
    sender_chat = str(msg.get("chat", {}).get("id", ""))
    if not text or not sender_chat:
        return

    parts = text.split()
    cmd = parts[0].lower().lstrip("/")
    args = parts[1:]

    if cmd in ("start", "help"):
        await send_message(sender_chat, HELP_TEXT)
    elif cmd == "status":
        await _handle_status(sender_chat)
    elif cmd == "nexus":
        await _handle_nexus_pulse(sender_chat, db)
    elif cmd == "leads":
        await _handle_leads(sender_chat, db)
    elif cmd == "briefing":
        await _handle_briefing(sender_chat, db)
    elif cmd == "heal":
        await _handle_self_heal(sender_chat)
    elif cmd == "queue":
        await _handle_queue(sender_chat, db)
    elif cmd == "drafts":
        await _handle_list_drafts(sender_chat)
    elif cmd == "draft" and args:
        await _handle_view_draft(sender_chat, args[0])
    elif cmd == "approve_draft" and args:
        await _handle_autopilot_draft_action(sender_chat, args[0], "approve")
    elif cmd == "reject_draft" and args:
        await _handle_autopilot_draft_action(sender_chat, args[0], "reject")
    elif cmd == "approve_all":
        await _handle_approve_all(sender_chat)
    elif cmd == "revenue":
        await _handle_revenue(sender_chat, db)
    elif cmd == "pipeline":
        await _handle_pipeline(sender_chat, db)
    elif cmd == "scout":
        await _handle_scout(sender_chat)
    elif cmd == "approve" and args:
        try:
            await _handle_approval_callback(sender_chat, int(args[0]), "approve", db)
        except ValueError:
            await send_message(sender_chat, "Usage: /approve <id>")
    elif cmd == "reject" and args:
        try:
            await _handle_approval_callback(sender_chat, int(args[0]), "reject", db)
        except ValueError:
            await send_message(sender_chat, "Usage: /reject <id>")
    else:
        await _handle_chat(sender_chat, text, db)


# ── Command handlers ──────────────────────────────────────────────────────────

async def _handle_status(chat_id: str) -> None:
    import time
    from app.services.ai.router import ai_router
    from app.services.scheduler.scheduler import get_scheduler, get_jobs

    lines = ["⚡ *JARVIS System Status*\n"]

    # AI Providers
    providers = ai_router.get_provider_status()
    available = [k for k, v in providers.items() if v["available"]]
    lines.append(f"🤖 AI: {len(available)}/{len(providers)} providers online")
    if available:
        lines.append(f"   Active: {', '.join(available[:5])}")

    # Scheduler
    try:
        sched = get_scheduler()
        running = sched is not None and sched.running
        job_count = len(get_jobs()) if running else 0
        lines.append(f"⏰ Scheduler: {'running' if running else '⚠️ STOPPED'} ({job_count} jobs)")
    except Exception:
        lines.append("⏰ Scheduler: unknown")

    # Redis
    try:
        import asyncio
        import redis.asyncio as aioredis
        from app.core.config import settings as _s
        if _s.REDIS_URL:
            t0 = time.monotonic()
            _c = aioredis.from_url(_s.REDIS_URL, socket_connect_timeout=2)
            await asyncio.wait_for(_c.ping(), timeout=2.0)
            await _c.aclose()
            latency = int((time.monotonic() - t0) * 1000)
            lines.append(f"🔴 Redis: online ({latency}ms)")
        else:
            lines.append("🔴 Redis: not configured")
    except Exception:
        lines.append("🔴 Redis: ⚠️ unreachable")

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
        briefing = resp.content if not resp.error else f"Briefing AI unavailable — {resp.error}"
        await send_message(chat_id, f"☀️ *Morning Briefing*\n\n{(briefing or 'No content returned.')[:3000]}")
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


async def _handle_self_heal(chat_id: str) -> None:
    await send_message(chat_id, "🔧 Running self-healing cycle… please wait.")
    try:
        from app.services.monitoring.self_healer import run_self_healing_cycle
        report = await run_self_healing_cycle()
        lines = [f"🔧 *Self-Heal Complete* ({report.get('duration_ms', '?')}ms)\n"]
        actions = report.get("actions", [])
        alerts = report.get("alerts", [])
        if actions:
            lines.append("*Auto-recovered:*")
            lines.extend(f"  ✅ {a}" for a in actions)
        else:
            lines.append("✅ All systems healthy — nothing to recover.")
        if alerts:
            lines.append("\n*Requires attention:*")
            lines.extend(f"  ⚠️ {a}" for a in alerts)
        await send_message(chat_id, "\n".join(lines))
    except Exception as e:
        await send_message(chat_id, f"❌ Self-heal failed: {e}")


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
        reply = resp.content if not resp.error else f"JARVIS momentarily unavailable — {resp.error}"
        await send_message(chat_id, (reply or "JARVIS unavailable.")[:4000])
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


async def notify_autopilot_drafts_pending(drafts: list[dict]) -> None:
    """Notify Captain of pending AUTOPILOT drafts — called by NEXUS heartbeat."""
    chat_id = str(settings.TELEGRAM_CHAT_ID or "")
    if not chat_id or not drafts:
        return
    count = len(drafts)
    lines = [f"✉️ *AUTOPILOT — {count} Draft{'s' if count > 1 else ''} Pending Approval*\n"]
    for d in drafts[:5]:
        short_id = d["id"][:8]
        lead_name = d.get("lead_contact") or d.get("lead_email", "?")
        company = d.get("lead_company", "")
        subject = d.get("subject", "(no subject)")
        lines.append(f"• `{short_id}` — *{lead_name}*{(' @ ' + company) if company else ''}\n"
                     f"  _{subject[:60]}_")
    if count > 5:
        lines.append(f"\n_...and {count - 5} more. Use /drafts to see all._")
    lines.append("\nUse `/approve_draft <id>` or `/reject_draft <id>`")
    await send_message(chat_id, "\n".join(lines))


async def notify_autopilot_draft_ready(draft: dict) -> None:
    """Send a single new AUTOPILOT draft to Captain with inline approve/reject buttons."""
    chat_id = str(settings.TELEGRAM_CHAT_ID or "")
    if not chat_id:
        return
    draft_id = draft.get("id", "")
    short_id = draft_id[:8]
    lead_name = draft.get("lead_contact") or draft.get("lead_email", "?")
    company = draft.get("lead_company", "")
    subject = draft.get("subject", "(no subject)")
    body_preview = (draft.get("body") or "")[:200]
    text = (f"📧 *New AUTOPILOT Draft Ready* `{short_id}`\n\n"
            f"*To:* {lead_name}{(' @ ' + company) if company else ''}\n"
            f"*Subject:* {subject}\n\n"
            f"_{body_preview}_{'…' if len(draft.get('body', '')) > 200 else ''}")
    await send_message(chat_id, text, reply_markup=_draft_keyboard(draft_id))


# ── Internal helpers ──────────────────────────────────────────────────────────

def _draft_keyboard(draft_id: str) -> dict:
    return {
        "inline_keyboard": [[
            {"text": "✅ Approve & Send", "callback_data": f"approve_draft:{draft_id}"},
            {"text": "❌ Reject",         "callback_data": f"reject_draft:{draft_id}"},
        ]]
    }


async def _handle_nexus_pulse(chat_id: str, db) -> None:
    await send_message(chat_id, "⚡ Pulsing NEXUS… please wait.")
    try:
        from app.services.nexus.heartbeat import run_pulse
        from app.services.autopilot.pipeline import get_pending_drafts
        pulse = await run_pulse(db)
        pending = await get_pending_drafts(None)
        pipeline = pulse.get("pipeline", {})
        lines = [
            "🧠 *NEXUS Heartbeat*\n",
            f"📊 Leads: {pipeline.get('total_leads', 0)} total "
            f"| 🔥 {pipeline.get('hot_leads', 0)} hot "
            f"| ☀️ {pipeline.get('warm_leads', 0)} warm",
            f"✉️ Pending drafts: {len(pending)}",
            f"📡 Signal: *{pulse.get('action_signal', 'MONITOR')}*",
            f"🤖 AI: {'✅' if pulse.get('ai_available') else '❌'}",
            f"🔴 Redis: {'✅' if pulse.get('redis_ok') else '⚠️ fallback'}",
        ]
        await send_message(chat_id, "\n".join(lines))
    except Exception as e:
        await send_message(chat_id, f"❌ NEXUS pulse failed: {e}")


async def _handle_list_drafts(chat_id: str) -> None:
    try:
        from app.services.autopilot.pipeline import get_pending_drafts
        drafts = await get_pending_drafts(None)
        if not drafts:
            await send_message(chat_id, "✅ No pending drafts. Inbox is clear.")
            return
        lines = [f"📋 *Pending Drafts ({len(drafts)})*\n"]
        for d in drafts[:10]:
            short_id = d["id"][:8]
            lead_name = d.get("lead_contact") or d.get("lead_email", "?")
            company = d.get("lead_company", "")
            subject = d.get("subject", "(no subject)")
            lines.append(f"`{short_id}` — *{lead_name}*{(' @ ' + company) if company else ''}\n"
                         f"  _{subject[:55]}_")
        if len(drafts) > 10:
            lines.append(f"\n_{len(drafts) - 10} more not shown_")
        lines.append("\n/approve\\_draft `<id>` or /reject\\_draft `<id>`")
        await send_message(chat_id, "\n".join(lines))
    except Exception as e:
        await send_message(chat_id, f"❌ Could not load drafts: {e}")


async def _handle_view_draft(chat_id: str, short_id: str) -> None:
    try:
        from app.services.autopilot.pipeline import get_pending_drafts
        drafts = await get_pending_drafts(None)
        match = next((d for d in drafts if d["id"].startswith(short_id)), None)
        if not match:
            await send_message(chat_id, f"❓ No pending draft starting with `{short_id}`.")
            return
        draft_id = match["id"]
        lead_name = match.get("lead_contact") or match.get("lead_email", "?")
        company = match.get("lead_company", "")
        subject = match.get("subject", "(no subject)")
        body = (match.get("body") or "")[:500]
        text = (f"📧 *Draft* `{draft_id[:8]}`\n\n"
                f"*To:* {lead_name}{(' @ ' + company) if company else ''}\n"
                f"*Subject:* {subject}\n\n{body}"
                f"{'…' if len(match.get('body', '')) > 500 else ''}")
        await send_message(chat_id, text, reply_markup=_draft_keyboard(draft_id))
    except Exception as e:
        await send_message(chat_id, f"❌ Error: {e}")


async def _handle_autopilot_draft_action(chat_id: str, draft_ref: str, action: str) -> None:
    try:
        from app.services.autopilot.pipeline import get_pending_drafts, approve_draft, reject_draft
        drafts = await get_pending_drafts(None)
        match = next((d for d in drafts if d["id"] == draft_ref or d["id"].startswith(draft_ref)), None)
        if not match:
            await send_message(chat_id, f"❓ No pending draft found for `{draft_ref[:8]}`.")
            return
        draft_id = match["id"]
        lead_name = match.get("lead_contact") or match.get("lead_email", "?")
        if action == "approve":
            result = await approve_draft(None, draft_id)
            method = result.get("method", "email")
            await send_message(
                chat_id,
                f"✅ *Sent!* Email dispatched to *{lead_name}* via {method}.\n"
                f"Draft `{draft_id[:8]}` marked as sent."
            )
        else:
            await reject_draft(None, draft_id, reason="Rejected via Telegram")
            await send_message(
                chat_id,
                f"❌ *Rejected.* Draft `{draft_id[:8]}` for *{lead_name}* has been discarded."
            )
    except Exception as e:
        await send_message(chat_id, f"❌ Action failed: {e}")


# ── New command handlers (Phase 26) ──────────────────────────────────────────

async def _handle_approve_all(chat_id: str) -> None:
    """Show pending draft count with inline Confirm button before bulk-sending."""
    try:
        from app.services.autopilot.pipeline import get_pending_drafts
        drafts = await get_pending_drafts(None)
        if not drafts:
            await send_message(chat_id, "✅ No pending drafts to approve.")
            return
        count = len(drafts)
        text = (f"⚡ *Approve All Pending Drafts*\n\n"
                f"You are about to send *{count} email{'s' if count != 1 else ''}* to leads.\n"
                f"This action cannot be undone. Confirm?")
        keyboard = {"inline_keyboard": [[
            {"text": f"⚡ Yes, Send {count}", "callback_data": "approve_all_drafts:confirm"},
            {"text": "✗ Cancel", "callback_data": "noop"},
        ]]}
        await send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        await send_message(chat_id, f"❌ Error: {e}")


async def _handle_approve_all_confirmed(chat_id: str) -> None:
    """Execute bulk approval after Captain confirms via inline button."""
    await send_message(chat_id, "⚡ Sending all pending drafts…")
    try:
        from app.services.autopilot.pipeline import approve_all_pending
        result = await approve_all_pending(None)
        sent = result.get("sent", 0)
        failed = result.get("failed", 0)
        total = result.get("total", 0)
        lines = [f"📬 *Bulk Send Complete*\n"]
        lines.append(f"✅ Sent:   {sent}/{total}")
        if failed:
            lines.append(f"❌ Failed: {failed}")
        lines.append("\nAll drafts have been processed.")
        await send_message(chat_id, "\n".join(lines))
    except Exception as e:
        await send_message(chat_id, f"❌ Bulk approve failed: {e}")


async def _handle_revenue(chat_id: str, db) -> None:
    """Quick revenue snapshot from invoices table."""
    try:
        from sqlalchemy import select, func
        from app.models.revenue import Invoice, InvoiceStatus

        total_all = await db.scalar(
            select(func.coalesce(func.sum(Invoice.amount_usd), 0.0))
        ) or 0.0

        total_paid = await db.scalar(
            select(func.coalesce(func.sum(Invoice.paid_amount_usd), 0.0))
            .where(Invoice.status == InvoiceStatus.PAID)
        ) or 0.0

        total_outstanding = await db.scalar(
            select(func.coalesce(func.sum(Invoice.amount_usd), 0.0))
            .where(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.OVERDUE]))
        ) or 0.0

        invoice_count = await db.scalar(select(func.count()).select_from(Invoice)) or 0

        lines = [
            "💰 *Revenue Snapshot*\n",
            f"Total Invoiced:  ${float(total_all):,.0f}",
            f"Collected:       ${float(total_paid):,.0f}",
            f"Outstanding:     ${float(total_outstanding):,.0f}",
            f"Invoice Count:   {invoice_count}",
        ]
        await send_message(chat_id, "\n".join(lines))
    except Exception as e:
        await send_message(chat_id, f"❌ Revenue data unavailable: {e}")


async def _handle_pipeline(chat_id: str, db) -> None:
    """Lead pipeline breakdown by status and tier."""
    try:
        from sqlalchemy import select, func
        from app.models.lead import Lead, LeadStatus

        lines = ["📊 *Pipeline Breakdown*\n"]

        for status in LeadStatus:
            cnt = await db.scalar(
                select(func.count()).select_from(Lead).where(Lead.status == status)
            ) or 0
            if cnt:
                lines.append(f"  {status.value:<12} {cnt}")

        avg_q = await db.scalar(select(func.avg(Lead.score)).where(Lead.score > 0))
        avg_score = round(float(avg_q or 0), 1)

        top_q = (await db.execute(
            select(Lead.company, Lead.score)
            .where(Lead.score >= 75, Lead.status == LeadStatus.NEW)
            .order_by(Lead.score.desc())
            .limit(3)
        )).all()

        lines.append(f"\nAvg Score: {avg_score}")
        if top_q:
            lines.append("\n🔥 *Top Targets*")
            for company, score in top_q:
                lines.append(f"  • {company} ({int(score)})")

        await send_message(chat_id, "\n".join(lines))
    except Exception as e:
        await send_message(chat_id, f"❌ Pipeline data unavailable: {e}")


async def _handle_scout(chat_id: str) -> None:
    """Trigger lead discovery scan now."""
    await send_message(chat_id, "🔍 Triggering lead discovery… results in ~30s.")
    try:
        from app.core.config import settings
        if not settings.JARVIS_DEFAULT_TENANT_ID:
            await send_message(chat_id, "⚠️ JARVIS_DEFAULT_TENANT_ID not configured.")
            return
        from app.services.leads.discovery import lead_discovery_engine
        targets = [
            {"query": "business automation AI workflow", "industry": "SaaS", "limit": 15},
            {"query": "cloud infrastructure DevOps scaling", "industry": "Technology", "limit": 15},
        ]
        inserted = await lead_discovery_engine.run_daily_discovery(
            settings.JARVIS_DEFAULT_TENANT_ID, targets
        )
        await send_message(chat_id, f"✅ Scout complete — *{inserted} new leads* added to pipeline.")
    except Exception as e:
        await send_message(chat_id, f"❌ Scout failed: {e}")


# ── Captain Morning Dashboard Briefing ───────────────────────────────────────

async def notify_captain_morning_briefing(db) -> None:
    """
    Rich morning dashboard sent to Captain at 06:55.
    Real DB stats: pipeline, hot leads, pending drafts, scheduler, NEXUS signal.
    """
    chat_id = str(settings.TELEGRAM_CHAT_ID or "")
    if not chat_id:
        return

    from datetime import datetime, timezone
    from sqlalchemy import select, func
    from app.models.lead import Lead, LeadStatus

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %d %b %Y")

    lines = [f"☀️ *Good morning, Captain* — {date_str}\n"]

    # ── Pipeline stats ────────────────────────────────────────────────────────
    try:
        total = await db.scalar(select(func.count()).select_from(Lead)) or 0
        hot = await db.scalar(
            select(func.count()).select_from(Lead).where(Lead.score >= 75)
        ) or 0
        warm = await db.scalar(
            select(func.count()).select_from(Lead).where(Lead.score >= 45, Lead.score < 75)
        ) or 0
        new_leads = await db.scalar(
            select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.NEW)
        ) or 0
        contacted = await db.scalar(
            select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.CONTACTED)
        ) or 0
        eligible = await db.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.outreach_eligible.is_(True),
                Lead.status == LeadStatus.NEW,
                Lead.score >= 45,
            )
        ) or 0

        lines.append(
            f"📊 *Pipeline*\n"
            f"  Total: {total} | 🔥 Hot: {hot} | ☀️ Warm: {warm}\n"
            f"  New: {new_leads} | Contacted: {contacted} | Ready: {eligible}"
        )
    except Exception:
        lines.append("📊 Pipeline: data unavailable")

    # ── Top 3 HOT leads ───────────────────────────────────────────────────────
    try:
        hot_rows = (await db.execute(
            select(Lead)
            .where(Lead.score >= 75, Lead.status == LeadStatus.NEW)
            .order_by(Lead.score.desc())
            .limit(3)
        )).scalars().all()
        if hot_rows:
            lines.append("\n🔥 *Top Hot Leads*")
            for l in hot_rows:
                company = l.company_name or l.company or "?"
                industry = l.industry or "?"
                lines.append(f"  • *{company}* ({industry}) — score {int(l.score)}")
    except Exception:
        pass

    # ── Pending drafts ────────────────────────────────────────────────────────
    try:
        from app.services.autopilot.pipeline import get_pending_drafts
        pending = await get_pending_drafts(None)
        if pending:
            lines.append(f"\n✉️ *{len(pending)} draft{'s' if len(pending) != 1 else ''} awaiting approval* — /drafts to review")
        else:
            lines.append("\n✉️ No pending drafts")
    except Exception:
        pass

    # ── NEXUS last signal ─────────────────────────────────────────────────────
    try:
        from app.services.nexus.heartbeat import get_latest_pulse
        pulse = await get_latest_pulse()
        if pulse:
            signal = pulse.get("action_signal", "MONITOR")
            signal_emoji = {"OUTREACH_READY": "🚀", "DRAFTS_PENDING": "✉️", "MONITOR": "📡"}.get(signal, "📡")
            lines.append(f"\n{signal_emoji} *NEXUS Signal:* {signal}")
    except Exception:
        pass

    # ── Revenue snapshot ──────────────────────────────────────────────────────
    try:
        from sqlalchemy import select, func
        from app.models.revenue import Invoice, InvoiceStatus
        total_paid = await db.scalar(
            select(func.coalesce(func.sum(Invoice.paid_amount_usd), 0.0))
            .where(Invoice.status == InvoiceStatus.PAID)
        ) or 0.0
        outstanding = await db.scalar(
            select(func.coalesce(func.sum(Invoice.amount_usd), 0.0))
            .where(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.OVERDUE]))
        ) or 0.0
        if total_paid or outstanding:
            lines.append(
                f"\n💰 *Revenue*\n"
                f"  Collected: ${float(total_paid):,.0f} | Outstanding: ${float(outstanding):,.0f}"
            )
    except Exception:
        pass

    # ── Last NEXUS decision ───────────────────────────────────────────────────
    try:
        from app.services.nexus.heartbeat import get_decisions
        decisions = await get_decisions(1)
        if decisions:
            d = decisions[0]
            action = d.get("action") or d.get("primary_decision", {}).get("action", "")
            if action:
                lines.append(f"\n🧠 *Last NEXUS Action:* `{action}`")
    except Exception:
        pass

    # ── Scheduler health ──────────────────────────────────────────────────────
    try:
        from app.services.scheduler.engine import get_scheduler, get_jobs
        sched = get_scheduler()
        if sched and sched.running:
            job_count = len(get_jobs())
            lines.append(f"⏰ Scheduler: {job_count} jobs running")
        else:
            lines.append("⏰ Scheduler: ⚠️ STOPPED — /heal")
    except Exception:
        pass

    lines.append("\n_/help for all commands_")
    await send_message(chat_id, "\n".join(lines))


# ── Weekly Performance Briefing ───────────────────────────────────────────────

async def notify_weekly_performance_briefing(db) -> None:
    """
    Weekly Saturday 19:00 UTC briefing — full 7-day performance summary.
    Covers leads discovered, outreach sent, revenue moved, system health.
    """
    chat_id = str(settings.TELEGRAM_CHAT_ID or "")
    if not chat_id:
        return

    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, func
    from app.models.lead import Lead, LeadStatus

    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    lines = [f"📈 *Weekly Performance Report*\n_{now.strftime('%d %b %Y')}_\n"]

    # ── Lead velocity ─────────────────────────────────────────────────────────
    try:
        new_this_week = await db.scalar(
            select(func.count()).select_from(Lead).where(Lead.created_at >= week_start)
        ) or 0
        total = await db.scalar(select(func.count()).select_from(Lead)) or 0
        hot = await db.scalar(
            select(func.count()).select_from(Lead).where(Lead.score >= 75)
        ) or 0
        contacted_week = await db.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.outreach_sent.is_(True),
                Lead.updated_at >= week_start,
            )
        ) or 0
        lines.append(
            f"📊 *Leads*\n"
            f"  New this week: {new_this_week}\n"
            f"  Total pipeline: {total}\n"
            f"  Hot (≥75):  {hot}\n"
            f"  Contacted:  {contacted_week}"
        )
    except Exception:
        lines.append("📊 Lead stats unavailable")

    # ── Autopilot activity ────────────────────────────────────────────────────
    try:
        from app.services.autopilot.pipeline import get_autopilot_status
        status = await get_autopilot_status(None)
        all_time_sent = status.get("all_time_sent", 0)
        pending_now = status.get("pending", 0)
        lines.append(
            f"\n✉️ *AUTOPILOT*\n"
            f"  All-time sent: {all_time_sent}\n"
            f"  Pending review: {pending_now}"
        )
    except Exception:
        pass

    # ── Revenue snapshot ──────────────────────────────────────────────────────
    try:
        from app.models.revenue import Invoice, InvoiceStatus
        paid = await db.scalar(
            select(func.coalesce(func.sum(Invoice.paid_amount_usd), 0.0))
            .where(Invoice.status == InvoiceStatus.PAID)
        ) or 0.0
        outstanding = await db.scalar(
            select(func.coalesce(func.sum(Invoice.amount_usd), 0.0))
            .where(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.OVERDUE]))
        ) or 0.0
        lines.append(
            f"\n💰 *Revenue*\n"
            f"  Collected:    ${float(paid):,.0f}\n"
            f"  Outstanding:  ${float(outstanding):,.0f}"
        )
    except Exception:
        pass

    # ── System health summary ─────────────────────────────────────────────────
    try:
        from app.services.nexus.heartbeat import get_latest_pulse
        pulse = await get_latest_pulse()
        if pulse:
            signal = pulse.get("action_signal", "MONITOR")
            ai_ok = pulse.get("ai_available", False)
            redis_ok = pulse.get("redis_ok", False)
            lines.append(
                f"\n🔧 *System*\n"
                f"  NEXUS Signal: {signal}\n"
                f"  AI Provider:  {'✅' if ai_ok else '❌'}\n"
                f"  Redis:        {'✅' if redis_ok else '⚠️'}"
            )
    except Exception:
        pass

    lines.append("\n_Have a great weekend, Captain. 🚀_")
    await send_message(chat_id, "\n".join(lines))
