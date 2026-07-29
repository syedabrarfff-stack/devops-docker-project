# 🎛️ JARVIS Dashboard Setup & Access Guide

## ✅ Configuration Complete

All three dashboards have been configured with unified credentials and authentication.

### Authentication Credentials

| Service | Username | Password | URL |
|---------|----------|----------|-----|
| **Control Room (Frontend)** | `captain` | `captain` | http://localhost:3002/control-room |
| **Grafana Dashboards** | `captain` | `captain` | http://localhost:3001 |
| **Loki Logs** | `captain` | `captain` | http://localhost:3001/d/loki-logs |
| **Prometheus Metrics** | (no auth) | (no auth) | http://localhost:9090 |
| **Backend API** | (no auth required) | (no auth required) | http://localhost:8000/api/v1 |

---

## 🚀 Starting All Services

### Prerequisites

```bash
# Navigate to project root
cd /home/user/devops-docker-project

# Ensure .env file has correct passwords (already configured)
grep -E "REDIS_PASSWORD|GRAFANA_ADMIN|POSTGRES_PASSWORD" .env
```

### Start Docker Compose Stack

```bash
# Start all services in background
docker compose up -d

# Watch the services starting up
docker compose logs -f

# Check service health
docker compose ps
```

### Expected Output

```
CONTAINER ID   IMAGE                                    STATUS           NAMES
...
  jarvis_redis              Up (healthy)      
  jarvis_postgres           Up (healthy)      
  jarvis_backend            Up (healthy)      
  jarvis_frontend           Up (healthy)      
  jarvis_nginx              Up (healthy)      
  jarvis_grafana            Up (healthy)      
  jarvis_prometheus         Up (healthy)      
  jarvis_loki               Up (healthy)      
  jarvis_promtail           Up (healthy)      
```

---

## 📊 Dashboard Access

### 1. JARVIS Control Room (Frontend Dashboard)

**What it shows:**
- Real-time system monitoring (AI costs, provider health, scheduler status)
- Lead management and CRM
- Outreach campaigns and communications
- Administrative controls

**Access:**
```
URL: http://localhost or http://localhost:3002/control-room
Auth: captain / captain
```

### 2. Grafana Dashboards

**What it shows:**
- System metrics (CPU, memory, disk)
- Database performance
- API request rates and response times
- Container resource usage

**Access:**
```
URL: http://localhost:3001 (or via nginx http://localhost/grafana)
Auth: captain / captain
```

**Default Dashboards:**
- **JARVIS Main** — Overall system health and metrics
- **Loki Logs** — Real-time application logs

### 3. Loki Logging Dashboard

**What it shows:**
- Real-time application logs from all containers
- Backend service logs
- Nginx access logs
- Error and warning traces

**Access:**
```
URL: http://localhost:3001/d/loki-logs
Auth: captain / captain
```

**Log Streams:**
- JARVIS System Logs — Combined logs from backend, frontend, nginx
- Backend Logs — FastAPI application logs
- Nginx Logs — HTTP access and error logs
- Errors & Warnings — Filtered ERROR, CRITICAL, FATAL level logs

---

## 🔧 Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy (80/443)             │
│                   (Basic Auth: captain/captain)             │
└────────┬────────────────────────────────────────────────────┘
         │
    ┌────┴────────┬──────────────┬──────────────┐
    │             │              │              │
    v             v              v              v
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│Frontend │  │ Backend  │  │ Evolution│  │ Grafana  │
│:3002    │  │ :8000    │  │ :8080    │  │ :3001    │
└────┬────┘  └────┬─────┘  └──────────┘  └────┬─────┘
     │            │                            │
     v            v                            v
  ┌──────────────────────────┐        ┌─────────────────┐
  │   PostgreSQL + Redis     │        │  Prometheus     │
  │   :5432 | :6379         │        │  Loki | Promtail│
  └──────────────────────────┘        └─────────────────┘
```

---

## 🔐 Environment Configuration

The following environment variables are already configured in `.env`:

```bash
# Database
POSTGRES_PASSWORD=jarvis_secret
POSTGRES_USER=jarvis
POSTGRES_DB=jarvis

# Redis
REDIS_PASSWORD=captain

# Grafana
GRAFANA_ADMIN_USER=captain
GRAFANA_ADMIN_PASSWORD=captain

