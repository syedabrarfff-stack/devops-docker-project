# JARVIS — TECHNOLOGY MAP
_Master architecture reference. Any model reads this to understand the full system._
_Last audited: 2026-06-19_

## System Overview

```
                    ┌─────────────────────────────────┐
                    │     CAPTAIN (Syed Abrar)         │
                    │  Telegram │ VS Code │ Web Browser │
                    └──────────┬──────────────────┬────┘
                               │                  │
              ┌────────────────▼──────────────┐   │
              │      ALB (Application         │   │
              │      Load Balancer)           │   │
              │   aliyarsolutions.com         │   │
              └────────────────┬──────────────┘   │
                               │                  │
       ┌───────────────────────▼──────────────────▼──┐
       │                   NGINX                       │
       │         (Reverse proxy, HSTS, CSP)            │
       └──────────┬───────────────────────────────────┘
                  │
       ┌──────────▼────────────────────────────────────┐
       │            JARVIS BACKEND (FastAPI)             │
       │  57 route modules │ ~411 endpoints             │
       │  Uvicorn async │ Gunicorn workers              │
       │                                                 │
       │  ┌──────────┐  ┌────────────┐  ┌───────────┐  │
       │  │ Rate Limiter│  │JWT Auth   │  │Middleware │  │
       │  │ slowapi   │  │(HS256 JWT) │  │X-Request  │  │
       │  │ Redis     │  │Captain only│  │-ID Tracing│  │
       │  └──────────┘  └────────────┘  └───────────┘  │
       └──────────┬───────────────────────────────────┘
                  │
       ┌──────────▼──────────────────────────────┐
       │           SERVICE LAYER                   │
       │  36 service directories │ ~202 files      │
       │                                           │
       │  ┌──────────┐  ┌──────────┐  ┌────────┐ │
       │  │ AI Router │  │ Scheduler│  │ AIONx  │ │
       │  │ 11 provid.│  │APScheduler  │ 32 files│ │
       │  │ 15 tasks  │  │ 7 jobs   │  │120+routes│ │
       │  └──────────┘  └──────────┘  └────────┘ │
       └──────────┬───────────────────────────────┘
                  │
       ┌──────────▼──────────────────────────────┐
       │           DATA LAYER                      │
       │                                           │
       │  PostgreSQL 16 (pgvector)                 │
       │  35 model files │ 29 migrations           │
       │  RLS multi-tenant isolation               │
       │                                           │
       │  Redis 7                                  │
       │  Rate limiting │ Sessions │ APScheduler   │
       └───────────────────────────────────────────┘
```

---

## Complete Stack Reference

### Backend
| Component | Version | Location |
|-----------|---------|----------|
| FastAPI | 0.115.5 | backend/app/main.py |
| SQLAlchemy | 2.0.36 (async) | backend/app/core/database.py |
| Alembic | 1.14.0 | backend/alembic/ |
| Pydantic | 2.10.3 | (built into FastAPI) |
| Uvicorn | 0.32.1 | uvicorn app.main:app |
| Gunicorn | 23.0.0 | production process manager |
| slowapi | 0.1.9 | backend/app/core/rate_limit.py |
| APScheduler | 3.10.4 | backend/app/services/scheduler/ |
| python-jose | 3.3.0 | JWT (HS256) auth |
| reportlab | 4.2.5 | PDF generation |

### Database
| Component | Version | Purpose |
|-----------|---------|---------|
| PostgreSQL | 16 | Primary data store |
| pgvector | latest | Semantic search (future) |
| Redis | 7 | Rate limits + sessions + scheduler state |
| AsyncPG | 0.30.0 | Async PostgreSQL driver |

### Frontend
| Component | Version | Location |
|-----------|---------|----------|
| React | 18 | frontend/src/ |
| Vite | latest | frontend/vite.config.js |
| Tailwind CSS | latest | Glassmorphism design system |
| Zustand | latest | frontend/src/store/useJarvisStore.js |
| Axios | latest | frontend/src/services/api.js |

### AI Layer
| Provider | API | Primary Use |
|----------|-----|------------|
| NVIDIA NIM | api.nvidia.com | PRIMARY — DeepSeek V4, Kimi K2, Llama 4, Mistral, Qwen |
| Anthropic | api.anthropic.com | STRATEGY + SALES tasks, code fallback |
| OpenAI | api.openai.com | Multimodal, last-resort fallback |
| Google | generativelanguage.googleapis.com | Multimodal fallback |
| DeepSeek | (direct API) | Configured but NIM version preferred |
| Groq | api.groq.com | Llama direct access |
| Mistral | api.mistral.ai | Direct (NIM version preferred) |
| ZhipuAI | (API) | CJK language specialization |
| Qwen | (via extra_providers.py) | CJK + structured |
| Moonshot | (API) | Long-context CJK |
| MiniMax | (API) | Additional Chinese LLM |
| AWS Bedrock | (AWS SDK) | Anthropic via AWS |

