import httpx
from typing import List
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message
from app.core.config import settings

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Ordered by quota availability (flash models first)
FALLBACK_MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
    "gemini-pro-latest",
]


class GoogleProvider(BaseAIProvider):
    name = "google"
    models = {
        "gemini-flash": "gemini-flash-latest",
        "gemini-2.5":   "gemini-2.5-flash",
        "gemini-lite":  "gemini-flash-lite-latest",
        "gemini-2":     "gemini-2.0-flash",
        "gemini-pro":   "gemini-pro-latest",
    }

    def is_available(self) -> bool:
        key = settings.GOOGLE_API_KEY
        return bool(key) and key != "AIza..."

    async def _call(self, model_id: str, contents: list, max_tokens: int) -> tuple[str, int]:
        import os
        url = f"{GEMINI_API_BASE}/{model_id}:generateContent?key={settings.GOOGLE_API_KEY}"
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
        }
        # Use CA bundle from environment if available (for proxy SSL verification)
        ca_cert = os.getenv("SSL_CERT_FILE") or os.getenv("REQUESTS_CA_BUNDLE") or True
        async with httpx.AsyncClient(timeout=60, verify=ca_cert) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        return text, tokens

    async def chat(self, messages: List[Message], model_id: str = "gemini-flash-latest",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        contents = []
        if system_prompt:
            contents.append({"role": "user",  "parts": [{"text": f"[System]: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
        for m in messages:
            role = "model" if m.role in ("assistant", "jarvis") else "user"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        # Try requested model first, then fallbacks
        attempts = [model_id] + [m for m in FALLBACK_MODELS if m != model_id]
        last_error = ""
        for attempt in attempts:
            try:
                text, tokens = await self._call(attempt, contents, max_tokens)
                return AIResponse(content=text, model=attempt, provider=self.name,
                                  task_type="general", tokens_used=tokens)
            except Exception as e:
                last_error = str(e)
                continue

        return AIResponse(content="", model=model_id, provider=self.name,
                          task_type="general", error=last_error)
