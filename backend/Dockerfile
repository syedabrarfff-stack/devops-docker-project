FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev postgresql-client curl gzip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

RUN useradd -m -u 1000 jarvis \
    && mkdir -p /data/proposals /data/invoices /var/backups/jarvis /etc/ssl/certs \
    && chown -R jarvis:jarvis /data /var/backups/jarvis

# Set CA bundle paths for agent proxy SSL verification
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt

USER jarvis

COPY --chown=jarvis:jarvis . .

# Pre-flight: verify the full app import chain works before the container ever starts.
# Catches missing modules, bad imports, and model errors at BUILD time, not at runtime.
# NOTE: Must be a single-line -c string — Docker parser treats bare newlines as instructions.
RUN DATABASE_URL="postgresql+asyncpg://t:t@localhost/t" \
    SECRET_KEY="6a4bf4ea1769d45abf21752fb25673d869b521d146fb93434a2648a66c4ee5d9" \
    CAPTAIN_PASSWORD="build-time-preflight-only" \
    CAPTAIN_USERNAME="captain" \
    DEBUG="false" \
    python3 -c "import sys, os; sys.path.insert(0, '/app'); os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://t:t@localhost/t'); from app.api.v1 import api_router; print('PRE_FLIGHT_OK: all imports resolved')" \
    2>&1 | tee /tmp/preflight.txt && grep -q PRE_FLIGHT_OK /tmp/preflight.txt

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=10s --start-period=40s --retries=5 \
    CMD curl -f --max-time 5 http://localhost:8000/health || exit 1

# Use gunicorn with uvicorn workers — production-grade process manager.
# Auto-restarts crashed workers; --preload reduces per-worker memory.
CMD ["gunicorn", "app.main:app", \
     "-c", "gunicorn.conf.py"]
