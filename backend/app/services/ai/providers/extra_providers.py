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
            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                model=model_id, provider=self.name, task_type="general",
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
    name = "nvidia"
    base_url = "https://integrate.api.nvidia.com/v1"
    models = {"nvidia-nim": "meta/llama-3.1-70b-instruct"}

    def is_available(self) -> bool:
        return bool(settings.NVIDIA_API_KEY)

    async def chat(self, messages: List[Message], model_id: str = "meta/llama-3.1-70b-instruct",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend([{"role": m.role, "content": m.content} for m in messages])
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
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
