"""
GLM (ZhipuAI), Qwen (Alibaba DashScope), MiniMax, Moonshot (Kimi), NVIDIA
"""
from typing import List
import httpx
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message
from app.core.config import settings


class ZhipuAIProvider(BaseAIProvider):
    name = "zhipuai"
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    # glm-4-flash = ultrafast/cheap | glm-4 = standard | glm-4-plus = premium
    models = {"glm-4-flash": "glm-4-flash", "glm-4-7": "glm-4", "glm-5-1": "glm-4-plus"}

    def is_available(self) -> bool:
        return bool(settings.ZHIPUAI_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "glm-4",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend([{"role": m.role, "content": m.content} for m in messages])
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ZHIPUAI_API_KEY}"},
                    json={"model": model_id, "messages": msgs, "max_tokens": max_tokens},
                )
                data = r.json()
            content = data["choices"][0]["message"]["content"]
            return AIResponse(
                content=content,
                model=model_id, provider=self.name, task_type="general",
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
            )
        except Exception as e:
            return AIResponse(content="", model=model_id, provider=self.name,
                              task_type="general", error=str(e))


class QwenProvider(BaseAIProvider):
    name = "qwen"
    base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    models = {"qwen-turbo": "qwen-turbo", "qwen-image": "wanx-v1"}

    def is_available(self) -> bool:
        return bool(settings.DASHSCOPE_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "qwen-turbo",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    self.base_url,
                    headers={"Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
                             "Content-Type": "application/json"},
                    json={"model": model_id,
                          "input": {"messages": [{"role": m.role, "content": m.content} for m in messages]},
                          "parameters": {"max_tokens": max_tokens}},
                )
                data = r.json()
            return AIResponse(
                content=data["output"]["text"],
                model=model_id, provider=self.name, task_type="general",
            )
        except Exception as e:
            return AIResponse(content="", model=model_id, provider=self.name,
                              task_type="general", error=str(e))


class MoonshotProvider(BaseAIProvider):
    name = "moonshot"
    base_url = "https://api.moonshot.cn/v1"
    models = {"kimi-k2": "moonshot-v1-128k"}

    def is_available(self) -> bool:
        return bool(settings.MOONSHOT_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "moonshot-v1-128k",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend([{"role": m.role, "content": m.content} for m in messages])
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.MOONSHOT_API_KEY}"},
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


class MinimaxProvider(BaseAIProvider):
    name = "minimax"
    models = {"minimax-m2": "MiniMax-Text-01"}

    def is_available(self) -> bool:
        return bool(settings.MINIMAX_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "MiniMax-Text-01",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    "https://api.minimaxi.chat/v1/text/chatcompletion_v2",
                    headers={"Authorization": f"Bearer {settings.MINIMAX_API_KEY}"},
                    json={"model": model_id,
                          "messages": [{"role": m.role, "content": m.content} for m in messages],
                          "max_tokens": max_tokens},
                )
                data = r.json()
            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                model=model_id, provider=self.name, task_type="general",
            )
        except Exception as e:
            return AIResponse(content="", model=model_id, provider=self.name,
                              task_type="general", error=str(e))


class NvidiaProvider(BaseAIProvider):
    """
    NVIDIA NIM unified provider — one endpoint, 10 rotating API keys,
    serving Llama 4, DeepSeek V4, Qwen, Kimi, Mistral, GLM, and more.
    """
    name = "nvidia"
    base_url = "https://integrate.api.nvidia.com/v1"
    models = {
        # Default / generic routing
        "nvidia-nim":         "meta/llama-4-maverick-17b-128e-instruct",
        # Llama family
        "llama-4-maverick":   "meta/llama-4-maverick-17b-128e-instruct",
        "llama-4-scout":      "meta/llama-4-scout-17b-16e-instruct",
        "llama-3-3":          "meta/llama-3.3-70b-instruct",
        # DeepSeek via NIM
        "deepseek-v4-flash":  "deepseek-ai/deepseek-v4-flash",
        "deepseek-v4-pro":    "deepseek-ai/deepseek-v4-pro",
        # Qwen via NIM
        "qwen-coder":         "qwen/qwen2.5-coder-32b-instruct",
        # Kimi (Moonshot) via NIM
        "kimi-k2":            "moonshotai/kimi-k2.6",
        # Mistral via NIM
        "mistral-medium":     "mistralai/mistral-medium-3-instruct",
        # MiniMax via NIM
        "minimax-m3":         "minimaxai/minimax-m3",
    }

    def _nim_keys(self) -> list:
        """Return all configured NIM API keys for round-robin rotation."""
        candidates = [
            settings.NVIDIA_API_KEY,
            settings.NVIDIA_API_KEY_B,
            settings.NVIDIA_API_KEY_C,
            settings.NVIDIA_API_KEY_D,
            settings.NVIDIA_API_KEY_E,
            settings.NVIDIA_API_KEY_F,
            settings.NVIDIA_API_KEY_G,
            settings.NVIDIA_API_KEY_H,
            settings.NVIDIA_API_KEY_I,
            settings.NVIDIA_API_KEY_J,
        ]
        return [k for k in candidates if k and not k.startswith("test") and k.startswith("nvapi-")]

    def is_available(self) -> bool:
        return len(self._nim_keys()) > 0

    async def chat(self, messages: List[Message], model_id: str = "meta/llama-4-maverick-17b-128e-instruct",
                   system_prompt: str = "", max_tokens: int = 4096) -> AIResponse:
        import os
        keys = self._nim_keys()
        if not keys:
            return AIResponse(content="", model=model_id, provider=self.name,
                              task_type="general", error="no_nvidia_nim_keys_configured")

        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend([{"role": m.role, "content": m.content} for m in messages])

        # Use CA bundle from environment if available (for proxy SSL verification)
        ca_cert = os.getenv("SSL_CERT_FILE") or os.getenv("REQUESTS_CA_BUNDLE") or True

        last_error = ""
        for api_key in keys:
            try:
                async with httpx.AsyncClient(timeout=90, verify=ca_cert) as client:
                    r = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={"model": model_id, "messages": msgs, "max_tokens": max_tokens,
                              "temperature": 0.7, "top_p": 0.95},
                    )
                    if r.status_code == 429:
                        last_error = "rate_limited"
                        continue
                    r.raise_for_status()
                    data = r.json()
                return AIResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=model_id, provider=self.name, task_type="general",
                    tokens_used=data.get("usage", {}).get("total_tokens", 0),
                )
            except httpx.TimeoutException:
                last_error = "timeout"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        return AIResponse(content="", model=model_id, provider=self.name,
                          task_type="general", error=f"all_nim_keys_failed:{last_error}")
