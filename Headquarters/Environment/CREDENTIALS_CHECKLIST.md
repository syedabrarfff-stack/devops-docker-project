# JARVIS Credentials Setup Checklist

**Current Status:** `.env` file created with auto-populated values  
**What's Missing:** 17 personal credentials (5 critical for MVP)  
**Time to Complete:** 2-3 hours (depending on service setup times)

---

## 🟢 Already Configured (25 Auto-Populated Variables)

These are set in `.env` and ready to use:

✅ Application Core (8 vars):
- DEBUG, SECRET_KEY, CAPTAIN_PASSWORD, CAPTAIN_USERNAME
- CORS_ORIGINS, APP_BASE_URL, JARVIS_DEFAULT_TENANT_ID

✅ Database (4 vars):
- DATABASE_URL, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

✅ Redis (2 vars):
- REDIS_URL, REDIS_PASSWORD

✅ Google Maps (1 var):
- GOOGLE_MAPS_API_KEY

✅ Payments — Stripe Test (2 vars):
- STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY

✅ Evolution API / WhatsApp (5 vars):
- EVOLUTION_API_KEY, EVOLUTION_API_URL, WHATSAPP_ENABLED
- WHATSAPP_INSTANCE_NAME, WHATSAPP_DISPLAY_IDENTITY

✅ Notifications (3 vars):
- SLACK_WEBHOOK_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

✅ Email (1 var):
- GMAIL_ADDRESS

✅ GitHub (3 vars):
- GITHUB_REPO_OWNER, GITHUB_REPO_NAME, GITHUB_BRIDGE_BRANCH

✅ Grafana (3 vars):
- GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD

✅ Monitoring (1 var):
- LOG_LEVEL

✅ n8n (2 vars):
- N8N_BASE_URL, N8N_WEBHOOK_URL

---

## 🔴 CRITICAL FOR MVP (5 Items — ~1 Hour Total)

**Must complete these before launching first customer:**

### 1. ANTHROPIC_API_KEY — AI Provider (Needed NOW)
**Priority:** 🔴 CRITICAL  
**Time:** 2-3 minutes  
**Use Case:** Claude models (Haiku, Sonnet, Opus) — primary AI reasoning

**Steps:**
```
1. Go to: https://console.anthropic.com
2. Sign in or create account
3. Click "API Keys" (left sidebar)
4. Click "Create Key"
5. Name: JARVIS Development
6. Copy the key (starts with "sk-ant-api03-")
7. Paste into .env:
   ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXX...
```

**Verify:**
```bash
curl -H "Authorization: Bearer sk-ant-api03-..." \
  https://api.anthropic.com/v1/models \
  | jq .data[0].id
# Should return a model ID
```

**Cost:** First $5 free, then pay-as-you-go (typically $0.10-$5/month for MVP)

---

### 2. STRIPE_WEBHOOK_SECRET — Payment Verification (Needed NOW)
**Priority:** 🔴 CRITICAL  
**Time:** 5 minutes  
**Use Case:** Verify payment events (invoice paid, charge refunded)

**Steps:**
```
1. Go to: https://dashboard.stripe.com
2. Make sure you're in TEST MODE (bottom left)
3. Click "Webhooks" (left sidebar)
4. Click "Add endpoint"
5. URL: https://aliyarsolutions.com/api/v1/webhooks/stripe
6. Events to send:
   ☑ payment_intent.succeeded
   ☑ invoice.payment_succeeded
   ☑ charge.refunded
7. Click "Add endpoint"
8. Click the newly created endpoint
9. Scroll down: "Signing secret" (starts with "whsec_")
10. Copy the secret
11. Paste into .env:
    STRIPE_WEBHOOK_SECRET=whsec_XXXXXXXX...
```

**Verify:**
```bash
# Check backend logs for webhook signature validation:
docker compose logs -f backend | grep -i "stripe.*webhook"
# Should show successful validation when test payment occurs
```

**Cost:** 2.9% + $0.30 per transaction (only charged on real payments)

---

### 3. AWS SES Setup — Email Sending (Needed in 24-48 hours)
**Priority:** 🔴 CRITICAL  
**Time:** 30 minutes (+ 24h for domain verification)  
**Use Case:** Outbound email (lead outreach, invoice notifications)

**3a. Create AWS SES Sender Identity**
```
1. Go to: https://console.aws.amazon.com/ses
2. Make sure region = ap-south-2 (Hyderabad)
3. Click "Verified identities" or "Send email" → "Create identity"
4. Type: Domain (not Email address)
5. Enter: aliyarsolutions.com
6. Click "Create identity"
7. Copy the 4 CNAME records shown
```

