"""
JARVIS vNEXT — Codex Deployment Blueprint
Structured for ChatGPT / Codex to implement directly.
Aliyar Solutions | Captain Syed Abrar
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from datetime import datetime

OUTPUT = "/home/user/devops-docker-project/JARVIS_Codex_Deployment_Blueprint.pdf"

NAVY  = colors.HexColor("#0A1628")
ELEC  = colors.HexColor("#0057FF")
CYAN  = colors.HexColor("#00C8FF")
GOLD  = colors.HexColor("#FFB700")
SILVER= colors.HexColor("#C8D6E5")
WHITE = colors.white
LIGHT = colors.HexColor("#F0F4FA")
BODY  = colors.HexColor("#1E2D40")
GREEN = colors.HexColor("#28CD41")
RED   = colors.HexColor("#FF3B30")
ORANGE= colors.HexColor("#FF9500")
W, H  = A4

def S():
    s = {}
    def ps(name, **kw): s[name] = ParagraphStyle(name, **kw)
    ps("title",  fontName="Helvetica-Bold", fontSize=26, textColor=WHITE,  alignment=TA_CENTER, spaceAfter=6, leading=32)
    ps("sub",    fontName="Helvetica-Bold", fontSize=13, textColor=GOLD,   alignment=TA_CENTER, spaceAfter=5)
    ps("meta",   fontName="Helvetica",      fontSize=9,  textColor=SILVER, alignment=TA_CENTER, spaceAfter=3)
    ps("h1",     fontName="Helvetica-Bold", fontSize=13, textColor=ELEC,   spaceAfter=6,  spaceBefore=12, leading=16)
    ps("h2",     fontName="Helvetica-Bold", fontSize=10.5,textColor=NAVY,  spaceAfter=4,  spaceBefore=8,  leading=13)
    ps("body",   fontName="Helvetica",      fontSize=9,  textColor=BODY,   spaceAfter=4,  leading=13, alignment=TA_JUSTIFY)
    ps("bullet", fontName="Helvetica",      fontSize=9,  textColor=BODY,   spaceAfter=3,  leading=13, leftIndent=14, bulletIndent=4)
    ps("bold",   fontName="Helvetica-Bold", fontSize=9,  textColor=NAVY,   spaceAfter=3,  leading=13)
    ps("code",   fontName="Courier",        fontSize=8,  textColor=NAVY,   spaceAfter=4,  leading=12, leftIndent=10, backColor=LIGHT)
    ps("code_sm",fontName="Courier",        fontSize=7.5,textColor=NAVY,   spaceAfter=3,  leading=11, leftIndent=10, backColor=LIGHT)
    ps("label",  fontName="Helvetica-Bold", fontSize=8,  textColor=SILVER, spaceAfter=2,  leading=11, alignment=TA_CENTER)
    ps("warn",   fontName="Helvetica-Bold", fontSize=9,  textColor=RED,    spaceAfter=4,  leading=13)
    ps("ok",     fontName="Helvetica-Bold", fontSize=9,  textColor=GREEN,  spaceAfter=4,  leading=13)
    ps("prompt", fontName="Helvetica-Bold", fontSize=10, textColor=GOLD,   spaceAfter=4,  leading=14)
    return s

ST = S()

def P(text, style="body"):    return Paragraph(text, ST[style])
def SP(n=6):                  return Spacer(1, n)
def HR(c=ELEC, t=0.5):       return HRFlowable(width="100%", thickness=t, color=c, spaceAfter=6, spaceBefore=6)
def PB():                     return PageBreak()

def box(text, color=GOLD, bg=LIGHT):
    return Table([[Paragraph(text, ST["body"])]],
        colWidths=[W-60],
        style=TableStyle([
            ("BACKGROUND",(0,0),(-1,-1), bg),
            ("BOX",(0,0),(-1,-1), 2, color),
            ("LEFTPADDING",(0,0),(-1,-1), 14),
            ("RIGHTPADDING",(0,0),(-1,-1), 14),
            ("TOPPADDING",(0,0),(-1,-1), 10),
            ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ]))

def code_block(text):
    return Table([[Paragraph(text, ST["code"])]],
        colWidths=[W-60],
        style=TableStyle([
            ("BACKGROUND",(0,0),(-1,-1), LIGHT),
            ("BOX",(0,0),(-1,-1), 1, ELEC),
            ("LEFTPADDING",(0,0),(-1,-1), 10),
            ("RIGHTPADDING",(0,0),(-1,-1), 10),
            ("TOPPADDING",(0,0),(-1,-1), 8),
            ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ]))

def task_table(tasks):
    ts = TableStyle([
        ("BACKGROUND",(0,0),(-1,0), NAVY),
        ("TEXTCOLOR",(0,0),(-1,0), WHITE),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 8.5),
        ("FONTNAME",(0,1),(-1,-1), "Helvetica"),
        ("TEXTCOLOR",(0,1),(-1,-1), BODY),
        ("TOPPADDING",(0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[LIGHT, WHITE]),
        ("GRID",(0,0),(-1,-1), 0.3, SILVER),
        ("BOX",(0,0),(-1,-1), 1, ELEC),
        ("VALIGN",(0,0),(-1,-1), "TOP"),
    ])
    header = tasks[0]
    data = [[Paragraph(h, ST["label"]) for h in header]]
    for row in tasks[1:]:
        data.append([Paragraph(c, ST["body"]) for c in row])
    widths = {3: [(W-60)/3]*3, 4: [(W-60)/4]*4, 2: [(W-60)/2]*2}
    cw = widths.get(len(header), [(W-60)/len(header)]*len(header))
    return Table(data, colWidths=cw, style=ts)

def prompt_box(n, title, prompt_text):
    return KeepTogether([
        Table([[
            Paragraph(f"CODEX PROMPT #{n}", ST["label"]),
            Paragraph(title, ST["prompt"]),
        ]], colWidths=[70, W-130],
        style=TableStyle([
            ("BACKGROUND",(0,0),(-1,-1), NAVY),
            ("TOPPADDING",(0,0),(-1,-1), 8),
            ("BOTTOMPADDING",(0,0),(-1,-1), 8),
            ("LEFTPADDING",(0,0),(-1,-1), 10),
            ("RIGHTPADDING",(0,0),(-1,-1), 10),
            ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
        ])),
        Table([[Paragraph(prompt_text, ST["body"])]],
        colWidths=[W-60],
        style=TableStyle([
            ("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#F8FAFC")),
            ("BOX",(0,0),(-1,-1), 1.5, GOLD),
            ("LEFTPADDING",(0,0),(-1,-1), 14),
            ("RIGHTPADDING",(0,0),(-1,-1), 14),
            ("TOPPADDING",(0,0),(-1,-1), 10),
            ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ])),
        SP(6),
    ])

# ─────────────────────────────────────────────────────────────────────────────

def cover():
    story = [SP(40)]
    story.append(Table([[
        Paragraph("ALIYAR SOLUTIONS — CAPTAIN EYES ONLY",
            ParagraphStyle("cn", fontName="Helvetica-Bold", fontSize=10,
                textColor=CYAN, alignment=TA_CENTER, letterSpacing=3))
    ]], colWidths=[W-60], style=TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), NAVY),
        ("TOPPADDING",(0,0),(-1,-1),8), ("BOTTOMPADDING",(0,0),(-1,-1),8),
    ])))
    story.append(SP(28))
    story.append(P("JARVIS vNEXT", "title"))
    story.append(P("CODEX DEPLOYMENT BLUEPRINT", "sub"))
    story.append(SP(8))
    story.append(HR(GOLD, 2))
    story.append(SP(8))
    story.append(P("Complete implementation guide for ChatGPT / Codex", "meta"))
    story.append(P("24 structured prompts · 12 implementation sprints · Full code specifications", "meta"))
    story.append(P("$1,000,000 Year 1 Target · SMB-First Strategy", "meta"))
    story.append(SP(40))
    story.append(HR(SILVER, 0.5))
    story.append(SP(6))
    story.append(P(f"JARVIS vNEXT Blueprint · Aliyar Solutions · {datetime.now().strftime('%B %Y')}", "meta"))
    story.append(PB())
    return story

def how_to_use():
    story = []
    story.append(Table([[
        Paragraph("HOW TO USE THIS BLUEPRINT WITH CODEX / CHATGPT-5.5",
            ParagraphStyle("htu", fontName="Helvetica-Bold", fontSize=14,
                textColor=WHITE, alignment=TA_CENTER))
    ]], colWidths=[W-60], style=TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), NAVY),
        ("TOPPADDING",(0,0),(-1,-1),14), ("BOTTOMPADDING",(0,0),(-1,-1),14),
    ])))
    story.append(SP(10))
    story.append(box(
        "<b>SYSTEM PROMPT TO PASTE AT THE START OF EVERY CODEX SESSION:</b><br/><br/>"
        "You are the Lead Architect implementing JARVIS vNEXT for Aliyar Solutions. "
        "CEO: Syed Abrar (Captain). You build the system described in the architecture document. "
        "Tech stack: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Redis 7 + React 18 + Vite + Tailwind CSS. "
        "AWS region: ap-south-2 (Hyderabad). Branch: claude/jarvis-cans-api-integration-ZThTD. "
        "Every table has tenant_id UUID. RLS from Day 1. Multi-tenancy built in. "
        "Never commit .env. All secrets in AWS Secrets Manager. "
        "Revenue target: $1,000,000 Year 1. Strategy: SMB first (clients 1-20), then enterprise.",
        GOLD
    ))
    story.append(SP(8))
    story.append(P("Blueprint Structure", "h1"))
    story.append(HR())
    story.append(P(
        "This blueprint is organized into 12 implementation sprints (Weeks 1–12). "
        "Each sprint contains: (1) exact Codex prompts to paste, (2) expected file outputs, "
        "(3) test commands to verify, (4) integration checkpoints. "
        "Complete each sprint before moving to the next.",
        "body"
    ))
    story.append(SP(6))
    story.append(task_table([
        ["SPRINT", "WEEKS", "FOCUS", "REVENUE GATE"],
        ["Sprint 1",  "1",    "Database schema + tenant_id + multi-tenancy",          "Foundation"],
        ["Sprint 2",  "1",    "Lead discovery + Apollo API + scoring engine",          "Leads flowing"],
        ["Sprint 3",  "2",    "Outreach engine + 3-email sequence + personas",         "First outreach"],
        ["Sprint 4",  "2",    "Email tracking + follow-up queue + reply handler",      "Full outreach loop"],
        ["Sprint 5",  "3",    "Demo builder + proposal generator + Captain approval",  "Close first deal"],
        ["Sprint 6",  "3",    "Invoice engine + client portal + delivery tracker",     "First invoice"],
        ["Sprint 7",  "4",    "AI Council + agent performance + memory system",        "System learns"],
        ["Sprint 8",  "5",    "Observability: Grafana + Prometheus + Loki",            "Zero blind spots"],
        ["Sprint 9",  "6",    "ECS Fargate migration + Terraform apply",               "Cloud-native"],
        ["Sprint 10", "7–8",  "White-label + RLS + multi-tenant API keys",             "Agency revenue"],
        ["Sprint 11", "9–10", "Content engine + SEO + tech radar + research",          "Intelligence live"],
        ["Sprint 12", "11–12","React frontend: all 25 views + real-time dashboard",    "Full system"],
    ]))
    story.append(PB())
    return story

def sprint1():
    story = []
    story.append(P("SPRINT 1 — Database Schema & Multi-Tenancy", "h1"))
    story.append(HR(GOLD))
    story.append(box(
        "GOAL: Create the unified JARVIS vNEXT database schema. Every table has tenant_id. "
        "PostgreSQL Row-Level Security (RLS) enforces tenant isolation. SQLAlchemy 2.0 async models.",
        ELEC
    ))
    story.append(SP(6))

    story.append(prompt_box(1, "Base Model + Tenant Architecture",
        """You are implementing JARVIS vNEXT. Create the SQLAlchemy 2.0 async base model structure.

