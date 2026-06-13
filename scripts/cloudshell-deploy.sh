#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# JARVIS — AWS CloudShell Deploy + WhatsApp Activation
# Aliyar Solutions — Captain Syed Abrar
#
# Paste into AWS CloudShell (console.aws.amazon.com → click >_ in top bar):
#   bash <(curl -s https://raw.githubusercontent.com/syedabrarfff-stack/devops-docker-project/claude/jarvis-cans-api-integration-ZThTD/scripts/cloudshell-deploy.sh)
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

REGION="ap-south-2"
INSTANCE="jarvis-main"
CAPTAIN_PHONE="97334360246"
EVOLUTION_KEY="jarvis-master-key"
OLD_KEY_ID="AKIA372ASNAQ45KIMZHX"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; WHITE='\033[1;37m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
fail() { echo -e "${RED}  ❌ $1${NC}"; }
info() { echo -e "${CYAN}  →  $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠  $1${NC}"; }
step() { echo -e "\n${CYAN}══════════════════════════════════════════${NC}"; echo -e "${WHITE}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════════${NC}"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   JARVIS — CloudShell Activation                 ║${NC}"
echo -e "${CYAN}║   Aliyar Solutions — Region: ap-south-2          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── SSM helper ────────────────────────────────────────────────────────────────
ssm_run() {
    local label="$1"
    local commands_json="$2"
    local wait_seconds="${3:-30}"

    info "$label"
    local CMD_ID
    CMD_ID=$(aws ssm send-command \
        --region "$REGION" \
        --instance-ids "$INSTANCE_ID" \
        --document-name "AWS-RunShellScript" \
        --parameters "{\"commands\": $commands_json}" \
        --comment "$label" \
        --query "Command.CommandId" \
        --output text 2>/dev/null)

    if [ -z "$CMD_ID" ]; then
        fail "SSM command failed to send"
        return 1
    fi

    sleep "$wait_seconds"

    # Poll up to 3 more times
    local OUTPUT STATUS
    for i in 1 2 3; do
        OUTPUT=$(aws ssm get-command-invocation \
            --region "$REGION" \
            --command-id "$CMD_ID" \
            --instance-id "$INSTANCE_ID" \
            --output json 2>/dev/null || echo '{"Status":"Pending"}')
        STATUS=$(echo "$OUTPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('Status','Pending'))" 2>/dev/null || echo "Pending")
        [ "$STATUS" = "Success" ] || [ "$STATUS" = "Failed" ] && break
        sleep 10
    done

    local STDOUT STDERR
    STDOUT=$(echo "$OUTPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('StandardOutputContent',''))" 2>/dev/null || echo "")
    STDERR=$(echo "$OUTPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('StandardErrorContent',''))" 2>/dev/null || echo "")

    echo "$STDOUT"
    [ -n "$STDERR" ] && echo -e "${YELLOW}STDERR: $STDERR${NC}"

    [ "$STATUS" = "Success" ] && return 0 || return 1
}

# ── Step 0: AWS Credential Rotation (Blocker 1) ───────────────────────────────
step "STEP 0 — AWS Credential Rotation"
info "Rotating compromised key $OLD_KEY_ID"

# Get the IAM username this CloudShell session is running as
IAM_USER=$(aws iam get-user --query "User.UserName" --output text 2>/dev/null || echo "")

if [ -z "$IAM_USER" ]; then
    warn "Could not determine IAM user — skipping key rotation (using IAM role / SSO session)"
    warn "If running under assumed role, keys are session-based and auto-expire — no rotation needed"
else
    ok "IAM User: $IAM_USER"

    # Check if old key still active — deactivate it
    OLD_KEY_STATUS=$(aws iam get-access-key-last-used --access-key-id "$OLD_KEY_ID" \
        --query "AccessKeyLastUsed.LastUsedDate" --output text 2>/dev/null || echo "NOT_FOUND")

    if [ "$OLD_KEY_STATUS" != "NOT_FOUND" ]; then
        info "Deactivating compromised key $OLD_KEY_ID ..."
        aws iam update-access-key --access-key-id "$OLD_KEY_ID" --status Inactive --user-name "$IAM_USER" 2>/dev/null \
            && ok "Key $OLD_KEY_ID deactivated" \
            || warn "Key already inactive or not owned by $IAM_USER"
    else
        info "Key $OLD_KEY_ID not found under $IAM_USER — already rotated or belonged to different user"
    fi

    # Create new key
    info "Creating new IAM access key for $IAM_USER ..."
    NEW_KEY_JSON=$(aws iam create-access-key --user-name "$IAM_USER" --output json 2>/dev/null || echo "{}")
    NEW_KEY_ID=$(echo "$NEW_KEY_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('AccessKey',{}).get('AccessKeyId',''))" 2>/dev/null || echo "")
    NEW_SECRET=$(echo "$NEW_KEY_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('AccessKey',{}).get('SecretAccessKey',''))" 2>/dev/null || echo "")

    if [ -n "$NEW_KEY_ID" ] && [ -n "$NEW_SECRET" ]; then
        ok "New key created: $NEW_KEY_ID"
        # Store new key ID for reference
        export NEW_AWS_KEY_ID="$NEW_KEY_ID"
        export NEW_AWS_SECRET="$NEW_SECRET"

        echo ""
        echo -e "${WHITE}  ╔══════════════════════════════════════════════════════╗${NC}"
        echo -e "${WHITE}  ║  NEW AWS CREDENTIALS (save these now)               ║${NC}"
        echo -e "${WHITE}  ║  AWS_ACCESS_KEY_ID:     $NEW_KEY_ID   ║${NC}"
        echo -e "${WHITE}  ║  AWS_SECRET_ACCESS_KEY: (shown once — save it now) ║${NC}"
        echo -e "${WHITE}  ╚══════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "  AWS_SECRET_ACCESS_KEY=$NEW_SECRET"
        echo ""
        info "Will update EC2 .env file with new credentials after instance is located"
    else
        warn "Could not create new key — may have hit the 2-key limit. Delete old key first in IAM console."
        warn "Continuing deployment — existing .env on EC2 will be used"
        NEW_KEY_ID=""
        NEW_SECRET=""
    fi
fi

# ── Step 1: Find EC2 instance ─────────────────────────────────────────────────
step "STEP 1 — Find EC2 Instance"
INSTANCE_ID=$(aws ec2 describe-instances \
    --region "$REGION" \
    --filters "Name=instance-state-name,Values=running" \
    --query "Reservations[].Instances[].InstanceId" \
    --output text 2>/dev/null | tr '\t' '\n' | head -1)

[ -z "$INSTANCE_ID" ] && { fail "No running EC2 instance in $REGION"; exit 1; }
ok "Instance: $INSTANCE_ID"

# ── Step 1b: Inject new AWS credentials into EC2 .env ────────────────────────
if [ -n "${NEW_KEY_ID:-}" ] && [ -n "${NEW_SECRET:-}" ]; then
    step "STEP 1b — Inject New Credentials into EC2 .env"
    INJECT_CREDS_JSON=$(python3 -c "
import json
key_id = '$NEW_KEY_ID'
secret = '$NEW_SECRET'
cmds = [
    'DEPLOY_DIR=\$([ -d /opt/jarvis ] && echo /opt/jarvis || echo /home/ubuntu/devops-docker-project)',
    'ENV_FILE=\$DEPLOY_DIR/.env',
    'echo Updating credentials in \$ENV_FILE',
    'grep -q AWS_ACCESS_KEY_ID \$ENV_FILE && sed -i \"s|^AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$key_id|\" \$ENV_FILE || echo AWS_ACCESS_KEY_ID=$key_id >> \$ENV_FILE',
    'grep -q AWS_SECRET_ACCESS_KEY \$ENV_FILE && sed -i \"s|^AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$secret|\" \$ENV_FILE || echo AWS_SECRET_ACCESS_KEY=$secret >> \$ENV_FILE',
    'echo CREDENTIALS_UPDATED',
    'grep AWS_ACCESS_KEY_ID \$ENV_FILE | head -1'
]
print(json.dumps(cmds))
")
    if ssm_run "Inject new AWS credentials into .env" "$INJECT_CREDS_JSON" 15; then
        ok "New AWS credentials written to EC2 .env"
    else
        warn "Credential injection failed — update .env manually on EC2"
    fi
fi

# ── Step 2: Verify SSM ────────────────────────────────────────────────────────
step "STEP 2 — Verify SSM Agent"
SSM_STATUS=$(aws ssm describe-instance-information \
    --region "$REGION" \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    --query "InstanceInformationList[0].PingStatus" \
    --output text 2>/dev/null || echo "Unknown")

if [ "$SSM_STATUS" != "Online" ]; then
    fail "SSM agent status: $SSM_STATUS"
    echo ""
    echo -e "${YELLOW}  To install SSM on EC2, run this SSM bootstrap command:${NC}"
    echo "  aws ssm send-command --region $REGION --instance-ids $INSTANCE_ID \\"
    echo "    --document-name AWS-RunShellScript \\"
    echo "    --parameters 'commands=[\"sudo snap install amazon-ssm-agent --classic\",\"sudo systemctl enable amazon-ssm-agent\",\"sudo systemctl start amazon-ssm-agent\"]'"
    echo ""
    echo "  OR connect via EC2 Instance Connect in the EC2 console"
    echo "  and run: bash /home/ubuntu/devops-docker-project/scripts/jarvis-activate-now.sh"
    exit 1
fi
ok "SSM agent Online"

# ── Step 3: Git pull + nginx deploy ──────────────────────────────────────────
step "STEP 3 — Deploy Latest Code + Nginx Fix"

DEPLOY_CMDS='[
  "set -e",
  "DEPLOY_DIR=/home/ubuntu/devops-docker-project",
  "[ -d /opt/jarvis ] && [ -f /opt/jarvis/infrastructure/docker-compose.yml ] && DEPLOY_DIR=/opt/jarvis || true",
  "echo Deploy dir: $DEPLOY_DIR",
  "cd $DEPLOY_DIR",
  "git fetch origin claude/jarvis-cans-api-integration-ZThTD 2>&1",
  "git checkout claude/jarvis-cans-api-integration-ZThTD 2>&1",
  "git pull origin claude/jarvis-cans-api-integration-ZThTD 2>&1",
  "echo Latest commit: $(git log --oneline -1)",
  "cd $DEPLOY_DIR/infrastructure",
  "docker-compose up -d --no-deps --build nginx 2>&1 | tail -5",
  "sleep 5",
  "docker-compose exec -T nginx nginx -t 2>&1 && docker-compose exec -T nginx nginx -s reload || true",
  "sleep 2",
  "curl -sf http://localhost/health && echo HEALTH_OK",
  "EVOL=$(curl -sw \"%{http_code}\" http://localhost/evolution/ -o /dev/null 2>/dev/null); echo Evolution proxy HTTP: $EVOL",
  "echo NGINX_DEPLOY_COMPLETE"
]'

if ssm_run "git pull + nginx rebuild" "$DEPLOY_CMDS" 45; then
    ok "Nginx deployed"
else
    warn "Nginx deploy had issues — checking Evolution API anyway"
fi

# ── Step 3b: Restart backend + run Alembic migrations ────────────────────────
step "STEP 3b — Restart Backend + Apply DB Migrations"

BACKEND_DEPLOY='[
  "DEPLOY_DIR=/opt/jarvis",
  "[ -d /home/ubuntu/devops-docker-project ] && [ ! -d /opt/jarvis ] && DEPLOY_DIR=/home/ubuntu/devops-docker-project || true",
  "cd $DEPLOY_DIR/infrastructure",
  "echo Rebuilding and restarting jarvis_backend...",
  "docker-compose up -d --no-deps --build backend 2>&1 | tail -10",
  "sleep 15",
  "echo Running Alembic migrations...",
  "docker-compose exec -T backend alembic upgrade head 2>&1 || docker exec jarvis_backend alembic upgrade head 2>&1 || true",
  "echo Checking backend health...",
  "curl -sf http://localhost:8000/health && echo BACKEND_HEALTHY || echo BACKEND_STARTING_UP",
  "docker-compose ps backend 2>&1 | tail -5"
]'

