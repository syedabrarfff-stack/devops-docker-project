from typing import List
import httpx
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message
from app.core.config import settings


class GroqProvider(BaseAIProvider):
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"
    models = {
        "llama-3-3": "llama-3.3-70b-versatile",
        "llama-4-scout": "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-4": "meta-llama/llama-4-maverick-17b-128e-instruct",
    }

    def is_available(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "llama-3.3-70b-versatile",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend([{"role": m.role, "content": m.content} for m in messages])
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
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


class MistralProvider(BaseAIProvider):
    name = "mistral"
    base_url = "https://api.mistral.ai/v1"
    models = {"mistral-large": "mistral-large-latest"}

    def is_available(self) -> bool:
        return bool(settings.MISTRAL_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "mistral-large-latest",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend([{"role": m.role, "content": m.content} for m in messages])
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
                    json={"model": model_id, "messages": msgs, "max_tokens": max_tokens},
                )
                data = r.json()
            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                model=model_id, provider=self.name, task_type="general",
            )
        except Exception as e:
            return AIResponse(content="", model=model_id, provider=self.name,
                              task_type="general", error=str(e))