Requirements:
- File: backend/app/models/base.py
- Base class with: id (UUID, primary key), tenant_id (UUID, not null, indexed), created_at (datetime), updated_at (datetime)
- Use: from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
- Use: from sqlalchemy import UUID as SUUID, func
- All models inherit from JarvisBase
- tenant_id must be on EVERY model - no exceptions

Also create: backend/app/core/database.py
- AsyncEngine with postgresql+asyncpg
- AsyncSession with expire_on_commit=False
- get_db() async context manager
- create_tables() startup function

Also create: backend/app/models/tenant.py
- Tenant model: id, name, slug (unique), plan_tier (enum: STARTER/GROWTH/ENTERPRISE/INDUSTRY_OS),
  api_key_hash, settings (JSON), is_active, created_at
- User model: id, tenant_id, email (unique per tenant), hashed_password, role (enum: CAPTAIN/ADMIN/VIEWER),
  is_captain (bool), last_login

Tech stack: Python 3.11, SQLAlchemy 2.0, PostgreSQL 16, asyncpg driver."""
    ))

    story.append(prompt_box(2, "Core CRM + Sales Schema",
        """Continue JARVIS vNEXT implementation. Create the CRM database models.

Files to create in backend/app/models/:
- lead.py: Lead model with fields: id, tenant_id, company_name, contact_name, email, phone,
  country, industry, score (float 0-100), status (enum: NEW/CONTACTED/REPLIED/DEMO/PROPOSAL/WON/LOST),
  source, pain_points (JSON array), enrichment_data (JSON), apollo_id, assigned_persona,
  outreach_count, last_contact, notes

