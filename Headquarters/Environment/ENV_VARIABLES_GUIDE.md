# JARVIS Environment Variables Guide

**SECURITY NOTE:** This file contains NO actual credentials or API keys. All real values must be stored only in your local `.env` file and NEVER committed to Git.

---

## 📋 Complete Environment Variable Reference

### Summary

| Category | Total Variables | Required | Optional | Status |
|---|---|---|---|---|
| Application Core | 11 | 11 | 0 | ✅ Complete |
| Database | 4 | 4 | 0 | ✅ Complete |
| Redis | 2 | 2 | 0 | ✅ Complete |
| AI Providers | 20 | 1 | 19 | 🟡 Partial |
| Lead Discovery | 1 | 1 | 0 | ✅ Complete |
| Payments | 6 | 1 | 5 | 🟡 Partial |
| Email / SES | 8 | 3 | 5 | 🟡 Partial |
| WhatsApp / Evolution | 5 | 4 | 1 | ✅ Complete |
| Notifications | 4 | 2 | 2 | ✅ Complete |
| n8n Integration | 2 | 0 | 2 | ✅ Complete |
| Connectors | 5 | 0 | 5 | 🔴 Missing |
| AWS | 12 | 0 | 12 | 🔴 Phase 3+ |
| GitHub Bridge | 4 | 1 | 0 | 🔴 Missing |
| Grafana & Monitoring | 3 | 3 | 0 | ✅ Complete |
| **TOTALS** | **88** | **33** | **48** | **7 Missing** |

---

## 🔐 Critical Security Rules

1. **NEVER commit .env to Git** — Already in `.gitignore`
2. **NEVER commit API keys, credentials, or secrets** — Even if "test" keys
3. **Store all secrets locally only** — In your `.env` file on your PC
4. **Production secrets go to AWS Secrets Manager** — Never in code/documentation
5. **Rotate API keys every 90 days** — In production environments
6. **Use IAM roles for AWS** — Never hardcode AWS access keys

**Consequence of violation:** Full system compromise. API keys can be revoked, subscriptions charged fraudulently, data accessed by anyone with the key.

---

## 🟢 Application Core (11/11 Required)

```env
DEBUG=false
SECRET_KEY=[64-byte hex string — generate with: python -c "import secrets; print(secrets.token_hex(32))"]
CAPTAIN_PASSWORD=[secure password for admin access]
CAPTAIN_USERNAME=captain [default, changeable]
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,https://aliyarsolutions.com
APP_BASE_URL=http://localhost:8000
JARVIS_DEFAULT_TENANT_ID=[UUID of default tenant]
CAPTAIN_NAME=Captain Abrar [default]
COMPANY_NAME=Aliyar Solutions [default]
FOUNDER_NAME=Syed Abrar [default]
```

**Where to get:**
- SECRET_KEY: Generate new random key (command above)
- CAPTAIN_PASSWORD: Create strong password
- JARVIS_DEFAULT_TENANT_ID: UUID from database (default provided)

---

## 🔴 Database (4/4 Required)

```env
DATABASE_URL=postgresql+asyncpg://[user]:[password]@[host]:5432/[database]
POSTGRES_USER=jarvis
POSTGRES_PASSWORD=[strong password]
POSTGRES_DB=jarvis
```

**Where to get:**
- From AWS RDS endpoint (production)
- Or Docker Compose (local: postgres:5432)
- Password: Create strong password (32+ chars)

---

## 🔴 Redis Cache (2/2 Required)

```env
REDIS_URL=redis://:[password]@[host]:6379/0
REDIS_PASSWORD=[strong password]
```

**Where to get:**
- From AWS ElastiCache (production)
- Or Docker Compose (local: redis:6379)

---

## 🟡 AI Providers (20 total, 1 required)

### Primary (Required — at least ONE)
```env
ANTHROPIC_API_KEY=[Get from: https://console.anthropic.com]
# Alternative (any ONE required):
OPENAI_API_KEY=[Get from: https://platform.openai.com/api-keys]
NVIDIA_API_KEY=[Get from: https://build.nvidia.com]
```

### Fallback Providers (Optional)
```env
DEEPSEEK_API_KEY=[Get from: https://platform.deepseek.com]
GROQ_API_KEY=[Get from: https://console.groq.com]
MISTRAL_API_KEY=[Get from: https://console.mistral.ai]
MOONSHOT_API_KEY=[Get from: https://platform.moonshot.cn]
ZHIPUAI_API_KEY=[Get from: https://open.bigmodel.cn]
DASHSCOPE_API_KEY=[Get from: https://dashscope.aliyun.com]
MINIMAX_API_KEY=[Get from: https://platform.minimaxi.com]
```

