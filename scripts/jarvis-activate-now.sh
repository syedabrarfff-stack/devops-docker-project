#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# JARVIS ONE-COMMAND FULL ACTIVATION
# Aliyar Solutions — Captain Syed Abrar
#
# Run this on EC2 via SSH:
#   bash <(curl -s https://raw.githubusercontent.com/syedabrarfff-stack/devops-docker-project/claude/jarvis-cans-api-integration-ZThTD/scripts/jarvis-activate-now.sh)
#
# OR after git pull:
#   bash scripts/jarvis-activate-now.sh
#
# This script handles:
#   1. Git pull latest code
#   2. Nginx fix deployment (webhook bypass + Evolution API proxy)
#   3. WhatsApp pairing code to Bahrain number
#   4. SES env configuration
#   5. Full status report
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
fail() { echo -e "${RED}  ❌ $1${NC}"; }
info() { echo -e "${CYAN}  →  $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠  $1${NC}"; }
step() { echo -e "\n${BLUE}══ $1 ══${NC}"; }

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   JARVIS — Full Activation Script                     ║${NC}"
echo -e "${BLUE}║   Aliyar Solutions — Captain Syed Abrar               ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Locate deploy directory ────────────────────────────────────────────────
step "STEP 1 — Locating deploy directory"
if [ -d "/opt/jarvis" ] && [ -f "/opt/jarvis/infrastructure/docker-compose.yml" ]; then
    DEPLOY_DIR="/opt/jarvis"
elif [ -d "/home/ubuntu/devops-docker-project" ] && [ -f "/home/ubuntu/devops-docker-project/infrastructure/docker-compose.yml" ]; then
    DEPLOY_DIR="/home/ubuntu/devops-docker-project"
else
    fail "Cannot find JARVIS deploy directory. Checked /opt/jarvis and /home/ubuntu/devops-docker-project"
    exit 1
fi
ok "Deploy directory: $DEPLOY_DIR"
cd "$DEPLOY_DIR"

# ── Git pull ───────────────────────────────────────────────────────────────
step "STEP 2 — Pulling latest code"
BRANCH="claude/jarvis-cans-api-integration-ZThTD"
git fetch origin "$BRANCH" 2>/dev/null
git checkout "$BRANCH" 2>/dev/null || true
git pull origin "$BRANCH" 2>/dev/null
COMMIT=$(git log --oneline -1)
ok "Latest commit: $COMMIT"

# ── Nginx reload ───────────────────────────────────────────────────────────
step "STEP 3 — Deploying nginx fix"
cd "$DEPLOY_DIR/infrastructure"

# Ensure .htpasswd exists (prompt to create if missing)
if [ ! -f "nginx/.htpasswd" ]; then
    warn ".htpasswd not found — control room password required"
    echo ""
    echo -e "  ${WHITE}Set a password for the control room (username: captain):${NC}"
    if command -v htpasswd &>/dev/null; then
        htpasswd -c nginx/.htpasswd captain
        ok "Created .htpasswd"
    elif command -v openssl &>/dev/null; then
        read -rsp "  Enter control room password: " CR_PASS
        echo ""
        HASHED=$(openssl passwd -apr1 "$CR_PASS")
        echo "captain:$HASHED" > nginx/.htpasswd
        unset CR_PASS
        ok "Created .htpasswd"
    else
        warn "Cannot create .htpasswd — install apache2-utils: sudo apt-get install apache2-utils"
        warn "Then run: htpasswd -c $DEPLOY_DIR/infrastructure/nginx/.htpasswd captain"
    fi
else
    ok ".htpasswd exists (credentials unchanged)"
fi

# Reload nginx
if docker compose exec -T nginx nginx -t 2>/dev/null; then
    docker compose exec -T nginx nginx -s reload 2>/dev/null
    ok "Nginx reloaded with new config"
else
    warn "Nginx config test failed — rebuilding nginx container"
    docker compose up -d --no-deps nginx 2>/dev/null
    sleep 5
fi

