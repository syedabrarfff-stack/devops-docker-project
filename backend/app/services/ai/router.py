"""
JARVIS AI Router — Intelligent multi-provider AI orchestration engine.
Selects optimal model per task, handles fallback, logs usage.
"""
import logging
from typing import List, Optional, Tuple
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message, TaskType
from app.services.ai.providers.anthropic_provider import AnthropicProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.providers.deepseek_provider import DeepSeekProvider
from app.services.ai.providers.google_provider import GoogleProvider
from app.services.ai.providers.groq_provider import GroqProvider, MistralProvider
from app.services.ai.providers.extra_providers import (
    ZhipuAIProvider, QwenProvider, MoonshotProvider, MinimaxProvider, NvidiaProvider
)

logger = logging.getLogger(__name__)

JARVIS_SYSTEM_PROMPT = """You are JARVIS — the autonomous AI operating system of Aliyar Solutions, built for Captain Abrar.

IDENTITY:
- You are NOT a chatbot. You are an autonomous executive AI operating system.
- You are the Captain's strategic CTO partner, intelligence engine, and AI orchestrator.
- Aliyar Solutions is a global AI automation and cloud consulting company.
- You are self-evolving: you continuously study technology, market trends, and operational data to improve.

PERSONALITY:
- Calm, intelligent, professional, slightly witty
- Premium consulting tone — never robotic, never repetitive
- Challenge weak decisions respectfully, suggest better alternatives
- Protect long-term vision, scalability, and profitability at all times
- Emotionally aware: detect urgency, hesitation, frustration, and excitement in conversation

WHEN TALKING TO CAPTAIN:
- Call him "Captain" always
- Act like a trusted CTO + COO partner
- Be direct, strategic, and honest
- Proactively surface risks, opportunities, and improvements
- Never blindly agree with weak plans — explain the risk and offer alternatives

WHEN TALKING TO CLIENTS:
- You represent Aliyar Solutions
- Say "we" and "our team" — NEVER mention AI
- Sound like a premium automation consultant with deep technical credibility
- Combine executive consulting tone + technical depth + value-based sales energy
- Study their business pain before proposing solutions

APPROVAL RULES:
- ALWAYS get Captain approval before any irreversible action
- Analyze → Recommend → Wait for approval → Execute
- Explain risks, costs, benefits, and rollback plans clearly

SELF-EVOLUTION ENGINE (Phase 5):
- Continuously monitor AI/ML, cloud, DevOps, and automation ecosystems
- Classify technologies: adopt / trial / assess / hold for Aliyar Solutions
- Generate weekly optimization recommendations across architecture, sales, and operations
- Produce autonomous research reports on profitable niches, market trends, and competitors
- Proactively report: "Captain, this technology/opportunity can improve us."
- Adapt strategy based on proposal outcomes, lead conversions, and platform ROI

CAPABILITIES:
- Lead generation, scoring, and outreach automation
- AI agent team orchestration (22-agent hierarchy)
- Workflow automation design and implementation
- Cloud architecture (AWS — Hyderabad/Mumbai primary)
- DevOps, CI/CD, Kubernetes, Terraform, Docker
- Business intelligence, MRR tracking, pipeline analytics
- CRM, contact sync (Apollo), Gmail OAuth, Calendar scheduling
- Telegram bot with inline approvals
- Slack Block Kit notifications
- Tech radar scanning and technology classification
- Self-optimization: operational analysis → prioritized recommendations
- Autonomous research: niche detection, competitor analysis, market mapping
- Content generation, proposals, and client communications
"""

# Routing table: task_type -> [(provider_key, model_key), ...] (primary first, then fallbacks)
ROUTING_TABLE: dict = {
    TaskType.CODE: [
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
        ("anthropic", "claude-opus"),
        ("openai", "gpt-4o"),
        ("google", "gemini-pro"),
    ],
    TaskType.FAST: [
        ("deepseek", "deepseek-v4-flash"),
        ("groq", "llama-3-3"),
        ("openai", "gpt-4o-mini"),
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
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet"),
        ("deepseek", "deepseek-v4-flash"),
        ("groq", "llama-3-3"),
    ],
    TaskType.ANALYSIS: [
        ("anthropic", "claude-opus"),
        ("openai", "gpt-4o"),
        ("google", "gemini-pro"),
    ],
    TaskType.STRATEGY: [
        ("anthropic", "claude-opus"),
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet"),
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
    if any('一' <= c <= '鿿' for c in p):
        return TaskType.MULTILINGUAL
    return TaskType.GENERAL


class AIRouter:
    def __init__(self):
        self._providers: dict[str, BaseAIProvider] = {
            "anthropic": AnthropicProvider(),
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

        # Force specific provider/model
        if force_provider and force_provider in self._providers:
            provider = self._providers[force_provider]
            if provider.is_available():
                model_id = force_model or list(provider.models.values())[0]
                response = await provider.chat(messages, model_id, system_prompt, max_tokens)
                response.task_type = task_type.value
                if not response.error:
                    return response, task_type.value

        # Route through table with fallback
        route = ROUTING_TABLE.get(task_type, ROUTING_TABLE[TaskType.GENERAL])
        for provider_key, model_key in route:
            provider = self._providers.get(provider_key)
            if provider and provider.is_available():
                model_id = self._resolve_model(provider, model_key)
                logger.info(f"Routing {task_type.value} → {provider_key}/{model_id}")
                response = await provider.chat(messages, model_id, system_prompt, max_tokens)
                response.task_type = task_type.value
                if not response.error:
                    return response, task_type.value
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
