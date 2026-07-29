# JARVIS Environment Setup Guide

Complete instructions for configuring all environment variables needed to run JARVIS. This guide covers 5 critical MVP blockers and 45+ optional advanced configurations.

---

## Critical Blockers (5) — Must Configure First

These environment variables are **required for MVP launch**. Without them, core functionality will not work.

---

## 1. STRIPE_WEBHOOK_SECRET 🔴 CRITICAL

**Purpose:** Secure webhook verification for payment events (charges, refunds, subscription updates)

**Why it matters:** Without this, webhook payloads cannot be verified, payment processing fails silently

### Get Your Secret

#### Step 1: Access Stripe Dashboard

1. Go to https://dashboard.stripe.com
2. Login with your account
3. Navigate to **Developers** → **Webhooks**

#### Step 2: Create/View Webhook Endpoint

1. Click **Add endpoint** (or view existing endpoint)
2. Endpoint URL: `https://your-api-domain.com/api/v1/payments/webhook`
3. Events to listen for:
   - `charge.succeeded`
   - `charge.failed`
   - `payment_intent.succeeded`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Click **Add endpoint**

#### Step 3: Copy Signing Secret

1. Click on the endpoint
2. Scroll to **Signing secret**
3. Click **Reveal signing secret** (it starts with `whsec_`)
4. Copy the full secret

### Configure in .env

```bash
# .env
STRIPE_WEBHOOK_SECRET=whsec_1234567890abcdefghijklmnop
```

### Verify It Works

```bash
# Test webhook delivery (in Stripe dashboard)
# Go to Webhooks → Your endpoint → Send test webhook

# Check backend logs
docker-compose logs backend | grep "webhook"

# Should see: "Webhook verified successfully"
```

---

## 2. SES_FROM_EMAIL 🔴 CRITICAL

**Purpose:** Verified sender email for AWS SES outbound emails

**Why it matters:** Without this, outreach automation cannot send emails. Leads never receive your messages.

### Get Your Email

#### Step 1: Verify Email in AWS SES

1. Go to AWS Console → **Simple Email Service** → **Verified identities**
2. Click **Create identity**
3. Choose **Email address**
4. Enter your sender email: `outreach@your-domain.com`
5. Click **Create identity**

#### Step 2: Verify Ownership

1. Check your email inbox for verification link from Amazon
2. Click the verification link
3. Email will show as **verified** in SES console

#### Step 3: Request Production Access (if sandbox mode)

If in sandbox:
1. Go to SES → **Account dashboard**
2. Scroll to **Email sending status**
3. If it says **Sandbox**, click **Request production access**
4. Fill form: Use case, volume, content type
5. Amazon will approve (usually within 24 hours)

### Configure in .env

```bash
# .env
SES_FROM_EMAIL=outreach@your-domain.com
# Also configure AWS credentials for SES:
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/...
AWS_REGION=ap-south-2  # or your region
```

### Verify It Works

```bash
# Test email sending (in backend)
# Route: POST /api/v1/outreach/test-send
curl -X POST http://localhost:8000/api/v1/outreach/test-send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"recipient_email": "your-test@example.com"}'

# Check email inbox for test message
```

---

## 3. AWS_ACCESS_KEY_ID & AWS_SECRET_ACCESS_KEY 🟡 HIGH

**Purpose:** AWS authentication for Bedrock (AI), S3 (storage), SES (email), ECS (deployment)

**Why it matters:** Without AWS credentials, Bedrock fallback provider unavailable, document storage fails, email sending fails, production deployment impossible

### Create AWS Credentials

#### Step 1: Create IAM User

1. Go to **AWS Console** → **IAM** → **Users**
2. Click **Create user**
3. Username: `jarvis-app` (or similar)
4. Click **Next**
5. Skip optional tags
6. Click **Create user**

#### Step 2: Attach Policies

1. Select the user
2. Click **Add permissions** → **Attach policies directly**
3. Search and attach:
   - `AmazonBedrockFullAccess`
   - `AmazonS3FullAccess`
   - `AmazonSESFullAccess`
   - `AmazonECS_FullAccess`
   - `AmazonEC2FullAccess`
   - `AmazonRDSFullAccess`
   - `AmazonElastiCacheFullAccess`
   - `SecretsManagerReadWrite`
4. Click **Next** → **Create**

Or use inline policy for fine-grained access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*:*:foundation-model/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::jarvis-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Step 3: Create Access Keys