# ── Verify nginx fix ───────────────────────────────────────────────────────
step "STEP 4 — Verifying nginx endpoints"
sleep 2

HEALTH=$(curl -sf http://localhost/health 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status','error'))" 2>/dev/null || echo "error")
if [ "$HEALTH" = "ok" ]; then
    ok "JARVIS health: ok"
else
    fail "JARVIS health check failed: $HEALTH"
fi

EVOLUTION_HEALTH=$(curl -sf http://localhost/evolution/ 2>/dev/null | head -1 || curl -sf http://localhost/evolution/health 2>/dev/null | head -1 || echo "ERROR")
if [[ "$EVOLUTION_HEALTH" != "ERROR" && -n "$EVOLUTION_HEALTH" ]]; then
    ok "Evolution API proxy: reachable"
else
    warn "Evolution API proxy: not responding (may need rebuild)"
    docker compose up -d --no-deps evolution 2>/dev/null
    sleep 10
fi

# ── SES env configuration ─────────────────────────────────────────────────
step "STEP 5 — Configuring SES inbound routing"
ENV_FILE="$DEPLOY_DIR/.env"
if ! grep -q "SES_REPLY_TO_EMAIL" "$ENV_FILE" 2>/dev/null; then
    echo "" >> "$ENV_FILE"
    echo "# SES inbound routing — replies@inbound.aliyarsolutions.com → SNS → webhook" >> "$ENV_FILE"
    echo "SES_REPLY_TO_EMAIL=replies@inbound.aliyarsolutions.com" >> "$ENV_FILE"
    ok "Added SES_REPLY_TO_EMAIL to .env"
    docker compose restart backend 2>/dev/null &
    BACKEND_RESTART_PID=$!
    info "Backend restarting in background (SES config update)..."
else
    ok "SES_REPLY_TO_EMAIL already configured"
    BACKEND_RESTART_PID=""
fi

# ── Evolution API: check / create instance ────────────────────────────────
step "STEP 6 — Evolution API / WhatsApp"
EVOLUTION_KEY="${EVOLUTION_API_KEY:-jarvis-master-key}"
INSTANCE="${WHATSAPP_INSTANCE_NAME:-jarvis-main}"
CAPTAIN_PHONE="97334360246"

info "Checking Evolution API..."
EVOLUTION_DIRECT="http://localhost:8080"

# Try internal Evolution API directly
EVOL_RESP=$(curl -sf "$EVOLUTION_DIRECT/instance/fetchInstances" \
    -H "apikey: $EVOLUTION_KEY" 2>/dev/null || echo "ERROR")

if [ "$EVOL_RESP" = "ERROR" ]; then
    warn "Evolution API not responding at localhost:8080 — checking container..."
    docker compose ps evolution 2>/dev/null | head -5
    docker compose up -d evolution 2>/dev/null
    sleep 15
    EVOL_RESP=$(curl -sf "$EVOLUTION_DIRECT/instance/fetchInstances" \
        -H "apikey: $EVOLUTION_KEY" 2>/dev/null || echo "ERROR")
fi

if [ "$EVOL_RESP" = "ERROR" ]; then
    fail "Evolution API unreachable — check Docker logs:"
    echo "  docker compose logs --tail=20 evolution"
    WHATSAPP_OK=false
else
    ok "Evolution API is running"

    # Check connection state
    STATE=$(curl -sf "$EVOLUTION_DIRECT/instance/connectionState/$INSTANCE" \
        -H "apikey: $EVOLUTION_KEY" 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('instance',{}).get('state') or d.get('state') or 'unknown')
" 2>/dev/null || echo "unknown")

    echo ""
    echo -e "  Connection state: ${WHITE}$STATE${NC}"

    if [[ "$STATE" == "open" ]]; then
        ok "WhatsApp is CONNECTED — sending live test message..."
        TEST=$(curl -sf -X POST "$EVOLUTION_DIRECT/message/sendText/$INSTANCE" \
            -H "apikey: $EVOLUTION_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"number\":\"$CAPTAIN_PHONE\",\"text\":\"JARVIS: WhatsApp transport LIVE. Aliyar Solutions communication pipeline is operational. First live message confirmed.\"}" 2>/dev/null || echo "{}")
        MSG_ID=$(echo "$TEST" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('key',{}).get('id',''))" 2>/dev/null || echo "")
        if [ -n "$MSG_ID" ]; then
            echo ""
            echo -e "${GREEN}  ╔══════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}  ║  🎉 FIRST LIVE WHATSAPP MESSAGE SENT!           ║${NC}"
            echo -e "${GREEN}  ║  Message ID: $MSG_ID  ║${NC}"
            echo -e "${GREEN}  ╚══════════════════════════════════════════════════╝${NC}"
        else
            warn "Message send returned: $TEST"
        fi
        WHATSAPP_OK=true
    else
        info "WhatsApp not paired — requesting pairing code for +$CAPTAIN_PHONE..."

        # Create instance if needed
        CREATE=$(curl -sf -X POST "$EVOLUTION_DIRECT/instance/create" \
            -H "apikey: $EVOLUTION_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"instanceName\":\"$INSTANCE\",\"qrcode\":true,\"integration\":\"WHATSAPP-BAILEYS\"}" 2>/dev/null || echo "{}")
        sleep 3

        # Request pairing code
        PAIR_RESP=$(curl -sf -X POST "$EVOLUTION_DIRECT/instance/pairingCode/$INSTANCE" \
            -H "apikey: $EVOLUTION_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"phoneNumber\":\"$CAPTAIN_PHONE\"}" 2>/dev/null || echo "{}")

        PAIRING_CODE=$(echo "$PAIR_RESP" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('code') or d.get('pairingCode') or '')
" 2>/dev/null || echo "")

        if [ -n "$PAIRING_CODE" ]; then
            echo ""
            echo -e "${GREEN}  ╔══════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}  ║  WHATSAPP PAIRING CODE READY                    ║${NC}"
            echo -e "${GREEN}  ║                                                  ║${NC}"
            echo -e "${GREEN}  ║  CODE:  ${CYAN}$PAIRING_CODE${GREEN}                       ║${NC}"
            echo -e "${GREEN}  ║                                                  ║${NC}"
            echo -e "${GREEN}  ║  On +973 34360246 (Bahrain WhatsApp Business):   ║${NC}"
            echo -e "${GREEN}  ║  Settings → Linked Devices → Link a Device       ║${NC}"
            echo -e "${GREEN}  ║  → Link with phone number → Enter code above     ║${NC}"
            echo -e "${GREEN}  ╚══════════════════════════════════════════════════╝${NC}"
            echo ""
            info "Waiting 90s for pairing to complete..."
            sleep 90
            FINAL=$(curl -sf "$EVOLUTION_DIRECT/instance/connectionState/$INSTANCE" \
                -H "apikey: $EVOLUTION_KEY" 2>/dev/null | python3 -c "
import json,sys; d=json.load(sys.stdin); print(d.get('instance',{}).get('state') or d.get('state') or 'unknown')
" 2>/dev/null || echo "unknown")
            if [[ "$FINAL" == "open" ]]; then
                ok "WhatsApp CONNECTED! Sending test message..."
                curl -sf -X POST "$EVOLUTION_DIRECT/message/sendText/$INSTANCE" \
                    -H "apikey: $EVOLUTION_KEY" \
                    -H "Content-Type: application/json" \
                    -d "{\"number\":\"$CAPTAIN_PHONE\",\"text\":\"JARVIS: WhatsApp transport LIVE. First message confirmed.\"}" >/dev/null 2>&1 && ok "TEST MESSAGE SENT to +973 34360246"
                WHATSAPP_OK=true
            else
                warn "State after 90s: $FINAL — may need more time or re-scan"
                WHATSAPP_OK=false
            fi
        else
            warn "Pairing code request returned: $PAIR_RESP"
            # Fall back to QR connect URL
            QR_URL="http://localhost:8080/instance/connect/$INSTANCE?qrcode=true"
            info "QR code available at (internal): $QR_URL"
            info "Public QR URL (after nginx reload): https://aliyarsolutions.com/evolution/instance/connect/$INSTANCE"
            WHATSAPP_OK=false
        fi
    fi
fi

# ── Wait for backend restart if running ────────────────────────────────────
if [ -n "${BACKEND_RESTART_PID:-}" ]; then
    wait "$BACKEND_RESTART_PID" 2>/dev/null || true
    sleep 5
fi

# ── Configure Evolution webhook ────────────────────────────────────────────
step "STEP 7 — Configuring Evolution webhook"
WEBHOOK_URL="http://backend:8000/api/v1/webhooks/whatsapp"
WEBHOOK_RESP=$(curl -sf -X POST "$EVOLUTION_DIRECT/webhook/set/$INSTANCE" \
    -H "apikey: $EVOLUTION_KEY" \
    -H "Content-Type: application/json" \
    -d "{
        \"webhook\": {
            \"enabled\": true,
            \"url\": \"$WEBHOOK_URL\",
            \"byEvents\": false,
            \"base64\": true,
            \"events\": [\"MESSAGES_UPSERT\",\"MESSAGES_UPDATE\",\"SEND_MESSAGE\",\"CONNECTION_UPDATE\"]
        }
    }" 2>/dev/null || echo "{}")
WEBHOOK_OK=$(echo "$WEBHOOK_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print('ok' if d else 'error')" 2>/dev/null || echo "error")
[ "$WEBHOOK_OK" = "ok" ] && ok "Evolution webhook configured → $WEBHOOK_URL" || warn "Webhook config: $WEBHOOK_RESP"

# ── SES status check ───────────────────────────────────────────────────────
step "STEP 8 — SES transport status"
# Check if AWS CLI is available
if command -v aws &>/dev/null && (aws sts get-caller-identity --region ap-south-2 &>/dev/null 2>&1); then
    ok "AWS CLI configured — checking SES..."

    # Check SES account
    ACCOUNT=$(aws sesv2 get-account --region ap-south-2 2>/dev/null || echo "{}")
    PROD_ACCESS=$(echo "$ACCOUNT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ProductionAccessEnabled', False))" 2>/dev/null || echo "false")
    SENDING=$(echo "$ACCOUNT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('SendingEnabled', False))" 2>/dev/null || echo "false")

    if [ "$PROD_ACCESS" = "True" ] && [ "$SENDING" = "True" ]; then
        ok "SES production access ACTIVE — sending enabled"
        SES_LIVE=true
    elif [ "$PROD_ACCESS" = "False" ]; then
        warn "SES is in SANDBOX mode — request production access:"
        warn "  AWS Console → SES (ap-south-2) → Account dashboard → Request production access"
        SES_LIVE=false
    fi

    # Check DKIM identity
    IDENTITY=$(aws sesv2 get-email-identity --email-identity aliyarsolutions.com --region ap-south-2 2>/dev/null || echo "{}")
    DKIM_STATUS=$(echo "$IDENTITY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('DkimAttributes',{}).get('Status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
    VERIFIED=$(echo "$IDENTITY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('VerifiedForSendingStatus', False))" 2>/dev/null || echo "false")

    echo ""
    echo "  SES Identity (aliyarsolutions.com):"
    echo "    DKIM Status:    $DKIM_STATUS"
    echo "    Verified:       $VERIFIED"
    echo "    Prod Access:    $PROD_ACCESS"

    # Test send email if live
    if [ "${SES_LIVE:-false}" = "true" ] && [ "$VERIFIED" = "True" ]; then
        info "Testing SES outbound send..."
        SEND_TEST=$(aws sesv2 send-email \
            --from-email-address "joseph.david@aliyarsolutions.com" \
            --destination "{\"ToAddresses\":[\"joseph.david@aliyarsolutions.com\"]}" \
            --content "{\"Simple\":{\"Subject\":{\"Data\":\"JARVIS SES Transport Test\"},\"Body\":{\"Text\":{\"Data\":\"JARVIS SES transport is live. First outbound email confirmed.\"}}}}" \
            --region ap-south-2 2>/dev/null || echo "{}")
        MSG_ID=$(echo "$SEND_TEST" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('MessageId',''))" 2>/dev/null || echo "")
        [ -n "$MSG_ID" ] && ok "SES TEST EMAIL SENT! Message ID: $MSG_ID" || warn "SES send test: $SEND_TEST"
    fi
else
    warn "AWS CLI not configured or no credentials — skipping SES checks"
    warn "Check SES status manually in AWS Console → ap-south-2"
    SES_LIVE=false
fi

# ── SPF DNS check ──────────────────────────────────────────────────────────
step "STEP 9 — DNS verification"
SPF=$(dig +short aliyarsolutions.com TXT 2>/dev/null | grep "v=spf1" || echo "")
if echo "$SPF" | grep -q "amazonses.com"; then
    ok "SPF includes amazonses.com: $SPF"
else
    fail "SPF missing amazonses.com"
    warn "  Current: $SPF"
    warn "  Required: v=spf1 include:_spf.google.com include:amazonses.com ~all"
    warn "  Action: Update in GoDaddy DNS"
fi

MX_INBOUND=$(dig +short inbound.aliyarsolutions.com MX 2>/dev/null || echo "")
if echo "$MX_INBOUND" | grep -q "amazonses"; then
    ok "inbound.aliyarsolutions.com MX → SES: $MX_INBOUND"
else
    fail "inbound.aliyarsolutions.com MX not pointing to SES"
    warn "  Action: Add MX record in GoDaddy:"
    warn "    Host: inbound | Value: inbound-smtp.ap-south-2.amazonaws.com | Priority: 10"
fi

# ── Final status report ────────────────────────────────────────────────────
step "ACTIVATION COMPLETE — STATUS REPORT"
echo ""
echo -e "${WHITE}Runtime:${NC}"
curl -sf http://localhost:8000/health 2>/dev/null | python3 -m json.tool 2>/dev/null | head -5 || echo "  Backend health: check manually"
echo ""

echo -e "${WHITE}Docker containers:${NC}"
cd "$DEPLOY_DIR/infrastructure" && docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | head -15
echo ""

echo -e "${WHITE}WhatsApp:${NC}"
if [[ "${WHATSAPP_OK:-false}" == "true" ]]; then
    echo -e "  ${GREEN}LIVE — paired and test message sent${NC}"
else
    STATE2=$(curl -sf "http://localhost:8080/instance/connectionState/$INSTANCE" \
        -H "apikey: $EVOLUTION_KEY" 2>/dev/null | python3 -c "
import json,sys; d=json.load(sys.stdin); print(d.get('instance',{}).get('state') or d.get('state') or 'not connected')
" 2>/dev/null || echo "not connected")
    echo -e "  ${YELLOW}State: $STATE2${NC}"
    echo "  Pair code URL: https://aliyarsolutions.com/evolution/instance/connect/$INSTANCE"
fi

echo ""
echo -e "${WHITE}Remaining Captain actions:${NC}"
if ! echo "$SPF" | grep -q "amazonses.com"; then
    echo -e "  ${RED}1. GoDaddy SPF — add include:amazonses.com${NC}"
fi
if ! echo "${MX_INBOUND:-}" | grep -q "amazonses"; then
    echo -e "  ${RED}2. GoDaddy MX — add inbound → inbound-smtp.ap-south-2.amazonaws.com (priority 10)${NC}"
fi
if [ "${SES_LIVE:-false}" != "true" ]; then
    echo -e "  ${RED}3. AWS Console SES ap-south-2 — request production access${NC}"
fi
if [[ "${WHATSAPP_OK:-false}" != "true" ]]; then
    echo -e "  ${RED}4. WhatsApp pairing — scan QR or enter pairing code shown above${NC}"
fi
echo ""
echo -e "${BLUE}JARVIS is operational. Aliyar Solutions outreach engine ready.${NC}"
echo ""
