#!/usr/bin/env python3
"""
JARVIS AI Council — Telegram Bot  v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Features:
  • Live progress counter — edits the thinking message as each model responds
  • Business shortcuts: /proposal /email /price /close /morning
  • Session history, search, replay
  • Captain-only access control

Usage: python telegram_bot.py
Setup: Add TELEGRAM_BOT_TOKEN and TELEGRAM_CAPTAIN_ID to council/.env
"""

import asyncio
import os
import sys
import json
import time
from datetime import datetime

# Always resolve paths relative to THIS script file, not CWD
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(SCRIPT_DIR, "sessions")
ENV_FILE     = os.path.join(SCRIPT_DIR, ".env")

def install(pkg):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
except ImportError:
    install("python-dotenv"); from dotenv import load_dotenv; load_dotenv(ENV_FILE)

try:
    import httpx
except ImportError:
    install("httpx"); import httpx

try:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
    from telegram.constants import ParseMode
except ImportError:
    print("Installing python-telegram-bot...")
    install("python-telegram-bot>=20.0")
    from telegram import Update
    from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
    from telegram.constants import ParseMode


# ── Config ────────────────────────────────────────────────────────────────────

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
CAPTAIN_ID = os.getenv("TELEGRAM_CAPTAIN_ID", "")

if not BOT_TOKEN:
    print("\n❌  TELEGRAM_BOT_TOKEN not set in council/.env")
    print("   Get it from @BotFather on Telegram → /newbot")
    print("   Then add:  TELEGRAM_BOT_TOKEN=your-token-here\n")
    sys.exit(1)

if not CAPTAIN_ID:
    print("\n⚠️   TELEGRAM_CAPTAIN_ID not set — bot will respond to ALL users.")
    print("   Add your Telegram user ID to council/.env:")
    print("   TELEGRAM_CAPTAIN_ID=123456789")
    print("   (Send /myid to @userinfobot on Telegram to get your ID)\n")

CAPTAIN_ID_INT = int(CAPTAIN_ID) if CAPTAIN_ID and CAPTAIN_ID.isdigit() else None


# ── Import council engine ─────────────────────────────────────────────────────

sys.path.insert(0, SCRIPT_DIR)
import importlib.util
spec = importlib.util.spec_from_file_location("council", os.path.join(SCRIPT_DIR, "council.py"))
_council = importlib.util.load_module_from_spec(spec)
spec.loader.exec_module(_council)

COUNCIL                  = _council.COUNCIL
call_bedrock_synthesizer = _council.call_bedrock_synthesizer
query_member             = _council.query_member
run_council_progressive  = _council.run_council_progressive
_save_session            = _council._save_session


# ── Business command prompts ──────────────────────────────────────────────────

BUSINESS_PROMPTS = {
    "proposal": (
        "Create a professional proposal for Aliyar Solutions.\n\n"
        "Target / Context: {args}\n\n"
        "The council must produce:\n"
        "1. Executive summary (2 sentences)\n"
        "2. Proposed solution architecture (3-4 bullet points)\n"
        "3. Investment tiers — Starter $3k-5k / Growth $5k-10k / Enterprise $15k-25k\n"
        "4. Why Aliyar Solutions over alternatives (3 differentiators)\n"
        "5. Recommended next step\n\n"
        "Tone: Premium technology firm. Output ready to present to client.\n"
        "Context: Aliyar Solutions delivers AI automation, cloud infrastructure, "
        "DevOps, and digital operations globally. We never do hourly billing."
    ),
    "email": (
        "Write a cold outreach email from Aliyar Solutions.\n\n"
        "Target: {args}\n\n"
        "Requirements:\n"
        "- Subject line (compelling, not salesy)\n"
        "- Opening hook (reference their specific business pain)\n"
        "- Value proposition (2-3 sentences, concrete outcomes)\n"
        "- Social proof (mention enterprise AI systems, cloud infrastructure)\n"
        "- Single CTA (frictionless — a 15-min call)\n"
        "- Sign as: Darren Mitchell, Client Acquisition Specialist, Aliyar Solutions\n\n"
        "Length: Under 200 words. Tone: Confident professional, never desperate. "
        "Output: ready to copy and send."
    ),
    "price": (
        "Create a pricing recommendation for Aliyar Solutions.\n\n"
        "Service / Context: {args}\n\n"
        "Council must produce:\n"
        "1. Market rate analysis (what competitors charge for similar)\n"
        "2. Recommended tiers with exact prices: Starter / Growth / Enterprise\n"
        "3. What is included at each tier\n"
        "4. Negotiation floor (minimum we should accept)\n"
        "5. Upsell path (how to grow client from Starter to Enterprise)\n\n"
        "Context: Aliyar Solutions retainers: $2,000-$8,000/month. "
        "Projects: $3,000-$25,000. No hourly billing ever."
    ),
    "close": (
        "Sales closing strategy for Aliyar Solutions.\n\n"
        "Situation: {args}\n\n"
        "Council must produce:\n"
        "1. Root cause of hesitation (diagnose the real objection)\n"
        "2. Reframe strategy (how to reposition value)\n"
        "3. Exact closing message to send (ready to copy-paste)\n"
        "4. 3-touchpoint follow-up sequence if no response\n"
        "5. Walk-away threshold (when to stop pursuing this lead)\n\n"
        "Tone: Executive confidence. Never desperate. "
        "We are a premium technology firm — qualify ruthlessly."
    ),
    "morning": (
        "Generate the JARVIS Morning Briefing for Captain (CEO of Aliyar Solutions).\n\n"
        "## BUSINESS PULSE\n"
        "[Today's 2-3 key priorities — what should Captain focus on?]\n\n"
        "## MARKET SIGNAL\n"
        "[One technology or market trend relevant to AI automation, cloud, DevOps right now]\n\n"
        "## SALES INTELLIGENCE\n"
        "[Best industry sector to target today and exactly why]\n\n"
        "## OPERATIONS SPOTLIGHT\n"
        "[One process improvement or system optimization for this week]\n\n"
        "## CAPTAIN'S EDGE\n"
        "[One strategic insight or competitive advantage worth internalizing today]\n\n"
        "Sharp, specific, actionable. Building Aliyar Solutions toward $1M+ revenue. "
        "Executive briefing — not a tip sheet. 300 words maximum."
    ),
}


