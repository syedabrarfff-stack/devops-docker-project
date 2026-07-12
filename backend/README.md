# JARVIS Backend — FastAPI + SQLAlchemy

The backend is a FastAPI application with SQLAlchemy 2.0 async ORM, providing 47 API routers (68+ endpoints), multi-provider AI routing, 64 scheduled jobs, and a complete operational intelligence core.

---

## Overview

| Component | Details |
|---|---|
| **Framework** | FastAPI (async) with Pydantic v2 |
| **Database** | SQLAlchemy 2.0 async + PostgreSQL 16 |
| **Cache** | Redis 7 (rate limiting, queues) |
| **Scheduler** | APScheduler 3.10 (64 jobs) |
| **AI Router** | 13+ providers with circuit breakers |
| **Models** | 40+ SQLAlchemy tables (8 domains) |
| **Routes** | 47 routers, 68+ endpoints |
| **Monitoring** | Prometheus, structured logging, X-Request-ID |

---

## Project Structure

```
backend/
├── app/
│   ├── api/v1/
│   │   ├── __init__.py              # Route registration (47 routers)
│   │   ├── routes/                  # 68 route modules
│   │   │   ├── chat.py              # AI chat endpoint
│   │   │   ├── leads.py             # Lead discovery & management
│   │   │   ├── outreach.py          # Email & outreach automation
│   │   │   ├── proposals.py         # Proposal generation & approval
│   │   │   ├── scheduler.py         # Job management & status
│   │   │   ├── intelligence.py      # Briefings & market intel
│   │   │   ├── ai_ops.py            # AI provider health & routing
│   │   │   ├── aionx.py             # AIONX sovereign organs
│   │   │   ├── nexus.py             # Supreme intelligence core
│   │   │   └── ...                  # 60+ more route modules
│   │   └── dependencies.py          # Shared dependencies (auth, pagination)
│   │
│   ├── services/
│   │   ├── ai/
│   │   │   ├── router.py            # Multi-provider router (13 providers)
│   │   │   ├── base_provider.py     # Abstract provider interface
│   │   │   └── providers/           # Concrete provider implementations
│   │   │       ├── anthropic_provider.py
│   │   │       ├── openai_provider.py
│   │   │       ├── bedrock_provider.py
│   │   │       ├── openrouter_provider.py
│   │   │       ├── nvidia_provider.py
│   │   │       └── ...
│   │   │
│   │   ├── scheduler/
│   │   │   ├── engine.py            # APScheduler initialization & core 38 jobs
│   │   │   └── job_failure.py       # Failure tracking & escalation
│   │   │
│   │   ├── aionx/
│   │   │   ├── aionx_scheduler.py   # 26 AIONX organ job registration
│   │   │   ├── sentinel_layer.py    # Threat & signal monitoring
│   │   │   ├── orchestration_cortex.py   # Decision & event routing
│   │   │   ├── decision_memory_engine.py # Retrospectives
│   │   │   ├── client_digital_twin.py    # Churn/upsell prediction
│   │   │   └── ...
│   │   │
│   │   ├── leads/
│   │   │   ├── engine.py            # Lead discovery orchestration
│   │   │   ├── scoring.py           # ICP scoring & ranking
│   │   │   └── discovery.py         # Apollo/Google Maps integration
│   │   │
│   │   ├── outreach/
│   │   │   ├── engine.py            # Sequence execution
│   │   │   ├── reply_handler.py     # AI classification of replies
│   │   │   ├── gmail.py             # Gmail sender
│   │   │   └── aws_ses_sender.py    # SES high-volume sender
│   │   │
│   │   ├── intelligence/
│   │   │   ├── morning_briefing.py
│   │   │   ├── market_intelligence.py
│   │   │   ├── tech_radar.py
│   │   │   └── ...
│   │   │
│   │   ├── notifications/
│   │   │   ├── telegram.py
│   │   │   ├── email_sender.py
│   │   │   └── slack.py
│   │   │
│   │   └── governance/
│   │       ├── proposal_generator.py
│   │       ├── approval_engine.py
│   │       └── invoice_engine.py
│   │
│   ├── models/
│   │   ├── __init__.py              # Model registry (40+ models)
│   │   ├── base.py                  # JarvisBase (common columns)
│   │   ├── tenant.py                # Tenancy & user management
│   │   ├── lead.py                  # Lead & scoring models
│   │   ├── outreach.py              # Email & reply models
│   │   ├── revenue.py               # Invoice, payment models
│   │   ├── memory.py                # Memory layer models
│   │   ├── intelligence.py          # Briefing, tech radar models
│   │   ├── aionx_organs.py          # AIONX sovereign organ models
│   │   ├── approval.py              # Approval workflow models
│   │   ├── governance.py            # Contracts, proposals
│   │   └── ...                      # 30+ model modules
│   │
│   ├── core/
│   │   ├── config.py                # Settings & environment (50+ vars)
│   │   ├── database.py              # AsyncSessionLocal & init_db()
│   │   ├── security.py              # JWT, authorization
│   │   └── constants.py
│   │
│   ├── middleware.py                # Request ID, response time, error envelope
│   └── main.py                      # FastAPI app initialization
│
├── alembic/                         # Database migrations
│   ├── versions/                    # Migration files
│   └── env.py
│
├── tests/                           # Unit & integration tests
│   ├── conftest.py
│   ├── test_ai_router.py
│   ├── test_scheduler.py
│   └── ...
│
└── requirements.txt                 # Python dependencies
```

