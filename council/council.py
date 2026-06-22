#!/usr/bin/env python3
"""
JARVIS AI COUNCIL — Aliyar Solutions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One task → 14 models respond simultaneously
Claude Opus synthesizes the final verdict
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import asyncio
import os
import sys
import json
from datetime import datetime

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
    install("colorama")
    from colorama import Fore, Style, init; init(autoreset=True)
    G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN
    R = Fore.RED;   W = Fore.WHITE;  B = Style.BRIGHT; RS = Style.RESET_ALL

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    install("python-dotenv")
    from dotenv import load_dotenv
    load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
#  API KEYS — loaded from .env file
# ═══════════════════════════════════════════════════════════════════════════════

ANTHROPIC_KEY    = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_KEY   = os.getenv("OPENROUTER_API_KEY", "")
GOOGLE_KEY       = os.getenv("GOOGLE_API_KEY", "")

# 10 NVIDIA keys — one per model
NV_LLAMA4_MAV   = os.getenv("NVIDIA_KEY_LLAMA4_MAV",   "")
NV_LLAMA4_SCOUT = os.getenv("NVIDIA_KEY_LLAMA4_SCOUT", "")
NV_LLAMA33      = os.getenv("NVIDIA_KEY_LLAMA33",       "")
NV_QWEN         = os.getenv("NVIDIA_KEY_QWEN",          "")
NV_KIMI         = os.getenv("NVIDIA_KEY_KIMI",          "")
NV_MISTRAL      = os.getenv("NVIDIA_KEY_MISTRAL",       "")
NV_ZAIGLAM      = os.getenv("NVIDIA_KEY_ZAIGLAM",       "")
NV_DEEPSEEK_V4  = os.getenv("NVIDIA_KEY_DEEPSEEK_V4",  "")
NV_DEEPSEEK_PRO = os.getenv("NVIDIA_KEY_DEEPSEEK_PRO", "")
NV_MINIMAX      = os.getenv("NVIDIA_KEY_MINIMAX",       "")


# ═══════════════════════════════════════════════════════════════════════════════
#  THE 14 COUNCIL MEMBERS
# ═══════════════════════════════════════════════════════════════════════════════

COUNCIL = [

    # ── SYNTHESIZER — reads all responses, writes final verdict ───────────────
    {
        "name":        "Claude Opus — Chief Synthesizer",
        "role":        "Supreme Council Synthesizer",
        "provider":    "anthropic",
        "model":       "claude-opus-4-5",
        "api_key":     ANTHROPIC_KEY,
        "synthesizer": True,
    },

    # ── Anthropic ─────────────────────────────────────────────────────────────
    {
        "name":     "Claude Sonnet 4.6",
        "role":     "Operations & Strategy Expert",
        "provider": "anthropic",
        "model":    "claude-sonnet-4-6",
        "api_key":  ANTHROPIC_KEY,
    },

    # ── NVIDIA — 10 models ────────────────────────────────────────────────────
    {
        "name":     "Meta Llama 4 Maverick",
        "role":     "Advanced Reasoning Lead",
        "provider": "nvidia",
        "model":    "meta/llama-4-maverick-17b-128e-instruct",
        "api_key":  NV_LLAMA4_MAV,
    },
    {
        "name":     "Meta Llama 4 Scout",
        "role":     "Fast Intelligence Scout",
        "provider": "nvidia",
        "model":    "meta/llama-4-scout-17b-16e-instruct",
        "api_key":  NV_LLAMA4_SCOUT,
    },
    {
        "name":     "Meta Llama 3.3 70B",
        "role":     "Deep Analysis Expert",
        "provider": "nvidia",
        "model":    "meta/llama-3.3-70b-instruct",
        "api_key":  NV_LLAMA33,
    },
    {
        "name":     "Qwen 2.5 Coder 32B",
        "role":     "Code & Engineering Specialist",
        "provider": "nvidia",
        "model":    "qwen/qwen2.5-coder-32b-instruct",
        "api_key":  NV_QWEN,
    },
    {
        "name":     "Moonshot Kimi K2.6",
        "role":     "Long-Context Thinker",
        "provider": "nvidia",
        "model":    "moonshotai/kimi-k2.6",
        "api_key":  NV_KIMI,
    },
    {
        "name":     "Mistral Medium 3",
        "role":     "Risk & Compliance Assessor",
        "provider": "nvidia",
        "model":    "mistralai/mistral-medium-3-instruct",
        "api_key":  NV_MISTRAL,
    },
    {
        "name":     "Z AI Glam 5.1",
        "role":     "Innovation & Creative Director",
        "provider": "nvidia",
        "model":    "zai-org/glam-5.1",
        "api_key":  NV_ZAIGLAM,
    },
    {
        "name":     "DeepSeek V4 Flash",
        "role":     "Lightning Code Engine",
        "provider": "nvidia",
        "model":    "deepseek-ai/deepseek-v4-flash",
        "api_key":  NV_DEEPSEEK_V4,
    },
    {
        "name":     "DeepSeek Pro 4",
        "role":     "Deep Research Analyst",
        "provider": "nvidia",
        "model":    "deepseek-ai/deepseek-v4-flash",
        "api_key":  NV_DEEPSEEK_PRO,
    },
    {
        "name":     "MiniMax M2.7",
        "role":     "Creative & Content Strategist",
        "provider": "nvidia",
        "model":    "minimaxai/minimax-m2.7",
        "api_key":  NV_MINIMAX,
    },

    # ── Google ────────────────────────────────────────────────────────────────
    {
        "name":     "Gemini 2.5 Pro",
        "role":     "Market Intelligence & Research",
        "provider": "google",
        "model":    "gemini-2.5-pro",
        "api_key":  GOOGLE_KEY,
    },

    # ── OpenRouter (AI21 Jamba) ───────────────────────────────────────────────
    {
        "name":     "AI21 Jamba Large 1.7",
        "role":     "Long-Context Document Expert",
        "provider": "openrouter",
        "model":    "ai21/jamba-1-5-large",
        "api_key":  OPENROUTER_KEY,
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  API CALLERS
# ═══════════════════════════════════════════════════════════════════════════════

NVIDIA_URL     = "https://integrate.api.nvidia.com/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_URL  = "https://api.anthropic.com/v1/messages"
GOOGLE_URL     = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


async def call_nvidia(client, member, task):
    if not member["api_key"]:
        return "[SKIPPED — NVIDIA key not set in .env]"
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
        return f"[ERROR: {str(e)[:150]}]"


async def call_openrouter(client, member, task):
    if not member["api_key"]:
        return "[SKIPPED — OpenRouter key not set in .env]"
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
        return f"[ERROR: {str(e)[:150]}]"


async def call_anthropic(client, member, task, max_tokens=1024):
    if not member["api_key"]:
        return "[SKIPPED — Anthropic key not set in .env]"
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
        return f"[ERROR: {str(e)[:150]}]"


async def call_google(client, member, task):
    if not member["api_key"]:
        return "[SKIPPED — Google key not set in .env]"
    try:
        url = GOOGLE_URL.format(model=member["model"])
        r = await client.post(
            f"{url}?key={member['api_key']}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": task}]}]},
            timeout=45.0,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        return f"[ERROR: {str(e)[:150]}]"


async def query_member(client, member, task):
    p = member["provider"]
    if p == "anthropic":   return await call_anthropic(client, member, task)
    if p == "nvidia":      return await call_nvidia(client, member, task)
    if p == "openrouter":  return await call_openrouter(client, member, task)
    if p == "google":      return await call_google(client, member, task)
    return "[Unknown provider]"


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN COUNCIL SESSION
# ═══════════════════════════════════════════════════════════════════════════════

async def run_council(task):
    synthesizer = next(m for m in COUNCIL if m.get("synthesizer"))
    members     = [m for m in COUNCIL if not m.get("synthesizer")]

    print(f"\n{B}{C}{'═'*65}{RS}")
    print(f"{B}{C}   JARVIS AI COUNCIL — Aliyar Solutions{RS}")
    print(f"{C}{'═'*65}{RS}")
    print(f"{W}   Task   : {task[:70]}{'...' if len(task)>70 else ''}{RS}")
    print(f"{W}   Council: {len(members)} members + {synthesizer['name']}{RS}")
    print(f"{W}   Time   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RS}")
    print(f"{C}{'═'*65}{RS}\n")
    print(f"{Y}⚡  Consulting all {len(members)} council members simultaneously...{RS}\n")

    async with httpx.AsyncClient() as client:

        results = await asyncio.gather(*[query_member(client, m, task) for m in members], return_exceptions=True)

        council_responses = []
        for i, (member, result) in enumerate(zip(members, results), 1):
            if isinstance(result, Exception):
                result = f"[ERROR: {str(result)[:150]}]"
            is_err = result.startswith("[")
            icon = f"{R}❌{RS}" if is_err else f"{G}✅{RS}"
            print(f"  {icon} [{i:02d}] {B}{member['name']:<30}{RS} {member['role']}")
            council_responses.append({"member": member["name"], "role": member["role"], "response": result})

        print(f"\n{C}{'─'*65}{RS}")
        print(f"{B}{Y}  🏛️  {synthesizer['name']} synthesizing verdict...{RS}")
        print(f"{C}{'─'*65}{RS}\n")

        valid = [r for r in council_responses if not r["response"].startswith("[")]

        synthesis_prompt = f"""You are the Chief AI Strategist for Aliyar Solutions, a global technology company.

