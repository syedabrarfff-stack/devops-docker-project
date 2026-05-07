#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  JARVIS — Pre-Deployment Readiness Check
#  Run before every production deployment.
#  Usage: bash scripts/pre-deploy-check.sh
# ════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

pass() { echo -e "${GREEN}✓${NC} $1"; ((PASS++)); }
fail() { echo -e "${RED}✗${NC} $1"; ((FAIL++)); }
warn() { echo -e "${YELLOW}⚠${NC} $1"; ((WARN++)); }
section() { echo -e "\n${BLUE}── $1 ──────────────────────────────────${NC}"; }

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}  JARVIS Pre-Deployment Check            ${NC}"
echo -e "${BLUE}  Aliyar Solutions — $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

# ── 1. Environment ─────────────────────────────────────────────
section "Environment"
[ -f ".env" ] && pass ".env file exists" || fail ".env file missing — run: cp config/.env.development .env"
[ "${DEBUG:-true}" = "false" ] && pass "DEBUG=false" || warn "DEBUG is not false — set DEBUG=false for production"
[ -n "${SECRET_KEY:-}" ] && [ "${SECRET_KEY}" != "change-this-in-production" ] && pass "SECRET_KEY is set" || fail "SECRET_KEY not configured"
[ -n "${DATABASE_URL:-}" ] && [[ "${DATABASE_URL}" != *"jarvis_pass"* ]] && pass "DATABASE_URL configured" || warn "DATABASE_URL may use default credentials"

# ── 2. Required API Keys ────────────────────────────────────────
section "AI Provider Credentials"
[ -n "${ANTHROPIC_API_KEY:-}" ] && pass "ANTHROPIC_API_KEY" || warn "ANTHROPIC_API_KEY missing — Claude unavailable"
[ -n "${OPENAI_API_KEY:-}" ] && pass "OPENAI_API_KEY" || warn "OPENAI_API_KEY missing — GPT-4o unavailable"
[ -n "${GROQ_API_KEY:-}" ] && pass "GROQ_API_KEY" || warn "GROQ_API_KEY missing — realtime ops degraded"

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
    fail "No primary AI provider configured — at least one required"
fi

# ── 3. Notifications ────────────────────────────────────────────
section "Notification Channels"
[ -n "${SLACK_WEBHOOK_URL:-}" ] && pass "SLACK_WEBHOOK_URL" || warn "SLACK_WEBHOOK_URL missing — no emergency alerts"
[ -n "${TELEGRAM_BOT_TOKEN:-}" ] && pass "TELEGRAM_BOT_TOKEN" || warn "TELEGRAM_BOT_TOKEN missing — no mobile alerts"

# ── 4. Docker ───────────────────────────────────────────────────
section "Docker"
command -v docker &>/dev/null && pass "Docker installed" || fail "Docker not found"
command -v docker-compose &>/dev/null || command -v docker compose &>/dev/null && pass "Docker Compose available" || fail "Docker Compose not found"

# ── 5. Services Reachable ───────────────────────────────────────
section "Services"
if curl -sf http://localhost:8000/health &>/dev/null; then
    pass "Backend /health responding"
else
    warn "Backend not responding (expected if not yet started)"
fi

# ── 6. Git State ────────────────────────────────────────────────
section "Git"
DIRTY=$(git status --porcelain 2>/dev/null | wc -l)
[ "$DIRTY" -eq 0 ] && pass "Working tree clean" || warn "$DIRTY uncommitted file(s)"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
echo -e "   Branch: ${BLUE}${BRANCH}${NC}"

# ── 7. Secret Scanning ─────────────────────────────────────────
section "Secret Scanning"
if command -v gitleaks &>/dev/null; then
    if gitleaks detect --no-git --source . -q 2>/dev/null; then
        pass "No secrets detected (gitleaks)"
    else
        fail "Potential secrets detected — run: gitleaks detect --source . for details"
    fi
else
    warn "gitleaks not installed — skipping secret scan (install: https://github.com/gitleaks/gitleaks)"
fi

# Check for .env in git
if git ls-files --error-unmatch .env &>/dev/null 2>&1; then
    fail ".env is tracked by git — add to .gitignore immediately"
else
    pass ".env is gitignored"
fi

# ── Summary ────────────────────────────────────────────────────
echo -e "\n${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}PASS: ${PASS}${NC}  ${RED}FAIL: ${FAIL}${NC}  ${YELLOW}WARN: ${WARN}${NC}"

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}✗ Deployment blocked — fix FAIL items above${NC}"
    exit 1
elif [ "$WARN" -gt 2 ]; then
    echo -e "${YELLOW}⚠ Deployment allowed with warnings — review WARN items${NC}"
    exit 0
else
    echo -e "${GREEN}✓ System is production-ready${NC}"
    exit 0
fi