### NVIDIA NIM — 10 Rotating Keys (Recommended)
```env
NVIDIA_API_KEY=[Get from https://build.nvidia.com]
NVIDIA_API_KEY_B through NVIDIA_API_KEY_J=[9 additional keys for load balancing]
```

**Status:** At least one AI provider key is required. NVIDIA NIM recommended for cost optimization.

---

## 🟡 Lead Discovery (1/1 Required)

```env
GOOGLE_MAPS_API_KEY=[Get from: https://console.cloud.google.com]
```

**Purpose:** Location enrichment for lead data
**Setup:** Enable Maps JavaScript API in Google Cloud Console

---

## 🟡 Payments (6 total, 1 required)

### Stripe (Primary — Required)
```env
STRIPE_SECRET_KEY=[Get from: https://dashboard.stripe.com → API Keys]
STRIPE_PUBLISHABLE_KEY=[Get from: https://dashboard.stripe.com → API Keys]
STRIPE_WEBHOOK_SECRET=[Get from: https://dashboard.stripe.com → Webhooks → Signing Secret]
```

### PayPal (Optional)
```env
PAYPAL_ENABLED=false [or true to enable]
PAYPAL_CLIENT_ID=[Get from: https://developer.paypal.com]
PAYPAL_CLIENT_SECRET=[Get from: https://developer.paypal.com]
PAYPAL_MODE=sandbox [or 'live' for production]
```

### Wise (Optional — International Transfers)
```env
WISE_API_KEY=[Get from: https://wise.com/developers]
```

### Bank Transfer (Optional)
```env
BANK_ACCOUNT_NAME=Aliyar Solutions
BANK_ACCOUNT_NUMBER=[Your bank account number]
BANK_SORT_CODE=[UK sort code format: XX-XX-XX]
BANK_IBAN=[IBAN for EU/International transfers]
```

**Status:** Stripe is required. Others optional based on payment methods.

---

## 🟡 Email / SES (8 total, 3 required for production)

### AWS SES (Primary — Recommended)
```env
OUTBOUND_EMAIL_PROVIDER=ses
SES_FROM_EMAIL=[e.g., outbound@aliyarsolutions.com — must be verified in SES]
SES_FROM_NAME=[e.g., Aliyar Solutions]
SES_REPLY_TO_EMAIL=[e.g., hello@aliyarsolutions.com — for inbound routing]
SES_REGION=ap-south-2 [or your AWS region]
SES_CONFIGURATION_SET=[Optional — create in AWS SES for tracking]
SMTP_HOST=email-smtp.[region].amazonaws.com
SMTP_PORT=587
SMTP_SECURE=false
```

### Gmail (Optional — Fallback/Legacy)
```env
GMAIL_ADDRESS=[e.g., jarvis@aliyarsolutions.com]
GMAIL_APP_PASSWORD=[Generate in Gmail Security → App Passwords]
```

### Additional Email Settings
```env
EXECUTIVE_EMAIL_NAME=Joseph David [Outbound identity]
EXECUTIVE_EMAIL_TITLE=Executive Director
EXECUTIVE_EMAIL_ADDRESS=joseph.david@aliyarsolutions.com
OUTREACH_PERSONALIZE_ON_SEND=true [Personalize outreach emails]
EMAIL_REPLY_TO_NAME=[Optional — replier name for emails]
```

**Status:** SES required for production. Gmail optional as fallback.

---

## 🟢 WhatsApp / Evolution (5/5 Configured)

```env
EVOLUTION_API_URL=http://evolution:8080 [Docker] or https://[your-url] [Production]
EVOLUTION_API_KEY=[Get from: https://evolution-api.com]
EVOLUTION_PUBLIC_URL=https://aliyarsolutions.com/evolution [Public webhook endpoint]
WHATSAPP_ENABLED=true
WHATSAPP_INSTANCE_NAME=jarvis-main
WHATSAPP_DISPLAY_IDENTITY=Joseph David [Sender name on WhatsApp]
WHATSAPP_CAPTAIN_PHONE=+[Captain phone number]
WHATSAPP_AUTO_REPLY_ENABLED=false [Enable auto-replies]
WHATSAPP_AUTO_REPLY_MIN_CONFIDENCE=0.85 [Confidence threshold]
```

---

## 🟢 Notifications (4 total, 2 configured)

### Slack (Optional)
```env
SLACK_WEBHOOK_URL=[Get from: https://api.slack.com/messaging/webhooks]
```

**Setup:**
1. Go to your Slack workspace settings
2. Create app → Incoming Webhooks
3. Copy webhook URL

### Telegram (Optional)
```env
TELEGRAM_BOT_TOKEN=[Get from: @BotFather on Telegram]
TELEGRAM_CHAT_ID=[Get Captain's chat ID]
TELEGRAM_WEBHOOK_SECRET=[Optional — for header validation]
```

