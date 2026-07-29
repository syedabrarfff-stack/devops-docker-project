# Secrets Rotation Runbook — Aliyar Solutions / JARVIS

## Current State (as of 2026-07-03)

**Risk:** 20 API keys stored as plaintext in `.env` on EC2 instance.  
**Exposure surface:** `.env` readable by any process with EC2 access; appears in `docker inspect` environment output; may appear in SSM command logs.  
**Target state:** All secrets in AWS Secrets Manager, fetched at container start, never stored in `.env` on disk.

---

## Phase 1 — Immediate: Key Rotation (do this now)

Rotate every key below. Each provider has a self-service key portal.

| Key | Provider Portal | Action |
|-----|-----------------|--------|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | Revoke old → Create new |
| `OPENAI_API_KEY` | platform.openai.com → API Keys | Revoke old → Create new |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | console.cloud.google.com → Credentials | Revoke old → Create new |
| `NVIDIA_API_KEY` + `_B` through `_J` (10 keys) | build.nvidia.com → API Keys | Revoke all 10 → Create 10 new |
| `DEEPSEEK_API_KEY` | platform.deepseek.com → API Keys | Revoke old → Create new |
| `GROQ_API_KEY` | console.groq.com → API Keys | Revoke old → Create new |
| `MISTRAL_API_KEY` | console.mistral.ai → API Keys | Revoke old → Create new |
| `TELEGRAM_BOT_TOKEN` | @BotFather → /revoke | Revoke → /token for new |
| `STRIPE_SECRET_KEY` | dashboard.stripe.com → Developers → API Keys | Roll key |
| `HUBSPOT_API_KEY` | app.hubspot.com → Settings → Integrations → API Key | Rotate |

### After rotating each key

SSH to EC2 or update via SSM:
```bash
# On EC2
sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=sk-ant-NEWVALUE|" /opt/jarvis/.env
# Restart backend to pick up new value
cd /opt/jarvis/infrastructure && docker-compose -p jarvis restart backend
```

Verify the new key works:
```bash
curl -sf http://localhost:8000/health | python3 -m json.tool
curl -sf http://localhost:8000/readyz | python3 -m json.tool
```

---

## Phase 2 — Migration: AWS Secrets Manager

**Goal:** Remove all secrets from `.env`. Container fetches them at startup from Secrets Manager.

### Step 1 — Create secrets in Secrets Manager

```bash
# Run from local machine with AWS CLI configured
REGION=ap-south-2

# Create one secret per key (or bundle into a single JSON secret)
aws secretsmanager create-secret \
  --region "$REGION" \
  --name "jarvis/production/anthropic-api-key" \
  --secret-string "sk-ant-NEWVALUE"

aws secretsmanager create-secret \
  --region "$REGION" \
  --name "jarvis/production/openai-api-key" \
  --secret-string "sk-NEWVALUE"

# Repeat for each key above.
# Or bundle all non-critical env vars into one JSON secret:
aws secretsmanager create-secret \
  --region "$REGION" \
  --name "jarvis/production/env-bundle" \
  --secret-string file://secrets-bundle.json
```

### Step 2 — IAM: allow ECS task role to read secrets

Add this policy to the `JarvisGitHubActionsRole` (or the ECS task execution role if using ECS):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadJarvisSecrets",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:ap-south-2:*:secret:jarvis/production/*"
    }
  ]
}
```

### Step 3 — Fetch secrets at container start

Add to `scripts/ec2-deploy-script.sh` (after the deploy dir is known):

```bash
# Fetch secrets from Secrets Manager and inject into .env
if command -v aws &>/dev/null; then
  REGION="${AWS_DEFAULT_REGION:-ap-south-2}"
  aws secretsmanager get-secret-value \
    --region "$REGION" \
    --secret-id "jarvis/production/env-bundle" \
    --query SecretString --output text \
    | python3 -c "
import sys, json
bundle = json.load(sys.stdin)
for k, v in bundle.items():
    # Update or append each key in .env
    import subprocess
    subprocess.run(['sed', '-i', f's|^{k}=.*|{k}={v}|', '.env'])
    print(f'Injected: {k}')
"
  echo "=== Secrets injected from Secrets Manager ==="
fi
```

### Step 4 — Remove plaintext keys from `.env.example` and `.env`

Replace all key values with a placeholder comment:
```
ANTHROPIC_API_KEY=# MANAGED BY AWS SECRETS MANAGER — do not commit
```

### Step 5 — Verify nothing is committed

```bash
git log --all --full-history -- '.env' | head -20
git grep -i "sk-ant-" -- ':!*.md' || echo "No Anthropic keys in codebase"
git grep -i "sk-" -- ':!*.md' || echo "No API keys found"
```

---

## Rotation Schedule

| Secret class | Rotation frequency | Method |
|---|---|---|
| AI provider API keys | Every 90 days | Manual — portal |
| Telegram bot token | Every 180 days | BotFather |
| Stripe keys | Every 180 days | Dashboard roll |
| DB password | Every 90 days | `ALTER ROLE jarvis_user PASSWORD '...'` + update secret |
| Redis password | Every 90 days | Update `requirepass` in redis.conf + update secret |
| JWT secret key | Every 180 days | Rolling restart (all active sessions invalidated) |

---

## Emergency: Suspected Compromise

If a key may be compromised:

1. Revoke immediately at the provider portal — do not wait.
2. Rotate to a new key.
3. Check provider usage logs for unauthorized calls in the last 24h.
4. Notify Captain within 60 seconds per incident protocol.
5. Document incident in `JARVIS_SELF_KNOWLEDGE.md` under Security Events.
6. File provider support ticket if unauthorized usage confirmed.

**Never rotate keys in a live commit.** Always set via SSM command or Secrets Manager.
