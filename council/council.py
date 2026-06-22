#!/usr/bin/env python3
"""
JARVIS AI COUNCIL — Aliyar Solutions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You type ONE task.
All 15 AI models respond simultaneously.
Claude Opus 4.8 synthesizes the final verdict.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import asyncio
import os
import sys
import json
from datetime import datetime

# ── Auto-install dependencies ─────────────────────────────────────────────────
def install(pkg):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    import httpx
except ImportError:
    print("Installing httpx..."); install("httpx"); import httpx

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN
    R = Fore.RED;   W = Fore.WHITE;  B = Style.BRIGHT; RS = Style.RESET_ALL
except ImportError:
    print("Installing colorama..."); install("colorama")
    from colorama import Fore, Style, init; init(autoreset=True)
    G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN
    R = Fore.RED;   W = Fore.WHITE;  B = Style.BRIGHT; RS = Style.RESET_ALL

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════════════════════
#  COUNCIL CONFIGURATION
#  Add your API keys here OR set them as environment variables
# ═══════════════════════════════════════════════════════════════════════════════

ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_KEY  = os.getenv("OPENROUTER_API_KEY", "")

# Your 11 NVIDIA keys — each mapped to a model
# Set these as environment variables or paste directly here
NVIDIA_KEYS = {
    "minimax":      os.getenv("NVIDIA_KEY_MINIMAX",      ""),
    "deepseek_v4":  os.getenv("NVIDIA_KEY_DEEPSEEK_V4",  ""),
    "deepseek_pro": os.getenv("NVIDIA_KEY_DEEPSEEK_PRO", ""),
    "zai_glam":     os.getenv("NVIDIA_KEY_ZAIGLAM",      ""),
    "mistral":      os.getenv("NVIDIA_KEY_MISTRAL",       ""),
    "jamba":        os.getenv("NVIDIA_KEY_JAMBA",         ""),
    "gemini":       os.getenv("NVIDIA_KEY_GEMINI",        ""),
    "nvidia_4":     os.getenv("NVIDIA_KEY_4",             ""),
    "nvidia_5":     os.getenv("NVIDIA_KEY_5",             ""),
    "nvidia_6":     os.getenv("NVIDIA_KEY_6",             ""),
    "nvidia_7":     os.getenv("NVIDIA_KEY_7",             ""),
}


# ═══════════════════════════════════════════════════════════════════════════════
#  THE 15 COUNCIL MEMBERS
# ═══════════════════════════════════════════════════════════════════════════════

COUNCIL = [
    # ── SYNTHESIZER — reads all responses and writes final verdict ─────────────
    {
        "name":          "Claude Opus 4.8",
        "role":          "Chief Council Synthesizer",
        "provider":      "anthropic",
        "model":         "claude-opus-4-5",   # latest opus
        "api_key":       ANTHROPIC_KEY,
        "synthesizer":   True,
    },

    # ── ANTHROPIC ─────────────────────────────────────────────────────────────
    {
        "name":     "Claude Opus 4.6",
        "role":     "Senior Strategic Advisor",
        "provider": "anthropic",
        "model":    "claude-opus-4-5",
        "api_key":  ANTHROPIC_KEY,
    },
    {
        "name":     "Claude Sonnet 4.6",
        "role":     "Operations Intelligence",
        "provider": "anthropic",
        "model":    "claude-sonnet-4-6",
        "api_key":  ANTHROPIC_KEY,
    },

    # ── NVIDIA ────────────────────────────────────────────────────────────────
    {
        "name":     "MiniMax M2.7",
        "role":     "Creative & Content Director",
        "provider": "nvidia",
        "model":    "minimax/minimax-01",
        "api_key":  NVIDIA_KEYS["minimax"],
    },
    {
        "name":     "DeepSeek V4 Flash",
        "role":     "Code & Engineering Lead",
        "provider": "nvidia",
        "model":    "deepseek-ai/deepseek-v4-flash",
        "api_key":  NVIDIA_KEYS["deepseek_v4"],
    },
    {
        "name":     "DeepSeek Pro 4",
        "role":     "Deep Research Analyst",
        "provider": "nvidia",
        "model":    "deepseek-ai/deepseek-v3-0324",
        "api_key":  NVIDIA_KEYS["deepseek_pro"],
    },
    {
        "name":     "Z AI Glam 5.1",
        "role":     "Innovation & Future Scout",
        "provider": "nvidia",
        "model":    "zai-org/glam-5.1",
        "api_key":  NVIDIA_KEYS["zai_glam"],
    },
    {
        "name":     "Mistral Medium",
        "role":     "Risk & Compliance Assessor",
        "provider": "nvidia",
        "model":    "mistralai/mistral-medium-3",
        "api_key":  NVIDIA_KEYS["mistral"],
    },
    {
        "name":     "Jamba Large 1.7",
        "role":     "Long-Context Document Expert",
        "provider": "nvidia",
        "model":    "ai21labs/jamba-1.7-large-instruct",
        "api_key":  NVIDIA_KEYS["jamba"],
    },
    {
        "name":     "Gemini 3.1 Pro",
        "role":     "Market Intelligence Officer",
        "provider": "nvidia",
        "model":    "google/gemini-2.5-pro",
        "api_key":  NVIDIA_KEYS["gemini"],
    },
    {
        "name":     "NVIDIA Model 4",
        "role":     "Technical Specialist",
        "provider": "nvidia",
        "model":    "meta/llama-3.3-70b-instruct",
        "api_key":  NVIDIA_KEYS["nvidia_4"],
    },
    {
        "name":     "NVIDIA Model 5",
        "role":     "Business Strategy Advisor",
        "provider": "nvidia",
        "model":    "qwen/qwen2.5-72b-instruct",
        "api_key":  NVIDIA_KEYS["nvidia_5"],
    },

    # ── OPENROUTER ────────────────────────────────────────────────────────────
    {
        "name":     "GPT-4o",
        "role":     "Executive Decision Advisor",
        "provider": "openrouter",
        "model":    "openai/gpt-4o",
        "api_key":  OPENROUTER_KEY,
    },
    {
        "name":     "Llama 3.3 70B",
        "role":     "Open Source Intelligence",
        "provider": "openrouter",
        "model":    "meta-llama/llama-3.3-70b-instruct",
        "api_key":  OPENROUTER_KEY,
    },
    {
        "name":     "Qwen 72B",
        "role":     "Global Markets Specialist",
        "provider": "openrouter",
        "model":    "qwen/qwen-2.5-72b-instruct",
        "api_key":  OPENROUTER_KEY,
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  API CALLERS
# ═══════════════════════════════════════════════════════════════════════════════

NVIDIA_URL     = "https://integrate.api.nvidia.com/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_URL  = "https://api.anthropic.com/v1/messages"


async def call_nvidia(client: httpx.AsyncClient, member: dict, task: str) -> str:
    if not member["api_key"]:
        return "[SKIPPED — no API key configured]"
    try:
        r = await client.post(
            NVIDIA_URL,
            headers={"Authorization": f"Bearer {member['api_key']}", "Content-Type": "application/json"},
            json={"model": member["model"], "messages": [{"role": "user", "content": task}],
                  "max_tokens": 1024, "temperature": 0.7},
            timeout=45.0,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[ERROR: {str(e)[:120]}]"


async def call_openrouter(client: httpx.AsyncClient, member: dict, task: str) -> str:
    if not member["api_key"]:
        return "[SKIPPED — no API key configured]"
    try:
        r = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {member['api_key']}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aliyarsolutions.com",
                "X-Title": "JARVIS AI Council",
            },
            json={"model": member["model"], "messages": [{"role": "user", "content": task}], "max_tokens": 1024},
            timeout=45.0,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[ERROR: {str(e)[:120]}]"


async def call_anthropic(client: httpx.AsyncClient, member: dict, task: str, max_tokens: int = 1024) -> str:
    if not member["api_key"]:
        return "[SKIPPED — no API key configured]"
    try:
        r = await client.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": member["api_key"],
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={"model": member["model"], "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": task}]},
            timeout=90.0,
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()
    except Exception as e:
        return f"[ERROR: {str(e)[:120]}]"


async def query_member(client: httpx.AsyncClient, member: dict, task: str) -> str:
    p = member["provider"]
    if p == "anthropic":
        return await call_anthropic(client, member, task)
    if p == "nvidia":
        return await call_nvidia(client, member, task)
    if p == "openrouter":
        return await call_openrouter(client, member, task)
    return "[Unknown provider]"


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN COUNCIL SESSION
# ═══════════════════════════════════════════════════════════════════════════════

async def run_council(task: str):
    synthesizer = next(m for m in COUNCIL if m.get("synthesizer"))
    members     = [m for m in COUNCIL if not m.get("synthesizer")]

    # ── Header ────────────────────────────────────────────────────────────────
    print(f"\n{B}{C}{'═'*65}{RS}")
    print(f"{B}{C}   JARVIS AI COUNCIL — Aliyar Solutions{RS}")
    print(f"{C}{'═'*65}{RS}")
    print(f"{W}   Task  : {task[:70]}{'...' if len(task)>70 else ''}{RS}")
    print(f"{W}   Models: {len(members)} council members + {synthesizer['name']}{RS}")
    print(f"{W}   Time  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RS}")
    print(f"{C}{'═'*65}{RS}\n")

    print(f"{Y}⚡  Sending task to all {len(members)} council members simultaneously...{RS}\n")

    # ── Query all members in parallel ─────────────────────────────────────────
    async with httpx.AsyncClient() as client:

        # Track progress as results come in
        tasks_list  = [query_member(client, m, task) for m in members]
        results_raw = await asyncio.gather(*tasks_list, return_exceptions=True)

        council_responses = []
        for i, (member, result) in enumerate(zip(members, results_raw), 1):
            if isinstance(result, Exception):
                result = f"[ERROR: {str(result)[:120]}]"
            is_error = result.startswith("[ERROR") or result.startswith("[SKIPPED")
            icon  = f"{R}❌{RS}" if is_error else f"{G}✅{RS}"
            print(f"  {icon}  [{i:02d}] {B}{member['name']:<22}{RS}  {member['role']}")
            council_responses.append({
                "member":   member["name"],
                "role":     member["role"],
                "response": result,
            })

        # ── Synthesis ─────────────────────────────────────────────────────────
        print(f"\n{C}{'─'*65}{RS}")
        print(f"{B}{Y}  🏛️  {synthesizer['name']} is synthesizing the council verdict...{RS}")
        print(f"{C}{'─'*65}{RS}\n")

        valid = [r for r in council_responses if not r["response"].startswith("[")]
        synthesis_prompt = f"""You are the Chief AI Strategist for Aliyar Solutions, a global technology company.