**Setup:**
1. Message @BotFather on Telegram
2. `/newbot` → create JARVIS bot
3. Copy token
4. Chat with bot, get chat ID from API response

---

## 🔴 Connectors (5 total, Optional)

```env
HUBSPOT_API_KEY=[Get from: HubSpot Settings → Integrations]
APOLLO_API_KEY=[Get from: Apollo Settings → API Keys]
NOTION_API_KEY=[Get from: Notion Settings → Integrations]
TWILIO_ACCOUNT_SID=[Get from: https://www.twilio.com/console]
TWILIO_AUTH_TOKEN=[Get from: https://www.twilio.com/console]
TWILIO_PHONE_NUMBER=[Your Twilio number]
```

---

## 🟡 n8n Automation (2 configured, 1 optional)

```env
N8N_BASE_URL=https://automation.aliyarsolutions.com
N8N_WEBHOOK_URL=https://automation.aliyarsolutions.com/webhook
N8N_API_KEY=[Get from: n8n Settings → API Key] [Optional]
```

---

## 🟡 GitHub Bridge (4 total, 1 missing)

```env
GITHUB_TOKEN=[Get from: GitHub → Settings → Developer → PAT]
GITHUB_REPO_OWNER=syedabrarfff-stack
GITHUB_REPO_NAME=devops-docker-project
GITHUB_BRIDGE_BRANCH=claude/jarvis-cans-api-integration-ZThTD
```

**Setup:** Generate Personal Access Token with `repo` and `workflow` permissions

---

## 🔴 AWS (12 total, optional for Phase 3+)

```env
USE_AWS=false [Set true for production]
AWS_REGION=ap-south-2 [Hyderabad primary]
AWS_BACKUP_REGION=ap-south-1 [Mumbai backup]
AWS_ACCESS_KEY_ID=[Get from: AWS IAM → Access Keys]
AWS_SECRET_ACCESS_KEY=[Get from: AWS IAM → Access Keys]
AWS_SESSION_TOKEN=[Optional — for temporary credentials]
AWS_S3_BUCKET=[Your S3 bucket name]
S3_BACKUP_BUCKET=[Backup bucket name]
AWS_ECS_CLUSTER=[Your ECS cluster name]
AWS_ECS_SERVICE=[Your ECS service name]
BEDROCK_API_KEY=[Optional — for AWS Bedrock models]
```

---

## 🟢 Grafana & Monitoring (3/3 Configured)

```env
GRAFANA_ADMIN_USER=captain
GRAFANA_ADMIN_PASSWORD=[Grafana admin password]
LOG_LEVEL=INFO [DEBUG, INFO, WARNING, ERROR, CRITICAL]
```

---

## 🎯 Priority Setup by Phase

### Phase 1: Local Development ✅
All variables already configured in `.env`. Start with:
```bash
docker compose up -d
./start-all.sh
```

### Phase 2: MVP Deployment 🟡
Before launching first customer, obtain:
1. STRIPE_WEBHOOK_SECRET
2. AWS SES setup (SES_FROM_EMAIL, SES_REPLY_TO_EMAIL)
3. GITHUB_TOKEN
4. GMAIL_APP_PASSWORD (fallback)
5. TELEGRAM_WEBHOOK_SECRET (optional)

### Phase 3: Production AWS 🔴
Before scaling beyond single server:
1. AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
2. AWS_ECS_CLUSTER / AWS_ECS_SERVICE
3. All backup/DR credentials
4. Certificate manager setup

---

## 🔒 Security Checklist

- [ ] .env is in .gitignore
- [ ] .env never committed to Git
- [ ] All secrets stored only locally
- [ ] Backup .env encrypted offline
- [ ] .env permissions: 600 (read-only to user)
- [ ] Production uses AWS Secrets Manager
- [ ] API keys rotated every 90 days
- [ ] No secrets in logs or error messages
- [ ] All third-party APIs have IP whitelisting
- [ ] CloudWatch alarms on API quota breaches

---

## 📝 How to Use This File

**For Local Development:**
Copy to your `.env` and fill in values from private credentials storage

**For New Team Member Onboarding:**
Share this file (NO secrets). They provide their own credentials for services they manage.

**For Production Deployment:**
Use AWS Secrets Manager + this file as reference for which variables are needed

**For Auditing:**
Compare your `.env` structure against this guide monthly

---

## 🆘 If You Lose Your .env

1. Check encrypted backup on personal device
2. Regenerate SECRET_KEY (new HS256)
3. Rotate all API keys that were compromised
4. Check CloudTrail logs for unauthorized access
5. Update Captain about the incident

**Prevention:** Keep automated encrypted backups of `.env` on personal storage

---

**Last Updated:** 2026-07-02  
**Location in Repo:** `/Headquarters/Environment/ENV_VARIABLES_GUIDE.md`  
**For Actual Secrets:** See your local `.env` file (never in Git)