- outreach.py: OutreachLog model: id, tenant_id, lead_id (FK), channel (enum: EMAIL/LINKEDIN/WHATSAPP),
  subject, body_text, sent_from_persona, sent_at, status (SENT/DELIVERED/OPENED/CLICKED/REPLIED/BOUNCED),
  sequence_step (int 1-3)
  EmailTracking model: id, tenant_id, outreach_id (FK), opened_at, clicked_at, replied_at, bounce_reason
  FollowUpQueue: id, tenant_id, lead_id, sequence_step, scheduled_at, executed_at, status

- revenue.py: Client model: id, tenant_id, company_name, contact_name, email, package_tier, mrr_usd (float),
  status (ACTIVE/PAUSED/CHURNED), started_at
  Invoice model: id, tenant_id, client_id (FK), invoice_number (format: ALY-YYYYMM-XXXX),
  amount_usd, status (DRAFT/SENT/PAID/OVERDUE), due_date, paid_at, pdf_url

- approval.py: ApprovalRequest: id, tenant_id, action_type, title, summary, risk_level, payload (JSON),
  status (PENDING/APPROVED/REJECTED), raised_by, decided_by, decided_at
  AuditLog: id, tenant_id, user_id, action, entity_type, entity_id, before_json, after_json, ip_addr

All models import from app.models.base.JarvisBase. Register all in backend/app/models/__init__.py."""
    ))

    story.append(prompt_box(3, "Row-Level Security (RLS) Migration",
        """Create Alembic migration that applies PostgreSQL Row-Level Security to all JARVIS tables.

Requirements:
- File: backend/alembic/versions/0001_rls_setup.py
- For EVERY table: enable RLS, create policy that WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
- Also create function: set_tenant_context(tenant_uuid) that sets app.current_tenant_id
- Add index on tenant_id for every table (idx_{table}_tenant_id)

Also modify backend/app/middleware.py:
- Add TenantContextMiddleware that extracts tenant_id from JWT token and calls set_tenant_context()
- Add X-Request-ID middleware (generate UUID if not present, add to response headers)
- Add response time header X-Response-Time

Test migration: alembic upgrade head
Verify RLS: INSERT with tenant_id A, query with tenant_id B context, should return 0 rows."""
    ))
    story.append(PB())
    return story

def sprint2():
    story = []
    story.append(P("SPRINT 2 — Lead Discovery Engine", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(4, "Apollo API Integration + Lead Discovery",
        """Implement the JARVIS Lead Discovery Engine. This is the system that fills the sales pipeline.

File: backend/app/services/leads/discovery.py

Class: LeadDiscoveryEngine
Methods:
- async search_apollo(query, filters) -> list[dict]
  Uses APOLLO_API_KEY from settings. Apollo endpoint: /people/search
  Filters: person_titles=['CEO','Founder','Director','VP'], locations by country
  Returns: list of enriched contact records

- async enrich_company(domain) -> dict
  Apollo /organizations/enrich endpoint. Gets: size, revenue, tech_stack, social_urls

- async score_lead(lead_data) -> float
  Use Gemini Pro (RESEARCH task type) with this prompt:
  "Score this lead 0-100 for Aliyar Solutions. ICP: SMB companies ($500K-$10M revenue, 5-100 employees),
  English-speaking, in UK/UAE/USA/AUS/Canada, with pain: manual processes, no AI systems, no tech team.
  Lead: {lead_data}. Return only a number 0-100."

- async run_daily_discovery(tenant_id, targets: list) -> int
  Discovers leads for given targets (industries, countries).
  Scores each. Saves scored leads to DB. Returns count.

- async discover_from_google_maps(query, location) -> list[dict]
  Uses GOOGLE_MAPS_API_KEY. Places API: /textsearch/json
  Returns businesses with name, address, phone, website

Also create: backend/app/api/v1/routes/discovery.py
Routes: POST /discover/run, POST /discover/leads/score, GET /discover/leads/today
Register in: backend/app/api/v1/__init__.py"""
    ))

    story.append(prompt_box(5, "Lead Scoring + ICP Matching",
        """Implement the JARVIS Ideal Customer Profile (ICP) scoring system.

File: backend/app/services/leads/scoring.py

ALIYAR_ICP = {
    "target_industries": ["e-commerce", "real estate", "consulting", "professional services",
                          "SaaS", "healthcare", "logistics", "education", "finance", "retail"],
    "target_countries": ["UK", "UAE", "USA", "Australia", "Canada", "Bahrain", "Europe"],
    "company_size": {"min_employees": 5, "max_employees": 200},
    "revenue_range": {"min_usd": 500000, "max_usd": 50000000},
    "pain_points": ["manual processes", "no automation", "poor lead generation",
                    "no AI systems", "no tech team", "scaling problems"],
    "disqualifiers": ["competitor", "no budget", "too large enterprise", "government"],
    "min_score_for_outreach": 60,
}

Class: LeadScoringEngine
- async score_against_icp(lead: dict) -> tuple[float, dict]
  Returns (score, reasoning_dict)
  Scoring weights: industry_match=25pts, country_match=20pts, size_fit=20pts,
  pain_point_match=25pts, contact_quality=10pts

- async batch_score(leads: list[dict], tenant_id) -> list[Lead]
  Score all leads, save to DB, return sorted by score descending

- async promote_to_pipeline(lead_id, tenant_id) -> Lead
  If score >= 60: set status=CONTACTED, assign persona (Darren Mitchell for sales),
  add to outreach queue

Daily job: score all NEW leads from yesterday, promote top 20 to pipeline."""
    ))
    story.append(PB())
    return story

def sprint3():
    story = []
    story.append(P("SPRINT 3 — Outreach Engine", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(6, "3-Email Sequence + Persona Engine",
        """Implement the JARVIS Outreach Engine. This system sends cold outreach as human personas.

File: backend/app/services/outreach/engine.py

PERSONAS = {
    "darren_mitchell": {
        "name": "Darren Mitchell",
        "email": "darren.mitchell@aliyarsolutions.com",
        "role": "Client Acquisition Specialist",
        "signature": "Darren Mitchell | Client Acquisition | Aliyar Solutions",
        "style": "Direct, results-focused, professional. Leads with value."
    }
}

