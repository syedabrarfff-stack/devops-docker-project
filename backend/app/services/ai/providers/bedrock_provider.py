import asyncio
from typing import List

from app.core.config import settings
from app.services.ai.base_provider import AIResponse, BaseAIProvider, Message


class BedrockProvider(BaseAIProvider):
    name = "bedrock"
    models = {
        "bedrock-nova-pro": settings.AWS_BEDROCK_MODEL_ID,
        "bedrock-nova-lite": settings.AWS_BEDROCK_FAST_MODEL_ID,
    }

    def is_available(self) -> bool:
        return bool(settings.AWS_BEDROCK_ENABLED and settings.AWS_REGION)

    async def chat(
        self,
        messages: List[Message],
        model_id: str = "",
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> AIResponse:
        model = model_id or settings.AWS_BEDROCK_MODEL_ID
        try:
            return await asyncio.to_thread(
                self._converse,
                messages,
                model,
                system_prompt,
                max_tokens,
            )
        except Exception as e:
            return AIResponse(
                content="",
                model=model,
                provider=self.name,
                task_type="general",
                error=str(e),
            )

    def _converse(
        self,
        messages: List[Message],
        model_id: str,
        system_prompt: str,
        max_tokens: int,
    ) -> AIResponse:
        import boto3

        client_kwargs = {"region_name": settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            client_kwargs.update(
                {
                    "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                    "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
                }
            )
        client = boto3.client("bedrock-runtime", **client_kwargs)

        bedrock_messages = [
            {
                "role": "assistant" if message.role == "assistant" else "user",
                "content": [{"text": message.content}],
            }
            for message in messages
            if message.role != "system" and message.content and message.content.strip()
        ]
        if not bedrock_messages:
            bedrock_messages = [{"role": "user", "content": [{"text": "Status check."}]}]

        payload = {
            "modelId": model_id,
            "messages": bedrock_messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": 0.4,
            },
        }
        if system_prompt:
            payload["system"] = [{"text": system_prompt}]

        result = client.converse(**payload)
        content_blocks = result.get("output", {}).get("message", {}).get("content", [])
        text = "\n".join(block.get("text", "") for block in content_blocks if block.get("text"))
        usage = result.get("usage", {})
        tokens = int(usage.get("inputTokens", 0) or 0) + int(usage.get("outputTokens", 0) or 0)
        return AIResponse(
            content=text,
            model=model_id,
            provider=self.name,
            task_type="general",
            tokens_used=tokens,
        )