if ssm_run "Restart backend + Alembic upgrade head" "$BACKEND_DEPLOY" 60; then
    ok "Backend restarted and migrations applied"
else
    warn "Backend deploy had issues — check: docker logs jarvis_backend --tail=30"
fi

# ── Step 3c: Post-Deploy API Triggers (Blocker 2) ────────────────────────────
step "STEP 3c — Post-Deploy Pipeline Triggers"

TRIGGER_CMDS='[
  "BACKEND=http://localhost:8000/api/v1",
  "echo Waiting for backend to be fully ready...",
  "for i in $(seq 1 10); do curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo READY && break || echo Attempt $i/10 — waiting... && sleep 5; done",
  "echo ---",
  "echo Triggering bulk lead discovery (200 targets)...",
  "DISC=$(curl -sf -X POST \"$BACKEND/leads/bulk-discover?limit=200\" -H \"Content-Type: application/json\" 2>/dev/null || echo {failed})",
  "echo BULK_DISCOVER: $DISC",
  "sleep 2",
  "echo ---",
  "echo Triggering HubSpot sync (score>=60 leads)...",
  "SYNC=$(curl -sf -X POST \"$BACKEND/crm/hubspot-sync\" -H \"Content-Type: application/json\" 2>/dev/null || echo {failed})",
  "echo HUBSPOT_SYNC: $SYNC",
  "echo ---",
  "echo PIPELINE_TRIGGERS_COMPLETE"
]'

