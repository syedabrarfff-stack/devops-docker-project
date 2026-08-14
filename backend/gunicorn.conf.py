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
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "500"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = "-"
errorlog  = "-"
loglevel  = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sus'

# ── Process naming ────────────────────────────────────────────────────────────
proc_name = "jarvis"


# ── Scheduler isolation ───────────────────────────────────────────────────────
# APScheduler is NOT safe to run in multiple gunicorn workers against the same
# database — it would execute every job N times (once per worker).  Mark workers
# beyond the first so the FastAPI lifespan can skip starting the scheduler there.
def post_fork(server, worker):
    import os
    if worker.age > 0:
        os.environ["JARVIS_SCHEDULER_DISABLED"] = "1"
