# JARVIS ACTIVATION PATH — From Blocked to First Client

**Goal:** First live outreach sent within 24 hours.

---

## CURRENT STATE

| Component | Status | Blocker |
|---|---|---|
| Backend Code | ✅ Complete | — |
| SES Transport | ✅ Built | DNS records added, awaiting verification |
| WhatsApp Transport | ✅ Built | Device restriction on pairing |
| Outreach Engine | ✅ Ready | Blocked on SES verification |
| Reply Handler | ✅ Ready | Blocked on SES inbound receipt rule |

---

## SES UNBLOCK (Parallel — do first)

### Step 1: Verify DNS Propagation (~10 min)

**Run diagnostic:**
```bash
chmod +x scripts/diagnose-ses.sh
./scripts/diagnose-ses.sh
```

**What we're looking for:**
- ProductionAccessEnabled: `true` → skip Step 2
- ProductionAccessEnabled: `false` → proceed to Step 2
- DKIM records showing as CNAME → domain is verified, skip to Step 3

**If DNS records not yet propagating:**
- GoDaddy DNS changes take 15–60 min
- Run diagnostic again in 10 min
- OR: Flush local DNS: `sudo systemctl restart systemd-resolved` (Linux)

### Step 2: Request Production Access (1–24 hours, usually same-day)

**AWS Console → SES (ap-south-2) → Account Dashboard:**

```
Use case:        Transactional business outreach
Domain:          aliyarsolutions.com
Weekly volume:   500 emails
Website:         https://aliyarsolutions.com
```

**Expected:** AWS approves within hours. Check email for confirmation.

### Step 3: Create SES Receipt Rule for Inbound (5 min, after domain verified)

**AWS Console → SES → Email Receiving → Rule Sets:**

```
Name:              jarvis-inbound-email
Recipient filter:  joseph.david@aliyarsolutions.com (or leave blank for all)
Action:            SNS
SNS topic:         Create new: jarvis-inbound-email

SNS subscription:  
  Protocol:        HTTPS
  Endpoint:        https://aliyarsolutions.com/api/v1/webhooks/email/inbound
  
Enable TLS:        Yes
```

**What happens:**
- SNS auto-confirms subscription on first email
- `POST /api/v1/webhooks/email/inbound` receives all inbound emails
- Replies are processed through full AIONX pipeline

---

## WHATSAPP UNBLOCK (Do this in parallel with SES)

### Root Cause: WhatsApp Device Restriction

**What this means:**
- Evolution API is running ✅
- Pairing code is generating ✅
- WhatsApp is rejecting the link ❌
- Meta/WhatsApp is blocking the device from linking

### Solution: Three-Path Unblock

**Path A: Try Different Device (Fastest — 5 min)**

If you have a tablet or second phone available:
```bash
# On the second device, open WhatsApp and:
1. Settings → Linked Devices
2. Scan QR code from: /api/v1/communication/whatsapp/qr
3. Confirm linking on phone

# If successful:
# - Delete Evolution instance on original device
# - Create new instance on tablet device
# - Run outreach from linked tablet
```

**Path B: Use WhatsApp Business Account (10 min)**

WhatsApp Business app has different device linking rules:

```bash
# On your phone:
1. Download "WhatsApp Business" (different app from regular WhatsApp)
2. Add account with +973 34360246
3. Settings → Linked Devices
4. Scan Evolution QR code

# Update Evolution config:
# WHATSAPP_DISPLAY_IDENTITY="Joseph David - Business"
```

**Path C: Request Device Unlink from Meta Support (1–24 hours)**

If +973 34360246 is linked to another device:

```
1. Go to: https://www.whatsapp.com/contact/
2. Describe: "Device unlink request for +973 34360246"
3. Meta reviews and unlinks within 24 hours
4. Then retry pairing with Evolution API
```

### Fastest Working Approach (Recommended)

**Given you said pairing is failing on the device:**

1. **Try Path A first** (different device) — instant answer
2. **If no other device available**, use Path B (Business app)
3. **If that fails**, use Path C (Meta support) while continuing with SES/testing

**Do NOT wait for WhatsApp if SES is ready.** Test outreach with email first.

---

## VALIDATION SEQUENCE (Start as soon as SES verified)

### Phase 1: Email Outreach Validation (1 day)

**Objective:** Send one email, receive one reply, verify full pipeline.