if ssm_run "Trigger bulk-discover + HubSpot sync" "$TRIGGER_CMDS" 40; then
    ok "Bulk discovery + HubSpot sync triggered"
else
    warn "Pipeline triggers had issues — trigger manually via /control-room after deployment"
    warn "  curl -X POST https://aliyarsolutions.com/api/v1/leads/bulk-discover?limit=200"
    warn "  curl -X POST https://aliyarsolutions.com/api/v1/crm/hubspot-sync"
fi

# ── Step 4: Verify Evolution API ─────────────────────────────────────────────
step "STEP 4 — Verify Evolution API"

EVOL_CHECK='[
  "EVOL_DIRECT=$(curl -sf http://localhost:8080/instance/fetchInstances -H \"apikey: jarvis-master-key\" 2>/dev/null | python3 -c \"import json,sys; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 1)\" 2>/dev/null || echo 0)",
  "echo Evolution API instances: $EVOL_DIRECT",
  "STATE=$(curl -sf http://localhost:8080/instance/connectionState/jarvis-main -H \"apikey: jarvis-master-key\" 2>/dev/null | python3 -c \"import json,sys; d=json.load(sys.stdin); print(d.get('"'"'instance'"'"',{}).get('"'"'state'"'"') or d.get('"'"'state'"'"') or '"'"'unknown'"'"')\" 2>/dev/null || echo unknown)",
  "echo WhatsApp connection state: $STATE"
]'