---

## Installation & Setup

### Prerequisites

```bash
python --version      # 3.11+
pip --version         # 22.0+
```

### Local Development

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Copy environment file
cp .env.example .env
# Edit .env with your API keys (see Configuration)

# 3. Start database & Redis (via Docker Compose)
docker-compose up -d postgres redis

# 4. Initialize database
cd backend
python -m alembic upgrade head

# 5. Run development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**API will be available at:**
- http://localhost:8000 (API root)
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

---

## Configuration

### Required Environment Variables

**AI Providers (at least one):**
```bash
ANTHROPIC_API_KEY=sk-ant-...           # Claude (primary)
OPENROUTER_API_KEY=sk-or-v1-...        # OpenRouter (fallback)
OPENAI_API_KEY=sk-...                  # GPT-4
GOOGLE_API_KEY=...                     # Gemini
```

**Database & Cache:**
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/jarvis
REDIS_URL=redis://localhost:6379/0
```

**Email & Notifications:**
```bash
SES_FROM_EMAIL=your-verified-sender@example.com
TELEGRAM_BOT_TOKEN=123456:ABCdefGHIjklmnoPQRstuvWXYZ
TELEGRAM_CHAT_ID=123456789
```

**Payments:**
```bash
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

**Application:**
```bash
APP_VERSION=1.0.0
JARVIS_DEFAULT_TENANT_ID=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa
DEBUG=false
```

**AWS (optional for production):**
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-south-2
```

See `.env.example` for all 50+ variables.

---

## API Reference

### Core Endpoints

#### AI Chat (Multi-Provider)

```bash
POST /api/v1/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Hello"},
  ],
  "task_type": "GENERAL",    # or FAST, ANALYSIS, CODE, REASONING, etc.
  "max_tokens": 2048
}

# Response
{
  "content": "...",
  "model": "claude-sonnet",
  "provider": "anthropic",
  "tokens_used": 256,
  "latency_ms": 1234
}
```

#### Lead Discovery

```bash
POST /api/v1/leads/discover
Content-Type: application/json

{
  "query": "SaaS operations automation",
  "country": "UK",
  "limit": 10
}

# Response
[
  {
    "id": "uuid",
    "company_name": "...",
    "contact_name": "...",
    "email": "...",
    "score": 85.5
  }
]
```

#### Outreach Execution

```bash
POST /api/v1/outreach/send
Content-Type: application/json

{
  "lead_id": "uuid",
  "template_id": "sequence-1",
  "step": 1
}

