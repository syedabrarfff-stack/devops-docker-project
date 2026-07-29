# JARVIS Local Development Handover
## Complete Setup Guide for VS Code

This document walks you through setting up JARVIS as your complete local development headquarters in VS Code with all capabilities end-to-end.

---

## Prerequisites Checklist

Before starting, verify you have installed:

- [ ] **Git** - `git --version` (should be 2.30+)
- [ ] **Docker Desktop** - `docker --version` (should be 4.0+)
- [ ] **Node.js** - `node --version` (should be 18+)
- [ ] **Python** - `python3 --version` (should be 3.9+)
- [ ] **pip** - `pip3 --version`
- [ ] **VS Code** - Latest version with extensions installed

### Install Missing Tools

**macOS (using Homebrew):**
```bash
brew install git node python3
brew install --cask docker
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y git nodejs python3 python3-pip docker.io
sudo usermod -aG docker $USER
```

**Windows (using Chocolatey or direct download):**
- Git: https://git-scm.com/download/win
- Node: https://nodejs.org/
- Python: https://www.python.org/downloads/
- Docker Desktop: https://www.docker.com/products/docker-desktop

---

## Step 1: Clone the Repository

```bash
# Navigate to your workspace
cd ~/workspace

# Clone the repository
git clone https://github.com/syedabrarfff-stack/devops-docker-project.git
cd devops-docker-project

# Open in VS Code
code .
```

---

## Step 2: Configure Environment Variables

Copy the example env file and add your API keys:

```bash
cp .env.example .env
```

Open `.env` in VS Code and fill in your credentials:

```env
# Database
DATABASE_URL=postgresql+asyncpg://jarvis:jarvis_password@localhost:5432/jarvis

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM API Keys (Configure all that you have)
ANTHROPIC_API_KEY=your_claude_key_here
OPENAI_API_KEY=your_openai_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
GOOGLE_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
MISTRAL_API_KEY=your_mistral_key_here

# AWS (for deployment - optional for local dev)
AWS_REGION=ap-south-2
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Company Configuration
COMPANY_NAME=Aliyar Solutions
JARVIS_DEFAULT_TENANT_ID=794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1

# Development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Frontend
REACT_APP_API_URL=http://localhost:8000
```

**⚠️ SECURITY:** Never commit `.env` to Git. It's in `.gitignore` for a reason.

---

## Step 3: Set Up Git Credentials

### GitHub CLI (Recommended)

```bash
# Install GitHub CLI
# macOS: brew install gh
# Linux: sudo apt-get install gh
# Windows: https://cli.github.com/

# Login to GitHub
gh auth login

# Select: GitHub.com
# Select: HTTPS
# Authenticate with browser
```

### SSH Key (Alternative)

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to GitHub: https://github.com/settings/keys
cat ~/.ssh/id_ed25519.pub

# Test connection
ssh -T git@github.com
```

---

## Step 4: Set Up AWS Credentials (Optional - for deployment)

```bash
# Install AWS CLI
# macOS: brew install awscli
# Linux: pip3 install awscli
# Windows: https://aws.amazon.com/cli/

# Configure AWS
aws configure

# Enter:
# AWS Access Key ID: [from IAM]
# AWS Secret Access Key: [from IAM]
# Default region: ap-south-2
# Default output format: json

# Verify
aws sts get-caller-identity
```

---

## Step 5: Install Dependencies

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; print(fastapi.__version__)"
```

### Frontend

```bash
cd frontend

# Install Node dependencies
npm install

# Verify installation
npm --version && node --version
```

---

## Step 6: Start Local Services

### Start Docker Containers (Database + Redis)

```bash
cd infrastructure

# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Verify services are running
docker-compose ps

# Wait 10 seconds for services to initialize
sleep 10

# Check logs if needed
docker-compose logs postgres
```

### Start Backend Server

```bash
cd backend

# Activate venv if not already active
source venv/bin/activate

# Run migrations
alembic upgrade head

# Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at: `http://localhost:8000`

API docs: `http://localhost:8000/docs`

### Start Frontend Server (in separate terminal)

```bash
cd frontend

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

---

## Step 7: Verify Everything Works

### Health Check - Backend

```bash
# Terminal 1: Backend is running

# Terminal 3: Run health check
curl http://localhost:8000/health | python3 -m json.tool

# Expected response:
# {
#   "status": "ok",
#   "system": "JARVIS",
#   "company": "Aliyar Solutions",
#   "version": "9.0.0"
# }
```

### Health Check - Frontend

Open browser: `http://localhost:5173`

You should see the JARVIS login page with dark theme.

### Health Check - Database

```bash
# Check if migrations applied
docker-compose exec postgres psql -U jarvis -d jarvis -c "\dt"

# You should see tables: leads, clients, approvals, etc.
```

### Health Check - APIs

```bash
# Test monitoring API
curl http://localhost:8000/api/v1/monitoring/health | python3 -m json.tool

# Test billing API  
curl http://localhost:8000/api/v1/billing/costs/summary/794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1 | python3 -m json.tool
```

---

## Step 8: Test Development Workflow

### Make a Code Change

