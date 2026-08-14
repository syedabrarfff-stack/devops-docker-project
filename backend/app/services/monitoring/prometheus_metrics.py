"""
Prometheus Metrics — Complete observability for JARVIS
Tracks: requests, errors, latency, database, cache, jobs, costs
"""

from prometheus_client import Counter, Gauge, Histogram, Summary
from typing import Optional

# Request metrics
requests_total = Counter(
    "jarvis_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

request_duration_ms = Histogram(
    "jarvis_request_duration_ms",
    "Request duration in milliseconds",
    ["method", "endpoint"],
    buckets=(10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
)

# Error metrics
errors_total = Counter(
    "jarvis_errors_total",
    "Total errors",
    ["error_type", "endpoint"],
)

exceptions_total = Counter(
    "jarvis_exceptions_total",
    "Total unhandled exceptions",
    ["exception_type", "endpoint"],
)

# Database metrics
db_connection_pool_size = Gauge(
    "jarvis_db_connections_active",
    "Active database connections",
)

db_query_duration_ms = Histogram(
    "jarvis_db_query_duration_ms",
    "Database query duration",
    ["query_type"],
    buckets=(10, 50, 100, 500, 1000, 5000),
)

db_query_errors = Counter(
    "jarvis_db_query_errors_total",
    "Database query errors",
    ["query_type", "error_type"],
)

# Cache metrics
cache_hits = Counter(
    "jarvis_cache_hits_total",
    "Cache hits",
    ["cache_key"],
)

cache_misses = Counter(
    "jarvis_cache_misses_total",
    "Cache misses",
    ["cache_key"],
)

redis_memory_bytes = Gauge(
    "jarvis_redis_memory_bytes",
    "Redis memory usage in bytes",
)

# Job/Task metrics
jobs_total = Counter(
    "jarvis_jobs_total",
    "Total scheduled jobs executed",
    ["job_name", "status"],
)

job_duration_ms = Histogram(
    "jarvis_job_duration_ms",
    "Job duration in milliseconds",
    ["job_name"],
    buckets=(100, 500, 1000, 5000, 10000, 30000, 60000),
)

active_jobs = Gauge(
    "jarvis_active_jobs",
    "Number of active jobs",
)

failed_jobs_last_hour = Gauge(
    "jarvis_failed_jobs_last_hour",
    "Failed jobs in last hour",
)

# AI/LLM metrics
llm_api_calls = Counter(
    "jarvis_llm_api_calls_total",
    "LLM API calls",
    ["provider", "model", "status"],
)

llm_tokens_used = Counter(
    "jarvis_llm_tokens_used_total",
    "Tokens used by LLM",
    ["provider", "model"],
)

llm_cost_dollars = Counter(
    "jarvis_llm_cost_dollars_total",
    "LLM API costs in dollars",
    ["provider"],
)

llm_latency_ms = Histogram(
    "jarvis_llm_latency_ms",
    "LLM API latency",
    ["provider"],
    buckets=(100, 500, 1000, 2000, 5000, 10000),
)

# Business metrics
leads_created = Counter(
    "jarvis_leads_created_total",
    "Leads created",
    ["source"],
)

deals_closed = Counter(
    "jarvis_deals_closed_total",
    "Deals closed",
    ["division"],
)

revenue_dollars = Counter(
    "jarvis_revenue_dollars_total",
    "Revenue in dollars",
    ["service", "client_segment"],
)

customer_satisfaction_score = Gauge(
    "jarvis_customer_satisfaction_score",
    "NPS/CSAT score",
)

# System health metrics
system_health_score = Gauge(
    "jarvis_system_health_score",
    "Overall system health (0-100)",
)

uptime_seconds = Gauge(
    "jarvis_uptime_seconds",
    "System uptime in seconds",
)

active_users = Gauge(
    "jarvis_active_users",
    "Number of active users",
)

agent_capacity_utilization = Gauge(
    "jarvis_agent_capacity_utilization",
    "Agent capacity utilization percentage",
)

# Authority metrics
decisions_made = Counter(
    "jarvis_decisions_made_total",
    "Decisions made by JARVIS",
    ["decision_type", "authority_level"],
)

captain_approvals_needed = Gauge(
    "jarvis_captain_approvals_needed",
    "Approvals waiting for Captain",
)

trust_score = Gauge(
    "jarvis_trust_score",
    "System trust score (0-100)",
)

# Alert metrics
alerts_active = Gauge(
    "jarvis_alerts_active",
    "Number of active alerts",
    ["severity"],
)

alerts_resolved_today = Gauge(
    "jarvis_alerts_resolved_today",
    "Alerts resolved today",
)
