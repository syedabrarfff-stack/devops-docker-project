"""
JARVIS Incident Playbooks — Detailed runbooks for all 10 failure scenarios.
Structured reference for JARVIS autonomous recovery + Captain escalation.
"""
from __future__ import annotations

INCIDENT_PLAYBOOK_REGISTRY: dict[str, dict] = {
    "aws_outage": {
        "name": "AWS Region Outage",
        "description": "Primary region ap-south-2 (Hyderabad) becomes unavailable.",
        "detection_signals": [
            "ECS health checks failing across all services",
            "ALB returning 502/503 on all routes",
            "CloudWatch metrics flatlined",
            "AWS Status Page shows ap-south-2 incident",
        ],
        "immediate_actions": [
            "Verify outage scope via AWS Health Dashboard",
            "Activate ECS cluster in ap-south-1 (Mumbai) DR region",
            "Update Route 53 DNS to point to DR ALB",
            "Enable CloudFront static maintenance page for <5min window",
        ],
        "short_term_actions": [
            "Monitor RDS Multi-AZ replication lag to DR",
            "Verify all 33 APScheduler jobs re-register on DR cluster",
            "Notify Captain via Telegram with ETA",
            "Enable read-only mode until primary region restored",
        ],
        "long_term_actions": [
            "Post-incident review within 24 hours",
            "Evaluate multi-region active-active architecture",
            "Update runbook with lessons learned",
        ],
        "captain_notification_template": "🔴 CRITICAL: AWS ap-south-2 outage detected. DR activated in ap-south-1. ETA: ~30min. No data loss expected. Monitoring recovery.",
        "estimated_rto_minutes": 30,
        "estimated_rpo_minutes": 5,
        "post_incident_review_required": True,
        "severity": "critical",
    },
    "db_outage": {
        "name": "Database Outage",
        "description": "PostgreSQL RDS primary instance becomes unavailable.",
        "detection_signals": [
            "FastAPI returning 500 on all database-dependent endpoints",
            "SQLAlchemy connection pool exhausted errors in logs",
            "RDS instance status: unavailable in AWS console",
            "APScheduler job failures in rapid succession",
        ],
        "immediate_actions": [
            "RDS Multi-AZ auto-failover triggers automatically (15min SLA)",
            "Enable API read-only mode — disable all write endpoints",
            "Queue all mutation requests in Redis for replay",
            "Alert Captain via Telegram immediately",
        ],
        "short_term_actions": [
            "Monitor failover progress in RDS Events console",
            "Verify connection string updates after failover",
            "Test /readyz endpoint for database connectivity",
            "Replay queued mutations after DB restored",
        ],
        "long_term_actions": [
            "Review connection pooling settings",
            "Enable Enhanced Monitoring on RDS instance",
            "Test failover quarterly",
        ],
        "captain_notification_template": "🔴 CRITICAL: Database outage detected. RDS auto-failover initiated (ETA 15min). API in read-only mode. Queuing all writes for replay.",
        "estimated_rto_minutes": 20,
        "estimated_rpo_minutes": 2,
        "post_incident_review_required": True,
        "severity": "critical",
    },
    "ai_provider_outage": {
        "name": "AI Provider Outage",
        "description": "Primary AI provider (NVIDIA NIM) or any fallback provider becomes unavailable.",
        "detection_signals": [
            "Circuit breaker tripped on 5 consecutive failures",
            "AI request logs showing provider timeout/429 errors",
            "Cost tracker showing zero spend for >10 minutes during active hours",
            "JARVIS chat returning errors",
        ],
        "immediate_actions": [
            "Circuit breaker auto-routes to next provider in fallback chain",
            "CODE: nvidia/deepseek-v4-pro → nvidia/qwen-coder → anthropic/claude-sonnet",
            "STRATEGY: anthropic/claude-sonnet → nvidia/llama-4-maverick",
            "Log all affected request IDs for potential replay",
        ],
        "short_term_actions": [
            "Monitor all 11 provider health endpoints every 60 seconds",
            "Self-healer probes tripped circuit breakers and resets after recovery",
            "Notify Captain if degraded mode lasts >30 minutes",
            "Defer non-urgent AI tasks (tech radar, research) until restored",
        ],
        "long_term_actions": [
            "Review circuit breaker trip counts monthly",
            "Evaluate adding additional providers if outage exceeds SLA",
            "Document provider reliability metrics in truth engine",
        ],
        "captain_notification_template": "⚠️ HIGH: AI provider circuit breaker tripped. Auto-failover active. Routing to backup providers. Monitoring recovery. No action needed.",
        "estimated_rto_minutes": 5,
        "estimated_rpo_minutes": 0,
        "post_incident_review_required": False,
        "severity": "high",
    },
    "ses_outage": {
        "name": "AWS SES Email Outage",
        "description": "Email delivery via SES (info@aliyarsolutions.com) fails.",
        "detection_signals": [
            "SES bounce rate spike in CloudWatch",
            "Outreach emails returning delivery failures",
            "SES sending statistics showing zero delivery",
            "Gmail SMTP fallback exhausted",
        ],
        "immediate_actions": [
            "Pause outreach scheduler job immediately",
            "Queue all pending outreach emails in Redis with retry flag",
            "Switch client notification channel to WhatsApp (+973 34360246)",
            "Check AWS SES console for bounce/complaint threshold breaches",
        ],
        "short_term_actions": [
            "Verify SPF/DKIM/DMARC DNS records intact",
            "Check SES sending limits and reputation dashboard",
            "Contact AWS Support if sandbox restrictions re-applied",
            "Resume outreach job once SES health confirmed",
        ],
        "long_term_actions": [
            "Implement SendGrid as secondary email provider",
            "Set up email deliverability monitoring via SES event publishing",
            "Review bounce rates weekly to maintain sender reputation",
        ],
        "captain_notification_template": "⚠️ HIGH: SES outage detected. Outreach paused. Emails queued. WhatsApp channel active. ETA: ~60min depending on SES resolution.",
        "estimated_rto_minutes": 60,
        "estimated_rpo_minutes": 0,
        "post_incident_review_required": False,
        "severity": "high",
    },
    "stripe_outage": {
        "name": "Stripe Payment Processing Outage",
        "description": "Stripe payment gateway unavailable for invoice processing.",
        "detection_signals": [
            "Stripe webhook delivery failures in dashboard",
            "Payment intent creation returning 500 errors",
            "stripe.com/status showing incident",
        ],
        "immediate_actions": [
            "Switch payment form to PayPal legacy integration",
            "Notify Captain — no payments can be collected during outage",
            "Hold all invoice delivery until payment method confirmed",
        ],
        "short_term_actions": [
            "Monitor Stripe status page for resolution",
            "Prepare Wise invoice payment instructions for international clients",
            "Update client-facing payment page with alternative instructions",
        ],
        "long_term_actions": [
            "Implement Stripe → PayPal → Wise payment fallback chain",
            "Test payment failover quarterly",
        ],
        "captain_notification_template": "⚠️ MEDIUM: Stripe outage. Switching to PayPal. Manual Wise transfers available for international clients. No revenue lost — deferred.",
        "estimated_rto_minutes": 120,
        "estimated_rpo_minutes": 0,
        "post_incident_review_required": False,
        "severity": "medium",
    },
    "redis_outage": {
        "name": "Redis Cache Outage",
        "description": "Redis 7 ElastiCache cluster becomes unavailable.",
        "detection_signals": [
            "Rate limiter falling back to in-memory mode",
            "Session data loss for active users",
            "APScheduler job store switching to PostgreSQL fallback",
            "Redis connection refused errors in logs",
        ],
        "immediate_actions": [
            "Rate limiter auto-switches to in-memory fallback (stateless per instance)",
            "APScheduler continues via PostgreSQL job store",
            "Session management falls back to database sessions",
            "No outage visible to end users — degraded performance only",
        ],
        "short_term_actions": [
            "Monitor ElastiCache cluster health in AWS console",
            "Alert Captain if Redis unavailable >15 minutes",
            "Verify all rate limits still enforced in fallback mode",
        ],
        "long_term_actions": [
            "Enable Redis Multi-AZ replication",
            "Implement Redis Sentinel for automatic failover",
        ],
        "captain_notification_template": "ℹ️ MEDIUM: Redis cache unavailable. Fallback systems active — no user impact. ETA: ~15min. Monitoring.",
        "estimated_rto_minutes": 15,
        "estimated_rpo_minutes": 5,
        "post_incident_review_required": False,
        "severity": "medium",
    },
    "dns_outage": {
        "name": "DNS / Domain Outage",
        "description": "aliyarsolutions.com DNS resolution fails globally.",
        "detection_signals": [
            "External monitoring showing aliyarsolutions.com unreachable",
            "Route 53 health checks failing",
            "SSL certificate validation errors",
            "Client reports of site unreachability",
        ],
        "immediate_actions": [
            "Verify Route 53 hosted zone records intact",
            "Provide Captain and key clients with direct ALB URL",
            "Check domain registrar for expiry or suspension",
            "Activate backup DNS provider if Route 53 issue confirmed",
        ],
        "short_term_actions": [
            "Monitor DNS propagation after any fixes via dig/nslookup",
            "Notify clients via WhatsApp if outage exceeds 30 minutes",
            "Verify SSL certificate via ACM after DNS restored",
        ],
        "long_term_actions": [
            "Set domain auto-renewal reminder (12 months ahead)",
            "Register backup domain aliyar-solutions.com as failover",
            "Add Route 53 health check alerts to CloudWatch",
        ],
        "captain_notification_template": "🔴 CRITICAL: DNS outage for aliyarsolutions.com. Direct ALB URL available for internal access. Investigating. ETA: ~45min.",
        "estimated_rto_minutes": 45,
        "estimated_rpo_minutes": 0,
        "post_incident_review_required": True,
        "severity": "critical",
    },
    "security_incident": {
        "name": "Critical Security Incident",
        "description": "Unauthorized access, data breach, or active attack detected.",
        "detection_signals": [
            "Unusual JWT authentication patterns in logs",
            "Spike in failed login attempts (>100/hour)",
            "Unexpected data export or API calls from unknown IPs",
            "AWS GuardDuty alert or CloudTrail anomaly",
            "Captain credentials used from unrecognized location",
        ],
        "immediate_actions": [
            "Revoke ALL active JWT tokens immediately",
            "Enable emergency lockdown mode — all write endpoints disabled",
            "Capture forensic snapshot of access logs",
            "Notify Captain IMMEDIATELY via Telegram + WhatsApp",
            "Isolate affected services if breach confirmed",
        ],
        "short_term_actions": [
            "Rotate all secrets in AWS Secrets Manager",
            "Review CloudTrail logs for unauthorized actions",
            "Run vulnerability scan across all endpoints",
            "Change Captain password and regenerate SECRET_KEY",
            "Audit all active API keys and OAuth tokens",
        ],
        "long_term_actions": [
            "Commission external security audit within 30 days",
            "Implement WAF rules for detected attack vectors",
            "Enhance anomaly detection in middleware logging",
            "Review and harden all authentication flows",
        ],
        "captain_notification_template": "🚨 CRITICAL SECURITY: Unauthorized access detected. Emergency lockdown activated. ALL tokens revoked. Your immediate action required. Call me.",
        "estimated_rto_minutes": 240,
        "estimated_rpo_minutes": 60,
        "post_incident_review_required": True,
        "severity": "critical",
    },
    "client_churn": {
        "name": "Major Client Churn Event",
        "description": "Active client cancels contract or goes unresponsive.",
        "detection_signals": [
            "Client health score drops below 30",
            "No client engagement for >14 days",
            "Explicit cancellation notice received",
            "Invoice payment overdue >30 days",
        ],
        "immediate_actions": [
            "Activate emergency client retention protocol",
            "Route to Olivia Bennett (Account Coordinator) immediately",
            "Review all recent service delivery records",
            "Generate emergency client health report",
        ],
        "short_term_actions": [
            "Schedule executive call within 24 hours",
            "Prepare customized retention offer (discount/scope adjustment)",
            "Conduct client satisfaction deep-dive interview",
            "Document root cause for learning engine",
        ],
        "long_term_actions": [
            "Update client health monitoring thresholds",
            "Implement proactive check-in schedule for all clients",
            "Add early warning indicators to client health scoring",
        ],
        "captain_notification_template": "⚠️ HIGH: Client churn risk detected. Retention protocol activated. Olivia Bennett engaged. Review client health report in dashboard.",
        "estimated_rto_minutes": 1440,
        "estimated_rpo_minutes": 0,
        "post_incident_review_required": True,
        "severity": "high",
    },
    "captain_unavailable": {
        "name": "Captain Unavailable (30+ Days)",
        "description": "CEO Syed Abrar is unreachable for extended period.",
        "detection_signals": [
            "No Captain login for >7 days",
            "Approval queue backlog exceeding 20 items",
            "Telegram messages unread for >48 hours",
            "Emergency contact protocol triggered",
        ],
        "immediate_actions": [
            "Activate JARVIS 30-day autonomous operation mode",
            "Queue ALL approval requests — do not auto-approve >$3,000",
            "Continue all 33 scheduled intelligence jobs uninterrupted",
            "Generate daily status digest for when Captain returns",
        ],
        "short_term_actions": [
            "Auto-approve routine approvals <$500 after 72-hour hold",
            "Escalate only business-critical decisions via all channels",
            "Maintain all active client engagements at current service level",
            "Defer all new client proposals until Captain available",
        ],
        "long_term_actions": [
            "Establish emergency contact protocol with designated backup",
            "Create autonomous operation mode documentation",
            "Define auto-approval thresholds in governance policy",
        ],
        "captain_notification_template": "ℹ️ LOW: Autonomous mode activated. All systems running normally. Approval queue held. Daily digest saved. Ready when you return, Captain.",
        "estimated_rto_minutes": 43200,
        "estimated_rpo_minutes": 0,
        "post_incident_review_required": False,
        "severity": "low",
    },
}


def get_playbook(incident_type: str) -> dict | None:
    return INCIDENT_PLAYBOOK_REGISTRY.get(incident_type)


def get_all_playbooks() -> dict:
    return INCIDENT_PLAYBOOK_REGISTRY


def format_captain_alert(incident_type: str, details: dict | None = None) -> str:
    pb = INCIDENT_PLAYBOOK_REGISTRY.get(incident_type)
    if not pb:
        return f"⚠️ Unknown incident type: {incident_type}"
    msg = pb["captain_notification_template"]
    if details:
        extra = " | ".join(f"{k}: {v}" for k, v in details.items() if v)
        if extra:
            msg += f"\n\nDetails: {extra}"
    return msg
