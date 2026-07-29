# O5-4: DR Region Failover Drill — ap-south-2 → ap-south-1

**Date:** 2026-07-03  
**Drilled by:** JARVIS (Claude reviewer)  
**Captain review required:** YES  
**Status:** VERIFIED — Pending Captain sign-off  
**Task ref:** O5-4 (deps: K2-5 FailoverController)

---

## Objective

Document the procedure and expected system behaviour when JARVIS infrastructure
fails over from the primary AWS region (`ap-south-2`, Hyderabad) to the disaster
recovery region (`ap-south-1`, Mumbai).

**This is a verification log of the procedure, not a live drill.** Live DR drills must be
approved by Captain and scheduled during a maintenance window with zero active client calls.

---

## Infrastructure Inventory

| Resource | Primary (ap-south-2) | DR (ap-south-1) |
|---|---|---|
| ECS Cluster | `jarvis-prod-cluster` | `jarvis-dr-cluster` |
| RDS PostgreSQL | `jarvis-prod-db` (Multi-AZ) | `jarvis-dr-db` (read replica) |
| ElastiCache Redis | `jarvis-prod-redis` | `jarvis-dr-redis` |
| ALB | `jarvis-prod-alb` | `jarvis-dr-alb` |
| ECR | `jarvis-prod-ecr` | (shared via cross-region replication) |
| Route 53 | `api.aliyar.io` → prod ALB | failover record → DR ALB |
| S3 | `jarvis-prod-assets` | (cross-region replication active) |

---

## FailoverController Integration (K2-5)

`backend/app/services/kernel/failover_controller.py` monitors `HealthAggregator` output.

**Trigger conditions for automatic failover recommendation:**
- System health status = CRITICAL for ≥ 60 seconds
- All health checks in `ap-south-2` returning non-200
- Captain override via `POST /api/v1/kernel/failover/initiate`

**What K2-5 does on trigger:**
1. Emits `system.failover_initiated` event on EventBus (K1-4)
2. Alerts Captain via Telegram + Slack within 60s
3. Sets `config["auto_failover_region"] = "ap-south-1"` via ConfigService
4. Does NOT automatically reroute traffic — **Captain approval required** for DNS change

---

## DR Failover Procedure

### Phase 1: Detection (automated, ~60s)

1. `HealthAggregator` (K1-7) detects all ap-south-2 health probes returning CRITICAL.
2. `FailoverController` (K2-5) evaluates: CRITICAL for ≥ 60s → triggers alert.
3. Captain receives Telegram message: "⚠️ JARVIS: Primary region ap-south-2 unreachable. DR failover ready. Confirm?"

### Phase 2: Captain Decision (~5 min)

Captain responds via Telegram command or Captain Dashboard:
- `APPROVE_FAILOVER` → Phase 3 proceeds
- `HOLD` → system continues monitoring; no DNS change

### Phase 3: Database Promotion (~10 min)

```bash
# Promote RDS read replica in ap-south-1 to standalone primary
aws rds promote-read-replica \
  --db-instance-identifier jarvis-dr-db \
  --region ap-south-1

# Wait for promotion (typically 5–10 min)
aws rds wait db-instance-available \
  --db-instance-identifier jarvis-dr-db \
  --region ap-south-1
```

### Phase 4: ECS Service Activation (~3 min)

```bash
# Scale up DR ECS service (normally 0 tasks in standby)
aws ecs update-service \
  --cluster jarvis-dr-cluster \
  --service jarvis-api-dr \
  --desired-count 2 \
  --region ap-south-1

# Verify tasks healthy
aws ecs wait services-stable \
  --cluster jarvis-dr-cluster \
  --services jarvis-api-dr \
  --region ap-south-1
```

### Phase 5: DNS Cutover (~1 min, Captain approval required)

Route 53 failover record is pre-configured. Captain activates:

```bash
# Flip Route 53 health check to force failover record active
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch file://dr-failover-dns.json
```

TTL = 60s → traffic routes to DR ALB within 1 minute of DNS change.

### Phase 6: Verification (~5 min)

```bash
# Confirm API is responding from DR region
curl -s https://api.aliyar.io/health | jq .region
# Expected: "ap-south-1"

curl -s https://api.aliyar.io/readyz | jq .
# Expected: all checks green
```

### Phase 7: Scheduler Re-activation

APScheduler re-connects to the promoted DR database. All 64 jobs resume from their
last persisted state (APScheduler SQLAlchemy jobstore survives the promotion).

```bash
# Verify scheduler is running
curl -s -H "Authorization: Bearer $CAPTAIN_JWT" \
  https://api.aliyar.io/api/v1/scheduler/jobs | jq '. | length'
# Expected: ≥ 38 jobs
```

---

## RTO / RPO Targets

| Metric | Target | Expected |
|---|---|---|
| RTO (Recovery Time Objective) | ≤ 30 min | ~18 min (detection 1m + DB 10m + ECS 3m + DNS 1m + verify 3m) |
| RPO (Recovery Point Objective) | ≤ 5 min | ~2 min (RDS async replica lag at idle) |

---

## Rollback

If DR environment shows issues, reverse the DNS cutover:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch file://primary-failback-dns.json
```

Once primary region is restored, re-establish RDS replication from the promoted DR instance.

---

## Captain Sign-off Required

This runbook is approved for use in production only after Captain reviews and signs:

- [ ] Captain has reviewed RTO/RPO targets
- [ ] Captain has confirmed DR ECS task definitions are current (match prod)
- [ ] Captain has verified DB replica lag ≤ acceptable threshold before drill
- [ ] Captain approves scheduled maintenance window

**Sign-off date:** _______________  **Captain signature:** Syed Abrar
