# JARVIS Integration Architecture

**Purpose:** Document how all JARVIS systems, external APIs, databases, and services integrate together. This is the authoritative guide to system connectivity and data flows.

**Last Updated:** 2026-07-02  
**Owner:** JARVIS Infrastructure  
**Status:** Living Document

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT TIER                                 │
├──────────────────┬──────────────────┬──────────────────────────────┤
│  Browser UI      │   Mobile Apps    │   API Clients                │
│  (React)         │   (React Native) │   (Third-party integrations) │
└────────┬─────────┴────────┬─────────┴──────────────┬───────────────┘
         │                  │                        │
         └──────────────────┼────────────────────────┘
                            │
         ┌──────────────────▼────────────────────────┐
         │    AWS Application Load Balancer          │
         │    (HTTPS, TLS 1.3, SSL termination)      │
         └──────────────────┬────────────────────────┘
                            │
         ┌──────────────────▼────────────────────────┐
         │    API TIER (FastAPI)                     │
         │    - Authentication & Authorization       │
         │    - Request validation & routing         │
         │    - Error handling & logging             │
         │    - Rate limiting & throttling           │
         └──────┬─────────────────────────────┬──────┘
                │                             │
    ┌───────────▼──────────────┐  ┌──────────▼──────────────┐
    │   BUSINESS LOGIC LAYER   │  │  AI OPERATIONS LAYER    │
    │                          │  │                         │
    │ - Service catalog        │  │ - LLM router            │
    │ - Billing & invoicing    │  │ - Cost tracking         │
    │ - CRM integration        │  │ - Quality assurance     │
    │ - Approval workflows     │  │ - Failure handling      │
    │ - Team routing           │  │ - Provider management   │
    │ - Scheduling             │  │                         │
    └──────┬───────────────────┘  └──────────┬──────────────┘
           │                                 │
           └─────────────┬───────────────────┘
                         │
           ┌─────────────▼──────────────┐
           │   DATA PERSISTENCE LAYER   │
           │                            │
           │ - PostgreSQL 16 (primary)  │
           │ - Redis 7 (cache/sessions) │
           │ - S3 (file storage)        │
           └─────────────┬──────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼─────┐    ┌────▼──────┐  ┌───▼──────┐
    │ PostgreSQL   │    │ Redis  │  │   S3     │
    │ (Data)   │    │ (Cache)│  │(Files) │
    └──────────┘    └────────┘  └────────┘
         │               │
    ┌────▼──────────────▼──────────────┐
    │   EXTERNAL INTEGRATIONS          │
    │                                  │
    │ ├─ LLM Providers (11)            │
    │ ├─ Email Services (Stripe email) │
    │ ├─ Payment Processors (Stripe)   │
    │ ├─ Communication (Slack, Telegram)
    │ ├─ CRM/Sales (HubSpot, Apollo)   │
    │ ├─ Monitoring (Prometheus)       │
    │ ├─ Scheduling (APScheduler)      │
    │ └─ Cloud (AWS)                   │
    └────────────────────────────────┘
```

---

## 2. Request Flow Diagram

### User → API → Response Journey

```
┌─────────────────────────────────────────────────────────────────────┐
│                    User Browser Request                             │
│                   GET /api/v1/monitoring                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │ AWS ALB receives HTTPS request       │
         │ - Validates TLS certificate         │
         │ - Decrypts payload                  │
         │ - Routes to ECS Fargate task        │
         └───────────────────┬──────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │ FastAPI Application Entry           │
         │ - Middleware: Request ID generation │
         │ - Middleware: Timing measurement    │
         │ - CORS validation                   │
         │ - Query parameter parsing           │
         └───────────────────┬──────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │ Authentication Middleware           │
         │ - Extract Authorization header      │
         │ - Validate OIDC token              │
         │ - Extract tenant_id from token     │
         └───────────────────┬──────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │ Route Handler: monitoring.py        │
         │ - Dependency injection (get_db)    │
         │ - Business logic layer             │
         └───────────────────┬──────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │ Database Query Layer                │
         │ SELECT * FROM metrics               │
         │ WHERE tenant_id = {authenticated}   │
         └───────────────────┬──────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │ PostgreSQL 16 Query Execution      │
         │ - Connection from pool              │
         │ - Execute parameterized query      │
         │ - Return result set                |
         └───────────────────┬──────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │ Serialize Response to JSON          │
         │ - Cast datetime to ISO 8601         │
         │ - Round floats to 4 decimals        │
         │ - Nest object structure             │
         └───────────────────┬──────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │ Response Middleware                 │
         │ - Add X-Request-ID header          │
         │ - Add timing headers               │
         │ - Add security headers             │
         │ - Set Cache-Control                │
         └───────────────────┬──────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │ ALB → Browser                       │
         │ HTTPS 200 OK                        │
         │ Content-Type: application/json      │
         │ Body: {...}                         │
         └─────────────────────────────────────┘
