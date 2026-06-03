# JARVIS Data Bridge — GitHub to EC2

This folder is the operational bridge between Claude (external connectors) and JARVIS (EC2).

Claude collects data from 9 connectors daily, structures it here, and pushes to GitHub.
JARVIS on EC2 pulls at 20:30 IST and ingests everything automatically.

---

## Data Flow

```
Claude (Connectors)  →  GitHub /jarvis-data/  →  Codex pulls to EC2  →  JARVIS ingests
      ↑                                                                        |
      └──────────── JARVIS outputs ←── /jarvis-data/outputs/ ←───────────────┘
```

---

## Directory Structure

```
/daily/YYYY-MM-DD/
  leads.json          New leads from Apollo / HubSpot / Close CRM
  sequences.json      Email sequences from Klaviyo
  decks.json          Pitch deck URLs from Gamma (mapped to company names)
  invoices.json       Invoice status from Zoho Books
  calendar.json       Booked calls from Google Calendar
  market_report.json  Daily market intelligence

/intelligence/
  apollo_market_study.md         Apollo.io user base and positioning analysis
  hubspot_trends.md              HubSpot CRM adoption patterns
  competitor_analysis.md         Competitive landscape
  trending_opportunities.json    AI-identified trending pain points

/outputs/             JARVIS writes these after processing
  leads_processed_YYYY-MM-DD.json
  outreach_sent_YYYY-MM-DD.json
  proposals_generated_YYYY-MM-DD.json
  deals_closed_YYYY-MM-DD.json
```

---

## Lead Schema

```json
{
  "company_name": "string",
  "contact_name": "string",
  "email": "string",
  "phone": "string",
  "country": "string (UK|UAE|USA|Australia|Canada)",
  "industry": "string",
  "employee_count": 35,
  "estimated_revenue": "$2.5M",
  "pain_points": ["manual processes", "no automation"],
  "source": "apollo|hubspot|close_crm|manual",
  "score_hint": 82,
  "deck_url": "https://gamma.app/docs/xxx (optional)",
  "notes": "string"
}
```

---

## Sequence Schema

```json
{
  "name": "E-commerce Outreach v3",
  "target_segment": "E-commerce companies UK/USA 20-100 employees",
  "persona": "Darren Mitchell",
  "emails": [
    {"day": 0,  "subject": "Quick question about [Company]", "body": "..."},
    {"day": 4,  "subject": "Re: [Company] — one more thought", "body": "..."},
    {"day": 8,  "subject": "Last note from Aliyar", "body": "..."}
  ]
}
```

---

## Deck Schema

```json
{
  "company_name": "BrightCommerce UK",
  "contact_name": "James Harrison",
  "deck_url": "https://gamma.app/docs/aliyar-brightcommerce-proposal-abc123",
  "created_date": "2026-06-03",
  "service_focus": "AI Lead Generation + CRM"
}
```

---

## Invoice Schema (from Zoho Books)

```json
{
  "invoice_number": "ALY-202606-0001",
  "client_name": "string",
  "amount_usd": 5000,
  "status": "paid|unpaid|overdue",
  "due_date": "YYYY-MM-DD",
  "service": "string"
}
```

---

## Calendar Schema (from Google Calendar)

```json
{
  "event_title": "Discovery Call — BrightCommerce",
  "date": "YYYY-MM-DD",
  "time": "14:00 UTC",
  "attendee_email": "james@brightcommerce.co.uk",
  "company": "BrightCommerce UK",
  "call_type": "discovery|demo|closing|onboarding"
}
```

---

## Schedule

| Time (UTC) | Time (IST) | Action |
|---|---|---|
| 04:00 | 09:30 | Claude collects leads, generates intelligence |
| 06:30 | 12:00 | Claude packages and pushes to GitHub |
| 07:00 | 12:30 | Claude posts daily summary to Slack |
| 14:30 | 20:00 | JARVIS ingests daily package (automatic) |
| 14:45 | 20:15 | JARVIS posts results to Slack #jarvis-sales |

---

## Environment

- **EC2 Repo Path:** `/home/ubuntu/jarvis_sales_pipeline/jarvis-data`
- **JARVIS API:** `http://localhost:8000`
- **Connector Hub Endpoint:** `POST /api/v1/connector-hub/ingest`
- **Branch:** `claude/jarvis-cans-api-integration-ZThTD`
- **Company:** Aliyar Solutions | CEO: Syed Abrar
