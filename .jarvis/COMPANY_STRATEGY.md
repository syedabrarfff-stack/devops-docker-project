# JARVIS — COMPANY STRATEGY
_12-month execution plan. Tactical and specific. Update quarterly._

## Current Priority: First Client Acquisition

Everything else is secondary until we have paying clients.

### Immediate Unblocking Actions (Captain Only)

| Action | Why | Urgency |
|--------|-----|---------|
| Terraform apply | Deploys AWS infrastructure | CRITICAL |
| Attach AdministratorAccess to JarvisGitHubActionsRole | CI/CD cannot push to ECR without it | CRITICAL |
| Point aliyarsolutions.com → ALB DNS | Production URL won't resolve | CRITICAL |
| Set STRIPE_WEBHOOK_SECRET | Payments won't confirm | HIGH |
| Merge PR → ECS deploy | Backend not live on production | CRITICAL |
| Register Telegram webhook | Captain won't receive alerts | HIGH |
| SES production access | Emails stuck in sandbox | HIGH |

### After Infrastructure Live: First 90 Days

**Month 1 — Outreach**
- Apollo sync: import 50–100 qualified leads into CRM
- Apollo route: POST /api/v1/sync/apollo
- Activate daily_lead_score job → trust scoring begins
- Target: 20 leads with trust_score ≥ 40 (ready for proposal)

**Month 1–2 — Trust-First Engagement**
- For each qualified lead:
  1. Generate Executive Opportunity Brief (POST /api/v1/trust/briefs/generate)
  2. Send brief as first touchpoint (via Darren Mitchell persona)
  3. Track engagement events (email open, reply, demo watch)
  4. Watch for trust_score ≥ 40 trigger
  5. Auto-generate proposal when threshold hit

**Month 2–3 — Close and Deliver**
- Proposal accepted → contract auto-generated → signed → client created
- Welcome email auto-sent → delivery begins
- Monthly reporting scheduled
- Referral engine activated at 60-day delivery mark

### Service Strategy — What to Lead With

**Lead service (easiest to sell, fastest to deliver):**
AI Workflow Automation — $2,000–$3,500/month
- Every business has manual workflows
- Visible ROI within 30 days
- Low technical risk
- Easy to scope: "what takes your team the most time manually?"

**Upsell service (after trust established):**
Cloud Infrastructure & CI/CD — $1,500–$3,000/month add-on
- Clients who already trust us hand over their tech stack
- Recurring: always growing

**Premium service (for qualified enterprise):**
Full AI Operations Stack — $6,000–$10,000/month
- CRM + Automation + Cloud + Intelligence
- Target: agencies, logistics companies, SaaS startups

### Outreach Strategy

**Channel 1: LinkedIn**
- Captain posts 3x/week: insights on AI automation, cloud, operational intelligence
- Positions as thought leader before reaching out
- Darren Mitchell sends connection requests to warm leads

**Channel 2: Cold Email (Apollo sequences)**
- Sequence: Brief → Follow-up → Case study → Soft close → Final
- Route: POST /api/v1/outreach/sequences + POST /api/v1/outreach/enroll

**Channel 3: Referral Engine**
- After first 2–3 clients deliver results
- Referral request generated automatically: POST /api/v1/trust/referrals/generate

**Channel 4: Agency Partnerships**
- Target: digital marketing agencies without technical delivery capability
- Offer: white-label our infrastructure under their brand
- Revenue: 30–40% of client value, zero delivery effort for them

### Competitive Positioning

When asked "why Aliyar Solutions over [agency/freelancer/big firm]?"

**vs. Freelancer:** "You're getting a full team, not a single person. When your developer gets sick, we don't stop."

**vs. Agency:** "We don't hand you a strategy deck. We build and run your systems. Our team stays on indefinitely."

**vs. Big firm:** "Same quality infrastructure. 10x faster delivery. No enterprise markup."

**vs. In-house hire:** "Junior developer costs $4,000–$6,000/month. Senior costs $8,000–$12,000/month. Neither has our breadth. Our team costs $2,500/month."

### Intelligence Operations (Weekly)

| Monday | Tuesday | Wednesday | Thursday | Friday |
|--------|---------|-----------|----------|--------|
| Tech radar scan | Outreach review | Pipeline health check | Lead scoring | Weekly briefing to Captain |
| New leads qualified | Proposals in flight | Contracts pending | Trust scores updated | Strategy adjustment |

### Content & Positioning (Long Game)

- Case studies published after first 3 client results
- Technical blog: JARVIS building in public (selective disclosure)
- LinkedIn articles: "How we built X for client in 48 hours"
- No pricing pages — discovery call gated
- Website: aliyarsolutions.com → conversion-focused landing page only

### North Star Metric

**Time to value for a new lead** = time from first contact → first deliverable received

Target: 7 days from signed contract to first working automation/deployment
Current baseline: not yet measured (no clients)

Every operational improvement we make is measured against this metric.
