#!/bin/bash
# WhatsApp pairing code generator — run via SSM
EVOL="http://localhost:8080"
KEY="jarvis-master-key"
PHONE="97334360246"
INST="jarvis-main"

echo "=== STEP 1: DELETE EXISTING ==="
curl -s -X DELETE "$EVOL/instance/delete/$INST" -H "apikey: $KEY" 2>/dev/null
sleep 3

echo ""
echo "=== STEP 2: CREATE INSTANCE ==="
curl -s -X POST "$EVOL/instance/create" \
  -H "apikey: $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"instanceName\":\"$INST\",\"qrcode\":false,\"integration\":\"WHATSAPP-BAILEYS\",\"number\":\"$PHONE\"}" 2>/dev/null
sleep 3

echo ""
echo "=== STEP 3: CONNECT (start Baileys) ==="
curl -s "$EVOL/instance/connect/$INST" -H "apikey: $KEY" 2>/dev/null > /tmp/connect.json
cat /tmp/connect.json

echo ""
echo "=== STEP 4: PAIRING CODE (immediate) ==="
PAIR=$(curl -s -X POST "$EVOL/instance/pairingCode/$INST" \
  -H "apikey: $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"phoneNumber\":\"$PHONE\"}" 2>/dev/null)
echo "RAW: $PAIR"
CODE=$(echo "$PAIR" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('code') or d.get('pairingCode') or 'NOT_FOUND')" 2>/dev/null)
echo ""
echo "=============================="
echo "PAIRING CODE: $CODE"
echo "=============================="

echo ""
echo "=== STEP 5: STATE ==="
curl -s "$EVOL/instance/connectionState/$INST" -H "apikey: $KEY" 2>/dev/null

echo ""
echo "=== STEP 6: QR FALLBACK ==="
QR_STR=$(cat /tmp/connect.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
qr = d.get('qrcode') or {}
code = qr.get('code','') or d.get('qr','') or d.get('code','')
b64 = qr.get('base64','') or d.get('base64','')
print('QR_CODE_STR:', code)
if b64:
    print('QR_URL: https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=' + code.replace(' ','%20') if code else 'no_code')
" 2>/dev/null)
echo "$QR_STR"

echo ""
echo "=== STEP 7: EVOLUTION LOGS ==="
docker logs evolution-api --tail 15 2>&1 || docker logs evolution --tail 15 2>&1
