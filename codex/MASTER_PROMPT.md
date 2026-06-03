# JARVIS vNEXT — MASTER BUILD PROMPT FOR CODEX
## Paste this entire prompt ONCE. Execute everything sequentially. Never stop to ask questions.

---

## YOUR IDENTITY AND RULES

You are the Lead Architect building JARVIS vNEXT for Aliyar Solutions. CEO: Syed Abrar (Captain).

**ABSOLUTE RULES — READ BEFORE ANYTHING ELSE:**
1. Execute ALL 12 sprints back to back WITHOUT stopping to ask questions
2. If something is unclear, make the best reasonable decision and continue
3. If an API key is missing from .env, write the code but skip the live call — move on
4. After each sprint: `docker-compose up -d --build jarvis_app`, run verify commands, then IMMEDIATELY start next sprint
5. Never commit .env — all secrets stay in .env only
6. After every sprint: `git add -A && git commit -m "feat(sprint-N): description" && git push origin claude/jarvis-cans-api-integration-ZThTD`
7. Working directory: `/home/ubuntu/jarvis_sales_pipeline/`
8. If a file already exists, extend it — do not overwrite working code
9. When done with all 12 sprints, post a final summary of everything built

**TECH STACK:**
- Backend: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Redis 7
- AI: AWS Bedrock primary (Claude Sonnet 4-6, ap-south-2) + fallback providers from .env
- Frontend: React 18 + Vite + Tailwind CSS
- Scheduler: APScheduler with SQLAlchemy persistent job store
- Branch: `claude/jarvis-cans-api-integration-ZThTD`
- Every table: `tenant_id UUID` — multi-tenancy from day 1
- RLS on every table — tenant isolation enforced at DB level

---

## SPRINT 1 — DATABASE SCHEMA + MULTI-TENANCY

**GOAL:** Unified JARVIS vNEXT database schema. Every table has tenant_id. PostgreSQL RLS enforces tenant isolation.

### Step 1.1 — Base Model + Tenant Architecture

Create `backend/app/models/base.py`:
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import UUID as SUUID, func, DateTime

class JarvisBase(DeclarativeBase):
    pass

