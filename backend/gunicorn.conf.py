"""
Gunicorn production configuration for JARVIS.
Uses UvicornWorker — async-compatible, handles HTTP/1.1 + WebSocket upgrades.
"""
import multiprocessing

# ── Server socket ─────────────────────────────────────────────────────────────
bind = "0.0.0.0:8000"
backlog = 256

# ── Worker processes ──────────────────────────────────────────────────────────
# 2 workers is stable for a 768 MB container; each UvicornWorker handles async I/O.
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 200

# ── Timeouts ──────────────────────────────────────────────────────────────────
timeout = 120           # worker silent time before SIGKILL
keepalive = 5           # TCP keepalive on idle connections
graceful_timeout = 30   # seconds for workers to finish before forced kill

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
