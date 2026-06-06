"""
Gunicorn production configuration for JARVIS.
Uses UvicornWorker — async-compatible, handles HTTP/1.1 + WebSocket upgrades.
"""
import multiprocessing
import os

# ── Server socket ─────────────────────────────────────────────────────────────
bind = "0.0.0.0:8000"
backlog = 256

# ── Worker processes ──────────────────────────────────────────────────────────
# One worker is the stable default for the small EC2 pilot and avoids duplicate
# startup seed/scheduler work. Larger hosts can override this with env.
workers = int(os.getenv("GUNICORN_WORKERS", os.getenv("WEB_CONCURRENCY", "1")))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 200

# ── Timeouts ──────────────────────────────────────────────────────────────────
timeout = int(os.getenv("GUNICORN_TIMEOUT", "240"))  # worker silent time before SIGKILL
keepalive = 5           # TCP keepalive on idle connections
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "45"))

# ── Lifecycle ─────────────────────────────────────────────────────────────────
preload_app = True      # load app once before forking → smaller per-worker RAM
max_requests = 500      # recycle workers after N requests → prevents memory leaks
max_requests_jitter = 50

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = "-"
errorlog  = "-"
loglevel  = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sus'

# ── Process naming ────────────────────────────────────────────────────────────
proc_name = "jarvis"
