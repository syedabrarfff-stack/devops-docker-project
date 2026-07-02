# JARVIS Service Endpoints & Access Guide

**⚠️ SECURITY NOTE:** This file contains NO actual credentials, passwords, or API keys. Real values are stored ONLY in your local `.env` file and AWS Secrets Manager (production).

---

## 📡 Service Endpoints Reference

### Control Room (Internal Dashboard)
```
URL (Local):      http://localhost:3002/control-room
URL (via Nginx):  http://localhost/control-room
URL (Production): https://aliyarsolutions.com/control-room
Port:             3002 (direct), 80/443 (via Nginx)
Authentication:   Basic HTTP Auth
Username:         captain
Password:         [stored in .env — CAPTAIN_PASSWORD]
```

**What it shows:**
- Real-time system monitoring
- AI costs by provider
- Scheduler job status
- Lead management
- Outreach campaigns
- Billing & invoices

---

### Public Website
```
URL (Local):      http://localhost
URL (Production): https://aliyarsolutions.com
Port:             80 (HTTP), 443 (HTTPS)
Authentication:   None (public)
```

**What it shows:**
- Marketing homepage
- Service overview (30 divisions)
- Team & company info
- Contact & lead capture

---

### Grafana Dashboards (Metrics)
```
URL (Local):      http://localhost:3001
URL (via Nginx):  http://localhost/grafana
URL (Production): https://aliyarsolutions.com/grafana
Port:             3001
Authentication:   Grafana login
Username:         captain
Password:         [stored in .env — GRAFANA_ADMIN_PASSWORD]
```

**Dashboards:**
- JARVIS Main — CPU, memory, container metrics
- Loki Logs — Application logs from all services
- API Performance — Request rates, latencies, errors
- Database — Query performance, connections

---

### Prometheus Metrics (Time-Series DB)
```
URL (Local):      http://localhost:9090
URL (via Nginx):  http://localhost/prometheus
URL (Production): https://aliyarsolutions.com/prometheus
Port:             9090
Authentication:   None (internal only)
Query Language:   PromQL
```

**Data Sources:**
- Node Exporter (system metrics)
- PostgreSQL Exporter (database)
- Redis Exporter (cache)
- cAdvisor (containers)
- Application metrics

---

### Loki Log Aggregation
```
URL (Local):      http://localhost:3100
URL (via Nginx):  http://localhost/loki
URL (Production): https://aliyarsolutions.com/loki
Port:             3100
Authentication:   None (internal only)
Query Language:   LogQL
Retention:        30 days
```

**Log Sources:**
- Backend (FastAPI)
- Frontend (React)
- Nginx (HTTP access & errors)
- Redis
- PostgreSQL
- All Docker containers

---

### Backend API Server
```
URL (Local):      http://localhost:8000
URL (via Nginx):  http://localhost/api
URL (Production): https://api.aliyarsolutions.com
Port:             8000
Authentication:   None (internal), Bearer token (production)
Language:         Python 3.11 + FastAPI
```

**Health Endpoints:**
```
GET /health              → Liveness check
GET /readyz              → Deep readiness (all dependencies)
GET /api/v1/system/env   → Environment status
```

**API Documentation:**
```
GET /docs               → Swagger UI (OpenAPI docs)
GET /redoc              → ReDoc (alternative docs)
```

**Core Routes (v1):**
```
POST   /api/v1/auth/login
GET    /api/v1/leads
POST   /api/v1/leads
GET    /api/v1/tenants
POST   /api/v1/outreach/send
GET    /api/v1/invoices
POST   /api/v1/proposals
GET    /api/v1/scheduler/jobs
GET    /api/v1/ai-ops/cost/today
GET    /api/v1/ai-ops/health
```

---

### PostgreSQL Database
```
Host (Docker):    postgres
Host (Direct):    localhost
Port:             5432
Database:         [stored in .env — POSTGRES_DB]
Username:         [stored in .env — POSTGRES_USER]
Password:         [stored in .env — POSTGRES_PASSWORD]
```

