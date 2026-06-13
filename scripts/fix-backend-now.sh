#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# JARVIS — Backend Emergency Fix
# Aliyar Solutions | Run from AWS CloudShell (ap-south-2)
#
# Diagnoses EC2 state, clones code if missing, builds + starts backend.
# Waits up to 10 minutes for Docker build to complete, then verifies health.
#
# Usage:
#   bash <(curl -s https://raw.githubusercontent.com/syedabrarfff-stack/\
# devops-docker-project/claude/jarvis-cans-api-integration-ZThTD/scripts/fix-backend-now.sh)
# ═══════════════════════════════════════════════════════════════════════════════

set -uo pipefail

REGION="ap-south-2"
BRANCH="claude/jarvis-cans-api-integration-ZThTD"
REPO="https://github.com/syedabrarfff-stack/devops-docker-project.git"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; WHITE='\033[1;37m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
fail() { echo -e "${RED}  ❌ $1${NC}"; }
info() { echo -e "${CYAN}  →  $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠  $1${NC}"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   JARVIS — Backend Emergency Fix                 ║${NC}"
echo -e "${CYAN}║   Aliyar Solutions | ap-south-2                  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── Find EC2 ──────────────────────────────────────────────────────────────────
INSTANCE_ID=$(aws ec2 describe-instances \
  --region "$REGION" \
  --filters "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[].InstanceId" \
  --output text 2>/dev/null | tr '\t' '\n' | head -1)

[ -z "$INSTANCE_ID" ] && { fail "No running EC2 in $REGION"; exit 1; }
ok "EC2: $INSTANCE_ID"

# ── Verify SSM ────────────────────────────────────────────────────────────────
SSM_STATUS=$(aws ssm describe-instance-information \
  --region "$REGION" \
  --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
  --query "InstanceInformationList[0].PingStatus" \
  --output text 2>/dev/null || echo "Unknown")
[ "$SSM_STATUS" != "Online" ] && { fail "SSM agent not online ($SSM_STATUS)"; exit 1; }
ok "SSM: Online"

ssm_wait() {
    local CMD_ID="$1" MAX_WAIT="${2:-600}"
    local ELAPSED=0
    while [ "$ELAPSED" -lt "$MAX_WAIT" ]; do
        local OUT STATUS
        OUT=$(aws ssm get-command-invocation \
            --region "$REGION" --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" \
            --output json 2>/dev/null || echo '{"Status":"Pending"}')
        STATUS=$(echo "$OUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('Status','Pending'))" 2>/dev/null || echo "Pending")
        if [ "$STATUS" = "Success" ] || [ "$STATUS" = "Failed" ]; then
            echo "$OUT"
            return 0
        fi
        sleep 15; ELAPSED=$((ELAPSED+15))
        echo -ne "${CYAN}  → ${ELAPSED}s elapsed (${STATUS})...\r${NC}"
    done
    echo "$OUT"
}

# ── Step 1: Diagnose ──────────────────────────────────────────────────────────
echo ""
info "Step 1 — Diagnosing current EC2 state..."

DIAG_ID=$(aws ssm send-command \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters '{"commands":[
    "echo === CONTAINERS ===",
    "docker ps -a --format \"table {{.Names}}\\t{{.Status}}\\t{{.Ports}}\" 2>/dev/null || echo docker_not_found",
    "echo === CODE ===",
    "ls /opt/jarvis/infrastructure/docker-compose.yml 2>/dev/null && echo CODE_AT_OPT_JARVIS || (ls /home/ubuntu/devops-docker-project/infrastructure/docker-compose.yml 2>/dev/null && echo CODE_AT_HOME || echo CODE_NOT_FOUND)",
    "echo === BACKEND LOGS (last 20) ===",
    "docker logs jarvis_backend --tail=20 2>/dev/null || echo NO_BACKEND_CONTAINER",
    "echo === DISK ===",
    "df -h / | tail -1"
  ]}' \
  --query "Command.CommandId" \
  --output text 2>/dev/null)

DIAG_OUT=$(ssm_wait "$DIAG_ID" 30)
STDOUT=$(echo "$DIAG_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('StandardOutputContent',''))" 2>/dev/null || echo "")
echo ""
echo -e "${WHITE}--- Diagnostic Output ---${NC}"
echo "$STDOUT"
echo ""

# Determine action
BACKEND_UP=$(echo "$STDOUT" | grep -c "jarvis_backend.*Up" || true)
CODE_AT_OPT=$(echo "$STDOUT" | grep -c "CODE_AT_OPT_JARVIS" || true)
CODE_AT_HOME=$(echo "$STDOUT" | grep -c "CODE_AT_HOME" || true)
CODE_FOUND=$((CODE_AT_OPT + CODE_AT_HOME))

if [ "$BACKEND_UP" -gt 0 ]; then
    warn "Backend is running but returning 502 — will force restart"
elif [ "$CODE_FOUND" -gt 0 ]; then
    info "Code is on EC2 but backend not running — will start it"
else
    info "Code not found on EC2 — will clone repo and build"
fi

# ── Step 2: Fix ───────────────────────────────────────────────────────────────
echo ""
info "Step 2 — Deploying backend (8-10 min for Docker build)..."

# Use python3 to build the JSON to avoid bash escaping issues with $DEPLOY_DIR
FIX_PARAMS=$(python3 -c "
import json
repo = '${REPO}'
branch = '${BRANCH}'
cmds = [
    'set -e',
    'echo === SETUP ===',
    'DEPLOY_DIR=/opt/jarvis',
    '[ -d /home/ubuntu/devops-docker-project/infrastructure ] && [ ! -d /opt/jarvis/infrastructure ] && DEPLOY_DIR=/home/ubuntu/devops-docker-project || true',
    'if [ ! -f \$DEPLOY_DIR/infrastructure/docker-compose.yml ]; then',
    '  echo Cloning repo...',
    '  apt-get install -y git curl 2>/dev/null || true',
    '  git clone ' + repo + ' /opt/jarvis 2>&1 | tail -5',
    '  DEPLOY_DIR=/opt/jarvis',
    'fi',
    'cd \$DEPLOY_DIR',
    'git fetch origin ' + branch + ' 2>&1',
    'git checkout ' + branch + ' 2>&1',
    'git pull origin ' + branch + ' 2>&1',
    'echo Latest: \$(git log --oneline -1)',
    'which docker-compose 2>/dev/null || (curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose && echo docker-compose installed)',
    '[ -f \$DEPLOY_DIR/.env ] || cp \$DEPLOY_DIR/.env.example \$DEPLOY_DIR/.env',
    'echo === ENSURE JARVIS-DATA DIR ===',
    'mkdir -p \$DEPLOY_DIR/jarvis-data/daily \$DEPLOY_DIR/jarvis-data/outputs \$DEPLOY_DIR/jarvis-data/intelligence',
    'echo === START DEPS (postgres + redis) ===',
    'cd \$DEPLOY_DIR/infrastructure',
    'docker-compose up -d postgres redis 2>&1 | tail -5',
    'echo Waiting 20s for postgres/redis to be healthy...',
    'sleep 20',
    'echo === BUILD + START BACKEND ===',
    'docker-compose up -d --no-deps --build backend 2>&1',
    'echo Backend build triggered. Waiting 35s for startup...',
    'sleep 35',
    'echo === BACKEND STATUS ===',
    'docker-compose ps backend 2>&1',
    'echo === LAST 30 LOG LINES ===',
    'docker logs jarvis_backend --tail=30 2>&1 || true',
    'echo === HEALTH CHECK ===',
    'curl -sf http://localhost:8000/health && echo BACKEND_HEALTHY || echo BACKEND_DOWN',
    'echo DONE'
]
print(json.dumps({'commands': cmds}))
")

FIX_ID=$(aws ssm send-command \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --timeout-seconds 720 \
  --parameters "$FIX_PARAMS" \
  --query "Command.CommandId" \
  --output text 2>/dev/null)

ok "Fix command sent (ID: $FIX_ID)"
info "Waiting up to 10 minutes for Docker build..."

FIX_OUT=$(ssm_wait "$FIX_ID" 600)
FIX_STATUS=$(echo "$FIX_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('Status','unknown'))" 2>/dev/null || echo "unknown")
FIX_STDOUT=$(echo "$FIX_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('StandardOutputContent',''))" 2>/dev/null || echo "")
FIX_STDERR=$(echo "$FIX_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('StandardErrorContent',''))" 2>/dev/null || echo "")

echo ""
echo -e "${WHITE}--- Deploy Output (SSM Status: $FIX_STATUS) ---${NC}"
echo "$FIX_STDOUT" | tail -40
[ -n "$FIX_STDERR" ] && echo -e "${YELLOW}STDERR: $FIX_STDERR${NC}"

# ── Step 3: Verify + migrate ──────────────────────────────────────────────────
echo ""
HEALTH=$(curl -so /dev/null -w "%{http_code}" --connect-timeout 10 https://aliyarsolutions.com/health 2>/dev/null || echo "000")

if [ "$HEALTH" = "200" ]; then
    ok "BACKEND IS LIVE — HTTP $HEALTH"
    info "Running Alembic migrations + pipeline triggers..."

    MIG_ID=$(aws ssm send-command \
      --region "$REGION" --instance-ids "$INSTANCE_ID" \
      --document-name "AWS-RunShellScript" \
      --timeout-seconds 120 \
      --parameters '{"commands":[
        "DEPLOY_DIR=$( [ -d /opt/jarvis ] && echo /opt/jarvis || echo /home/ubuntu/devops-docker-project)",
        "cd $DEPLOY_DIR/infrastructure",
        "echo Running Alembic migrations...",
        "docker-compose exec -T backend alembic upgrade head 2>&1 || docker exec jarvis_backend alembic upgrade head 2>&1 || echo MIGRATION_ATTEMPTED",
        "sleep 3",
        "echo Triggering lead discovery...",
        "curl -sf -X POST http://localhost:8000/api/v1/leads/bulk-discover?limit=200 2>/dev/null && echo BULK_DISCOVER_OK || echo BULK_DISCOVER_FAIL",
        "echo Triggering HubSpot sync...",
        "curl -sf -X POST http://localhost:8000/api/v1/crm/hubspot-sync 2>/dev/null && echo HUBSPOT_SYNC_OK || echo HUBSPOT_SYNC_FAIL",
        "echo DONE"
      ]}' \
      --query "Command.CommandId" --output text 2>/dev/null)

    sleep 30
    MIG_OUT=$(aws ssm get-command-invocation \
      --region "$REGION" --command-id "$MIG_ID" --instance-id "$INSTANCE_ID" \
      --query "StandardOutputContent" --output text 2>/dev/null || echo "")
    echo "$MIG_OUT"

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  JARVIS OPERATIONAL STATUS                       ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  Backend:    ✅ LIVE (HTTP 200)                  ║${NC}"
    EVOL=$(curl -so /dev/null -w "%{http_code}" --connect-timeout 5 https://aliyarsolutions.com/evolution/ 2>/dev/null || echo "000")
    GRF=$(curl -so /dev/null -w "%{http_code}" --connect-timeout 5 https://aliyarsolutions.com/grafana/ 2>/dev/null || echo "000")
    WA=$(curl -sf --connect-timeout 5 "https://aliyarsolutions.com/evolution/instance/connectionState/jarvis-main" -H "apikey: jarvis-master-key" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('instance',{}).get('state','unknown'))" 2>/dev/null || echo "unknown")
    echo -e "${GREEN}║  Evolution:  HTTP $EVOL                               ║${NC}"
    echo -e "${GREEN}║  Grafana:    HTTP $GRF                               ║${NC}"
    echo -e "${GREEN}║  WhatsApp:   $WA                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
else
    warn "Backend still at HTTP $HEALTH — it may still be starting up"
    info "Check in 2 minutes: curl https://aliyarsolutions.com/health"
    info "View logs: run this in CloudShell:"
    echo ""
    echo "  aws ssm send-command --region ap-south-2 --instance-ids $INSTANCE_ID \\"
    echo "    --document-name AWS-RunShellScript \\"
    echo "    --parameters 'commands=[\"docker logs jarvis_backend --tail=50\"]' \\"
    echo "    --query Command.CommandId --output text"
fi