The AI Council of {len(valid)} expert models has reviewed this task:

TASK: {task}

COUNCIL INPUTS:
{json.dumps([{"expert": r["member"], "role": r["role"], "input": r["response"][:500]} for r in valid], indent=2)}

Your job:
1. Extract the BEST ideas from each council member
2. Identify strong consensus points
3. Flag any important disagreements
4. Produce ONE definitive, authoritative answer superior to any individual response
5. Structure it clearly for Captain

COUNCIL VERDICT:"""

        final = await call_anthropic(client, synthesizer, synthesis_prompt, max_tokens=2048)

        print(f"{B}{G}{'═'*65}{RS}")
        print(f"{B}{G}  🏆  COUNCIL VERDICT{RS}")
        print(f"{G}{'═'*65}{RS}\n")
        print(f"{W}{final}{RS}\n")
        print(f"{G}{'═'*65}{RS}")

        try:
            show = input(f"\n{Y}  Show individual responses? (y/n): {RS}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            show = "n"

        if show == "y":
            for r in council_responses:
                print(f"\n{C}{'─'*65}{RS}")
                print(f"{B}{r['member']}{RS}  |  {r['role']}")
                print(f"{C}{'─'*65}{RS}")
                print(r["response"])

        os.makedirs("sessions", exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sessions/council_{ts}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"JARVIS AI COUNCIL SESSION\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Task: {task}\n\n")
            f.write(f"{'='*65}\nCOUNCIL VERDICT\n{'='*65}\n{final}\n\n")
            for r in council_responses:
                f.write(f"\n{'─'*65}\n{r['member']} — {r['role']}\n{'─'*65}\n{r['response']}\n")

        print(f"\n{Y}  💾  Session saved → {filename}{RS}\n")


def main():
    print(f"\n{B}  JARVIS AI Council — Aliyar Solutions{RS}")
    print(f"  14 models. One task. One verdict.\n")

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        try:
            task = input("  Enter your task: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return

    if not task:
        print("  No task entered.")
        return

    asyncio.run(run_council(task))


if __name__ == "__main__":
    main()
