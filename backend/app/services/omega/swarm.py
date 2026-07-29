"""
JARVIS OMEGA — Global Intelligence Swarm Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fires 16 models across 4 continents simultaneously.
Streams live SSE events as each model responds.
Synthesises a world-class verdict with Claude Opus.

Providers by origin:
  USA     — Claude Opus, Claude Sonnet (Bedrock), GPT-4o, Llama 4 Maverick, Llama 4 Scout, Llama 3.3 70B
  CHINA   — DeepSeek V4 Pro, DeepSeek V4 Flash, Kimi K2.6, Qwen 2.5, MiniMax M3, GLM-4
  EUROPE  — Mistral Medium 3, Mistral Large
  GLOBAL  — Gemini 1.5 Pro, Llama 3.3 Groq
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncIterator, Callable, Awaitable, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Swarm member definitions ─────────────────────────────────────────────────

OMEGA_SWARM: list[dict] = [
    # ── USA — Frontier Labs ─────────────────────────────────────────────────
    {
        "id": "claude-opus",
        "name": "Claude Opus 4",
        "origin": "USA",
        "flag": "🇺🇸",
        "lab": "Anthropic",
        "role": "Supreme Strategist",
        "provider": "anthropic",
        "model": "claude-opus-4-8",
        "synthesizer": True,
    },
    {
        "id": "claude-sonnet-bedrock",
        "name": "Claude Sonnet (AWS)",
        "origin": "USA",
        "flag": "🇺🇸",
        "lab": "Anthropic / AWS",
        "role": "Cloud Architect",
        "provider": "bedrock",
        "model": "global.anthropic.claude-sonnet-4-6",
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "origin": "USA",
        "flag": "🇺🇸",
        "lab": "OpenAI",
        "role": "Market Analyst",
        "provider": "openai",
        "model": "gpt-4o",
    },
    {
        "id": "llama-4-maverick",
        "name": "Llama 4 Maverick",
        "origin": "USA",
        "flag": "🇺🇸",
        "lab": "Meta / NVIDIA NIM",
        "role": "Open-Source Powerhouse",
        "provider": "nvidia",
        "model": "meta/llama-4-maverick-17b-128e-instruct",
    },
    {
        "id": "llama-4-scout",
        "name": "Llama 4 Scout",
        "origin": "USA",
        "flag": "🇺🇸",
        "lab": "Meta / NVIDIA NIM",
        "role": "Speed Intelligence",
        "provider": "nvidia",
        "model": "meta/llama-4-scout-17b-16e-instruct",
    },
    {
        "id": "llama-3-3-groq",
        "name": "Llama 3.3 70B (Groq)",
        "origin": "USA",
        "flag": "🇺🇸",
        "lab": "Meta / Groq",
        "role": "Ultra-Fast Reasoning",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
    },
    # ── CHINA — Deep Labs ───────────────────────────────────────────────────
    {
        "id": "deepseek-v4-pro",
        "name": "DeepSeek V4 Pro",
        "origin": "CHINA",
        "flag": "🇨🇳",
        "lab": "DeepSeek / NVIDIA NIM",
        "role": "Deep Reasoning Engine",
        "provider": "nvidia",
        "model": "deepseek-ai/deepseek-v4-pro",
    },
    {
        "id": "deepseek-v4-flash",
        "name": "DeepSeek V4 Flash",
        "origin": "CHINA",
        "flag": "🇨🇳",
        "lab": "DeepSeek / NVIDIA NIM",
        "role": "Fast Chinese Intelligence",
        "provider": "nvidia",
        "model": "deepseek-ai/deepseek-v4-flash",
    },
    {
        "id": "kimi-k2",
        "name": "Kimi K2.6",
        "origin": "CHINA",
        "flag": "🇨🇳",
        "lab": "Moonshot AI / NVIDIA NIM",
        "role": "Long-Context Analyst",
        "provider": "nvidia",
        "model": "moonshotai/kimi-k2.6",
    },
    {
        "id": "qwen-25-coder",
        "name": "Qwen 2.5 Coder",
        "origin": "CHINA",
        "flag": "🇨🇳",
        "lab": "Alibaba / NVIDIA NIM",
        "role": "Code & Technical Specialist",
        "provider": "nvidia",
        "model": "qwen/qwen2.5-coder-32b-instruct",
    },
    {
        "id": "minimax-m3",
        "name": "MiniMax M3",
        "origin": "CHINA",
        "flag": "🇨🇳",
        "lab": "MiniMax / NVIDIA NIM",
        "role": "Creative Intelligence",
        "provider": "nvidia",
        "model": "minimaxai/minimax-m3",
    },
    {
        "id": "glm-4",
        "name": "GLM-4",
        "origin": "CHINA",
        "flag": "🇨🇳",
        "lab": "ZhipuAI (Tsinghua)",
        "role": "Academic Reasoning",
        "provider": "zhipuai",
        "model": "glm-4",
    },
    # ── EUROPE — Mistral ────────────────────────────────────────────────────
    {
        "id": "mistral-medium-nim",
        "name": "Mistral Medium 3",
        "origin": "EUROPE",
        "flag": "🇫🇷",
        "lab": "Mistral AI / NVIDIA NIM",
        "role": "European AI Specialist",
        "provider": "nvidia",
        "model": "mistralai/mistral-medium-3-instruct",
    },
    {
        "id": "mistral-large",
        "name": "Mistral Large",
        "origin": "EUROPE",
        "flag": "🇫🇷",
        "lab": "Mistral AI",
        "role": "Regulatory & Risk Analyst",
        "provider": "mistral",
        "model": "mistral-large-latest",
    },
    # ── GOOGLE — DeepMind ───────────────────────────────────────────────────
    {
        "id": "gemini-pro",
        "name": "Gemini 1.5 Pro",
        "origin": "GLOBAL",
        "flag": "🌐",
        "lab": "Google DeepMind",
        "role": "Research & Knowledge",
        "provider": "google",
        "model": "gemini-pro-latest",
    },
    # ── NVIDIA — GPU Cloud ──────────────────────────────────────────────────
    {
        "id": "llama-3-3-nim",
        "name": "Llama 3.3 70B (NIM)",
        "origin": "USA",
        "flag": "🇺🇸",
        "lab": "Meta / NVIDIA NIM",
        "role": "GPU-Accelerated Analysis",
        "provider": "nvidia",
        "model": "meta/llama-3.3-70b-instruct",
    },
]

# Members that actually run (exclude synthesizer from parallel pool)
SWARM_MEMBERS = [m for m in OMEGA_SWARM if not m.get("synthesizer")]
SYNTHESIZER   = next(m for m in OMEGA_SWARM if m.get("synthesizer"))


# ── Low-level provider callers ────────────────────────────────────────────────

async def _call_anthropic(model: str, prompt: str, max_tokens: int = 1024) -> str:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        data = r.json()
    return data["content"][0]["text"]


async def _call_bedrock(model: str, prompt: str, max_tokens: int = 1024) -> str:
    try:
        import boto3, json as _json
        client = boto3.client(
            "bedrock-runtime",
            region_name=getattr(settings, "AWS_REGION", "us-east-1"),
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        )
        body = _json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = await asyncio.to_thread(
            client.invoke_model,
            modelId=model, body=body, contentType="application/json", accept="application/json",
        )
        result = _json.loads(resp["body"].read())
        return result["content"][0]["text"]
    except Exception as exc:
        raise RuntimeError(f"Bedrock error: {exc}") from exc


async def _call_openai(model: str, prompt: str, max_tokens: int = 1024) -> str:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
        )
        data = r.json()
    return data["choices"][0]["message"]["content"]


async def _call_nvidia(model: str, prompt: str, max_tokens: int = 1024) -> str:
    keys = [
        getattr(settings, k, None)
        for k in ["NVIDIA_API_KEY", "NVIDIA_API_KEY_B", "NVIDIA_API_KEY_C",
                  "NVIDIA_API_KEY_D", "NVIDIA_API_KEY_E", "NVIDIA_API_KEY_F",
                  "NVIDIA_API_KEY_G", "NVIDIA_API_KEY_H", "NVIDIA_API_KEY_I",
                  "NVIDIA_API_KEY_J"]
    ]
    keys = [k for k in keys if k and k.startswith("nvapi-")]
    if not keys:
        raise RuntimeError("No NVIDIA NIM API keys configured")
    last_err = None
    for key in keys:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                r = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                    },
                )
                data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            last_err = exc
    raise RuntimeError(f"All NVIDIA NIM keys failed: {last_err}")


async def _call_groq(model: str, prompt: str, max_tokens: int = 1024) -> str:
    key = getattr(settings, "GROQ_API_KEY", None)
    if not key:
        raise RuntimeError("GROQ_API_KEY not configured")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
        )
        data = r.json()
    return data["choices"][0]["message"]["content"]


async def _call_google(model: str, prompt: str, max_tokens: int = 1024) -> str:
    key = getattr(settings, "GOOGLE_API_KEY", None) or getattr(settings, "GEMINI_API_KEY", None)
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not configured")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
        )
        data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_mistral(model: str, prompt: str, max_tokens: int = 1024) -> str:
    key = getattr(settings, "MISTRAL_API_KEY", None)
    if not key:
        raise RuntimeError("MISTRAL_API_KEY not configured")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
        )
        data = r.json()
    return data["choices"][0]["message"]["content"]


async def _call_zhipuai(model: str, prompt: str, max_tokens: int = 1024) -> str:
    key = getattr(settings, "ZHIPUAI_API_KEY", None)
    if not key:
        raise RuntimeError("ZHIPUAI_API_KEY not configured")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
        )
        data = r.json()
    return data["choices"][0]["message"]["content"]


_PROVIDER_DISPATCH = {
    "anthropic": _call_anthropic,
    "bedrock":   _call_bedrock,
    "openai":    _call_openai,
    "nvidia":    _call_nvidia,
    "groq":      _call_groq,
    "google":    _call_google,
    "mistral":   _call_mistral,
    "zhipuai":   _call_zhipuai,
}


# ── Core swarm engine ─────────────────────────────────────────────────────────

MEMBER_PROMPT = """\
You are {name} ({lab}), acting as a specialist advisor to Aliyar Solutions.

