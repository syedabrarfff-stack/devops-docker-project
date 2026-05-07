from typing import List
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message
from app.core.config import settings


class GoogleProvider(BaseAIProvider):
    name = "google"
    models = {
        "gemini-pro": "gemini-1.5-pro",
        "gemini-flash": "gemini-1.5-flash",
        "gemini-2": "gemini-2.0-flash",
    }

    def is_available(self) -> bool:
        return bool(settings.GOOGLE_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "gemini-1.5-pro",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel(model_name=model_id, system_instruction=system_prompt or None)
            prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
            result = await model.generate_content_async(prompt)
            return AIResponse(
                content=result.text,
                model=model_id, provider=self.name, task_type="general",
            )
        except Exception as e:
            return AIResponse(content="", model=model_id, provider=self.name,
                              task_type="general", error=str(e))
