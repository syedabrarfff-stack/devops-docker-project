#!/usr/bin/env python3
"""
JARVIS AI Council — REST API Server  v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Exposes the 14-model Council as an HTTP API so the JARVIS backend
(FastAPI on port 8000) can call it programmatically.

Also runs APScheduler for autonomous daily morning briefing at 07:00 IST.

Endpoints:
  POST /council/convene   — fire the council, return verdict
  GET  /council/sessions  — list recent sessions with metadata
  GET  /council/health    — provider key presence check (no live calls)
  GET  /                  — service info

Usage: python api.py
Runs on: http://localhost:8001
"""

import asyncio
import os
import sys
from datetime import datetime

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
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("Installing FastAPI + uvicorn...")
    install("fastapi>=0.111.0"); install("uvicorn>=0.30.0")
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

try:
    from pydantic import BaseModel, Field
except ImportError:
    install("pydantic>=2.0.0"); from pydantic import BaseModel, Field

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    print("Installing APScheduler...")
    install("apscheduler>=3.10.0")
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

try:
    import httpx
except ImportError:
    install("httpx"); import httpx


# ── Import council engine ─────────────────────────────────────────────────────

sys.path.insert(0, SCRIPT_DIR)
import importlib.util
spec = importlib.util.spec_from_file_location("council", os.path.join(SCRIPT_DIR, "council.py"))
_council = importlib.util.load_module_from_spec(spec)
spec.loader.exec_module(_council)

run_council_progressive  = _council.run_council_progressive
_save_session            = _council._save_session
COUNCIL                  = _council.COUNCIL
BEDROCK_API_KEY          = _council.BEDROCK_API_KEY
ANTHROPIC_KEY            = _council.ANTHROPIC_KEY
GOOGLE_KEY               = _council.GOOGLE_KEY
OPENROUTER_KEY           = _council.OPENROUTER_KEY
NV_KEYS                  = _council.NV_KEYS

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
CAPTAIN_ID = os.getenv("TELEGRAM_CAPTAIN_ID", "")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="JARVIS AI Council API",
    description=(
        "Programmatic access to the 14-model AI Council for Aliyar Solutions. "
        "Also exposes an autonomous 07:00 daily morning briefing via APScheduler."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ConveneRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=4000, description="The question or task for the council")
    max_tokens: int = Field(2048, ge=256, le=4096)


class ConveneResponse(BaseModel):
    task: str
    verdict: str
    active_members: int
    total_members: int
    duration_seconds: float
    session_file: str
    timestamp: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service":   "JARVIS AI Council API",
        "version":   "1.0.0",
        "company":   "Aliyar Solutions",
        "endpoints": [
            "POST /council/convene",
            "GET  /council/sessions",
            "GET  /council/health",
            "GET  /docs",
        ],
    }