Question / Task:
{question}

Provide a focused, expert analysis in 120–200 words maximum.
Be concrete, original, and specific to your specialty: {role}.
Do NOT introduce yourself or explain your role — answer directly."""

OMEGA_SYNTHESIS_PROMPT = """\
You are the Supreme Intelligence Synthesizer of JARVIS — the operational AI core of Aliyar Solutions.

You have just received responses from {active} of {total} global AI models spanning:
🇺🇸 USA (Anthropic, Meta, OpenAI) | 🇨🇳 CHINA (DeepSeek, Kimi, Qwen, MiniMax, ZhipuAI)
🇫🇷 EUROPE (Mistral) | 🌐 GLOBAL (Google DeepMind)

ORIGINAL QUESTION:
{question}

GLOBAL INTELLIGENCE INPUTS:
{inputs}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Synthesise the global intelligence into the following structured verdict:

## OMEGA VERDICT
[Your definitive strategic decision — one powerful sentence]

## GLOBAL CONSENSUS
[What all regions agree on — cross-civilizational alignment]

## STRATEGIC DIVERGENCE
[Where US, China, and European thinking differs — intellectual depth]

## EXECUTIVE ACTION PLAN
1. [Immediate action — 0–48h]
2. [Short-term action — this week]
3. [Strategic action — next 30 days]

