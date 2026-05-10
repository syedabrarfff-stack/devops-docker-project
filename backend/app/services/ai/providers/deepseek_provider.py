from typing import List
import httpx
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message
from app.core.config import settings


class DeepSeekProvider(BaseAIProvider):
    name = "deepseek"
    base_url = "https://api.deepseek.com"
    models = {
        "deepseek-v3": "deepseek-chat",
        "deepseek-v4-pro": "deepseek-reasoner",
        "deepseek-v4-flash": "deepseek-chat",
    }

    def is_available(self) -> bool:
        return bool(settings.DEEPSEEK_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "deepseek-chat",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend([{"role": m.role, "content": m.content} for m in messages])
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
                    json={"model": model_id, "messages": msgs, "max_tokens": max_tokens},
                )
                data = r.json()
            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                model=model_id, provider=self.name, task_type="general",
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
            )
        except Exception as e:
            return AIResponse(content="", model=model_id, provider=self.name,
                              task_type="general", error=str(e))
