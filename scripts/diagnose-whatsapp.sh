#!/bin/bash
# EVOLUTION API WHATSAPP PAIRING DIAGNOSTIC
# Run this to diagnose Evolution API pairing failures

set -e

EVOLUTION_URL="${EVOLUTION_API_URL:-http://localhost:9000}"
EVOLUTION_KEY="${EVOLUTION_API_KEY:-jarvis-master-key}"
INSTANCE="jarvis-main"
TARGET_PHONE="+97334360246"

echo "=== EVOLUTION API WHATSAPP PAIRING DIAGNOSTIC ==="
echo "Evolution URL: $EVOLUTION_URL"
echo "Instance: $INSTANCE"
echo "Target Phone: $TARGET_PHONE"
echo ""

# Test 1: Evolution API reachable?
echo "1. Testing Evolution API connectivity..."
if curl -s -f "$EVOLUTION_URL/health" > /dev/null 2>&1; then
    echo "   ✅ Evolution API is reachable"
else
    echo "   ❌ Evolution API is NOT reachable at $EVOLUTION_URL"
    echo "   Action: Start Evolution API container or check URL"
    exit 1
fi

echo ""
echo "2. Checking authentication..."
INSTANCES=$(curl -s "$EVOLUTION_URL/instance/list" \
    -H "apikey: $EVOLUTION_KEY" 2>/dev/null || echo "AUTH_FAILED")

if [ "$INSTANCES" == "AUTH_FAILED" ]; then
    echo "   ❌ API key authentication failed"
    echo "   Action: Verify EVOLUTION_API_KEY is correct in .env"
    exit 1
else
    echo "   ✅ API key is valid"
fi

echo ""
echo "3. Checking instance status..."
INSTANCE_STATUS=$(curl -s "$EVOLUTION_URL/instance/$INSTANCE" \
    -H "apikey: $EVOLUTION_KEY" 2>/dev/null || echo "{}")

if echo "$INSTANCE_STATUS" | jq '.instance' > /dev/null 2>&1; then
    echo "   ✅ Instance '$INSTANCE' exists"
    echo "   Status: $(echo "$INSTANCE_STATUS" | jq -r '.instance_data.state // .state // "unknown"')"
else
    echo "   ❌ Instance '$INSTANCE' does not exist"
    echo "   Action: Create instance with: POST /instance/create"
    exit 1
fi

echo ""
echo "4. Checking connection state..."
CONNECTION=$(curl -s "$EVOLUTION_URL/instance/connectionState/$INSTANCE" \
    -H "apikey: $EVOLUTION_KEY" 2>/dev/null || echo "{}")

STATE=$(echo "$CONNECTION" | jq -r '.state // .connectionState // "UNKNOWN"')
echo "   Connection State: $STATE"

if [[ "$STATE" == "open" || "$STATE" == "connected" ]]; then
    echo "   ✅ WhatsApp is connected!"
    exit 0
fi

echo ""
echo "5. Checking pairing code availability..."
QR=$(curl -s "$EVOLUTION_URL/instance/connect/$INSTANCE" \
    -H "apikey: $EVOLUTION_KEY" 2>/dev/null || echo "{}")

if echo "$QR" | jq '.qrcode' > /dev/null 2>&1; then
    echo "   ✅ QR code endpoint available"
else
    echo "   ❌ QR code endpoint failed"
fi

echo ""
echo "6. Checking for pairing blockers..."
echo ""
echo "   Common issues and solutions:"
echo ""
echo "   A) 'WhatsApp device restriction - cannot link more devices'"
echo "      → This device is already linked to WhatsApp on another number"
echo "      → Solution: Unlink from other device first, or use different device"
echo ""
echo "   B) 'Invalid pairing code'"
echo "      → Pairing code expired (valid for ~60 seconds)"
echo "      → Solution: Request new code: POST /instance/$INSTANCE/request-code"
echo ""
echo "   C) 'WhatsApp Web not detected'"
echo "      → Evolution API version issue or WhatsApp block"
echo "      → Solution: Upgrade Evolution API to latest version"
echo ""
echo "   D) 'Business account not linked'"
echo "      → Number doesn't have WhatsApp Business account"
echo "      → Solution: Go to WhatsApp Business app on phone, link account"
echo ""

echo ""
echo "=== NEXT STEPS ==="
echo ""
echo "If WhatsApp is NOT connected:"
echo ""
echo "Option 1: Request pairing code (works on most devices)"
echo "  curl -X POST $EVOLUTION_URL/instance/$INSTANCE/request-code \\"
echo "    -H 'apikey: $EVOLUTION_KEY' \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"phoneNumber\": \"$TARGET_PHONE\"}'"
echo ""
echo "Option 2: Get QR code (scan from another device)"
echo "  curl -X GET '$EVOLUTION_URL/instance/connect/$INSTANCE?qrcode=true' \\"
echo "    -H 'apikey: $EVOLUTION_KEY'"
echo ""
echo "Option 3: Check if device is blacklisted by WhatsApp"
echo "  → Try pairing from a different phone/device"
echo "  → Try with WhatsApp Business app instead of regular WhatsApp"
echo ""

echo "=== DIAGNOSTIC COMPLETE ==="