The AI Council of {len(valid)} expert AI models has reviewed this task:

TASK:
{task}

COUNCIL INPUTS:
{json.dumps([{"expert": r["member"], "role": r["role"], "input": r["response"][:600]} for r in valid], indent=2)}

Your job as Chief Synthesizer:
1. Extract the BEST ideas and insights from each council member
2. Identify consensus points and highlight unique valuable perspectives
3. Eliminate contradictions and weak suggestions
4. Write ONE definitive, authoritative response that is superior to any individual answer
5. Structure it professionally — Aliyar Solutions standard

COUNCIL VERDICT:"""

        final = await call_anthropic(client, synthesizer, synthesis_prompt, max_tokens=2048)

        # ── Output ────────────────────────────────────────────────────────────
        print(f"{B}{G}{'═'*65}{RS}")
        print(f"{B}{G}  🏆  COUNCIL VERDICT{RS}")
        print(f"{G}{'═'*65}{RS}\n")
        print(f"{W}{final}{RS}\n")
        print(f"{G}{'═'*65}{RS}")

        # ── Optional: show individual responses ───────────────────────────────
        try:
            show = input(f"\n{Y}  Show individual council responses? (y/n): {RS}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            show = "n"

        if show == "y":
            for r in council_responses:
                print(f"\n{C}{'─'*65}{RS}")
                print(f"{B}{r['member']}{RS}  |  {r['role']}")
                print(f"{C}{'─'*65}{RS}")
                print(r["response"])

        # ── Save session ──────────────────────────────────────────────────────
        os.makedirs("sessions", exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sessions/council_{ts}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("JARVIS AI COUNCIL SESSION\n")
            f.write(f"Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Task   : {task}\n")
            f.write(f"Members: {len(members)}\n")
            f.write(f"\n{'='*65}\nCOUNCIL VERDICT\n{'='*65}\n{final}\n\n")
            for r in council_responses:
                f.write(f"\n{'─'*65}\n{r['member']} — {r['role']}\n{'─'*65}\n{r['response']}\n")

        print(f"\n{Y}  💾  Session saved → {filename}{RS}\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{B}  JARVIS AI Council — Aliyar Solutions{RS}")
    print(f"  {len([m for m in COUNCIL if not m.get('synthesizer')])} models. One task. One verdict.\n")

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        print(f"  Task: {task}\n")
    else:
        try:
            task = input("  Enter your task: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return

    if not task:
        print("  No task entered. Exiting.")
        return

    asyncio.run(run_council(task))


if __name__ == "__main__":
    main()