# ── Telegram helpers ──────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def verdict_to_telegram(verdict: str, active: int, total: int, task: str) -> str:
    """Convert the structured council verdict to Telegram MarkdownV2 format."""
    ellipsis  = "\\.\\.\\." if len(task) > 80 else ""
    task_line = f"_{_escape(task[:80])}{ellipsis}_"
    lines = [
        "🏛️ *COUNCIL VERDICT*",
        task_line,
        f"_{active}/{total} members active_\n",
    ]
    section_map = {
        "## VERDICT":            "🎯 *VERDICT*",
        "## KEY INSIGHTS":       "💡 *KEY INSIGHTS*",
        "## ACTION PLAN":        "📋 *ACTION PLAN*",
        "## RISKS & WATCH-OUTS": "⚠️ *RISKS*",
        "## COUNCIL CONSENSUS":  "🤝 *CONSENSUS*",
    }
    for line in verdict.splitlines():
        stripped = line.strip()
        matched  = False
        for md_header, tg_header in section_map.items():
            if stripped.startswith(md_header):
                lines.append(f"\n{tg_header}")
                matched = True
                break
        if not matched:
            if stripped.startswith("- ") or stripped.startswith("• "):
                lines.append(f"• {_escape(stripped[2:])}")
            elif stripped and stripped[0].isdigit() and len(stripped) > 2 and stripped[1] in ".)":
                lines.append(_escape(stripped))
            elif stripped:
                lines.append(_escape(stripped))
            else:
                lines.append("")

    lines.append(f"\n⏱️ _{_escape(datetime.now().strftime('%Y-%m-%d %H:%M'))}_")
    return "\n".join(lines)


async def _send_chunked(update: Update, text: str):
    """Send text that may exceed Telegram's 4096-char limit."""
    if len(text) <= 4000:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    chunks = text.split("\n\n")
    current = ""
    for chunk in chunks:
        if len(current) + len(chunk) + 2 > 3800:
            if current:
                await update.message.reply_text(current, parse_mode=ParseMode.MARKDOWN_V2)
            current = chunk
        else:
            current += ("\n\n" if current else "") + chunk
    if current:
        await update.message.reply_text(current, parse_mode=ParseMode.MARKDOWN_V2)


# ── Core council runner with live progress ────────────────────────────────────

