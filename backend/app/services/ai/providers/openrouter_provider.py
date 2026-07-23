"""
OpenRouter Provider — Unified gateway to 100+ models including DeepSeek, Claude, and more.
OpenRouter provides a single endpoint for models across multiple providers with unified billing.
"""
import httpx
from typing import List
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message
from app.core.config import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(BaseAIProvider):
    name = "openrouter"

    # Model mappings for OpenRouter
    models = {
        # DeepSeek models
        "deepseek-r1-distill": "deepseek/deepseek-r1-distill-llama-70b",
        "deepseek-v4-pro": "deepseek/deepseek-v4-pro",
        "deepseek-v4-turbo": "deepseek/deepseek-v4-turbo",

        # Claude models via OpenRouter
        "claude-sonnet": "anthropic/claude-3.5-sonnet",
        "claude-haiku": "anthropic/claude-3.5-haiku",
        "claude-opus": "anthropic/claude-3-opus",
        # Review/refine layer — Opus 4.8 is the system-wide second-pass reviewer
        "claude-opus-4-8": "anthropic/claude-opus-4.8",

        # Llama models
        "llama-90b": "meta-llama/llama-3.1-405b-instruct",
        "llama-70b": "meta-llama/llama-3.1-70b-instruct",

        # Other models
        "mistral-large": "mistralai/mistral-large-2407",
        "gpt-4o": "openai/gpt-4-turbo",
        "gpt-4o-mini": "openai/gpt-4o-mini",
    }

    def is_available(self) -> bool:
        return bool(settings.OPENROUTER_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "deepseek/deepseek-v4-pro",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        """
        Call OpenRouter API with specified model.
        Supports 100+ models across multiple providers with unified interface.
        """
        try:
            import os

            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend([{"role": m.role, "content": m.content} for m in messages])

            # Use CA bundle from environment if available
            ca_cert = os.getenv("SSL_CERT_FILE") or os.getenv("REQUESTS_CA_BUNDLE") or True

            async with httpx.AsyncClient(timeout=60, verify=ca_cert) as client:
                response = await client.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://aliyarsolutions.com",
                        "X-Title": "JARVIS — Aliyar Solutions",
                    },
                    json={
                        "model": model_id,
                        "messages": msgs,
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                        "top_p": 0.95,
                    },
                )

                if response.status_code == 429:
                    return AIResponse(
                        content="", model=model_id, provider=self.name,
                        task_type="general", error="rate_limited"
                    )

                response.raise_for_status()
                data = response.json()

                return AIResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=model_id,
                    provider=self.name,
                    task_type="general",
                    tokens_used=data.get("usage", {}).get("total_tokens", 0),
                )

        except httpx.TimeoutException:
            return AIResponse(
                content="", model=model_id, provider=self.name,
                task_type="general", error="timeout"
            )
        except Exception as e:
            return AIResponse(
                content="", model=model_id, provider=self.name,
                task_type="general", error=str(e)
            )