1. Go to **IAM** → **Users** → `jarvis-app`
2. Click **Security credentials** tab
3. Scroll to **Access keys**
4. Click **Create access key**
5. Choose **Application running outside AWS**
6. Click **Create access key**
7. **Copy both values immediately** (can't be retrieved later):
   - Access Key ID: `AKIA...`
   - Secret Access Key: `wJal...`

### Configure in .env

```bash
# .env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-south-2

# Optional S3 bucket for document storage
AWS_S3_BUCKET=jarvis-documents-prod

# Bedrock model (optional, uses Claude by default)
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Verify It Works

```bash
# Test AWS credentials
aws sts get-caller-identity

# Output should show your AWS account
{
  "UserId": "AIDA...",
  "Account": "111111111111",
  "Arn": "arn:aws:iam::111111111111:user/jarvis-app"
}

# Test Bedrock access
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --body '{"messages": [{"role": "user", "content": "test"}]}' \
  --region ap-south-2 \
  response.json

# Test S3 access
aws s3 ls s3://jarvis-documents-prod
```

---

## 4. GITHUB_TOKEN 🟡 MEDIUM

**Purpose:** Authentication for GitHub API used by scout network (lead discovery automation)

**Why it matters:** Without this, scout network cannot push discovered lead data to `jarvis-data/` repository

### Create GitHub Token

#### Step 1: Personal Access Token

1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name: `JARVIS Scout Network`
4. Expiration: **90 days** (or 1 year)
5. Select scopes:
   - `repo` (full control of private repositories)
   - `workflow` (update GitHub Action workflows)
   - `admin:repo_hook` (write webhook events)
6. Click **Generate token**
7. **Copy the token immediately** (can't be retrieved later)

Starts with: `ghp_`

### Configure in .env

```bash
# .env
GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz
GITHUB_OWNER=your-github-username-or-org
GITHUB_REPO=jarvis-data  # Repository where scout pushes data
GITHUB_SCOUT_BRANCH=scout-data  # Branch for lead discoveries
```

### Verify It Works

```bash
# Test GitHub token
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Should return your GitHub user info

# Check scout network job
curl http://localhost:8000/api/v1/scheduler/jobs | grep scout_network

# Should show job status and next run time
```

---

## Optional High-Priority Configurations

These are not strictly required for MVP but are highly recommended for production use.

### AI Providers

```bash
# Primary AI Provider (Claude via Anthropic)
ANTHROPIC_API_KEY=sk-ant-api03-...
# Get from: https://console.anthropic.com/account/keys

# Fallback: OpenRouter (unified gateway to 100+ models)
OPENROUTER_API_KEY=sk-or-v1-...
# Get from: https://openrouter.ai/account/keys

# Alternative: OpenAI (GPT-4)
OPENAI_API_KEY=sk-...
# Get from: https://platform.openai.com/account/api-keys

# Alternative: Google Gemini
GOOGLE_API_KEY=...
# Get from: https://makersuite.google.com/app/apikey

# NIM (NVIDIA inference endpoints)
NVIDIA_API_KEY=nvapi-...
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
```

### Additional Services

```bash
# Telegram (Captain notifications)
TELEGRAM_BOT_TOKEN=123456:ABCdefGHIjklmnoPQRstuvWXYZ
TELEGRAM_CHAT_ID=123456789
# Get from: https://t.me/BotFather

# Slack (Team notifications)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000/B00000/XXXX
# Get from: Slack App → Incoming Webhooks

# Google Maps API (Lead discovery)
GOOGLE_MAPS_API_KEY=AIzaSy...
# Get from: Google Cloud Console → APIs & Services → Credentials

# Stripe (Payments - already have WEBHOOK_SECRET)
STRIPE_SECRET_KEY=sk_test_xxxxx  # or sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
# Get from: https://dashboard.stripe.com/apikeys
```

---

## Complete Environment Variables Template

See `.env.example` for all 50+ variables. Here's the organized structure:

```bash
# ─── CRITICAL BLOCKERS (5) ────────────────────────────────────

# Email
SES_FROM_EMAIL=

# Payments
STRIPE_WEBHOOK_SECRET=

# Cloud
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# GitHub
GITHUB_TOKEN=

# ─── PRIMARY AI PROVIDERS ─────────────────────────────────────

ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=

# ─── DATABASE & CACHE ─────────────────────────────────────────

DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/jarvis
REDIS_URL=redis://localhost:6379/0

# ─── APPLICATION ──────────────────────────────────────────────

APP_VERSION=1.0.0
APP_NAME=JARVIS
JARVIS_DEFAULT_TENANT_ID=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa
DEBUG=false
LOG_LEVEL=INFO

# ─── NOTIFICATIONS ────────────────────────────────────────────

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# ─── AWS SERVICES ─────────────────────────────────────────────

AWS_REGION=ap-south-2
AWS_S3_BUCKET=jarvis-documents-prod
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# ... and more (see .env.example)
```

---

## Quick Setup Checklist

### Phase 1: MVP (30 minutes)

- [ ] Copy `.env.example` to `.env`
- [ ] Configure `STRIPE_WEBHOOK_SECRET` (Stripe dashboard)
- [ ] Configure `SES_FROM_EMAIL` (AWS SES verify)
- [ ] Configure `AWS_*` credentials (AWS IAM)
- [ ] Configure `GITHUB_TOKEN` (GitHub settings)
- [ ] Test with: `docker-compose up -d`
- [ ] Verify all services: `docker-compose ps`

### Phase 2: AI Intelligence (20 minutes)

- [ ] Add `ANTHROPIC_API_KEY` (Anthropic console)
- [ ] Add `OPENROUTER_API_KEY` (OpenRouter dashboard)
- [ ] Test AI: `curl http://localhost:8000/api/v1/chat`

### Phase 3: Notifications (15 minutes)

- [ ] Add `TELEGRAM_BOT_TOKEN` (BotFather)
- [ ] Add `TELEGRAM_CHAT_ID` (save message in chat)
- [ ] Test briefing: `docker-compose logs backend | grep briefing`

### Phase 4: Optional (later)

- [ ] Google Maps for lead discovery
- [ ] Slack for team notifications
- [ ] Additional AI providers for fallback

---

## Troubleshooting

### "Invalid API Key" Error

```bash
# Verify key is not empty
echo $ANTHROPIC_API_KEY  # Should show key, not empty

# Check for typos or extra spaces
echo "$ANTHROPIC_API_KEY" | wc -c  # Should match key length + 1

# Test directly with provider
curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  https://api.anthropic.com/v1/models
```

### "Webhook Signature Verification Failed"

```bash
# Stripe webhook secret must match exactly
# Check in Stripe dashboard → Webhooks → Your endpoint
# Copy the EXACT secret (don't mix up test vs live)

# Test webhook locally (from Stripe dashboard)
# Send test event and check backend logs
docker-compose logs backend | grep webhook
```

### "AWS Credentials Invalid"

```bash
# Verify credentials are set correctly
aws sts get-caller-identity

# If fails, check:
# 1. Access key ID: should start with AKIA
# 2. Secret key: should be ~40 characters
# 3. No extra spaces or typos

# Reset credentials if needed
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
export AWS_ACCESS_KEY_ID="new-key-here"
export AWS_SECRET_ACCESS_KEY="new-secret-here"
```

### "GitHub Token Expired or Invalid"

```bash
# Check token
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user

# If fails:
# 1. Go to GitHub Settings → Personal access tokens
# 2. Generate new token
# 3. Copy exact token (no spaces)
# 4. Update .env

# Test scout network
curl http://localhost:8000/api/v1/scheduler/jobs | grep scout
```

---

## Security Best Practices

### Never Commit Secrets

```bash
# ❌ Wrong: commit secrets to Git
git add .env
git commit -m "add secrets"  # DON'T DO THIS

# ✅ Right: Use .env.example template
git add .env.example
git commit -m "add env template"

# ✅ Right: Use GitHub Secrets for CI/CD
# Settings → Secrets and variables → New repository secret
```

### Rotate Keys Regularly

```bash
# Every 90 days, regenerate:
# - AWS access keys
# - GitHub tokens
# - Stripe API keys

# Old key: Delete from AWS/GitHub
# New key: Update in .env and deploy
```

### Use Minimal Permissions

```bash
# ❌ Don't: Use root AWS account or admin user
# ✅ Do: Create dedicated IAM user with specific permissions

# Example policy (least privilege):
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"  # Only Bedrock, nothing else
      ],
      "Resource": "arn:aws:bedrock:*:*:foundation-model/*"
    }
  ]
}
```

---

## Next Steps After Configuration

1. **Verify Setup**
   ```bash
   docker-compose up -d
   docker-compose ps  # All services should be "running"
   curl http://localhost:8000/readyz  # Should return 200 OK
   ```

2. **Test Core Features**
   ```bash
   # AI chat
   curl -X POST http://localhost:8000/api/v1/chat \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "hello"}]}'

   # Lead discovery (if Google Maps configured)
   curl -X POST http://localhost:8000/api/v1/leads/discover \
     -H "Content-Type: application/json" \
     -d '{"query": "saas operations"}'
   ```

3. **Launch Frontend**
   ```bash
   npm run dev
   # Open http://localhost:5173
   ```

4. **Monitor Logs**
   ```bash
   docker-compose logs -f backend
   docker-compose logs -f frontend
   ```

---

## Support

- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **Logs:** `docker-compose logs backend`
- **Health Check:** `curl http://localhost:8000/health`
- **Status:** Check `Headquarters/STATUS.md` for known issues

---

**Last Updated:** 2024-07-02  
**Status:** 5 Critical Blockers documented + 45+ optional configs
