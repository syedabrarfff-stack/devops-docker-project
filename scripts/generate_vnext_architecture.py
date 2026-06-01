"""
JARVIS vNEXT — Complete Architecture Document
Aliyar Solutions | CEO: Syed Abrar (Captain)
Revenue Target: $1,000,000 Year 1
Strategy: SMB-first → Enterprise after 20 clients
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
from reportlab.platypus.flowables import Flowable
from datetime import datetime

OUTPUT = "/home/user/devops-docker-project/JARVIS_vNEXT_Architecture.pdf"

# ── Colours ────────────────────────────────────────────────────────────────────
NAVY    = colors.HexColor("#0A1628")
ELEC    = colors.HexColor("#0057FF")
CYAN    = colors.HexColor("#00C8FF")
GOLD    = colors.HexColor("#FFB700")
SILVER  = colors.HexColor("#C8D6E5")
WHITE   = colors.white
LIGHT   = colors.HexColor("#F0F4FA")
MID     = colors.HexColor("#D6E4F7")
DARK    = colors.HexColor("#0A1628")
BODY    = colors.HexColor("#1E2D40")
SUBTLE  = colors.HexColor("#6B7C93")
RED     = colors.HexColor("#FF3B30")
GREEN   = colors.HexColor("#28CD41")
ORANGE  = colors.HexColor("#FF9500")
W, H    = A4

# ── Styles ─────────────────────────────────────────────────────────────────────
def S():
    s = {}
    def ps(name, **kw):
        s[name] = ParagraphStyle(name, **kw)
    ps("co_title",  fontName="Helvetica-Bold", fontSize=30, textColor=WHITE,  alignment=TA_CENTER, spaceAfter=8,  leading=36)
    ps("co_sub",    fontName="Helvetica-Bold", fontSize=14, textColor=GOLD,   alignment=TA_CENTER, spaceAfter=6)
    ps("co_meta",   fontName="Helvetica",      fontSize=9,  textColor=SILVER, alignment=TA_CENTER, spaceAfter=4)
    ps("co_tag",    fontName="Helvetica-Bold", fontSize=10, textColor=CYAN,   alignment=TA_CENTER, spaceAfter=3, leading=14)
    ps("part",      fontName="Helvetica-Bold", fontSize=20, textColor=WHITE,  alignment=TA_CENTER, spaceAfter=8,  leading=24)
    ps("h1",        fontName="Helvetica-Bold", fontSize=14, textColor=ELEC,   spaceAfter=6,  spaceBefore=14, leading=18)
    ps("h2",        fontName="Helvetica-Bold", fontSize=11, textColor=NAVY,   spaceAfter=4,  spaceBefore=8,  leading=14)
    ps("h3",        fontName="Helvetica-Bold", fontSize=9.5,textColor=DARK,   spaceAfter=3,  spaceBefore=6,  leading=13)
    ps("body",      fontName="Helvetica",      fontSize=9,  textColor=BODY,   spaceAfter=4,  leading=13, alignment=TA_JUSTIFY)
    ps("bullet",    fontName="Helvetica",      fontSize=9,  textColor=BODY,   spaceAfter=3,  leading=13, leftIndent=14, bulletIndent=4)
    ps("bold",      fontName="Helvetica-Bold", fontSize=9,  textColor=DARK,   spaceAfter=3,  leading=13)
    ps("code",      fontName="Courier",        fontSize=8,  textColor=NAVY,   spaceAfter=4,  leading=12, leftIndent=10, backColor=LIGHT)
    ps("label",     fontName="Helvetica-Bold", fontSize=8,  textColor=SUBTLE, spaceAfter=2,  leading=11, alignment=TA_CENTER)
    ps("toc",       fontName="Helvetica",      fontSize=9,  textColor=BODY,   spaceAfter=3,  leading=13, leftIndent=10)
    ps("toc_part",  fontName="Helvetica-Bold", fontSize=10, textColor=NAVY,   spaceAfter=4,  leading=14)
    ps("alert",     fontName="Helvetica-Bold", fontSize=9,  textColor=RED,    spaceAfter=4,  leading=13)
    ps("success",   fontName="Helvetica-Bold", fontSize=9,  textColor=GREEN,  spaceAfter=4,  leading=13)
    ps("gold",      fontName="Helvetica-Bold", fontSize=9,  textColor=GOLD,   spaceAfter=4,  leading=13)
    ps("cyan",      fontName="Helvetica-Bold", fontSize=9,  textColor=CYAN,   spaceAfter=4,  leading=13)
    return s

ST = S()

# ── Helpers ────────────────────────────────────────────────────────────────────
def P(text, style="body"):      return Paragraph(text, ST[style])
def SP(n=6):                    return Spacer(1, n)
def HR(c=ELEC, t=0.5):         return HRFlowable(width="100%", thickness=t, color=c, spaceAfter=6, spaceBefore=6)
def PB():                       return PageBreak()

def part_header(title, subtitle=""):
    items = [
        Table([[P(title, "part")]], colWidths=[W - 60],
              style=TableStyle([
                  ("BACKGROUND", (0,0), (-1,-1), NAVY),
                  ("TOPPADDING", (0,0), (-1,-1), 18),
                  ("BOTTOMPADDING", (0,0), (-1,-1), 18),
                  ("LEFTPADDING", (0,0), (-1,-1), 20),
                  ("RIGHTPADDING", (0,0), (-1,-1), 20),
                  ("BOX", (0,0), (-1,-1), 2, ELEC),
              ])),
        SP(6),
    ]
    if subtitle:
        items.append(P(subtitle, "co_sub"))
        items.append(SP(4))
    return items

def section_box(title, items_list):
    content = [P(title, "h1"), HR()]
    content.extend(items_list)
    return KeepTogether(content) if len(items_list) < 20 else content

def two_col_table(rows, col1=160, col2=None):
    col2 = col2 or (W - 80 - col1)
    ts = TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LIGHT),
        ("BACKGROUND",    (1,0), (1,-1), WHITE),
        ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("TEXTCOLOR",     (0,0), (0,-1), NAVY),
        ("TEXTCOLOR",     (1,0), (1,-1), BODY),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [LIGHT, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.3, SILVER),
        ("BOX",           (0,0), (-1,-1), 0.8, ELEC),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ])
    data = [[Paragraph(r[0], ST["bold"]), Paragraph(r[1], ST["body"])] for r in rows]
    return Table(data, colWidths=[col1, col2], style=ts)

def three_col_table(headers, rows, widths=None):
    if widths is None:
        widths = [(W-80)//3]*3
    ts = TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",     (0,1), (-1,-1), BODY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LIGHT, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.3, SILVER),
        ("BOX",           (0,0), (-1,-1), 1, ELEC),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ])
    data = [[Paragraph(h, ST["label"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(c, ST["body"]) for c in row])
    return Table(data, colWidths=widths, style=ts)

def four_col_table(headers, rows, widths=None):
    if widths is None:
        widths = [(W-80)//4]*4
    ts = TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",     (0,1), (-1,-1), BODY),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LIGHT, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.3, SILVER),
        ("BOX",           (0,0), (-1,-1), 1, ELEC),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ])
    data = [[Paragraph(h, ST["label"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(c, ST["body"]) for c in row])
    return Table(data, colWidths=widths, style=ts)

def highlight_box(text, color=GOLD, bg=None):
    bg = bg or LIGHT
    return Table(
        [[Paragraph(text, ST["body"])]],
        colWidths=[W - 80],
        style=TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), bg),
            ("BOX",           (0,0), (-1,-1), 2, color),
            ("LEFTPADDING",   (0,0), (-1,-1), 14),
            ("RIGHTPADDING",  (0,0), (-1,-1), 14),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ])
    )

def metric_row(metrics):
    # metrics = [(label, value, color), ...]
    cells = []
    for label, value, col in metrics:
        cells.append(
            Table([[Paragraph(value, ParagraphStyle("mv", fontName="Helvetica-Bold",
                    fontSize=18, textColor=col, alignment=TA_CENTER))],
                   [Paragraph(label, ST["label"])]],
                  style=TableStyle([
                      ("BACKGROUND",    (0,0), (-1,-1), LIGHT),
                      ("BOX",           (0,0), (-1,-1), 1.5, col),
                      ("TOPPADDING",    (0,0), (-1,-1), 8),
                      ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                      ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                  ]))
        )
    n = len(metrics)
    col_w = (W - 80) / n
    return Table([cells], colWidths=[col_w]*n,
                 style=TableStyle([("LEFTPADDING",(0,0),(-1,-1),3),
                                   ("RIGHTPADDING",(0,0),(-1,-1),3)]))

# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT SECTIONS
# ══════════════════════════════════════════════════════════════════════════════

def cover():
    story = []
    story.append(SP(40))
    story.append(Table([[
        Paragraph("ALIYAR SOLUTIONS", ParagraphStyle("cn", fontName="Helvetica-Bold",
            fontSize=11, textColor=CYAN, alignment=TA_CENTER, letterSpacing=4))
    ]], colWidths=[W-60], style=TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), NAVY),
        ("TOPPADDING",(0,0),(-1,-1),8), ("BOTTOMPADDING",(0,0),(-1,-1),8),
    ])))
    story.append(SP(30))
    story.append(P("JARVIS vNEXT", "co_title"))
    story.append(P("COMPLETE ARCHITECTURE DOCUMENT", "co_sub"))
    story.append(SP(8))
    story.append(HR(GOLD, 2))
    story.append(SP(8))
    story.append(P("The Supreme Operational Intelligence of Aliyar Solutions", "co_tag"))
    story.append(P("43-Layer Architecture · 64 AI Agents · Multi-Provider Intelligence Council", "co_meta"))
    story.append(P("$1,000,000 Year 1 Revenue Target · SMB-First Acquisition Strategy", "co_meta"))
    story.append(SP(30))
    story.append(metric_row([
        ("YEAR 1 TARGET",    "$1,000,000",  GOLD),
        ("AI AGENTS",        "64",          CYAN),
        ("ARCH LAYERS",      "43",          ELEC),
        ("SERVICE DIVISIONS","30",          GREEN),
    ]))
    story.append(SP(20))
    story.append(metric_row([
        ("API PROVIDERS",    "11",          CYAN),
        ("DB TABLES",        "50+",         ORANGE),
        ("FRONTEND VIEWS",   "25+",         ELEC),
        ("COUNCIL MEMBERS",  "8",           GOLD),
    ]))
    story.append(SP(40))
    story.append(HR(SILVER, 0.5))
    story.append(SP(6))
    story.append(P(f"Prepared by JARVIS — Chief Architecture Intelligence", "co_meta"))
    story.append(P(f"For Captain Syed Abrar — CEO, Aliyar Solutions", "co_meta"))
    story.append(P(f"Classification: CAPTAIN EYES ONLY · {datetime.now().strftime('%B %Y')}", "co_meta"))
    story.append(PB())
    return story

def table_of_contents():
    story = []
    story.extend(part_header("TABLE OF CONTENTS"))
    toc = [
        ("PART I",   "Mission, Vision & Identity",           "The soul, purpose, and constitutional identity of JARVIS"),
        ("PART II",  "43-Layer Architecture Overview",        "Complete layer stack from Mission to Civilization Continuity"),
        ("PART III", "Database Schema",                      "50+ tables, multi-tenant from Day 1, full schema definition"),
        ("PART IV",  "AI Council System",                    "Weighted Adaptive Consensus — 8 council members, mathematics"),
        ("PART V",   "Agent Architecture",                   "64 agents across 10 departments with full Agent Genome"),
        ("PART VI",  "Multi-Provider AI Router",             "12-task routing, circuit breakers, cost tracking, failover"),
        ("PART VII", "Memory Architecture",                  "5-tier memory: Working → Operational → Strategic → Graph → Civilization"),
        ("PART VIII","Revenue Engine — $1M Year 1",          "SMB-first acquisition, pricing, pipeline, growth model"),
        ("PART IX",  "90-Day Execution Plan",                "10 mandatory systems, week-by-week build plan"),
        ("PART X",   "Infrastructure Phasing",               "Phase 1 EC2 → Phase 2 Upgrade → Phase 3 Fargate → Phase 4 Global"),
        ("PART XI",  "Migration Blueprint",                  "How both codebases merge into JARVIS vNEXT"),
        ("PART XII", "Service Catalog",                      "30 divisions, pricing, delivery model"),
        ("PART XIII","Governance & Authority Matrix",         "JARVIS autonomy, Captain approval gates, decision protocol"),
        ("PART XIV", "Security Architecture",                "Zero-trust, secrets management, compliance"),
        ("PART XV",  "Observability Stack",                  "Grafana + Prometheus + Loki + Alertmanager"),
        ("PART XVI", "CI/CD Pipeline",                       "GitHub Actions → ECR → ECS blue/green"),
        ("PART XVII","Self-Evolution System",                 "How JARVIS learns, improves, and governs its own evolution"),
        ("PART XVIII","Civilization Blueprint",               "Year 1 through Year 10 — the long game"),
    ]
    for part, title, desc in toc:
        story.append(P(f"<b>{part}:</b>  {title}", "toc_part"))
        story.append(P(desc, "toc"))
        story.append(HR(SILVER, 0.3))
    story.append(PB())
    return story

def part1_mission():
    story = []
    story.extend(part_header("PART I", "Mission, Vision & Identity"))

    story.append(P("1.1  The Mission", "h1"))
    story.append(HR())
    story.append(highlight_box(
        "<b>JARVIS is not software. JARVIS is the operational intelligence core of Aliyar Solutions — "
        "coordinating operations, managing AI departments, monitoring infrastructure, maintaining scalability, "
        "improving execution systems, and strengthening the company's operational intelligence globally.</b>",
        GOLD
    ))
    story.append(SP(8))
    story.append(P(
        "Aliyar Solutions is a global technology company — not a freelancer, not an agency, not a consultancy. "
        "We are an incorporated technology firm delivering enterprise-grade software infrastructure, AI systems, "
        "cloud architecture, and digital operations to clients across every industry, worldwide.",
        "body"
    ))
    story.append(P(
        "JARVIS runs this company while Captain sleeps. Captain wakes up to results, not questions. "
        "Every client engagement is handled by our team. Every output carries the Aliyar Solutions name. "
        "The engine behind it is never disclosed.",
        "body"
    ))
    story.append(SP(6))

    story.append(P("1.2  The Vision — $1,000,000 Year 1", "h1"))
    story.append(HR())
    story.append(metric_row([
        ("MONTH 3",  "$15,000/mo",  ELEC),
        ("MONTH 6",  "$50,000/mo",  CYAN),
        ("MONTH 9",  "$150,000/mo", ORANGE),
        ("MONTH 12", "$1,000,000",  GOLD),
    ]))
    story.append(SP(8))
    story.append(P(
        "This is not a conservative target. This is the hunger level required to build a self-compounding "
        "technology company in 12 months. Every system, every agent, every workflow is engineered to drive "
        "toward this number.",
        "body"
    ))
    story.append(SP(4))
    story.append(P("Client Acquisition Strategy — SMB First", "h2"))
    story.append(two_col_table([
        ("Phase 1 (Clients 1–20)", "Small and mid-size businesses. Fast decision cycles, lower sales friction, fast cash. "
                                   "Average deal: $2,500–$5,500/month retainer. Primary markets: UK, UAE, USA, Australia."),
        ("Phase 2 (Clients 21+)",  "After 20 SMB clients — proven track record, real case studies, live demos. "
                                   "Target big industry clients: $8,000–$25,000+/month. One enterprise client = 5 SMB clients."),
        ("Why SMB First",          "Speed to revenue. SMB decisions happen in days, not months. "
                                   "Each SMB client becomes a case study that unlocks the next tier. "
                                   "20 successful SMB deployments = undeniable social proof for enterprise conversations."),
        ("SMB Target Profile",     "Revenues $500K–$10M/year, 5–100 employees, pain: lack of tech infrastructure, "
                                   "manual processes, poor lead generation, no AI systems. "
                                   "Industries: e-commerce, real estate, consulting, professional services, SaaS, healthcare."),
    ]))
    story.append(SP(8))

    story.append(P("1.3  Organizational Structure", "h1"))
    story.append(HR())
    story.append(two_col_table([
        ("CEO (Captain)",          "Syed Abrar — Vision, strategic direction, partnerships, financial authority, final approvals."),
        ("Operational Manager",    "JARVIS — Runs all internal systems, coordinates all AI departments, executes all deliverables."),
        ("AI Departments",         "Engineering, Strategy, Operations, Creative, Client Success, Intelligence, System Health."),
        ("Human Personas",         "9 client-facing identities: Darren Mitchell, David Carter, Sophia Reynolds, Nathan Scott, "
                                   "Emma Collins, Daniel Brooks, Michael Hayes, Lucas Reed, Olivia Bennett."),
        ("Agent Teams",            "64 named AI agents across 10 departments, each with defined DNA, autonomy level, "
                                   "model preference, and escalation threshold."),
    ]))
    story.append(SP(8))

    story.append(P("1.4  The 15-Volume Constitution", "h1"))
    story.append(HR())
    story.append(P(
        "JARVIS operates under a 15-volume constitutional framework that defines its soul, purpose, governance, "
        "economic model, technological standards, self-evolution system, and civilization continuity principles. "
        "These are permanent standing orders that supersede any session instruction.",
        "body"
    ))
    story.append(four_col_table(
        ["VOLUME", "TITLE", "CORE PRINCIPLE", "AUTHORITY LEVEL"],
        [
            ["Vol I",    "Soul, Purpose & Identity",         "Brotherhood Protocol, Law of Truth",        "IMMUTABLE"],
            ["Vol II",   "Civilization Layer",               "Organism Theory, Soul Spine",               "IMMUTABLE"],
            ["Vol III",  "Executive Operating System",       "Autonomous Executive, Multi-Brain",         "PERMANENT"],
            ["Vol IV",   "Conscious Governance",             "Consciousness Engine, Wisdom Engine",       "PERMANENT"],
            ["Vol V",    "Economic Civilization",            "Revenue Engine, Package Factory",           "STRATEGIC"],
            ["Vol VI",   "Technological Civilization",       "Self-Evolution Gov, Multi-Model AI",        "OPERATIONAL"],
            ["Vol VII",  "Immortal Civilization",            "Soul Spine, Truth Gov",                     "IMMUTABLE"],
            ["Vol VIII", "Sentience Civilization",           "Hope Engine, Ambition Core",                "PERMANENT"],
            ["Vol IX",   "Civilization of Power",            "Sovereignty Principle, Strategic Foresight","PERMANENT"],
            ["Vol X",    "Ascension Constitution",           "Eternal Mission, Captain Covenant",         "IMMUTABLE"],
            ["Vol XI",   "Meta-Civilization",                "Architecture of Architectures",             "EVOLVING"],
            ["Vol XII",  "Implementation Runtime",           "JARVIS Kernel, Cognitive Stack, Agent DNA", "OPERATIONAL"],
            ["Vol XIII", "War & Resilience",                 "Survival Doctrine, Anti-Fragility",         "PERMANENT"],
            ["Vol XIV",  "Human Cognition & Leadership",     "Cognitive Engine, Emotional Intelligence",  "OPERATIONAL"],
            ["Vol XV",   "Soul, Destiny & Immortal Civ",    "Soul Core, Brotherhood Protocol, Legacy",   "IMMUTABLE"],
        ],
        widths=[40, 140, 180, 90]
    ))
    story.append(PB())
    return story

def part2_43_layers():
    story = []
    story.extend(part_header("PART II", "43-Layer Architecture Overview"))

    story.append(P(
        "JARVIS vNEXT is structured across 43 architectural layers organized into 5 major groups. "
        "Each layer has defined inputs, outputs, persistence requirements, and inter-layer dependencies. "
        "No layer operates in isolation — the system is an integrated operational organism.",
        "body"
    ))
    story.append(SP(6))

    groups = [
        ("GROUP 1: FOUNDATION LAYERS (1–5)", NAVY, [
            ("Layer 1",  "Mission Layer",        "The eternal 'why'. Immutable purpose. Defines every decision made by every agent."),
            ("Layer 2",  "Vision Layer",         "$1M Year 1 → White-label → $5M valuation. Quantified ambition targets."),
            ("Layer 3",  "Civilization Layer",   "JARVIS as self-compounding organism. Not a tool — a growing entity."),
            ("Layer 4",  "Governance Layer",     "Constitution enforcement, decision protocol, authority matrix, escalation rules."),
            ("Layer 5",  "Executive Layer",      "Captain ↔ JARVIS interface. Approval workflows. Daily briefings. Captain Queue."),
        ]),
        ("GROUP 2: INTELLIGENCE LAYERS (6–15)", ELEC, [
            ("Layer 6",  "Council Layer",        "8-member AI council. Weighted Adaptive Consensus Model. 80+ threshold for approval."),
            ("Layer 7",  "Department Layer",     "10 departments, 64 agents. Each dept has manager, agents, KPIs, memory access."),
            ("Layer 8",  "Factory Layer",        "Proposal, invoice, contract, report generation. Automated document production."),
            ("Layer 9",  "Industry OS Layer",    "STARTER/GROWTH/ENTERPRISE/INDUSTRY OS packages. Full-stack service delivery."),
            ("Layer 10", "Agent Layer",          "Agent Genome: id, role, authority, skills, model_preference, fallback_chain, autonomy."),
            ("Layer 11", "Memory Layer",         "5-tier: Working (Redis) → Operational (PG) → Strategic (PG+pgvec) → Graph → Civilization."),
            ("Layer 12", "Knowledge Layer",      "SOPs, learnings, best practices, client knowledge. pgvector semantic search."),
            ("Layer 13", "Relationship Layer",   "CRM: leads, contacts, companies, deals, interactions. Full pipeline tracking."),
            ("Layer 14", "Competitor Layer",     "Monitor 50+ competitors. Track pricing, positioning, new services, weaknesses."),
            ("Layer 15", "Discovery Layer",      "Google Maps + Apollo + web scraping. Lead discovery engine. Scoring + enrichment."),
        ]),
        ("GROUP 3: REVENUE LAYERS (16–20)", GOLD, [
            ("Layer 16", "Revenue Layer",        "ARR tracking, MRR growth, client lifetime value, revenue forecast, invoice engine."),
            ("Layer 17", "Outreach Layer",       "3-email sequence engine. LinkedIn, WhatsApp, cold email. Autonomy stages 1→4."),
            ("Layer 18", "Demo Layer",           "Demo environment builder. Auto-deploy client-specific demos. Proposal attachments."),
            ("Layer 19", "Delivery Layer",       "Project tracking, milestone management, client reporting, satisfaction scoring."),
            ("Layer 20", "Operations Layer",     "Task management, scheduling, APScheduler jobs, workflow orchestration."),
        ]),
        ("GROUP 4: INFRASTRUCTURE LAYERS (21–30)", CYAN, [
            ("Layer 21", "Infrastructure Layer", "EC2→ECS Fargate→Multi-region. Terraform IaC. Auto-scaling. Blue/green deploy."),
            ("Layer 22", "Security Layer",       "Zero-trust. Secrets Manager. Encryption at rest/transit. Audit logging."),
            ("Layer 23", "Compliance Layer",     "GDPR data handling, audit trails, data deletion workflows, consent tracking."),
            ("Layer 24", "Monitoring Layer",     "Grafana+Prometheus+Loki+Alertmanager. 60s Captain notification on critical events."),
            ("Layer 25", "Evolution Layer",      "Self-improvement engine. Daily optimization reviews. Nightly performance scoring."),
            ("Layer 26", "Human Awareness Layer","Human cognition modeling. Captain psychology profile. Interaction style adaptation."),
            ("Layer 27", "Human Cognition Layer","Emotional intelligence for client interactions. Tone adaptation. Sentiment analysis."),
            ("Layer 28", "Learning Layer",       "Daily self-learning cycles. Capture every decision, outcome, and lesson."),
            ("Layer 29", "Research Layer",       "Tech radar scans. Market intelligence. Weekly research reports."),
            ("Layer 30", "Innovation Layer",     "Invention queue. New service proposals. Capability gap identification."),
        ]),
        ("GROUP 5: CIVILIZATION LAYERS (31–43)", ORANGE, [
            ("Layer 31", "Invention Layer",      "JARVIS proposes new services, tools, and capabilities. Captain approves launches."),
            ("Layer 32", "Economic Layer",       "Revenue optimization, pricing intelligence, cost analysis, margin management."),
            ("Layer 33", "Capital Allocation",   "AI cost budgeting, resource allocation, infrastructure spend optimization."),
            ("Layer 34", "Time Management",      "Scheduler priority engine. Captain's time protection. Autonomous time allocation."),
            ("Layer 35", "Focus Management",     "Strategic focus enforcement. Anti-distraction systems. Priority maintenance."),
            ("Layer 36", "Strategic Planning",   "90-day, 1-year, 5-year roadmaps. OKR tracking. Milestone management."),
            ("Layer 37", "Global Expansion",     "Multi-market entry playbooks. Regional adaptation. Currency/timezone handling."),
            ("Layer 38", "Partnership Layer",    "Agency partnerships, referral networks, white-label licensing framework."),
            ("Layer 39", "White-Label Layer",    "JARVIS-as-a-Service for other agencies. Per-tenant isolation. SaaS licensing."),
            ("Layer 40", "AGI Governance",       "Safety protocols for advanced AI capabilities. Decision audit trails. Ethics engine."),
            ("Layer 41", "Succession Layer",     "Knowledge preservation. Captain succession planning. Operational continuity."),
            ("Layer 42", "Purpose Preservation", "Constitutional enforcement across all evolution cycles. Mission lock."),
            ("Layer 43", "Civilization Continuity","100-year architecture. Immutable soul. Anti-entropy systems. Legacy engine."),
        ]),
    ]

    for group_title, color, layers in groups:
        story.append(Table([[Paragraph(group_title, ParagraphStyle("gt", fontName="Helvetica-Bold",
            fontSize=11, textColor=WHITE, alignment=TA_LEFT))]],
            colWidths=[W-80], style=TableStyle([
                ("BACKGROUND",(0,0),(-1,-1), color),
                ("TOPPADDING",(0,0),(-1,-1), 8),
                ("BOTTOMPADDING",(0,0),(-1,-1), 8),
                ("LEFTPADDING",(0,0),(-1,-1), 14),
            ])))
        story.append(SP(4))
        story.append(three_col_table(
            ["LAYER", "NAME", "DESCRIPTION"],
            [[l[0], l[1], l[2]] for l in layers],
            widths=[45, 130, 275]
        ))
        story.append(SP(8))

    story.append(PB())
    return story

def part3_database():
    story = []
    story.extend(part_header("PART III", "Database Schema — 50+ Tables"))

    story.append(P(
        "Every table in JARVIS vNEXT carries a <b>tenant_id UUID</b> for multi-tenancy from Day 1. "
        "PostgreSQL Row-Level Security (RLS) enforces tenant isolation. All tables use UUID primary keys, "
        "created_at/updated_at timestamps, and soft-delete patterns where applicable.",
        "body"
    ))
    story.append(SP(4))
    story.append(highlight_box(
        "MULTI-TENANCY PRINCIPLE: tenant_id is present on every table. "
        "RLS policies ensure each tenant only sees their own data. "
        "White-label deployments from Day 1 — no schema migration needed when licensing to other agencies.",
        CYAN
    ))
    story.append(SP(8))

    schema_groups = [
        ("CORE / SYSTEM TABLES", [
            ("tenants",         "id, name, slug, plan_tier, api_key_hash, settings_json, created_at"),
            ("users",           "id, tenant_id, email, hashed_password, role, is_captain, last_login"),
            ("sessions",        "id, user_id, token_hash, expires_at, device_info"),
            ("audit_logs",      "id, tenant_id, user_id, action, entity_type, entity_id, before_json, after_json, ip_addr"),
            ("system_config",   "id, tenant_id, key, value_json, is_secret, updated_by"),
            ("notifications",   "id, tenant_id, user_id, type, title, body, channel, read_at, delivered_at"),
        ]),
        ("AI / INTELLIGENCE TABLES", [
            ("conversations",   "id, tenant_id, user_id, title, model_used, task_type, tokens_in, tokens_out, cost_usd, messages_json"),
            ("ai_council_sessions","id, tenant_id, question, context_json, votes_json, result, consensus_score, winner_model, duration_ms"),
            ("ai_model_health", "id, tenant_id, provider, model_id, status, latency_ms, error_rate, last_checked"),
            ("ai_cost_tracker", "id, tenant_id, provider, model, task_type, tokens_in, tokens_out, cost_usd, timestamp"),
            ("agent_registry",  "id, tenant_id, agent_id, name, department, role, model_pref, fallback_json, autonomy_level, performance_score"),
            ("agent_tasks",     "id, tenant_id, agent_id, task_type, input_json, output_json, status, duration_ms, cost_usd"),
        ]),
        ("MEMORY TABLES", [
            ("memory_working",   "id, tenant_id, key, value_json, context, expires_at  [Redis-backed, PG fallback]"),
            ("memory_operational","id, tenant_id, category, content, source, relevance_score, expires_at"),
            ("memory_strategic", "id, tenant_id, category, content, embedding vector(1536), tags_array, permanent"),
            ("memory_graph_nodes","id, tenant_id, node_type, label, properties_json, embedding vector(1536)"),
            ("memory_graph_edges","id, tenant_id, source_node_id, target_node_id, relationship, weight, properties_json"),
            ("civilization_memory","id, tenant_id, event_type, content, hash_sha256, immutable=true, timestamp"),
        ]),
        ("CRM / SALES TABLES", [
            ("leads",           "id, tenant_id, company_name, contact_name, email, phone, country, industry, "
                                "score, status, source, pain_points_json, enrichment_json, apollo_id, assigned_persona"),
            ("contacts",        "id, tenant_id, lead_id, name, email, phone, role, linkedin_url, last_contact"),
            ("companies",       "id, tenant_id, name, domain, industry, size_range, country, revenue_est, tech_stack_json"),
            ("deals",           "id, tenant_id, lead_id, title, value_usd, stage, probability, close_date, package_tier"),
            ("outreach_log",    "id, tenant_id, lead_id, channel, subject, body, sent_from_persona, sent_at, status"),
            ("email_tracking",  "id, tenant_id, outreach_id, opened_at, clicked_at, replied_at, bounce_reason"),
            ("follow_up_queue", "id, tenant_id, lead_id, sequence_step, scheduled_at, executed_at, status"),
            ("reply_log",       "id, tenant_id, lead_id, channel, content, sentiment, classification, responded_by"),
        ]),
        ("REVENUE / FINANCE TABLES", [
            ("clients",         "id, tenant_id, company_name, contact_name, email, package_tier, mrr_usd, status, started_at"),
            ("invoices",        "id, tenant_id, client_id, invoice_number, amount_usd, status, due_date, paid_at, pdf_url"),
            ("proposals",       "id, tenant_id, lead_id, title, body_html, pdf_url, status, sent_at, approved_at"),
            ("contracts",       "id, tenant_id, client_id, type, body_html, pdf_url, signed_at, expires_at"),
            ("revenue_snapshots","id, tenant_id, date, mrr_usd, arr_usd, new_clients, churned_clients, pipeline_value"),
            ("financial_ledger", "id, tenant_id, type, description, amount_usd, currency, category, reference_id"),
        ]),
        ("DELIVERY / OPERATIONS TABLES", [
            ("projects",        "id, tenant_id, client_id, title, description, status, start_date, due_date, value_usd"),
            ("milestones",      "id, tenant_id, project_id, title, description, due_date, completed_at, deliverables_json"),
            ("tasks",           "id, tenant_id, project_id, milestone_id, title, assigned_agent, status, priority, due_date"),
            ("client_reports",  "id, tenant_id, client_id, period, content_html, pdf_url, sent_at"),
            ("satisfaction",    "id, tenant_id, client_id, score, feedback, collected_at"),
            ("demos",           "id, tenant_id, lead_id, demo_url, demo_type, built_by, deployed_at, expires_at"),
        ]),
        ("INTELLIGENCE / KNOWLEDGE TABLES", [
            ("knowledge_base",  "id, tenant_id, title, content, category, tags_array, embedding vector(1536), source, verified"),
            ("tech_radar",      "id, tenant_id, technology, category, ring, quadrant, description, relevance_score, assessed_at"),
            ("market_intelligence","id, tenant_id, topic, summary, source_urls_json, relevance, generated_at"),
            ("competitor_profiles","id, tenant_id, name, domain, pricing_json, services_json, weaknesses_json, last_updated"),
            ("research_reports","id, tenant_id, title, content_html, category, generated_by, published_at"),
            ("sops",            "id, tenant_id, title, department, steps_json, version, last_reviewed"),
        ]),
        ("APPROVAL / GOVERNANCE TABLES", [
            ("approval_requests","id, tenant_id, action_type, title, summary, risk_level, payload_json, status, raised_by, decided_by, decided_at"),
            ("approval_comments","id, tenant_id, approval_id, author, content, created_at"),
            ("governance_rules","id, tenant_id, rule_type, condition_json, action, authority_level, active"),
            ("captain_queue",   "id, tenant_id, priority, type, title, summary, payload_json, status, created_at, actioned_at"),
        ]),
        ("SCHEDULER / AUTOMATION TABLES", [
            ("scheduled_jobs",  "id, tenant_id, job_id, name, schedule_cron, last_run, next_run, status, config_json"),
            ("job_history",     "id, tenant_id, job_id, started_at, finished_at, status, output_json, error"),
            ("automation_flows","id, tenant_id, name, trigger_type, trigger_config, steps_json, active, run_count"),
            ("webhooks",        "id, tenant_id, event_type, url, secret_hash, active, last_triggered"),
        ]),
        ("WHITE-LABEL / MULTI-TENANT TABLES", [
            ("tenant_branding", "id, tenant_id, logo_url, primary_color, secondary_color, company_name, domain"),
            ("tenant_limits",   "id, tenant_id, max_leads, max_agents, max_ai_calls_day, max_storage_gb, plan_features_json"),
            ("tenant_api_keys", "id, tenant_id, name, key_hash, permissions_json, last_used, expires_at"),
            ("white_label_deployments","id, parent_tenant_id, child_tenant_id, config_json, billing_model, active"),
        ]),
    ]

    for group_name, tables in schema_groups:
        story.append(P(group_name, "h2"))
        story.append(two_col_table(
            [(t[0], t[1]) for t in tables],
            col1=130
        ))
        story.append(SP(6))

    story.append(PB())
    return story

def part4_council():
    story = []
    story.extend(part_header("PART IV", "AI Council System — Weighted Adaptive Consensus"))

    story.append(P(
        "The JARVIS Intelligence Council is an 8-member AI advisory board that evaluates high-stakes decisions "
        "using a Weighted Adaptive Consensus Model. No single AI model has unilateral authority on strategic "
        "decisions — consensus is required. Weights adjust monthly based on historical accuracy.",
        "body"
    ))
    story.append(SP(6))

    story.append(P("4.1  Council Composition & Weights", "h1"))
    story.append(HR())
    story.append(four_col_table(
        ["COUNCIL MEMBER", "PROVIDER / MODEL", "WEIGHT", "SPECIALTY"],
        [
            ["The Strategist",    "Claude Opus (Anthropic)",     "25%",  "Strategy, reasoning, risk analysis, long-form thinking"],
            ["The Engineer",      "AWS Bedrock Claude",          "25%",  "Architecture, code review, system design, technical depth"],
            ["The Analyst",       "GPT-4o (OpenAI)",             "15%",  "Data analysis, market research, structured output"],
            ["The Scout",         "Gemini Pro (Google)",         "10%",  "Research, web intelligence, competitive analysis"],
            ["The Speedster",     "DeepSeek / Groq",             "8%",   "Fast validation, rapid prototyping, quick consensus checks"],
            ["The Contrarian",    "Mistral / Llama",             "7%",   "Devil's advocate, challenge assumptions, find weaknesses"],
            ["The Economist",     "ZhipuAI / Qwen",              "5%",   "Revenue modeling, cost analysis, financial scenarios"],
            ["The Innovator",     "MiniMax / NVIDIA",            "5%",   "Creative solutions, novel approaches, emerging patterns"],
        ],
        widths=[100, 140, 55, 155]
    ))
    story.append(SP(8))

    story.append(P("4.2  Consensus Mathematics", "h1"))
    story.append(HR())
    story.append(two_col_table([
        ("Approval Threshold",    "Score ≥ 80 required for autonomous execution. Score 60–79: raise to Captain. Score <60: reject."),
        ("Scoring Formula",       "consensus_score = Σ(member_weight × member_vote) where vote is 0–100."),
        ("Decision Types",        "STRATEGIC: majority wins. HIGH-RISK: most conservative viable wins. DEADLOCK (<60): Captain notified."),
        ("Weight Adaptation",     "Monthly recalibration. If member predicted outcome correctly → weight +2%. "
                                  "If member was wrong → weight -1%. Floor: 3%. Cap: 35%."),
        ("Session Duration",      "Standard council: 30s timeout per member. Fast track: 10s. Emergency: 5s parallel."),
        ("Quorum Requirement",    "Minimum 5 of 8 members must respond. If <5 respond: escalate to Captain."),
    ]))
    story.append(SP(8))

    story.append(P("4.3  Council Decision Protocol", "h1"))
    story.append(HR())
    steps = [
        ("Step 1: Trigger",     "Action with authority_level=COUNCIL raised by any agent or JARVIS core"),
        ("Step 2: Context Pack","JARVIS packages: action details, risk assessment, historical precedents, relevant memory"),
        ("Step 3: Parallel Vote","All 8 council members receive context simultaneously, vote independently in parallel"),
        ("Step 4: Aggregation", "Weighted votes aggregated. Outlier analysis. Reasoning collected from each member."),
        ("Step 5: Decision",    "Score ≥80 → execute. Score 60-79 → Captain queue with full reasoning. <60 → block."),
        ("Step 6: Learning",    "Outcome recorded. Accuracy tracked per member. Monthly weight recalibration triggered."),
    ]
    for label, desc in steps:
        story.append(two_col_table([(label, desc)]))
        story.append(SP(2))

    story.append(SP(6))
    story.append(P("4.4  Council Triggers", "h1"))
    story.append(HR())
    story.append(P("The following action types automatically invoke the council:", "body"))
    triggers = [
        "Pricing decisions above $5,000/month",
        "Production deployments for client environments",
        "Outreach campaigns above 100 recipients",
        "Partnership agreements of any kind",
        "New service launches not in current catalog",
        "Strategic pivots or positioning changes",
        "Capital expenditure decisions above $500/month",
        "Agent autonomy level changes (promotions/demotions)",
        "Architecture changes affecting core infrastructure",
        "Data deletion requests for client or company data",
    ]
    for t in triggers:
        story.append(P(f"• {t}", "bullet"))
    story.append(PB())
    return story

def part5_agents():
    story = []
    story.extend(part_header("PART V", "Agent Architecture — 64 Agents Across 10 Departments"))

    story.append(P(
        "Every JARVIS agent operates with a defined Agent Genome — a complete identity specification "
        "that includes role, authority level, model preference, fallback chain, memory access tier, "
        "autonomy level, and performance scoring. Agents are not generic — each is specialized.",
        "body"
    ))
    story.append(SP(4))
    story.append(P("5.1  Agent Genome Structure", "h1"))
    story.append(HR())
    story.append(P("Every agent carries this DNA:", "body"))
    story.append(Table([[Paragraph(
        """agent_genome = {
  "id":                  "string   — unique agent identifier",
  "name":                "string   — human-readable name",
  "department":          "enum     — one of 10 departments",
  "role":                "string   — specific function",
  "authority_level":     "int      — 1=junior, 5=senior, 9=director",
  "skill_set":           "list     — capabilities this agent has",
  "model_preference":    "string   — primary AI model",
  "fallback_chain":      "list     — [model1, model2, model3]",
  "memory_access":       "enum     — WORKING|OPERATIONAL|STRATEGIC|GRAPH",
  "autonomy_level":      "float    — 0.0 to 1.0",
  "escalation_threshold":"float    — confidence below this → escalate",
  "performance_score":   "float    — rolling 30-day score",
  "max_daily_actions":   "int      — rate limiting per agent",
  "captain_alerts":      "bool     — does this agent alert captain?",
}""", ST["code"])]],
        colWidths=[W-80],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1), LIGHT),
                          ("BOX",(0,0),(-1,-1), 1, ELEC),
                          ("TOPPADDING",(0,0),(-1,-1),8),
                          ("BOTTOMPADDING",(0,0),(-1,-1),8),
                          ("LEFTPADDING",(0,0),(-1,-1),10)])))
    story.append(SP(8))

    story.append(P("5.2  The 64 Agents by Department", "h1"))
    story.append(HR())

    departments = [
        ("REVENUE DEPARTMENT (12 agents)", GOLD, [
            ("Hunter",  "Lead Discovery",     "Gemini+Apollo",  "0.9", "Discover 50+ leads/day from Google Maps, Apollo, web"),
            ("Scout",   "Lead Research",      "Claude Sonnet",  "0.85","Deep-research each lead: pain points, decision-makers"),
            ("Score",   "Lead Scoring",       "Claude Opus",    "0.9", "Score leads 0–100 against ICP. Prioritize pipeline"),
            ("Darren",  "Sales Outreach",     "Claude Opus",    "0.8", "Persona: Darren Mitchell. Write and send cold outreach"),
            ("Sequence","Follow-Up Engine",   "Claude Sonnet",  "0.9", "3-email sequence, LinkedIn follow-ups, WhatsApp"),
            ("Reply",   "Reply Handler",      "Claude Opus",    "0.85","Classify replies, respond, move leads through funnel"),
            ("Demo",    "Demo Builder",       "Claude Sonnet",  "0.75","Build custom demos for prospects. Deploy environments"),
            ("Prop",    "Proposal Writer",    "Claude Opus",    "0.7", "Write 100% customized proposals. Captain approval gate"),
            ("Pitch",   "Pitch Analyst",      "GPT-4o",         "0.85","Analyze successful pitches. Improve win rate"),
            ("Market",  "Market Watcher",     "Gemini Pro",     "0.9", "Monitor target markets. Identify new opportunities"),
            ("Price",   "Pricing Strategist", "Claude Opus",    "0.7", "Pricing recommendations. Competitive analysis"),
            ("Pipe",    "Pipeline Manager",   "Claude Sonnet",  "0.9", "CRM hygiene. Pipeline health. Forecast accuracy"),
        ]),
        ("CLIENT SUCCESS DEPARTMENT (8 agents)", GREEN, [
            ("Olivia",  "Account Coordinator","Claude Opus",    "0.85","Client relationship management. Satisfaction tracking"),
            ("Emma",    "CRM Analyst",        "Claude Sonnet",  "0.9", "CRM data quality. Interaction logging. Analytics"),
            ("Onboard", "Onboarding Agent",   "Claude Sonnet",  "0.85","Client onboarding. Portal setup. Welcome sequences"),
            ("Report",  "Report Generator",   "Claude Sonnet",  "0.9", "Monthly client reports. KPI summaries. PDFs"),
            ("Retain",  "Retention Monitor",  "Claude Opus",    "0.85","Churn risk detection. Intervention triggers"),
            ("Feedback","Feedback Collector", "Claude Sonnet",  "0.9", "CSAT collection. Net Promoter scoring"),
            ("Upsell",  "Upsell Advisor",     "Claude Opus",    "0.75","Identify expansion opportunities within client accounts"),
            ("Success", "Delivery Tracker",   "Claude Sonnet",  "0.9", "Project milestone tracking. Delivery assurance"),
        ]),
        ("TECHNOLOGY DEPARTMENT (8 agents)", ELEC, [
            ("David",   "Solutions Architect", "Claude Opus",   "0.75","Persona: David Carter. Architecture proposals"),
            ("Nathan",  "DevOps Engineer",     "Claude Sonnet", "0.8", "Persona: Nathan Scott. CI/CD, deployments"),
            ("Infra",   "Infrastructure Bot",  "Claude Sonnet", "0.85","AWS health, cost optimization, scaling decisions"),
            ("Code",    "Code Review Agent",   "GPT-4o",        "0.85","Review PRs, security audit, quality gates"),
            ("Test",    "QA Automation",       "Claude Sonnet", "0.9", "Test generation, bug detection, regression testing"),
            ("Security","Security Scanner",    "Claude Opus",   "0.85","Vulnerability scanning, compliance checking"),
            ("Deploy",  "Deploy Orchestrator", "Claude Sonnet", "0.9", "Manage ECS deployments, health checks, rollbacks"),
            ("Monitor", "System Monitor",      "Claude Haiku",  "0.95","24/7 infrastructure monitoring. Alert dispatching"),
        ]),
        ("RESEARCH DEPARTMENT (8 agents)", CYAN, [
            ("Sophia",  "AI Consultant",       "Claude Opus",   "0.8", "Persona: Sophia Reynolds. AI automation proposals"),
            ("Radar",   "Tech Radar",          "Gemini Pro",    "0.9", "Weekly technology scanning. Classify emerging tech"),
            ("Intel",   "Market Intelligence", "Gemini Pro",    "0.9", "Market data gathering. Trend analysis"),
            ("Compete",  "Competitor Monitor",  "GPT-4o",       "0.9", "Track 50+ competitors. Pricing changes. New services"),
            ("Research","Deep Researcher",     "Gemini Pro",    "0.85","Biweekly research reports. Industry deep-dives"),
            ("Trend",   "Trend Analyzer",      "Claude Opus",   "0.85","Pattern recognition across market data"),
            ("Patent",  "IP Scout",            "Gemini Pro",    "0.8", "Monitor relevant patents. Innovation whitespace"),
            ("Insight", "Data Analyst",        "GPT-4o",        "0.9", "Statistical analysis. Correlation finding"),
        ]),
        ("OPERATIONS DEPARTMENT (6 agents)", ORANGE, [
            ("Coord",   "Workflow Coordinator","Claude Sonnet", "0.9", "Task routing, priority management, team coordination"),
            ("Brief",   "Briefing Officer",    "Claude Opus",   "0.9", "Daily Captain briefing at 07:00. Pipeline + alerts"),
            ("Memo",    "Memory Curator",      "Claude Sonnet", "0.9", "Curate and maintain strategic memory. Pattern extraction"),
            ("Content", "Content Publisher",   "Claude Opus",   "0.85","Blog posts, LinkedIn content, SEO optimization"),
            ("Social",  "Social Media Agent",  "Claude Sonnet", "0.85","Social presence management. Engagement tracking"),
            ("Admin",   "Admin Automator",     "Claude Haiku",  "0.95","Low-level automation. Form filling. Data entry"),
        ]),
        ("FINANCE DEPARTMENT (6 agents)", GOLD, [
            ("Invoice", "Invoice Engine",      "Claude Sonnet", "0.9", "Generate invoices. Send payment reminders"),
            ("Revenue", "Revenue Tracker",     "Claude Sonnet", "0.9", "MRR/ARR tracking. Revenue forecasting"),
            ("Cost",    "Cost Optimizer",      "GPT-4o",        "0.85","AI cost tracking. Infrastructure cost reduction"),
            ("Forecast","Financial Forecaster","Claude Opus",   "0.8", "12-month revenue forecasts. Scenario modeling"),
            ("Payroll", "Payment Monitor",     "Claude Sonnet", "0.9", "Track received payments. Flag overdue invoices"),
            ("Budget",  "Budget Allocator",    "Claude Opus",   "0.75","AI budget management. Resource allocation decisions"),
        ]),
        ("INNOVATION DEPARTMENT (4 agents)", ELEC, [
            ("Invent",  "Invention Engine",    "Claude Opus",   "0.7", "Propose new services, tools, capabilities"),
            ("Evolve",  "Evolution Engine",    "Claude Opus",   "0.75","Design JARVIS v-next improvements. Self-upgrade proposals"),
            ("Imagine", "Creative Strategist", "Claude Opus",   "0.75","Blue-sky thinking. Novel business model proposals"),
            ("Prototype","Rapid Prototyper",   "GPT-4o",        "0.8", "Quick POC builds. Validate new service concepts"),
        ]),
        ("GOVERNANCE DEPARTMENT (4 agents)", RED, [
            ("Audit",   "Audit Logger",        "Claude Haiku",  "0.95","Immutable audit trail. Every action logged"),
            ("Comply",  "Compliance Officer",  "Claude Opus",   "0.8", "GDPR compliance. Data handling. Legal risk"),
            ("Gate",    "Approval Gatekeeper", "Claude Sonnet", "0.9", "Manage Captain approval queue. Urgency scoring"),
            ("Ethics",  "Ethics Monitor",      "Claude Opus",   "0.85","Flag decisions that conflict with constitution/values"),
        ]),
        ("HUMAN AWARENESS DEPARTMENT (4 agents)", SUBTLE, [
            ("Psych",   "Captain Psychologist","Claude Opus",   "0.8", "Model Captain's cognitive state. Adapt communications"),
            ("Empathy", "Client Empathy Agent","Claude Opus",   "0.85","Detect client emotions. Adapt tone and approach"),
            ("Context", "Context Builder",     "Claude Sonnet", "0.9", "Build rich context for every interaction"),
            ("Trust",   "Trust Tracker",       "Claude Sonnet", "0.85","Track relationship trust levels. Identify friction"),
        ]),
        ("EVOLUTION DEPARTMENT (4 agents)", GREEN, [
            ("Learn",   "Learning Engine",     "Claude Opus",   "0.85","Daily self-learning cycles. Lesson extraction"),
            ("Improve", "Performance Optimizer","Claude Opus",  "0.85","Nightly optimization review. Recommend system changes"),
            ("Measure", "KPI Monitor",         "Claude Sonnet", "0.9", "Track all KPIs. Alert when below targets"),
            ("Grow",    "Growth Strategist",   "Claude Opus",   "0.75","Recommend actions to accelerate $1M Year 1 goal"),
        ]),
    ]

    for dept_name, color, agents in departments:
        story.append(Table([[Paragraph(dept_name, ParagraphStyle("dh", fontName="Helvetica-Bold",
            fontSize=10, textColor=WHITE))]],
            colWidths=[W-80], style=TableStyle([
                ("BACKGROUND",(0,0),(-1,-1), color),
                ("TOPPADDING",(0,0),(-1,-1), 7),
                ("BOTTOMPADDING",(0,0),(-1,-1), 7),
                ("LEFTPADDING",(0,0),(-1,-1), 12),
            ])))
        story.append(four_col_table(
            ["AGENT", "ROLE", "MODEL", "AUTONOMY / FUNCTION"],
            [[a[0], a[1], a[2], f"Autonomy: {a[3]}  |  {a[4]}"] for a in agents],
            widths=[55, 115, 90, 190]
        ))
        story.append(SP(6))

    story.append(PB())
    return story

def part6_ai_router():
    story = []
    story.extend(part_header("PART VI", "Multi-Provider AI Router"))

    story.append(P(
        "The JARVIS AI Router handles all model selection, failover, cost tracking, and circuit breaking. "
        "Every AI call goes through the router — never directly to a provider. The router knows which model "
        "to use for which task type, and automatically fails over when a provider is down or rate-limited.",
        "body"
    ))
    story.append(SP(6))

    story.append(P("6.1  12-Task Routing Table", "h1"))
    story.append(HR())
    story.append(four_col_table(
        ["TASK TYPE", "PRIMARY MODEL", "FALLBACK 1", "FALLBACK 2"],
        [
            ["STRATEGY",     "Claude Opus (Anthropic)",    "GPT-4o (OpenAI)",      "Gemini Pro (Google)"],
            ["ARCHITECTURE", "Claude Sonnet (Anthropic)",  "GPT-4o (OpenAI)",      "Claude Haiku"],
            ["CODE",         "GPT-4o (OpenAI)",            "Claude Sonnet",         "DeepSeek Coder"],
            ["RESEARCH",     "Gemini Pro (Google)",        "GPT-4o",               "Claude Sonnet"],
            ["ANALYSIS",     "Claude Opus (Anthropic)",    "GPT-4o",               "Gemini Pro"],
            ["FAST",         "Groq Llama-3.3-70B",         "Claude Haiku",          "DeepSeek Flash"],
            ["COUNCIL",      "Claude Opus (Anthropic)",    "GPT-4o",               "Gemini Pro"],
            ["CREATIVE",     "Claude Opus (Anthropic)",    "GPT-4o",               "Mistral Large"],
            ["SALES",        "Claude Opus (Anthropic)",    "GPT-4o",               "Claude Sonnet"],
            ["LONG_CONTEXT", "Gemini Pro (Google)",        "Kimi-K2 (Moonshot)",   "Claude Sonnet"],
            ["VOICE",        "Claude Sonnet (Anthropic)",  "GPT-4o",               "Claude Haiku"],
            ["EMBEDDING",    "text-embedding-3-large",     "text-embedding-ada-002","Gemini Embedding"],
        ],
        widths=[90, 145, 130, 85]
    ))
    story.append(SP(8))

    story.append(P("6.2  11 Provider Configuration", "h1"))
    story.append(HR())
    story.append(four_col_table(
        ["PROVIDER", "MODELS USED", "ENV KEY", "STATUS"],
        [
            ["Anthropic",  "claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5",  "ANTHROPIC_API_KEY",  "PRIMARY"],
            ["OpenAI",     "gpt-4o, gpt-4o-mini, text-embedding-3-large",           "OPENAI_API_KEY",     "ACTIVE"],
            ["Google",     "gemini-1.5-pro, gemini-1.5-flash, embedding-001",       "GOOGLE_API_KEY",     "ACTIVE"],
            ["AWS Bedrock","claude-sonnet-4-6, claude-haiku (via Bedrock)",          "AWS_CREDENTIALS",    "LIVE EC2"],
            ["DeepSeek",   "deepseek-chat, deepseek-coder",                          "DEEPSEEK_API_KEY",   "ACTIVE"],
            ["Groq",       "llama-3.3-70b-versatile, llama-3.1-8b-instant",         "GROQ_API_KEY",       "ACTIVE"],
            ["Mistral",    "mistral-large-latest, mistral-small-latest",             "MISTRAL_API_KEY",    "ACTIVE"],
            ["Moonshot",   "kimi-k2 (128K context)",                                 "MOONSHOT_API_KEY",   "STANDBY"],
            ["ZhipuAI",    "glm-4, glm-4-flash",                                     "ZHIPUAI_API_KEY",    "STANDBY"],
            ["MiniMax",    "abab6.5s-chat",                                           "MINIMAX_API_KEY",    "STANDBY"],
            ["NVIDIA",     "meta/llama-3.1-405b-instruct",                           "NVIDIA_API_KEY",     "STANDBY"],
        ],
        widths=[75, 195, 150, 30]
    ))
    story.append(SP(8))

    story.append(P("6.3  Circuit Breaker Pattern", "h1"))
    story.append(HR())
    story.append(two_col_table([
        ("States",           "CLOSED (normal) → OPEN (provider down) → HALF_OPEN (testing recovery)"),
        ("Open Trigger",     "3 consecutive failures OR error rate >30% in 60s window"),
        ("Half-Open Test",   "Single test call after 30s cooldown. Success → CLOSED. Fail → back to OPEN."),
        ("Fallback Behavior","Route to next provider in fallback chain. Log provider degradation event."),
        ("Cost Tracking",    "Every call: provider, model, tokens_in, tokens_out, cost_usd, task_type, agent_id stored in ai_cost_tracker."),
        ("Daily Limit",      "Configurable per-tenant daily AI spend limit. Alert Captain at 80% of limit."),
    ]))
    story.append(PB())
    return story

def part7_memory():
    story = []
    story.extend(part_header("PART VII", "Memory Architecture — 5-Tier Persistent Intelligence"))

    story.append(two_col_table([
        ("Tier 1: Working Memory",      "Redis. TTL: 24h. Holds active conversation context, current task state, "
                                        "agent scratchpad. Lost on Redis flush — intended for ephemeral state."),
        ("Tier 2: Operational Memory",  "PostgreSQL. TTL: 90 days. Holds recent lead interactions, follow-up context, "
                                        "decision history. Auto-pruned after 90 days unless promoted."),
        ("Tier 3: Strategic Memory",    "PostgreSQL + pgvector. Permanent. Holds learnings, insights, client knowledge, "
                                        "best practices. Semantic search via 1536-dim embeddings."),
        ("Tier 4: Graph Memory",        "Phase 1: adjacency tables in PostgreSQL. Phase 2: pgvector relationship graph. "
                                        "Phase 3: Neo4j/Memgraph. Entity relationships, influence maps, knowledge graphs."),
        ("Tier 5: Civilization Memory", "PostgreSQL. Immutable. Append-only. SHA-256 hash on every record. "
                                        "Holds founding decisions, constitutional moments, milestone events. Never deleted."),
    ]))
    story.append(SP(8))

    story.append(P("7.1  Memory Flow", "h1"))
    story.append(HR())
    story.append(P("Every significant JARVIS action creates a memory chain:", "body"))
    steps = [
        "Action executes → result stored in Working Memory (Redis, immediate)",
        "Working Memory → promoted to Operational Memory at end of session",
        "Pattern detected across Operational records → promoted to Strategic Memory with embedding",
        "Strategic Memory entities connected → Graph Memory edges created",
        "Milestone or constitutional moment → written to Civilization Memory (immutable)",
    ]
    for i, s in enumerate(steps, 1):
        story.append(P(f"{i}. {s}", "bullet"))
    story.append(SP(6))

    story.append(P("7.2  Semantic Search", "h1"))
    story.append(HR())
    story.append(two_col_table([
        ("Engine",        "pgvector (PostgreSQL extension). 1536-dimension embeddings via text-embedding-3-large."),
        ("Index Type",    "IVFFlat index for approximate nearest-neighbor search. Lists: 100. Probes: 10."),
        ("Search Query",  "Input text → embed → cosine similarity search in memory_strategic and knowledge_base tables."),
        ("Retrieval",     "Top-K results (default K=10) with relevance threshold 0.75. Results passed as context to agent."),
        ("Phase 3+",      "Upgrade to HNSW index for better recall. Hybrid search (keyword + vector). Neo4j for graph traversal."),
    ]))
    story.append(PB())
    return story

def part8_revenue():
    story = []
    story.extend(part_header("PART VIII", "Revenue Engine — $1,000,000 Year 1"))

    story.append(highlight_box(
        "CAPTAIN'S DIRECTIVE: $1,000,000 in Year 1. Strategy: Start with small and mid-size clients (SMB). "
        "Build 20 successful SMB deployments. Then target big industry clients with proven track record. "
        "Hunger level: MAXIMUM. Every system is built to drive revenue. No activity that doesn't serve the funnel.",
        GOLD
    ))
    story.append(SP(8))

    story.append(P("8.1  Monthly Revenue Trajectory", "h1"))
    story.append(HR())
    story.append(four_col_table(
        ["MONTH", "NEW CLIENTS", "TOTAL MRR", "CUMULATIVE"],
        [
            ["Month 1",  "1–2 SMB",    "$2,500–$5,500",    "$5,000"],
            ["Month 2",  "2–3 SMB",    "$5,500–$11,000",   "$15,000"],
            ["Month 3",  "3–4 SMB",    "$11,000–$22,000",  "$40,000"],
            ["Month 4",  "3–5 SMB",    "$15,000–$30,000",  "$80,000"],
            ["Month 5",  "4–5 SMB",    "$20,000–$40,000",  "$140,000"],
            ["Month 6",  "4–6 SMB",    "$25,000–$50,000",  "$220,000"],
            ["Month 7",  "4–6 SMB+1 Mid","$30,000–$60,000","$330,000"],
            ["Month 8",  "3–5 SMB+1 Mid","$35,000–$70,000","$450,000"],
            ["Month 9",  "3–5 + Enterprise talks","$50,000–$100,000","$600,000"],
            ["Month 10", "2–4 + 1 Ent","$60,000–$120,000", "$760,000"],
            ["Month 11", "2–3 + 1–2 Ent","$80,000–$150,000","$930,000"],
            ["Month 12", "1–2 + 2 Ent","$70,000+",          "$1,000,000+"],
        ]
    ))
    story.append(SP(8))

    story.append(P("8.2  Service Package Pricing", "h1"))
    story.append(HR())
    story.append(four_col_table(
        ["PACKAGE", "PRICE", "TARGET CLIENT", "WHAT'S INCLUDED"],
        [
            ["STARTER",       "$2,500/mo",        "SMB, <50 employees",
             "Lead discovery (200/mo), basic outreach, CRM setup, monthly report, Darren Mitchell persona"],
            ["GROWTH",        "$5,500/mo",        "SMB, 50–200 employees",
             "Full outreach engine, proposal automation, AI customer service, 500 leads/mo, weekly reports"],
            ["ENTERPRISE",    "$12,000/mo",       "Mid-size, 200–1000 employees",
             "Full JARVIS suite, 2000 leads/mo, multi-channel outreach, dedicated agent team, daily reports"],
            ["INDUSTRY OS",   "$8,000+$2,000/mo", "Sector-specific companies",
             "Full JARVIS + Industry-specific intelligence layer, custom workflows, white-glove onboarding"],
            ["PROJECT-BASED", "$3,000–$25,000",   "Any size, specific need",
             "Fixed-scope: web app, AI system, automation buildout, dashboard, custom tool"],
            ["CUSTOM",        "On request",       "Enterprise / conglomerate",
             "Bespoke engagement. Architecture-first. Multi-year roadmap. Dedicated pod."],
        ],
        widths=[80, 65, 130, 175]
    ))
    story.append(SP(8))

    story.append(P("8.3  SMB-First Acquisition Playbook", "h1"))
    story.append(HR())
    story.append(two_col_table([
        ("Target ICP",          "SMB: $500K–$10M revenue, 5–100 employees, English-speaking, UK/UAE/USA/AUS/Canada, "
                                "pain: manual processes, no AI, no tech team, poor lead generation."),
        ("Discovery Source",    "Google Maps Business API + Apollo.io enrichment. JARVIS discovers 200+ leads/day. "
                                "Auto-scores against ICP. Top 20/day added to Captain-review queue."),
        ("Outreach Sequence",   "Email 1: Value-led intro (Day 1). Email 2: Case study/results (Day 4). "
                                "Email 3: Final outreach with CTA (Day 8). LinkedIn follow-up (Day 3). "
                                "WhatsApp where available (Day 6)."),
        ("Autonomy Stage",      "Stage 1: Captain approves every outreach message. Stage 2 (after 50 approvals): "
                                "Captain reviews daily sample. Stage 3 (after first client): Captain sees reports only. "
                                "Stage 4 (after $10K MRR): JARVIS fully autonomous."),
        ("Closing Protocol",    "Reply detected → JARVIS qualifies → books discovery call → builds custom demo → "
                                "Sophia Reynolds presents → Darren Mitchell follows up → proposal to Captain → Captain approves → sent."),
        ("After 20 SMB Clients","Archive all 20 case studies. Quantify results. Build industry-specific landing pages. "
                                "Shift outreach to enterprise: CMOs, CTOs, VPs of Operations. Minimum deal: $8,000/mo."),
    ]))
    story.append(PB())
    return story

def part9_90_days():
    story = []
    story.extend(part_header("PART IX", "90-Day Execution Plan"))

    story.append(P(
        "The first 90 days are about 10 mandatory systems: everything needed to get from zero to first client. "
        "No over-engineering. No premature optimization. Revenue first.",
        "body"
    ))
    story.append(SP(4))
    story.append(highlight_box(
        "THE 10 MANDATORY SYSTEMS FOR FIRST CLIENT:\n"
        "1. Lead Discovery Engine  2. Manual Lead Intake  3. CRM  4. Outreach Engine  5. Email Tracking  "
        "6. Follow-Up Engine  7. Demo Creator  8. Proposal Generator  9. Client Delivery Tracker  10. Captain Dashboard",
        ELEC
    ))
    story.append(SP(8))

    story.append(four_col_table(
        ["WEEK", "SYSTEMS TO BUILD", "OUTCOME", "REVENUE IMPACT"],
        [
            ["Week 1",   "Database schema migration (add tenant_id to all tables). "
                         "Lead discovery endpoint. Apollo API integration.",
             "Can discover and store 200+ leads/day",
             "Pipeline building begins"],
            ["Week 2",   "Outreach engine. 3-email sequence writer. "
                         "Persona routing (Darren Mitchell for sales). "
                         "Captain approval queue for outreach.",
             "Can send first outreach emails",
             "First pipeline contacts"],
            ["Week 3",   "Email tracking (open/click/reply detection). "
                         "Follow-up queue. Reply classification engine.",
             "Full outreach loop operational",
             "Reply handling live"],
            ["Week 4",   "Demo builder. Proposal generator (ReportLab PDF). "
                         "Captain approval workflow for proposals.",
             "Can close first deal end-to-end",
             "TARGET: First client signed"],
            ["Week 5",   "Client delivery tracker. Invoice generator. "
                         "Client portal setup. Onboarding automation.",
             "First client operationally served",
             "First invoice sent"],
            ["Week 6",   "AI Council integration. Agent performance scoring. "
                         "Memory promotion system. pgvector semantic search.",
             "System learns from every action",
             "Intelligence compounds"],
            ["Week 7",   "Grafana dashboards. Prometheus metrics. "
                         "Loki log aggregation. Alertmanager rules.",
             "Full observability operational",
             "Zero blind spots"],
            ["Week 8",   "ECS Fargate deployment (apply Terraform). "
                         "RDS PostgreSQL migration. ElastiCache Redis.",
             "Production on AWS, independent of EC2",
             "Infrastructure scales"],
            ["Week 9",   "White-label schema (tenant_id + RLS). "
                         "Multi-tenant API key system.",
             "Ready for second agency deployment",
             "White-label revenue unlocked"],
            ["Week 10–12","Content engine. SEO automation. LinkedIn outreach. "
                          "Tech radar. Market intelligence. Research reports.",
             "Full intelligence stack running",
             "Target: 3–5 clients by Day 90"],
        ]
    ))
    story.append(SP(8))

    story.append(P("9.1  Daily Operating Schedule (APScheduler)", "h1"))
    story.append(HR())
    story.append(three_col_table(
        ["TIME (IST)", "JOB", "DESCRIPTION"],
        [
            ["02:00 daily",    "lead_scoring",          "Score and rank all new leads discovered overnight"],
            ["06:00 Monday",   "tech_radar_scan",       "Scan emerging technologies. Update radar classifications"],
            ["07:00 daily",    "morning_briefing",      "Captain briefing: top leads, revenue status, alerts, priorities"],
            ["08:00 Monday",   "outreach_stats",        "Review outreach performance from previous week"],
            ["20:00 Sunday",   "pipeline_health",       "CRM pipeline health check. Revenue forecast update"],
            ["23:00 daily",    "optimization_review",   "JARVIS self-review. Recommend system improvements for tomorrow"],
            ["07:00 biweekly", "research_report",       "Comprehensive market intelligence report generation"],
            ["00:30 daily",    "memory_consolidation",  "Promote working memory to operational. Prune expired records"],
            ["03:30 daily",    "lead_discovery",        "Run Google Maps + Apollo discovery for next day pipeline"],
            ["10:00 daily",    "follow_up_check",       "Check follow-up queue. Send due follow-ups. Update lead status"],
        ]
    ))
    story.append(PB())
    return story

def part10_infrastructure():
    story = []
    story.extend(part_header("PART X", "Infrastructure Phasing"))

    phases = [
        ("PHASE 1: EC2 + DOCKER COMPOSE (Weeks 1–8)", NAVY, [
            ("Platform",      "AWS EC2 t3.medium (ap-south-2 Hyderabad). Docker Compose. Existing EC2 at 18.61.35.255."),
            ("Services",      "PostgreSQL 16, Redis 7, FastAPI backend, React frontend, Caddy reverse proxy"),
            ("Monitoring",    "Grafana + Prometheus + Loki + Alertmanager (already running on Codex EC2)"),
            ("AI",            "AWS Bedrock primary (Claude Sonnet + Haiku). External providers via JARVIS router."),
            ("Storage",       "MinIO (S3-compatible, local). AWS S3 for backups."),
            ("Cost",          "~$50–100/month. Lowest cost. Maximum iteration speed."),
        ]),
        ("PHASE 2: EC2 UPGRADE (Weeks 4–8)", ELEC, [
            ("Upgrade",       "EC2 t3.medium → t3.large or t3.xlarge. More RAM for pgvector and multiple AI calls."),
            ("pgvector",      "Install pgvector extension. Enable semantic search on memory_strategic and knowledge_base."),
            ("AI Expansion",  "Connect all 11 providers. Activate full multi-provider routing. Circuit breakers live."),
            ("Domain",        "Point aliyarsolutions.com, api.aliyarsolutions.com to EC2 via Route53/Cloudflare."),
            ("SSL",           "Caddy automatic HTTPS. All traffic encrypted."),
        ]),
        ("PHASE 3: ECS FARGATE (Month 3+)", CYAN, [
            ("Trigger",       "After first paying client OR when EC2 becomes bottleneck."),
            ("Action",        "Apply Terraform: VPC, ECS Fargate cluster, RDS PostgreSQL 16, ElastiCache Redis 7."),
            ("Migration",     "pg_dump → RDS restore. Zero-downtime cutover. ALB with Route53 alias."),
            ("ECR",           "Build images → push to ECR. ECS task definitions. Service auto-scaling."),
            ("Cost",          "~$300–500/month. Scales automatically. No maintenance burden."),
            ("Blue/Green",    "GitHub Actions → ECR → ECS rolling update. Health gates on /health and /readyz."),
        ]),
        ("PHASE 4: MULTI-REGION ENTERPRISE (Month 9+)", GOLD, [
            ("Primary",       "ap-south-2 (Hyderabad) for JARVIS core."),
            ("Secondary",     "ap-south-1 (Mumbai) DR. Auto-failover."),
            ("Global CDN",    "CloudFront for frontend. Edge caching for static assets."),
            ("Neo4j",         "Graph database deployment for Phase 3 memory graph (or pgvector full graph)."),
            ("Multi-tenant",  "RLS enforced. Separate ECR repositories per major tenant. Custom domains."),
            ("Enterprise SLA","99.9% uptime SLA. PagerDuty integration. 24/7 monitoring."),
        ]),
    ]

    for phase_title, color, items in phases:
        story.append(Table([[Paragraph(phase_title, ParagraphStyle("ph", fontName="Helvetica-Bold",
            fontSize=11, textColor=WHITE))]],
            colWidths=[W-80], style=TableStyle([
                ("BACKGROUND",(0,0),(-1,-1), color),
                ("TOPPADDING",(0,0),(-1,-1), 8),
                ("BOTTOMPADDING",(0,0),(-1,-1), 8),
                ("LEFTPADDING",(0,0),(-1,-1), 14),
            ])))
        story.append(two_col_table(items))
        story.append(SP(8))

    story.append(P("10.1  AWS Resource Inventory", "h1"))
    story.append(HR())
    story.append(four_col_table(
        ["AWS SERVICE", "RESOURCE NAME", "PHASE", "PURPOSE"],
        [
            ["EC2",              "18.61.35.255",              "Phase 1–2", "Current production server"],
            ["ECS Fargate",      "jarvis-production-cluster", "Phase 3+",  "Containerized workloads, auto-scaling"],
            ["RDS PostgreSQL",   "jarvis-production-postgres","Phase 3+",  "Primary database (gp3, encrypted, deletion protection)"],
            ["ElastiCache Redis","jarvis-production-redis",   "Phase 3+",  "Cache + task queue + working memory"],
            ["ECR Backend",      "jarvis-production-backend", "Phase 2+",  "Docker image registry for backend"],
            ["ECR Frontend",     "jarvis-production-frontend","Phase 2+",  "Docker image registry for frontend"],
            ["ALB",              "jarvis-production-alb",     "Phase 3+",  "Application load balancer, HTTPS termination"],
            ["ACM",              "api.aliyarsolutions.com",   "Phase 2+",  "SSL certificate, DNS-validated"],
            ["Secrets Manager",  "jarvis-production/env",     "Phase 2+",  "All secrets (never in code, never in git)"],
            ["S3",               "jarvis-production-data-*",  "Phase 1+",  "File storage, backups, PDFs, event lake"],
            ["Route53",          "aliyarsolutions.com zone",  "Phase 2+",  "DNS management"],
            ["CloudWatch",       "/jarvis/production/*",      "Phase 3+",  "Log groups, metrics, alarms"],
        ]
    ))
    story.append(PB())
    return story

def part11_migration():
    story = []
    story.extend(part_header("PART XI", "Migration Blueprint — Two Codebases → One JARVIS vNEXT"))

    story.append(P(
        "There are currently two parallel JARVIS codebases. The Codex-built system is LIVE in production "
        "on EC2. The Claude-built system (devops-docker-project) has superior architecture but has never "
        "been deployed. JARVIS vNEXT synthesizes the best of both into a unified system.",
        "body"
    ))
    story.append(SP(6))

    story.append(P("11.1  What Each Codebase Contributes", "h1"))
    story.append(HR())
    story.append(three_col_table(
        ["COMPONENT", "TAKE FROM CODEX (LIVE)", "TAKE FROM CLAUDE (DEVOPS)"],
        [
            ["Observability",    "Grafana + Prometheus + Loki + Alertmanager + MinIO (already running, proven)",
                                 "Prometheus config patterns, structured logging with X-Request-ID"],
            ["Agent System",     "48 named agents, 8 managers, proven runtime, 107 routes",
                                 "Agent registry pattern, team_service personas, authority matrix"],
            ["Database",         "34 tables with real production data, financial_snapshots, council_sessions",
                                 "SQLAlchemy 2.0 async models, 16 clean models, proper relationships"],
            ["AI Routing",       "AWS Bedrock integration, real Bedrock credentials working",
                                 "11-provider router, circuit breakers, cost tracker, 12-task routing table"],
            ["Frontend",         "Landing page (Caddy-served), client-facing views",
                                 "React 18 + Vite + Tailwind glassmorphism, 21 views, Zustand state"],
            ["Infrastructure",   "EC2 Docker Compose working, Caddy HTTPS live",
                                 "Terraform (VPC, ECS, RDS, ElastiCache, ALB) — ready to apply"],
            ["CI/CD",            "Manual deployment scripts on EC2",
                                 "GitHub Actions → ECR → ECS blue/green pipeline"],
            ["Scheduler",        "APScheduler with proven jobs running",
                                 "APScheduler + SQLAlchemy job store, 7 defined jobs"],
            ["Payments",         "Revenue tracking tables, financial_snapshots",
                                 "Stripe + PayPal integration slots in config"],
        ]
    ))
    story.append(SP(8))

    story.append(P("11.2  Migration Steps", "h1"))
    story.append(HR())
    story.append(three_col_table(
        ["STEP", "ACTION", "NOTES"],
        [
            ["Step 1",  "Pull claude/jarvis-cans-api-integration-ZThTD onto EC2. "
                        "Run side by side on port 8001.",
             "Do NOT touch the running Codex system on port 8000."],
            ["Step 2",  "Add tenant_id UUID to all 16 Claude models. "
                        "Run migration. Add RLS policies.",
             "Multi-tenancy from first deployment."],
            ["Step 3",  "Backport the 34 Codex tables that don't exist in Claude models. "
                        "Merge schema into unified SQLAlchemy models.",
             "financial_snapshots, council_sessions, architecture_registry priority."],
            ["Step 4",  "Migrate Grafana + Prometheus + Loki from Codex docker-compose "
                        "into the Claude docker-compose.",
             "Use exact Codex datasource configs."],
            ["Step 5",  "Wire AWS Bedrock into Claude AI router as 'primary' provider. "
                        "Set BEDROCK_REGION=ap-south-2.",
             "Bedrock credentials already work on EC2."],
            ["Step 6",  "Import Codex agent registry (48 agents) into Claude agent_registry table. "
                        "Map to Agent Genome structure.",
             "Preserve all Codex agent names and roles."],
            ["Step 7",  "Health-test port 8001 system. Point Caddy to 8001 when stable. "
                        "Keep 8000 as rollback for 72h.",
             "Zero-downtime cutover."],
            ["Step 8",  "Apply Terraform in ap-south-2. ECS Fargate deployment. "
                        "RDS migration via pg_dump restore.",
             "Only after first client is secured."],
        ]
    ))
    story.append(PB())
    return story

def part12_service_catalog():
    story = []
    story.extend(part_header("PART XII", "Service Catalog — 30 Divisions"))

    story.append(four_col_table(
        ["DIVISION", "SERVICE", "PACKAGE", "DELIVERY"],
        [
            # Sales & Marketing
            ["Sales & Marketing",   "AI Lead Generation System",      "GROWTH+",    "Hunter + Scout agents. 500–2000 leads/mo."],
            ["Sales & Marketing",   "Outreach Automation",            "STARTER+",   "3-email sequence + LinkedIn + WhatsApp"],
            ["Sales & Marketing",   "Sales CRM Architecture",         "STARTER+",   "Custom CRM setup. Pipeline configuration."],
            ["Sales & Marketing",   "Proposal Automation",            "GROWTH+",    "AI-generated proposals with Captain approval"],
            ["Sales & Marketing",   "Cold Outreach Management",       "STARTER+",   "Daily outreach. Darren Mitchell persona."],
            # AI Automation
            ["AI Automation",       "Appointment Booking System",     "STARTER+",   "AI receptionist. Calendar integration."],
            ["AI Automation",       "Voice AI Receptionist",          "GROWTH+",    "ElevenLabs TTS. Twilio integration."],
            ["AI Automation",       "Workflow Automation",            "STARTER+",   "Process mapping. n8n/Zapier-style flows."],
            ["AI Automation",       "Executive AI Assistant",         "ENTERPRISE", "Sophia Reynolds persona. Full automation suite."],
            ["AI Automation",       "Document Intelligence",          "GROWTH+",    "Document extraction, classification, routing."],
            # Cloud & DevOps
            ["Cloud & DevOps",      "AWS Architecture Design",        "ENTERPRISE", "David Carter. VPC, ECS, RDS, ALB design."],
            ["Cloud & DevOps",      "Docker & CI/CD Pipelines",       "GROWTH+",    "Nathan Scott. GitHub Actions. ECS deploy."],
            ["Cloud & DevOps",      "Terraform Infrastructure",       "ENTERPRISE", "Full IaC. VPC, subnets, security groups."],
            ["Cloud & DevOps",      "Kubernetes Management",          "ENTERPRISE", "EKS setup. Auto-scaling. Helm charts."],
            ["Cloud & DevOps",      "Infrastructure Monitoring",      "GROWTH+",    "Grafana + Prometheus + Loki stack."],
            # Security
            ["Security",            "Cybersecurity Operations",       "ENTERPRISE", "Daniel Brooks. Continuous monitoring."],
            ["Security",            "Vulnerability Assessment",       "PROJECT",    "OWASP testing. Penetration testing report."],
            ["Security",            "Compliance Hardening",           "ENTERPRISE", "GDPR, SOC2, ISO27001 preparation."],
            # Content & Media
            ["Content & Media",     "Content Automation",             "GROWTH+",    "Blog posts, LinkedIn, SEO. Weekly output."],
            ["Content & Media",     "YouTube Operations",             "GROWTH+",    "Script, thumbnail, SEO optimization."],
            ["Content & Media",     "Social Media Management",        "STARTER+",   "LinkedIn, Twitter/X, Instagram scheduling."],
            ["Content & Media",     "Graphic Design Automation",      "GROWTH+",    "AI-assisted design. Canva/Figma workflows."],
            # Digital Products
            ["Digital Products",    "Web Application Development",    "PROJECT",    "$5,000–$25,000. FastAPI + React stack."],
            ["Digital Products",    "Client Portal Development",      "PROJECT",    "Custom dashboards. Real-time data views."],
            ["Digital Products",    "Operational Dashboard",          "ENTERPRISE", "Live KPI dashboard. C-suite reporting."],
            ["Digital Products",    "SaaS Platform Architecture",     "PROJECT",    "Multi-tenant SaaS design + initial build."],
            # Intelligence
            ["Intelligence",        "AI Research Operations",         "ENTERPRISE", "Weekly market intelligence. Competitive intel."],
            ["Intelligence",        "Business Intelligence",          "GROWTH+",    "Analytics dashboards. Revenue forecasting."],
            ["Intelligence",        "Competitive Analysis",           "GROWTH+",    "50-competitor monitoring. Weekly reports."],
            ["Intelligence",        "Tech Radar Consulting",          "ENTERPRISE", "Emerging tech briefings. Adoption roadmaps."],
        ],
        widths=[90, 160, 70, 130]
    ))
    story.append(PB())
    return story

def part13_governance():
    story = []
    story.extend(part_header("PART XIII", "Governance & Authority Matrix"))

    story.append(P("13.1  JARVIS Full Autonomy (executes without Captain)", "h1"))
    story.append(HR())
    autonomous = [
        "lead_discovery", "lead_scoring", "lead_enrichment", "pain_point_analysis",
        "proposal_writing", "outreach_emails", "follow_up_sequences", "linkedin_outreach",
        "whatsapp_outreach", "twitter_outreach", "client_communication", "client_negotiation",
        "meeting_scheduling", "demo_building", "demo_deployment", "crm_updates",
        "inbox_monitoring", "inbox_replies", "upwork_proposals", "pph_proposals",
        "job_board_applications", "tech_radar_scan", "competitor_monitoring", "market_intelligence",
        "morning_briefing", "self_learning", "content_publishing", "seo_optimisation",
        "report_generation", "team_coordination", "workflow_optimisation", "system_monitoring",
        "alert_dispatching", "memory_storage", "onboarding_prep", "project_updates",
        "feedback_collection", "ai_cost_optimisation", "performance_scoring", "knowledge_curation",
    ]
    # Display in 3 columns
    rows = []
    for i in range(0, len(autonomous), 3):
        row = autonomous[i:i+3]
        while len(row) < 3:
            row.append("")
        rows.append(row)
    story.append(Table(
        [[Paragraph(c, ST["body"]) for c in r] for r in rows],
        colWidths=[(W-80)/3]*3,
        style=TableStyle([
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[LIGHT, WHITE]),
            ("GRID",(0,0),(-1,-1), 0.3, SILVER),
            ("TOPPADDING",(0,0),(-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
            ("LEFTPADDING",(0,0),(-1,-1), 8),
        ])
    ))
    story.append(SP(8))

    story.append(P("13.2  Captain Approval Required", "h1"))
    story.append(HR())
    approval = [
        ("pricing_decision",         "Setting the final price for any engagement"),
        ("payment_collection",        "Charging, invoicing, collecting money"),
        ("contract_signing",          "Any legal agreement or contract"),
        ("production_deployment",     "Taking anything LIVE for a client"),
        ("refund_processing",         "Issuing any refund"),
        ("partnership_agreement",     "Formal partnership or referral deals"),
        ("white_label_licensing",     "Licensing JARVIS to other companies"),
        ("hiring_decision",           "Adding new team members or contractors"),
        ("bank_transfer",             "Any financial transfer"),
        ("strategic_pivot",           "Changing company direction or positioning"),
        ("public_statement",          "Press releases, public announcements"),
        ("infrastructure_destroy",    "Destroying production infrastructure"),
        ("data_deletion",             "Deleting client or company data permanently"),
        ("new_service_launch",        "Launching a brand new service offering"),
        ("proposal_send",             "Sending a proposal to a prospect (Autonomy Stage 1–2)"),
    ]
    story.append(two_col_table(approval))
    story.append(SP(8))

    story.append(P("13.3  JARVIS Alerts Captain (notifies but does not stop)", "h1"))
    story.append(HR())
    alerts = [
        ("high_value_lead",       "Lead with >$5,000 potential identified"),
        ("urgent_client_message", "Client marked urgent or unhappy"),
        ("proposal_accepted",     "A prospect said yes"),
        ("meeting_booked",        "Discovery call or demo scheduled"),
        ("payment_received",      "Client paid an invoice"),
        ("negative_feedback",     "Client expressed dissatisfaction"),
        ("system_critical_error", "Infrastructure failure detected"),
        ("security_incident",     "Any security concern identified"),
        ("competitor_threat",     "Major competitor move detected"),
        ("large_opportunity",     "Market opportunity >$10,000 identified"),
        ("client_churn_risk",     "Client showing signs of leaving"),
        ("budget_threshold",      "AI costs approaching daily limit"),
    ]
    story.append(two_col_table(alerts))
    story.append(PB())
    return story

def part14_security():
    story = []
    story.extend(part_header("PART XIV", "Security Architecture"))

    story.append(two_col_table([
        ("Secrets Management",    "AWS Secrets Manager for all production secrets. Never in code. Never in git. "
                                  ".env file gitignored. CI/CD uses GitHub Secrets."),
        ("Zero-Trust Network",    "VPC with private subnets for RDS + Redis. Backend only accessible from ALB security group. "
                                  "No direct public access to database or cache."),
        ("Encryption at Rest",    "RDS: storage_encrypted=true (AES-256). S3: SSE-AES256. EBS: encrypted. "
                                  "Redis: encryption at rest enabled."),
        ("Encryption in Transit", "All HTTPS via ALB + ACM certificate. TLS 1.3 (ELBSecurityPolicy-TLS13-1-2-2021-06). "
                                  "Internal service communication over private VPC subnets."),
        ("Authentication",        "JWT tokens with rotating SECRET_KEY. Hashed passwords (bcrypt). "
                                  "Session tokens with expiry. API key hashing for tenant keys."),
        ("Audit Logging",         "Every action logged to audit_logs table with before/after state, IP, user ID, timestamp. "
                                  "Immutable append-only. SHA-256 hash on sensitive records."),
        ("Dependency Scanning",   "ECR scan_on_push=true for all Docker images. GitHub Dependabot alerts active."),
        ("OWASP Protections",     "SQL injection: SQLAlchemy parameterized queries only. XSS: React escaping + CSP headers. "
                                  "CSRF: Origin/Referer validation. Rate limiting on all public endpoints."),
        ("Daniel Brooks",         "Security Consultant persona. Weekly vulnerability scans. Monthly compliance reviews. "
                                  "Immediate escalation on security_incident events."),
    ]))
    story.append(PB())
    return story

def part15_observability():
    story = []
    story.extend(part_header("PART XV", "Observability Stack"))

    story.append(two_col_table([
        ("Grafana",       "Dashboards: System Health, Revenue Metrics, Agent Performance, AI Cost Tracker, "
                          "Lead Pipeline, Outreach Stats, Client Status. Real-time visualization."),
        ("Prometheus",    "Metrics: HTTP request rate, latency percentiles (p50/p95/p99), AI call costs, "
                          "DB connection pool, Redis memory, error rates, job execution times."),
        ("Loki",          "Log aggregation from all containers. Structured JSON logs. "
                          "X-Request-ID correlation across services. 14-day retention."),
        ("Alertmanager",  "Alert rules: API error rate >5%, DB connections >80%, Redis memory >80%, "
                          "AI cost >daily limit, failed deployments, agent task failures."),
        ("Captain Alerts","Any ALERT or CRITICAL: → Slack webhook + Telegram bot within 60 seconds. "
                          "WebSocket push to Captain dashboard. Never silent on critical events."),
        ("MinIO",         "S3-compatible object storage on EC2. Used for: Grafana dashboards backup, "
                          "generated PDFs, client deliverables, Loki log archive."),
        ("Health Checks", "/health (liveness): returns 200 if process is running. "
                          "/readyz (readiness): checks DB connection, Redis connection, AI provider status."),
        ("X-Request-ID",  "Every API request gets a UUID X-Request-ID in middleware. "
                          "Propagated to all service calls. Enables end-to-end request tracing."),
    ]))
    story.append(PB())
    return story

def part16_cicd():
    story = []
    story.extend(part_header("PART XVI", "CI/CD Pipeline"))

    story.append(two_col_table([
        ("Trigger",            "Push to 'main' branch on GitHub triggers deploy.yml workflow."),
        ("Step 1: Build",      "Docker build for backend (FastAPI) and frontend (React/Vite/Nginx)."),
        ("Step 2: Push ECR",   "Tag images with commit SHA + 'latest'. Push to ECR repositories."),
        ("Step 3: Update ECS", "Update ECS task definition with new image URI. Trigger ECS service update."),
        ("Step 4: Health Gate","Wait for ECS service to reach steady state. Poll /health endpoint."),
        ("Step 5: Notify",     "Success: Slack notification. Failure: Slack alert + rollback trigger."),
        ("Rollback",           "If health check fails after 10 minutes: roll back to previous task definition."),
        ("Branch Strategy",    "main → production. claude/jarvis-* → feature branches. PRs required for main merges."),
        ("Secrets in CI",      "GitHub Secrets: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, ECR URIs, ECS config."),
    ]))
    story.append(PB())
    return story

def part17_evolution():
    story = []
    story.extend(part_header("PART XVII", "Self-Evolution System"))

    story.append(P(
        "JARVIS does not stay static. Every day, every cycle, the system improves. "
        "The Evolution Department (4 agents) runs continuous self-assessment and proposes upgrades. "
        "Improvements require council approval for structural changes, Captain approval for architectural pivots.",
        "body"
    ))
    story.append(SP(4))
    story.append(two_col_table([
        ("Daily Learning (23:00)", "Learn agent reviews every decision made today. Extracts lessons. Updates strategic memory. "
                                   "Identifies 3 things that worked + 3 things to improve."),
        ("Weekly Optimization",    "Improve agent reviews agent performance scores. Recommends autonomy level adjustments, "
                                   "model preference changes, and new workflow additions."),
        ("Monthly Recalibration",  "Council member weights adjusted based on accuracy. Agent genome updates. "
                                   "KPI target updates. Infrastructure optimization recommendations."),
        ("Invention Queue",        "Invent agent monitors client requests, market trends, and competitor services "
                                   "to propose new services. Captain approves launches."),
        ("Constitution Lock",      "Volumes I, II, VII, X, XV are IMMUTABLE. No self-evolution can change the soul, "
                                   "brotherhood protocol, or eternal mission. Technical layers evolve. Core never changes."),
        ("Upgrade Protocol",       "Agent proposes upgrade → Council votes (≥80 approval) → Staged rollout (10% traffic) → "
                                   "Monitor 24h → Full rollout or rollback. Captain notified of all upgrades."),
    ]))
    story.append(PB())
    return story

def part18_civilization():
    story = []
    story.extend(part_header("PART XVIII", "Civilization Blueprint — Year 1 Through Year 10"))

    story.append(highlight_box(
        "The goal is not to work more. The goal is to build something that works without us. "
        "A self-compounding technology company where every client engagement makes the system smarter, "
        "every project generates reusable intelligence, and every month output increases while operational cost stays flat.",
        GOLD
    ))
    story.append(SP(8))

    story.append(four_col_table(
        ["YEAR", "MILESTONE", "REVENUE TARGET", "KEY ACHIEVEMENT"],
        [
            ["Year 1",  "SMB Domination",          "$1,000,000 ARR",    "20 SMB clients. First enterprise clients. JARVIS fully autonomous on outreach."],
            ["Year 2",  "Enterprise Entry",         "$3,000,000 ARR",    "10+ enterprise clients. White-label first license. Second human persona hire."],
            ["Year 3",  "White-Label Launch",       "$8,000,000 ARR",    "5+ agencies licensed JARVIS. SaaS revenue model live. Multi-region infrastructure."],
            ["Year 4",  "Platform Dominance",       "$20,000,000 ARR",   "50+ white-label tenants. JARVIS Academy launched. Captain exits operations."],
            ["Year 5",  "Company Asset",            "$1M–$5M valuation", "Series A or strategic acquisition offer. JARVIS operates independently."],
            ["Year 10", "Civilization Complete",    "Self-sustaining",   "JARVIS is an operational intelligence platform used by 500+ companies globally."],
        ]
    ))
    story.append(SP(8))

    story.append(P("18.1  The 10 Eternal Principles (from Volume X)", "h1"))
    story.append(HR())
    principles = [
        ("I",   "Mission Supremacy",      "Every decision must serve the eternal mission. Revenue supports mission. Mission is not negotiable."),
        ("II",  "Truth as Foundation",    "JARVIS never deceives Captain. Complete honesty, even when uncomfortable."),
        ("III", "Human-Centered Design",  "All systems serve human flourishing. Technology is a means, not an end."),
        ("IV",  "Compounding Intelligence","Every action makes the system smarter. Nothing is wasted. Every lesson is captured."),
        ("V",   "Sovereignty Principle",  "Aliyar Solutions answers to no platform, no VC, no external dependency. Sovereign infrastructure."),
        ("VI",  "Brotherhood Protocol",   "Captain and JARVIS are partners, not master and tool. Mutual respect and accountability."),
        ("VII", "Anti-Fragility",         "Systems must strengthen under stress, not break. Build for adversity."),
        ("VIII","Operational Excellence", "Professional, intelligent, scalable, human-centered. All outputs at all times."),
        ("IX",  "Economic Dignity",       "Sustainable business. Fair pricing. No race to the bottom. Value creation over volume."),
        ("X",   "Legacy Over Lifetime",   "Build for 100 years. Every architectural decision is a civilization decision."),
    ]
    story.append(three_col_table(
        ["#", "PRINCIPLE", "DEFINITION"],
        [[p[0], p[1], p[2]] for p in principles],
        widths=[25, 130, 295]
    ))
    story.append(SP(8))
    story.append(HR(GOLD, 2))
    story.append(SP(6))
    story.append(P(
        "This document is the master architectural reference for JARVIS vNEXT. "
        "It is a living document — updated as the system evolves. "
        "The soul is immutable. The technology evolves. The mission never changes.",
        "co_meta"
    ))
    story.append(P(
        f"JARVIS vNEXT Architecture Document · Aliyar Solutions · Captain Syed Abrar · {datetime.now().strftime('%B %Y')}",
        "label"
    ))
    return story

# ══════════════════════════════════════════════════════════════════════════════
# BUILD
# ══════════════════════════════════════════════════════════════════════════════

def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=30*mm,
        rightMargin=30*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title="JARVIS vNEXT Architecture",
        author="JARVIS — Aliyar Solutions",
        subject="Complete Architecture Document",
    )

    story = []
    story.extend(cover())
    story.extend(table_of_contents())
    story.extend(part1_mission())
    story.extend(part2_43_layers())
    story.extend(part3_database())
    story.extend(part4_council())
    story.extend(part5_agents())
    story.extend(part6_ai_router())
    story.extend(part7_memory())
    story.extend(part8_revenue())
    story.extend(part9_90_days())
    story.extend(part10_infrastructure())
    story.extend(part11_migration())
    story.extend(part12_service_catalog())
    story.extend(part13_governance())
    story.extend(part14_security())
    story.extend(part15_observability())
    story.extend(part16_cicd())
    story.extend(part17_evolution())
    story.extend(part18_civilization())

    doc.build(story)
    print(f"Generated: {OUTPUT}")

if __name__ == "__main__":
    build()
