# JARVIS — CLIENT MEMORY
_All active clients, leads, and deals. Update after every client interaction._
_Structured for any model to instantly understand the full client landscape._

## Active Clients
_None yet — Pre-revenue phase. First client acquisition is the primary operational objective._

## Pipeline (Leads in System)

### How to Query
```bash
# From backend container or local:
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/leads
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/revenue/clients
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/revenue/pipeline
```

### Lead Scoring System
- trust_score: 0–100 (computed from engagement events)
- conversion_probability: 0–100 (weighted from event types)
- ready_for_proposal: true when trust_score ≥ 40
- Event types tracked: email_opened(5), reply_received(20), meeting_attended(25), demo_watched(30), brief_viewed(15), proposal_viewed(20), technical_question(15), decision_maker_contacted(25), contract_viewed(35)

## Deal Templates (Pricing Reference)

### Tier 1 — Foundation ($2,000–$3,500/month retainer)
- AI automation setup (CRM, workflows, email)
- Cloud infrastructure (AWS basic, Docker, CI/CD)
- Monthly reporting + optimization
- Best for: SMBs, agencies, local enterprises

### Tier 2 — Growth ($4,000–$6,000/month retainer)
- Full AI automation stack
- Multi-environment AWS (prod + staging)
- Weekly intelligence briefings
- Dedicated team member (named)
- Best for: Growing startups, mid-market companies

### Tier 3 — Enterprise ($7,000–$15,000/month retainer)
- Custom AI systems and integrations
- Full cloud architecture (ECS/RDS/Redis/CDN)
- 24/7 system monitoring + SLA
- Executive dashboard access
- Best for: Tech companies, Series A+, enterprises

### Project Rates
- Discovery + Architecture: $3,000–$5,000
- Full MVP Build: $8,000–$15,000
- Migration + Re-architecture: $5,000–$12,000
- Security Audit + Hardening: $3,000–$6,000

## Client Communication Templates

### First Touchpoint (after lead scores ≥ 40)
From: Darren Mitchell (Client Acquisition Specialist)
Subject: Aliyar Solutions — [specific pain point observed]

### Proposal Delivery (auto-triggered via system)
From: [Team member matched to service type]
Subject: [Service Type] — [Company Name] — Aliyar Solutions Proposal

### Contract Delivery (auto-triggered on proposal accepted)
From: Syed Abrar (CEO) — via JARVIS automation
Subject: Service Agreement — [Company Name] × Aliyar Solutions

### Welcome (auto-triggered on client record creation)
From: Olivia Bennett (Account Coordinator)
Subject: Welcome to Aliyar Solutions — [Company Name]

## Relationship Intelligence (to fill as clients come in)

```
## [CLIENT COMPANY NAME]
- **Contact:** [Name, Title]
- **Email:** [email]
- **Status:** [lead/active/paused/churned]
- **Service:** [what we're building for them]
- **Monthly Value:** $X,XXX
- **Start Date:** [date]
- **Pain Points:** [3 specific things they mentioned]
- **Decision Maker:** [name + how they make decisions]
- **Communication Style:** [direct/formal/casual/data-driven]
- **Key Metrics They Care About:** [e.g., CAC, MRR, churn rate]
- **At-Risk Signals:** [anything that could cause churn]
- **Expansion Opportunities:** [what else they might need]
- **Last Touchpoint:** [date + summary]
- **Next Action:** [what JARVIS needs to do next]
```

## ICP (Ideal Client Profile)

**Primary ICP:** Technology-forward SMBs ($1M–$20M revenue) struggling with:
- Manual operations eating 10+ hours/week of leadership time
- Disconnected tools (CRM + Slack + email + spreadsheets)
- No CI/CD or infrastructure automation
- AI curiosity but no technical team to implement it

**Secondary ICP:** Digital agencies wanting to white-label our infrastructure to their own clients

**Negative ICP (do not pursue):**
- One-time project buyers with no retainer intent
- Clients who want hourly billing
- Non-technology sectors with <$500K revenue
- Clients who need to "check with their developer" (no internal authority)

## Revenue Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| First client signed | $2,000+/month | PENDING |
| 3 active retainers | $6,000–$9,000/month | PENDING |
| 5 active retainers | $10,000–$15,000/month | PENDING |
| 10 active retainers | $20,000–$30,000/month | PENDING |
| White-label launch | $50,000+/month | Phase 3 |
