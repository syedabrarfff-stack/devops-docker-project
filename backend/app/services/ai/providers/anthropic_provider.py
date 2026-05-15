import json
import logging
from typing import Any, List, Optional
from app.services.ai.base_provider import BaseAIProvider, AIResponse, Message
from app.core.config import settings

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseAIProvider):
    name = "anthropic"
    models = {
        "claude-sonnet": "claude-sonnet-4-6",
        "claude-opus": "claude-opus-4-7",
    }

    def is_available(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    def _clean_text_block(self, block: dict[str, Any]) -> Optional[dict[str, Any]]:
        if block.get("type") != "text":
            return block

        text = block.get("text")
        if not isinstance(text, str) or not text.strip():
            return None

        cleaned = {**block, "text": text.strip()}
        return cleaned

    def _normalise_content(self, content: Any) -> Optional[Any]:
        if isinstance(content, str):
            text = content.strip()
            return text or None

        if isinstance(content, list):
            cleaned_blocks = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                cleaned = self._clean_text_block(block)
                if cleaned:
                    cleaned_blocks.append(cleaned)
            return cleaned_blocks or None

        return None

    def _normalise_messages(self, messages: List[Message]) -> list[dict[str, Any]]:
        normalised = []
        for message in messages:
            content = self._normalise_content(message.content)
            if content is None:
                continue
            normalised.append({"role": message.role, "content": content})
        return normalised

    async def chat(self, messages: List[Message], model_id: str = "claude-sonnet-4-6",
                   system_prompt: str = "", max_tokens: int = 2048) -> AIResponse:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            cleaned_messages = self._normalise_messages(messages)
            if not cleaned_messages:
                return AIResponse(
                    content="",
                    model=model_id,
                    provider=self.name,
                    task_type="general",
                    error="No non-empty messages to send to Anthropic.",
                )

            logger.debug("Anthropic payload messages: %s", json.dumps(cleaned_messages, indent=2))
            result = await client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                system=system_prompt.strip() if system_prompt else "",
                messages=cleaned_messages,
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
