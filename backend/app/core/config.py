import logging
from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import Optional

_cfg_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # App
    APP_NAME: str = "JARVIS"
    APP_VERSION: str = "9.0.0"
    COMPANY_NAME: str = "Aliyar Solutions"
    FOUNDER_NAME: str = "Syed Abrar"
    CAPTAIN_NAME: str = "Captain Abrar"
    COMPANY_TAGLINE: str = "Global AI-Powered Technology Operations"
    COMPANY_EXTERNAL_TEAM: str = "Aliyar Solutions Team"
    COMPANY_PHYSICAL_ADDRESS: str = "Aliyar Solutions, Hyderabad, Telangana, India"
    TARGET_MARKETS: str = "USA,UK,UAE,Bahrain,Europe,Australia"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production"
    CAPTAIN_ADMIN_TOKEN: Optional[str] = None
    # Captain authentication — MUST be overridden in production .env
    CAPTAIN_USERNAME: str = "captain"
    CAPTAIN_PASSWORD: str = "CHANGE_ME_IN_ENV"
    APP_BASE_URL: str = "http://localhost:8000"
    JARVIS_DEFAULT_TENANT_ID: Optional[str] = None
    PILOT_READY: bool = True
    AUTONOMOUS_CONFIDENCE_THRESHOLD: float = 0.70
    SYSTEM_CONFIDENCE_BASE: float = 0.68
    EXTERNAL_API_BLOCKERS_BYPASSED_FOR_PILOT: bool = True
    OUTREACH_DAILY_SEND_CAP: int = 48
    OUTREACH_DOMAIN_AGE_DAYS: int = 365
    OUTREACH_PAUSED: bool = False
    # Autonomous Governance Thresholds
    AUTO_APPROVE_PROPOSAL_THRESHOLD_USD: float = 5000.0
    AUTO_APPROVE_INVOICE_THRESHOLD_USD: float = 5000.0
    AUTO_SEND_OUTREACH: bool = True
    AUTO_SEND_OUTREACH_WARM_LEADS_ONLY: bool = True
    AUTO_SEND_OUTREACH_MIN_QUALITY_SCORE: float = 0.70

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://jarvis:jarvis_pass@postgres:5432/jarvis_db"

    # AI Providers
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    MOONSHOT_API_KEY: Optional[str] = None
    ZHIPUAI_API_KEY: Optional[str] = None
    DASHSCOPE_API_KEY: Optional[str] = None
    MINIMAX_API_KEY: Optional[str] = None
    NVIDIA_API_KEY: Optional[str] = None
    # NIM key rotation pool — all keys work for all NIM-hosted models
    NVIDIA_API_KEY_B: Optional[str] = None
    NVIDIA_API_KEY_C: Optional[str] = None
    NVIDIA_API_KEY_D: Optional[str] = None
    NVIDIA_API_KEY_E: Optional[str] = None
    NVIDIA_API_KEY_F: Optional[str] = None
    NVIDIA_API_KEY_G: Optional[str] = None
    NVIDIA_API_KEY_H: Optional[str] = None
    NVIDIA_API_KEY_I: Optional[str] = None
    NVIDIA_API_KEY_J: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: str = "onwK4e9ZLuTAKqWW03F9"  # Daniel — British male
    CLAUDE_BUDGET_TOTAL_USD: float = 50.0
    CLAUDE_BUDGET_WINDOW_DAYS: int = 14
    CLAUDE_RESERVE_RATIO: float = 0.20
    CLAUDE_SINGLE_CALL_MAX_USD: float = 1.00

    # Lead discovery
    GOOGLE_MAPS_API_KEY: Optional[str] = None

    # Notifications
    SLACK_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None  # Set to validate X-Telegram-Bot-API-Secret-Token
    VOICE_WEBHOOK_SECRET: Optional[str] = None  # Set to validate X-Voice-Webhook-Secret on /api/v1/webhooks/voice/*

    # Executive email / SES
    OUTBOUND_EMAIL_PROVIDER: str = "ses"
    EXECUTIVE_EMAIL_NAME: str = "Joseph David"
    EXECUTIVE_EMAIL_TITLE: str = "Executive Director"
    EXECUTIVE_EMAIL_ADDRESS: str = "joseph.david@aliyarsolutions.com"
    SES_FROM_NAME: Optional[str] = None
    SES_FROM_EMAIL: Optional[str] = None
    SES_CONFIGURATION_SET: Optional[str] = None
    SES_REGION: Optional[str] = None
    # Inbound reply routing: replies from clients go to this address,
    # which is routed via SES receipt rules (not Google Workspace).
    # MX record for inbound.aliyarsolutions.com must point to SES inbound SMTP.
    SES_REPLY_TO_EMAIL: Optional[str] = None  # e.g. replies@inbound.aliyarsolutions.com
    OUTREACH_PERSONALIZE_ON_SEND: bool = True
    EMAIL_REPLY_TO_NAME: Optional[str] = None
    # Legacy mailbox fields retained only for retired compatibility paths
    GMAIL_ADDRESS: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None
    GMAIL_USER: Optional[str] = None
    EMAIL_USER: Optional[str] = None
    EMAIL_PASS: Optional[str] = None
    SMTP_HOST: str = "email-smtp.ap-south-2.amazonaws.com"
    SMTP_PORT: int = 587
    SMTP_SECURE: bool = False
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None

    # WhatsApp / Evolution API transport
    WHATSAPP_PROVIDER: str = "evolution"
    WHATSAPP_ENABLED: bool = True
    WHATSAPP_INSTANCE_NAME: str = "jarvis-main"
    WHATSAPP_DISPLAY_IDENTITY: str = "Joseph David"
    WHATSAPP_CAPTAIN_PHONE: str = "+97334360246"  # Captain's Bahrain number for notifications
    EVOLUTION_API_URL: str = "http://evolution:8080"
    EVOLUTION_API_KEY: Optional[str] = None
    EVOLUTION_PUBLIC_URL: Optional[str] = None
    EVOLUTION_WEBHOOK_URL: Optional[str] = None
    WHATSAPP_AUTO_REPLY_ENABLED: bool = False
    WHATSAPP_AUTO_REPLY_MIN_CONFIDENCE: float = 0.85

    # Connectors
    HUBSPOT_API_KEY: Optional[str] = None
    APOLLO_API_KEY: Optional[str] = None
    NOTION_API_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    WISE_API_KEY: Optional[str] = None
    PAYPAL_ENABLED: bool = False
    BANK_TRANSFER_ENABLED: bool = True
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Slack Bot (two-way: Phase 6A)
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None

    # Zapier / Make.com webhook gateway (Phase 6A)
    ZAPIER_WEBHOOK_SECRET: Optional[str] = None
    MAKE_WEBHOOK_SECRET: Optional[str] = None
    ZAPIER_LEAD_QUALIFIED_HOOK: Optional[str] = None
    ZAPIER_PROPOSAL_SENT_HOOK: Optional[str] = None
    MAKE_APPROVAL_HOOK: Optional[str] = None

    # LinkedIn outreach (Phase 6A — Proxycurl enrichment)
    PROXYCURL_API_KEY: Optional[str] = None

    # n8n Automation Platform
    N8N_BASE_URL: str = "https://automation.aliyarsolutions.com"
    N8N_WEBHOOK_URL: str = "https://automation.aliyarsolutions.com/webhook"
    N8N_API_KEY: Optional[str] = None

    # GitHub Bridge (scout network pushes daily leads to jarvis-data/)
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO_OWNER: str = "syedabrarfff-stack"
    GITHUB_REPO_NAME: str = "devops-docker-project"
    GITHUB_BRIDGE_BRANCH: str = "claude/jarvis-cans-api-integration-ZThTD"

    # AWS (Phase 3 — SSM + S3 | Phase 6 — ECS production)
    USE_AWS: bool = False
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None
    AWS_REGION: str = "ap-south-2"             # Hyderabad primary
    AWS_BACKUP_REGION: str = "ap-south-1"      # Mumbai backup (Phase 2)
    BEDROCK_API_KEY: Optional[str] = None       # Bedrock bearer token fallback
    AWS_BEARER_TOKEN_BEDROCK: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    S3_BACKUP_BUCKET: Optional[str] = None
    AWS_SSM_PREFIX: str = "/jarvis"
    AWS_ECS_CLUSTER: Optional[str] = None
    AWS_ECS_SERVICE: Optional[str] = None

    # Redis (Phase 6 — production cache + task queue)
    REDIS_URL: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None

    # PayPal (Phase 6 — initial payment system)
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"               # sandbox | live

    # CORS
    CORS_ORIGINS: str = "http://localhost,http://localhost:3000,https://aliyarsolutions.com,https://www.aliyarsolutions.com"

    # Separate from DEBUG on purpose: DEBUG also controls verbose logging/tracebacks
    # and gets flipped for reasons unrelated to secrets (e.g. diagnosing on a
    # prod-like box). A stale or copied .env with DEBUG=True must not silently
    # skip the insecure-default checks below — this second, explicitly-named
    # flag has to also be set for that skip to take effect.
    ALLOW_INSECURE_DEV_DEFAULTS: bool = False

    @model_validator(mode="after")
    def _validate_production_config(self) -> "Settings":
        if not (self.DEBUG and self.ALLOW_INSECURE_DEV_DEFAULTS):
            errors: list[str] = []
            if self.SECRET_KEY in ("change-this-in-production", "", None):
                errors.append(
                    "SECRET_KEY is the insecure default — all JWTs are compromised. "
                    "Set a strong random value in .env or AWS Secrets Manager."
                )
            elif len(self.SECRET_KEY) < 32:
                errors.append(
                    f"SECRET_KEY is too short ({len(self.SECRET_KEY)} chars) — "
                    "HS256 requires at least 32 characters (256 bits). "
                    "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            if self.CAPTAIN_PASSWORD in ("CHANGE_ME_IN_ENV", "change_me", "", None):
                errors.append(
                    "CAPTAIN_PASSWORD is the insecure default — "
                    "Set a strong password in .env or AWS Secrets Manager."
                )
            if any(p in self.DATABASE_URL for p in ("jarvis_pass", "jarvis_secret", "CHANGE_ME", "password")):
                errors.append(
                    "DATABASE_URL contains the default development password — "
                    "Set a strong password in .env or AWS Secrets Manager."
                )
            if errors:
                for msg in errors:
                    _cfg_logger.critical("STARTUP BLOCKED: %s", msg)
                raise ValueError(
                    "Production startup blocked — insecure defaults detected:\n"
                    + "\n".join(f"  • {e}" for e in errors)
                )
        else:
            # DEBUG=True and ALLOW_INSECURE_DEV_DEFAULTS=true both set — warn but don't block
            if self.SECRET_KEY == "change-this-in-production":
                _cfg_logger.warning("DEV: SECRET_KEY is the default (acceptable only with ALLOW_INSECURE_DEV_DEFAULTS=true)")
            if self.CAPTAIN_PASSWORD in ("CHANGE_ME_IN_ENV", "change_me", ""):
                _cfg_logger.warning("DEV: CAPTAIN_PASSWORD is the default (acceptable only with ALLOW_INSECURE_DEV_DEFAULTS=true)")
        return self

    class Config:
        env_file = (".env", "../.env")
        case_sensitive = True
        extra = "ignore"


settings = Settings()