**Connection String Template:**
```
postgresql+asyncpg://[user]:[password]@[host]:5432/[database]
```

**Access via CLI:**
```bash
docker exec -it jarvis_postgres psql -U [POSTGRES_USER] -d [POSTGRES_DB]
```

**Key Tables (35+ total):**
- tenant, user, lead, contact, opportunity, invoice, proposal
- ai_request_log, ai_provider_health, scheduler_job, scheduler_job_run
- outreach_campaign, communication, team_member, + more

---

### Redis Cache & Session Store
```
Host (Docker):    redis
Host (Direct):    localhost
Port:             6379
Password:         [stored in .env — REDIS_PASSWORD]
Database:         0 (default)
```

**Connection String Template:**
```
redis://:[password]@[host]:6379/0
```

**Access via CLI:**
```bash
docker exec -it jarvis_redis redis-cli -a [REDIS_PASSWORD]
```

**Usage:**
- Session tokens & auth state
- Rate limiting state
- Cached queries (lead scores, provider health)
- Real-time subscriptions (WebSocket)

---

### Nginx Reverse Proxy & Load Balancer
```
HTTP Port:        80
HTTPS Port:       443
Auth Type:        Basic .htpasswd
Username:         captain
Password Hash:    [stored in .htpasswd — bcrypt]
```

