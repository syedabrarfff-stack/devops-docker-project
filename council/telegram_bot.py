#!/usr/bin/env python3
"""
JARVIS AI Council — Telegram Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Captain sends a task via Telegram → all 14 models fire → verdict delivered back.
Usage: python telegram_bot.py
Setup: Add TELEGRAM_BOT_TOKEN and TELEGRAM_CAPTAIN_ID to council/.env
"""

import asyncio
import os
import sys
import json
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
CAPTAIN_ID = os.getenv("TELEGRAM_CAPTAIN_ID", "")  # Your Telegram user ID (numeric)

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


# ── Import council engine (reuse all providers + API callers) ─────────────────

sys.path.insert(0, SCRIPT_DIR)

# Load keys from council.py without running main()
import importlib.util
spec = importlib.util.spec_from_file_location("council", os.path.join(SCRIPT_DIR, "council.py"))
_council = importlib.util.load_module_from_spec(spec)
spec.loader.exec_module(_council)

COUNCIL              = _council.COUNCIL
call_bedrock_synthesizer = _council.call_bedrock_synthesizer
query_member         = _council.query_member


# ── Telegram helpers ──────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def verdict_to_telegram(verdict: str, active: int, total: int, task: str) -> str:
    """Convert the structured council verdict to Telegram-formatted message."""
    lines = []
    lines.append(f"🏛️ *COUNCIL VERDICT*")
    lines.append(f"_{_escape(task[:80])}{'...' if len(task) > 80 else ''}_")
    lines.append(f"_{active}/{total} members active_\n")

    section_map = {
        "## VERDICT":           "🎯 *VERDICT*",
        "## KEY INSIGHTS":      "💡 *KEY INSIGHTS*",
        "## ACTION PLAN":       "📋 *ACTION PLAN*",
        "## RISKS & WATCH-OUTS": "⚠️ *RISKS*",
        "## COUNCIL CONSENSUS": "🤝 *CONSENSUS*",
    }

    for line in verdict.splitlines():
        stripped = line.strip()
        matched = False
        for md_header, tg_header in section_map.items():
            if stripped.startswith(md_header):
                lines.append(f"\n{tg_header}")
                matched = True
                break
        if not matched:
            if stripped.startswith("- ") or stripped.startswith("• "):
                lines.append(f"• {_escape(stripped[2:])}")
            elif stripped and stripped[0].isdigit() and len(stripped) > 2 and stripped[1] in ".)" :
                lines.append(f"{_escape(stripped)}")
            elif stripped:
                lines.append(_escape(stripped))
            else:
                lines.append("")

    lines.append(f"\n⏱️ _{_escape(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}_")
    return "\n".join(lines)


# ── Council runner ────────────────────────────────────────────────────────────

