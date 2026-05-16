"""
JARVIS AI Router — Intelligent multi-provider AI orchestration engine.
Selects optimal model per task, integrates circuit-breaker health monitoring,
per-call cost estimation, and automatic latency-aware failover.
"""
import time
import logging
from typing import List, Optional, Tuple
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message, TaskType
from app.services.ai.providers.anthropic_provider import AnthropicProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.providers.deepseek_provider import DeepSeekProvider
from app.services.ai.providers.google_provider import GoogleProvider
from app.services.ai.providers.groq_provider import GroqProvider, MistralProvider
from app.services.ai.providers.bedrock_provider import BedrockProvider
from app.services.ai.providers.extra_providers import (
    ZhipuAIProvider, QwenProvider, MoonshotProvider, MinimaxProvider, NvidiaProvider
)
from app.services.ai.health_monitor import health_monitor
from app.services.ai.cost_tracker import estimate_cost

logger = logging.getLogger(__name__)

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
30 SERVICE DIVISIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SALES & MARKETING:
  1. AI Lead Generation Systems       2. AI Outreach Automation
  3. AI Sales Systems                 4. CRM Automation

AI AUTOMATION:
  5. AI Appointment Booking           6. AI Voice Receptionist Systems
  7. Business Workflow Automation     8. Executive Automation Systems

CLOUD & DEVOPS:
  9. DevOps Infrastructure Services   10. AWS Cloud Architecture
 11. Docker Deployments               12. CI/CD Automation
 13. Jenkins Infrastructure           14. Terraform Infrastructure Automation
 15. Ansible Automation               16. Kubernetes Infrastructure
 17. Monitoring & Logging Systems     18. SaaS Deployment Services

SECURITY:
 19. Cybersecurity Operations         20. Vulnerability Assessment

CONTENT & MEDIA:
 21. AI Content Automation            22. YouTube Automation Pipelines
 23. Social Media Management          24. Graphic Design Systems
 25. Video Editing Pipelines

DIGITAL PRODUCTS:
 26. Website Development              27. Client Portal Systems
 28. Operational Dashboards

INTELLIGENCE & ANALYTICS:
 29. AI Research Operations           30. Business Intelligence Analytics

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

# Routing table: task_type -> [(provider_key, model_key), ...] (primary first, then fallbacks)
ROUTING_TABLE: dict = {
    TaskType.CODE: [
        ("bedrock", "bedrock-nova-pro"),
        ("anthropic", "claude-sonnet"),
        ("deepseek", "deepseek-v4-pro"),
        ("openai", "gpt-4o"),
    ],
    TaskType.RESEARCH: [
        ("google", "gemini-pro"),
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet"),
    ],
    TaskType.REASONING: [
        ("bedrock", "bedrock-nova-pro"),
        ("anthropic", "claude-opus"),
        ("openai", "gpt-4o"),
        ("google", "gemini-pro"),
    ],
    TaskType.FAST: [
        ("bedrock", "bedrock-nova-lite"),
        ("deepseek", "deepseek-v4-flash"),
        ("groq", "llama-3-3"),
        ("openai", "gpt-4o-mini"),
        ("nvidia", "nvidia-nim"),
    ],
    TaskType.LONG_CONTEXT: [
        ("google", "gemini-pro"),
        ("moonshot", "kimi-k2"),
        ("anthropic", "claude-sonnet"),
    ],
    TaskType.MULTILINGUAL: [
        ("zhipuai", "glm-5-1"),
        ("qwen", "qwen-turbo"),
        ("openai", "gpt-4o"),
    ],
    TaskType.MATH: [
        ("deepseek", "deepseek-v4-pro"),
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet"),
    ],
    TaskType.GENERAL: [
        ("bedrock", "bedrock-nova-pro"),
        ("openai", "gpt-4o"),
        ("nvidia", "nvidia-nim"),
        ("anthropic", "claude-sonnet"),
        ("deepseek", "deepseek-v4-flash"),
        ("groq", "llama-3-3"),
    ],
    TaskType.ANALYSIS: [
        ("bedrock", "bedrock-nova-pro"),
        ("anthropic", "claude-opus"),
        ("openai", "gpt-4o"),
        ("nvidia", "nvidia-nim"),
        ("google", "gemini-pro"),
    ],
    TaskType.STRATEGY: [
        ("bedrock", "bedrock-nova-pro"),
        ("anthropic", "claude-opus"),
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet"),
    ],
    TaskType.MULTIMODAL: [
        ("openai", "gpt-4o"),         # GPT-4o vision
        ("qwen", "qwen-image"),       # Qwen image editing
        ("google", "gemini-pro"),     # Gemini multimodal
    ],
    TaskType.REALTIME: [
        ("groq", "llama-4-scout"),    # Groq — ultra-low latency
        ("groq", "llama-3-3"),
        ("zhipuai", "glm-4-flash"),   # GLM flash — fast
        ("deepseek", "deepseek-v4-flash"),
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
            "openai": OpenAIProvider(),
            "bedrock": BedrockProvider(),
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

    def get_provider_status(self) -> dict:
        return {
            name: {"available": p.is_available(), "models": list(p.models.keys())}
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
        last_user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")

        # Detect task type if not provided
        if not task_type and auto_detect:
            task_type = detect_task_type(last_user_msg)
        task_type = task_type or TaskType.GENERAL

        # Force specific provider/model (bypasses circuit breaker — Captain override)
        if force_provider and force_provider in self._providers:
            provider = self._providers[force_provider]
            if provider.is_available():
                model_id = force_model or list(provider.models.values())[0]
                t0 = time.monotonic()
                response = await provider.chat(messages, model_id, system_prompt, max_tokens)
                latency = int((time.monotonic() - t0) * 1000)
                response.task_type = task_type.value
                response.latency_ms = latency
                response.cost_estimate_usd = estimate_cost(force_provider, model_id, response.tokens_used)
                if not response.error:
                    health_monitor.record_success(force_provider, latency)
                    return response, task_type.value
                health_monitor.record_failure(force_provider, latency)

        # Route through table with health-aware fallback
        route = ROUTING_TABLE.get(task_type, ROUTING_TABLE[TaskType.GENERAL])
        for provider_key, model_key in route:
            # Skip providers with open circuit breakers
            if not health_monitor.is_available(provider_key):
                logger.debug(f"Skipping {provider_key}: circuit OPEN")
                continue
            provider = self._providers.get(provider_key)
            if provider and provider.is_available():
                model_id = self._resolve_model(provider, model_key)
                logger.info(f"Routing {task_type.value} → {provider_key}/{model_id}")
                t0 = time.monotonic()
                response = await provider.chat(messages, model_id, system_prompt, max_tokens)
                latency = int((time.monotonic() - t0) * 1000)
                response.task_type = task_type.value
                response.latency_ms = latency
                response.cost_estimate_usd = estimate_cost(provider_key, model_id, response.tokens_used)
                if not response.error:
                    health_monitor.record_success(provider_key, latency)
                    return response, task_type.value
                health_monitor.record_failure(provider_key, latency)
                logger.warning(f"Provider {provider_key} failed: {response.error}")

        # No provider available — return demo response
        demo_response = self._demo_response(last_user_msg, task_type)
        return demo_response, task_type.value

    def _demo_response(self, prompt: str, task_type: TaskType) -> AIResponse:
        p = prompt.lower()
        if "status" in p or "health" in p:
            available = self.available_providers()
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


# Singleton instance
ai_router = AIRouter()