### Infrastructure (AWS — ap-south-2 Hyderabad)
| Resource | Name | Purpose |
|----------|------|---------|
| VPC | jarvis-production | Isolated network |
| ECS Cluster | jarvis-production | Container orchestration |
| ECS Service | jarvis-backend | FastAPI (Fargate) |
| ECS Service | jarvis-frontend | React (Fargate) |
| RDS PostgreSQL | jarvis-production-db | Primary DB (Multi-AZ option) |
| ElastiCache Redis | jarvis-production-redis | Cache + rate limits |
| ALB | Application Load Balancer | Routes traffic to ECS |
| ECR | jarvis-production-backend | Backend Docker images |
| ECR | jarvis-production-frontend | Frontend Docker images |
| S3 | AWS_S3_BUCKET | Invoice PDFs, documents |
| S3 | jarvis-terraform-state-824232273953 | Terraform state |
| DynamoDB | jarvis-terraform-locks | Terraform state locking |
| Route53 | aliyarsolutions.com | DNS → ALB |
| SES | (production) | Outbound email |
| Secrets Manager | jarvis-production/env | All secrets (AWS_SSM_PREFIX) |
| IAM Role | JarvisGitHubActionsRole | GitHub Actions OIDC |

### CI/CD Pipeline
```
git push main
    ↓
GitHub Actions (deploy.yml)
    ↓
Build Docker images (backend + frontend)
    ↓
Push to ECR (ap-south-2)
    ↓
ECS Blue/Green Rolling Update
    ↓
Health Gate: GET /health (liveness)
    ↓
Health Gate: GET /readyz (DB + Redis)
    ↓
Cutover (old tasks drained)
```

### Monitoring Stack
| Tool | Port | Purpose |
|------|------|---------|
| Prometheus | 9090 | Metrics collection |
| AlertManager | 9093 | Alert routing |
| Loki | 3100 | Log aggregation |
| Promtail | (agent) | Docker logs → Loki |
| Grafana | 3001 | Dashboards (jarvis_main.json) |

---

## Key Service Files

### Core Services (start reading here for any implementation)

| Need | Read This |
|------|-----------|
| Add a new route | backend/app/api/v1/routes/ (any file as template) + register in __init__.py |
| Understand AI routing | backend/app/services/ai/router.py |
| Add an AI call | Import ai_router from app.services.ai.router, call ai_router.chat() |
| Add email delivery | Import send_outbound_email from app.services.outreach.email_transport |
| Add a scheduled job | backend/app/services/scheduler/ |
| Generate a proposal | backend/app/services/governance/document_gen.py → generate_proposal() |
| Generate a contract | backend/app/services/governance/document_gen.py → generate_contract() |
| Add team member routing | backend/app/services/team/team_service.py |
| Trust scoring | backend/app/services/trust/scoring.py |
| Trust brief generation | backend/app/services/trust/brief_generator.py |
| Captain JWT auth | from app.api.v1.routes.auth import get_current_captain |
| Rate limiting | from app.core.rate_limit import limiter; @limiter.limit("N/minute") |
| DB session | Depends(get_db) in route signature |
| Background task | FastAPI BackgroundTasks, bg.add_task(fn, args) |

### Critical Patterns

**Route with auth + rate limit:**
```python
@router.post("/endpoint")
@limiter.limit("10/minute")
async def my_route(
    request: Request,              # MUST BE FIRST for rate limiting
    body: MyRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_captain),  # JWT auth
    bg: BackgroundTasks = None,
):
```

**Async DB query:**
```python
result = await db.execute(select(MyModel).where(MyModel.id == id))
obj = result.scalar_one_or_none()
```

**AI call:**
```python
from app.services.ai.router import ai_router
from app.services.ai.base_provider import Message, TaskType

response, provider = await ai_router.chat(
    [Message(role="user", content=prompt)],
    task_type=TaskType.STRATEGY,
    max_tokens=2500,
)
content = response.content.strip()
```

**Background email:**
```python
from app.services.outreach.email_transport import send_outbound_email

async def _send_email_bg(data: dict) -> None:
    await send_outbound_email(
        to=data["email"], subject="Subject",
        body="Body text", to_name=data["name"]
    )

bg.add_task(_send_email_bg, serialized_object)
```

**New migration:**
```python
# File: backend/alembic/versions/0030_my_feature.py
revision = '0030_my_feature'
down_revision = '0029_trust_engine'  # ALWAYS match last migration

def upgrade() -> None:
    op.create_table('my_table', ...)
    op.create_index('ix_my_table_field', 'my_table', ['field'])

def downgrade() -> None:
    op.drop_index('ix_my_table_field')
    op.drop_table('my_table')
```

