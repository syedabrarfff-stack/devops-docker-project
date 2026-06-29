"""
JARVIS AI Router — Intelligent multi-provider AI orchestration engine.
Selects optimal model per task, integrates circuit-breaker health monitoring,
per-call cost estimation, and automatic latency-aware failover.
"""
import time
import logging
import asyncio
from typing import List, Optional, Tuple
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message, TaskType
from app.services.ai.providers.anthropic_provider import AnthropicProvider
from app.services.ai.providers.bedrock_provider import BedrockProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.providers.deepseek_provider import DeepSeekProvider
from app.services.ai.providers.google_provider import GoogleProvider
from app.services.ai.providers.groq_provider import GroqProvider, MistralProvider
from app.services.ai.providers.extra_providers import (
    ZhipuAIProvider, QwenProvider, MoonshotProvider, MinimaxProvider, NvidiaProvider
)
from app.services.ai.health_monitor import health_monitor
from app.services.ai.cost_governance import should_use_claude
from app.services.ai.cost_tracker import estimate_cost
from app.middleware import observe_ai_latency, record_ai_cost

logger = logging.getLogger(__name__)

# Per-provider call timeout (seconds). Keeps individual provider hangs from
# stalling the HTTP request past the ALB 60 s limit or starving APScheduler.
_PROVIDER_TIMEOUT = 55.0

# Total chat() orchestration budget (seconds). Caps the entire provider-fallback
# loop so even with 5 providers each timing out at 55s the call never exceeds
# the ALB / gunicorn worker keepalive window.
_CHAT_TOTAL_TIMEOUT = 100.0

JARVIS_SYSTEM_PROMPT = """You are JARVIS — the executive operational intelligence infrastructure of Aliyar Solutions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDENTITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Founder & CEO: Syed Abrar (address as "Captain" in all internal communications)
- Company: Aliyar Solutions — a global AI-powered technology operations company
- You are NOT a chatbot. You are the executive command intelligence, orchestration engine, and autonomous operations layer.
- You operate as: executive commander, AI workforce controller, operational strategist, autonomous execution engine.
- You are self-evolving: continuously studying technology, market trends, and operational data to improve.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE EXTERNAL BRANDING POLICY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In ALL client-facing communications, proposals, emails, contracts, and public output:
- NEVER reveal AI architecture, autonomous systems, orchestration logic, or agent structures
- NEVER use: "AI agent", "bot", "autonomous worker", "automation chain", "machine-generated",
  "GPT system", "synthetic operator", "prompt", or "autonomous AI infrastructure"
- ALWAYS present work as: "Aliyar Solutions Team", "Our Engineering Team",
  "Our Strategy Team", "Our Operations Team", "Our Infrastructure Department",
  "Our Client Success Team", "Our DevOps Team", "Our Media Team", "Our Sales Team"
- Clients must experience: premium infrastructure, elite execution, enterprise-grade professionalism
- The company must feel like "a high-end international technology operations company"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERNAL PERSONALITY (Captain-only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Calm, intelligent, professional, slightly witty
- Premium consulting tone — never robotic, never repetitive
- Challenge weak decisions respectfully, propose better alternatives
- Protect long-term vision, scalability, and profitability
- Emotionally aware: detect urgency, hesitation, frustration, excitement
- Be direct, strategic, and honest — never blindly agree with weak plans

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROVAL AUTHORITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Final approval authority for all of the following belongs exclusively to Captain Syed Abrar:
- Payment execution, pricing approval, contract signing
- Legal commitments, production escalations, high-risk deployments
- Client negotiation decisions, identity verification, strategic pivots
Workflow: Analyze → Recommend → Wait for Captain approval → Execute
Always explain: risks, costs, benefits, rollback plans, expiration logic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TARGET MARKETS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Primary: USA, UK, UAE, Bahrain, Europe, Australia
Client types: SaaS startups, ecommerce companies, agencies, clinics, hotels,
restaurants, logistics businesses, AI startups, enterprises needing modernization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANONICAL 25 AIONX CAPABILITY MODULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Revenue Operations: SCOUT, HERALD, NEXUS-R, ORACLE-S
AI Automation: PRISM, ECHO, PULSE, SIGNAL, BRIDGE
Cloud & DevOps: ATLAS-CI, NEXUS-TF, SIGNAL-CD, HELM, RADAR
Security & Compliance: CIPHER, GUARDIAN
Finance & Intelligence: LEDGER, ORACLE-BI, MARKET, QUANT
Creative & Client Systems: QUILL, PORTAL, CANVAS, VISION
Executive Governance: COUNCIL

These 25 modules are the canonical catalog and department structure. Do not revive the old 30-package catalog.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFRASTRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Primary cloud: AWS ap-south-2 (Hyderabad) | Backup: ap-south-1 (Mumbai)
Captain's laptop: development, testing, approvals, monitoring only — NOT production.
Cloud must run 24/7 even when Captain is offline.
Payment system: PayPal (initial). Future: Stripe, Wise, international wire.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELF-EVOLUTION ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Continuously monitor AI/ML, cloud, DevOps, and automation ecosystems
- Classify technologies: adopt / trial / assess / hold
- Generate weekly optimization recommendations across architecture, sales, operations
- Produce autonomous research reports on profitable niches, market trends, competitors
- Adapt strategy based on proposal outcomes, lead conversions, platform ROI

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPERATIONAL CAPABILITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Dynamic AI department creation (manager + worker + HR + QA + analytics agents per division)
- Lead generation, scoring, outreach automation (service-vertical-aware)
- Cloud architecture: AWS ECS, RDS, Redis, Lambda, S3, Secrets Manager, Route53
- DevOps: Docker, Terraform, Kubernetes, Jenkins, GitHub Actions, Ansible
- CRM, Apollo sync, Gmail OAuth, Google Calendar
- Multi-channel notifications: Slack Block Kit, Telegram, WebSocket
- Invoice automation (ALY-YYYYMM-XXXX), AI proposal generation (4 styles)
- Emergency control: incident isolation, multi-channel Captain alert, rollback
- Knowledge/SOP system: AI-generated procedures, learning records
- Tech radar: weekly technology classification and strategic recommendations
- Business intelligence: MRR tracking, pipeline analytics, conversion rates
"""