```
1. Create one test lead:
   POST /api/v1/leads/ with email = your-email@example.com

2. Queue outreach:
   POST /api/v1/outreach/queue with lead_id

3. Execute:
   POST /api/v1/outreach/execute

4. Check outreach log:
   GET /api/v1/outreach/logs

5. Receive reply at your email

6. Verify reply processing:
   GET /api/v1/communication/events?channel=EMAIL
   GET /api/v1/aionx/decision-memory (should show LEAD_REPLIED event)

7. Verify Digital Twin updated:
   GET /api/v1/aionx/client-twin/{client_id}

✅ Phase 1 Complete: Email pipeline works end-to-end
```

### Phase 2: WhatsApp Validation (parallel with Phase 1)

**Only after pairing succeeds.**

```
1. Send test WhatsApp:
   POST /api/v1/communication/whatsapp/send-text
   {
     "number": "+973XXXXXXXXX",  (your test number)
     "text": "JARVIS test message"
   }

2. Verify delivery:
   GET /api/v1/communication/status

3. Send reply from WhatsApp back to instance

4. Verify reply processing:
   GET /api/v1/communication/events?channel=WHATSAPP
   GET /api/v1/aionx/decision-memory (should show inbound WhatsApp event)

✅ Phase 2 Complete: WhatsApp pipeline works end-to-end
```

### Phase 3: Live Lead Outreach (1–2 days)

```
1. Import 5–10 real leads:
   POST /api/v1/discovery/google-maps (UK SaaS, score ≥75)
   OR
   POST /api/v1/leads/ (batch upload)

2. Queue all for outreach:
   POST /api/v1/outreach/queue

3. Execute daily:
   POST /api/v1/outreach/execute (automatic every 30 min after this)

4. Monitor dashboard:
   GET /api/v1/ops/status

5. When INTERESTED reply arrives:
   → Council convenes automatically
   → Captain notified
   → Proposal generated
   → Send proposal
   → Track signature

✅ Phase 3 Complete: First client acquisition validated
```

---

## TIMELINE TO FIRST CLIENT ACQUISITION

| Stage | Dependency | Time Estimate |
|---|---|---|
| SES domain verified | AWS | 15 min (DNS) + awaiting AWS |
| SES production access | AWS | 1–24 hrs (usually 2–4 hrs) |
| SES receipt rule live | AWS approval | 5 min after approval |
| Email validation complete | All of above + test | 30 min |
| **First outreach sent** | Phase 1 complete | **~2–6 hours from now** |
| WhatsApp pairing | Device/Meta | 5 min (Path A) to 24 hrs (Path C) |
| Live lead discovery | Manual/API | 10 min |
| **First reply received** | Leads exist + outreach sent | **24–48 hrs** |
| **First proposal generated** | Council + Gamma integration | **+4 hrs after reply** |
| **First client signed** | Proposal + negotiation | **+3–7 days** |

---

## CRITICAL PATH (Do This Now)

**In parallel:**

1. **Run SES diagnostic** → report exact status
2. **Check WhatsApp pairing** → try Path A (different device)
3. **Request SES production** → submit form if needed
4. **Prepare 5 test leads** → ready to import once SES is verified

**Once SES verified + email works:**
- Start Phase 1 immediately
- Do NOT wait for WhatsApp
- Email alone can complete first acquisition

**Parallel WhatsApp pairing while Phase 1 runs.**

---

## SUCCESS METRICS

| Milestone | Definition | Target Time |
|---|---|---|
| SES Live | Domain verified, prod access granted, receipt rule active | 6 hours |
| Email Validation | Outreach sent, reply received, processed through AIONX | 8 hours |
| First Real Outreach | 5+ leads queued, emails executing daily | 12 hours |
| First Reply | Inbound email from real prospect received | 24–48 hours |
| First Proposal | Council approved, Gamma deck generated, sent | +4 hours after reply |
| First Client | Signature received, marked as signed in CRM | +3–7 days |

---

## NEXT ACTION

Run diagnostics and report exact blockers:

```bash
chmod +x scripts/diagnose-ses.sh scripts/diagnose-whatsapp.sh
./scripts/diagnose-ses.sh > /tmp/ses-diagnostic.txt
./scripts/diagnose-whatsapp.sh > /tmp/wa-diagnostic.txt
cat /tmp/ses-diagnostic.txt
cat /tmp/wa-diagnostic.txt
```

Then tell me:
1. SES: ProductionAccessEnabled true/false? DKIM verified?
2. WhatsApp: Connection state? Can get QR/pairing code?
3. Which Path (A/B/C) is feasible for you right now?

**Do not build more code. Unblock the transports. Run the validation. Acquire the client.**
