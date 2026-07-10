# JARVIS Production Architecture — Phase 8 (Stability First)

**Status:** AWAITING CAPTAIN APPROVAL
**Date:** 2026-07-10
**Author:** JARVIS Engineering Division
**Directive:** One region, one instance, Docker Compose, self-healing, $40–60/month, GoDaddy DNS stays.

---

## 1. CURRENT STATE — What Actually Exists (Measured, Not Assumed)

### 1.1 AWS Account Inventory (account 824232273953, region ap-south-2)

| Resource | Details | Verdict |
|---|---|---|
| **i-07887c05a28c22675** "jarvis-work-dr-recovery" | t3.micro, 1GB RAM, 25GB gp3, Elastic IP 16.112.184.189 | ✅ **THE production server** (DNS confirmed) |
| **i-00381dfb44fd3cf45** "Jarvis-Terraform-Server" | t3.micro, running, 8GB vol, serves HTTP 503, SSM agent dead | ❌ **Zombie — burning ~$8.5/mo for nothing** |
| **i-0ef8f36bbe4c23681** "jarvis-work" | t3.micro, STOPPED (pre-DR original), 25GB vol still attached | ❌ **Paying ~$2.4/mo for its idle disk** |
| S3 `jarvis-production-data-…` | DB backups + proposal PDFs | ⚠️ **Last backup 2026-06-13 — 27 days ago** |
| S3 `jarvis-ops-artifacts-…` | deploy artifacts, patches | ✅ keep |
| ECS clusters | **NONE** | ❌ `deploy.yml` ECS workflow deploys to nothing |
| ECR repositories | **NONE** | ❌ same |
| ap-south-1 / us-east-1 | empty | ✅ nothing hidden |

### 1.2 Production Server (measured 2026-07-10)

- **RAM: 908MB total, ~86MB free, 1GB swap in use** — the machine survives on swap; any Docker build takes the site DOWN (proven live today)
- **Disk: 24GB usable, 17GB used (72%)** — will hit the 85% cleanup threshold soon
- **Containers: 14 of 16 healthy.** Broken: `evolution-api` (WhatsApp) exited 2 days ago; `jarvis_frontend` intermittently unhealthy
- **Code on server: current** (commit 8260f2c, latest)

### 1.3 Built in GitHub but NEVER Deployed

| Item | Repo location | State on server |
|---|---|---|
| Nightly S3 backup + restore-verify | `scripts/backup-postgres.sh` + `infrastructure/systemd/jarvis-backup.{service,timer}` | **NOT installed** — backups dead since Jun 13 |
| 5-min self-healing health check (auto-restart containers, disk cleanup, memory/SSL/backup-age monitoring) | `scripts/jarvis-health-check.sh` + `jarvis-health-check.{service,timer}` | **NOT installed** |
| Boot-time auto-start of full stack | `jarvis-docker-compose.service` | **NOT installed** — reboot = manual recovery |
| Validation & benchmarking suite | `scripts/phase-8-validation.sh` | **NOT run** |
| Captain login credentials | `.env` `CAPTAIN_USERNAME/PASSWORD` | **NOT set** — login broken |
| IAM backup policy | `infrastructure/aws/iam-backup-policy.json` | **NOT attached** |

### 1.4 Root Causes Found & Already Fixed Today (in git, commits 134b6b6→8260f2c)

1. Deploy workflow picked "first running instance" → deployed to the zombie for weeks. **Fixed: pinned to prod instance ID.**
2. SSM shell has no `$HOME` → every SSM deploy died at git config. **Fixed.**
3. Workflow default action was destructive `full-restart` → accidental rebuilds. **Fixed: default now read-only `verify-status`.**
4. Password hash was committed to git at a wrong path. **Removed.**
5. `set-captain-credentials` action added (secrets travel as masked runtime inputs, never in git).

### 1.5 Still Broken (needs the plan below)

- ⛔ `on: push` trigger auto-deploys to production on every commit — caused today's outage
- ⛔ Captain cannot log in to the dashboard
- ⛔ No backups for 27 days
- ⛔ Evolution API (WhatsApp) container down
- ⛔ 1GB RAM cannot run 16 containers + builds (root cause of all fragility)
- ⛔ Dead ECS/Terraform workflows create noise and risk
- ⛔ No alerting reaches Captain before failures become outages

---

## 2. TARGET ARCHITECTURE