3-EMAIL SEQUENCE:
Email 1 (Day 1): Subject: "Quick question about [Company]'s operations"
  - Lead with a specific observation about their business
  - One concrete problem they likely face
  - Soft CTA: "Would a 15-minute conversation make sense?"

Email 2 (Day 4): Subject: "Results we delivered for similar [Industry] companies"
  - Reference: "Following up on my note earlier"
  - One specific result example (quantified: "reduced manual work by 70%")
  - CTA: "Happy to show you exactly how we did this"

Email 3 (Day 8): Subject: "Last note from me, [FirstName]"
  - Acknowledge they're busy
  - Final value statement
  - Easy out: "If the timing isn't right, no worries at all"

Class: OutreachEngine
- async generate_sequence(lead: Lead, tenant_id) -> list[OutreachLog]
  Use Claude Opus (SALES task type) to write all 3 emails personalized to the specific lead.

- async queue_sequence(lead_id, tenant_id) -> None
  Add 3 emails to FollowUpQueue with correct scheduled_at dates

- async execute_due_outreach(tenant_id) -> int
  Find all FollowUpQueue items where scheduled_at <= now and status=PENDING.
  For each: generate email, check captain_approval_required(autonomy_stage),
  send via SMTP (Gmail) or add to captain_queue, update lead status.
  Returns count of messages sent.

Also: backend/app/api/v1/routes/outreach.py
Routes: POST /outreach/queue/{lead_id}, POST /outreach/execute, GET /outreach/stats"""
    ))

    story.append(prompt_box(7, "Gmail SMTP Integration",
        """Implement Gmail SMTP sending for JARVIS outreach.

File: backend/app/services/notifications/gmail_sender.py

Uses: GMAIL_ADDRESS and GMAIL_APP_PASSWORD from settings (Phase 1 SMTP)

Class: GmailSender
- async send_email(to: str, subject: str, body_html: str, from_name: str, from_email: str) -> bool
  Uses aiosmtplib with gmail SMTP: smtp.gmail.com:587, STARTTLS
  Returns True on success, logs failure to audit_log on error

- async send_outreach(outreach: OutreachLog) -> bool
  Sends the outreach email. Updates outreach.status to SENT.
  Records in email_tracking table with tracking pixel URL if configured.

- async check_replies(tenant_id) -> list[dict]
  Uses GMAIL_ADDRESS credentials to check inbox via IMAP.
  Finds replies to our outreach emails. Returns list of reply dicts.
  (Phase 1: basic IMAP. Phase 2: Gmail OAuth API)

Also: backend/app/services/notifications/slack.py
- async notify_slack(message: str) -> bool (uses SLACK_WEBHOOK_URL)

Also: backend/app/services/notifications/telegram.py
- async notify_telegram(message: str) -> bool (uses TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)

Alert on: proposal_accepted, meeting_booked, payment_received, system_critical_error"""
    ))
    story.append(PB())
    return story

def sprint4():
    story = []
    story.append(P("SPRINT 4 — Email Tracking + Follow-Up + Reply Handler", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(8, "Reply Classification + Lead Progression",
        """Implement the JARVIS Reply Handler — the system that processes prospect responses.

File: backend/app/services/outreach/reply_handler.py

REPLY_CLASSIFICATIONS = [
    "INTERESTED",    # "Yes, let's talk" / "Tell me more" / "Can we schedule a call?"
    "QUESTION",      # Asking about pricing, process, timeline
    "NOT_NOW",       # "Maybe later" / "Not the right time"
    "NO",            # Hard no / unsubscribe
    "OUT_OF_OFFICE", # Auto-reply
    "UNKNOWN",       # Cannot classify
]

Class: ReplyHandler
- async classify_reply(reply_text: str) -> tuple[str, float]
  Use Claude Opus. Returns (classification, confidence_score)

- async process_reply(lead_id, reply_text, tenant_id) -> dict
  1. Classify reply
  2. Update lead status based on classification:
     INTERESTED → status=DEMO, alert Captain, pause follow-up sequence
     QUESTION → status=REPLIED, generate response using Claude Opus as Darren Mitchell persona
     NOT_NOW → status=NURTURE, schedule re-contact in 30 days
     NO → status=LOST, stop all outreach, respect opt-out
  3. Log to reply_log table
  4. Return action taken

- async generate_response(reply_text: str, lead: Lead, classification: str) -> str
  Write response as Darren Mitchell persona. Natural, human, intelligent.
  INTERESTED: Offer calendar link (or specific time slots)
  QUESTION: Answer directly and professionally

Integrate: JARVIS checks Gmail inbox every 2 hours for new replies."""
    ))
    story.append(PB())
    return story

def sprint5():
    story = []
    story.append(P("SPRINT 5 — Demo Builder + Proposal Generator", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(9, "AI-Generated Proposal PDFs",
        """Implement the JARVIS Proposal Generator — creates fully customized proposals as PDFs.

File: backend/app/services/governance/proposal_generator.py

Uses ReportLab for PDF generation.

Class: ProposalGenerator
- async generate(lead: Lead, package_tier: str, tenant_id) -> str
  Returns path to generated PDF.

  Proposal structure:
  Page 1: Cover — Aliyar Solutions logo area, "Proposal for [Company Name]", date, confidential
  Page 2: Executive Summary — 3 paragraphs about their specific situation and how we solve it
  Page 3: Proposed Solution — 4-6 bullet points mapping their pain points to our capabilities
  Page 4: Package Details — table with selected package (STARTER/GROWTH/ENTERPRISE), features, price
  Page 5: Implementation Timeline — 4-week onboarding plan, milestones
  Page 6: Investment Summary — pricing table, payment terms (50% upfront + 50% on delivery), next steps
  Page 7: About Aliyar Solutions — company description, team, technology

  Use Claude Opus (SALES task type) to generate all text content personalized to the lead.
  Invoice numbering: ALY-YYYYMM-XXXX

- async submit_for_approval(proposal_id, tenant_id) -> dict
  Calls request_captain_approval() from jarvis_authority.py
  Notifies Captain via Slack + Telegram with PDF link

Routes: POST /proposals/generate, POST /proposals/{id}/approve, POST /proposals/{id}/send
Save PDFs to: AWS S3 bucket (or local /data/proposals/ in Phase 1)"""
    ))

    story.append(prompt_box(10, "Captain Approval Queue + Dashboard",
        """Implement the Captain Approval Queue — the most critical UX in the system.

File: backend/app/services/governance/captain_queue.py

This is what Captain sees every morning. Every decision that needs approval appears here.

