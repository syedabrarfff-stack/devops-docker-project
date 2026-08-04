"""
Test environment bootstrap.

Settings has no defaults for credentials on purpose — a missing env var must
fail startup rather than fall back to something weak. That means tests touching
any module which calls get_settings() need placeholders in place before the
first import, which is what this file guarantees (pytest imports conftest
before collecting test modules).

Every value here is an obvious dummy. Nothing in this file is a real secret,
and tests must never read the developer's own .env.
"""

import os

_TEST_ENV = {
    "OPENROUTER_API_KEY": "test-not-a-real-key",
    "TWILIO_ACCOUNT_SID": "ACtest00000000000000000000000000",
    "TWILIO_AUTH_TOKEN": "test-not-a-real-token",
    "TWILIO_PHONE_NUMBER": "+15550000000",
    "DEEPGRAM_API_KEY": "test-not-a-real-key",
    "ELEVENLABS_API_KEY": "test-not-a-real-key",
    "ELEVENLABS_VOICE_ID": "test-voice-id",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
    "REDIS_URL": "redis://localhost:6379/0",
    "JWT_SECRET_KEY": "test-not-a-real-secret",
    "APP_BASE_URL": "https://sarah.example.com",
    "APP_ENV": "test",
}

# setdefault so a deliberately-set value in CI still wins.
for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)

# Settings reads .env when present; pointing it at a file that does not exist
# keeps a developer's real credentials out of the test run.
os.environ.setdefault("ENV_FILE", "/nonexistent")
