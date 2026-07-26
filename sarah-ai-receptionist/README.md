# Sarah — AI Voice Receptionist Platform

Multi-tenant AI voice receptionist SaaS, built by **Aliyar Solutions**. Sarah answers inbound
phone calls for dental clinics 24/7 — books appointments, answers insurance/hours questions,
handles emergencies, and gives every clinic a live dashboard of every call.

## Architecture

```
Caller dials clinic's Twilio number
        │
        ▼
   Twilio Media Streams (bidirectional WebSocket audio)
        │
        ▼
   voice-service (FastAPI, ECS Fargate)
        │
        ├─► Deepgram Nova-3 ── streaming speech-to-text (event-driven, not polled)
        │
        ├─► Claude Sonnet 4.6 (via OpenRouter) ── sentence-buffered streaming response
        │        first sentence starts speaking before the rest finishes generating
        │
        └─► ElevenLabs Turbo ── streaming text-to-speech, mulaw/8kHz (Twilio-native)
        │
        ▼
   Caller hears Sarah — with real barge-in: interrupting mid-sentence
   cancels in-flight TTS/AI and flushes Twilio's audio buffer instantly.
```

Every call is transcribed, logged, and — if the caller books — turned into a real
`appointments` row, an SMS confirmation, and a clinic-dashboard entry, all scoped by
`clinic_id` for strict multi-tenant isolation.

## Repository Layout

```
backend/            FastAPI app — voice engine, REST API, Alembic migrations
  app/
    services/        ai_brain, speech_to_text, text_to_speech, call_manager, barge_in,
                      appointment_service, notification_service, call_recorder
    routes/           call_handler (Twilio), auth, appointments, dashboard, admin
    models/           organizations, clinics, providers, patients, appointments,
                       call_logs, users, audit_log, subscriptions
    workers/          Arq background jobs — call summaries, appointment reminders
frontend/            React 18 + Vite + Tailwind — clinic dashboard + admin console (single SPA)
infra/terraform/     VPC, ECS Fargate, RDS, ElastiCache, S3, Route53, CloudFront, ACM
docker/              Dockerfiles for backend (voice/api/worker) and frontend
.github/workflows/   CI (lint/test/security scan) + CD (build → ECR → ECS blue/green)
scripts/             test_call.py, setup_twilio.py, smoke_test.py
```

## Local Development

```bash
cd sarah-ai-receptionist
cp .env.example backend/.env   # fill in real API keys — never commit this file
docker compose up --build
```

- API: http://localhost:8000/docs
- Dashboard: http://localhost:5173
- Terminal call simulator (no phone needed): `python scripts/test_call.py`

To take a real call locally: `ngrok http 8000`, then
`python scripts/setup_twilio.py --url https://your-ngrok-url.ngrok.io`.

## Database Migrations

```bash
cd backend
alembic upgrade head
```

## Production Deployment

Infrastructure is Terraform-managed. DNS uses **subdomain delegation** — the root domain
`aliyarsolutions.com` (currently on GoDaddy) is untouched; only three subdomains are
delegated to Route53:

| Subdomain | Serves | Why |
|---|---|---|
| `sarah.aliyarsolutions.com` | Voice engine + API (ALB direct) | Twilio Media Streams need low-latency WebSocket, no CDN hop |
| `app.aliyarsolutions.com` | Clinic dashboard (CloudFront + S3) | Static SPA, CDN-cached |
| `admin.aliyarsolutions.com` | Admin console (same SPA, `/admin` routes) | Same distribution as above |

```bash
cd infra/terraform/environments/prod
cp terraform.tfvars.example terraform.tfvars   # fill in real values
terraform init -backend-config="bucket=..." -backend-config="key=..." -backend-config="region=..."
terraform plan
terraform apply
```

After `apply`, Terraform outputs three sets of Route53 name servers — add each as an
**NS record** for its subdomain in the GoDaddy DNS panel for `aliyarsolutions.com`
(e.g. host `sarah`, type `NS`, values = the four name servers). Propagation is typically
under an hour. The root domain, website, and email records are never touched.

Real secrets (Twilio, Deepgram, ElevenLabs, OpenRouter, Stripe, JWT signing key) are
populated directly into AWS Secrets Manager after `apply` — Terraform only creates the
secret containers, never the values, so nothing sensitive lives in state or git history.

CI/CD (`.github/workflows/deploy.yml`) builds the backend image once (shared by
voice/api/worker services), pushes to ECR, force-deploys all three ECS services with
the deployment circuit breaker (auto-rollback on failed health checks), and syncs the
frontend build to S3 behind a CloudFront invalidation.

## Engineering Standards

- No `debug=True` anywhere in the codebase
- Every table carries `clinic_id` — every query is tenant-scoped, no exceptions
- Secrets only via environment variables (local) or Secrets Manager (prod) — never in code
- PHI encrypted at rest (RDS + S3 via KMS) and in transit (TLS 1.3)
- Structured logging with `call_sid` on every voice-engine log line
- ECS deployments use the circuit breaker: a failing health check auto-rolls back
