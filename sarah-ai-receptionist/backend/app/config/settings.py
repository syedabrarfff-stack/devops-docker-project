from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenRouter / AI
    openrouter_api_key: str
    ai_model: str = "anthropic/claude-sonnet-4-6"
    ai_model_fast: str = "anthropic/claude-haiku-4-5-20251001"
    ai_model_summary: str = "google/gemini-flash-1.5"

    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    # Deepgram
    deepgram_api_key: str

    # ElevenLabs
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    elevenlabs_model: str = "eleven_turbo_v2_5"

    # Database — required, no default. A missing env var must fail startup,
    # not silently fall back to a weak local credential.
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 40

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AWS / S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_recordings: str = "sarah-receptionist-recordings-prod"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    app_base_url: str = "http://localhost:8000"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Data retention (HIPAA/GDPR) — days a call transcript/recording is kept
    # before it's redacted. Override per clinic-contract requirements.
    call_transcript_retention_days: int = 365

    @property
    def is_production(self) -> bool:
        # Terraform sets APP_ENV to var.environment ("prod"), not the literal
        # word "production" — this mismatch silently forced wss:// media
        # streams to fall back to ws://, which Twilio's <Stream> verb rejects
        # outright, breaking every real call while /health still reported OK.
        return self.app_env in ("production", "prod")


@lru_cache
def get_settings() -> Settings:
    return Settings()