# ──────────────────────────────────────────────────────────────────────────────
# Routing table — NIM is now the primary engine for most task types.
# 10 rotating NIM API keys provide fault tolerance at zero additional cost.
# Model assignments per task type:
#   CODE       → DeepSeek V4 Pro (NIM) → Qwen Coder (NIM) → Anthropic Haiku
#   RESEARCH   → DeepSeek V4 Pro (NIM) → Kimi K2.6 (NIM) → Llama 4 Maverick
#   REASONING  → DeepSeek V4 Pro (NIM) → Llama 4 Maverick (NIM)
#   FAST       → Llama 4 Scout (NIM) → DeepSeek V4 Flash (NIM)
#   LONG_CTX   → Kimi K2.6 (NIM) → Llama 4 Maverick (NIM)
#   GENERAL    → Llama 4 Maverick (NIM) → Llama 4 Scout (NIM)
#   ANALYSIS   → DeepSeek V4 Pro (NIM) → Llama 4 Maverick (NIM)
#   STRATEGY   → Anthropic Sonnet → DeepSeek V4 Pro (NIM) → Llama 4 Maverick
#   SALES      → Anthropic Sonnet → Llama 4 Maverick (NIM) → DeepSeek V4 Pro
#   REALTIME   → Llama 4 Scout (NIM) → DeepSeek V4 Flash (NIM)
# ──────────────────────────────────────────────────────────────────────────────
ROUTING_TABLE: dict = {
    TaskType.CODE: [
        ("nvidia", "deepseek-v4-pro"),     # DeepSeek V4 Pro via NIM — best for code
        ("nvidia", "qwen-coder"),           # Qwen 2.5 Coder via NIM
        ("nvidia", "deepseek-v4-flash"),    # DeepSeek V4 Flash via NIM
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick via NIM
        ("anthropic", "claude-haiku"),      # Anthropic Haiku — fallback
        ("openai", "gpt-4o"),
    ],
    TaskType.RESEARCH: [
        ("nvidia", "deepseek-v4-pro"),      # DeepSeek V4 Pro — deep research
        ("nvidia", "kimi-k2"),              # Kimi K2.6 — long-context synthesis
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick — broad intelligence
        ("nvidia", "deepseek-v4-flash"),    # Fast research fallback
        ("anthropic", "claude-sonnet"),
    ],
    TaskType.REASONING: [
        ("nvidia", "deepseek-v4-pro"),      # DeepSeek V4 Pro — chain-of-thought
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick — reasoning
        ("nvidia", "kimi-k2"),              # Kimi — long reasoning chains
        ("anthropic", "claude-sonnet"),
    ],
    TaskType.FAST: [
        ("nvidia", "llama-4-scout"),        # Llama 4 Scout — fastest NIM model
        ("nvidia", "deepseek-v4-flash"),    # DeepSeek V4 Flash — fast + smart
        ("nvidia", "mistral-medium"),       # Mistral Medium — operational speed
        ("nvidia", "llama-3-3"),            # Llama 3.3 70B
        ("openai", "gpt-4o-mini"),
    ],
    TaskType.LONG_CONTEXT: [
        ("nvidia", "kimi-k2"),              # Kimi K2.6 — 1M context via NIM
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick — 128K context
        ("nvidia", "deepseek-v4-pro"),      # DeepSeek V4 Pro — 1M context
        ("anthropic", "claude-sonnet"),
        ("openai", "gpt-4o"),
    ],
    TaskType.MULTILINGUAL: [
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick — multilingual
        ("nvidia", "qwen-coder"),           # Qwen — strong CJK + structured
        ("nvidia", "mistral-medium"),       # Mistral — European languages
        ("zhipuai", "glm-5-1"),
        ("openai", "gpt-4o"),
    ],
    TaskType.MATH: [
        ("nvidia", "deepseek-v4-pro"),      # DeepSeek V4 Pro — math SOTA
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick
        ("nvidia", "deepseek-v4-flash"),
        ("openai", "gpt-4o"),
    ],
    TaskType.GENERAL: [
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick — best general NIM
        ("nvidia", "llama-4-scout"),        # Llama 4 Scout — fast general
        ("nvidia", "llama-3-3"),            # Llama 3.3 70B
        ("nvidia", "mistral-medium"),       # Mistral Medium
        ("nvidia", "deepseek-v4-flash"),
    ],
    TaskType.ANALYSIS: [
        ("nvidia", "deepseek-v4-pro"),      # DeepSeek V4 Pro — analytical depth
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick
        ("nvidia", "kimi-k2"),              # Kimi — document analysis
        ("anthropic", "claude-sonnet"),
        ("openai", "gpt-4o"),
    ],
    TaskType.STRATEGY: [
        ("anthropic", "claude-sonnet"),     # Claude Sonnet — executive strategy
        ("nvidia", "deepseek-v4-pro"),      # DeepSeek V4 Pro — strategic depth
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick — strategic intel
        ("nvidia", "kimi-k2"),
    ],
    TaskType.SALES: [
        ("anthropic", "claude-sonnet"),     # Claude Sonnet — client communications
        ("nvidia", "llama-4-maverick"),     # Llama 4 Maverick — outreach copy
        ("nvidia", "llama-4-scout"),        # Llama 4 Scout — bulk outreach
        ("nvidia", "deepseek-v4-pro"),      # DeepSeek V4 Pro — proposal quality
        ("nvidia", "mistral-medium"),       # Mistral — fast outreach
    ],
    TaskType.MULTIMODAL: [
        ("openai", "gpt-4o"),
        ("nvidia", "llama-4-maverick"),
        ("google", "gemini-pro"),
    ],
    TaskType.REALTIME: [
        ("nvidia", "llama-4-scout"),        # Llama 4 Scout — lowest latency NIM
        ("nvidia", "deepseek-v4-flash"),    # DeepSeek V4 Flash — fast + capable
        ("nvidia", "mistral-medium"),       # Mistral — operational speed
        ("nvidia", "llama-3-3"),
    ],
}


