# Sarah — AI Voice Receptionist Platform

Production-grade, multi-tenant AI voice receptionist SaaS for dental clinics. Sarah answers inbound phone calls 24/7, understands natural speech in English and Arabic, books/reschedules/cancels appointments in real time, and hands off urgent cases to on-call staff — all without human involvement.

---

## What It Does

A patient calls the clinic's existing phone number. Sarah answers within one ring, introduces herself by the clinic's name, and conducts a natural conversation. She can:

- **Book, reschedule, and cancel appointments** — conflicts checked per-provider in real time, confirmation SMS sent automatically
- **Look up existing patients** by phone number and greet them by name
- **Switch languages mid-call** — bilingual English/Arabic, caller-led
- **Transfer live calls** to on-call staff during business hours with a real dial outcome recorded; after hours, fires an SMS escalation instead
- **Play back recordings** to clinic staff through the dashboard with full transcripts

The entire voice pipeline runs inside a streaming WebSocket loop — no polling, no blocking calls.

---

## Architecture

```
PSTN ──► Twilio                     (SIP termination + Media Streams WebSocket)
           │
           ▼
    voice-service (ECS Fargate)
           │
           ├── Deepgram Nova-3       (streaming STT, partial transcripts for barge-in)
           ├── Claude Sonnet         (LLM via OpenRouter, sentence-buffered streaming)
           └── ElevenLabs Flash      (streaming TTS → mulaw → Twilio)
           │
           ▼
    api-service (ECS Fargate)       (FastAPI REST — dashboard + admin)
           │
    worker-service (ECS Fargate)    (Arq — SMS, call summaries, reminders)
           │
    ┌──────┴──────┐
    │             │
  RDS Postgres   ElastiCache Redis
  (Multi-AZ)     (replication group)
```

**Key design decisions:**

- **Barge-in**: Deepgram partial transcripts cancel in-flight TTS immediately; audio buffer flushed via Twilio's `<Clear>` verb. The LLM never finishes a sentence the caller interrupted.
- **One-shot media-stream token**: A 120-second Redis token gates every WebSocket upgrade so direct connections are refused — Twilio's signature-validated HTTP webhook is the only entry point.
- **Consent-first**: The HIPAA consent disclosure is a hard-coded `<Say>` before the media stream opens. There is no code path that skips it.
- **Provider-level conflict detection**: Appointment availability uses half-open interval overlap `[start, start+duration)` against individual dentist calendars, not just clinic-wide slots. Race-safe patient creation uses savepoints + unique-constraint retry.
- **Action-tag system**: Claude emits structured tags (`[BOOK]`, `[CANCEL]`, `[RESCHEDULE]`, `[TRANSFER]`, `[END]`, `[LOOKUP_PATIENT]`) that the backend parses and executes against the database and Twilio. The model cannot directly touch any system — all effects go through validated handlers.

---

## Infrastructure

Fully managed via Terraform — no manual console steps.

| Layer | Detail |
|---|---|
| Network | VPC, 2 public + 2 private subnets, one NAT Gateway per AZ (HA) |
| Compute | ECS Fargate — 3 separate services (voice, api, worker) |
| Database | RDS PostgreSQL 16 Multi-AZ, 14-day PITR, KMS encryption |
| Cache | ElastiCache Redis 7 replication group, in-transit + at-rest encryption |
| Storage | S3 recordings bucket — KMS, versioning, lifecycle, DenyInsecureTransport |
| Secrets | AWS Secrets Manager (16 secrets) — zero env-var credentials at runtime |
| Auth (CI) | OIDC-based GitHub Actions → AWS (no static IAM keys in CI) |
| Autoscaling | Voice service: CPU-based, up to 10 tasks; API service: up to 6 tasks |
| Deployment | Circuit-breaker + automatic rollback on every ECS service |

---

## Multi-Tenancy

Every database table carries `clinic_id`. The `get_scoped_clinic_id()` FastAPI dependency is the single tenancy chokepoint:

- Clinic-role JWTs: `clinic_id` is baked in — the query parameter is silently ignored, so URL manipulation cannot cross clinic boundaries.
- Platform-admin tokens: must explicitly name `?clinic_id=` — no implicit access to any clinic.

A clinic's data cannot appear in another clinic's API response regardless of how requests are crafted.

---

## Security Highlights