---

## Data Flow Maps

### Lead-to-Client Pipeline (Automated)
```
Lead created (manual or Apollo sync)
    ↓
daily_lead_score (02:00 UTC) → trust_score calculated
    ↓
trust_score ≥ 40 → ready_for_proposal = True
    ↓
Captain or JARVIS: POST /trust/briefs/generate → Executive Opportunity Brief → emailed to lead
    ↓
Captain or JARVIS: POST /proposals/generate → Proposal created → auto-emailed to lead
    ↓
Lead replies "accepted" → POST /governance/proposals/{id}/status {status: "accepted"}
    ↓ (auto-trigger)
Contract generated → auto-emailed to lead
    ↓
Lead signs → POST /governance/contracts/{id}/status {status: "signed"}
    ↓ (manual Captain action)
POST /clients → Client created → auto welcome email sent
    ↓
delivery begins → 60 days → POST /trust/referrals/generate
```

### AI Request Flow
```
Route receives request
    ↓
ai_router.chat(messages, task_type=TaskType.X)
    ↓
ROUTING_TABLE[task_type][0] → first provider
    ↓
health_monitor.is_available(provider)? → yes: use it
    ↓
provider.chat(messages) → response
    ↓
on failure: circuit breaker trip count++
    ↓
if trips ≥ 5: circuit OPEN → skip for 60s
    ↓
try ROUTING_TABLE[task_type][1] → next provider
    ↓ (repeat until success or all exhausted)
cost_tracker.record(provider, tokens, task_type)
    ↓
return AIResponse
```

### Email Delivery Flow
```
Route action (invoice created / proposal generated / etc.)
    ↓
db.flush() → object gets ID
    ↓
bg.add_task(_send_email_bg, serialized_object)
    ↓
HTTP response returned immediately (non-blocking)
    ↓ (background)
send_outbound_email(to, subject, body, to_name)
    ↓
AWS SES API → client inbox
```

---

## Frontend Architecture

### View Registration Pattern
Every new view needs 3 changes:
1. Create component: `frontend/src/components/[name]/[Name]View.jsx`
2. Register in App.jsx: add to VIEWS map
3. Register in Sidebar.jsx: add to NAV array

### State Management
- Store: `frontend/src/store/useJarvisStore.js` (Zustand)
- Single store, multiple slices
- Never use raw fetch/axios — always use helpers from `frontend/src/services/api.js`

### Design System
- Glassmorphism: `backdrop-filter: blur()` + semi-transparent cards
- Colors: dark background + gradient accents (blue/purple/cyan)
- Typography: Inter font, clean hierarchy
- Pattern: `bg-white/10 backdrop-blur-md rounded-2xl border border-white/20`

---

## Security Architecture

### What Is Protected
| Resource | Protection |
|----------|-----------|
| /captain/* | JWT required (router-level) |
| /system/hud | JWT required |
| /system/self-heal | JWT required |
| /briefing/morning-ai | JWT required |
| /briefing/generate | JWT required |
| /emergency/incidents | JWT required |
| /emergency/alert | JWT required |
| /approvals/decide | JWT required |
| /scheduler/* mutations | JWT required |
| /aionx/self-heal | JWT required |
| /ws/captain | JWT required (query param) |

### What Is Public
- POST /auth/login
- GET /health, /readyz
- GET /ws (public WebSocket)
- POST /ses_inbound (SES signature verified)
- POST /telegram/webhook (Telegram signature verified)
- POST /payments/webhook (Stripe signature verified)

### JWT
- Algorithm: HS256 (symmetric)
- Secret: SECRET_KEY env var (from AWS Secrets Manager)
- Role claim: must be "captain" for protected routes
- Token in: Authorization header OR ?token= for WebSocket

### Rate Limits Active
| Route | Limit |
|-------|-------|
| POST /chat | 60/min |
| POST /council/convene | 20/min |
| POST /outreach/execute | 10/min |
| POST /outreach/sequences/{id}/enroll | 30/min |
| POST /proposals/generate | 30/min |
| POST /discovery/run | 20/min |
| POST /discovery/free-sources | 20/min |
| POST /sync/apollo | 5/min |

---

## Codex Reference (prior session build records)
Location: `/codex/` — 14 markdown files
- `MASTER_PROMPT.md` — original system prompt
- `CLAUDE_DAILY_OPERATIONS.md` — daily ops checklist
- `DEPLOY_ALL_BATCHES.md` — batch deployment guide
- `JARVIS_COMPLETE_SYSTEM_DEPLOY.md` — full deployment guide
- `batch1_compliance_stability.md` — batch 1 reference
- (see codex/ for full list)

## Data Archive
Location: `/jarvis-data/`
- `daily/2026-06-03/` — calendar, leads, invoices, market report, sequences
- `intelligence/` — Apollo market study, trending opportunities