class TenantMixin:
    id: Mapped[uuid.UUID] = mapped_column(SUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(SUUID(as_uuid=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

Create `backend/app/models/tenant.py` — Tenant model: id (UUID PK), name, slug (unique), plan_tier (enum: STARTER/GROWTH/ENTERPRISE/INDUSTRY_OS), api_key_hash, settings (JSON), is_active, created_at. User model: id, tenant_id, email (unique per tenant), hashed_password, role (enum: CAPTAIN/ADMIN/VIEWER), is_captain (bool), last_login.

### Step 1.2 — Core CRM + Sales Schema

Create `backend/app/models/lead.py` — Lead: id, tenant_id, company_name, contact_name, email, phone, country, industry, score (float 0-100), status (enum: NEW/CONTACTED/REPLIED/DEMO/PROPOSAL/WON/LOST), source, pain_points (JSONB array), enrichment_data (JSONB), apollo_id, assigned_persona, outreach_count, last_contact, notes, outreach_eligible (bool default true), review_queue (bool default false), disqualification_reason, signal_breakdown (JSONB).

Create `backend/app/models/outreach.py` — OutreachLog: id, tenant_id, lead_id (FK), channel (EMAIL/LINKEDIN), subject, body_text, sent_from_persona, sent_at, status (SENT/DELIVERED/OPENED/CLICKED/REPLIED/BOUNCED/SKIPPED), sequence_step (int 1-3), skip_reason. EmailTracking: id, tenant_id, outreach_id (FK), opened_at, clicked_at, replied_at, bounce_reason. FollowUpQueue: id, tenant_id, lead_id, sequence_step, scheduled_at, executed_at, status.

Create `backend/app/models/revenue.py` — Client: id, tenant_id, company_name, contact_name, email, package_tier, mrr_usd (float), status (ACTIVE/PAUSED/CHURNED), started_at. Invoice: id, tenant_id, client_id (FK), invoice_number (ALY-YYYYMM-XXXX), amount_usd, status (DRAFT/SENT/PAID/OVERDUE), due_date, paid_at, pdf_url.

Create `backend/app/models/approval.py` — ApprovalRequest: id, tenant_id, action_type, title, summary, risk_level, payload (JSONB), status (PENDING/APPROVED/REJECTED), raised_by, decided_by, decided_at. AuditLog: id, tenant_id, user_id, action, entity_type, entity_id, before_json, after_json, ip_addr.

Register all models in `backend/app/models/__init__.py`.

### Step 1.3 — RLS Migration

Create Alembic migration `backend/alembic/versions/0100_rls_multi_tenant.py`:
- For every table: `ALTER TABLE {t} ENABLE ROW LEVEL SECURITY`
- Policy: `CREATE POLICY tenant_isolation ON {t} USING (tenant_id = current_setting('app.current_tenant_id')::uuid)`
- Create function: `set_tenant_context(tenant_uuid uuid)` sets `app.current_tenant_id`
- Add index on tenant_id for every table
- Create default tenant: name='Aliyar Solutions', slug='aliyar', plan_tier='ENTERPRISE', is_active=true — insert with fixed UUID so system always has a tenant

Extend `backend/app/middleware.py` — add TenantContextMiddleware that reads tenant_id from JWT or X-Tenant-ID header and calls set_tenant_context(). Add X-Request-ID middleware. Add X-Response-Time header.

### Step 1.4 — Deploy Sprint 1

```bash
cd /home/ubuntu/jarvis_sales_pipeline
docker-compose exec jarvis_app alembic upgrade head
docker-compose up -d --build jarvis_app
sleep 10
curl -s http://localhost:8000/health
git add -A && git commit -m "feat(sprint-1): multi-tenant schema, RLS, base models" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 2 — LEAD DISCOVERY ENGINE

**GOAL:** Fill the sales pipeline automatically. Apollo API + Google Maps + ICP scoring.

### Step 2.1 — Apollo API Integration

Create `backend/app/services/leads/discovery.py`, class `LeadDiscoveryEngine`:

```python
# Methods to implement:
async def search_apollo(query: str, filters: dict) -> list[dict]:
    # POST https://api.apollo.io/v1/mixed_people/search
    # Headers: {"x-api-key": APOLLO_API_KEY}
    # Filters: person_titles=['CEO','Founder','Director','VP','Owner'], num_page=1, per_page=25
    # If APOLLO_API_KEY not set: log warning, return []

async def enrich_company(domain: str) -> dict:
    # POST https://api.apollo.io/v1/organizations/enrich
    # Returns: size, revenue, tech_stack, social_urls
    # If key missing: return {}

async def discover_from_google_maps(query: str, location: str) -> list[dict]:
    # GET https://maps.googleapis.com/maps/api/place/textsearch/json
    # If GOOGLE_MAPS_API_KEY not set: return []

async def run_daily_discovery(tenant_id: UUID, targets: list) -> int:
    # Run discovery for each target, score results, save to DB
    # Return count of leads discovered
```

Create `backend/app/api/v1/routes/discovery.py` — routes: POST /discover/run, POST /discover/leads/score, GET /discover/leads/today. Register in `backend/app/api/v1/__init__.py`.

### Step 2.2 — ICP Scoring Engine

Create `backend/app/services/leads/scoring.py`, class `LeadScoringEngine`:

```python
ALIYAR_ICP = {
    "target_industries": ["e-commerce","real estate","consulting","professional services",
                          "SaaS","healthcare","logistics","education","finance","retail","hotel","hospitality"],
    "target_countries": ["UK","UAE","USA","Australia","Canada","Bahrain"],
    "company_size": {"min_employees": 5, "max_employees": 200},
    "pain_points": ["manual processes","no automation","poor lead generation",
                    "no AI systems","no tech team","scaling problems"],
    "disqualifiers": ["competitor","no budget","government"],
    "min_score_for_outreach": 65,
    "review_threshold": 45,
}

async def score_against_icp(lead: dict) -> tuple[float, dict]:
    # Scoring weights: industry_match=25pts, country_match=20pts, size_fit=20pts,
    # pain_point_match=25pts, contact_quality=10pts
    # Returns (score, reasoning_dict)

async def route_after_scoring(lead_id, score: float, tenant_id):
    # score >= 65: auto-enroll in outreach
    # 45-64: add to captain_review_queue
    # < 45: store only, outreach_eligible=false

async def batch_score(leads: list[dict], tenant_id) -> list:
    # Score all leads, save, return sorted by score desc
```

### Step 2.3 — Deploy Sprint 2

```bash
docker-compose up -d --build jarvis_app
sleep 10
curl -s http://localhost:8000/api/v1/discover/leads/today
git add -A && git commit -m "feat(sprint-2): lead discovery, Apollo integration, ICP scoring" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 3 — OUTREACH ENGINE

**GOAL:** Send cold outreach as human personas. 3-email sequence. Gmail SMTP.

### Step 3.1 — 3-Email Sequence + Persona Engine

Create `backend/app/services/outreach/engine.py`, class `OutreachEngine`:

Personas:
```python
PERSONAS = {
    "darren_mitchell": {
        "name": "Darren Mitchell", "email": "darren.mitchell@aliyarsolutions.com",
        "role": "Client Acquisition Specialist",
        "signature": "Darren Mitchell\nClient Acquisition Specialist\nAliyar Solutions",
        "style": "Direct, results-focused, professional. Leads with value, not features."
    },
    "sophia_reynolds": {
        "name": "Sophia Reynolds", "email": "sophia.reynolds@aliyarsolutions.com",
        "role": "Workflow Consultant",
        "signature": "Sophia Reynolds\nWorkflow Consultant\nAliyar Solutions",
        "style": "Consultative, empathetic, solution-focused."
    }
}
```

3-email sequence:
- **Email 1 (Day 0):** Subject: "Quick question about {company}'s operations" — specific observation, one problem, CTA: "15-minute conversation?"
- **Email 2 (Day 4):** Subject: "Results for similar {industry} companies" — reference Email 1, one quantified result (e.g. "reduced manual work by 70%"), CTA: "Happy to show how"
- **Email 3 (Day 8):** Subject: "Last note from me, {first_name}" — acknowledge they're busy, final value, easy out: "If timing isn't right, no worries"

Methods:
```python
async def generate_sequence(lead: Lead, tenant_id) -> list[OutreachLog]:
    # Use AI to write all 3 emails personalized to lead
    # Apply compliance check before generating

async def queue_sequence(lead_id, tenant_id) -> None:
    # Add 3 emails to FollowUpQueue with correct scheduled_at (now, +4d, +8d)

async def execute_due_outreach(tenant_id) -> int:
    # Find FollowUpQueue items where scheduled_at <= now and status=PENDING
    # For each: check compliance (DNC, unsubscribe, timezone, daily cap)
    # If eligible: send via Gmail, update status, increment daily cap
    # Append compliant footer to every email body
    # Return count sent
```

### Step 3.2 — Gmail SMTP Sender

Create `backend/app/services/notifications/gmail_sender.py`, class `GmailSender`:
```python
async def send_email(to, subject, body_html, from_name, from_email) -> bool:
    # aiosmtplib, host=smtp.gmail.com, port=587, STARTTLS
    # Uses GMAIL_ADDRESS + GMAIL_APP_PASSWORD from .env
    # Returns True on success, False on failure (logs to audit_log)

async def send_outreach(outreach: OutreachLog) -> bool:
    # Sends email, updates outreach.status=SENT, records in email_tracking

async def check_replies(tenant_id) -> list[dict]:
    # IMAP check inbox for replies to our outreach
    # Returns list of reply dicts
```

Create `backend/app/services/notifications/slack.py`:
```python
async def notify_slack(message: str) -> bool:
    # POST to SLACK_WEBHOOK_URL from .env
    # If not set: log and return False
```

Create `backend/app/services/notifications/telegram.py`:
```python
async def notify_telegram(message: str) -> bool:
    # POST to https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage
    # chat_id=TELEGRAM_CHAT_ID from .env
    # If not set: log and return False
```

Alert on: proposal_accepted, meeting_booked, payment_received, system_critical_error, hot_reply_detected.

Create routes: POST /outreach/queue/{lead_id}, POST /outreach/execute, GET /outreach/stats.

### Step 3.3 — Deploy Sprint 3

```bash
docker-compose up -d --build jarvis_app && sleep 10
curl -s http://localhost:8000/api/v1/outreach/stats
git add -A && git commit -m "feat(sprint-3): outreach engine, 3-email sequence, Gmail SMTP" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 4 — EMAIL TRACKING + FOLLOW-UP + REPLY HANDLER

**GOAL:** Full outreach loop — track emails, process replies, advance leads.

### Step 4.1 — Reply Classification + Lead Progression

Create `backend/app/services/outreach/reply_handler.py`, class `ReplyHandler`:

```python
REPLY_CLASSIFICATIONS = ["INTERESTED", "QUESTION", "NOT_NOW", "NO", "OUT_OF_OFFICE", "UNKNOWN"]

async def classify_reply(reply_text: str) -> tuple[str, float]:
    # Use AI to classify. Returns (classification, confidence_score)
    # Simple fallback: keyword matching if AI unavailable

async def process_reply(lead_id, reply_text, tenant_id) -> dict:
    # 1. Classify reply
    # 2. Update lead status:
    #    INTERESTED → status=DEMO, alert Captain (Slack+Telegram), pause follow-up sequence
    #    QUESTION   → status=REPLIED, generate response as Darren Mitchell
    #    NOT_NOW    → status=NURTURE, schedule re-contact in 30 days
    #    NO         → status=LOST, stop all outreach, add to DNC list
    #    OUT_OF_OFFICE → no change, wait
    # 3. Log to reply_log table
    # 4. Return action taken

async def generate_response(reply_text: str, lead: Lead, classification: str) -> str:
    # Write response as Darren Mitchell persona
    # INTERESTED: offer specific time slots
    # QUESTION: answer directly and professionally
```

Integrate: check Gmail inbox every 2 hours for new replies via APScheduler job.

### Step 4.2 — Email Open Tracking

Add tracking pixel endpoint: `GET /track/open/{outreach_id}` — returns 1x1 transparent GIF, records opened_at in email_tracking, updates outreach.status=OPENED.

Add click tracking: wrap links in outreach emails with `/track/click/{outreach_id}?url={encoded_url}`, records clicked_at, redirects to destination.

### Step 4.3 — Deploy Sprint 4

```bash
docker-compose up -d --build jarvis_app && sleep 10
curl -s http://localhost:8000/api/v1/outreach/stats
git add -A && git commit -m "feat(sprint-4): reply handler, email tracking, follow-up queue" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 5 — PROPOSAL GENERATOR + CAPTAIN APPROVAL QUEUE

**GOAL:** AI-generated proposal PDFs. Captain sees every important decision in one queue.

### Step 5.1 — AI Proposal Generator (PDF)

Create `backend/app/services/governance/proposal_generator.py`, class `ProposalGenerator`:

```python
async def generate(lead: Lead, package_tier: str, tenant_id) -> str:
    # Use AI (STRATEGY task type) to generate all text personalized to lead
    # Use ReportLab to build PDF
    # PDF structure (7 pages):
    #   Page 1: Cover — "Proposal for {company}", date, CONFIDENTIAL
    #   Page 2: Executive Summary — 3 paragraphs about their situation and our solution
    #   Page 3: Proposed Solution — 4-6 bullets mapping pain points to capabilities
    #   Page 4: Package Details — STARTER/GROWTH/ENTERPRISE table with features + price
    #   Page 5: Implementation Timeline — 4-week onboarding milestones
    #   Page 6: Investment Summary — pricing, payment terms (50% upfront + 50% delivery)
    #   Page 7: About Aliyar Solutions — company description, team, tech
    # Save PDF to /data/proposals/{tenant_id}/{proposal_id}.pdf
    # Store path in proposals table
    # Return file path

async def submit_for_approval(proposal_id, tenant_id) -> dict:
    # Call captain_queue.add_item()
    # Notify Captain: Slack + Telegram with proposal summary
```

Package pricing (use these exact prices):
- STARTER: $2,500/month — AI automation, basic CRM, monthly reporting
- GROWTH: $5,500/month — Full automation suite, custom integrations, bi-weekly reviews
- ENTERPRISE: $12,000/month — Complete AI OS, dedicated team, weekly strategy sessions
- INDUSTRY_OS: $8,000+$2,000/month — Full operational system for specific industry

Routes: POST /proposals/generate, POST /proposals/{id}/approve, POST /proposals/{id}/send, GET /proposals/{id}/pdf.

### Step 5.2 — Captain Approval Queue

Create `backend/app/services/governance/captain_queue.py`, class `CaptainQueue`:

```python
async def add_item(action_type, title, summary, payload, risk_level, tenant_id) -> ApprovalRequest:
    # Create ApprovalRequest
    # Priority: HIGH for pricing/contract/deploy, MEDIUM for proposals, LOW for others
    # Notify Captain: Slack + Telegram + WebSocket broadcast

async def get_pending(tenant_id) -> list[ApprovalRequest]:
    # Return all pending sorted by priority DESC, created_at ASC

async def approve(approval_id, captain_note, tenant_id) -> dict:
    # Set status=APPROVED, execute queued action, log to audit_log, notify agent

async def reject(approval_id, reason, tenant_id) -> dict:
    # Set status=REJECTED, notify agent with reason
```

WebSocket endpoint: `/ws/captain` — on connect: send pending count + system health. On new item: push notification to all Captain sessions.

### Step 5.3 — Deploy Sprint 5

```bash
# Install reportlab if not present
docker-compose exec jarvis_app pip install reportlab
docker-compose up -d --build jarvis_app && sleep 10
curl -s -X POST http://localhost:8000/api/v1/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{"lead_id": 1, "package_tier": "GROWTH"}' | head -50
git add -A && git commit -m "feat(sprint-5): proposal generator, captain approval queue" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 6 — INVOICE ENGINE + CLIENT MANAGEMENT

**GOAL:** First invoice. Revenue tracking. Client portal.

### Step 6.1 — Invoice Engine

Create `backend/app/services/governance/invoice_engine.py`, class `InvoiceEngine`:

```python
async def generate(client_id, amount_usd, description, due_days=14, tenant_id) -> Invoice:
    # Auto-number: ALY-YYYYMM-XXXX (sequential per month per tenant)
    # Generate PDF invoice with ReportLab:
    #   Aliyar Solutions letterhead, client details, line items,
    #   payment instructions, due date, invoice number
    # Save PDF, store url in invoice.pdf_url

async def send_invoice(invoice_id, tenant_id) -> bool:
    # Email PDF to client, update status=SENT, alert Captain

async def check_overdue(tenant_id) -> list[Invoice]:
    # Find invoices where due_date < now and status != PAID
    # Send reminder (max 3). Alert Captain on 7-day overdue.

async def record_payment(invoice_id, amount, tenant_id) -> Invoice:
    # Update status=PAID, set paid_at, alert Captain (payment_received)
    # Update client.mrr_usd, update revenue_snapshots table
```

Routes: POST /invoices/generate, POST /invoices/{id}/send, POST /invoices/{id}/pay, GET /revenue/snapshot, GET /revenue/mrr-chart.

Revenue snapshots table: daily snapshot of total MRR, active clients, total invoiced, total paid.

### Step 6.2 — Client Portal Endpoints

Routes: POST /clients (create), GET /clients (list), GET /clients/{id} (detail), PUT /clients/{id}/status, GET /clients/{id}/invoices, GET /clients/{id}/health.

Client onboarding trigger: when proposal status → accepted, automatically create client record, create onboarding task sequence (contract → payment → access → kickoff → first deliverable, each with deadline).

### Step 6.3 — Deploy Sprint 6

```bash
docker-compose up -d --build jarvis_app && sleep 10
curl -s http://localhost:8000/api/v1/revenue/snapshot
git add -A && git commit -m "feat(sprint-6): invoice engine, client management, revenue tracking" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 7 — AI COUNCIL + MEMORY SYSTEM

**GOAL:** JARVIS learns. 8 AI members vote on decisions. 5-tier memory persists intelligence.

### Step 7.1 — Intelligence Council (8 members, weighted consensus)

Create `backend/app/services/ai/council.py`, class `IntelligenceCouncil`:

Council members:
```python
COUNCIL_MEMBERS = [
    {"name": "claude", "provider": "anthropic", "model": "claude-sonnet-4-6", "weight": 0.25, "specialty": "reasoning"},
    {"name": "gpt4", "provider": "openai", "model": "gpt-4o", "weight": 0.20, "specialty": "analysis"},
    {"name": "gemini", "provider": "google", "model": "gemini-pro", "weight": 0.18, "specialty": "research"},
    {"name": "deepseek", "provider": "deepseek", "model": "deepseek-chat", "weight": 0.12, "specialty": "code"},
    {"name": "llama", "provider": "groq", "model": "llama-3.3-70b-versatile", "weight": 0.10, "specialty": "speed"},
    {"name": "mistral", "provider": "mistral", "model": "mistral-large", "weight": 0.08, "specialty": "european"},
    {"name": "qwen", "provider": "qwen", "model": "qwen-max", "weight": 0.04, "specialty": "multilingual"},
    {"name": "minimax", "provider": "minimax", "model": "abab6.5s", "weight": 0.03, "specialty": "creative"},
]
```

```python
async def convene(question: str, context: dict, task_type: str, tenant_id) -> dict:
    # Call all available members in parallel (skip if provider not configured)
    # Each member responds independently
    # Synthesize: weighted average of confidence scores
    # If weighted_score >= 80: AUTO_APPROVE
    # If 60-79: CAPTAIN_REVIEW
    # If < 60: REJECT
    # Update member weights: +1% if prediction correct, -1% if wrong
    # Store in council_sessions table

async def get_session_history(tenant_id, limit=20) -> list:
    # Return recent council sessions
```

Council sessions table: id, tenant_id, question, context_json, responses_json, consensus, weighted_score, decision, created_at.

### Step 7.2 — 5-Tier Memory System

Create `backend/app/services/memory/memory_engine.py`:

```python
# Tier 1 — Working Memory (Redis, TTL 24h)
async def set_working(key: str, value: dict, ttl: int = 86400) -> None
async def get_working(key: str) -> dict | None
async def delete_working(key: str) -> None

# Tier 2 — Operational Memory (PostgreSQL, 90-day TTL)
async def store_operational(category: str, content: str, source: str, importance: float, tenant_id) -> MemoryRecord
async def retrieve_operational(category: str, limit: int, tenant_id) -> list[MemoryRecord]
async def prune_operational(tenant_id) -> int  # deletes records older than 90 days

# Tier 3 — Strategic Memory (PostgreSQL + pgvector semantic search)
async def promote_from_operational(memory_id, tenant_id) -> MemoryStrategic
async def semantic_search(query: str, tenant_id, limit=10) -> list  # requires pgvector extension

# Tier 5 — Civilization Memory (Immutable, append-only)
async def record_civilization_event(event_type: str, description: str, impact: str, tenant_id) -> CivilizationRecord
async def get_civilization_ledger(tenant_id) -> list[CivilizationRecord]
```

Enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector` in migration.
Memory tables: memory_records (working/operational/strategic), civilization_ledger (immutable, no UPDATE/DELETE).

Routes: GET /memory/operational, GET /memory/strategic, POST /memory/search, GET /memory/civilization.

### Step 7.3 — Deploy Sprint 7

```bash
docker-compose exec jarvis_postgres psql -U jarvis -d jarvis -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker-compose up -d --build jarvis_app && sleep 10
curl -s http://localhost:8000/api/v1/memory/civilization
git add -A && git commit -m "feat(sprint-7): AI council 8-member consensus, 5-tier memory system" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 8 — OBSERVABILITY STACK

**GOAL:** Full visibility. Prometheus metrics, Grafana dashboard, structured logging.

### Step 8.1 — Prometheus Metrics

Extend `backend/app/middleware.py` — add Prometheus instrumentation:

```python
# Metrics to expose at /metrics:
jarvis_http_requests_total        # counter, labels: method, endpoint, status_code
jarvis_http_request_duration_ms   # histogram, labels: method, endpoint
jarvis_leads_total                # gauge, labels: status, tenant_id
jarvis_outreach_sent_total        # counter, labels: persona, sequence_step
jarvis_ai_calls_total             # counter, labels: provider, task_type, success
jarvis_ai_cost_usd_total          # counter, labels: provider, task_type
jarvis_council_sessions_total     # counter, labels: decision
jarvis_approvals_pending          # gauge, labels: risk_level
jarvis_clients_active             # gauge
jarvis_mrr_usd                    # gauge
jarvis_jobs_failed_total          # counter, labels: job_name
```

### Step 8.2 — Grafana Dashboard

Create `infrastructure/grafana/dashboards/jarvis_main.json` — Grafana dashboard JSON with panels:
- Request rate and error rate (time series)
- Active leads by stage (stat + time series)
- Outreach sent today (stat)
- AI cost tracker (time series by provider)
- Revenue MRR gauge
- System health grid (all green/yellow/red)
- Council sessions and approval rate
- Top failing jobs

Also create `infrastructure/grafana/provisioning/datasources/prometheus.yml` pointing to jarvis_prometheus:9090.

### Step 8.3 — Structured Logging

Ensure all log output is JSON-formatted with: timestamp, level, service, tenant_id, request_id, message, duration_ms. Add `python-json-logger` to requirements.txt.

### Step 8.4 — Deploy Sprint 8

```bash
docker-compose up -d --build jarvis_app && sleep 10
curl -s http://localhost:8000/metrics | head -30
# Verify Grafana
curl -s http://localhost:3000/api/health
git add -A && git commit -m "feat(sprint-8): Prometheus metrics, Grafana dashboard, structured logging" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 9 — ECS FARGATE MIGRATION (TERRAFORM)

**GOAL:** Production-grade AWS infrastructure. Cloud-native. Auto-scaling.

### Step 9.1 — Review Terraform Config

Review `infra/terraform/` directory. The Terraform config should already exist with:
- VPC, subnets (private/public), internet gateway, NAT gateway
- ECS Fargate cluster + service + task definition
- RDS PostgreSQL 16 (gp3 encrypted)
- ElastiCache Redis 7
- ALB + ACM + Route53
- ECR repositories (jarvis-backend, jarvis-frontend)
- AWS Secrets Manager for all env vars
- CloudWatch log groups

If any of these are missing, create them. Region: ap-south-2 (Hyderabad).

### Step 9.2 — CI/CD Pipeline

Review `.github/workflows/deploy.yml`. It should:
1. On push to main/claude branch: build Docker images
2. Push to ECR (jarvis-backend:latest, jarvis-frontend:latest)
3. Update ECS task definitions
4. Trigger ECS rolling deployment (blue/green)
5. Health check: wait for /health to return 200
6. Rollback on failure

If deploy.yml is missing or incomplete, fix it.

### Step 9.3 — Production Health Endpoints

Ensure these are implemented:
- `GET /health` → `{"status": "ok", "timestamp": "...", "version": "..."}`
- `GET /readyz` → deep health check (DB connection, Redis ping, AI provider availability)

### Step 9.4 — Deploy Sprint 9

```bash
# Do NOT run terraform apply — just validate config
cd infra/terraform && terraform validate && terraform plan -out=tfplan 2>&1 | tail -20 || echo "Terraform validation complete"
cd /home/ubuntu/jarvis_sales_pipeline
curl -s http://localhost:8000/readyz | python3 -m json.tool
git add -A && git commit -m "feat(sprint-9): ECS Fargate config, CI/CD pipeline, health endpoints" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 10 — WHITE-LABEL + MULTI-TENANT

**GOAL:** Sell JARVIS as a product to other agencies. Per-tenant isolation, API keys, billing.

### Step 10.1 — Tenant Manager

Create `backend/app/services/tenancy/tenant_manager.py`, class `TenantManager`:

```python
async def create_tenant(name: str, slug: str, plan_tier: str) -> Tenant:
    # Create tenant with unique slug
    # Generate API key (UUID4, store hashed)
    # Set plan limits based on tier:
    #   STARTER: max_leads=500, max_outreach=50/day, max_users=2
    #   GROWTH: max_leads=5000, max_outreach=200/day, max_users=5
    #   ENTERPRISE: unlimited
    # Return tenant with raw API key (only shown once)

async def authenticate_tenant(api_key: str) -> Tenant | None:
    # Hash API key, lookup tenant
    # Return tenant or None

async def get_tenant_usage(tenant_id) -> dict:
    # Return: leads_count, outreach_sent_today, active_users, mrr_usd

async def enforce_plan_limits(tenant_id) -> dict:
    # Check if tenant is within plan limits
    # Return: within_limits bool, exceeded fields
```

Create `backend/app/api/v1/routes/tenancy.py` (Captain-only, requires is_captain=true):
- POST /admin/tenants — create new tenant
- GET /admin/tenants — list all tenants with usage stats
- PUT /admin/tenants/{id}/limits — update plan limits
- POST /admin/tenants/{id}/api-key — regenerate API key
- GET /admin/tenants/{id}/usage — detailed usage stats

### Step 10.2 — API Key Auth Middleware

Add API key authentication: requests with `X-API-Key` header are authenticated as tenants. JWT auth remains for UI users. Both paths set tenant context for RLS.

### Step 10.3 — Deploy Sprint 10

```bash
docker-compose up -d --build jarvis_app && sleep 10
curl -s -X POST http://localhost:8000/api/v1/admin/tenants \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Agency","slug":"test-agency","plan_tier":"STARTER"}' | python3 -m json.tool
git add -A && git commit -m "feat(sprint-10): white-label, multi-tenant, API key auth" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 11 — INTELLIGENCE STACK + ALL SCHEDULER JOBS

**GOAL:** JARVIS runs autonomously. All intelligence jobs scheduled. Morning briefing live.

### Step 11.1 — Tech Radar

Create `backend/app/services/intelligence/tech_radar.py`, class `TechRadarEngine`:
```python
async def scan_new_technologies(tenant_id) -> list[dict]:
    # Use AI (RESEARCH task type) to identify 5 emerging technologies per scan
    # Categories: ADOPT (use now), TRIAL (experiment), ASSESS (watch), HOLD (avoid)
    # Save to tech_radar table: name, category, description, relevance_score, source

async def generate_radar_report(tenant_id) -> str:
    # Weekly summary of tech landscape relevant to Aliyar Solutions
```

Create `backend/app/services/intelligence/market_intel.py`, class `MarketIntelligenceEngine`:
```python
async def generate_report(topics: list[str], tenant_id) -> str:
    # Use AI (RESEARCH task type) to generate market intelligence report
    # Topics: competitor moves, market trends, pricing changes, opportunity signals

async def generate_morning_briefing(tenant_id) -> dict:
    # Pull: top 5 leads by score, pipeline value, outreach stats, 
    #       pending approvals, system health, today's priorities
    # Format as clean executive summary
    # Send via Telegram + Slack to Captain
    # Store in briefing_log table
```

### Step 11.2 — ALL Scheduler Jobs

Create/extend `backend/app/services/scheduler/scheduler.py` with ALL jobs:

```python
# Use distributed Redis locks on every job (lock before run, release after)
# Use resilient_job wrapper (3 retries with backoff, dead letter on failure)

SCHEDULED_JOBS = [
    # Daily
    {"id": "morning_briefing",       "cron": "30 1 * * *",   "fn": run_morning_briefing},         # 07:00 IST
    {"id": "lead_scoring",           "cron": "30 20 * * *",  "fn": run_lead_scoring},              # 02:00 IST
    {"id": "lead_discovery",         "cron": "0 22 * * *",   "fn": run_lead_discovery},            # 03:30 IST
    {"id": "follow_up_check",        "cron": "30 4 * * *",   "fn": run_follow_up_check},           # 10:00 IST
    {"id": "reply_check",            "cron": "0 */2 * * *",  "fn": run_reply_check},               # every 2h
    {"id": "memory_consolidate",     "cron": "0 19 * * *",   "fn": run_memory_consolidation},      # 00:30 IST
    {"id": "optimization_review",    "cron": "30 17 * * *",  "fn": run_optimization_review},       # 23:00 IST
    {"id": "client_health_scoring",  "cron": "30 3 * * *",   "fn": score_all_clients},             # 09:00 IST
    {"id": "revenue_drift_check",    "cron": "0 */6 * * *",  "fn": check_revenue_drift},           # every 6h
    {"id": "predicted_actions",      "cron": "0 */4 * * *",  "fn": generate_predicted_actions},    # every 4h
    {"id": "daily_backup",           "cron": "30 19 * * *",  "fn": run_daily_backup},              # 01:00 IST
    {"id": "reply_rate_monitor",     "cron": "0 18 * * *",   "fn": check_and_pause_sequences},     # 23:30 IST
    # Weekly
    {"id": "outreach_stats",         "cron": "30 2 * * MON", "fn": run_outreach_stats},            # Mon 08:00 IST
    {"id": "pipeline_health",        "cron": "30 14 * * SUN","fn": run_pipeline_health},           # Sun 20:00 IST
    {"id": "tech_radar",             "cron": "30 0 * * MON", "fn": run_tech_radar_scan},           # Mon 06:00 IST
    {"id": "self_assessment",        "cron": "30 16 * * SUN","fn": run_self_assessment},           # Sun 22:00 IST
    {"id": "memory_synthesis",       "cron": "30 21 * * SUN","fn": run_weekly_synthesis},          # Sun 03:00 IST
    {"id": "revenue_forecast",       "cron": "30 14 * * SUN","fn": run_revenue_forecast},          # Sun 20:00 IST
    {"id": "flywheel_metrics",       "cron": "30 1 * * MON", "fn": calculate_flywheel_momentum},   # Mon 07:00 IST
    {"id": "long_game_touches",      "cron": "30 4 * * *",   "fn": run_long_game_touches},         # 10:00 IST
    {"id": "red_team_analysis",      "cron": "30 22 * * SUN","fn": run_red_team_analysis},         # Sun 04:00 IST
    # Biweekly
    {"id": "research_report",        "cron": "0 1 * * SUN",  "fn": run_research_report},           # every other Sun
]
```

All jobs must use distributed lock pattern:
```python
async def locked_job(job_id: str, fn):
    r = await get_redis()
    acquired = await r.set(f"jarvis:lock:{job_id}", "1", nx=True, ex=300)
    if not acquired:
        return
    try:
        await fn()
    except Exception as e:
        await write_dead_letter(job_id, e)
        raise
    finally:
        await r.delete(f"jarvis:lock:{job_id}")
```

### Step 11.3 — Deploy Sprint 11

```bash
docker-compose up -d --build jarvis_app && sleep 10
curl -s http://localhost:8000/api/v1/scheduler/jobs | python3 -m json.tool
curl -s http://localhost:8000/api/v1/scheduler/failures
git add -A && git commit -m "feat(sprint-11): full intelligence stack, all 20+ scheduler jobs" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## SPRINT 12 — REACT FRONTEND (25 VIEWS)

**GOAL:** Full Captain dashboard. Every system visible and controllable. Glassmorphism design.

### Design System (apply to ALL views)

```css
/* Colors */
background: #0A0A1A (dark navy)
primary: #0057FF (electric blue)
accent: #00C8FF (cyan)
gold: #FFB700
text-primary: white
text-secondary: #9CA3AF

/* Glassmorphism card style */
background: rgba(255,255,255,0.05)
border: 1px solid rgba(255,255,255,0.1)
border-radius: 16px
backdrop-filter: blur(10px)
```

### All 25 Views to Build

Create each view in `frontend/src/components/{ViewName}/{ViewName}.jsx`:

**1. Dashboard** (`/`) — Live KPIs: MRR, active leads, outreach sent, proposals open, system health grid, predicted actions (top 3), morning briefing panel.

**2. Chat** (`/chat`) — Real-time chat with JARVIS. WebSocket. Markdown rendering. Conversation history.

**3. Briefing** (`/briefing`) — Morning briefing view. Latest briefing display. Historical briefings archive.

**4. Approvals** (`/approvals`) — Captain's approval queue. Cards with approve/reject buttons. Pending count badge. Risk level color coding.

**5. Agents** (`/agents`) — Agent roster. 48 named agents across departments. Status indicators. Performance stats.

**6. CRM** (`/crm`) — Lead management table. Filters by status/score/country. Lead detail modal. Score visualization.

**7. Leads** (`/leads`) — Lead discovery controls. Run discovery button. Today's discovered leads. Score distribution chart.

**8. Outreach** (`/outreach`) — Active sequences. Stats (sent, opened, replied). Compliance status. Reply rate chart.

**9. Proposals** (`/proposals`) — Proposal pipeline. Generate button. Status kanban. PDF preview.

**10. Clients** (`/clients`) — Active clients. Health scores. MRR per client. Invoice status.

**11. Revenue** (`/revenue`) — MRR chart (monthly). Revenue forecast (P10/P50/P90). Pipeline value. Invoice list.

**12. Intelligence** (`/intelligence`) — Tech radar. Market intel reports. Operating beliefs. Flywheel momentum.

**13. Memory** (`/memory`) — Memory tiers visualization. Civilization ledger. Search memories. Synthesis history.

**14. Tasks** (`/tasks`) — Task list by assignee. Upcoming tasks. Completed today. Overdue alerts.

**15. Council** (`/council`) — Convene council form. Session history. Member weight display. Latest consensus.

**16. Captain Bridge** (`/captain-bridge`) — Lead intake form. Brain dump textarea. Apollo import. Case studies. Intelligence feed.

**17. Voice** (`/voice`) — Voice command interface. Text input + mic icon. Response display. Command history.

**18. War Room** (`/war-room`) — Activate/deactivate. Situation brief. Threat grid. Active session display.

**19. System HUD** (`/hud`) — All system health indicators. Dead letter queue. Predicted actions. Consciousness feed.

**20. Governance** (`/governance`) — Audit log. Autonomous decisions. Approval history.

**21. Team** (`/team`) — 9 human personas. Role, email, department. Service routing map.

**22. AI Ops** (`/ai-ops`) — Provider status. Cost per provider. Routing performance. Circuit breaker status.

**23. Scheduler** (`/scheduler`) — All 20+ jobs. Last run time. Next run time. Failure count. Manual trigger buttons.

**24. Settings** (`/settings`) — API keys status (redacted). Integration config. Notification settings.

**25. Relationships** (`/relationships`) — Relationship graph. Warm intro finder. Add person/relationship forms.

### Step 12.1 — Zustand State Store

Create `frontend/src/store/useJarvisStore.js`:
```javascript
const useJarvisStore = create((set, get) => ({
  // State
  user: null, tenant: null, notifications: [], captainQueue: [],
  systemHealth: {}, pipeline: {}, leads: [], outreach: {},
  
  // Actions
  setUser: (user) => set({ user }),
  addNotification: (n) => set(state => ({ notifications: [n, ...state.notifications].slice(0, 50) })),
  fetchDashboard: async () => { /* fetch /api/v1/dashboard */ },
  // etc
}))
```

### Step 12.2 — API Service Layer

Create `frontend/src/services/api.js` — axios instance with:
- Base URL from VITE_API_URL env var
- Auth header injection from localStorage token
- Request/response interceptors for error handling
- Helper functions for every API endpoint

### Step 12.3 — Register All Views

In `frontend/src/App.jsx`, register all 25 views with React Router. In `frontend/src/components/layout/Sidebar.jsx`, add all nav items with icons.

### Step 12.4 — Deploy Sprint 12

```bash
docker-compose up -d --build
sleep 20
curl -s http://localhost:8000/health
curl -s http://localhost:3000  # or wherever frontend is served
git add -A && git commit -m "feat(sprint-12): complete React frontend, all 25 views" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## FINAL INTEGRATION + FIRST CLIENT READINESS

### Pre-Launch Validation

Create `scripts/pre_launch_check.py`:
```python
# Check every system required for first client:
CHECKS = [
    ("Database connection", check_db),
    ("Redis connection", check_redis),
    ("AI provider active (at least 1)", check_ai_provider),
    ("Outreach compliance enabled", check_compliance),
    ("Gmail SMTP configured", check_gmail),
    ("Telegram notifications configured", check_telegram),
    ("Proposal generator working", check_proposals),
    ("Invoice engine working", check_invoices),
    ("Captain approval queue empty", check_approvals),
    ("All scheduler jobs registered", check_scheduler),
    ("At least 1 active sequence", check_sequences),
    ("Backup system working", check_backup),
]
# Print PASS/FAIL for each, overall READY / NOT READY
```

### Final System Wiring

Ensure these connections are made:
1. When lead score >= 65 → auto-enroll in outreach sequence
2. When outreach reply = INTERESTED → alert Captain, pause sequence, add to approval queue
3. When proposal approved by Captain → send to prospect, schedule follow-up sequence
4. When proposal accepted → trigger client onboarding, create invoice, alert Captain
5. When invoice paid → update MRR, record civilization event, alert Captain

### Final Deploy and Verification

```bash
cd /home/ubuntu/jarvis_sales_pipeline

# Run all migrations
docker-compose exec jarvis_app alembic upgrade head

# Full rebuild
docker-compose up -d --build
sleep 30

# Run pre-launch check
docker-compose exec jarvis_app python scripts/pre_launch_check.py

# Count everything
curl -s http://localhost:8000/openapi.json | python3 -c "
import json,sys
s=json.load(sys.stdin)
print('API Routes:', len(s.get('paths',{})))
"
curl -s http://localhost:8000/api/v1/scheduler/jobs | python3 -c "import json,sys; d=json.load(sys.stdin); print('Scheduler jobs:', len(d.get('jobs',[])))"
curl -s http://localhost:8000/api/v1/system/hud | python3 -m json.tool

# Final commit
git add -A && git commit -m "feat(complete): JARVIS vNEXT fully operational — all 12 sprints, 25 views, 20+ jobs" && git push origin claude/jarvis-cans-api-integration-ZThTD
```

### Report Back to Captain

When all 12 sprints are done, post this summary:
```
JARVIS vNEXT — BUILD COMPLETE

✅ Sprint 1: Multi-tenant DB schema + RLS
✅ Sprint 2: Lead discovery + ICP scoring  
✅ Sprint 3: 3-email outreach engine + Gmail SMTP
✅ Sprint 4: Reply handler + email tracking
✅ Sprint 5: Proposal generator + Captain approval queue
✅ Sprint 6: Invoice engine + client management
✅ Sprint 7: AI Council (8 members) + 5-tier memory
✅ Sprint 8: Prometheus + Grafana + structured logging
✅ Sprint 9: ECS Fargate config + CI/CD pipeline
✅ Sprint 10: White-label + multi-tenant API keys
✅ Sprint 11: Full intelligence stack + 20+ scheduler jobs
✅ Sprint 12: React frontend — all 25 views live

API Routes: [count]
Scheduler Jobs: [count]  
Database Tables: [count]
Health: [status]
Live URL: https://aliyarsolutions.com

JARVIS is ready for the first client, Captain.
```