@app.post("/council/convene", response_model=ConveneResponse)
async def convene_council(request: ConveneRequest):
    """
    Fire the full AI Council for a given task.
    All 13 members query simultaneously; Bedrock synthesizes the final verdict.
    Typical latency: 15-40 seconds depending on provider availability.
    """
    t0 = asyncio.get_event_loop().time()

    council_responses, verdict, active, total = await run_council_progressive(request.task)

    duration = round(asyncio.get_event_loop().time() - t0, 2)
    session_file = _save_session(request.task, council_responses, verdict, prefix="api")

    return ConveneResponse(
        task=request.task,
        verdict=verdict,
        active_members=active,
        total_members=total,
        duration_seconds=duration,
        session_file=os.path.basename(session_file),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.get("/council/sessions")
async def list_sessions(limit: int = 20, source: str = ""):
    """
    List recent council sessions with metadata.
    source filter: 'api' | 'telegram' | 'terminal' (empty = all)
    """
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    sessions = []
    prefix_map = {"api": "api_", "telegram": "telegram_", "terminal": "council_"}
    filter_prefix = prefix_map.get(source, "")

    for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
        if not fname.endswith(".txt"):
            continue
        if filter_prefix and not fname.startswith(filter_prefix):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        task_line = date_line = active_line = ""
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Task   :") or line.startswith("Task:"):
                        task_line = line.split(":", 1)[1].strip()
                    if line.startswith("Date   :") or line.startswith("Date:"):
                        date_line = line.split(":", 1)[1].strip()
                    if line.startswith("Council:") or line.startswith("Active:"):
                        active_line = line.split(":", 1)[1].strip()
                    if task_line and date_line:
                        break
        except Exception:
            pass
        src = "telegram" if fname.startswith("telegram_") else ("api" if fname.startswith("api_") else "terminal")
        sessions.append({
            "file":   fname,
            "task":   task_line or fname,
            "date":   date_line,
            "active": active_line,
            "source": src,
        })
        if len(sessions) >= limit:
            break

    return {"sessions": sessions, "count": len(sessions)}


@app.get("/council/health")
async def health_check():
    """Provider key presence check. Does NOT make live API calls."""
    nv_count = sum(1 for v in NV_KEYS.values() if v and v.startswith("nvapi-"))
    synthesizer_ready = bool(BEDROCK_API_KEY or ANTHROPIC_KEY)
    return {
        "status":    "online" if synthesizer_ready else "degraded",
        "synthesizer": {
            "bedrock_api_key":  bool(BEDROCK_API_KEY),
            "anthropic_direct": bool(ANTHROPIC_KEY),
            "ready":            synthesizer_ready,
        },
        "council_members": {
            "anthropic":   bool(ANTHROPIC_KEY),
            "nvidia_nim":  nv_count,
            "google":      bool(GOOGLE_KEY),
            "openrouter":  bool(OPENROUTER_KEY),
            "total_slots": 13,
            "configured":  int(bool(ANTHROPIC_KEY)) + nv_count + int(bool(GOOGLE_KEY)) + int(bool(OPENROUTER_KEY)),
        },
        "morning_briefing": {
            "scheduled": "07:00 daily",
            "telegram":  bool(BOT_TOKEN and CAPTAIN_ID),
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Morning briefing job ──────────────────────────────────────────────────────

MORNING_PROMPT = (
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
)


async def send_morning_briefing():
    """Fires the full council for a morning briefing, delivers result to Captain via Telegram."""
    if not BOT_TOKEN or not CAPTAIN_ID:
        print("[Morning Briefing] Skipped — TELEGRAM_BOT_TOKEN or TELEGRAM_CAPTAIN_ID not set")
        return
    try:
        print(f"[Morning Briefing] {datetime.now().strftime('%H:%M')} — Convening council...")
        _, verdict, active, total = await run_council_progressive(MORNING_PROMPT)
        _save_session("Morning Briefing", [], verdict, prefix="morning")

        day_str = datetime.now().strftime("%A, %B %d")
        msg = (
            f"🌅 *Good morning, Captain*\n"
            f"_JARVIS Morning Briefing — {day_str}_\n"
            f"_{active}/{total} council members active_\n\n"
            + verdict[:3500]
        )
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CAPTAIN_ID, "text": msg, "parse_mode": "Markdown"},
                timeout=30.0,
            )
        print(f"[Morning Briefing] ✅ Delivered to Captain at {datetime.now().strftime('%H:%M')}")
    except Exception as e:
        print(f"[Morning Briefing] ❌ ERROR: {e}")


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def on_startup():
    scheduler.add_job(
        send_morning_briefing,
        CronTrigger(hour=7, minute=0, timezone="Asia/Kolkata"),
        id="morning_briefing",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()

    nv_count = sum(1 for v in NV_KEYS.values() if v and v.startswith("nvapi-"))
    print(f"\n{'═'*60}")
    print(f"  JARVIS AI Council API — Online")
    print(f"{'═'*60}")
    print(f"  POST http://localhost:8001/council/convene")
    print(f"  GET  http://localhost:8001/council/sessions")
    print(f"  GET  http://localhost:8001/council/health")
    print(f"  GET  http://localhost:8001/docs  (interactive API docs)")
    print(f"{'─'*60}")
    print(f"  Bedrock  : {'✓' if BEDROCK_API_KEY else '✗'}")
    print(f"  Anthropic: {'✓' if ANTHROPIC_KEY else '✗'}")
    print(f"  NVIDIA   : {nv_count}/10 slots")
    print(f"  Google   : {'✓' if GOOGLE_KEY else '✗'}")
    print(f"  Telegram : {'✓' if BOT_TOKEN else '✗ (morning briefing disabled)'}")
    print(f"  Morning  : 07:00 IST daily")
    print(f"{'═'*60}\n")


@app.on_event("shutdown")
async def on_shutdown():
    if scheduler.running:
        scheduler.shutdown()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info",
    )
