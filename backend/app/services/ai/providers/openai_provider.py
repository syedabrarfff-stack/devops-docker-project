from typing import List
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message
from app.core.config import settings


class OpenAIProvider(BaseAIProvider):
    name = "openai"
    models = {
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "dalle-3": "dall-e-3",
        "whisper": "whisper-1",
    }

    def is_available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "gpt-4o",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend([{"role": m.role, "content": m.content} for m in messages])
            result = await client.chat.completions.create(
                model=model_id, messages=msgs, max_tokens=max_tokens
            )
            return AIResponse(
                content=result.choices[0].message.content,
                model=model_id, provider=self.name, task_type="general",
                tokens_used=result.usage.total_tokens,
            )
        except Exception as e:
            return AIResponse(content="", model=model_id, provider=self.name,
                              task_type="general", error=str(e))