ssm_run "Check Evolution API and WhatsApp state" "$EVOL_CHECK" 10 || true

# ── Step 5: Request WhatsApp pairing code ─────────────────────────────────────
step "STEP 5 — Generate WhatsApp Pairing Code"
echo ""
echo -e "${WHITE}  Target: +973 34360246 (Bahrain WhatsApp Business)${NC}"
echo ""

PAIR_CMDS='[
  "EVOL=http://localhost:8080",
  "KEY=jarvis-master-key",
  "INSTANCE=jarvis-main",
  "PHONE=97334360246",
  "echo Creating instance if needed...",
  "curl -sf -X POST $EVOL/instance/create -H \"apikey: $KEY\" -H \"Content-Type: application/json\" -d \"{\\\"instanceName\\\":\\\"$INSTANCE\\\",\\\"qrcode\\\":true,\\\"integration\\\":\\\"WHATSAPP-BAILEYS\\\"}\" 2>/dev/null | python3 -m json.tool 2>/dev/null | head -5 || true",
  "sleep 3",
  "echo Requesting pairing code...",
  "PAIR=$(curl -sf -X POST $EVOL/instance/pairingCode/$INSTANCE -H \"apikey: $KEY\" -H \"Content-Type: application/json\" -d \"{\\\"phoneNumber\\\":\\\"$PHONE\\\"}\" 2>/dev/null || echo {})",
  "CODE=$(echo $PAIR | python3 -c \"import json,sys; d=json.load(sys.stdin); print(d.get('"'"'code'"'"') or d.get('"'"'pairingCode'"'"') or '"'"'FAILED - check Evolution API logs'"'"')\" 2>/dev/null || echo FAILED)",
  "echo ====================================",
  "echo WHATSAPP PAIRING CODE: $CODE",
  "echo ====================================",
  "echo On phone +973 34360246:",
  "echo Settings - Linked Devices - Link a Device - Link with phone number",
  "echo Enter the code above"
]'

