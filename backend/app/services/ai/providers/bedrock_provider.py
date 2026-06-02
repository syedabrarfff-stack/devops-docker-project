from __future__ import annotations

import asyncio
import json
from typing import List

from app.core.config import settings
from app.services.ai.base_provider import AIResponse, BaseAIProvider, Message


class BedrockProvider(BaseAIProvider):
    name = "bedrock"
    models = {
        "claude-sonnet-4-6": "global.anthropic.claude-sonnet-4-6",
        "claude-sonnet": "global.anthropic.claude-sonnet-4-6",
        "claude-haiku": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "claude-opus": "global.anthropic.claude-opus-4-8",
    }

    def is_available(self) -> bool:
        return bool(settings.USE_AWS and settings.AWS_REGION)

    async def chat(
        self,
        messages: List[Message],
        model_id: str = "global.anthropic.claude-sonnet-4-6",
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> AIResponse:
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
            }
            data = await asyncio.to_thread(_invoke_bedrock, model_id, payload)
            text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
            usage = data.get("usage", {})
            tokens = int(usage.get("input_tokens", 0) or 0) + int(usage.get("output_tokens", 0) or 0)
            return AIResponse(
                content=text,
                model=model_id,
                provider=self.name,
                task_type="general",
                tokens_used=tokens,
            )
        except Exception as exc:
            return AIResponse(
                content="",
                model=model_id,
                provider=self.name,
                task_type="general",
                error=str(exc),
            )


def _invoke_bedrock(model_id: str, payload: dict) -> dict:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(payload),
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())