async def run_council_for_telegram(task: str) -> tuple[str, int, int]:
    """Fire all council members, synthesize, return (verdict, active_count, total_count)."""
    synthesizer = next(m for m in COUNCIL if m.get("synthesizer"))
    members     = [m for m in COUNCIL if not m.get("synthesizer")]

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[query_member(client, m, task) for m in members],
            return_exceptions=True,
        )

    council_responses = []
    for member, result in zip(members, results):
        if isinstance(result, Exception):
            result = f"[ERROR: {str(result)[:100]}]"
        council_responses.append({
            "member":   member["name"],
            "role":     member["role"],
            "response": result,
        })

    valid = [r for r in council_responses if not r["response"].startswith("[")]

    synthesis_prompt = f"""You are the Supreme Strategic Intelligence of Aliyar Solutions.

The AI Council ({len(valid)} members) analyzed this task for the CEO:

TASK: {task}

COUNCIL INPUTS:
{json.dumps([{"expert": r["member"], "role": r["role"], "analysis": r["response"][:500]} for r in valid], indent=2)}

Produce a DEFINITIVE executive verdict in this EXACT format:

## VERDICT
[One decisive paragraph. No hedging.]

## KEY INSIGHTS
[3-5 bullet points — most valuable non-obvious insights]

## ACTION PLAN
[Numbered executable steps in priority order]

## RISKS & WATCH-OUTS
[2-3 critical risks. Skip if none significant.]

## COUNCIL CONSENSUS
[What all members agreed on — 1-2 sentences]

Be specific to Aliyar Solutions. 400 words max.

COUNCIL VERDICT:"""

    verdict = await call_bedrock_synthesizer(synthesis_prompt, max_tokens=1500)

    # Save session
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(SESSIONS_DIR, f"telegram_{ts}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"JARVIS TELEGRAM COUNCIL SESSION\n{'='*60}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Task: {task}\n")
        f.write(f"Active: {len(valid)}/{len(council_responses)}\n\n")
        f.write(f"VERDICT\n{'='*60}\n{verdict}\n\n")
        for r in council_responses:
            status = "ACTIVE" if not r["response"].startswith("[") else "SKIPPED"
            f.write(f"\n[{status}] {r['member']}\n{r['response']}\n")

    return verdict, len(valid), len(council_responses)


# ── Telegram handlers ─────────────────────────────────────────────────────────

def _is_captain(update: Update) -> bool:
    if CAPTAIN_ID_INT is None:
        return True  # No restriction set — allow all
    return update.effective_user.id == CAPTAIN_ID_INT


def _list_sessions(prefix: str = "") -> list[dict]:
    """Return session files sorted newest-first with metadata."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    sessions = []
    for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
        if not fname.endswith(".txt"):
            continue
        if prefix and not fname.startswith(prefix):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        task_line = ""
        date_line = ""
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
        sessions.append({"file": fname, "path": path, "task": task_line, "date": date_line})
    return sessions


def _read_verdict_from_file(path: str) -> str:
    """Extract just the COUNCIL VERDICT section from a session file."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Find between COUNCIL VERDICT and INDIVIDUAL MEMBER RESPONSES
        start = content.find("COUNCIL VERDICT\n")
        if start == -1:
            start = content.find("VERDICT\n=")
        end   = content.find("INDIVIDUAL MEMBER RESPONSES", start)
        if start == -1:
            return content[:2000]
        section = content[start:end if end != -1 else start + 3000]
        # Strip the header line
        lines = section.splitlines()
        return "\n".join(lines[2:]).strip()[:2500]
    except Exception as e:
        return f"[Could not read session: {e}]"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_captain(update):
        return
    await update.message.reply_text(
        "🏛️ *JARVIS AI Council — Online*\n\n"
        "Send any task → 14 models fire → verdict delivered\\.\n\n"
        "*Commands:*\n"
        "/history — last 8 council sessions\n"
        "/last — re\\-read most recent verdict\n"
        "/find keyword — search past sessions\n"
        "/status — provider health\n\n"
        "*Examples:*\n"
        "• _What pricing should Aliyar use for enterprise clients?_\n"
        "• _How do I close the healthcare lead who hasn't responded?_\n"
        "• _Write a cold outreach email for a logistics company_",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_captain(update):
        return
    bedrock  = "✅" if _council.BEDROCK_API_KEY else "❌"
    anthropic = "✅" if _council.ANTHROPIC_KEY else "❌"
    nv_count = sum(1 for v in _council.NV_KEYS.values() if v and v.startswith("nvapi-"))
    google   = "✅" if _council.GOOGLE_KEY else "❌"
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
        await update.message.reply_text("No council sessions yet\\. Send a task to get started\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    lines = ["📚 *Recent Council Sessions*\n"]
    for i, s in enumerate(sessions, 1):
        date  = _escape(s["date"][:16]) if s["date"] else "unknown"
        task  = _escape(s["task"][:55]) + ("\\.\\.\\." if len(s["task"]) > 55 else "")
        lines.append(f"`{i}.` {date}\n    _{task}_")
    lines.append(f"\n_Use /last to re\\-read the latest verdict_")
    lines.append(f"_Use /find keyword to search sessions_")
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
    header  = f"🔁 *Last Session*\n_{_escape(s['date'][:16])}_\n_{_escape(s['task'][:80])}_\n\n"
    full    = header + _escape(verdict)
    if len(full) <= 4000:
        await update.message.reply_text(full, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(header, parse_mode=ParseMode.MARKDOWN_V2)
        # Send verdict without escaping (it was already escaped by council)
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
    lines = [f"🔍 *Found {len(matches)} session(s) for* _{_escape(keyword)}_\n"]
    for i, s in enumerate(matches[:6], 1):
        date = _escape(s["date"][:16]) if s["date"] else "unknown"
        task = _escape(s["task"][:60]) + ("\\.\\.\\." if len(s["task"]) > 60 else "")
        lines.append(f"`{i}.` {date}\n    _{task}_")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_captain(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return

    task = update.message.text.strip()
    if not task:
        return

    # Send "thinking" acknowledgment immediately
    task_preview = _escape(task[:80]) + ("\\.\\.\\." if len(task) > 80 else "")
    thinking_msg = await update.message.reply_text(
        f"⚡ *Consulting 14\\-model council\\.\\.\\.*\n\n_{task_preview}_",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    try:
        verdict, active, total = await run_council_for_telegram(task)
        reply = verdict_to_telegram(verdict, active, total, task)

        # Telegram has 4096 char limit per message — split if needed
        if len(reply) <= 4000:
            await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN_V2)
        else:
            # Send in chunks at section boundaries
            chunks = reply.split("\n\n")
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

        # Delete the "thinking" message
        await thinking_msg.delete()

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Council error: {_escape(str(e)[:200])}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        await thinking_msg.delete()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 60)
    print("  JARVIS AI Council — Telegram Bot")
    print("═" * 60)
    print(f"  Bot token : {BOT_TOKEN[:12]}...{BOT_TOKEN[-4:]}")
    print(f"  Captain ID: {CAPTAIN_ID if CAPTAIN_ID else 'NOT SET (all users allowed)'}")
    print(f"  Env file  : {ENV_FILE}")
    print("═" * 60)
    print("  Bot is running. Send a message on Telegram.")
    print("  Press Ctrl+C to stop.\n")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("last",    cmd_last))
    app.add_handler(CommandHandler("find",    cmd_find))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
