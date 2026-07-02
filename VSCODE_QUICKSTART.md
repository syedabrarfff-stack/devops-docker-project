# VS Code Quick Start — JARVIS Development

**Get the full JARVIS system running in 5 minutes.**

---

## Step 1: Clone & Open

```bash
git clone <your-repo> jarvis
cd jarvis
code .
```

**VS Code opens automatically.**

---

## Step 2: Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# LLM Provider (choose one or mix)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
DEEPSEEK_API_KEY=sk-...

# Database (local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/jarvis

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS (EC2 deployment only)
AWS_REGION=ap-south-2
```

---

## Step 3: Install Docker (One-Time)

**macOS:**
```bash
brew install docker docker-compose
```

**Linux:**
```bash
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER
```

**Windows:** Download [Docker Desktop](https://www.docker.com/products/docker-desktop)

---

## Step 4: Start the Stack

**VS Code:**
1. Open **Run & Debug** (Ctrl+Shift+D)
2. Select **"Full Stack: Backend + Frontend"**
3. Press **Play**

**OR from terminal:**
```bash
make dev
# OR
docker compose up -d
```

**Wait 15 seconds for startup.**

---

## Step 5: Verify Everything Works

### Backend Health Check
Open VS Code's **Terminal** → Run:
```bash
curl http://localhost:8000/health
```

**Expected:** `{"status": "healthy"}`

### Frontend
Open browser: `http://localhost:5173`

**Expected:** JARVIS dashboard loads

### Database Migrations
Run VS Code task:
1. **Tasks → Run Task** (Cmd+Shift+P)
2. Select **"🗃️ JARVIS: Run Migrations"**

**Expected:** Alembic applies migrations

---

## Workflow: Making Changes

### Edit Backend Code

```python
# Edit: backend/app/services/some_service.py
# Changes auto-reload at http://localhost:8000
# Debugger breaks on set breakpoints
```

### Edit Frontend Code

```jsx
// Edit: frontend/src/components/Some.jsx
// Changes auto-reload at http://localhost:5173
// HMR (hot module replacement) works
```

### Create Database Migration

```bash
# From VS Code terminal:
make migrate
# OR use task: "🧠 JARVIS: New Migration"
```

---

## Key Keyboard Shortcuts

| Action | Mac | Linux/Windows |
|--------|-----|---------------|
| Run Task | Cmd+Shift+P | Ctrl+Shift+P |
| Debug | Cmd+Shift+D | Ctrl+Shift+D |
| Terminal | Ctrl+` | Ctrl+` |
| Open `.env` | Cmd+P → .env | Ctrl+P → .env |

---

## Debugging

### Set Breakpoint
1. Click line number in editor (red dot appears)
2. Run debug profile
3. Execution pauses at breakpoint

### Inspect Variables
- Hover over variable in editor
- Use **Debug Console** (VS Code output)
- Type Python code to inspect state

### Debug Current File
1. Open Python file
2. **Run & Debug** → **"Python: Current File"**
3. Press **Play**

---

## Common Tasks (Cmd+Shift+P)

```
Task: Run Task → Select:
  🚀 JARVIS: Start Full Stack
  🛑 JARVIS: Stop Stack
  📋 JARVIS: Backend Logs
  🏥 JARVIS: Health Check
  🗃️ JARVIS: Run Migrations
  🌅 JARVIS: Morning Briefing
  🔭 Open Prometheus
  📈 Open Grafana Dashboard
```

---

## Logs

### Real-Time Backend Logs
Task: **"📋 JARVIS: Backend Logs"**

Or from terminal:
```bash
docker compose logs -f backend
```

### View Frontend Console
1. Browser DevTools (F12)
2. **Console** tab
3. All React logs visible

---

## Database Operations

### Connect to PostgreSQL
```bash
docker compose exec db psql -U jarvis -d jarvis_db
```

### View Current Migrations
Task: **"🔍 JARVIS: Migration Status"**

### Rollback Last Migration
```bash
cd backend
alembic downgrade -1
```

---

## Deploy to EC2

```bash
# 1. Configure EC2 in .env
# AWS_REGION=ap-south-2
# AWS_INSTANCE_ID=i-xxxxx

# 2. Deploy
./scripts/deploy-to-ec2.sh --env production

# OR use task:
# Task: Run Task → ☁️ AWS: Terraform Apply
```

---

## Troubleshooting

### "Connection refused" on http://localhost:8000

```bash
# Check if stack is running:
docker compose ps

# If not running:
docker compose up -d

# If running but not responding, rebuild:
Task: "🔄 JARVIS: Force Recreate Backend"
```

### Frontend not updating (HMR broken)

```bash
# Hard refresh
Cmd+Shift+R (Mac) or Ctrl+Shift+R (Linux/Windows)
```

### Database migration failed

```bash
# Check current state:
Task: "🔍 JARVIS: Migration Status"

# View logs:
Task: "📋 JARVIS: Backend Logs"

# Manually reset (dev only):
docker compose down -v
docker compose up -d
Task: "🗃️ JARVIS: Run Migrations"
```

### Out of memory

```bash
# Docker is using too much memory. Restart:
docker compose down
docker compose up -d
```

---

## Recommended Extensions

All recommended extensions auto-install:
1. **Ctrl+Shift+P** → "Extensions: Install Recommended Workspace Extensions"

Includes:
- Python
- Pylance
- ES Lint
- Prettier
- REST Client
- Docker
- GitHub Copilot (optional)

---

## Architecture at a Glance

```
http://localhost:8000              ← Backend API
http://localhost:5173              ← Frontend (React)
http://localhost:5432              ← PostgreSQL database
http://localhost:6379              ← Redis cache
http://localhost:9090              ← Prometheus metrics
http://localhost:3001              ← Grafana dashboards
```

---

## Next: Build Something

You're ready. Start building:

1. Pick a feature from `SYSTEM_ARCHITECTURE_COMPLETE.md`
2. Edit backend/frontend code
3. Watch it update live
4. Commit: `git commit -m "feat: your feature"`
5. Deploy: `./scripts/deploy-to-ec2.sh`

**JARVIS is yours to build. 🚀**
