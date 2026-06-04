from pydantic_settings import BaseSettings
from typing import Optional


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
    APP_BASE_URL: str = "http://localhost:8000"
    JARVIS_DEFAULT_TENANT_ID: Optional[str] = None
    PILOT_READY: bool = True
    AUTONOMOUS_CONFIDENCE_THRESHOLD: float = 0.70
    SYSTEM_CONFIDENCE_BASE: float = 0.68
    EXTERNAL_API_BLOCKERS_BYPASSED_FOR_PILOT: bool = True
    OUTREACH_DAILY_SEND_CAP: int = 50
    OUTREACH_DOMAIN_AGE_DAYS: int = 365
    OUTREACH_PAUSED: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://jarvis:jarvis_pass@postgres:5432/jarvis_db"

    # AI Providers
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    MOONSHOT_API_KEY: Optional[str] = None
    ZHIPUAI_API_KEY: Optional[str] = None
    DASHSCOPE_API_KEY: Optional[str] = None
    MINIMAX_API_KEY: Optional[str] = None
    NVIDIA_API_KEY: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: str = "onwK4e9ZLuTAKqWW03F9"  # Daniel — British male
    CLAUDE_BUDGET_TOTAL_USD: float = 5.0
    CLAUDE_BUDGET_WINDOW_DAYS: int = 14
    CLAUDE_RESERVE_RATIO: float = 0.20
    CLAUDE_SINGLE_CALL_MAX_USD: float = 0.20

    # Lead discovery
    GOOGLE_MAPS_API_KEY: Optional[str] = None

    # Notifications
    SLACK_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Gmail (Phase 2 SMTP / Phase 3 OAuth)
    GMAIL_ADDRESS: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None    # Phase 2 SMTP
    GMAIL_CLIENT_ID: Optional[str] = None       # Phase 3 OAuth
    GMAIL_CLIENT_SECRET: Optional[str] = None   # Phase 3 OAuth

    # Connectors
    HUBSPOT_API_KEY: Optional[str] = None
    APOLLO_API_KEY: Optional[str] = None
    NOTION_API_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # AWS (Phase 3 — SSM + S3 | Phase 6 — ECS production)
    USE_AWS: bool = False
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
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
    CORS_ORIGINS: str = "http://localhost,http://localhost:3000"

    class Config:
        env_file = (".env", "../.env")
        case_sensitive = True
        extra = "ignore"


settings = Settings()