async def _run_and_reply(update: Update, task: str, label: str = ""):
    """
    Fire the council, stream live progress by editing the thinking message,
    then deliver the final verdict. Saves the session file automatically.
    """
    members_total = len([m for m in COUNCIL if not m.get("synthesizer")])
    display_label = _escape(label or task[:70])

    thinking_msg = await update.message.reply_text(
        f"⚡ *Council assembling\\.\\.\\.*\n\n"
        f"_{display_label}_\n\n"
        f"`0 / {members_total} members responding`",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    progress_lines = []
    edit_state     = {"last_edit": 0.0}

    async def on_model_done(name: str, success: bool, done: int, total: int):
        icon = "✅" if success else "❌"
        progress_lines.append(f"{icon} {_escape(name[:30])}")
        now = time.monotonic()
        if now - edit_state["last_edit"] < 2.0 and done < total:
            return
        edit_state["last_edit"] = now
        preview = "\n".join(progress_lines[-5:])
        try:
            await thinking_msg.edit_text(
                f"⚡ *Council deliberating\\.\\.\\.*\n\n"
                f"_{display_label}_\n\n"
                f"`{done} / {total} members responded`\n\n"
                f"{preview}",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Exception:
            pass

    try:
        council_responses, verdict, active, total = await run_council_progressive(task, on_model_done)

        try:
            await thinking_msg.edit_text(
                f"🏛️ *Council complete \\({active}/{total}\\)\\. Synthesizing\\.\\.\\.* ",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Exception:
            pass

        _save_session(task, council_responses, verdict, prefix="telegram")
        reply = verdict_to_telegram(verdict, active, total, label or task)
        await _send_chunked(update, reply)
        await thinking_msg.delete()

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Council error: {_escape(str(e)[:250])}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        try:
            await thinking_msg.delete()
        except Exception:
            pass


# ── Auth helper ───────────────────────────────────────────────────────────────

def _is_captain(update: Update) -> bool:
    if CAPTAIN_ID_INT is None:
        return True
    return update.effective_user.id == CAPTAIN_ID_INT


# ── Session helpers ───────────────────────────────────────────────────────────

def _list_sessions() -> list[dict]:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    sessions = []
    for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        task_line = date_line = ""
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Task   :") or line.startswith("Task:"):
                        task_line = line.split(":", 1)[1].strip()
                    if line.startswith("Date   :") or line.startswith("Date:"):
                        date_line = line.split(":", 1)[1].strip()
                    if task_line and date_line:
                        break
        except Exception:
            pass
        source = "tg" if fname.startswith("telegram_") else ("api" if fname.startswith("api_") else "term")
        sessions.append({"file": fname, "path": path, "task": task_line, "date": date_line, "source": source})
    return sessions


def _read_verdict_from_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        start = content.find("COUNCIL VERDICT\n")
        if start == -1:
            start = content.find("VERDICT\n=")
        end = content.find("INDIVIDUAL MEMBER RESPONSES", start)
        if start == -1:
            return content[:2500]
        section = content[start: end if end != -1 else start + 3000]
        lines = section.splitlines()
        return "\n".join(lines[2:]).strip()[:2500]
    except Exception as e:
        return f"[Could not read session: {e}]"


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_captain(update):
        return
    await update.message.reply_text(
        "🏛️ *JARVIS AI Council — Online*\n\n"
        "Send any task → 14 models fire simultaneously → verdict delivered\\.\n\n"
        "*General commands:*\n"
        "/history — last 8 council sessions\n"
        "/last — re\\-read most recent verdict\n"
        "/find keyword — search past sessions\n"
        "/status — provider health check\n\n"
        "*Business shortcuts:*\n"
        "/proposal target — generate a client proposal\n"
        "/email target — write a cold outreach email\n"
        "/price service — pricing recommendation\n"
        "/close situation — sales closing strategy\n"
        "/morning — today's executive briefing\n\n"
        "*Example tasks:*\n"
        "• _What pricing should Aliyar use for enterprise clients?_\n"
        "• _How do I close the healthcare lead who went silent?_\n"
        "• _Design the architecture for a logistics AI system_",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_captain(update):
        return
    bedrock    = "✅" if _council.BEDROCK_API_KEY else "❌"
    anthropic  = "✅" if _council.ANTHROPIC_KEY else "❌"
    nv_count   = sum(1 for v in _council.NV_KEYS.values() if v and v.startswith("nvapi-"))
    google     = "✅" if _council.GOOGLE_KEY else "❌"
    openrouter = "✅" if _council.OPENROUTER_KEY else "❌"
    msg = (
        f"*JARVIS Council Status*\n\n"
        f"{bedrock} Bedrock API Key \\(primary synthesizer\\)\n"
        f"{anthropic} Anthropic \\(fallback\\)\n"
        f"{'✅' if nv_count else '❌'} NVIDIA NIM \\({nv_count}/10 slots\\)\n"
        f"{google} Google Gemini\n"
        f"{openrouter} OpenRouter\n\n"
        f"_Run /diagnose to test all keys live_"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_captain(update):
        return
    sessions = _list_sessions()[:8]
    if not sessions:
        await update.message.reply_text(
            "No council sessions yet\\. Send a task to get started\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    lines = ["📚 *Recent Council Sessions*\n"]
    for i, s in enumerate(sessions, 1):
        date   = _escape(s["date"][:16]) if s["date"] else "unknown"
        task   = _escape(s["task"][:52]) + ("\\.\\.\\." if len(s["task"]) > 52 else "")
        source = f" \\[{s['source']}\\]" if s["source"] != "term" else ""
        lines.append(f"`{i}.` {date}{source}\n    _{task}_")
    lines.append(f"\n_Use /last to read the latest verdict_")
    lines.append(f"_Use /find keyword to search_")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_captain(update):
        return
    sessions = _list_sessions()
    if not sessions:
        await update.message.reply_text("No sessions yet\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    s       = sessions[0]
    verdict = _read_verdict_from_file(s["path"])
    header  = (
        f"🔁 *Last Session*\n"
        f"_{_escape(s['date'][:16])}_\n"
        f"_{_escape(s['task'][:80])}_\n\n"
    )
    full = header + _escape(verdict)
    if len(full) <= 4000:
        await update.message.reply_text(full, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(header, parse_mode=ParseMode.MARKDOWN_V2)
        chunks = [verdict[i:i+3800] for i in range(0, len(verdict), 3800)]
        for chunk in chunks:
            await update.message.reply_text(_escape(chunk), parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_captain(update):
        return
    keyword = " ".join(context.args).strip().lower() if context.args else ""
    if not keyword:
        await update.message.reply_text("Usage: /find keyword", parse_mode=ParseMode.MARKDOWN_V2)
        return
    sessions = _list_sessions()
    matches  = [s for s in sessions if keyword in s["task"].lower()]
    if not matches:
        await update.message.reply_text(
            f"No sessions found matching _{_escape(keyword)}_",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    lines = [f"🔍 *Found {len(matches)} session\\(s\\) for* _{_escape(keyword)}_\n"]
    for i, s in enumerate(matches[:6], 1):
        date = _escape(s["date"][:16]) if s["date"] else "unknown"
        task = _escape(s["task"][:60]) + ("\\.\\.\\." if len(s["task"]) > 60 else "")
        lines.append(f"`{i}.` {date}\n    _{task}_")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


# ── Business shortcut handlers ────────────────────────────────────────────────

async def _business_command(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    if not _is_captain(update):
        return
    args_text = " ".join(context.args).strip() if context.args else ""
    template  = BUSINESS_PROMPTS[key]

    if key == "morning":
        task  = template
        label = "Morning Briefing"
    elif not args_text:
        examples = {
            "proposal": "/proposal logistics company in Dubai",
            "email":    "/email SaaS startup in Singapore",
            "price":    "/price AI automation retainer",
            "close":    "/close prospect ghosted after pricing call",
        }
        ex = _escape(examples.get(key, f"/{key} description"))
        await update.message.reply_text(
            f"Usage: `{ex}`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    else:
        task  = template.format(args=args_text)
        label = f"{key.upper()}: {args_text[:60]}"

    await _run_and_reply(update, task, label=label)


async def cmd_proposal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _business_command(update, context, "proposal")

async def cmd_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _business_command(update, context, "email")

async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _business_command(update, context, "price")

async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _business_command(update, context, "close")

async def cmd_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _business_command(update, context, "morning")


# ── Free-text task handler ────────────────────────────────────────────────────

async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_captain(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return
    task = update.message.text.strip()
    if not task:
        return
    await _run_and_reply(update, task)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 60)
    print("  JARVIS AI Council — Telegram Bot  v2.0")
    print("═" * 60)
    print(f"  Bot token : {BOT_TOKEN[:12]}...{BOT_TOKEN[-4:]}")
    print(f"  Captain ID: {CAPTAIN_ID if CAPTAIN_ID else 'NOT SET (all users allowed)'}")
    print(f"  Env file  : {ENV_FILE}")
    print("═" * 60)
    print("  Commands: /start /status /history /last /find")
    print("  Business: /proposal /email /price /close /morning")
    print("  Press Ctrl+C to stop.\n")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("history",  cmd_history))
    app.add_handler(CommandHandler("last",     cmd_last))
    app.add_handler(CommandHandler("find",     cmd_find))
    app.add_handler(CommandHandler("proposal", cmd_proposal))
    app.add_handler(CommandHandler("email",    cmd_email))
    app.add_handler(CommandHandler("price",    cmd_price))
    app.add_handler(CommandHandler("close",    cmd_close))
    app.add_handler(CommandHandler("morning",  cmd_morning))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