| Control | Implementation |
|---|---|
| Auth | Short-lived JWT (15 min) + rotating HttpOnly refresh cookie (one-shot, SHA-256 hash stored in Redis) |
| Rate limiting | 8 login attempts / 5 min per email+IP, Redis-backed |
| Timing attacks | Dummy bcrypt comparison for nonexistent users — response time is constant regardless |
| TwiML injection | `quoteattr()` used throughout TwiML builders — not `escape()` |
| Twilio webhook validation | `RequestValidator` against configured base URL — raw `Host` header is never trusted |
| PHI in logs | Structured logging; phone numbers and names explicitly excluded from log lines |
| KMS | All PHI at rest encrypted; S3, RDS, ElastiCache, Secrets Manager all use dedicated KMS keys |
| IAM | ECS tasks use task-scoped IAM roles — no static credentials anywhere in the codebase |

---

## CI/CD Pipeline

```
git push → GitHub Actions
              ├── pytest (183 tests)
              ├── Bandit (security scan)
              ├── Trivy (container image scan)
              ├── docker build → ECR push (immutable tags: git-SHA)
              ├── ECS blue/green deploy (both services in parallel)
              └── smoke_test.py → /health + /readyz (DB + Redis verified)
```

Concurrency group queues — never cancels — so two simultaneous pushes won't race on ECR image tags.

---

## Backend Stack

- **Python 3.11** / FastAPI / SQLAlchemy 2.0 async
- **PostgreSQL 16** with Alembic migrations
- **Redis 7** via `arq` (background jobs) and direct (sessions, rate limiting, tokens)
- **Stripe** — Customer + Subscription creation, webhook handlers for lifecycle events
- **Twilio** — Media Streams, Voice SDK (WebRTC browser demo), SMS, area-code search
- **Deepgram** Nova-3 — streaming STT
- **ElevenLabs** Flash — streaming TTS
- **Claude Sonnet** via OpenRouter — primary LLM

## Frontend

React 18 + Vite + Tailwind CSS — clinic dashboard (call log, recordings playback, appointments, settings) and platform admin panel (clinic onboarding, analytics).

---

## Repository Layout

```
sarah-ai-receptionist/
├── backend/
│   ├── app/
│   │   ├── config/settings.py          # Pydantic settings, all env-var driven
│   │   ├── core/                        # database, security, redis, clinic_time
│   │   ├── models/                      # 12 SQLAlchemy models
│   │   ├── routes/                      # call_handler, auth, appointments,
│   │   │                                #   dashboard, admin, billing
│   │   ├── services/                    # call_manager, ai_brain, stt, tts,
│   │   │                                #   appointment_service, billing_service,
│   │   │                                #   transfer_service, notification_service,
│   │   │                                #   call_recorder, action_parser
│   │   ├── workers/worker.py            # Arq job definitions
│   │   └── prompts/dental_receptionist.py
│   ├── alembic/                         # 5 migrations
│   └── requirements.txt
├── frontend/src/
│   ├── pages/                           # Dashboard, CallLog, Appointments,
│   │                                    #   Settings, Login, admin/*
│   └── services/api.js
├── infra/terraform/
│   └── modules/                         # networking, compute, database,
│                                        #   storage, security, loadbalancer
├── .github/workflows/
│   ├── sarah-deploy.yml                 # Full CI/CD pipeline
│   └── sarah-pr-checks.yml             # Lint + type-check + Bandit + Trivy
├── scripts/
│   ├── smoke_test.py
│   └── test_call.py                     # Local voice-loop simulator (no phone)
├── tests/                               # 183 tests
└── docker-compose.yml                   # Full local stack (postgres + redis + services)
```

---

## Local Development

```bash
cp .env.example .env          # fill in API keys
docker-compose up             # postgres + redis + all services
python scripts/test_call.py   # simulate a full call in terminal (no phone needed)
```

All external services have local stubs for development — no Twilio account required to run unit tests.

---

## What Was Hard

**Barge-in latency**: Cancelling TTS mid-stream requires flushing Twilio's jitter buffer, which involves a `<Clear>` verb injected on a separate HTTP call while the WebSocket is still open. Timing this against Deepgram's partial-vs-final transcript distinction took significant iteration.

**Cold-start health check kills**: ECS was killing the worker container before the Python interpreter finished importing SQLAlchemy + arq under low CPU. Solved by tuning `startPeriod` to 45s and using `python -c 'import app.workers.worker'` as the health check command — no HTTP surface needed.

**Race-safe booking**: Two concurrent calls booking the same slot hit a unique constraint. Rather than serializing all bookings, a savepoint + retry pattern handles the collision without locking the table.

**Token isolation per clinic**: The multi-tenant boundary had to be enforced at the dependency level, not the route level, so it could not be accidentally bypassed by a new route author. `get_scoped_clinic_id()` as a FastAPI dependency on every protected route achieves this.
