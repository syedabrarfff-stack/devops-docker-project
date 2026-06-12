#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# JARVIS — AWS CloudShell Deploy
# Aliyar Solutions — Captain Syed Abrar
#
# Run this from AWS CloudShell (console.aws.amazon.com → click >_ in top bar)
# No SSH key needed. No port 22 needed. Just AWS credentials.
#
# Usage (paste this entire block into CloudShell):
#   bash <(curl -s https://raw.githubusercontent.com/syedabrarfff-stack/devops-docker-project/claude/jarvis-cans-api-integration-ZThTD/scripts/cloudshell-deploy.sh)
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

REGION="ap-south-2"
BRANCH="claude/jarvis-cans-api-integration-ZThTD"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  JARVIS CloudShell Deploy — Aliyar Solutions  ${NC}"
echo -e "${CYAN}  Region: $REGION                          ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

# ── Find EC2 instance ──────────────────────────────────────────────────────
echo -e "${CYAN}→  Finding EC2 instance...${NC}"
INSTANCE_ID=$(aws ec2 describe-instances \
    --region "$REGION" \
    --filters "Name=instance-state-name,Values=running" \
    --query "Reservations[].Instances[].InstanceId" \
    --output text 2>/dev/null | tr '\t' '\n' | head -1)

if [ -z "$INSTANCE_ID" ]; then
    echo -e "${RED}❌ No running EC2 instance found in $REGION${NC}"
    echo "   Check AWS Console → EC2 → Instances"
    exit 1
fi

echo -e "${GREEN}✅ Found instance: $INSTANCE_ID${NC}"

# ── Check SSM availability ─────────────────────────────────────────────────
echo -e "${CYAN}→  Checking SSM agent...${NC}"
SSM_STATUS=$(aws ssm describe-instance-information \
    --region "$REGION" \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    --query "InstanceInformationList[0].PingStatus" \
    --output text 2>/dev/null || echo "Unknown")

if [ "$SSM_STATUS" != "Online" ]; then
    echo -e "${YELLOW}⚠  SSM agent status: $SSM_STATUS${NC}"
    echo ""
    echo "  If SSM is not available, install it on EC2:"
    echo "    sudo snap install amazon-ssm-agent --classic"
    echo "    sudo systemctl enable amazon-ssm-agent"
    echo "    sudo systemctl start amazon-ssm-agent"
    echo ""
    echo "  Then re-run this script."
    echo ""
    echo "  Alternatively, open port 22 in the security group and SSH:"
    echo "    ssh ubuntu@aliyarsolutions.com -i your-key.pem"
    echo "    bash /home/ubuntu/devops-docker-project/scripts/jarvis-activate-now.sh"
    exit 1
fi

echo -e "${GREEN}✅ SSM agent is Online${NC}"

# ── Send activation command ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}→  Sending activation command via SSM...${NC}"
echo "   (This runs jarvis-activate-now.sh on the EC2 instance)"
echo ""

COMMANDS=$(cat <<'CMDS'
[
  "set -e",
  "DEPLOY_DIR=/home/ubuntu/devops-docker-project",
  "[ -d /opt/jarvis ] && [ -f /opt/jarvis/infrastructure/docker-compose.yml ] && DEPLOY_DIR=/opt/jarvis || true",
  "cd $DEPLOY_DIR",
  "git fetch origin claude/jarvis-cans-api-integration-ZThTD",
  "git checkout claude/jarvis-cans-api-integration-ZThTD",
  "git pull origin claude/jarvis-cans-api-integration-ZThTD",
  "echo '--- Git pull complete ---'",
  "git log --oneline -3",
  "echo '--- Reloading nginx ---'",
  "cd $DEPLOY_DIR/infrastructure",
  "docker compose exec -T nginx nginx -t 2>&1 && docker compose exec -T nginx nginx -s reload || docker compose up -d --no-deps nginx",
  "sleep 3",
  "echo '--- Nginx reloaded ---'",
  "curl -sf http://localhost/health && echo 'HEALTH OK' || echo 'HEALTH CHECK FAILED'",
  "curl -sf http://localhost/evolution/ > /dev/null 2>&1 && echo 'EVOLUTION PROXY OK' || echo 'EVOLUTION: check separately'",
  "echo '--- Docker status ---'",
  "docker compose ps"
]
CMDS
)