```

---

## 3. Database Integration

### PostgreSQL Schema Overview

**Core Tables:**

```
┌─────────────────────────────────────────────────────────────┐
│                    MULTI-TENANT TABLES                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ clients (Revenue Model)                                     │
│  ├─ id (UUID primary key)                                   │
│  ├─ tenant_id (UUID, indexed)                              │
│  ├─ name, email, status                                     │
│  ├─ mrr_usd (monthly recurring revenue)                     │
│  └─ [15+ fields]                                            │
│                                                             │
│ ai_request_log (Cost Tracking)                              │
│  ├─ id (UUID)                                               │
│  ├─ tenant_id (UUID, indexed)                              │
│  ├─ provider, model                                         │
│  ├─ tokens_used, cost_estimate_usd                          │
│  ├─ latency_ms, created_at                                  │
│  └─ [~35 rows per day per active tenant]                    │
│                                                             │
│ approval_request (Workflow)                                 │
│  ├─ id (UUID)                                               │
│  ├─ tenant_id (UUID, indexed)                              │
│  ├─ status (pending, approved, rejected)                    │
│  ├─ risk_level (critical, high, medium, low)                │
│  └─ [10+ fields]                                            │
│                                                             │
│ scheduler_job (Automation Engine)                           │
│  ├─ id (UUID)                                               │
│  ├─ tenant_id (nullable — some jobs are global)            │
│  ├─ job_name, trigger_type                                  │
│  ├─ last_run, next_run                                      │
│  └─ [64 total jobs: 38 core + 26 AIONX]                     │
│                                                             │
│ leads (Sales)                                               │
│  ├─ id (UUID)                                               │
│  ├─ tenant_id (UUID, indexed)                              │
│  ├─ name, email, company                                    │
│  ├─ status (new, qualified, contacted, won)                 │
│  ├─ score (AI-assigned ICP match score)                     │
│  └─ [20+ fields]                                            │
│                                                             │
│ ... [25+ more tables]                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Indexing Strategy:**

```sql
-- Most important indexes for query performance
CREATE INDEX idx_clients_tenant_id ON clients(tenant_id);
CREATE INDEX idx_ai_request_log_tenant_id_created ON ai_request_log(tenant_id, created_at DESC);
CREATE INDEX idx_ai_request_log_provider ON ai_request_log(provider);
CREATE INDEX idx_approval_request_tenant_status ON approval_request(tenant_id, status);
CREATE INDEX idx_leads_tenant_score ON leads(tenant_id, score DESC);
CREATE INDEX idx_scheduler_job_next_run ON scheduler_job(next_run);

-- Composite index for common cost queries
CREATE INDEX idx_cost_by_provider_day ON ai_request_log(tenant_id, DATE(created_at), provider);
```

**Connection Pooling:**

```
PostgreSQL Connection Pool
├─ Pool size: 20 connections
├─ Min idle: 5 connections
├─ Max overflow: 10 connections
├─ Connection timeout: 30 seconds
└─ Idle timeout: 30 minutes (auto-close)

Benefits:
- Reuse connections (no new connection overhead)
- Prevent connection exhaustion
- Handle spikes gracefully
- Auto-cleanup idle connections
```

### Redis Integration

**Use Cases:**

```
Redis Cache Layer
├─ Session management (user auth tokens)
├─ Rate limiting (token bucket per user/IP)
├─ Cost tracking cache (5-minute aggregations)
├─ Health check cache (30-second provider status)
└─ Request deduplication (5-minute window)

Configuration:
├─ Host: redis://localhost:6379
├─ Database: 0 (main), 1 (cache), 2 (sessions)
├─ TTL: 300s (5 min) for most data
├─ Eviction: LRU (least recently used)
└─ Persistence: RDB + AOF for critical data
```

---

## 4. LLM Provider Integration

### Provider Configuration

Each provider has standardized interface:

```
Provider Config Structure:
├─ name (string)
├─ base_url (string)
├─ api_key_env_var (string)
├─ models (dict)
│  ├─ model_name: {
│  │   ├─ cost_per_1m_input_tokens
│  │   ├─ cost_per_1m_output_tokens
│  │   ├─ max_context_length
│  │   ├─ max_output_tokens
│  │   └─ supports_streaming
│  │ }
├─ rate_limits (dict)
│  ├─ requests_per_minute
│  ├─ tokens_per_minute
│  └─ requests_per_day
├─ health_check_url
└─ is_active (boolean)
```

**Provider API Adapters:**

```
backend/app/services/ai/providers/
├─ __init__.py (provider registry)
├─ anthropic_provider.py (Claude)
├─ openai_provider.py (GPT-4o)
├─ gemini_provider.py (Gemini)
├─ deepseek_provider.py (DeepSeek)
├─ groq_provider.py (Llama)
├─ mistral_provider.py (Mistral)
└─ [5 more providers]

Each adapter implements:
├─ async call_api(prompt, model, **kwargs)
├─ async get_health()
├─ calculate_cost(tokens_in, tokens_out)
└─ handle_errors(error) → retry or failover
```

---

## 5. External API Integration Map

### Payment Processing (Stripe)

**Integration Points:**

```
Webhook Flows:
┌─ Customer clicks "Subscribe" on pricing page
│  └─ Redirects to Stripe Checkout → payment_links = {API}
│
├─ Customer completes payment
│  └─ Stripe sends webhook to /api/v1/payments/webhook
│  └─ JARVIS creates subscription in database
│  └─ Sets MRR on client record
│
├─ Monthly billing cycle (automated)
│  └─ Invoice generation: /api/v1/billing/invoice-ready
│  └─ Stripe charges via PaymentIntent API
│
└─ Customer cancels subscription
   └─ Webhook: invoice.payment_failed
   └─ JARVIS sets client.status = "PAUSED"
   └─ Stops API access in middleware
```

**Data Model:**

```
Stripe Integration:
├─ public_key (Stripe publishable key)
├─ secret_key (AWS Secrets Manager)
├─ webhook_secret (AWS Secrets Manager)
├─ API endpoint: https://api.stripe.com/v1/
└─ Webhook endpoint: /api/v1/payments/webhook

For each client:
├─ stripe_customer_id (Customer)
├─ stripe_subscription_id (Subscription)
├─ stripe_payment_method_id (PaymentMethod)
└─ billing_email
```

### CRM Integration (HubSpot)

**Sync Direction:**

```
JARVIS → HubSpot (Outbound)
├─ Create/update contacts (email, name, company)
├─ Create deals (sales pipeline stages)
├─ Add notes (interaction history)
└─ Schedule: Real-time (immediately after action)

HubSpot → JARVIS (Inbound)
├─ Webhook: Contact updated
├─ Webhook: Deal moved to stage
├─ Schedule: Real-time via webhook
└─ Fallback: Daily sync at 02:00 UTC

Data Mapping:
HubSpot Contact ←→ JARVIS Lead
├─ firstname + lastname ↔ name
├─ email ↔ email
├─ company ↔ company
├─ lifecyclestage ↔ status
└─ hs_lead_status ↔ score_confidence
```

### Email Integration (AWS SES)

**Outbound Email Flow:**

```
Action: Send outreach email
  1. Generate personalized email in JARVIS
  2. Store in database (email_campaign)
  3. Queue to SES via boto3
  4. SES sends SMTP
  5. Receive webhook (delivery, bounce, complaint)
  6. Update email status in database

Rate Limiting:
  ├─ SES limit: 14 emails/second (default)
  ├─ JARVIS limit: 10/second (safe margin)
  └─ Queue management: Batch send during off-peak

Cost:
  ├─ SES: $0.10 per 1,000 emails
  ├─ Volume: 10,000 emails/month = $1.00
  └─ Total: Negligible compared to LLM costs
```

### Communication Integration (Slack/Telegram)

**Outbound Notifications:**

```
Alert Types:
├─ Daily briefing (08:00 UTC)
├─ High-cost alert (>$100/day)
├─ Provider failure (circuit opened)
├─ Customer signup (real-time)
└─ Approval needed (immediate)

Slack Integration:
├─ API: https://slack.com/api/
├─ Authentication: OAuth token (in Secrets Manager)
├─ Endpoint: channels.list, chat.postMessage
├─ Format: Rich blocks (includes buttons, charts)

Telegram Integration:
├─ API: https://api.telegram.org/bot{TOKEN}/
├─ Authentication: Bot token (in Secrets Manager)
├─ Endpoint: sendMessage, sendPhoto, sendDocument
├─ Format: Markdown for text, inline keyboards for buttons
```