**3b. Verify Domain (On Your Domain Registrar)**
```
1. Log in to your domain registrar (GoDaddy, Namecheap, etc.)
2. Go to DNS settings
3. Add 4 CNAME records from Step 3a above
4. Wait 10 minutes to 1 hour for DNS propagation
5. Go back to AWS SES
6. Should show "Verified" status
```

**3c. Create SMTP Credentials (For Application)**
```
1. In AWS SES, click "SMTP settings" (left sidebar)
2. Click "Create SMTP credentials"
3. Username: jarvis-smtp (or any name)
4. Click "Create"
5. Download credentials.csv or copy:
   Username: [AWS-SMTP-USERNAME]
   Password: [AWS-SMTP-PASSWORD]
```

**3d. Create Configuration Set (For Tracking)**
```
1. In AWS SES, click "Configuration sets"
2. Click "Create configuration set"
3. Name: jarvis-notifications
4. Click "Create configuration set"
5. Optional: Add delivery tracking rules
```

**3e. Update .env**
```
SES_FROM_EMAIL=outbound@aliyarsolutions.com
SES_FROM_NAME=Aliyar Solutions
SES_REPLY_TO_EMAIL=hello@aliyarsolutions.com
SES_CONFIGURATION_SET=jarvis-notifications
SES_REGION=ap-south-2
# SMTP credentials are used for SMTP_HOST/PORT/authentication
```

**3f. Configure Inbound Email (Optional But Recommended)**
```
1. In AWS SES, click "Inbound email" or "Create receipt rule"
2. Configure MX records to route inbound to SES
3. Set up receipt rule to forward replies to backend webhook
4. This allows capture of client replies from your outreach emails
```

**Verify:**
```bash
# Test sending email via SES
docker compose logs backend | grep -i "ses.*email"
# Should show email sent successfully
```

**Cost:** $0.10 per 1,000 emails (very cheap for MVP)

---

### 4. GITHUB_TOKEN — Scout Network Integration (Needed for daily lead discovery)
**Priority:** 🟡 HIGH (Blocks scout network)  
**Time:** 10 minutes  
**Use Case:** Daily lead discovery automation (scout agents push leads to jarvis-data/)

**Steps:**
```
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Fine-grained personal access token"
3. Token name: JARVIS Scout Network
4. Expiration: 90 days
5. Resource owner: syedabrarfff-stack
6. Repository access: 
   ☑ Only select repositories
   ☑ syedabrarfff-stack/devops-docker-project
7. Repository permissions:
   ☑ Contents (Read & Write)
   ☑ Workflows (Read & Write)
8. Click "Generate token"
9. Copy token (starts with "github_pat_")
10. Paste into .env:
    GITHUB_TOKEN=github_pat_XXXXXXXX...
```

**What This Does:**
- Every day at 01:30 UTC: 9 scout agents search for high-ICP leads
- Results automatically pushed to `jarvis-data/leads_YYYY-MM-DD.json`
- No manual work needed — fully automated

**Verify:**
```bash
# Check if scout network job is scheduled:
curl http://localhost:8000/api/v1/scheduler/jobs | jq '.[] | select(.name=="daily_scout_network")'
# Should show job with next_run_time

# Check if token works:
curl -H "Authorization: token github_pat_XXXX" \
  https://api.github.com/user | jq .login
# Should show your GitHub username
```

