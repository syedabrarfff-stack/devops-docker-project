from __future__ import annotations

import asyncio
import json
import os
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
        "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    }

    def is_available(self) -> bool:
        aws_creds_present = bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)
        bearer_present = bool(settings.BEDROCK_API_KEY or settings.AWS_BEARER_TOKEN_BEDROCK)
        return bool(settings.AWS_REGION and (settings.USE_AWS or aws_creds_present or bearer_present))

    async def chat(
        self,
        messages: List[Message],
        model_id: str = "global.anthropic.claude-sonnet-4-6",
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> AIResponse:
        try:
            data = await asyncio.to_thread(_invoke_with_fallbacks, model_id, messages, system_prompt, max_tokens)
            text = data["text"]
            tokens = data["tokens"]
            return AIResponse(
                content=text,
                model=data["model_id"],
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


def _prepare_bedrock_auth() -> None:
    token = settings.AWS_BEARER_TOKEN_BEDROCK or settings.BEDROCK_API_KEY
    if token and not os.getenv("AWS_BEARER_TOKEN_BEDROCK"):
        # Boto3 recognizes this official Bedrock bearer-token environment variable.
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = token


def _bedrock_session_kwargs() -> dict:
    kwargs = {}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        if settings.AWS_SESSION_TOKEN:
            kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN
    return kwargs


def _candidate_model_ids(preferred_model_id: str) -> list[str]:
    candidates = [
        preferred_model_id,
        "global.anthropic.claude-sonnet-4-6",
        "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "anthropic.claude-sonnet-4-6",
        "anthropic.claude-haiku-4-5-20251001-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-sonnet-4-20250514-v1:0",
    ]
    seen: set[str] = set()
    return [m for m in candidates if m and not (m in seen or seen.add(m))]


def _invoke_with_fallbacks(
    model_id: str,
    messages: List[Message],
    system_prompt: str,
    max_tokens: int,
) -> dict:
    errors: list[str] = []
    for candidate in _candidate_model_ids(model_id):
        try:
            return _converse_bedrock(candidate, messages, system_prompt, max_tokens)
        except Exception as exc:
            errors.append(f"{candidate}: {type(exc).__name__}: {str(exc)[:360]}")
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
            }
            data = _invoke_bedrock(candidate, payload)
            text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
            usage = data.get("usage", {})
            tokens = int(usage.get("input_tokens", 0) or 0) + int(usage.get("output_tokens", 0) or 0)
            return {"model_id": candidate, "text": text, "tokens": tokens}
        except Exception as exc:
            errors.append(f"{candidate}/invoke: {type(exc).__name__}: {str(exc)[:360]}")
    raise RuntimeError("Bedrock invocation failed for all configured candidates. " + " | ".join(errors[:8]))


def _bedrock_client():
    import boto3

    _prepare_bedrock_auth()
    session_kwargs = _bedrock_session_kwargs()
    if session_kwargs:
        return boto3.Session(**session_kwargs).client("bedrock-runtime", region_name=settings.AWS_REGION)
    return boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)


def _converse_bedrock(model_id: str, messages: List[Message], system_prompt: str, max_tokens: int) -> dict:
    client = _bedrock_client()
    response = client.converse(
        modelId=model_id,
        messages=[{"role": m.role, "content": [{"text": m.content}]} for m in messages],
        system=[{"text": system_prompt}] if system_prompt else [],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
    )
    content = response.get("output", {}).get("message", {}).get("content", [])
    text = "".join(part.get("text", "") for part in content)
    usage = response.get("usage", {})
    tokens = int(usage.get("inputTokens", 0) or 0) + int(usage.get("outputTokens", 0) or 0)
    return {"model_id": model_id, "text": text, "tokens": tokens}


def _invoke_bedrock(model_id: str, payload: dict) -> dict:
    client = _bedrock_client()
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(payload),
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())
