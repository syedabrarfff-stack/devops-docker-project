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

    # Twilio Voice SDK (browser "Call Sarah" widget). Separate from the main
    # auth token: the Voice SDK issues short-lived client access tokens
    # signed with an API Key/Secret pair, scoped only to a single TwiML
    # Application -- so a compromised widget token can't touch the account
    # the way the main auth_token could. Empty means the widget is disabled;
    # /api/v1/voice-widget/token returns 503 rather than crash on startup.
    twilio_voice_api_key_sid: str = ""
    twilio_voice_api_key_secret: str = ""
    twilio_voice_twiml_app_sid: str = ""

    # Deepgram
    deepgram_api_key: str
    # Transcription language. Sarah's prompt makes her bilingual (Modern
    # Standard Arabic and English) and her ElevenLabs voice can speak Arabic,
    # so this single value decides whether she can also *understand* an Arabic
    # caller. Threaded through settings rather than hardcoded so serving a new
    # market is a deployment decision, not a code change.
    #
    # Pinning this to a single language (previously "ar-SA") is a real
    # production hazard, confirmed live: any caller speaking a different
    # language than the pin doesn't just transcribe less accurately --
    # Deepgram can't confidently match the audio to the pinned language, so
    # it never cleanly finalizes the utterance. It keeps revising interim
    # transcripts instead of emitting speech_final, and the whole call loop
    # waits on that before Sarah can respond -- multi-second dead air on
    # every turn, not a quality degradation. Saudi Arabia/GCC is the primary
    # go-to-market and Sarah's prompt is bilingual, so neither "en" nor
    # "ar-SA" alone is acceptable as the default.
    #
    # "multi" is Deepgram's real multilingual code-switching mode, confirmed
    # against current docs to work with Nova-3 (the model this app
    # requests): each turn is recognized in its own language natively,
    # rather than every turn being forced through one pinned language's
    # acoustic model. This is what actually delivers "seamless Arabic/English
    # switching," not a single-language pin with a hopeful prompt on top.
    deepgram_language: str = "multi"

    # ElevenLabs
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    elevenlabs_model: str = "eleven_turbo_v2_5"

    # Database — required, no default. A missing env var must fail startup,
    # not silently fall back to a weak local credential.
    #
    # Pool sizing: every container (api, voice, worker; 2 tasks each = 6
    # containers) opens its own pool, and during a blue/green rollout old and
    # new tasks briefly coexist (up to ~12 containers). At the previous
    # defaults (20 + 40 = 60/container) that peaks near 720 connections
    # against db.t4g.medium's ~450 max_connections ceiling -- exceeding the
    # database's own limit during an ordinary deploy. 5 + 10 = 15/container
    # peaks around 180, leaving headroom for one-off admin/migration tasks.
    # No single container plausibly holds 20 connections at once; requests
    # acquire one briefly, not per-concurrent-caller.
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AWS / S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_recordings: str = "sarah-receptionist-recordings-prod"

    # JWT + session model.
    #
    # Previously: access token = 24h, held in localStorage. That means any
    # XSS anywhere in the SPA is a full 24h session-token theft, and there
    # is no path to shorter tokens without forcing re-logins every 15 min.
    #
    # Now: short-lived access token (in-memory only on the client) + opaque
    # refresh token in an HttpOnly Secure cookie, revocable via Redis. The
    # refresh cookie is served across app./admin./sarah. subdomains, which
    # requires SameSite=None; that's paired with Secure and a same-parent
    # domain, so it's cross-subdomain, not cross-site.
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    # Set at deploy time to `.aliyarsolutions.com` so app./admin. can both
    # send the refresh cookie to sarah.'s /auth/refresh. Empty means "no
    # explicit domain" (host-only cookie -- correct for local dev).
    refresh_cookie_domain: str = ""

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"  # nosec B104 — behind ALB in a private VPC subnet; see docs/SECURITY_AUDIT.md F5
    app_port: int = 8000
    log_level: str = "INFO"
    app_base_url: str = "http://localhost:8000"

    # Stripe. price_id names the Product+Price the subscription attaches to;
    # without it billing_service creates a Customer only (nothing charges),
    # so a missing key is treated as "billing disabled locally" -- it must
    # not silently onboard clinics as free forever in production.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

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