---

## 6. Data Flow Patterns

### Daily Cost Tracking Flow

```
Time 08:00 UTC (Morning)
  ├─ Scheduler job: daily_cost_summary runs
  │
  ├─ Query AIRequestLog for yesterday's requests
  │  └─ SELECT * FROM ai_request_log
  │     WHERE DATE(created_at) = yesterday
  │     GROUP BY tenant_id, provider
  │
  ├─ Aggregate costs by tenant and provider
  │  └─ SUM(cost_estimate_usd) for each group
  │
  ├─ Store in daily_cost_summary table
  │  └─ INSERT INTO daily_cost_summary (...)
  │
  ├─ Cache in Redis (5-minute TTL)
  │  └─ SET daily_cost:{tenant_id} {json_data}
  │
  ├─ Send Slack briefing to Captain
  │  └─ POST to Slack API with summary + trends
  │
  └─ Mark job as completed in scheduler_job table

Latency: ~2 seconds (aggregation across millions of rows)
Reliability: 99.9% (transactional, self-healing)
Cost: Negligible (database-internal operation)
```

### Lead Scoring Pipeline

```
Time: Real-time (Trigger: New lead ingested)

Step 1: Lead Ingested
  ├─ Source: API, form, import, CRM sync
  ├─ Data: name, email, company, industry
  └─ Status: new (needs scoring)

Step 2: Queue to AI Engine
  ├─ Add to batch queue (max 100, max 5s wait)
  ├─ Task type: FAST (simple scoring)
  └─ Priority: normal

Step 3: AI Scoring
  ├─ Route to DeepSeek (cheap, fast)
  ├─ Score against ICP (0-100)
  ├─ Estimate probability of close
  └─ Assign to sales team

Step 4: Database Update
  ├─ UPDATE leads SET score = {score}
  ├─ Set status = qualified (if score > 70)
  └─ Timestamp: {created_at}

Step 5: CRM Sync
  ├─ Send to HubSpot via API
  ├─ Create deal if qualified
  └─ Assign to team member

Step 6: Notification
  ├─ Send Slack to sales team
  ├─ "New qualified lead: Acme Corp (score: 87)"
  └─ Include AI reasoning (3-4 sentences)

End-to-end latency: 5-10 seconds
Cost: $0.0002 per lead (AI only)
Automation: 100% hands-free
```

---

## 7. Error Handling & Resilience Patterns

### Database Connection Failure

```
Request arrives → Database query
  ├─ Try connection from pool
  │  ├─ Available? → Use it
  │  └─ Not available? → Wait (30s timeout)
  │
  ├─ Connection timeout
  │  ├─ Log error with request ID
  │  ├─ Alert Captain: "DB connection pool exhausted"
  │  └─ Return HTTP 503 (service unavailable)
  │
  └─ After 5 minutes
     ├─ Auto-restart application (health check fails)
     └─ ECS replaces failed task with new one
```

### LLM Provider Timeout

```
Request to Claude → Timeout (30s)
  ├─ Retry 1: Wait 1s, try again → Timeout
  ├─ Retry 2: Wait 2s, try again → Timeout
  ├─ Exhausted retries to Claude
  │
  ├─ Failover to fallback: GPT-4o
  ├─ Send request → Success (8s latency)
  │
  ├─ Log to database
  │  ├─ provider: claude → gpg-4o (fallback)
  │  ├─ cost: charged both Claude attempts + GPT-4o success
  │  └─ latency: 30 + 30 + 1 + 8 = 69s total
  │
  └─ Return to user (successful, user doesn't know about failover)
```

### Cascading Failures (All Providers Down)

```
Scenario: Stripe API down + OpenAI down + Claude down + Gemini down

Action: Receive request to charge customer
  ├─ Try payment processing
  │  └─ Stripe timeout → Fail
  │
  ├─ Try generating invoice
  │  └─ Need cost summary from Claude → Fail
  │
  ├─ Emergency mode activated
  │  ├─ Return cached previous month's data
  │  ├─ Add note: "Using cached data; live data will update when services recover"
  │  └─ Return HTTP 202 (accepted, processing)
  │
  ├─ Queue background retry
  │  └─ Retry every 5 minutes until successful
  │
  └─ Alert Captain immediately
     ├─ SMS: "Multiple critical systems down"
     ├─ Slack: Details + action items
     └─ Create incident in log
```