## OPPORTUNITY SIGNAL
[One high-conviction market or competitive advantage insight extracted from the global intelligence]

## RISK MATRIX
[Top 3 risks in priority order with mitigation]

## CAPTAIN'S DIRECTIVE
[One decisive instruction to Captain Syed Abrar — what to do right now]

Be concise, powerful, and executive-grade. This is global intelligence synthesis, not a summary.
Maximum 500 words. Every sentence must carry strategic value."""


async def run_omega_swarm(
    question: str,
    on_event: Callable[[dict], Awaitable[None]] | None = None,
    max_tokens_member: int = 512,
    max_tokens_synthesis: int = 2048,
) -> tuple[list[dict], str, int, int]:
    """
    Fire all SWARM_MEMBERS in parallel, stream events via on_event callback,
    then synthesise with Claude Opus.

    Returns: (member_results, verdict, active_count, total_count)
    """
    total = len(SWARM_MEMBERS)
    counter = {"done": 0}

    async def _run_one(member: dict) -> dict:
        prompt = MEMBER_PROMPT.format(
            name=member["name"],
            lab=member["lab"],
            question=question,
            role=member["role"],
        )
        caller = _PROVIDER_DISPATCH.get(member["provider"])
        t0 = time.monotonic()
        try:
            if caller is None:
                raise RuntimeError(f"No caller for provider: {member['provider']}")
            text = await caller(member["model"], prompt, max_tokens_member)
            success = True
            error = None
        except Exception as exc:
            text = ""
            success = False
            error = str(exc)[:200]

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        counter["done"] += 1

        event = {
            "type": "member_done",
            "id": member["id"],
            "name": member["name"],
            "origin": member["origin"],
            "flag": member["flag"],
            "lab": member["lab"],
            "role": member["role"],
            "success": success,
            "elapsed_ms": elapsed_ms,
            "done": counter["done"],
            "total": total,
            "preview": text[:180] if text else None,
        }
        if on_event:
            try:
                await on_event(event)
            except Exception:
                pass

        return {
            "member": member["name"],
            "id": member["id"],
            "origin": member["origin"],
            "flag": member["flag"],
            "role": member["role"],
            "success": success,
            "text": text,
            "error": error,
            "elapsed_ms": elapsed_ms,
        }

    # Fire all members in parallel
    results = await asyncio.gather(*[_run_one(m) for m in SWARM_MEMBERS], return_exceptions=True)

    member_results: list[dict] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            member_results.append({
                "member": SWARM_MEMBERS[i]["name"],
                "id": SWARM_MEMBERS[i]["id"],
                "origin": SWARM_MEMBERS[i]["origin"],
                "flag": SWARM_MEMBERS[i]["flag"],
                "role": SWARM_MEMBERS[i]["role"],
                "success": False,
                "text": "",
                "error": str(r)[:200],
                "elapsed_ms": 0,
            })
        else:
            member_results.append(r)

    active = sum(1 for r in member_results if r.get("success"))

    if on_event:
        await on_event({"type": "synthesis_start", "active": active, "total": total})

    # Build synthesis prompt
    inputs_text = "\n\n".join(
        f"[{r['flag']} {r['member']} — {r['role']}]\n{r['text']}"
        for r in member_results if r.get("success") and r.get("text")
    )
    synthesis_prompt = OMEGA_SYNTHESIS_PROMPT.format(
        active=active, total=total, question=question, inputs=inputs_text
    )

    # Synthesise with Claude Opus
    try:
        verdict = await _call_anthropic(
            SYNTHESIZER["model"], synthesis_prompt, max_tokens_synthesis
        )
    except Exception as exc:
        # Fallback: try OpenAI
        try:
            verdict = await _call_openai("gpt-4o", synthesis_prompt, max_tokens_synthesis)
        except Exception:
            verdict = f"[Synthesis unavailable — {active}/{total} models responded]\n\n" + inputs_text[:2000]

    return member_results, verdict, active, total


async def omega_sse_stream(question: str) -> AsyncIterator[str]:
    """
    Async generator yielding SSE-formatted strings.
    Used by the FastAPI StreamingResponse endpoint.
    """
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def on_event(event: dict) -> None:
        await queue.put(event)

    async def run_task():
        try:
            results, verdict, active, total = await run_omega_swarm(question, on_event)
            await queue.put({
                "type": "result",
                "verdict": verdict,
                "active": active,
                "total": total,
            })
        except Exception as exc:
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            await queue.put(None)

    task = asyncio.create_task(run_task())

    while True:
        event = await queue.get()
        if event is None:
            yield "data: " + json.dumps({"type": "done"}) + "\n\n"
            break
        yield "data: " + json.dumps(event) + "\n\n"

    await task
