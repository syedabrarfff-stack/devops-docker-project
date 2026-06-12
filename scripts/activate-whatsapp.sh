#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# JARVIS WhatsApp Activation — Evolution API v2.3.7
# Run AFTER nginx fix is deployed on EC2
#
# Usage:  bash scripts/activate-whatsapp.sh
# Or:     EVOLUTION_URL=http://localhost:8080 bash scripts/activate-whatsapp.sh
# ═══════════════════════════════════════════════════════════════════

EVOLUTION_URL="${EVOLUTION_URL:-https://aliyarsolutions.com/evolution}"
EVOLUTION_KEY="${EVOLUTION_API_KEY:-jarvis-master-key}"
INSTANCE="${WHATSAPP_INSTANCE_NAME:-jarvis-main}"
CAPTAIN_PHONE="${CAPTAIN_PHONE:-97334360246}"   # without + prefix

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $1${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; }
info() { echo -e "${CYAN}→  $1${NC}"; }
warn() { echo -e "${YELLOW}⚠  $1${NC}"; }

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  JARVIS WhatsApp Activation                   ${NC}"
echo -e "${CYAN}  Evolution API: $EVOLUTION_URL         ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

# ── Step 1: Evolution API health ─────────────────────────────────
info "Step 1: Testing Evolution API connectivity..."
if curl -sf "$EVOLUTION_URL/" -o /dev/null 2>/dev/null; then
    ok "Evolution API is reachable"
else
    fail "Evolution API NOT reachable at $EVOLUTION_URL"
    echo ""
    echo "  This means the nginx fix has not been deployed yet."
    echo "  Run on EC2:"
    echo "    git pull origin claude/jarvis-cans-api-integration-ZThTD"
    echo "    cd infrastructure && docker compose exec nginx nginx -s reload"
    exit 1
fi

# ── Step 2: Check existing connection state ───────────────────────
info "Step 2: Checking connection state..."
STATE_RESP=$(curl -s "$EVOLUTION_URL/instance/connectionState/$INSTANCE" \
    -H "apikey: $EVOLUTION_KEY" 2>/dev/null)
STATE=$(echo "$STATE_RESP" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('instance',{}).get('state') or d.get('state') or d.get('connectionState') or 'unknown')
" 2>/dev/null || echo "unknown")

echo "   Connection state: $STATE"

if [[ "$STATE" == "open" ]]; then
    ok "WhatsApp is already connected!"
    echo ""
    info "Sending test message to Captain..."
    TEST_RESULT=$(curl -s -X POST "$EVOLUTION_URL/message/sendText/$INSTANCE" \
        -H "apikey: $EVOLUTION_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"number\": \"$CAPTAIN_PHONE\",
            \"text\": \"JARVIS: WhatsApp transport is LIVE. Evolution API connected and operational. First live message confirmed.\"
        }" 2>/dev/null)
    MSG_ID=$(echo "$TEST_RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('key',{}).get('id','none'))" 2>/dev/null || echo "none")
    if [[ "$MSG_ID" != "none" && -n "$MSG_ID" ]]; then
        ok "TEST MESSAGE SENT! Message ID: $MSG_ID"
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  🎉 WHATSAPP IS LIVE — FIRST MESSAGE SENT     ${NC}"
        echo -e "${GREEN}  Check +973 34360246 for the test message      ${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    else
        warn "Message delivery unclear: $TEST_RESULT"
    fi
    exit 0
fi

# ── Step 3: Instance exists? ──────────────────────────────────────
info "Step 3: Checking instance '$INSTANCE'..."
INSTANCES=$(curl -s "$EVOLUTION_URL/instance/fetchInstances" \
    -H "apikey: $EVOLUTION_KEY" 2>/dev/null || echo "[]")

if echo "$INSTANCES" | python3 -c "
import json,sys
instances=json.load(sys.stdin)
if isinstance(instances, list):
    names=[i.get('instance',{}).get('instanceName') or i.get('instanceName','') for i in instances]
    print('found' if '$INSTANCE' in names else 'missing')