---

## 8. Security & Isolation

### Multi-Tenant Data Isolation

```
Every Query Has Mandatory tenant_id Filter

Middleware Layer (Security Boundary):
  1. Extract token from Authorization header
  2. Validate OIDC token signature
  3. Extract tenant_id from token claims
  4. Store in request context

Service Layer (Data Access):
  Every query automatically includes:
  WHERE tenant_id = {authenticated_tenant_id}

Example:
  SELECT * FROM leads WHERE tenant_id = ?
                     ↑─ Required parameter, no default

Protection:
  ├─ If parameter missing → Query fails (no default)
  ├─ If parameter wrong → Query returns empty (wrong tenant data)
  └─ No cross-tenant data leakage possible
```

### Secrets Management

```
Secrets Storage (AWS Secrets Manager)

Never in code:
  ❌ LLM API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
  ❌ Database password
  ❌ Stripe secret key
  ❌ AWS access keys
  ❌ OAuth tokens

Always in .env (local development):
  ✅ .env file (git ignored)
  ✅ Never committed to GitHub
  ✅ Loaded at startup

Production retrieval:
  1. ECS task starts
  2. IAM role authorizes access
  3. boto3 fetches from Secrets Manager
  4. Environment variable set
  5. Application reads from env var

Rotation:
  ├─ Automated (Secrets Manager supports auto-rotation)
  ├─ No app changes needed
  └─ New keys work immediately
```

---

## 9. Deployment Integration

### Docker Compose (Local Development)

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: jarvis
      POSTGRES_PASSWORD: jarvis_password
      POSTGRES_DB: jarvis
    ports: ['5432:5432']

  redis:
    image: redis:7
    ports: ['6379:6379']

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://jarvis:jarvis_password@postgres:5432/jarvis
      REDIS_URL: redis://redis:6379/0
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports: ['8000:8000']
    depends_on: ['postgres', 'redis']

  frontend:
    build: ./frontend
    environment:
      REACT_APP_API_URL: http://localhost:8000
    ports: ['5173:5173']
    depends_on: ['backend']
```

### AWS ECS Deployment (Production)

```
Infrastructure as Code (Terraform):

├─ Network Layer
│  ├─ VPC (10.0.0.0/16)
│  ├─ 3 subnets (private, public × 2)
│  └─ Internet Gateway + NAT Gateway
│
├─ Compute Layer
│  ├─ ECS Fargate cluster
│  ├─ Task definition (CPU: 2, Memory: 4GB)
│  ├─ Auto-scaling policy (scale 2-10 tasks)
│  └─ Health check (/health endpoint)
│
├─ Load Balancer
│  ├─ Application Load Balancer (ALB)
│  ├─ Target group (port 8000)
│  ├─ SSL certificate (ACM)
│  └─ HTTPS listener (port 443)
│
├─ Database Layer
│  ├─ RDS PostgreSQL 16
│  ├─ Multi-AZ (primary + standby)
│  ├─ Automated backups (35-day retention)
│  └─ Encryption at rest (AWS KMS)
│
├─ Cache Layer
│  ├─ ElastiCache Redis 7
│  ├─ Cluster mode enabled
│  └─ Automatic failover
│
└─ Storage
   ├─ S3 bucket (file uploads, backups)
   ├─ Versioning enabled
   └─ Encryption at rest
```

---

## 10. System Integration Checklist

Before launching a new feature:

- [ ] Database tables created and indexed
- [ ] API endpoint registered in `__init__.py`
- [ ] Frontend component added to App.jsx VIEWS
- [ ] API service client added to `monitoringApi.js`
- [ ] Error handling implemented (try/catch)
- [ ] Logging added (request ID tracing)
- [ ] Multi-tenant isolation enforced (tenant_id filter)
- [ ] Cost tracking enabled (if applicable)
- [ ] Cache strategy defined (Redis TTL)
- [ ] Rate limiting applied (if external API)
- [ ] Monitoring metrics added (Prometheus)
- [ ] Documentation updated
- [ ] Integration tests written
- [ ] Deployed to staging environment
- [ ] Smoke tests passed
- [ ] Performance benchmarked
- [ ] Security audit completed
- [ ] Deployed to production (blue-green)

---

**Document Authority:** JARVIS Infrastructure & Integration Team  
**Last Updated:** 2026-07-02  
**Next Review:** 2026-08-02  
**Maintained by:** System Architecture Council
