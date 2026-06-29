"""
JARVIS OMEGA — Global Intelligence Swarm API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST /omega/ignite          — fire global swarm, stream SSE
GET  /omega/members         — list all 16 swarm members with origin / status
GET  /omega/pulse           — quick system capability overview
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.services.omega.swarm import omega_sse_stream, SWARM_MEMBERS, SYNTHESIZER, OMEGA_SWARM

router = APIRouter(prefix="/omega", tags=["OMEGA Global Swarm"])


class IgniteRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=8000)


@router.post("/ignite")
@limiter.limit("3/minute")
async def ignite_swarm(request: Request, body: IgniteRequest):
    """
    Fire the OMEGA global swarm and stream SSE events.

    Stream protocol:
      data: {"type":"member_done","name":"...","origin":"...","success":true,"done":3,"total":15,...}
      data: {"type":"synthesis_start","active":13,"total":15}
      data: {"type":"result","verdict":"...","active":13,"total":15}
      data: {"type":"done"}
    """
    return StreamingResponse(
        omega_sse_stream(body.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/members")
async def list_members():
    """List all OMEGA swarm members with their origin and capability profile."""
    members = []
    for m in OMEGA_SWARM:
        members.append({
            "id": m["id"],
            "name": m["name"],
            "origin": m["origin"],
            "flag": m["flag"],
            "lab": m["lab"],
            "role": m["role"],
            "provider": m["provider"],
            "is_synthesizer": m.get("synthesizer", False),
        })
    return {
        "total": len(members),
        "swarm_size": len(SWARM_MEMBERS),
        "synthesizer": SYNTHESIZER["name"],
        "members": members,
        "regions": {
            "USA":    sum(1 for m in SWARM_MEMBERS if m["origin"] == "USA"),
            "CHINA":  sum(1 for m in SWARM_MEMBERS if m["origin"] == "CHINA"),
            "EUROPE": sum(1 for m in SWARM_MEMBERS if m["origin"] == "EUROPE"),
            "GLOBAL": sum(1 for m in SWARM_MEMBERS if m["origin"] == "GLOBAL"),
        },
    }


@router.get("/pulse")
async def omega_pulse():
    """Quick capability overview — no live API calls."""
    from app.core.config import settings

    nim_keys = sum(1 for attr in [
        "NVIDIA_API_KEY", "NVIDIA_API_KEY_B", "NVIDIA_API_KEY_C", "NVIDIA_API_KEY_D",
        "NVIDIA_API_KEY_E", "NVIDIA_API_KEY_F", "NVIDIA_API_KEY_G", "NVIDIA_API_KEY_H",
        "NVIDIA_API_KEY_I", "NVIDIA_API_KEY_J",
    ] if getattr(settings, attr, None) and getattr(settings, attr, "").startswith("nvapi-"))

    nim_models = [
        "Llama 4 Maverick", "Llama 4 Scout", "DeepSeek V4 Pro",
        "DeepSeek V4 Flash", "Kimi K2.6", "Qwen 2.5 Coder",
        "MiniMax M3", "Mistral Medium 3", "Llama 3.3 70B",
    ]

    return {
        "system": "JARVIS OMEGA Global Intelligence Swarm",
        "version": "1.0",
        "swarm_size": len(SWARM_MEMBERS),
        "synthesizer": SYNTHESIZER["name"],
        "capability": {
            "anthropic":  bool(getattr(settings, "ANTHROPIC_API_KEY", None)),
            "openai":     bool(getattr(settings, "OPENAI_API_KEY", None)),
            "google":     bool(getattr(settings, "GOOGLE_API_KEY", None) or getattr(settings, "GEMINI_API_KEY", None)),
            "groq":       bool(getattr(settings, "GROQ_API_KEY", None)),
            "mistral":    bool(getattr(settings, "MISTRAL_API_KEY", None)),
            "zhipuai":    bool(getattr(settings, "ZHIPUAI_API_KEY", None)),
            "nvidia_nim": nim_keys,
            "nim_models": nim_models if nim_keys else [],
        },
        "regions": {
            "USA":    {"models": 6, "providers": ["Anthropic", "OpenAI", "Meta/Groq", "Meta/NIM"]},
            "CHINA":  {"models": 6, "providers": ["DeepSeek", "MoonshotAI", "Alibaba", "MiniMax", "ZhipuAI"]},
            "EUROPE": {"models": 2, "providers": ["Mistral AI"]},
            "GLOBAL": {"models": 2, "providers": ["Google DeepMind"]},
        },
        "streaming": "SSE via POST /omega/ignite",
    }