Class: CaptainQueue
- async add_item(action_type, title, summary, payload, risk_level, tenant_id) -> ApprovalRequest
  Creates ApprovalRequest. Notifies Captain via Slack + Telegram + WebSocket.
  Priority scoring: HIGH for pricing/contract/production deploy, MEDIUM for proposals, LOW for others.

- async get_pending(tenant_id) -> list[ApprovalRequest]
  Returns all pending items sorted by: priority DESC, created_at ASC

- async approve(approval_id, captain_note, tenant_id) -> dict
  Sets status=APPROVED. Executes the queued action.
  Logs to audit_log. Notifies relevant agent.

- async reject(approval_id, reason, tenant_id) -> dict
  Sets status=REJECTED. Notifies agent with reason.

WebSocket endpoint: /ws/captain
- On connect: send all pending approvals count + system health
- On approval/rejection: broadcast to all Captain sessions
- On new approval item: push notification to Captain

Frontend route needed: /approvals view showing pending queue with approve/reject buttons."""
    ))
    story.append(PB())
    return story

def sprint6():
    story = []
    story.append(P("SPRINT 6 — Invoice Engine + Client Management", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(11, "Invoice Generator + Payment Tracking",
        """Implement the JARVIS Invoice Engine.

File: backend/app/services/governance/invoice_engine.py

Class: InvoiceEngine
- async generate(client_id, amount_usd, description, due_days=14, tenant_id) -> Invoice
  Auto-number: ALY-YYYYMM-XXXX (XXXX = sequential per month per tenant)
  Generate PDF invoice using ReportLab (same style as proposals)
  PDF includes: Aliyar Solutions letterhead, client details, line items, payment instructions,
  bank details placeholder, due date, invoice number
  Save to S3/local. Store url in invoice.pdf_url.

- async send_invoice(invoice_id, tenant_id) -> bool
  Email invoice PDF to client. Update status=SENT. Alert Captain.

- async check_overdue(tenant_id) -> list[Invoice]
  Find invoices where due_date < now and status != PAID.
  Send reminder email (max 3 reminders). Alert Captain on 7-day overdue.

- async record_payment(invoice_id, amount, tenant_id) -> Invoice
  Update status=PAID. Set paid_at. Alert Captain (payment_received event).
  Update client.mrr_usd. Update revenue_snapshots.

Routes: POST /invoices/generate, POST /invoices/{id}/send, POST /invoices/{id}/pay
GET /revenue/snapshot, GET /revenue/mrr-chart"""
    ))
    story.append(PB())
    return story

def sprint7():
    story = []
    story.append(P("SPRINT 7 — AI Council + Memory System", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(12, "AI Council Implementation",
        """Implement the JARVIS Intelligence Council — 8 AI members, weighted consensus.

File: backend/app/services/ai/council.py

COUNCIL_MEMBERS = [
    {"id": "strategist", "provider": "anthropic", "model": "claude-opus-4-8",    "weight": 0.25, "specialty": "strategy"},
    {"id": "engineer",   "provider": "bedrock",   "model": "claude-sonnet-4-6",  "weight": 0.25, "specialty": "architecture"},
    {"id": "analyst",    "provider": "openai",    "model": "gpt-4o",             "weight": 0.15, "specialty": "analysis"},
    {"id": "scout",      "provider": "google",    "model": "gemini-1.5-pro",     "weight": 0.10, "specialty": "research"},
    {"id": "speedster",  "provider": "groq",      "model": "llama-3.3-70b",      "weight": 0.08, "specialty": "fast"},
    {"id": "contrarian", "provider": "mistral",   "model": "mistral-large",      "weight": 0.07, "specialty": "critique"},
    {"id": "economist",  "provider": "zhipuai",   "model": "glm-4",              "weight": 0.05, "specialty": "economics"},
    {"id": "innovator",  "provider": "minimax",   "model": "abab6.5s",           "weight": 0.05, "specialty": "creative"},
]

Class: IntelligenceCouncil
- async convene(question: str, context: dict, council_type: str) -> CouncilResult
  1. Package question + context for each council member
  2. Parallel asyncio.gather() all 8 member votes (with timeout=30s per member)
  3. For members that timeout: use weight=0 for that session
  4. Require minimum 5 responses (quorum)
  5. Calculate weighted score: sum(member.weight * member.vote_score)
  6. Aggregate reasoning from all members
  7. Decision: score>=80 APPROVE, 60-79 CAPTAIN_REVIEW, <60 REJECT
  8. Save to ai_council_sessions table
  9. Return CouncilResult(decision, score, reasoning, member_votes)

- async adjust_weights_monthly(tenant_id) -> None
  For each member: compare their votes to actual outcomes (from audit_log).
  +2% weight if prediction correct. -1% if wrong. Floor 3%, Cap 35%.

Routes: POST /council/convene, GET /council/sessions, GET /council/health"""
    ))

    story.append(prompt_box(13, "5-Tier Memory System",
        """Implement the JARVIS Memory Architecture — 5 tiers of persistent intelligence.

File: backend/app/services/memory/memory_engine.py

Tier 1 — Working Memory (Redis):
- async set_working(key: str, value: dict, ttl_hours=24, tenant_id) -> None
- async get_working(key: str, tenant_id) -> dict | None
- async clear_working(tenant_id) -> None

Tier 2 — Operational Memory (PostgreSQL, 90-day TTL):
- async store_operational(category: str, content: str, source: str, tenant_id) -> MemoryOperational
- async retrieve_operational(category: str, limit=50, tenant_id) -> list[MemoryOperational]
- async prune_operational(tenant_id) -> int (removes records older than 90 days)

Tier 3 — Strategic Memory (PostgreSQL + pgvector):
- async store_strategic(category, content, tags: list, tenant_id) -> MemoryStrategic
  Generates embedding using text-embedding-3-large before storing.
- async semantic_search(query: str, limit=10, threshold=0.75, tenant_id) -> list[MemoryStrategic]
  Embeds query, cosine similarity search in memory_strategic table.
- async promote_from_operational(memory_id, tenant_id) -> MemoryStrategic

Tier 5 — Civilization Memory (Immutable):
- async record_milestone(event_type: str, content: str, tenant_id) -> CivilizationMemory
  Appends SHA-256 hash. Never updates, never deletes.

Daily job at 00:30: consolidate working → operational, prune expired operational.
Weekly job: promote high-relevance operational records to strategic with embeddings."""
    ))
    story.append(PB())
    return story

def sprint8():
    story = []
    story.append(P("SPRINT 8 — Observability Stack", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(14, "Prometheus Metrics + Grafana Dashboards",
        """Add comprehensive observability to JARVIS vNEXT.

