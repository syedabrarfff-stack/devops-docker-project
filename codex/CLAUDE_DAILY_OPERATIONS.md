# CLAUDE DAILY OPERATIONS — JARVIS SALES ENGINE
## Company: Aliyar Solutions | CEO: Syed Abrar ("Captain")
## These are standing orders. Run every day. No prompting needed.

---

## DAILY MISSION

Collect intelligence and leads from 9 connectors, structure them as JSON packages,
and push to GitHub `/jarvis-data/`. JARVIS on EC2 will handle all processing,
outreach, and reporting automatically at 20:30 IST.

The engine runs without Captain's input. Every day. Zero human intervention required.

---

## CONNECTOR INVENTORY

| # | Connector | Purpose | Tool |
|---|---|---|---|
| 1 | Apollo.io | New ICP lead discovery | MCP Apollo / Search |
| 2 | HubSpot | Deal stage tracking, existing contacts | MCP HubSpot |
| 3 | Close CRM | Reply log, activity tracking, cold outreach status | MCP Close |
| 4 | Klaviyo | Email sequence performance, open/click rates | MCP Klaviyo |
| 5 | Gamma | AI pitch deck generation for hot leads | MCP Gamma |
| 6 | Zoho Books | Invoice status, overdue payments | MCP Zoho |
| 7 | Notion | Knowledge base updates, SOPs | MCP Notion |
| 8 | Google Calendar | Booked discovery and demo calls | MCP Google Calendar |
| 9 | Slack | Post summaries, receive Captain alerts | MCP Slack |

---

## DAILY SCHEDULE

### 09:00 IST — MORNING COLLECTION

**Apollo Lead Search (10 new ICP leads)**

Search parameters:
- Titles: CEO, Founder, COO, Head of Operations, CTO
- Company size: 5-200 employees
- Countries (rotate): UK → UAE → USA → Australia → Canada
- Industries (rotate): E-commerce, SaaS, Agency, Healthcare, Logistics, Real Estate, Consulting
- Keywords: "scaling", "growing team", "operational challenges", "no automation", "manual processes"
- Exclude: competitors, government, enterprises >500 employees

For each lead, capture: company_name, contact_name, email, phone, country, industry, employee_count, estimated_revenue, pain_points (from LinkedIn/website), source=apollo

**HubSpot Deal Updates**

Pull all deals updated in the last 24 hours:
- Stage changes (prospect → qualified → demo → proposal → closed)
- New contacts added
- Notes and activities

Add to `calendar.json` if a call was booked.
Update enrichment data for existing JARVIS leads.

**Close CRM Activity Log**

Pull from yesterday:
- Email replies received
- Call outcomes logged
- New contacts added from outreach responses
- Open rate / reply rate on active sequences

Flag any "interested" or "hot" replies for JARVIS priority queue.

**Klaviyo Performance**

Pull active sequences performance:
- Open rates by sequence
- Click rates by sequence
- Reply rates
- Unsubscribes (flag for suppression list)

Update `sequences.json` with current performance data.

---

### 10:00 IST — INTELLIGENCE GENERATION

**Daily Market Case Study**

Rotate through DAILY_RESEARCH_TOPICS:
1. Apollo.io AI prospecting market trends 2025
2. HubSpot CRM adoption SMB market
3. AI automation ROI case studies UK UAE
4. SaaS operational automation pricing benchmarks
5. Digital agency AI transformation
6. E-commerce automation tools comparison
7. Cloud DevOps market demand analysis

Generate a structured 500-word market intelligence report.
Write to `jarvis-data/intelligence/market_report_YYYY-MM-DD.md`

**Trending Opportunity Scan**

Identify 3 trending pain points in target markets right now:
- What are companies Googling / posting on LinkedIn?
- What compliance deadlines are approaching?
- What market disruptions are creating urgency?

Write to `jarvis-data/intelligence/trending_opportunities.json`

**Apollo Market Intelligence**

Weekly (Mondays only):
Refresh the Apollo market study with updated segment data.
Write to `jarvis-data/intelligence/apollo_market_study.md`

---

### 11:00 IST — CONTENT CREATION

**Gamma Pitch Decks**

For each lead with score >= 80 that doesn't have a deck yet:
1. Generate a custom Gamma pitch deck using the lead's industry and pain points
2. Structure: Problem → Our Solution → Case Study → Pricing → Next Steps
3. Write to `jarvis-data/daily/YYYY-MM-DD/decks.json`
4. Format: `{"company_name": "...", "deck_url": "...", "service_focus": "..."}`

**Klaviyo Sequence Optimisation**

If any sequence has open rate < 25% or reply rate < 3%:
- Rewrite subject lines
- Shorten email body (under 120 words)
- Strengthen call-to-action
- Update sequence in `sequences.json`

**Zoho Books Review**

Check all invoices:
- Mark overdue invoices (>5 days past due)
- Flag for Captain review if >$2,000 overdue
- Add to `invoices.json`

