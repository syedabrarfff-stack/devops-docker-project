from __future__ import annotations

from app.core.config import settings
from app.services.storage.secure import get_credential


RUNTIME_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "MOONSHOT_API_KEY",
    "ZHIPUAI_API_KEY",
    "DASHSCOPE_API_KEY",
    "MINIMAX_API_KEY",
    "NVIDIA_API_KEY",
    "ELEVENLABS_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_BEDROCK_ENABLED",
    "AWS_BEDROCK_MODEL_ID",
    "AWS_BEDROCK_FAST_MODEL_ID",
)


async def hydrate_runtime_settings(db) -> dict[str, bool]:
    """Load Access Vault values into process settings for env-only integrations."""
    hydrated: dict[str, bool] = {}
    for key in RUNTIME_KEYS:
        value = await get_credential(db, key)
        if value in (None, ""):
            hydrated[key] = False
            continue
        current = getattr(settings, key, None)
        if not current:
            if isinstance(current, bool):
                setattr(settings, key, str(value).lower() in {"1", "true", "yes", "on"})
            else:
                setattr(settings, key, value)
        hydrated[key] = bool(getattr(settings, key, None))
    return hydrated