File: backend/app/middleware.py (extend existing)

Add Prometheus metrics using prometheus-fastapi-instrumentator:
- HTTP request rate by endpoint and status code
- Request latency percentiles (p50, p95, p99)
- Active DB connections
- Redis memory usage

Custom metrics to add:
- jarvis_leads_discovered_total (counter, labels: source, country)
- jarvis_outreach_sent_total (counter, labels: channel, persona)
- jarvis_ai_cost_usd_total (counter, labels: provider, model, task_type)
- jarvis_ai_latency_seconds (histogram, labels: provider, model)
- jarvis_council_sessions_total (counter, labels: decision)
- jarvis_approvals_pending (gauge, labels: risk_level)
- jarvis_clients_active (gauge)
- jarvis_mrr_usd (gauge)

File: infrastructure/grafana/dashboards/jarvis_main.json
Create Grafana dashboard JSON with panels:
- System Health (CPU, memory, request rate, error rate)
- Revenue Metrics (MRR gauge, ARR gauge, new clients this month)
- AI Operations (cost per day, calls per provider, latency)
- Lead Pipeline (leads by stage funnel, outreach sent today)
- Captain Queue (pending approvals count, last updated)

Update docker-compose.yml to add prometheus scrape config for backend:8000/metrics."""
    ))
    story.append(PB())
    return story

def sprint9():
    story = []
    story.append(P("SPRINT 9 — ECS Fargate Migration", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(15, "Apply Terraform + ECS Deployment",
        """Execute the JARVIS cloud infrastructure deployment.

The Terraform is already written at infra/terraform/. Apply it.

Steps to execute (run as Captain on EC2):

Step 1 — Set Terraform variables:
Create infra/terraform/terraform.tfvars (NEVER COMMIT — add to .gitignore):
  aws_region = "ap-south-2"
  project = "jarvis"
  environment = "production"
  db_password = "<from AWS Secrets Manager>"
  secret_key = "<generate with: openssl rand -hex 32>"
  # ... all required variables

Step 2 — Initialize and plan:
  cd infra/terraform
  terraform init
  terraform plan -out=tfplan

Step 3 — Apply (creates all AWS resources):
  terraform apply tfplan

Step 4 — Build and push Docker images:
  aws ecr get-login-password --region ap-south-2 | docker login --username AWS --password-stdin <ECR_URI>
  docker build -t jarvis-backend backend/
  docker tag jarvis-backend:latest <ECR_BACKEND_URI>:latest
  docker push <ECR_BACKEND_URI>:latest

Step 5 — Update ECS task definitions:
  Create ECS task definition JSON with:
  - Container: jarvis-backend, image: ECR_URI, port: 8000
  - Environment: from AWS Secrets Manager (valueFrom arn)
  - Log driver: awslogs, group: /jarvis/production/backend
  - Memory: 1024 MB, CPU: 512

Step 6 — Register task definition, update ECS service:
  aws ecs register-task-definition --cli-input-json file://task-def.json
  aws ecs update-service --cluster jarvis-production-cluster --service jarvis-backend --task-definition jarvis-backend:latest

Step 7 — Verify deployment:
  aws ecs describe-services --cluster jarvis-production-cluster --services jarvis-backend
  curl https://api.aliyarsolutions.com/health

File to create: scripts/deploy_ecs.sh — wrapper script for steps 4-7."""
    ))
    story.append(PB())
    return story

def sprint10():
    story = []
    story.append(P("SPRINT 10 — White-Label + Multi-Tenant", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(16, "Multi-Tenant API + Tenant Management",
        """Implement the JARVIS white-label multi-tenant system.

File: backend/app/services/tenancy/tenant_manager.py

Class: TenantManager
- async create_tenant(name, plan_tier, admin_email, admin_password) -> tuple[Tenant, User]
  Create tenant record. Create admin user with is_captain=False.
  Generate API key (32-byte random, store SHA-256 hash).
  Apply RLS context for new tenant.
  Return tenant + user.

- async provision_tenant(tenant_id) -> None
  Seed default data: personas, agent configs, service catalog entries, governance rules.
  This runs after create_tenant.

- async get_tenant_from_api_key(api_key: str) -> Tenant | None
  Hash the provided key, look up in tenant_api_keys table.

Auth middleware update:
- Accept JWT OR X-API-Key header
- JWT: extract tenant_id from sub claim
- API Key: look up tenant from key hash
- Set app.current_tenant_id in DB session context

File: backend/app/api/v1/routes/tenancy.py
Routes (Captain-only):
  POST /admin/tenants — create new tenant
  GET /admin/tenants — list all tenants
  PUT /admin/tenants/{id}/limits — update plan limits
  POST /admin/tenants/{id}/api-key — rotate API key

Pricing per tenant tier (enforce in middleware):
  STARTER: max_leads=500/mo, max_agents=10, max_ai_calls=1000/day
  GROWTH: max_leads=2000/mo, max_agents=25, max_ai_calls=5000/day
  ENTERPRISE: max_leads=10000/mo, max_agents=64, max_ai_calls=unlimited"""
    ))
    story.append(PB())
    return story

def sprint11():
    story = []
    story.append(P("SPRINT 11 — Intelligence Stack", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(17, "Tech Radar + Market Intelligence",
        """Implement the JARVIS Intelligence Division services.

File: backend/app/services/intelligence/tech_radar.py
Class: TechRadarEngine
- async scan_week(tenant_id) -> list[TechRadarEntry]
  Use Gemini Pro (RESEARCH task type) to scan for emerging technologies.
  Categories: AI/ML, Cloud, Security, DevOps, Data, Frontend, Backend.
  Rings: ADOPT (proven), TRIAL (promising), ASSESS (watch), HOLD (avoid).
  Save to tech_radar table. Return new entries.

File: backend/app/services/intelligence/market_intel.py
Class: MarketIntelligenceEngine
- async generate_report(topics: list[str], tenant_id) -> str
  Use Gemini Pro to generate market intelligence report.
  Topics: AI automation market, SMB technology adoption, competitor pricing changes.
  Save to market_intelligence table. Return report content.

- async monitor_competitors(tenant_id) -> list[dict]
  For each competitor in competitor_profiles:
  Check their website, LinkedIn, pricing pages for changes.
  Alert Captain if pricing changes detected.

APScheduler jobs to create:
- tech_radar_scan: every Monday 06:00
- market_intelligence_report: every other Sunday 07:00
- competitor_monitoring: every Monday 09:00
- morning_briefing: every day 07:00

