# JARVIS — REVENUE STATE
_Live financial pulse. Update every session. Captain reads this first thing each morning._

## Current MRR
**$0** — Pre-revenue. Infrastructure complete. Acquisition phase active.

## Pipeline Value

| Stage | Count | Value |
|-------|-------|-------|
| Leads in system | 0 | — |
| Proposals sent | 0 | — |
| Contracts out | 0 | — |
| Active clients | 0 | $0/month |
| **Total Pipeline** | | **$0** |

_Query live: GET /api/v1/revenue/pipeline_
_Query MRR: GET /api/v1/revenue/mrr_

## Revenue Systems (All Built, Ready)

### Auto-Invoice System
- Route: POST /api/v1/governance/invoices
- Auto-emails client via SES on creation
- Format: ALY-YYYYMM-XXXX
- Status flow: draft → sent → paid
- Stripe payment link: attached when payment intent created

### Auto-Proposal System
- Route: POST /api/v1/governance/proposals/generate
- AI-generated (claude-opus → gpt-4o fallback)
- Styles: standard, case_study, short_urgent, social_proof
- Auto-emails full proposal content to client
- Includes: Cost of Inaction section + outcome framing
- Signed by: matched team member from team_service.py

### Auto-Contract System
- Route: POST /api/v1/governance/contracts
- Triggered: automatically when proposal marked "accepted" or "won"
- AI-generated 10-section service agreement
- Auto-emails contract to client with "reply ACCEPTED" CTA

### Stripe Integration
- Route: POST /api/v1/payments/create-link
- Creates payment link for invoiced amount
- Webhook: POST /api/v1/payments/webhook (STRIPE_WEBHOOK_SECRET required)
- Handles: payment_intent.succeeded → marks invoice as paid

### Trust Engine (Conversion Acceleration)
- Brief generation: POST /api/v1/trust/briefs/generate
- Engagement tracking: POST /api/v1/trust/engagement
- Score retrieval: GET /api/v1/trust/score/{lead_id}
- Referral generation: POST /api/v1/trust/referrals/generate

## Financial Targets

| Phase | MRR Target | Timeline |
|-------|-----------|----------|
| Phase 1 | Infrastructure built | COMPLETE |
| Phase 2 | $10,000–$30,000/month | 3–6 months post-launch |
| Phase 3 | $50,000+/month | 12 months (white-label) |
| Phase 4 | $1M–$5M valuation | 24–36 months |

## Payment Infrastructure

### Stripe (Primary)
- Payment links for invoices
- Recurring subscriptions for retainers
- Webhook secret: set in AWS Secrets Manager (PENDING — Captain action)

### PayPal (Legacy)
- Available for international clients who prefer it
- Route: POST /api/v1/payments/paypal

### Wise (International)
- Bank transfer for large international payments
- Route: POST /api/v1/payments/bank-transfer

## Revenue Operations Checklist

Before first client goes live, Captain must:
- [ ] Set STRIPE_WEBHOOK_SECRET in AWS Secrets Manager
- [ ] Verify SES production access (sandbox → production)
- [ ] Configure Stripe account (business details, bank)
- [ ] Test invoice → payment flow end-to-end
- [ ] Test proposal → contract → client record flow

## Invoice Archive
_No invoices issued yet. First invoice will be ALY-YYYYMM-XXXX format._
_Query: GET /api/v1/governance/invoices_

## Scheduled Revenue Intelligence

| Job | Schedule | Output |
|-----|----------|--------|
| weekly_pipeline_health | Sunday 20:00 | MRR forecast, deal velocity |
| daily_morning_briefing | 07:00 | Pipeline summary for Captain |
| daily_lead_score | 02:00 | Updated trust scores, hot leads |