# Response
{
  "status": "sent",
  "email_id": "uuid",
  "sent_at": "2024-07-02T10:30:00Z"
}
```

#### Scheduler Management

```bash
# List jobs
GET /api/v1/scheduler/jobs

# Get job details
GET /api/v1/scheduler/jobs/{job_id}

# Pause job
POST /api/v1/scheduler/jobs/{job_id}/pause

# Resume job
POST /api/v1/scheduler/jobs/{job_id}/resume
```

#### Intelligence Briefing

```bash
GET /api/v1/intelligence/briefing

# Response
{
  "date": "2024-07-02",
  "leads_discovered": 15,
  "leads_scored": 42,
  "emails_sent": 8,
  "pipeline_value": 125000,
  "alerts": []
}
```

---

## AI Provider Routing

### How It Works

JARVIS routes each task to the best-suited model based on task type and provider performance:

```
Task Type     Primary              Fallback 1           Fallback 2
───────────────────────────────────────────────────────────────
FAST          deepseek-flash       llama-3.3            gpt-4o-mini
GENERAL       claude-sonnet        gpt-4o               gemini-pro
ANALYSIS      openrouter (stable)  nvidia-nims          llama-90b
CODE          claude-sonnet        deepseek-coder       gpt-4o
REASONING     claude-opus          gpt-4o               gemini-pro
STRATEGY      claude-opus          gpt-4o               claude-sonnet
RESEARCH      gemini-pro           gpt-4o               claude-sonnet
SALES         claude-sonnet        gpt-4o-mini          deepseek-flash
```

### Providers Implemented

| Provider | Models | Status | Fallback |
|---|---|---|---|
| Anthropic | Claude 3.5 Sonnet, Haiku, Opus | ✅ Active | Primary |
| OpenRouter | 100+ models via unified gateway | ✅ Active | Stable endpoint |
| OpenAI | GPT-4, GPT-4 Mini | ✅ Active | Premium models |
| Google | Gemini Pro | ✅ Active | Research tasks |
| NVIDIA NIM | DeepSeek, Llama, Mistral | ✅ Active | Distributed inference |
| Groq | Fast inference | ✅ Active | Speed-critical |
| AWS Bedrock | Claude, Titan | ⚙️ Configured | Optional |
| DeepSeek | V4 Pro, V4 Turbo, R1 | ✅ Active | Analysis tasks |

### Circuit Breaker Protection

Each provider has:
- **Timeout:** 60 seconds per call
- **Rate limit detection:** 429 response handling
- **Failure threshold:** 3 consecutive failures → switch provider
- **Recovery:** 5-minute cooldown before retry

---

## Database Schema (40+ Tables)

### Core Tables

**Tenancy Domain:**
- `tenant` — Organization/customer
- `user` — User accounts with roles
- `tenant_api_key` — API authentication

**Lead Domain:**
- `lead` — Discovered prospects
- `lead_score_snapshot` — Historical scores
- `icp_characteristic` — ICP profile definition

**Outreach Domain:**
- `outreach_email` — Email campaigns
- `reply_log` — Prospect replies
- `reply_classification` — AI classification results
- `follow_up_queue` — Sequence queue

**Revenue Domain:**
- `client` — Paying customers
- `invoice` — Billing records
- `payment` — Transaction records
- `revenue_snapshot` — Monthly snapshots

**Memory Domain:**
- `memory_episodic` — Short-term events
- `memory_semantic` — Long-term knowledge
- `memory_instruction` — Permanent instructions
- `memory_graph_node` — Entities
- `memory_graph_edge` — Relationships

**Intelligence Domain:**
- `briefing_history` — Briefing content
- `market_intelligence` — Market signals
- `tech_radar_entry` — Emerging tech
- `competitor_profile` — Competitive data

**Governance Domain:**
- `approval_request` — Approval workflows
- `proposal` — Sales proposals
- `contract` — Customer contracts
- `audit_log` — Activity audit trail

**AIONX Organs Domain:**
- `decision_object` — AI decisions
- `client_digital_twin` — Predictive models
- `sentinel_observation` — Signal monitoring
- `wisdom_index_snapshot` — Institutional learning

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head

# Rollback one version
alembic downgrade -1

# Show migration status
alembic current
```

