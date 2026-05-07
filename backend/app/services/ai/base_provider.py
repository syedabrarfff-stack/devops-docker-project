from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class TaskType(str, Enum):
    CODE = "code"
    RESEARCH = "research"
    REASONING = "reasoning"
    FAST = "fast"
    IMAGE = "image"
    VOICE = "voice"
    LONG_CONTEXT = "long_context"
    MULTILINGUAL = "multilingual"
    MATH = "math"
    GENERAL = "general"


@dataclass
class Message:
    role: str    # "user" | "assistant" | "system"
    content: str


@dataclass
class AIResponse:
    content: str
    model: str
    provider: str
    task_type: str
    tokens_used: int = 0
    demo: bool = False
    error: Optional[str] = None


class BaseAIProvider(ABC):
    name: str = "base"
    models: dict = {}

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model_id: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> AIResponse:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    def get_model_id(self, key: str) -> str:
        return self.models.get(key, list(self.models.values())[0])