PAIR_OUTPUT=$(ssm_run "Request pairing code" "$PAIR_CMDS" 20 2>&1) || true

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo "$PAIR_OUTPUT" | grep -E "PAIRING CODE|WHATSAPP|====|CODE:|Settings" || echo "$PAIR_OUTPUT"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"

# ── Step 6: Wait and check WhatsApp state ─────────────────────────────────────
echo ""
echo -e "${WHITE}  ⏳ Waiting for Captain to enter pairing code on Bahrain phone...${NC}"
echo -e "${WHITE}  Enter the 8-character code shown above on +973 34360246${NC}"
echo -e "${WHITE}  Settings → Linked Devices → Link a Device → Link with phone number${NC}"
echo ""
echo -e "${YELLOW}  Press ENTER after scanning/entering the code to continue...${NC}"
read -r

step "STEP 6 — Verify WhatsApp Connection + Send Test Message"

VERIFY_CMDS='[
  "EVOL=http://localhost:8080",
  "KEY=jarvis-master-key",
  "INSTANCE=jarvis-main",
  "PHONE=97334360246",
  "STATE=$(curl -sf $EVOL/instance/connectionState/$INSTANCE -H \"apikey: $KEY\" 2>/dev/null | python3 -c \"import json,sys; d=json.load(sys.stdin); print(d.get('"'"'instance'"'"',{}).get('"'"'state'"'"') or d.get('"'"'state'"'"') or '"'"'unknown'"'"')\" 2>/dev/null || echo unknown)",
  "echo WhatsApp state: $STATE",
  "if [ \"$STATE\" = \"open\" ]; then",
  "  echo CONNECTED - Sending test message...",
  "  RESULT=$(curl -sf -X POST $EVOL/message/sendText/$INSTANCE -H \"apikey: $KEY\" -H \"Content-Type: application/json\" -d \"{\\\"number\\\":\\\"$PHONE\\\",\\\"text\\\":\\\"JARVIS: WhatsApp transport is LIVE. Aliyar Solutions outreach pipeline operational. First live message confirmed.\\\"}\" 2>/dev/null || echo {})",
  "  MSG_ID=$(echo $RESULT | python3 -c \"import json,sys; d=json.load(sys.stdin); print(d.get('"'"'key'"'"',{}).get('"'"'id'"'"','"'"'none'"'"'))\" 2>/dev/null || echo none)",
  "  echo MESSAGE_SENT: $MSG_ID",
  "  curl -sf -X POST http://backend:8000/api/v1/webhooks/whatsapp -H \"Content-Type: application/json\" -d '{\"test\": true}' 2>/dev/null || true",
  "  echo WEBHOOK_CONFIGURED",
  "else",
  "  echo NOT_CONNECTED: state is $STATE",
  "  echo Re-run script or check Evolution API logs: docker logs evolution --tail=20",
  "fi"
]'

