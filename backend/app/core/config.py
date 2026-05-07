from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "JARVIS"
    APP_VERSION: str = "1.0.0"
    COMPANY_NAME: str = "Aliyar Solutions"
    CAPTAIN_NAME: str = "Captain Abrar"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production"

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

    # Connectors
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    HUBSPOT_API_KEY: Optional[str] = None
    APOLLO_API_KEY: Optional[str] = None
    NOTION_API_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None

    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "ap-south-1"

    # CORS
    CORS_ORIGINS: str = "http://localhost,http://localhost:3000"

    class Config:
        env_file = (".env", "../.env")
        case_sensitive = True
        extra = "ignore"


settings = Settings()