---

## Scheduler Jobs (64 Total)

### Core Jobs (38)

**Briefing & Intelligence (5 jobs):**
- `daily_briefing` — 08:00 UTC — Captain morning briefing
- `morning_briefing` — 07:00 UTC — Intelligence briefing
- `captain_dashboard_briefing` — 06:55 UTC — Dashboard snapshot

**Lead Operations (4 jobs):**
- `lead_scoring_sweep` — every 6h — Score discovered leads
- `daily_icp_lead_scoring` — 05:00 UTC — Score new leads, promote top 20
- `lead_embedding_sweep` — 03:15 UTC — Semantic embeddings for leads

**Outreach Automation (6 jobs):**
- `outreach_processor` — every 1h — Send queued emails
- `reply_handler_scan` — every 2h — Classify replies, advance leads
- `overnight_cold_outreach` — 20:30 UTC — US afternoon prime time
- `overnight_followup_sequences` — 23:30 UTC — US evening follow-ups
- `overnight_freelance_bids` — 21:30 UTC — Upwork/PPH bid sweep

**Memory & Learning (3 jobs):**
- `daily_self_learning` — 00:05 UTC — JARVIS self-evolution
- `memory_consolidation` — 00:30 UTC — Working → operational memory
- `weekly_memory_promotion` — Sun 00:45 UTC — Operational → strategic

**Intelligence & Market (5 jobs):**
- `tech_radar_scan` — Mon 06:00 UTC — Emerging tech tracking
- `competitor_monitoring` — Mon 09:00 UTC — Competitive landscape
- `market_intelligence_report` — Sun 07:00 UTC — Market signals
- `daily_optimization_review` — 23:00 UTC — System tuning
- `biweekly_research_report` — Sun 07:00 UTC — Deep research

**Overnight Revenue Engine (8 jobs):**
- `overnight_lead_discovery` — 18:00 UTC — Lead discovery
- `overnight_intel_analysis` — 18:30 UTC — Market analysis
- `overnight_proposal_engine` — 19:30 UTC — Generate proposals
- `overnight_pipeline_health` — 01:00 UTC — Health check
- `overnight_ops_report` — 02:30 UTC — Morning report

**Advanced Operations (7 jobs):**
- `daily_strategy_report` — 23:00 UTC — Strategy cascade
- `milestone_bulk_review` — 10:00 UTC — Council review
- `tech_evolution_scan` — every 6h — 24/7 discovery
- `pre_call_briefing_trigger` — every 30m — Call preparation
- `weekly_strategy_review` — Sun 07:00 UTC — Strategic review
- `dio_health_check` — 06:30 UTC — DIO verification
- `self_healer` — every 15m — Autonomous repair

### AIONX Organ Jobs (26)

Registered via `register_aionx_jobs()` from `aionx_scheduler.py`:

- `aionx_sentinel_sweep` — every 2h — Threat monitoring
- `aionx_escalation_processor` — every 30m — Event routing
- `aionx_operational_iq` — every 1h — System IQ computation
- `aionx_retro_30d` / `aionx_retro_90d` — Decision retrospectives
- `aionx_twin_predictions` — 03:00 UTC — Churn prediction refresh
- `aionx_wisdom_weekly` — Sun 19:00 UTC — Institutional learning
- And 19 more specialized jobs

---

## Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ai_router.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run with verbose output
pytest -v
```

### Integration Test

```bash
# Full end-to-end test (requires running backend)
python scripts/integration_test.py

# Tests cover:
# - Tenant creation
# - Lead discovery
# - Outreach queuing
# - Reply handling
# - Proposal generation
# - Approval workflow
# - Briefing generation
```

### AI Provider Verification

```bash
# Test all configured providers
python scripts/test-ai-providers.py

