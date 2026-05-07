from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "JARVIS"
    APP_VERSION: str = "2.0.0"
    COMPANY_NAME: str = "Aliyar Solutions"
    CAPTAIN_NAME: str = "Captain Abrar"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production"
    APP_BASE_URL: str = "http://localhost:8000"

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

    # AWS (Phase 3 — SSM + S3)
    USE_AWS: bool = False
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: Optional[str] = None
    AWS_SSM_PREFIX: str = "/jarvis"

    # CORS
    CORS_ORIGINS: str = "http://localhost,http://localhost:3000"

    class Config:
        env_file = (".env", "../.env")
        case_sensitive = True
        extra = "ignore"


settings = Settings()