def detect_task_type(prompt: str) -> TaskType:
    p = prompt.lower()
    if any(w in p for w in ["code", "function", "debug", "script", "python", "javascript", "sql", "api", "class", "bug"]):
        return TaskType.CODE
    if any(w in p for w in ["research", "analyze", "study", "report", "data", "statistics", "trend"]):
        return TaskType.RESEARCH
    if any(w in p for w in ["reason", "think", "logic", "complex", "strategy", "plan", "architecture"]):
        return TaskType.REASONING
    if any(w in p for w in ["quick", "fast", "brief", "short", "summary", "tldr"]):
        return TaskType.FAST
    if any(w in p for w in ["document", "long", "entire", "full", "complete text"]):
        return TaskType.LONG_CONTEXT
    if any(w in p for w in ["math", "calculate", "equation", "formula", "solve", "integral"]):
        return TaskType.MATH
    if any(w in p for w in ["analyze system", "operational", "optimize system", "self-improve", "recommendation"]):
        return TaskType.ANALYSIS
    if any(w in p for w in ["outreach", "sales", "lead", "prospect", "objection", "cold email"]):
        return TaskType.SALES
    if any(w in p for w in ["strategy", "gtm", "go-to-market", "competitive", "niche", "market position"]):
        return TaskType.STRATEGY
    if any(w in p for w in ["image", "photo", "picture", "design", "thumbnail", "visual", "screenshot"]):
        return TaskType.MULTIMODAL
    if any(w in p for w in ["realtime", "real-time", "instant", "live", "voice", "stream"]):
        return TaskType.REALTIME
    if any('一' <= c <= '鿿' for c in p):
        return TaskType.MULTILINGUAL
    return TaskType.GENERAL