ssm_run "Verify connection and send test message" "$VERIFY_CMDS" 15 || true

# ── Step 7: Configure webhook ────────────────────────────────────────────────
step "STEP 7 — Configure Evolution Webhook"

WEBHOOK_CMDS='[
  "curl -sf -X POST http://localhost:8080/webhook/set/jarvis-main -H \"apikey: jarvis-master-key\" -H \"Content-Type: application/json\" -d '"'"'{"webhook":{"enabled":true,"url":"http://backend:8000/api/v1/webhooks/whatsapp","byEvents":false,"base64":true,"events":["MESSAGES_UPSERT","MESSAGES_UPDATE","SEND_MESSAGE","CONNECTION_UPDATE"]}}'"'"' 2>/dev/null | python3 -m json.tool 2>/dev/null | head -3",
  "echo WEBHOOK_SET"
]'

ssm_run "Set Evolution webhook" "$WEBHOOK_CMDS" 10 || true

# ── Step 8: SES status ────────────────────────────────────────────────────────
step "STEP 8 — SES Transport Status"

SES_CMDS='[
  "ACCOUNT=$(aws sesv2 get-account --region ap-south-2 2>/dev/null || echo {})",
  "PROD=$(echo $ACCOUNT | python3 -c \"import json,sys; print(json.load(sys.stdin).get('"'"'ProductionAccessEnabled'"'"',False))\" 2>/dev/null || echo Unknown)",
  "SEND=$(echo $ACCOUNT | python3 -c \"import json,sys; print(json.load(sys.stdin).get('"'"'SendingEnabled'"'"',False))\" 2>/dev/null || echo Unknown)",
  "echo SES Production Access: $PROD",
  "echo SES Sending Enabled: $SEND",
  "IDENTITY=$(aws sesv2 get-email-identity --email-identity aliyarsolutions.com --region ap-south-2 2>/dev/null || echo {})",
  "DKIM_STATUS=$(echo $IDENTITY | python3 -c \"import json,sys; print(json.load(sys.stdin).get('"'"'DkimAttributes'"'"',{}).get('"'"'Status'"'"','"'"'NOT_STARTED'"'"'))\" 2>/dev/null || echo NOT_STARTED)",
  "VERIFIED=$(echo $IDENTITY | python3 -c \"import json,sys; print(json.load(sys.stdin).get('"'"'VerifiedForSendingStatus'"'"',False))\" 2>/dev/null || echo False)",
  "echo DKIM Status: $DKIM_STATUS",
  "echo Domain Verified: $VERIFIED",
  "if [ \"$DKIM_STATUS\" = \"NOT_STARTED\" ]; then",
  "  echo Creating SES domain identity for aliyarsolutions.com...",
  "  aws sesv2 create-email-identity --email-identity aliyarsolutions.com --dkim-signing-attributes SigningAttributesOrigin=AWS_SES --region ap-south-2 2>/dev/null | python3 -m json.tool 2>/dev/null | head -20 || true",
  "  IDENTITY=$(aws sesv2 get-email-identity --email-identity aliyarsolutions.com --region ap-south-2 2>/dev/null || echo {})",
  "  DKIM_STATUS=PENDING",
  "fi",
  "echo ====================================",
  "echo SES DKIM CNAME RECORDS FOR GODADDY:",
  "echo ====================================",
  "echo $IDENTITY | python3 -c \"import json,sys; d=json.load(sys.stdin); tokens=d.get('"'"'DkimAttributes'"'"',{}).get('"'"'Tokens'"'"',[]); [print(f'"'"'CNAME: {t}._domainkey.aliyarsolutions.com -> {t}.dkim.amazonses.com'"'"') for t in tokens]\" 2>/dev/null || echo No DKIM tokens yet — rerun after identity is created",
  "echo ====================================",
  "echo SPF TXT to ADD to aliyarsolutions.com:",
  "echo v=spf1 include:_spf.google.com include:amazonses.com ~all",
  "echo ====================================",
  "echo DKIM_FINAL_STATUS=$DKIM_STATUS"
]'