**Routing:**
- Frontend (http://localhost:3002)
- Backend API (http://localhost:8000)
- Grafana (http://localhost:3001)
- Evolution API (http://localhost:8080)

**Rate Limiting:**
- General: 20 requests/second
- Login: 5 requests/minute
- Webhooks: 30 requests/second

**Security Headers:**
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Content-Security-Policy: strict
- Strict-Transport-Security: max-age=31536000

---

## 🔐 Third-Party Service Endpoints

### Anthropic (Claude API)
```
Endpoint:   https://api.anthropic.com
API Key:    [stored in .env — ANTHROPIC_API_KEY]
Console:    https://console.anthropic.com
Models:     claude-haiku-4-5-20251001, claude-opus-4-8
```

### NVIDIA NIM (Multi-Model Hosting)
```
Endpoint:   https://integrate.api.nvidia.com
API Keys:   [10 rotating keys in .env — NVIDIA_API_KEY*]
Console:    https://build.nvidia.com
Models:     Llama 4, DeepSeek V4, Mistral, Qwen, GLM
```

### OpenAI (GPT-4o)
```
Endpoint:   https://api.openai.com/v1
API Key:    [stored in .env — OPENAI_API_KEY]
Console:    https://platform.openai.com
Models:     gpt-4o, gpt-4-turbo
```

### Google Maps API
```
Endpoint:   https://maps.googleapis.com
API Key:    [stored in .env — GOOGLE_MAPS_API_KEY]
Console:    https://console.cloud.google.com
```

### Stripe (Payment Processing)
```
API Endpoint:      https://api.stripe.com
Webhook Endpoint:  /api/v1/webhooks/stripe
API Key (Secret):  [stored in .env — STRIPE_SECRET_KEY]
API Key (Public):  [stored in .env — STRIPE_PUBLISHABLE_KEY]
Webhook Secret:    [stored in .env — STRIPE_WEBHOOK_SECRET]
Console:           https://dashboard.stripe.com
```

### AWS SES (Email Sending)
```
SMTP Endpoint:     email-smtp.[region].amazonaws.com:587
API Endpoint:      https://email.[region].amazonaws.com
Region:            [stored in .env — AWS_REGION]
From Email:        [stored in .env — SES_FROM_EMAIL]
Reply-To:          [stored in .env — SES_REPLY_TO_EMAIL]
Console:           https://console.aws.amazon.com/ses
```

### Evolution API (WhatsApp)
```
URL (Docker):      http://evolution:8080
URL (Production):  [stored in .env — EVOLUTION_PUBLIC_URL]
API Key:           [stored in .env — EVOLUTION_API_KEY]
Instance:          [stored in .env — WHATSAPP_INSTANCE_NAME]
Console:           https://evolution-api.com
```

### Slack
```
Webhook Endpoint:  https://hooks.slack.com/services/[WEBHOOK_ID]
Webhook URL:       [stored in .env — SLACK_WEBHOOK_URL]
Channel:           [determined by webhook]
Console:           https://api.slack.com
```

### Telegram
```
API Endpoint:      https://api.telegram.org/bot[TOKEN]
Bot Token:         [stored in .env — TELEGRAM_BOT_TOKEN]
Chat ID:           [stored in .env — TELEGRAM_CHAT_ID]
Bot Setup:         @BotFather on Telegram
```

### GitHub (Scout Network)
```
API Endpoint:      https://api.github.com
Token Type:        Personal Access Token
Token:             [stored in .env — GITHUB_TOKEN]
Repo:              syedabrarfff-stack/devops-docker-project
Console:           https://github.com/settings/tokens
```

---

## 🧪 Health Check Commands

```bash
# Backend API
curl http://localhost:8000/health

# PostgreSQL
docker exec jarvis_postgres pg_isready -U [POSTGRES_USER]

# Redis
docker exec jarvis_redis redis-cli -a [REDIS_PASSWORD] PING

# Grafana
curl http://localhost:3001/api/health

# Prometheus
curl http://localhost:9090/-/healthy

# Loki
curl http://localhost:3100/ready

# Frontend
curl http://localhost:3002 | head -1

# Full stack
docker compose ps
```

---

## 🔄 API Documentation

All internal APIs use REST with JSON payloads.

**Authentication Headers (Production):**
```bash
Authorization: Bearer [JWT_TOKEN]
X-Request-ID: [unique-request-id]  # auto-generated
Content-Type: application/json
```

**Response Format:**
```json
{
  "status": "success|error",
  "data": { /* response payload */ },
  "error": { /* error details if status=error */ },
  "meta": { "request_id": "...", "timestamp": "..." }
}
```

**Error Codes:**
- 200: Success
- 201: Created
- 400: Bad request (validation error)
- 401: Unauthorized (missing/invalid token)
- 403: Forbidden (insufficient permissions)
- 404: Not found
- 429: Too many requests (rate limited)
- 500: Internal server error

---

## 📊 WebSocket Connections

**Endpoint:** `ws://localhost:8000/ws` (Docker) or `wss://api.aliyarsolutions.com/ws` (production)

**Authentication:** Bearer token in query string or header

**Subscriptions:**
- System metrics updates
- Real-time lead scoring
- Notification broadcasts
- Scheduler job status changes

---

## 🆘 Connection Troubleshooting

| Issue | Diagnosis | Fix |
|---|---|---|
| "Connection refused" | Service not running | `docker compose up -d` |
| "Auth failed" | Wrong credentials | Check .env values |
| "No route to host" | Network isolation | Check docker-compose.yml networks |
| "Timeout" | Service overloaded | Check logs: `docker compose logs [service]` |
| "DNS error" | Container DNS | Restart service or docker daemon |

---

## 🔒 Security Best Practices

1. **Never share actual credentials** — Only share this file (no values)
2. **Use IP whitelisting** — Restrict API access to known IPs
3. **Rotate tokens regularly** — Every 90 days minimum
4. **Monitor access logs** — Check for suspicious activity
5. **Use VPN for production access** — Never connect directly to public endpoints
6. **Audit CloudTrail logs** — Weekly review of API calls (AWS)
7. **Enable MFA** — On all third-party service accounts
8. **Use encrypted connections** — HTTPS/TLS for all external APIs

---

**Last Updated:** 2026-07-02  
**Location:** `/Headquarters/Environment/SERVICE_ENDPOINTS_REFERENCE.md`  
**Actual Values:** In your local `.env` file only (never in Git)
