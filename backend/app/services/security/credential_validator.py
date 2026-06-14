"""
Credential Validator — startup audit of all configured API keys and secrets.
Logs which providers are active, which are missing, and flags critical gaps.
"""
import logging
from dataclasses import dataclass
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

SEVERITY_CRITICAL = "critical"   # system cannot function without this
SEVERITY_HIGH = "high"           # major capability degraded
SEVERITY_MEDIUM = "medium"       # some features unavailable
SEVERITY_LOW = "low"             # optional enhancement

@dataclass
class CredentialCheck:
    name: str
    category: str
    configured: bool
    severity: str
    description: str
    masked_value: Optional[str] = None


def _mask(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def run_credential_audit() -> dict:
    checks: list[CredentialCheck] = [
        # ── Database ────────────────────────────────────────────────────────────
        CredentialCheck("DATABASE_URL", "Database", bool(settings.DATABASE_URL and "jarvis_pass" not in settings.DATABASE_URL), SEVERITY_CRITICAL, "PostgreSQL connection string"),
        CredentialCheck("SECRET_KEY", "App Security", bool(settings.SECRET_KEY and settings.SECRET_KEY != "change-this-in-production"), SEVERITY_CRITICAL, "Application secret key for JWT/session signing"),
        CredentialCheck("CAPTAIN_PASSWORD", "Auth", bool(settings.CAPTAIN_PASSWORD and settings.CAPTAIN_PASSWORD not in ("CHANGE_ME_IN_ENV", "change-this-to-a-strong-password", "")), SEVERITY_CRITICAL, "Captain login password — must be set in .env"),
        # ── AI Providers ────────────────────────────────────────────────────────
        CredentialCheck("ANTHROPIC_API_KEY", "AI — Primary", bool(settings.ANTHROPIC_API_KEY), SEVERITY_HIGH, "Claude — primary reasoning + strategy engine", _mask(settings.ANTHROPIC_API_KEY)),
        CredentialCheck("OPENAI_API_KEY", "AI — Primary", bool(settings.OPENAI_API_KEY), SEVERITY_HIGH, "GPT-4o — code + general intelligence fallback", _mask(settings.OPENAI_API_KEY)),
        CredentialCheck("DEEPSEEK_API_KEY", "AI — Fast", bool(settings.DEEPSEEK_API_KEY), SEVERITY_MEDIUM, "DeepSeek — fast operations + code generation", _mask(settings.DEEPSEEK_API_KEY)),
        CredentialCheck("GOOGLE_API_KEY", "AI — Research", bool(settings.GOOGLE_API_KEY), SEVERITY_MEDIUM, "Gemini — research + long context tasks", _mask(settings.GOOGLE_API_KEY)),
        CredentialCheck("GROQ_API_KEY", "AI — Realtime", bool(settings.GROQ_API_KEY), SEVERITY_MEDIUM, "Groq — ultra-fast Llama inference for realtime ops", _mask(settings.GROQ_API_KEY)),
        CredentialCheck("MISTRAL_API_KEY", "AI — Supplemental", bool(settings.MISTRAL_API_KEY), SEVERITY_LOW, "Mistral — European compliance, supplemental tasks", _mask(settings.MISTRAL_API_KEY)),
        CredentialCheck("MOONSHOT_API_KEY", "AI — Long Context", bool(settings.MOONSHOT_API_KEY), SEVERITY_LOW, "Kimi — 128K context window for long documents", _mask(settings.MOONSHOT_API_KEY)),
        CredentialCheck("ZHIPUAI_API_KEY", "AI — GLM", bool(settings.ZHIPUAI_API_KEY), SEVERITY_LOW, "GLM — multilingual + fast operations", _mask(settings.ZHIPUAI_API_KEY)),
        CredentialCheck("DASHSCOPE_API_KEY", "AI — Qwen", bool(settings.DASHSCOPE_API_KEY), SEVERITY_LOW, "Qwen — image editing + Chinese language tasks", _mask(settings.DASHSCOPE_API_KEY)),
        CredentialCheck("MINIMAX_API_KEY", "AI — MiniMax", bool(settings.MINIMAX_API_KEY), SEVERITY_LOW, "MiniMax — supplemental AI operations", _mask(settings.MINIMAX_API_KEY)),
        CredentialCheck("NVIDIA_API_KEY", "AI — NVIDIA", bool(settings.NVIDIA_API_KEY), SEVERITY_LOW, "NVIDIA NIM — realtime speaker detection + Nemotron", _mask(settings.NVIDIA_API_KEY)),
        # ── Notifications ───────────────────────────────────────────────────────
        CredentialCheck("SLACK_WEBHOOK_URL", "Notifications", bool(settings.SLACK_WEBHOOK_URL), SEVERITY_HIGH, "Slack — Captain alerts and emergency notifications", _mask(settings.SLACK_WEBHOOK_URL)),
        CredentialCheck("TELEGRAM_BOT_TOKEN", "Notifications", bool(settings.TELEGRAM_BOT_TOKEN), SEVERITY_MEDIUM, "Telegram — mobile approval push notifications", _mask(settings.TELEGRAM_BOT_TOKEN)),
        # ── Email ───────────────────────────────────────────────────────────────
        CredentialCheck("OUTBOUND_EMAIL_PROVIDER", "Email", bool(settings.OUTBOUND_EMAIL_PROVIDER), SEVERITY_HIGH, "Outbound email provider selector"),
        CredentialCheck("EXECUTIVE_EMAIL_ADDRESS", "Email", bool(settings.EXECUTIVE_EMAIL_ADDRESS), SEVERITY_HIGH, "Executive sender address for outreach and proposals"),
        CredentialCheck("SES_FROM_EMAIL", "Email — SES", bool(settings.SES_FROM_EMAIL or settings.EXECUTIVE_EMAIL_ADDRESS), SEVERITY_HIGH, "AWS SES verified sender identity"),
        CredentialCheck("AWS_ACCESS_KEY_ID", "AWS — SES", bool(settings.AWS_ACCESS_KEY_ID or settings.USE_AWS), SEVERITY_HIGH if settings.USE_AWS else SEVERITY_LOW, "AWS credentials for SES sending"),
        # ── Connectors ──────────────────────────────────────────────────────────
        CredentialCheck("APOLLO_API_KEY", "CRM Connectors", bool(settings.APOLLO_API_KEY), SEVERITY_MEDIUM, "Apollo.io — lead enrichment and contact sync", _mask(settings.APOLLO_API_KEY)),
        CredentialCheck("HUBSPOT_API_KEY", "CRM Connectors", bool(settings.HUBSPOT_API_KEY), SEVERITY_LOW, "HubSpot CRM integration", _mask(settings.HUBSPOT_API_KEY)),
        # ── Payments ────────────────────────────────────────────────────────────
        CredentialCheck("PAYPAL_CLIENT_ID", "Payments", bool(settings.PAYPAL_CLIENT_ID), SEVERITY_HIGH, "PayPal — primary payment system", _mask(settings.PAYPAL_CLIENT_ID)),
        CredentialCheck("STRIPE_SECRET_KEY", "Payments", bool(settings.STRIPE_SECRET_KEY), SEVERITY_LOW, "Stripe — future payment provider", _mask(settings.STRIPE_SECRET_KEY)),
        # ── AWS ─────────────────────────────────────────────────────────────────
        CredentialCheck("AWS_ACCESS_KEY_ID", "AWS", bool(settings.AWS_ACCESS_KEY_ID), SEVERITY_HIGH if settings.USE_AWS else SEVERITY_LOW, "AWS credentials — required when USE_AWS=true", _mask(settings.AWS_ACCESS_KEY_ID)),
        CredentialCheck("AWS_SECRET_ACCESS_KEY", "AWS", bool(settings.AWS_SECRET_ACCESS_KEY), SEVERITY_HIGH if settings.USE_AWS else SEVERITY_LOW, "AWS secret key", _mask(settings.AWS_SECRET_ACCESS_KEY)),
    ]

    configured = [c for c in checks if c.configured]
    missing = [c for c in checks if not c.configured]
    critical_missing = [c for c in missing if c.severity == SEVERITY_CRITICAL]
    high_missing = [c for c in missing if c.severity == SEVERITY_HIGH]

    # Log summary to console at startup
    logger.info(f"[credentials] Configured: {len(configured)}/{len(checks)}")
    if critical_missing:
        for c in critical_missing:
            logger.error(f"[credentials] CRITICAL MISSING: {c.name} — {c.description}")
    if high_missing:
        for c in high_missing:
            logger.warning(f"[credentials] HIGH MISSING: {c.name} — {c.description}")

    ai_configured = [c for c in configured if c.category.startswith("AI")]
    ai_missing = [c for c in missing if c.category.startswith("AI")]

    return {
        "total": len(checks),
        "configured": len(configured),
        "missing": len(missing),
        "critical_missing": len(critical_missing),
        "high_missing": len(high_missing),
        "system_ready": len(critical_missing) == 0,
        "ai_providers_active": len(ai_configured),
        "ai_providers_missing": len(ai_missing),
        "checks": [
            {
                "name": c.name,
                "category": c.category,
                "configured": c.configured,
                "severity": c.severity,
                "description": c.description,
                "masked_value": c.masked_value,
            }
            for c in checks
        ],
    }