Morning briefing job:
  Compile: top 5 leads by score, revenue snapshot (MRR, pipeline),
  pending Captain approvals, system health summary, today's scheduled outreach.
  Send to Captain via Slack + Telegram. Log to briefing history."""
    ))

    story.append(prompt_box(18, "Morning Briefing + APScheduler",
        """Implement the JARVIS APScheduler system with all production jobs.

File: backend/app/services/scheduler/scheduler.py

Use apscheduler[asyncio] with SQLAlchemy job store (persistent jobs survive restarts).

Jobs to register:
  daily_morning_briefing    — cron: 07:00 daily (IST = UTC+5:30, so 01:30 UTC)
  daily_lead_scoring        — cron: 02:00 daily (IST)
  daily_lead_discovery      — cron: 03:30 daily (IST)
  daily_follow_up_check     — cron: 10:00 daily (IST)
  daily_memory_consolidate  — cron: 00:30 daily (IST)
  daily_optimization_review — cron: 23:00 daily (IST)
  weekly_outreach_stats     — cron: Monday 08:00 (IST)
  weekly_pipeline_health    — cron: Sunday 20:00 (IST)
  weekly_tech_radar         — cron: Monday 06:00 (IST)
  biweekly_research_report  — cron: every other Sunday 07:00 (IST)
  monthly_weight_adjust     — cron: 1st of month 00:00 (IST)

Morning Briefing content:
  "JARVIS MORNING BRIEFING — {date}

  REVENUE:
  - Current MRR: ${mrr}
  - New leads today: {new_leads}
  - Pipeline value: ${pipeline}

  ACTION REQUIRED ({pending_approvals} items):
  {approval_list}

  OUTREACH:
  - Scheduled today: {outreach_count} messages
  - Replied this week: {reply_count}
  - Top lead: {top_lead_name} ({top_lead_score}/100)

  SYSTEM: {system_health_summary}"

Start scheduler in FastAPI lifespan (backend/app/main.py)."""
    ))
    story.append(PB())
    return story

def sprint12():
    story = []
    story.append(P("SPRINT 12 — React Frontend (25 Views)", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(19, "React Frontend Architecture",
        """Implement the JARVIS React frontend — glassmorphism design, all 25 views.

Tech stack: React 18 + Vite + Tailwind CSS + Zustand + Axios + Recharts

