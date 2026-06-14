FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev postgresql-client curl gzip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 jarvis \
    && mkdir -p /data/proposals /data/invoices /var/backups/jarvis \
    && chown -R jarvis:jarvis /data /var/backups/jarvis
USER jarvis

COPY --chown=jarvis:jarvis . .

# Pre-flight: verify the full app import chain works before the container ever starts.
# Catches missing modules, bad imports, and model errors at BUILD time, not at runtime.
# NOTE: Must be a single-line -c string — Docker parser treats bare newlines as instructions.
RUN DATABASE_URL="postgresql+asyncpg://t:t@localhost/t" \
    python3 -c "import sys, os; sys.path.insert(0, '/app'); os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://t:t@localhost/t'); from app.api.v1 import api_router; print('PRE_FLIGHT_OK: all imports resolved')" \
    2>&1 | tee /tmp/preflight.txt && grep -q PRE_FLIGHT_OK /tmp/preflight.txt

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=10s --start-period=40s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use gunicorn with uvicorn workers — production-grade process manager.
# Auto-restarts crashed workers; --preload reduces per-worker memory.
CMD ["gunicorn", "app.main:app", \
     "-c", "gunicorn.conf.py"]