**Cost:** Free (GitHub doesn't charge for PATs)

---

### 5. GMAIL_APP_PASSWORD — Fallback Email (Optional for MVP)
**Priority:** 🟢 OPTIONAL (Fallback only)  
**Time:** 5 minutes  
**Use Case:** Fallback email if SES fails

**Only needed if you want Gmail as backup. Skip if confident in SES.**

**Steps:**
```
1. Enable 2-factor authentication on Gmail (required)
2. Go to: https://myaccount.google.com/apppasswords
3. Select device: "Mail"
4. Select OS: "Other (custom name)" → "JARVIS"
5. Click "Generate"
6. Copy 16-character password (no spaces)
7. Paste into .env:
   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

**Cost:** Free (Gmail API)

---

## 🟡 OPTIONAL FOR MVP (Secondary Credentials)

These don't block launch but add functionality:

### Optional: Alternative AI Providers
**Priority:** 🟢 OPTIONAL  
**Time:** 5 minutes each  
**Use Case:** Fallback routing if Claude unavailable

- **OPENAI_API_KEY** (ChatGPT/GPT-4o): Get from https://platform.openai.com/api-keys
- **DEEPSEEK_API_KEY**: Get from https://platform.deepseek.com
- **GROQ_API_KEY**: Get from https://console.groq.com
- **MISTRAL_API_KEY**: Get from https://console.mistral.ai
- **MOONSHOT_API_KEY**: Get from https://platform.moonshot.cn
- **ZHIPUAI_API_KEY** (GLM): Get from https://open.bigmodel.cn
- **DASHSCOPE_API_KEY** (Qwen): Get from https://dashscope.aliyun.com
- **MINIMAX_API_KEY**: Get from https://platform.minimaxi.com

**Note:** NVIDIA NIM keys already provided for cost optimization

### Optional: CRM & Integrations
**Priority:** 🟢 OPTIONAL  
**Time:** 10 minutes each  
**Use Case:** Advanced lead enrichment

- **HUBSPOT_API_KEY**: Get from HubSpot Settings → Integrations
- **APOLLO_API_KEY**: Get from Apollo Settings → API Keys
- **NOTION_API_KEY**: Get from Notion Settings → Integrations
- **TWILIO_ACCOUNT_SID/AUTH_TOKEN**: Get from https://www.twilio.com/console

### Optional: PayPal (If Enabling PayPal Payments)
**Priority:** 🟢 OPTIONAL  
**Time:** 15 minutes  
**Use Case:** Alternative payment method

1. Go to: https://developer.paypal.com
2. Log in or create account
3. Create app in Sandbox environment
4. Copy Client ID & Secret
5. Set in .env:
   ```
   PAYPAL_ENABLED=true
   PAYPAL_CLIENT_ID=AXxxxxxxxx...
   PAYPAL_CLIENT_SECRET=EHxxxxxxxx...
   PAYPAL_MODE=sandbox
   ```

### Optional: Wise API (International Transfers)
**Priority:** 🟢 OPTIONAL  
**Time:** 10 minutes  
**Use Case:** Currency conversion & international payouts

1. Go to: https://wise.com/developers
2. Create API token
3. Set in .env:
   ```
   WISE_API_KEY=your_wise_api_key
   ```

---

## 🔴 PRODUCTION DEPLOYMENT (Phase 3+ — AWS)

**Not needed for MVP. Only for scaling production.**

### Required for Production:
- **AWS_ACCESS_KEY_ID** & **AWS_SECRET_ACCESS_KEY**
  - Get from: AWS IAM → Access Keys
  - Use case: ECS, RDS, S3 deployment
  - Time: 30 minutes

- **AWS_ECS_CLUSTER** & **AWS_ECS_SERVICE**
  - Create in AWS Console
  - Set up after infrastructure provisioning
  - Time: 2-3 hours

- **Bank Account Details** (if enabling bank transfers)
  - BANK_ACCOUNT_NUMBER
  - BANK_SORT_CODE (UK) or BANK_IBAN (EU)
  - Time: 10 minutes

- **SSL Certificate**
  - Already auto-provisioned by Certbot (in docker-compose.yml)
  - Set LETSENCRYPT_EMAIL in production

---

## ✅ Checklist: Do This Now (MVP Readiness)

### Step 1: Get Anthropic API Key (2 min)
- [ ] Visit https://console.anthropic.com
- [ ] Create API key
- [ ] Copy to .env: ANTHROPIC_API_KEY=...
- [ ] Verify with: `curl -H "Authorization: Bearer sk-ant-..." https://api.anthropic.com/v1/models | jq .`

### Step 2: Get Stripe Webhook Secret (5 min)
- [ ] Visit https://dashboard.stripe.com/webhooks
- [ ] Create endpoint for https://aliyarsolutions.com/api/v1/webhooks/stripe
- [ ] Select payment events (payment_intent.succeeded, invoice.payment_succeeded, charge.refunded)
- [ ] Copy Signing Secret to .env: STRIPE_WEBHOOK_SECRET=whsec_...
- [ ] Verify with test payment

### Step 3: Set Up AWS SES (30 min + 24h wait)
- [ ] Go to https://console.aws.amazon.com/ses
- [ ] Verify domain: aliyarsolutions.com
- [ ] Add CNAME records to domain registrar
- [ ] Wait for "Verified" status (1-24 hours)
- [ ] Create SMTP credentials
- [ ] Copy to .env: SES_FROM_EMAIL, SES_FROM_NAME, SES_REPLY_TO_EMAIL
- [ ] Optional: Create configuration set jarvis-notifications

### Step 4: Create GitHub Token (10 min)
- [ ] Visit https://github.com/settings/tokens
- [ ] Create Fine-grained PAT
- [ ] Select repository: syedabrarfff-stack/devops-docker-project
- [ ] Permissions: Contents (R+W), Workflows (R+W)
- [ ] Copy to .env: GITHUB_TOKEN=github_pat_...
- [ ] Verify with: `curl -H "Authorization: token github_pat_..." https://api.github.com/user | jq .login`

### Step 5: Optional — Gmail App Password (5 min)
- [ ] Enable 2FA on Gmail
- [ ] Visit https://myaccount.google.com/apppasswords
- [ ] Create "JARVIS" app password
- [ ] Copy to .env: GMAIL_APP_PASSWORD=...

---

## 🚀 Launch Readiness (After Checklist Complete)

**Once you've completed all 5 items above:**

```bash
# 1. Start the full stack
docker compose down
docker compose up -d
./start-all.sh

# 2. Verify all services healthy
docker compose ps | grep -c "healthy"
# Should show 17

# 3. Test API endpoints
curl http://localhost:8000/health | jq .
curl http://localhost:8000/api/v1/ai-ops/health | jq .

# 4. Access dashboards
# Control Room: http://localhost:3002/control-room (captain/captain)
# Grafana: http://localhost:3001 (captain/captain)

# 5. Test email sending (optional)
curl -X POST http://localhost:8000/api/v1/email/test \
  -H "Content-Type: application/json" \
  -d '{"to": "test@example.com"}'

# 6. Check scout network scheduled
curl http://localhost:8000/api/v1/scheduler/jobs | jq '.[] | select(.name=="daily_scout_network")'
```

**Result:** MVP production-ready ✅

---

## 📋 Quick Reference Table

| Credential | Needed? | Priority | Time | Cost | Get From |
|---|---|---|---|---|---|
| ANTHROPIC_API_KEY | ✅ | 🔴 NOW | 2 min | $0-5/mo | https://console.anthropic.com |
| STRIPE_WEBHOOK_SECRET | ✅ | 🔴 NOW | 5 min | Free | https://dashboard.stripe.com |
| SES_FROM_EMAIL | ✅ | 🔴 NOW | 30 min | $0.10/1k | https://console.aws.amazon.com/ses |
| GITHUB_TOKEN | ✅ | 🔴 NOW | 10 min | Free | https://github.com/settings/tokens |
| GMAIL_APP_PASSWORD | ❌ | 🟡 Optional | 5 min | Free | https://myaccount.google.com/apppasswords |
| Alt AI Keys | ❌ | 🟢 Optional | 5 min each | Varies | Various (OpenAI, DeepSeek, etc.) |
| AWS (Phase 3+) | ❌ | 🔴 Future | 30 min | $800-1k/mo | https://console.aws.amazon.com |

---

## 🆘 If You Get Stuck

**Problem:** "Anthropic API returns 401 Unauthorized"
→ Make sure you copied the full key (sk-ant-api03-...)
→ Check API key isn't expired

**Problem:** "Stripe webhook test fails"
→ Make sure webhook URL is exactly: https://aliyarsolutions.com/api/v1/webhooks/stripe
→ Check backend is running: docker compose logs -f backend | grep stripe

**Problem:** "Email not sending via SES"
→ Verify domain is "Verified" in AWS SES console
→ Check SES_FROM_EMAIL is verified email/domain
→ Ensure SES_REGION matches where domain verified

**Problem:** "GitHub token has insufficient permissions"
→ Make sure PAT is Fine-grained (not classic)
→ Verify Contents & Workflows both have Read+Write
→ Confirm repository syedabrarfff-stack/devops-docker-project is selected

---

## ✨ Final Note

**Your `.env` file is now created and safe:**
- ✅ Never committed to Git (.gitignore active)
- ✅ Contains only auto-populated values + clear TODOs
- ✅ Ready to receive credentials as you gather them
- ✅ Fully functional with just ANTHROPIC_API_KEY added

**Next step:** Get ANTHROPIC_API_KEY (2 minutes) and start using JARVIS!

---

**Created:** 2026-07-02  
**Location:** `/home/user/devops-docker-project/.env`  
**Status:** Ready for MVP credentials (17 items: 5 critical, 12 optional)
