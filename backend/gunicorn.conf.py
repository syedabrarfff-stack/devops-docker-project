"""Gunicorn production configuration for JARVIS."""

bind = "0.0.0.0:8000"
backlog = 256

# Keep one worker until the scheduler has a distributed lock. Multiple workers
# start duplicate APScheduler loops and make every recurring job run twice.
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 200

timeout = 120
keepalive = 5
graceful_timeout = 30

max_requests = 500
max_requests_jitter = 50

accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sus'

proc_name = "jarvis"