Design system (glassmorphism):
- Background: linear-gradient(135deg, #0A1628 0%, #0D1F3C 50%, #0A1628 100%)
- Cards: bg-white/5 backdrop-blur-md border border-white/10 rounded-xl
- Accent colors: blue-500 (#0057FF), cyan-400 (#00C8FF), gold (#FFB700)
- Text: white primary, gray-400 secondary

File: frontend/src/App.jsx
VIEWS map (25 views with their routes):
  dashboard    → /          → Executive Dashboard (MRR, pipeline, alerts, briefing)
  chat         → /chat      → JARVIS chat interface (full-page conversational AI)
  briefing     → /briefing  → Morning briefing history
  approvals    → /approvals → Captain Approval Queue (cards with approve/reject)
  leads        → /leads     → Lead pipeline (table + kanban, filters, score badges)
  outreach     → /outreach  → Outreach log, sequence status, stats
  crm          → /crm       → Client management, contacts, companies
  proposals    → /proposals → Proposal list, PDF previews, status
  invoices     → /invoices  → Invoice management, payment status
  agents       → /agents    → Agent registry, performance scores
  council      → /council   → AI Council session history + new session
  memory       → /memory    → Memory browser (working/operational/strategic)
  intel        → /intel     → Market intelligence, tech radar, competitor profiles
  discovery    → /discovery → Lead discovery controls, run jobs, view today's leads
  tasks        → /tasks     → Task management across all projects
  projects     → /projects  → Client project tracker, milestones
  scheduler    → /scheduler → APScheduler job dashboard, run/pause jobs
  notifications→ /notifications → Notification center + WebSocket events
  gmail        → /gmail     → Gmail inbox monitor, outreach drafts
  voice        → /voice     → ElevenLabs TTS, voice briefings
  knowledge    → /knowledge → Knowledge base browser + SOP library
  research     → /research  → Research reports, tech radar viewer
  governance   → /governance→ Audit log, rules, compliance
  catalog      → /catalog   → Service catalog (30 divisions)
  settings     → /settings  → Tenant settings, API keys, config

File: frontend/src/store/useJarvisStore.js (Zustand)
State: { user, tenant, notifications, captainQueue, systemHealth, ws }"""
    ))

    story.append(prompt_box(20, "Executive Dashboard View",
        """Build the JARVIS Executive Dashboard — the most important view in the system.

File: frontend/src/components/dashboard/Dashboard.jsx

Layout (4 metric cards at top + main content below):
- Card 1: MRR (gold, big number, +% vs last month)
- Card 2: Active Clients (cyan)
- Card 3: Pipeline Value (blue)
- Card 4: Pending Approvals (red if >0, green if 0)

Main content grid:
- Left (60%):
  - "Today's Pipeline" — top 5 leads by score, with quick actions
  - "Recent Activity" — last 10 audit log entries

- Right (40%):
  - "Morning Briefing" — latest briefing content (collapsed/expandable)
  - "System Health" — green/red status for: API, DB, Redis, AI providers
  - "Captain Queue" — count of pending approvals with link to /approvals

Bottom section:
  - MRR trend chart (Recharts LineChart, last 12 months)
  - Lead funnel chart (Recharts BarChart: NEW/CONTACTED/REPLIED/DEMO/PROPOSAL/WON)
  - AI Cost breakdown (Recharts PieChart: by provider)

Real-time via WebSocket (/ws/captain):
  - Approval badge count updates without page refresh
  - System health indicators update every 30s
  - New alert banner on critical events"""
    ))

    story.append(prompt_box(21, "Approvals View — Captain Decision Center",
        """Build the Captain Approval Queue view — where Captain approves/rejects JARVIS actions.

File: frontend/src/components/approvals/Approvals.jsx

Layout:
- Header: "Captain's Queue" + count badge
- Filters: All / High Risk / Proposals / Infrastructure / Financial
- Approval cards (sorted by priority, then age):

Each card shows:
  - Risk badge (HIGH=red, MEDIUM=orange, LOW=blue)
  - Action type (e.g., "proposal_send", "pricing_decision")
  - Title and summary (first 200 chars, expandable)
  - Time in queue
  - Payload preview (JSON collapse/expand)
  - Two buttons: ✓ APPROVE (green) and ✗ REJECT (red)
  - Optional note field before confirming

On approve: POST /approvals/{id}/approve → card disappears with animation
On reject: POST /approvals/{id}/reject with reason → card disappears

Keyboard shortcuts: A to approve focused card, R to reject, Tab to navigate

Stats bar at top: Approved today, Rejected today, Average time in queue"""
    ))
    story.append(PB())
    return story

def sprint_final():
    story = []
    story.append(P("FINAL PROMPTS — Integration + First Client", "h1"))
    story.append(HR(GOLD))

    story.append(prompt_box(22, "End-to-End Integration Test",
        """Test the complete JARVIS vNEXT pipeline end-to-end before going live.

Create file: scripts/integration_test.py

Test flow:
1. Create test tenant: test_tenant = await TenantManager.create_tenant("Test Agency", "GROWTH", ...)
2. Run lead discovery: leads = await LeadDiscoveryEngine.run_daily_discovery(tenant_id, ["SaaS", "UK"])
3. Assert: len(leads) > 0, all leads have score > 0
4. Score a lead: lead = leads[0]; scored = await LeadScoringEngine.score_against_icp(lead)
5. Queue outreach: await OutreachEngine.queue_sequence(lead.id, tenant_id)
6. Assert: FollowUpQueue has 3 records for this lead
7. Execute outreach (test mode — don't actually send): await OutreachEngine.execute_due_outreach(tenant_id, dry_run=True)
8. Simulate reply: await ReplyHandler.process_reply(lead.id, "Yes, this sounds interesting!", tenant_id)
9. Assert: lead.status == "DEMO"
10. Generate proposal: pdf_path = await ProposalGenerator.generate(lead, "GROWTH", tenant_id)
11. Assert: os.path.exists(pdf_path)
12. Submit to Captain queue: result = await CaptainQueue.add_item("proposal_send", ..., tenant_id)
13. Assert: result.status == "PENDING"
14. Run morning briefing: briefing = await generate_morning_briefing(tenant_id)
15. Assert: "leads" in briefing and "revenue" in briefing

All assertions with clear pass/fail output. If all pass: print "JARVIS vNEXT INTEGRATION: ALL SYSTEMS GO" """)
    )

    story.append(prompt_box(23, "Pre-Launch Checklist Script",
        """Create the JARVIS pre-launch validation script.

File: scripts/pre_launch_check.py

Check every system required for first client:

CHECKS = [
  ("Database connection", test_db_connection),
  ("Redis connection", test_redis_connection),
  ("AWS Bedrock reachable", test_bedrock),
  ("Anthropic API key valid", test_anthropic),
  ("Apollo API key valid", test_apollo),
  ("Gmail SMTP working", test_gmail),
  ("Slack webhook working", test_slack),
  ("Telegram bot working", test_telegram),
  ("Lead discovery returning results", test_discovery),
  ("Email generation working", test_email_gen),
  ("Proposal PDF generation working", test_proposal_gen),
  ("Captain approval queue working", test_approval_queue),
  ("WebSocket endpoint working", test_websocket),
  ("Grafana accessible", test_grafana),
  ("Prometheus scraping", test_prometheus),
  ("S3 upload working", test_s3),
  ("Domain resolving correctly", test_domain),
]

For each check: green ✓ or red ✗ with error message.
Print summary: "X/17 systems ready"
If all pass: print "JARVIS IS READY. CAPTAIN, BEGIN THE MISSION." """)
    )

    story.append(prompt_box(24, "Captain's First Client Activation Protocol",
        """This is the final prompt — the system is built, Captain is ready to activate.

ACTIVATION STEPS:

1. Run integration test: python scripts/integration_test.py — all must pass

2. Run pre-launch check: python scripts/pre_launch_check.py — all must pass

3. Configure Captain's account:
   POST /admin/tenants with: name="Aliyar Solutions", plan_tier="ENTERPRISE", captain_email="syedabrarbhd@gmail.com"

4. Set autonomy stage to 1 (Captain approves every outreach):
   PUT /settings with: autonomy_stage=1, max_daily_outreach=20, outreach_countries=["UK","UAE","USA","AUS","Canada"]

5. Run first lead discovery manually:
   POST /discover/run with: industries=["SaaS","e-commerce","consulting"], countries=["UK","UAE"], limit=50

6. Review leads in dashboard /leads — set minimum score filter to 65

7. Select top 3 leads manually → click "Queue Outreach"

8. Check Captain Queue at /approvals — 3 outreach emails await approval

9. Review each email. If good → APPROVE. If needs editing → REJECT with note (JARVIS will rewrite)

10. After first 3 are approved and sent — monitor /outreach for opens and replies

11. First reply received → JARVIS will alert Captain via Slack + Telegram
    Go to /leads → find the lead → review JARVIS's drafted response → approve

12. First discovery call booked → JARVIS will build a demo → add to Captain Queue for approval

13. First proposal sent → JARVIS will track opens → follow up → close.

CAPTAIN: THE SYSTEM IS NOW LIVE. $1,000,000 STARTS HERE."""
    ))
    story.append(SP(10))
    story.append(HR(GOLD, 2))
    story.append(SP(8))
    story.append(Table([[
        Paragraph(
            "JARVIS vNEXT CODEX DEPLOYMENT BLUEPRINT\n"
            "Aliyar Solutions · CEO: Captain Syed Abrar\n"
            f"Generated: {datetime.now().strftime('%B %Y')}\n"
            "Revenue Target: $1,000,000 Year 1 · SMB-First Strategy\n"
            "Classification: CAPTAIN EYES ONLY",
            ParagraphStyle("footer", fontName="Helvetica-Bold", fontSize=10,
                textColor=WHITE, alignment=TA_CENTER, leading=16)
        )
    ]], colWidths=[W-60], style=TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), NAVY),
        ("TOPPADDING",(0,0),(-1,-1), 20),
        ("BOTTOMPADDING",(0,0),(-1,-1), 20),
        ("BOX",(0,0),(-1,-1), 2, GOLD),
    ])))
    return story

def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=28*mm,
        rightMargin=28*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title="JARVIS vNEXT Codex Deployment Blueprint",
        author="JARVIS — Aliyar Solutions",
    )
    story = []
    story.extend(cover())
    story.extend(how_to_use())
    story.extend(sprint1())
    story.extend(sprint2())
    story.extend(sprint3())
    story.extend(sprint4())
    story.extend(sprint5())
    story.extend(sprint6())
    story.extend(sprint7())
    story.extend(sprint8())
    story.extend(sprint9())
    story.extend(sprint10())
    story.extend(sprint11())
    story.extend(sprint12())
    story.extend(sprint_final())
    doc.build(story)
    print(f"Generated: {OUTPUT}")

if __name__ == "__main__":
    build()
