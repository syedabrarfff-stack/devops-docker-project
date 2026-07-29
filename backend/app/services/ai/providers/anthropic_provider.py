from typing import List
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message
from app.core.config import settings


class AnthropicProvider(BaseAIProvider):
    name = "anthropic"
    # Captain directive: Haiku 4.5 and Sonnet 4.6 ONLY — never Opus
    models = {
        "claude-sonnet": "claude-sonnet-4-6",
        "claude-haiku":  "claude-haiku-4-5-20251001",
    }
    # Hard block: reject any attempt to use Opus through this provider
    _BLOCKED_MODELS = {"claude-opus", "claude-opus-4", "claude-opus-4-7", "claude-opus-4-8"}

    def is_available(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "claude-sonnet-4-6",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        # Enforce Captain's directive: Haiku 4.5 / Sonnet 4.6 only
        if model_id in self._BLOCKED_MODELS or "opus" in model_id.lower():
            model_id = "claude-sonnet-4-6"
        try:
            import anthropic
            # Python's ssl module respects SSL_CERT_FILE env var set at container start
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            result = await client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            )
            return AIResponse(
                content=result.content[0].text,
                model=model_id,
                provider=self.name,
                task_type="general",
                tokens_used=result.usage.input_tokens + result.usage.output_tokens,
            )
        except Exception as e:
            return AIResponse(content="", model=model_id, provider=self.name,
                              task_type="general", error=str(e))