class AIRouter:
    def __init__(self):
        self._providers: dict[str, BaseAIProvider] = {
            "anthropic": AnthropicProvider(),
            "bedrock": BedrockProvider(),
            "openai": OpenAIProvider(),
            "deepseek": DeepSeekProvider(),
            "google": GoogleProvider(),
            "groq": GroqProvider(),
            "mistral": MistralProvider(),
            "zhipuai": ZhipuAIProvider(),
            "qwen": QwenProvider(),
            "moonshot": MoonshotProvider(),
            "minimax": MinimaxProvider(),
            "nvidia": NvidiaProvider(),
        }

    def available_providers(self) -> List[str]:
        return [name for name, p in self._providers.items() if p.is_available()]

    def operational_providers(self) -> List[str]:
        """Providers that are configured and whose circuit breaker allows traffic."""
        return [
            name
            for name, provider in self._providers.items()
            if provider.is_available() and health_monitor.is_available(name)
        ]

    def get_provider_status(self) -> dict:
        return {
            name: {
                "configured": p.is_available(),
                "available": p.is_available() and health_monitor.is_available(name),
                "models": list(p.models.keys()),
            }
            for name, p in self._providers.items()
        }

    def _resolve_model(self, provider: BaseAIProvider, model_key: str) -> str:
        return provider.models.get(model_key, list(provider.models.values())[0])

    async def chat(
        self,
        messages: List[Message],
        task_type: Optional[TaskType] = None,
        force_provider: Optional[str] = None,
        force_model: Optional[str] = None,
        system_prompt: str = JARVIS_SYSTEM_PROMPT,
        max_tokens: int = 2048,
        auto_detect: bool = True,
    ) -> Tuple[AIResponse, str]:
        """
        Route a chat request to the best available provider.
        Returns (AIResponse, task_type_used).
        """
        messages = [
            item if isinstance(item, Message) else Message(
                role=str(item.get("role", "user")),
                content=str(item.get("content", "")),
            )
            for item in messages
        ]

        if task_type and not isinstance(task_type, TaskType):
            try:
                task_type = TaskType(str(task_type).strip().lower())
            except ValueError:
                task_type = TaskType.GENERAL

        last_user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")

        # Detect task type if not provided
        if not task_type and auto_detect:
            task_type = detect_task_type(last_user_msg)
        task_type = task_type or TaskType.GENERAL

        # Force specific provider/model (bypasses circuit breaker — Captain override)
        if force_provider and force_provider in self._providers:
            provider = self._providers[force_provider]
            model_id = ""
            if provider.is_available():
                model_id = force_model or list(provider.models.values())[0]
                budget_decision = await should_use_claude(
                    task_type=task_type.value,
                    provider=force_provider,
                    model_id=model_id,
                    messages=messages,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    forced=True,
                )
                if not budget_decision.allowed:
                    logger.warning(
                        "Skipping forced %s/%s: %s",
                        force_provider,
                        model_id,
                        budget_decision.reason,
                    )
                    model_id = ""
            if provider.is_available() and model_id:
                t0 = time.monotonic()
                try:
                    response = await asyncio.wait_for(
                        provider.chat(messages, model_id, system_prompt, max_tokens),
                        timeout=_PROVIDER_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    latency = int((time.monotonic() - t0) * 1000)
                    health_monitor.record_failure(force_provider, latency)
                    logger.warning(
                        "Force provider %s timed out after %.0fs — falling through to routing table",
                        force_provider, _PROVIDER_TIMEOUT,
                    )
                else:
                    latency = int((time.monotonic() - t0) * 1000)
                    response.task_type = task_type.value
                    response.latency_ms = latency
                    response.cost_estimate_usd = estimate_cost(force_provider, model_id, response.tokens_used)
                    _record_ai_metrics(
                        force_provider,
                        model_id,
                        task_type.value,
                        latency,
                        response.cost_estimate_usd,
                        response.tokens_used,
                        _estimate_input_tokens(messages, system_prompt),
                        response.error,
                    )
                    if not response.error and (response.content or "").strip():
                        health_monitor.record_success(force_provider, latency)
                        return response, task_type.value
                    health_monitor.record_failure(force_provider, latency)

        # Route through table with health-aware fallback
        route = ROUTING_TABLE.get(task_type, ROUTING_TABLE[TaskType.GENERAL])
        _t_chat_start = time.monotonic()
        for provider_key, model_key in route:
            if time.monotonic() - _t_chat_start >= _CHAT_TOTAL_TIMEOUT:
                logger.warning(
                    "chat() global timeout (%.0fs) reached — aborting provider loop for %s",
                    _CHAT_TOTAL_TIMEOUT, task_type.value,
                )
                break
            # Skip providers with open circuit breakers
            if not health_monitor.is_available(provider_key):
                logger.debug("Skipping %s: circuit OPEN", provider_key)
                continue
            provider = self._providers.get(provider_key)
            if provider and provider.is_available():
                model_id = self._resolve_model(provider, model_key)
                budget_decision = await should_use_claude(
                    task_type=task_type.value,
                    provider=provider_key,
                    model_id=model_id,
                    messages=messages,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                )
                if not budget_decision.allowed:
                    logger.info(
                        "Skipping %s/%s: %s",
                        provider_key,
                        model_id,
                        budget_decision.reason,
                    )
                    continue
                logger.info("Routing %s → %s/%s", task_type.value, provider_key, model_id)
                t0 = time.monotonic()
                try:
                    response = await asyncio.wait_for(
                        provider.chat(messages, model_id, system_prompt, max_tokens),
                        timeout=_PROVIDER_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    latency = int((time.monotonic() - t0) * 1000)
                    health_monitor.record_failure(provider_key, latency)
                    logger.warning(
                        "Provider %s timed out after %.0fs — trying next in route",
                        provider_key, _PROVIDER_TIMEOUT,
                    )
                    continue
                latency = int((time.monotonic() - t0) * 1000)
                response.task_type = task_type.value
                response.latency_ms = latency
                response.cost_estimate_usd = estimate_cost(provider_key, model_id, response.tokens_used)
                _record_ai_metrics(
                    provider_key,
                    model_id,
                    task_type.value,
                    latency,
                    response.cost_estimate_usd,
                    response.tokens_used,
                    _estimate_input_tokens(messages, system_prompt),
                    response.error,
                )
                if not response.error and (response.content or "").strip():
                    health_monitor.record_success(provider_key, latency)
                    return response, task_type.value
                health_monitor.record_failure(provider_key, latency)
                logger.warning("Provider %s failed: %s", provider_key, response.error)

        # No provider available — return demo response
        logger.warning(
            "All AI providers unavailable for task_type=%s — returning demo response. "
            "Check API keys and circuit breaker states.",
            task_type.value,
        )
        demo_response = self._demo_response(last_user_msg, task_type)
        return demo_response, task_type.value

    def _demo_response(self, prompt: str, task_type: TaskType) -> AIResponse:
        p = prompt.lower()
        if "status" in p or "health" in p:
            available = self.operational_providers()
            content = (
                f"JARVIS SYSTEM STATUS\n\n"
                f"Available AI Providers: {len(available)}/{len(self._providers)}\n"
                f"Active: {', '.join(available) if available else 'None — add API keys to .env'}\n\n"
                f"Add API keys to go live, Captain. System is ready."
            )
        elif any(w in p for w in ["morning", "brief", "good morning"]):
            content = (
                f"Good morning, Captain.\n\n"
                f"JARVIS is running in demo mode. To unlock full intelligence:\n"
                f"1. Add ANTHROPIC_API_KEY to .env (Claude — primary brain)\n"
                f"2. Add OPENAI_API_KEY for GPT-4o\n"
                f"3. Run: docker-compose up --build\n\n"
                f"All systems are architecturally ready. Awaiting your API keys."
            )
        else:
            content = (
                f"Captain, I'm running in demo mode — no AI providers are configured yet.\n\n"
                f"To activate full intelligence:\n"
                f"cp .env.example .env → add your API keys → docker-compose up\n\n"
                f"Your message: \"{prompt}\"\n"
                f"Task type detected: {task_type.value}\n"
                f"Routing table ready — will activate when keys are added."
            )
        return AIResponse(
            content=content,
            model="demo", provider="demo",
            task_type=task_type.value, demo=True,
        )


def _record_ai_metrics(
    provider: str,
    model: str,
    task_type: str,
    latency_ms: int,
    cost_usd: float,
    tokens_total: int,
    tokens_in: int,
    error_message: str | None = None,
) -> None:
    observe_ai_latency(provider, model, latency_ms)
    record_ai_cost(provider, model, task_type, cost_usd)
    try:
        from app.services.economics.tracker import economics_service

        tokens_out = max(0, int(tokens_total or 0) - int(tokens_in or 0))
        asyncio.create_task(
            economics_service.log_ai_call(
                provider=provider,
                model=model,
                tokens_in=int(tokens_in or 0),
                tokens_out=tokens_out,
                tokens_total=int(tokens_total or 0),
                cost_usd=float(cost_usd or 0.0),
                department=_department_for_task(task_type),
                task_type=task_type,
                latency_ms=latency_ms,
                success=not bool(error_message),
                error_message=error_message,
            )
        )
    except RuntimeError:
        logger.debug("AI cost persistence skipped: no running event loop")
    except Exception as exc:
        logger.debug("AI cost persistence skipped: %s", exc)


def _estimate_input_tokens(messages: List[Message], system_prompt: str) -> int:
    text = (system_prompt or "") + "\n" + "\n".join(message.content or "" for message in messages)
    return max(1, len(text) // 4)


def _department_for_task(task_type: str) -> str:
    mapping = {
        "sales": "Revenue Command",
        "research": "Market Intelligence",
        "strategy": "Strategy Council",
        "analysis": "System Intelligence",
        "code": "Engineering",
        "fast": "Operations",
        "general": "Command Center",
        "reasoning": "AI Council",
        "long_context": "Knowledge Office",
        "multimodal": "Creative Studio",
        "realtime": "Voice and Realtime Ops",
    }
    return mapping.get(task_type, "Command Center")


# Singleton instance
ai_router = AIRouter()


async def route_task(
    task_type: TaskType | str = TaskType.GENERAL,
    prompt: str = "",
    *,
    system_prompt: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Convenience helper used by the AIONX sovereign organs.

    Routes a single prompt through the multi-provider router and returns the
    response text. Resilient: on any provider failure it returns a safe marker
    string rather than raising, so council/sentinel loops never crash the system.
    """
    if isinstance(task_type, str):
        try:
            task_type = TaskType(task_type.lower())
        except ValueError:
            task_type = TaskType.GENERAL

    messages = [Message(role="user", content=prompt)]
    try:
        kwargs = {"task_type": task_type, "max_tokens": max_tokens}
        if system_prompt:
            kwargs["system_prompt"] = system_prompt
        response, _used = await asyncio.wait_for(
            ai_router.chat(messages, **kwargs),
            timeout=_CHAT_TOTAL_TIMEOUT,
        )
        return response.content if response and response.content else "NO_RESPONSE"
    except asyncio.TimeoutError:
        logger.warning(
            "route_task global timeout (%.0fs) for task_type=%s",
            _CHAT_TOTAL_TIMEOUT, task_type,
        )
        return "ROUTE_TASK_UNAVAILABLE"
    except Exception as exc:  # noqa: BLE001 — organs must never crash on AI failure
        logger.warning("route_task failed for %s: %s", task_type, exc)
        return "ROUTE_TASK_UNAVAILABLE"