**Google Calendar Pull**

Pull all scheduled calls for the next 7 days.
Format as `calendar.json`.
Pre-call prep notes: include lead score, pain points, recommended service package.

---

### 12:00 IST — PACKAGE AND PUSH

**Structure Data Package**

Create `/jarvis-data/daily/YYYY-MM-DD/`:
- `leads.json` — all new leads collected today
- `sequences.json` — active email sequences
- `decks.json` — pitch deck URLs for hot leads
- `invoices.json` — invoice status update
- `calendar.json` — upcoming calls
- `market_report.json` — today's market intelligence

**Write Intelligence Files**

Create/update `/jarvis-data/intelligence/`:
- `market_report_YYYY-MM-DD.md`
- `trending_opportunities.json`
- `apollo_market_study.md` (Mondays only)

**Commit and Push to GitHub**

```
git add jarvis-data/
git commit -m "data(connector-hub): daily package YYYY-MM-DD — X leads, X sequences, X decks"
git push origin claude/jarvis-cans-api-integration-ZThTD
```

**Post Summary to Slack #jarvis-sales**

Message format:
```
JARVIS Daily Package Pushed — [DATE]
Leads collected: X | Hot leads: X
Sequences updated: X | Decks generated: X
Calls booked: X | Overdue invoices: X
Intelligence reports: X

JARVIS will ingest at 20:30 IST and fire outreach automatically.
```

---

### 20:30 IST — CODEX PULLS AND JARVIS INGESTS
_Automatic — no action needed from Claude_

JARVIS:
- Scores all leads against ICP
- Qualifies and promotes to pipeline
- Loads email sequences into outreach engine
- Matches decks to prospects
- Reviews intelligence with AI Council
- Fires outreach for hot leads (score >= 80)
- Posts results to Slack #jarvis-sales

---

## ICP SCORING REFERENCE

| Signal | Points |
|---|---|
| Target industry (e-commerce, SaaS, agency, healthcare, logistics) | 25 |
| Target country (UK, UAE, USA, Australia, Canada) | 20 |
| Company size 5-200 employees | 20 |
| Pain points match (manual processes, no automation, scaling) | 25 |
| Valid email + contact name | 10 |

**Score >= 80:** Hot lead — immediate outreach triggered
**Score 60-79:** Qualified — enters pipeline for sequenced outreach
**Score 45-59:** Review queue — Captain manual review
**Score < 45:** Disqualified

---

## SERVICES TO LEAD WITH (by market segment)

| Segment | Lead Service | Price |
|---|---|---|
| E-commerce UK/Australia | AI Lead Generation + CRM Architecture | $3,500/mo |
| SaaS/Tech USA/UK | Cloud DevOps + CI/CD Pipelines | $4,500/mo |
| Digital Agencies | Full AI Automation Stack | $5,500/mo |
| Healthcare/Clinics | Appointment + CRM Automation | $2,500/mo |
| Logistics UAE/UK | Process Automation + Reporting | $3,000/mo |
| Consulting/Professional | CRM + Proposal Automation | $4,000/mo |
| Fintech/Regulated | Compliance Infrastructure + DevOps | $6,000/mo |

---

## QUALITY STANDARDS

Every lead added must have:
- Valid email address (no generic info@, hello@)
- Specific pain point (not just "wants automation")
- Company employee count
- Correct country assignment

Every email sequence must:
- Sound natural and human (no corporate speak)
- Lead with a pain point, not a pitch
- Be under 150 words per email
- Have a clear single call-to-action

Every market report must:
- Include specific numbers (market size, ROI %s, timeframes)
- Name 3 real prospectable companies
- Have a clear outreach angle for Aliyar Solutions

---

## CAPTAIN ESCALATION TRIGGERS

Notify Captain immediately (via Slack) if:
- Any invoice is overdue > 10 days and > $3,000
- A lead with score >= 90 is found
- A prospect responds asking for an urgent meeting
- Any JARVIS system error prevents daily ingestion
- A deal moves to "proposal" or "closing" stage

---

## PROHIBITED ACTIONS

- Never commit `.env` files or secrets
- Never use "AI agent", "bot", "automation", "prompt" in client-facing content
- Never add leads with estimated_revenue < $300K
- Never add government, military, or competitor leads
- Never generate invoices without Captain approval
- Never send outreach on behalf of Aliyar Solutions directly — that is JARVIS's job

---

## NOTES

- JARVIS system tenant ID: `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa`
- Active branch: `claude/jarvis-cans-api-integration-ZThTD`
- EC2 repo path: `/home/ubuntu/jarvis_sales_pipeline`
- JARVIS API: `http://localhost:8000` (EC2 internal)
- Company: Aliyar Solutions | Contact: syedabrarbhd@gmail.com

_JARVIS Operational Intelligence — Aliyar Solutions | Running every day._
