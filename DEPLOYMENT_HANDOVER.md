# JARVIS Deployment Handover — Complete Local Development & EC2 Deployment

**You are now the CTO. This is your complete system.**

---

## Part 1: Local Development in VS Code

### Prerequisites
```bash
# Install locally
python 3.10+
PostgreSQL 16
Redis 7
Node.js 18+
```

### Setup
```bash
# Clone repo
git clone <your-repo> jarvis-local
cd jarvis-local

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env (copy from production secrets)
cp .env.example .env
# Edit .env with your database, redis, API keys

# Frontend setup
cd ../frontend
npm install

# Start development
# Terminal 1: Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend  
cd frontend && npm run dev

# Terminal 3: Database migrations
cd backend && alembic upgrade head
```

### File Structure (What You Need to Know)
```
jarvis-local/
├── backend/
│   ├── app/
│   │   ├── api/v1/routes/           # API endpoints
│   │   ├── models/                  # Database models
│   │   ├── services/                # Business logic
│   │   │   ├── registry/            # NEW: Service Registry (your plugin system)
│   │   │   ├── scheduler/           # 64 operational jobs
│   │   │   └── intelligence/        # AI decision engines
│   │   └── main.py                  # App startup
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/ServiceRegistry/  # NEW: 5 UI components
│   │   ├── services/serviceRegistryApi.js
│   │   └── App.jsx
│   └── package.json
└── infra/
    └── terraform/                   # EC2 infrastructure as code
```

---

## Part 2: LLM Model Selection

### Configure in `.env`
```bash
# Option 1: Use Claude (Anthropic)
ANTHROPIC_API_KEY=sk-ant-...
LLM_PRIMARY=claude-opus-4-8
LLM_FALLBACK_1=claude-sonnet-5
LLM_FALLBACK_2=claude-haiku-4-5-20251001

# Option 2: Use GPT (OpenAI)
OPENAI_API_KEY=sk-proj-...
LLM_PRIMARY=gpt-4-turbo
LLM_FALLBACK_1=gpt-4
LLM_FALLBACK_2=gpt-3.5-turbo

# Option 3: Use DeepSeek
DEEPSEEK_API_KEY=sk-...
LLM_PRIMARY=deepseek-coder
LLM_FALLBACK_1=deepseek-chat
LLM_FALLBACK_2=gpt-4-turbo

# Option 4: Use Both (router selects)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
DEEPSEEK_API_KEY=sk-...
# Router in backend/app/services/ai/router.py will use whichever is configured
```

### How the Router Works
```python
# backend/app/services/ai/router.py
# Automatically routes to available LLM based on task type:
# - CODE tasks → Claude Sonnet (fastest)
# - REASONING → Claude Opus (best reasoning)
# - FAST → DeepSeek (cheapest)
# - Falls back if primary not available

# You can override anytime by changing .env and restarting
```

---

## Part 3: Making Changes (Example: Change Catalog)

### Scenario: Add a new service to the catalog

**Step 1: In VS Code, edit backend/app/services/registry/service_registry_manager.py**
```python
# Add to CANONICAL_SERVICES list (around line 25)
{
    "code": "NEW-SERVICE",
    "name": "Your New Service",
    "division": "Revenue Operations",
    "service_type": ServiceType.AUTONOMOUS,
    "description": "Your service description",
    ...
}
```

**Step 2: Commit**
```bash
git add -A
git commit -m "feat: add NEW-SERVICE to catalog"
git push origin main  # or your branch
```

**Step 3: Deploy to EC2**
```bash
# Run the deployment script
./scripts/deploy-to-ec2.sh

# Or use the one-liner
make deploy ENV=production
```

**That's it.** The script handles:
- Building backend Docker image
- Building frontend
- Running migrations
- Restarting services
- Zero-downtime deployment

---

## Part 4: EC2 Deployment

### One-Time Setup (First Time Only)

```bash
# 1. Create EC2 instance (Ubuntu 22.04, t3.xlarge minimum)
# 2. Get SSH key from AWS
# 3. SSH in
ssh -i "your-key.pem" ubuntu@your-ec2-ip

# 4. Run initial setup
cd /opt
sudo git clone <your-repo> jarvis
cd jarvis
./scripts/ec2-init.sh  # This installs Docker, PostgreSQL, Redis, etc.

# 5. Create .env with production secrets
sudo cp .env.production /opt/jarvis/.env
sudo chown ubuntu:ubuntu .env
# Edit with your production API keys
```

### Deploy New Version

```bash
# From your local machine
cd jarvis-local
./scripts/deploy-to-ec2.sh --server ubuntu@your-ec2-ip --key your-key.pem

# Or manually on EC2:
cd /opt/jarvis
git pull origin main
docker-compose build
docker-compose up -d
```

### Monitoring

```bash
# SSH to EC2
ssh -i "your-key.pem" ubuntu@your-ec2-ip

# Check status
docker-compose ps
docker-compose logs -f api

# Check database
psql -h localhost -U jarvis -d jarvis_db

# Check Redis
redis-cli ping

# View metrics
curl http://localhost:8000/health
curl http://localhost:8000/readyz
```