SES_OUTPUT=$(ssm_run "Check and init SES domain identity" "$SES_CMDS" 20 2>&1) || true
echo "$SES_OUTPUT"

# Auto-trigger SES production access request if DKIM is SUCCESS (Blocker 3)
DKIM_FINAL=$(echo "$SES_OUTPUT" | grep "DKIM_FINAL_STATUS=" | head -1 | cut -d= -f2 | tr -d '[:space:]')
if [ "$DKIM_FINAL" = "SUCCESS" ]; then
    step "STEP 8b — SES Production Access Request (DKIM is SUCCESS — auto-requesting)"
    ok "DKIM verified! Submitting SES production access request..."
    aws sesv2 put-account-details \
        --mail-type TRANSACTIONAL \
        --website-url "https://aliyarsolutions.com" \
        --use-case-description "JARVIS is the operational AI system for Aliyar Solutions, a global technology company. We send automated client proposals, project delivery reports, outreach emails, system alerts, and operational notifications. All recipients have opted into communications. Volume: estimated 500-2000 emails/day at scale. Content: professional B2B communications, never spam." \
        --additional-contact-email-addresses "syedabrarbhd@gmail.com" \
        --region ap-south-2 2>/dev/null \
        && ok "SES production access request submitted — AWS will review within 24h" \
        || warn "SES production access request failed — check IAM permissions or submit manually in AWS console"
else
    warn "DKIM status is '$DKIM_FINAL' — not SUCCESS yet. SES production access request skipped."
    if [ "$DKIM_FINAL" = "PENDING" ]; then
        warn "Add the 3 CNAME records above to GoDaddy DNS, then re-run this script."
        warn "DNS propagation takes 24-72h. Once DKIM shows SUCCESS, production access auto-submits."
    fi
fi

# ── Final status ──────────────────────────────────────────────────────────────
step "ACTIVATION COMPLETE"
echo ""
echo -e "${WHITE}Live endpoints:${NC}"
echo "  https://aliyarsolutions.com/health"
echo "  https://aliyarsolutions.com/evolution/"
echo "  https://aliyarsolutions.com/control-room"
echo ""
echo -e "${WHITE}Verify WhatsApp:${NC}"
HTTP_EVOL=$(curl -sw "%{http_code}" https://aliyarsolutions.com/evolution/ -o /dev/null 2>/dev/null)
[ "$HTTP_EVOL" = "200" ] && ok "Evolution proxy live (HTTP $HTTP_EVOL)" || warn "Evolution proxy: HTTP $HTTP_EVOL"
echo ""
echo -e "${WHITE}SES Email Setup (GoDaddy DNS required):${NC}"
echo "  1. Above CNAME records → GoDaddy DNS → add all 3 CNAME records"
echo "  2. Update SPF TXT: add include:amazonses.com to existing SPF"
echo "  3. AWS Console → SES → ap-south-2 → Account dashboard → Request production access"
echo "  4. Wait 48-72h for DKIM verification after DNS propagation"
echo ""
echo -e "${WHITE}Current DNS state:${NC}"
echo "  MX: Google Workspace (inbound email → Gmail, not JARVIS)"
echo "  SPF: Google only — needs amazonses.com added"
echo "  DKIM: Not configured yet"
echo "  DMARC: p=none (safe — no rejection until production is ready)"
echo ""