elif isinstance(instances, dict):
    # single instance response
    name=instances.get('instance',{}).get('instanceName') or instances.get('instanceName','')
    print('found' if name=='$INSTANCE' else 'missing')
else:
    print('missing')
" 2>/dev/null | grep -q "found"; then
    ok "Instance '$INSTANCE' exists"
else
    warn "Instance '$INSTANCE' not found — creating..."
    CREATE_RESULT=$(curl -s -X POST "$EVOLUTION_URL/instance/create" \
        -H "apikey: $EVOLUTION_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"instanceName\": \"$INSTANCE\",
            \"qrcode\": true,
            \"integration\": \"WHATSAPP-BAILEYS\"
        }" 2>/dev/null)
    echo "   Create result: $(echo "$CREATE_RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('instance',{}).get('instanceName') or d.get('instanceName','failed'))" 2>/dev/null)"
    sleep 3
fi

# ── Step 4: Request pairing code ─────────────────────────────────
echo ""
info "Step 4: Requesting pairing code for +$CAPTAIN_PHONE..."
echo "   (This sends a code to the Bahrain WhatsApp number)"
echo ""

PAIR_RESULT=$(curl -s -X POST "$EVOLUTION_URL/instance/pairingCode/$INSTANCE" \
    -H "apikey: $EVOLUTION_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"phoneNumber\": \"$CAPTAIN_PHONE\"}" 2>/dev/null)

PAIRING_CODE=$(echo "$PAIR_RESULT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('code') or d.get('pairingCode') or '')
" 2>/dev/null)

if [[ -n "$PAIRING_CODE" ]]; then
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  PAIRING CODE READY                           ${NC}"
    echo ""
    echo -e "${GREEN}  CODE:  ${CYAN}$PAIRING_CODE${NC}"
    echo ""
    echo -e "${GREEN}  On Bahrain WhatsApp (+973 34360246):         ${NC}"
    echo -e "${GREEN}  Settings → Linked Devices → Link a Device    ${NC}"
    echo -e "${GREEN}  → Link with phone number → Enter code above  ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    echo ""
    info "Waiting 60s for pairing to complete..."
    sleep 60
    FINAL_STATE=$(curl -s "$EVOLUTION_URL/instance/connectionState/$INSTANCE" \
        -H "apikey: $EVOLUTION_KEY" 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('instance',{}).get('state') or d.get('state') or 'unknown')
" 2>/dev/null || echo "unknown")
    echo ""
    if [[ "$FINAL_STATE" == "open" ]]; then
        ok "CONNECTED! WhatsApp state: $FINAL_STATE"
        bash "$0"  # re-run to send test message
    else
        warn "State after pairing: $FINAL_STATE (may need more time)"
        echo "   Re-run this script to check again and send test message."
    fi
    exit 0
fi

# ── Fallback: QR code ──────────────────────────────────────────────
info "Pairing code not available — fetching QR code..."
QR_RESULT=$(curl -s "$EVOLUTION_URL/instance/connect/$INSTANCE" \
    -H "apikey: $EVOLUTION_KEY" 2>/dev/null)

QR_URL="$EVOLUTION_URL/instance/connect/$INSTANCE"
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  QR CODE — SCAN FROM BAHRAIN PHONE            ${NC}"
echo ""
echo -e "${YELLOW}  Browser URL:${NC}"
echo -e "${CYAN}  $QR_URL${NC}"
echo ""
echo -e "${YELLOW}  With header: apikey: $EVOLUTION_KEY           ${NC}"
echo ""
echo -e "${YELLOW}  OR open this URL in the Evolution dashboard:  ${NC}"
echo -e "${CYAN}  https://aliyarsolutions.com/evolution          ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "Raw QR response:"
echo "$QR_RESULT" | python3 -m json.tool 2>/dev/null | head -20
