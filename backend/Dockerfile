FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 jarvis \
    && mkdir -p /data/proposals /data/invoices \
    && chown -R jarvis:jarvis /data
USER jarvis

COPY --chown=jarvis:jarvis . .

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=10s --start-period=40s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use gunicorn with uvicorn workers — production-grade process manager.
# Auto-restarts crashed workers; --preload reduces per-worker memory.
CMD ["gunicorn", "app.main:app", \
     "-c", "gunicorn.conf.py"]