COMMAND_ID=$(aws ssm send-command \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "{\"commands\": $(echo "$COMMANDS" | python3 -c 'import json,sys; cmds=json.load(sys.stdin); print(json.dumps(cmds))')}" \
    --comment "JARVIS nginx fix + activation" \
    --query "Command.CommandId" \
    --output text 2>/dev/null)

if [ -z "$COMMAND_ID" ]; then
    echo -e "${RED}❌ SSM command failed to send${NC}"
    echo "   Check IAM role on EC2 instance has AmazonSSMManagedInstanceCore policy"
    exit 1
fi

echo -e "${GREEN}✅ SSM Command sent: $COMMAND_ID${NC}"
echo ""
echo -e "${CYAN}→  Waiting for command to complete (up to 60s)...${NC}"

# ── Poll for completion ────────────────────────────────────────────────────
for i in $(seq 1 12); do
    sleep 5
    OUTPUT=$(aws ssm get-command-invocation \
        --region "$REGION" \
        --command-id "$COMMAND_ID" \
        --instance-id "$INSTANCE_ID" \
        --output json 2>/dev/null || echo '{"Status":"Pending"}')

    STATUS=$(echo "$OUTPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('Status','Unknown'))" 2>/dev/null || echo "Unknown")

    if [ "$STATUS" = "Success" ] || [ "$STATUS" = "Failed" ] || [ "$STATUS" = "Cancelled" ]; then
        break
    fi
    echo "   Status: $STATUS (${i}/12)..."
done

STDOUT=$(echo "$OUTPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('StandardOutputContent',''))" 2>/dev/null || echo "")
STDERR=$(echo "$OUTPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('StandardErrorContent',''))" 2>/dev/null || echo "")

echo ""
echo -e "${CYAN}═══════ COMMAND OUTPUT ═══════${NC}"
echo "$STDOUT"
[ -n "$STDERR" ] && echo -e "${YELLOW}STDERR: $STDERR${NC}"
echo -e "${CYAN}══════════════════════════════${NC}"
echo ""

if [ "$STATUS" = "Success" ]; then
    echo -e "${GREEN}✅ Nginx fix DEPLOYED successfully!${NC}"
    echo ""
    echo -e "${CYAN}→  Next: Run the full WhatsApp activation:${NC}"
    echo ""

    # Send the full activation script as a second command
    echo "   Sending WhatsApp pairing command..."
    CMD2=$(aws ssm send-command \
        --region "$REGION" \
        --instance-ids "$INSTANCE_ID" \
        --document-name "AWS-RunShellScript" \
        --parameters '{"commands":["DEPLOY_DIR=/home/ubuntu/devops-docker-project","[ -d /opt/jarvis ] && [ -f /opt/jarvis/infrastructure/docker-compose.yml ] && DEPLOY_DIR=/opt/jarvis || true","cd $DEPLOY_DIR","bash scripts/jarvis-activate-now.sh 2>&1 | head -100"]}' \
        --comment "JARVIS WhatsApp activation" \
        --query "Command.CommandId" \
        --output text 2>/dev/null || echo "")

    if [ -n "$CMD2" ]; then
        echo -e "${GREEN}✅ Activation command sent: $CMD2${NC}"
        echo ""
        echo "   Waiting 30s then fetching output..."
        sleep 30
        ACT_OUTPUT=$(aws ssm get-command-invocation \
            --region "$REGION" \
            --command-id "$CMD2" \
            --instance-id "$INSTANCE_ID" \
            --query "StandardOutputContent" \
            --output text 2>/dev/null || echo "")
        echo ""
        echo -e "${CYAN}═══ Activation Output ═══${NC}"
        echo "$ACT_OUTPUT"
        echo -e "${CYAN}═════════════════════════${NC}"
    fi
else
    echo -e "${RED}❌ Command status: $STATUS${NC}"
    echo ""
    echo "   Manual fallback — SSH into EC2 and run:"
    echo "     bash /home/ubuntu/devops-docker-project/scripts/jarvis-activate-now.sh"
fi

echo ""
echo -e "${CYAN}Verify at: https://aliyarsolutions.com/health${NC}"
echo -e "${CYAN}Control Room: https://aliyarsolutions.com/control-room${NC}"
echo ""