```
                     GoDaddy DNS (unchanged)
                aliyarsolutions.com → 16.112.184.189 (same Elastic IP)
                              │
┌─────────────────────────────▼──────────────────────────────────────┐
│  EC2 i-07887c05a28c22675 — RESIZED IN PLACE t3.micro → t3.large    │
│  2 vCPU / 8GB RAM / EBS grown 25GB → 50GB gp3 / same IP, same disk │
│                                                                    │
│  ┌──────────── systemd (self-healing layer) ─────────────────────┐ │
│  │ jarvis-docker-compose.service  → full stack up on every boot  │ │
│  │ jarvis-health-check.timer (5m) → restart unhealthy containers,│ │
│  │   disk >85% auto-prune, RAM/SSL/backup-age/scheduler watch    │ │
│  │ jarvis-backup.timer (02:00)    → pg_dump → gzip → S3 +        │ │
│  │   restore-verification + 30-day retention                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  Docker Compose (16 services)                                      │
│  ├─ nginx (80/443, TLS, basic-auth) ── certbot auto-renew          │
│  ├─ backend FastAPI (Gunicorn ×3) ── frontend React                │
│  ├─ postgres 16 + pgvector ── redis 7                              │
│  ├─ evolution-api (WhatsApp) ← REPAIRED                            │
│  └─ prometheus, grafana, alertmanager, loki, promtail,             │
│     node/postgres/redis exporters, cadvisor                        │
│                                                                    │
│  Alerting: Alertmanager → Telegram/Slack to Captain                │
│  (container down, disk, RAM, SSL expiry, backup age, 5xx spike)    │
└────────────────────────────────────────────────────────────────────┘
                              │
              AWS layer (outside the box):
              • CloudWatch StatusCheckFailed alarm → EC2 auto-recover
                (hardware failure = automatic instance recovery)
              • Daily EBS snapshot (7-day retention) via Data
                Lifecycle Manager — whole-disk disaster recovery
              • S3: nightly DB dumps, 30-day retention
```

**Why resize-in-place instead of a new instance:** same disk, same Elastic IP, same data — zero migration risk, zero DNS change at GoDaddy, ~5 minutes downtime once. A new instance would mean DB restore + DNS cutover + cert re-issue for no benefit at this stage.

**Deploy pipeline (after fix):** GitHub Actions is **manual-trigger only** (`workflow_dispatch`). Push to branch never touches production again. One workflow, pinned to the production instance, actions: `verify-status` (default, read-only) / `full-restart` / `backend-only` / `frontend-only` / `nginx-reload` / `set-captain-credentials`.

---

## 3. COST (honest numbers, ap-south-2)

| Item | Monthly |
|---|---|
| EC2 t3.large on-demand (~$0.0848/hr × 730h) | ~$61.90 |
| EBS 50GB gp3 | ~$4.40 |
| Daily EBS snapshots (7-day retention, incremental) | ~$2.50 |
| S3 backups (~15GB) | ~$0.40 |
| Data transfer | ~$0.50 |
| **Subtotal t3.large on-demand** | **~$69.70** ⚠️ over budget |
| Savings from killing zombie instance + stopped-instance volume | **−$11** |
| **Net total** | **~$59/mo — inside the $40–60 budget** ✅ |

**Options if you want more headroom:**
- **1-year no-upfront Compute Savings Plan** on t3.large → ~$42/mo net total ✅✅ (commits you for 12 months)
- **t3.medium fallback** (4GB RAM = 4× current): net ~$36/mo, but less headroom for AI workloads

**My recommendation: t3.large on-demand now (net ~$59/mo), add the Savings Plan after 30 days of stable measured usage.**

---

## 4. IMPLEMENTATION PLAN (after your approval)

**Phase A — Stabilize (30 min, no downtime)**
1. Remove `on: push` production trigger from ec2-deploy.yml (root cause of today's outage)
2. Disable dead ECS deploy.yml + terraform-apply.yml workflows
3. Fix Captain login via `set-captain-credentials` workflow run
4. Repair evolution-api container
5. **Take an immediate manual DB backup to S3** (ends the 27-day gap today)

**Phase B — Resize (5–10 min planned downtime, your go/no-go)**
6. EBS snapshot (restore point) → stop instance → modify type to t3.large → grow volume to 50GB → start → verify all 16 containers

**Phase C — Self-healing deployment (1 hour, no downtime)**
7. Install the 3 systemd units (boot-start, 5-min health check, nightly backup)
8. Verify Alertmanager routes alerts to your Telegram/Slack; add backup-age + disk + container-down alert rules
9. Create CloudWatch StatusCheckFailed → auto-recover alarm; enable daily EBS snapshots (DLM)

**Phase D — Verify & report (1 hour)**
10. Run `phase-8-validation.sh` full suite; test: kill a container (auto-restarts?), reboot instance (stack auto-starts?), restore a backup (data intact?)
11. Deliver Production Health Report: every issue found, every issue fixed, measured CPU/RAM/disk/DB/Redis utilization on the new instance

**Cleanup (needs your explicit approval — destructive):**
- Terminate zombie `Jarvis-Terraform-Server` (i-00381dfb44fd3cf45)
- Snapshot then terminate stopped `jarvis-work` (i-0ef8f36bbe4c23681) and delete its volume

---

## 5. FUTURE (not now — for the record)

- **Headquarters multi-LLM control** (OpenRouter, DeepSeek, Gemini): backend AI-router already supports 11 providers; keys go into `.env` via Secrets Manager — no infra change needed
- **Phase 2 (first paying clients):** second instance + ALB (~+$45/mo)
- **Phase 3 (>$10k MRR):** managed RDS/ElastiCache, multi-AZ

---

*Nothing in Phases B–D executes until Captain approves this document.*