# Tests all 8 task types for:
# - Provider availability
# - Timeout compliance
# - Response quality
# - Fallback chain activation
```

---

## Monitoring

### Health Checks

```bash
# Liveness check (quick)
curl http://localhost:8000/health

# Response
{
  "status": "ok",
  "system": "JARVIS",
  "company": "Aliyar Solutions",
  "version": "1.0.0"
}

# Deep readiness check
curl http://localhost:8000/readyz

# Response
{
  "status": "ready",
  "database": "connected",
  "redis": "connected",
  "scheduler": "running",
  "checks": {
    "database": true,
    "redis": true,
    "scheduler": true,
    "config": true
  }
}
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Available metrics:
# - request_duration_seconds
# - request_count
# - ai_provider_cost_usd
# - scheduler_job_duration_seconds
# - scheduler_job_failure_count
```

### Logs

```bash
# View application logs
docker-compose logs -f backend

# View scheduler logs
docker-compose logs -f backend | grep "Scheduler:"

# View AI router logs
docker-compose logs -f backend | grep "AIRouter"
```

---

## Common Tasks

### Adding a New API Route

1. Create route file: `app/api/v1/routes/my_feature.py`
2. Define router and endpoints
3. Register in `app/api/v1/__init__.py`:
   ```python
   from app.api.v1.routes import my_feature
   api_router.include_router(my_feature.router)
   ```

### Adding a Scheduled Job

`app/services/scheduler/scheduler.py` is the single canonical scheduler —
there is no other one. (A second module, `engine.py`, existed alongside it
until Task #23; it was never started in production and was deleted once
every job and consumer was migrated off it. If you see `engine.py`
referenced anywhere, that reference is stale.)

1. Define the job function directly in `scheduler.py`, following the
   existing pattern — no manual try/except needed, `run_registered_production_job`
   already wraps every job call with locking, retry, and failure recording:
   ```python
   async def my_task() -> None:
       result = await do_the_work()
       await _record_job_result("my_task", "success", result)
   ```

2. Add it to `_production_job_specs()` and `PRODUCTION_JOB_IDS`:
   ```python
   {"job_id": "my_task", "func": my_task, "kind": "interval", "hours": 1},
   ```

### Adding a Database Model

1. Create model file: `app/models/my_domain.py`
2. Define SQLAlchemy class extending `JarvisBase`
3. Import in `app/models/__init__.py`
4. Create migration:
   ```bash
   alembic revision --autogenerate -m "Add my_domain model"
   alembic upgrade head
   ```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check for port conflicts
lsof -i :8000

# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip list | grep -E "fastapi|sqlalchemy"

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker-compose ps | grep postgres

# Test connection
psql postgresql://user:pass@localhost:5432/jarvis

# Check DATABASE_URL in .env
echo $DATABASE_URL

# Restart database
docker-compose restart postgres
```

### AI Provider Failure

```bash
# Test all providers
python scripts/test-ai-providers.py

# Check API keys
echo $ANTHROPIC_API_KEY | head -c 20

# Check provider health
curl http://localhost:8000/api/v1/ai/health
```

### Scheduler Jobs Not Running

```bash
# Check scheduler status
curl http://localhost:8000/api/v1/scheduler/jobs

# View scheduler logs
docker-compose logs -f backend | grep "Scheduler:"

# Restart scheduler
docker-compose restart backend

# Check job store
# Query: SELECT * FROM apscheduler_jobs;
```

---

## Performance Tips

1. **Database:** Use connection pooling (SQLAlchemy async)
2. **AI Calls:** Batch requests when possible
3. **Caching:** Redis for rate limiting, session caching
4. **Logging:** Use structured logging with request IDs
5. **Monitoring:** Check Prometheus metrics regularly

---

## Deployment

See `infrastructure/README.md` for Docker Compose and AWS ECS Fargate deployment instructions.

---

**Last Updated:** 2024-07-02  
**Version:** 1.0.0-MVP
