# JARVIS Infrastructure Setup Guide

**Date:** 2026-06-12
**Region:** ap-south-2 (Hyderabad)
**Captain:** Syed Abrar
**WhatsApp Number:** +973 34360246

---

## Phase 1: WhatsApp Integration (Evolution API)

### Status
- ✅ Evolution API configured in Docker Compose
- ✅ Instance name: `jarvis-main`
- ⏳ Pending: Phone pairing to +973 34360246

### Pairing Instructions (AWS ECS)

1. **Access Evolution API on EC2/ECS:**
```bash
# SSH into EC2 or exec into ECS task
curl -X POST http://localhost:9000/instance/create \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "jarvis-main",
    "qrcode": true
  }'
```

2. **Request pairing code to Captain's phone:**
```bash
curl -X POST http://localhost:9000/instance/jarvis-main/request-code \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "+97334360246"}'
```

3. **Confirm connection:**
```bash
curl -X GET http://localhost:9000/instance/jarvis-main/connection-state \
  -H "apikey: jarvis-master-key"
```

### Environment Variables (Already set in `.env`)
```
EVOLUTION_API_KEY=jarvis-master-key
EVOLUTION_API_URL=http://evolution:8080
EVOLUTION_PUBLIC_URL=https://aliyarsolutions.com/evolution
WHATSAPP_ENABLED=true
WHATSAPP_INSTANCE_NAME=jarvis-main
WHATSAPP_DISPLAY_IDENTITY=Joseph David
```

---

## Phase 2: AWS SES Domain Verification

### Domain: aliyarsolutions.com
### Status
- ⏳ Pending: DNS records added to GoDaddy

### Required DNS Records

Add the following records to **GoDaddy DNS** for `aliyarsolutions.com`:

**1. DKIM Record 1 (Get tokens from AWS SES Console first):**
```
Type: CNAME
Name: token1._domainkey.aliyarsolutions.com
Value: token1.dkim.amazonses.com
TTL: 3600
```

**2. DKIM Record 2:**
```
Type: CNAME
Name: token2._domainkey.aliyarsolutions.com
Value: token2.dkim.amazonses.com
TTL: 3600
```

**3. DKIM Record 3:**
```
Type: CNAME
Name: token3._domainkey.aliyarsolutions.com
Value: token3.dkim.amazonses.com
TTL: 3600
```

**4. SPF Record:**
```
Type: TXT
Name: aliyarsolutions.com (or @)
Value: v=spf1 include:amazonses.com ~all
TTL: 3600
```

**5. DMARC Record (Optional but recommended):**
```
Type: TXT
Name: _dmarc.aliyarsolutions.com
Value: v=DMARC1; p=none; rua=mailto:jarvis@aliyarsolutions.com
TTL: 3600
```

### Steps to Get DKIM Tokens from AWS

1. Go to AWS SES Console (ap-south-2)
2. Select "Domains" → "Verify New Domain"
3. Enter: `aliyarsolutions.com`
4. AWS will generate 3 CNAME tokens
5. Copy token values into GoDaddy DNS
6. Return to AWS and click "Verify Domain DKIM"

---

## Phase 3: AWS ECS Deployment (Current)

### Cluster Configuration
```
Region:        ap-south-2 (Hyderabad)
Cluster:       jarvis-production
Capacity:      FARGATE + FARGATE_SPOT
Task CPU:      512 (0.5 vCPU)
Task Memory:   1024 MB
Auto-scaling:  1-5 tasks (70% CPU threshold)
```

### Database
```
Engine:        PostgreSQL 16 (RDS)
Instance:      db.t3.small
Storage:       20GB (auto-scales to 100GB)
Region:        ap-south-2
Backup:        ap-south-1 (Phase 2)
```

### Redis Cache
```
Engine:        Redis 7
Provider:      ElastiCache
Memory:        256MB default
Region:        ap-south-2
```

---

## Phase 4: Monitoring & Logging

### CloudWatch
- ✅ ECS Container Insights enabled
- ✅ Application Logs: `/aws/ecs/jarvis-production`
- ✅ Metrics: CPU, Memory, Network

### Prometheus + Grafana
- ✅ Local stack configured
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

---

## Deployment Checklist

- [ ] WhatsApp pairing confirmed (+973 34360246)
- [ ] SES domain verified (3 DKIM CNAMEs + SPF in GoDaddy DNS)
- [ ] ECS task logs showing healthy startup
- [ ] Redis connection verified
- [ ] PostgreSQL migration complete
- [ ] API health check: `/health` returning 200
- [ ] Dashboard accessible at https://aliyarsolutions.com
- [ ] Email sends via SES working (test with `/api/v1/test/send-email`)

---

## Rollback Procedures

### WhatsApp Disconnect
```bash
curl -X DELETE http://localhost:9000/instance/jarvis-main
```

### RDS Snapshot Restore
```bash
# AWS CLI
aws rds describe-db-snapshots --region ap-south-2
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier jarvis-restored \
  --db-snapshot-identifier <snapshot-id> \
  --region ap-south-2
```

---

## Next Steps

1. **Pair WhatsApp** (execute commands on ECS task)
2. **Add DNS records** (GoDaddy — 15 min propagation)
3. **Verify SES** (AWS Console — 1 min)
4. **Test integration** (API endpoint tests)
5. **Monitor logs** (CloudWatch)

---

**JARVIS Infrastructure Core** — Aliyar Solutions  
Generated: 2026-06-12 | Hyderabad Region