**Backend Example:**
```bash
# Edit file
code backend/app/api/v1/routes/monitoring.py

# Change something (e.g., a response message)
# Server auto-reloads (check terminal for reload message)

# Test via curl
curl http://localhost:8000/api/v1/monitoring/health
```

**Frontend Example:**
```bash
# Edit file
code frontend/src/components/MonitoringDashboard/index.jsx

# Change something (e.g., a dashboard title)
# Browser auto-reloads (check browser for change)
```

### Commit and Push Changes

```bash
# Check status
git status

# Stage changes
git add .

# Commit
git commit -m "feat: your feature description"

# Push to your branch
git push origin your-branch-name
```

---

## Step 9: Configure VS Code for JARVIS Development

### Recommended Extensions

Install from VS Code Extensions:

1. **Python** - Microsoft (code completion, debugging)
2. **Pylance** - Microsoft (advanced Python analysis)
3. **FastAPI** - Tiangolo (FastAPI support)
4. **ESLint** - Microsoft (JavaScript linting)
5. **Prettier** - Prettier (code formatting)
6. **Thunder Client** - rangav (API testing)
7. **Docker** - Microsoft (Docker management)
8. **GitHub Pull Requests** - Microsoft (PR management)
9. **GitLens** - Eric Amodio (git history)

### Debug Configurations

VS Code debug profiles are already configured in `.vscode/launch.json`. Available:

- **FastAPI: Local Dev** - Backend with reload
- **FastAPI: Debug (no reload)** - Backend debugging
- **Frontend: Vite Dev** - Frontend with HMR
- **Pytest: Current File** - Run tests for current file
- **Alembic: Upgrade Head** - Database migrations

### Development Tasks

VS Code tasks are configured in `.vscode/tasks.json`. Use Cmd+Shift+P and search "Tasks: Run Task":

- **JARVIS: Start Full Stack** - Start backend + frontend + database
- **JARVIS: Stop Stack** - Stop all services
- **JARVIS: Backend Logs** - View backend logs
- **JARVIS: Health Check** - Run health checks
- **JARVIS: Run Migrations** - Apply database migrations

---

## Step 10: Daily Development Workflow

### Morning Setup

```bash
# Terminal 1: Start services
cd ~/devops-docker-project/infrastructure
docker-compose up -d

# Terminal 2: Start backend
cd ~/devops-docker-project/backend
source venv/bin/activate
python -m uvicorn app.main:app --reload

# Terminal 3: Start frontend
cd ~/devops-docker-project/frontend
npm run dev

# Open VS Code to the project
code ~/devops-docker-project
```

### During Development

1. **Make changes** in your editor
2. **Auto-reload** handles backend (FastAPI) and frontend (Vite)
3. **Test via browser** at `http://localhost:5173` or API at `http://localhost:8000/docs`
4. **Commit frequently** with clear messages
5. **Push to your branch** when ready

### Before Ending Day

```bash
# Commit all changes
git add .
git commit -m "feat: daily progress"
git push origin your-branch-name

# Stop services
cd infrastructure
docker-compose down

# Backup .env (keep locally, never commit)
```

---

## Troubleshooting

### Backend won't start

```bash
# Check if port 8000 is in use
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process if needed
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Try starting again
python -m uvicorn app.main:app --reload --port 8001
```

### Database connection fails

```bash
# Check if PostgreSQL is running
docker-compose ps

# Start if not running
docker-compose up -d postgres

# Check logs
docker-compose logs postgres

# Reset database (warning: deletes all data)
docker-compose down -v
docker-compose up -d postgres
cd backend
alembic upgrade head
```

### Frontend won't start

```bash
# Clear node modules and reinstall
rm -rf frontend/node_modules frontend/package-lock.json
cd frontend
npm install
npm run dev
```

### API keys not working

```bash
# Verify .env file exists
ls -la .env

# Check specific key is set
grep ANTHROPIC_API_KEY .env

# Restart backend after changing .env
# (Backend needs restart to reload env vars)
```

---

## Your New Headquarters

You now have:

✅ **Full local development** - Backend + Frontend + Database  
✅ **Git integration** - Commit and push directly  
✅ **AWS ready** - Can deploy to production  
✅ **LLM access** - Claude, GPT, DeepSeek, Gemini, etc.  
✅ **Monitoring** - Real-time dashboards and metrics  
✅ **Billing system** - Cost tracking and invoice generation  
✅ **Optimization engine** - AI-powered recommendations  

## Next Steps

1. **Make your first feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Build your next capability** following the execution directive in this repo

3. **Deploy to AWS** when ready:
   ```bash
   cd infrastructure
   terraform apply
   docker-compose push
   ```

4. **Monitor in production:**
   Visit `http://your-aws-endpoint/api/v1/monitoring/dashboard/overview`

---

## Support

If you hit issues:

1. Check `.vscode/VSCODE_QUICKSTART.md` for detailed environment setup
2. Read `JARVIS_SELF_KNOWLEDGE.md` for system architecture
3. Check `SYSTEM_ARCHITECTURE_COMPLETE.md` for detailed specs
4. Review task definitions in `.vscode/tasks.json`

You own this codebase now. Make it yours.