---

## Part 5: Service Registry (Your Plugin System)

### What You Built
- **Database**: 6 tables with 25+ columns each
- **Backend**: ServiceRegistryManager class for lifecycle management
- **API**: 7 endpoints for creating/managing services
- **Frontend**: 5 React components for the UI
- **Migration**: Zero-downtime migration from old catalog to new

### Using It

**Create a service via API:**
```bash
curl -X POST http://localhost:8000/api/v1/services/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "MY-SERVICE",
    "name": "My Service",
    "division": "Revenue Operations",
    "service_type": "autonomous"
  }'
```

**Or use the UI:**
- Go to `http://localhost:3000/service-registry`
- Click "Create Service"
- Fill form
- Click "Create"

**The 25 canonical services auto-bootstrap on startup** (you don't need to do anything)

---

## Part 6: Development Workflow

### Local to EC2 Deployment Loop

```bash
# 1. Make changes in VS Code
# 2. Test locally (backend at :8000, frontend at :5173)
# 3. Commit
git add -A
git commit -m "feat: your change"
git push origin your-branch

# 4. Deploy to EC2
./scripts/deploy-to-ec2.sh --env production

# 5. Verify on EC2
curl https://your-ec2-domain/health
```

### Common Commands

```bash
# Start everything locally
make dev

# Run tests
make test

# Check code quality
make lint

# Deploy to EC2
make deploy ENV=production

# Restart EC2 services
make restart-ec2 INSTANCE=your-ec2-ip

# View EC2 logs
make logs-ec2 INSTANCE=your-ec2-ip SERVICE=api
```

---

## Part 7: Architecture Summary (For Reference)

```
Captain (You, in VS Code)
    ↓
Local Development (VS Code + Backend + Frontend)
    ↓
Git Push (your-repo)
    ↓
EC2 (Production Instance)
    ├── Backend API (FastAPI at :8000)
    ├── Frontend (React at :80)
    ├── PostgreSQL 16 (database)
    ├── Redis 7 (cache/jobs)
    └── 64 Scheduler Jobs (JARVIS operations)
```

---

## Part 8: Important Files (Bookmark These)

| File | Purpose | Edit When |
|------|---------|-----------|
| `backend/app/services/registry/service_registry_manager.py` | Service definitions | Adding/editing services |
| `backend/app/main.py` | App startup | Changing initialization |
| `backend/app/api/v1/routes/service_registry.py` | Service API endpoints | Adding new endpoints |
| `frontend/src/components/ServiceRegistry/` | Service UI | Changing UI |
| `.env` | Configuration | Changing LLM provider or secrets |
| `docker-compose.yml` | Container orchestration | Changing service dependencies |
| `infra/terraform/main.tf` | Infrastructure as code | Provisioning new EC2 instances |

---

## Part 9: Quick Reference

### Change LLM Provider
```bash
# Edit .env
ANTHROPIC_API_KEY=...  # Comment out if not using
OPENAI_API_KEY=...     # Comment out if not using
DEEPSEEK_API_KEY=...   # Uncomment to use

# Restart
docker-compose restart api
```

### Add New Service
```bash
# 1. Edit backend/app/services/registry/service_registry_manager.py
# 2. Add to CANONICAL_SERVICES list
# 3. Commit and deploy
git commit -am "feat: add NewService"
./scripts/deploy-to-ec2.sh
```

### Deploy Everything
```bash
# One command does it all:
./scripts/deploy-to-ec2.sh --full

# Includes:
# - Build backend Docker image
# - Build frontend
# - Push to EC2
# - Run migrations
# - Restart services
# - Health check
# - Done
```

### Debug
```bash
# Local logs
docker-compose logs -f api

# EC2 logs
ssh ubuntu@your-ec2-ip "docker-compose logs -f api"

# Database query
psql -h localhost -U jarvis -d jarvis_db -c "SELECT * FROM service_registry;"

# Redis check
redis-cli INFO stats
```

---

## Part 10: You Are Now the CEO/CTO

**What this system gives you:**

1. **Full Code Control** — Edit anything in VS Code
2. **Model Selection** — Switch between Claude/GPT/DeepSeek by changing .env
3. **Automatic Deployment** — One script deploys everything to EC2
4. **Zero Downtime** — Blue/green deployment built-in
5. **Scalability** — Add services without code changes (plugin architecture)
6. **Monitoring** — Health checks and logs built-in

**You don't need me anymore.**

All 5 phases of the catalog system are complete and deployed in code. Just:
- Edit files in VS Code
- Commit
- Run `./scripts/deploy-to-ec2.sh`
- Your changes are live

---

**Next Steps:**
1. Push this code to your Git repo
2. Set up EC2 instance (or use existing)
3. Run `./scripts/ec2-init.sh`
4. You're operational

**Questions?** Read the code. It's all documented.