# API Keys & Services
ANTHROPIC_API_KEY=sk-ant-...
EVOLUTION_API_KEY=jarvis-master-key
TELEGRAM_BOT_TOKEN=...
SLACK_WEBHOOK_URL=...
```

---

## 📈 Monitoring & Logs

### Real-Time Monitoring

```bash
# Watch backend logs
docker compose logs -f backend

# Watch frontend logs
docker compose logs -f frontend

# Watch all logs
docker compose logs -f

# Watch specific service
docker compose logs -f grafana
```

### Health Checks

```bash
# Test Backend API
curl http://localhost:8000/health

# Test Grafana
curl http://localhost:3001/api/health

# Test Prometheus
curl http://localhost:9090/-/healthy

# Test Loki
curl http://localhost:3100/ready
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it jarvis_postgres psql -U jarvis -d jarvis

# Useful queries:
SELECT * FROM tenant;          -- Check tenants
SELECT * FROM ai_request_log;  -- Check AI costs
SELECT COUNT(*) FROM leads;    -- Check lead count
```

---

## 🛠️ Troubleshooting

### Services Not Starting

```bash
# Check Docker status
docker compose ps

# Check logs for errors
docker compose logs <service-name>

# Restart a single service
docker compose restart <service-name>

# Restart all services
docker compose restart
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running and accessible
docker exec jarvis_postgres pg_isready -U jarvis

# Check database exists
docker exec jarvis_postgres psql -U jarvis -l
```

### Grafana Not Showing Data

1. Verify Prometheus is running: `http://localhost:9090`
2. Check Prometheus targets are healthy
3. Verify Loki datasource is configured (should be automatic)
4. Check container logs: `docker compose logs grafana`

### Authentication Issues

```bash
# Verify nginx .htpasswd file
cat infrastructure/nginx/.htpasswd

# Test basic auth (should return 200)
curl -u captain:captain http://localhost/control-room
```

---

## 📱 Mobile Access (Local Network)

If accessing from another device on the local network:

```bash
# Get your machine's IP
hostname -I

# Access from another device:
# http://<YOUR_IP>:3002/control-room
# http://<YOUR_IP>:3001/grafana
# http://<YOUR_IP>:9090 (Prometheus)
```

---

## 📋 Daily Operations

### Check System Health

```bash
# Navigate to Control Room
# → Monitoring → Check dashboard

# Or use CLI:
curl http://localhost:8000/api/v1/system/hud | jq .
```

### View Recent Errors

```bash
# In Grafana Loki
# → Errors & Warnings panel
# → Filter by time range

# Or CLI:
docker compose logs --tail=100 --timestamps=true
```

### Monitor AI Costs

```bash
# Navigate to Control Room
# → Monitoring → AI Cost Breakdown

# Or API:
curl -u captain:captain http://localhost:8000/api/v1/ai-ops/cost/today | jq .
```

---

## 🔄 Updates & Maintenance

### Rebuild Containers

```bash
# Rebuild with latest code
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Database Migrations

```bash
# Backend automatically runs migrations on startup
# Monitor the logs:
docker compose logs -f backend | grep -i "migration\|alembic"
```

### Backup Data

```bash
# PostgreSQL backup
docker exec jarvis_postgres pg_dump -U jarvis jarvis > backup.sql

# Full volume backup
docker compose down
tar -czf jarvis_backup.tar.gz postgres_data/ redis_data/ grafana_data/
```

---

## 🎯 Quick Start Summary

```bash
# 1. Navigate to project
cd /home/user/devops-docker-project

# 2. Start services
docker compose up -d

# 3. Wait for health checks (30-60 seconds)
docker compose ps

# 4. Access dashboards:
# Control Room:  http://localhost:3002/control-room
# Grafana:       http://localhost:3001
# Loki Logs:     http://localhost:3001/d/loki-logs
# Prometheus:    http://localhost:9090

# 5. Login with: captain / captain
```

---

## ✨ All Systems Operational

✅ **Frontend Dashboard** — React 18 with Glassmorphism UI  
✅ **Backend API** — FastAPI with 11-provider LLM routing  
✅ **Grafana** — Real-time metrics and monitoring  
✅ **Loki** — Centralized log aggregation  
✅ **Prometheus** — Metrics scraping and storage  
✅ **PostgreSQL** — Primary data store  
✅ **Redis** — Caching and session management  
✅ **Evolution API** — WhatsApp integration  

All systems are configured, authenticated, and ready to deploy! 🚀
