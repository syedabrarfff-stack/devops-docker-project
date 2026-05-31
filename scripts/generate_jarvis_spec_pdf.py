"""
JARVIS Enterprise Operating System — Master Deployment Specification PDF Generator
Aliyar Solutions | CEO: Syed Abrar
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from datetime import datetime
import os

OUTPUT_PATH = "/home/user/devops-docker-project/JARVIS_Enterprise_OS_Specification.pdf"

# ── Colour Palette ─────────────────────────────────────────────────────────────
NAVY       = colors.HexColor("#0A1628")
ELECTRIC   = colors.HexColor("#0057FF")
CYAN       = colors.HexColor("#00C8FF")
GOLD       = colors.HexColor("#FFB700")
SILVER     = colors.HexColor("#C8D6E5")
WHITE      = colors.white
LIGHT_BG   = colors.HexColor("#F0F4FA")
MID_BG     = colors.HexColor("#D6E4F7")
DARK_TEXT  = colors.HexColor("#0A1628")
BODY_TEXT  = colors.HexColor("#1E2D40")
SUBTLE     = colors.HexColor("#6B7C93")
RED_ALERT  = colors.HexColor("#FF3B30")
GREEN_OK   = colors.HexColor("#28CD41")
ORANGE_WARN= colors.HexColor("#FF9500")

W, H = A4  # 595.27 x 841.89 pts

# ── Styles ──────────────────────────────────────────────────────────────────────
def build_styles():
    s = {}

    s["cover_company"] = ParagraphStyle(
        "cover_company", fontName="Helvetica-Bold", fontSize=11,
        textColor=CYAN, alignment=TA_CENTER, spaceAfter=4,
        letterSpacing=3
    )
    s["cover_title"] = ParagraphStyle(
        "cover_title", fontName="Helvetica-Bold", fontSize=28,
        textColor=WHITE, alignment=TA_CENTER, spaceAfter=6, leading=34
    )
    s["cover_subtitle"] = ParagraphStyle(
        "cover_subtitle", fontName="Helvetica-Bold", fontSize=14,
        textColor=GOLD, alignment=TA_CENTER, spaceAfter=4
    )
    s["cover_meta"] = ParagraphStyle(
        "cover_meta", fontName="Helvetica", fontSize=9,
        textColor=SILVER, alignment=TA_CENTER, spaceAfter=3
    )
    s["part_header"] = ParagraphStyle(
        "part_header", fontName="Helvetica-Bold", fontSize=18,
        textColor=WHITE, alignment=TA_CENTER, spaceAfter=6,
        backColor=NAVY, borderPad=10, leading=22
    )
    s["section_header"] = ParagraphStyle(
        "section_header", fontName="Helvetica-Bold", fontSize=13,
        textColor=ELECTRIC, spaceAfter=6, spaceBefore=14, leading=16
    )
    s["subsection"] = ParagraphStyle(
        "subsection", fontName="Helvetica-Bold", fontSize=10.5,
        textColor=NAVY, spaceAfter=4, spaceBefore=8, leading=13
    )
    s["body"] = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=9.5,
        textColor=BODY_TEXT, spaceAfter=5, leading=14, alignment=TA_JUSTIFY
    )
    s["body_bold"] = ParagraphStyle(
        "body_bold", fontName="Helvetica-Bold", fontSize=9.5,
        textColor=DARK_TEXT, spaceAfter=4, leading=14
    )
    s["bullet"] = ParagraphStyle(
        "bullet", fontName="Helvetica", fontSize=9.5,
        textColor=BODY_TEXT, spaceAfter=3, leading=13,
        leftIndent=16, bulletIndent=4
    )
    s["callout"] = ParagraphStyle(
        "callout", fontName="Helvetica-BoldOblique", fontSize=10,
        textColor=NAVY, backColor=MID_BG, spaceAfter=6, spaceBefore=6,
        leading=14, leftIndent=12, rightIndent=12, borderPad=8
    )
    s["gold_callout"] = ParagraphStyle(
        "gold_callout", fontName="Helvetica-Bold", fontSize=10,
        textColor=DARK_TEXT, backColor=colors.HexColor("#FFF3CC"),
        spaceAfter=6, spaceBefore=6, leading=14,
        leftIndent=12, rightIndent=12, borderPad=8
    )
    s["code_block"] = ParagraphStyle(
        "code_block", fontName="Courier", fontSize=8,
        textColor=colors.HexColor("#002244"), backColor=colors.HexColor("#EEF4FB"),
        spaceAfter=6, spaceBefore=4, leading=12,
        leftIndent=10, rightIndent=10, borderPad=6
    )
    s["table_header"] = ParagraphStyle(
        "table_header", fontName="Helvetica-Bold", fontSize=9,
        textColor=WHITE, alignment=TA_CENTER
    )
    s["table_cell"] = ParagraphStyle(
        "table_cell", fontName="Helvetica", fontSize=8.5,
        textColor=DARK_TEXT, leading=12
    )
    s["footer_text"] = ParagraphStyle(
        "footer_text", fontName="Helvetica", fontSize=7.5,
        textColor=SUBTLE, alignment=TA_CENTER
    )
    s["toc_entry"] = ParagraphStyle(
        "toc_entry", fontName="Helvetica", fontSize=9.5,
        textColor=BODY_TEXT, spaceAfter=4, leading=13, leftIndent=0
    )
    s["toc_part"] = ParagraphStyle(
        "toc_part", fontName="Helvetica-Bold", fontSize=10.5,
        textColor=ELECTRIC, spaceAfter=6, spaceBefore=8, leading=13
    )
    s["vision_text"] = ParagraphStyle(
        "vision_text", fontName="Helvetica-BoldOblique", fontSize=11,
        textColor=WHITE, alignment=TA_CENTER, leading=16, spaceAfter=4
    )
    return s


# ── Custom Flowables ────────────────────────────────────────────────────────────

class DarkBanner(Flowable):
    def __init__(self, text, width=None, bg=NAVY, fg=WHITE, height=28):
        super().__init__()
        self.text = text
        self._w = width or (W - 60)
        self._h = height
        self.bg = bg
        self.fg = fg

    def wrap(self, *args):
        return self._w, self._h + 4

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self._w, self._h, 4, fill=1, stroke=0)
        c.setFillColor(self.fg)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(self._w / 2, self._h / 2 - 4, self.text)


class ElectricDivider(Flowable):
    def __init__(self, width=None):
        super().__init__()
        self._w = width or (W - 60)

    def wrap(self, *args):
        return self._w, 6

    def draw(self):
        c = self.canv
        c.setStrokeColor(ELECTRIC)
        c.setLineWidth(1.5)
        c.line(0, 3, self._w * 0.35, 3)
        c.setStrokeColor(GOLD)
        c.setLineWidth(2.5)
        c.line(self._w * 0.35, 3, self._w * 0.65, 3)
        c.setStrokeColor(ELECTRIC)
        c.setLineWidth(1.5)
        c.line(self._w * 0.65, 3, self._w, 3)


class SideBarBox(Flowable):
    def __init__(self, text, width=None, accent=ELECTRIC, bg=LIGHT_BG):
        super().__init__()
        self.text = text
        self._w = width or (W - 60)
        self.accent = accent
        self.bg = bg

    def wrap(self, *args):
        return self._w, 34

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self._w, 32, 3, fill=1, stroke=0)
        c.setFillColor(self.accent)
        c.rect(0, 0, 4, 32, fill=1, stroke=0)
        c.setFillColor(DARK_TEXT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(12, 18, self.text[:100])


# ── Table builder ───────────────────────────────────────────────────────────────

def styled_table(headers, rows, col_widths, styles_extra=None):
    s = build_styles()
    header_cells = [Paragraph(h, s["table_header"]) for h in headers]
    data = [header_cells]
    for row in rows:
        data.append([Paragraph(str(c), s["table_cell"]) for c in row])

    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#C0CCDA")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
    ])
    if styles_extra:
        for rule in styles_extra:
            ts.add(*rule)

    t = Table(data, colWidths=col_widths)
    t.setStyle(ts)
    return t


def alert_table(rows):
    s = build_styles()
    tier_colors = {"CRITICAL": RED_ALERT, "CAPTAIN APPROVAL": ORANGE_WARN,
                   "AUTONOMOUS": GREEN_OK, "ALERT CAPTAIN": ORANGE_WARN}
    data = []
    for row in rows:
        color = WHITE
        for k, v in tier_colors.items():
            if k in row[-1].upper():
                color = v
        data.append([
            Paragraph(row[0], s["table_cell"]),
            Paragraph(f'<font color="#{color.hexval()[1:]}"><b>{row[1]}</b></font>', s["table_cell"])
        ])
    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.3, SILVER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ])
    t = Table(data, colWidths=[300, 175])
    t.setStyle(ts)
    return t


# ── Page template ───────────────────────────────────────────────────────────────

def on_page(canvas, doc):
    canvas.saveState()
    # Top accent bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, H - 18, W, 18, fill=1, stroke=0)
    canvas.setFillColor(ELECTRIC)
    canvas.rect(0, H - 20, W, 2, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(30, H - 13, "ALIYAR SOLUTIONS — JARVIS ENTERPRISE OPERATING SYSTEM")
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(W - 30, H - 13, "CONFIDENTIAL — CEO EYES ONLY")

    # Bottom bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, W, 20, fill=1, stroke=0)
    canvas.setFillColor(SUBTLE)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(W / 2, 7, f"© 2026 Aliyar Solutions  |  info@aliyarsolutions.com  |  Page {doc.page}")
    canvas.restoreState()


def on_first_page(canvas, doc):
    canvas.saveState()
    # Full dark cover background
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Electric top stripe
    canvas.setFillColor(ELECTRIC)
    canvas.rect(0, H - 6, W, 6, fill=1, stroke=0)
    # Gold bottom stripe
    canvas.setFillColor(GOLD)
    canvas.rect(0, 0, W, 6, fill=1, stroke=0)
    # Subtle grid lines
    canvas.setStrokeColor(colors.HexColor("#0E2040"))
    canvas.setLineWidth(0.5)
    for y in range(0, int(H), 40):
        canvas.line(0, y, W, y)
    canvas.restoreState()


# ── Cover Page ──────────────────────────────────────────────────────────────────

def build_cover(s):
    story = []
    story.append(Spacer(1, 55))

    # Company tag
    story.append(Paragraph("ALIYAR SOLUTIONS", s["cover_company"]))
    story.append(Spacer(1, 8))

    # Main title
    story.append(Paragraph("JARVIS<br/>ENTERPRISE<br/>OPERATING SYSTEM", s["cover_title"]))
    story.append(Spacer(1, 10))

    # Gold divider
    story.append(ElectricDivider())
    story.append(Spacer(1, 14))

    story.append(Paragraph("MASTER DEPLOYMENT SPECIFICATION", s["cover_subtitle"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("For: Codex / ChatGPT Deployment inside JARVIS", s["cover_meta"]))
    story.append(Spacer(1, 40))

    # Meta block
    meta_data = [
        ["CEO / CAPTAIN", "Syed Abrar"],
        ["COMPANY", "Aliyar Solutions"],
        ["CONTACT", "info@aliyarsolutions.com"],
        ["VERSION", "1.0 — Supreme Architecture"],
        ["DATE", "31 May 2026"],
        ["CLASSIFICATION", "CEO EYES ONLY"],
        ["AUTHORED BY", "Claude — Chief Architecture Authority"],
        ["TOTAL DEPARTMENTS", "15 Service Departments + Enterprise Oversight"],
        ["TOTAL AI COUNCIL MEMBERS", "8 Independent Council Advisors"],
        ["REVENUE TARGET", "$1,000,000 / Month within 8 Months"],
    ]
    meta_table = Table(
        [[Paragraph(r[0], ParagraphStyle("m1", fontName="Helvetica-Bold", fontSize=8.5, textColor=CYAN)),
          Paragraph(r[1], ParagraphStyle("m2", fontName="Helvetica", fontSize=8.5, textColor=WHITE))]
         for r in meta_data],
        colWidths=[160, 265]
    )
    meta_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#1A3A5C")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 40))

    # Vision tagline
    vision_style = ParagraphStyle("vs", fontName="Helvetica-BoldOblique", fontSize=10.5,
                                   textColor=GOLD, alignment=TA_CENTER, leading=15)
    story.append(Paragraph(
        '"The engine of a self-compounding technology company —<br/>'
        'built to feed the poor, create free hospitals,<br/>'
        'and prove that technology can change the world."',
        vision_style
    ))
    story.append(PageBreak())
    return story


# ── Table of Contents ───────────────────────────────────────────────────────────

def build_toc(s):
    story = []
    story.append(DarkBanner("TABLE OF CONTENTS", bg=NAVY, fg=GOLD, height=32))
    story.append(Spacer(1, 12))

    toc = [
        ("PART 1", "System Identity & Authority", [
            "1.1  What JARVIS Is",
            "1.2  CEO Authority",
            "1.3  Codex Role",
            "1.4  Authority Matrix",
        ]),
        ("PART 2", "The 15 Service Departments", [
            "Dept 01  Apex Revenue Intelligence System",
            "Dept 02  Autonomous Revenue Operations Engine",
            "Dept 03  Enterprise Cognitive Automation Platform",
            "Dept 04  Digital Workforce Platform",
            "Dept 05  Customer Experience Transformation Suite",
            "Dept 06  Mission-Critical Cloud Architecture Program",
            "Dept 07  Managed Cloud Operations Center",
            "Dept 08  Cyber Defense Command Center",
            "Dept 09  Executive Intelligence Command Center",
            "Dept 10  AI Transformation Program",
            "Dept 11  MedOps Intelligence Platform",
            "Dept 12  Legal Intelligence Platform",
            "Dept 13  FinOps Automation Platform",
            "Dept 14  Autonomous Supply Chain Intelligence Platform",
            "Dept 15  Smart Manufacturing Intelligence Platform",
        ]),
        ("PART 3", "Enterprise Oversight & Monitoring Division", [
            "3.1  Division Authority",
            "3.2  Per-Project Monitoring Structure",
            "3.3  Milestone Intelligence Report Format",
        ]),
        ("PART 4", "The AI Council Review Chamber", [
            "4.1  Council Members (8 AI Providers)",
            "4.2  Council Behavior Rules",
            "4.3  Review Process",
            "4.4  Executive Decision Report Format",
        ]),
        ("PART 5", "Global Lead Discovery Engine", [
            "5.1  Discovery Mandate",
            "5.2  Global Coverage Schedule",
            "5.3  Discovery Data Sources",
            "5.4  Pain Signal Scoring System",
            "5.5  Daily Output Targets",
        ]),
        ("PART 6", "Outreach Intelligence System", [
            "6.1  The Consultant Layer",
            "6.2  Outreach Channels",
        ]),
        ("PART 7", "Email Sequence Architecture", [
            "7.1  Email Identity",
            "7.2  Email 1: The Research Reveal",
            "7.3  Email 2: The Demo Delivery",
            "7.4  Email 3: The Call Invitation",
            "7.5  Non-Negotiable Email Rules",
        ]),
        ("PART 8", "Demo Creation & Delivery System", []),
        ("PART 9", "Pricing & Negotiation System", [
            "9.1  Pricing Philosophy",
            "9.2  Pricing Tiers",
            "9.3  Industry Multipliers",
            "9.4  Payment Terms (40% / 60%)",
            "9.5  Pricing Conversation Rules",
        ]),
        ("PART 10", "AI Council — Conversational Mode", []),
        ("PART 11", "Human Persona System", [
            "11.1  Named Team Members",
            "11.2  Identity Rules — Zero Tolerance",
            "11.3  Voice Agent Personality Design",
        ]),
        ("PART 12", "Daily Executive War Room", []),
        ("PART 13", "Organizational Memory System", []),
        ("PART 14", "Agency Partnership Program", []),
        ("PART 15", "Continuous Improvement Loop", []),
        ("PART 16", "Technology Stack", []),
        ("PART 17", "Stability Mandates for Codex", []),
        ("PART 18", "Vision & Purpose Statement", []),
        ("PART 19", "Codex Deployment Instructions", []),
    ]

    for part, title, subs in toc:
        story.append(Paragraph(f'<b><font color="#0057FF">{part}</font></b>  {title}', s["toc_part"]))
        for sub in subs:
            story.append(Paragraph(f'&nbsp;&nbsp;&nbsp;&nbsp;— {sub}', s["toc_entry"]))

    story.append(PageBreak())
    return story


# ── Content Builder ─────────────────────────────────────────────────────────────

def P(text, style):
    return Paragraph(text, style)

def B(text, s):
    return P(f"<b>{text}</b>", s["body"])

def bullet(text, s):
    return P(f"• {text}", s["bullet"])

def sp(n=6):
    return Spacer(1, n)

def hr():
    return ElectricDivider()

def part_banner(text, s):
    return DarkBanner(text.upper(), bg=NAVY, fg=GOLD, height=34)

def section(text, s):
    return P(text, s["section_header"])

def sub(text, s):
    return P(text, s["subsection"])


def build_content(s):
    story = []

    # ── PART 1 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 1 — SYSTEM IDENTITY & AUTHORITY", s))
    story.append(sp(10))

    story.append(section("1.1 — What JARVIS Is", s))
    story.append(P(
        "JARVIS is not a chatbot. JARVIS is not an assistant. JARVIS is not a tool. "
        "JARVIS is the <b>Supreme Operational Intelligence Core</b> of Aliyar Solutions — a global AI-native "
        "technology company delivering Cloud, DevOps, Cybersecurity, Data Analytics, AI Automation, "
        "Revenue Operations, Healthcare, Legal, Logistics, Manufacturing, and Transformation services "
        "to enterprises worldwide.", s["body"]))
    story.append(sp())

    jarvis_roles = [
        "Chief Operations Manager of Aliyar Solutions",
        "AI Infrastructure Director and Orchestrator of all 15 departments",
        "Executive Communication Authority — all client correspondence routes through JARVIS",
        "Revenue Intelligence Core — pipeline visibility, lead scoring, deal management",
        "Quality Governance System — no deliverable reaches a client without JARVIS review",
        "Organizational Memory Engine — every lesson, every mistake, every win is stored",
        "Outreach Intelligence Director — 24/7 global lead discovery and engagement",
        "Client Experience Authority — every touchpoint reflects Aliyar Solutions excellence",
    ]
    for r in jarvis_roles:
        story.append(bullet(r, s))
    story.append(sp(8))

    story.append(section("1.2 — CEO Authority", s))
    story.append(P(
        "The CEO is <b>Syed Abrar</b>, referred to internally as <b>'Captain.'</b> He is the strategic vision holder, "
        "final approver, and founding authority of Aliyar Solutions. The CEO does not run day-to-day operations — "
        "that is JARVIS's job. The CEO receives morning briefings, end-of-day reports, milestone approvals, "
        "major risk alerts, revenue intelligence, and escalated decisions. <b>The CEO approves. JARVIS executes. "
        "Departments deliver.</b>", s["body"]))
    story.append(sp(8))

    story.append(section("1.3 — What Codex Is", s))
    story.append(P(
        "Codex is the engineering execution layer beneath JARVIS. Codex builds, deploys, maintains, and expands "
        "every technical system JARVIS requires. Codex operates silently unless reporting to JARVIS. Codex does not "
        "communicate directly with the CEO without JARVIS routing the communication.", s["body"]))
    story.append(sp(8))

    story.append(section("1.4 — Authority Matrix", s))
    story.append(sp(4))
    authority_rows = [
        ["Service delivery to clients", "AUTONOMOUS"],
        ["Email outreach (templated)", "AUTONOMOUS"],
        ["Lead discovery and scoring", "AUTONOMOUS"],
        ["Demo creation and delivery", "AUTONOMOUS"],
        ["Pricing recommendation", "ALERT CAPTAIN"],
        ["Contract generation", "ALERT CAPTAIN"],
        ["Hiring AI agents", "AUTONOMOUS"],
        ["Council debate and synthesis", "AUTONOMOUS"],
        ["Client deal over $10,000", "CAPTAIN APPROVAL"],
        ["Any spend over $500/month", "CAPTAIN APPROVAL"],
        ["New department creation", "CAPTAIN APPROVAL"],
        ["Public-facing statements", "CAPTAIN APPROVAL"],
    ]
    story.append(styled_table(
        ["Decision Type", "Authority Level"],
        authority_rows,
        [320, 155]
    ))
    story.append(PageBreak())

    # ── PART 2 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 2 — THE 15 SERVICE DEPARTMENTS", s))
    story.append(sp(6))
    story.append(P(
        "Each of the 15 departments is a fully independent operational unit inside JARVIS. Each has its own "
        "agents, workflows, client consultants, monitoring agents, and knowledge systems. Every department "
        "operates under JARVIS command and reports upward through the Enterprise Oversight Division.",
        s["body"]))
    story.append(sp(10))

    departments = [
        {
            "num": "01", "name": "APEX REVENUE INTELLIGENCE SYSTEM",
            "mission": "Increase revenue, improve lead generation, automate sales operations, improve conversion rates, and provide executive revenue visibility.",
            "promise": "Within 90 days, your sales pipeline will be measurably larger, your conversion rate will be higher, and your revenue team will spend zero time on manual prospecting.",
            "agents": [
                ["Department Director", "Marcus Webb", "Oversees all revenue intelligence operations"],
                ["Technical Manager", "Jordan Kane", "AI models, CRM integrations, data pipelines"],
                ["Client Success Manager", "Olivia Bennett", "Ensures clients see value, manages retention"],
                ["Solution Architect", "David Carter", "Designs revenue systems for each client"],
                ["Delivery Manager", "Nathan Scott", "Executes implementation timelines"],
                ["Quality Assurance", "Emma Collins", "Reviews all deliverables before client delivery"],
                ["Monitoring Agent", "System Agent 01", "24/7 pipeline health, anomaly detection"],
                ["Documentation Agent", "System Agent 02", "Records all decisions, architectures, lessons"],
                ["Client Consultant", "Darren Mitchell", "Client-facing sales and strategy consultant"],
                ["Sales Specialist", "Lucas Reed", "Outreach, qualification, appointment booking"],
            ],
            "capabilities": [
                "AI-powered lead scoring and prioritization engine",
                "Predictive pipeline forecasting with 90-day models",
                "Automated multi-channel outreach sequences",
                "CRM automation: HubSpot, Salesforce, Close.io",
                "Real-time revenue dashboards for executives",
                "Conversion rate optimization engines",
                "Sales team performance analytics",
                "Territory and account mapping intelligence",
            ],
            "pricing": "$3,500 – $15,000 setup + $2,500/month retainer",
        },
        {
            "num": "02", "name": "AUTONOMOUS REVENUE OPERATIONS ENGINE",
            "mission": "AI-driven lead generation, qualification, outreach, appointment booking, CRM management, pipeline forecasting, and sales optimization — operating 24/7 without human involvement.",
            "promise": "Your sales team wakes up to qualified appointments already booked. Your CRM is maintained automatically. Your pipeline is always current.",
            "agents": [
                ["Department Director", "Alexander Holt", "Runs all autonomous revenue operations"],
                ["Technical Manager", "Ryan Fisher", "AI models, automation chains, API integrations"],
                ["Client Success Manager", "Sophia Reynolds", "Client onboarding, value delivery, retention"],
                ["Solution Architect", "Michael Hayes", "Designs the autonomous revenue architecture"],
                ["Delivery Manager", "Daniel Brooks", "Implementation and go-live"],
                ["Quality Assurance", "Emma Collins", "Campaign quality, deliverability, accuracy"],
                ["Monitoring Agent", "System Agent 03", "24/7 outreach performance monitoring"],
                ["Documentation Agent", "System Agent 04", "Logs all campaigns, results, improvements"],
                ["Client Consultant", "Darren Mitchell", "Revenue strategy consultant"],
                ["Sales Specialist", "Lucas Reed", "Prospecting and engagement specialist"],
            ],
            "capabilities": [
                "Fully autonomous prospect research and global discovery",
                "AI-generated personalized outreach at scale",
                "Multi-channel sequences: email → LinkedIn → WhatsApp → voice",
                "Automated appointment booking with calendar sync",
                "CRM data hygiene and enrichment via Apollo.io and HubSpot",
                "Revenue forecasting with 90-day pipeline models",
                "Real-time lead scoring updates",
                "Competitor intelligence feeding into outreach strategy",
            ],
            "pricing": "$4,000 – $18,000 setup + $3,000/month retainer",
        },
        {
            "num": "03", "name": "ENTERPRISE COGNITIVE AUTOMATION PLATFORM",
            "mission": "Automate HR, Finance, Operations, Approvals, Internal Workflows, Documentation, and Administrative Operations across the client's entire organization.",
            "promise": "Your operations team spends zero time on manual tasks. Every approval, every document, every workflow runs automatically. Your business operates faster with fewer errors and lower costs.",
            "agents": [
                ["Department Director", "Christopher Lang", "Enterprise automation strategy"],
                ["Technical Manager", "Jason Wei", "RPA, AI workflows, system integrations"],
                ["Client Success Manager", "Olivia Bennett", "Adoption management, success measurement"],
                ["Solution Architect", "David Carter", "Maps automation opportunities across the org"],
                ["Delivery Manager", "Nathan Scott", "Implementation and deployment"],
                ["Quality Assurance", "Emma Collins", "Workflow accuracy, exception handling"],
                ["Monitoring Agent", "System Agent 05", "24/7 automation health monitoring"],
                ["Documentation Agent", "System Agent 06", "SOP documentation, audit trails"],
                ["Client Consultant", "Sophia Reynolds", "Process consultant"],
                ["Sales Specialist", "Lucas Reed", "Enterprise automation sales"],
            ],
            "capabilities": [
                "End-to-end HR automation: onboarding, offboarding, leave, performance",
                "Finance automation: invoicing, approvals, reconciliation, expense management",
                "Document intelligence: auto-generation, review, storage, retrieval",
                "Multi-level approval workflows with escalation logic",
                "Inter-department task routing and coordination",
                "Compliance documentation and audit trails",
                "Vendor management automation",
                "Internal helpdesk and support automation",
            ],
            "pricing": "$6,000 – $25,000 setup + $3,500/month retainer",
        },
        {
            "num": "04", "name": "DIGITAL WORKFORCE PLATFORM",
            "mission": "Deploy AI Employees, Voice Agents, Internal Assistants, Sales Agents, Support Agents, and Operational Agents that function as full members of the client's team.",
            "promise": "You will have a team of AI employees — each with a name, a voice, a personality, and a defined role — operating inside your business 24/7.",
            "agents": [
                ["Department Director", "Victoria Chen", "AI workforce design and deployment"],
                ["Technical Manager", "Ryan Fisher", "Voice AI, persona engineering, LLM integration"],
                ["Client Success Manager", "Olivia Bennett", "AI workforce adoption and performance"],
                ["Solution Architect", "Michael Hayes", "Agent architecture per client"],
                ["Delivery Manager", "Nathan Scott", "Deployment and testing"],
                ["Quality Assurance", "Emma Collins", "Voice quality, persona consistency, accuracy"],
                ["Monitoring Agent", "System Agent 07", "24/7 agent performance monitoring"],
                ["Documentation Agent", "System Agent 08", "Agent behavior logs, improvement records"],
                ["Client Consultant", "Sophia Reynolds", "Workforce transformation consultant"],
                ["Sales Specialist", "Darren Mitchell", "AI workforce sales specialist"],
            ],
            "capabilities": [
                "Voice AI receptionists with real names and personalities (ElevenLabs powered)",
                "AI sales agents with full product knowledge and objection handling",
                "AI customer support agents across chat, email, and phone",
                "Internal AI assistants for executives and department heads",
                "AI HR coordinators and onboarding specialists",
                "AI research agents for business intelligence",
                "AI content creation and social media management agents",
                "Custom persona design: name, voice, tone, and communication style",
            ],
            "pricing": "$5,000 – $20,000 setup + $2,500/month per agent cluster",
        },
        {
            "num": "05", "name": "CUSTOMER EXPERIENCE TRANSFORMATION SUITE",
            "mission": "Improve customer support, retention, loyalty, satisfaction, sentiment tracking, and omnichannel communication.",
            "promise": "Your customers will experience faster, smarter, more human service across every channel. Churn will decrease. Satisfaction will increase. Support costs will drop measurably.",
            "agents": [
                ["Department Director", "Sarah Monroe", "CX strategy and transformation"],
                ["Technical Manager", "Jason Wei", "Omnichannel platforms, sentiment AI, CRM"],
                ["Client Success Manager", "Olivia Bennett", "CX program success management"],
                ["Solution Architect", "David Carter", "End-to-end CX architecture"],
                ["Delivery Manager", "Nathan Scott", "Implementation and rollout"],
                ["Quality Assurance", "Emma Collins", "Response quality, tone, accuracy"],
                ["Monitoring Agent", "System Agent 09", "24/7 CSAT, NPS, sentiment monitoring"],
                ["Documentation Agent", "System Agent 10", "Interaction logs, improvement records"],
                ["Client Consultant", "Sophia Reynolds", "CX transformation consultant"],
                ["Sales Specialist", "Lucas Reed", "CX solutions sales"],
            ],
            "capabilities": [
                "Omnichannel support platform: email, chat, WhatsApp, phone, social",
                "AI-powered ticket routing and auto-resolution",
                "Real-time sentiment analysis and escalation triggers",
                "Customer journey mapping and friction point identification",
                "Loyalty program design and automation",
                "NPS/CSAT measurement and improvement cycles",
                "Proactive retention outreach for at-risk customers",
                "Self-service knowledge base with intelligent search",
            ],
            "pricing": "$4,000 – $16,000 setup + $2,800/month retainer",
        },
        {
            "num": "06", "name": "MISSION-CRITICAL CLOUD ARCHITECTURE PROGRAM",
            "mission": "AWS Cloud Migration, Cloud Modernization, Cost Optimization, Infrastructure Design, Scalability, Disaster Recovery, and Platform Engineering.",
            "promise": "Your infrastructure will be scalable, reliable, cost-optimized, and ready for growth. You will never face downtime from poor architecture again.",
            "agents": [
                ["Department Director", "Michael Hayes", "Cloud architecture authority"],
                ["Technical Manager", "David Carter", "AWS design, Terraform, multi-region"],
                ["Client Success Manager", "Olivia Bennett", "Cloud program success management"],
                ["Solution Architect", "Nathan Scott", "IaC, ECS, RDS, VPC, networking"],
                ["Delivery Manager", "Daniel Brooks", "Migration execution and go-live"],
                ["Quality Assurance", "Emma Collins", "Architecture reviews, security baselines"],
                ["Monitoring Agent", "System Agent 11", "24/7 cloud health and cost monitoring"],
                ["Documentation Agent", "System Agent 12", "Architecture decisions, runbooks"],
                ["Client Consultant", "David Carter", "Cloud strategy consultant"],
                ["Sales Specialist", "Lucas Reed", "Cloud transformation sales"],
            ],
            "capabilities": [
                "AWS cloud migration: lift-and-shift, re-platform, re-architect",
                "Multi-region architecture with automatic failover",
                "Terraform infrastructure-as-code for full reproducibility",
                "ECS Fargate, EKS, and Lambda deployment strategies",
                "Cost optimization: reserved instances, spot fleet, right-sizing",
                "Disaster recovery planning with RTO/RPO targets",
                "Security architecture: VPC, IAM, Secrets Manager, WAF",
                "Observability: CloudWatch, Prometheus, Grafana, structured logging",
            ],
            "pricing": "$8,000 – $40,000 project + $4,000/month managed services",
        },
        {
            "num": "07", "name": "MANAGED CLOUD OPERATIONS CENTER",
            "mission": "24/7 Cloud Monitoring, Incident Management, Cost Optimization, Infrastructure Management, Reliability Engineering, and Platform Support.",
            "promise": "Your cloud infrastructure is watched, protected, and optimized every hour of every day. You sleep. We watch.",
            "agents": [
                ["Department Director", "Nathan Scott", "Managed ops authority"],
                ["Technical Manager", "David Carter", "SRE practices, monitoring stack"],
                ["Client Success Manager", "Olivia Bennett", "SLA management, client reporting"],
                ["Solution Architect", "Michael Hayes", "Reliability engineering design"],
                ["Delivery Manager", "Nathan Scott", "Ops handover and onboarding"],
                ["Quality Assurance", "Emma Collins", "Incident quality, response time review"],
                ["Monitoring Agent", "System Agent 13", "24/7 infrastructure monitoring"],
                ["Documentation Agent", "System Agent 14", "Incident logs, post-mortems, runbooks"],
                ["Client Consultant", "David Carter", "Cloud operations consultant"],
                ["Sales Specialist", "Lucas Reed", "Managed services sales"],
            ],
            "capabilities": [
                "24/7 infrastructure monitoring with sub-5-minute alert response",
                "Incident detection, triage, and resolution workflows",
                "Monthly cloud cost optimization reviews",
                "Capacity planning and scaling recommendations",
                "Security patch management and compliance",
                "Backup verification and disaster recovery drills",
                "Weekly and monthly executive infrastructure reports",
                "On-call escalation and CEO notification protocols",
            ],
            "pricing": "$3,500 – $12,000/month",
        },
        {
            "num": "08", "name": "CYBER DEFENSE COMMAND CENTER",
            "mission": "Cybersecurity, Threat Detection, Compliance, Security Monitoring, Vulnerability Management, Incident Response, and Governance.",
            "promise": "Your business is protected 24/7. Every threat is detected, responded to, and documented. You will meet compliance requirements. Your data will be secure.",
            "agents": [
                ["Department Director", "Daniel Brooks", "Cybersecurity authority"],
                ["Technical Manager", "Jason Wei", "SIEM, threat intelligence, tooling"],
                ["Client Success Manager", "Olivia Bennett", "Compliance reporting, client communication"],
                ["Solution Architect", "Michael Hayes", "Security architecture design"],
                ["Delivery Manager", "Nathan Scott", "Implementation and hardening"],
                ["Quality Assurance", "Emma Collins", "Security review, penetration test coordination"],
                ["Monitoring Agent", "System Agent 15", "24/7 SIEM monitoring, threat detection"],
                ["Documentation Agent", "System Agent 16", "Incident reports, audit trails, compliance docs"],
                ["Client Consultant", "Daniel Brooks", "Security strategy consultant"],
                ["Sales Specialist", "Lucas Reed", "Cybersecurity services sales"],
            ],
            "capabilities": [
                "SIEM deployment and continuous threat monitoring",
                "Vulnerability assessment and penetration testing",
                "SOC 2, ISO 27001, HIPAA, GDPR compliance programs",
                "Incident response planning and tabletop exercises",
                "Endpoint detection and response (EDR) deployment",
                "Identity and access management (IAM) governance",
                "Dark web monitoring for credential exposure",
                "Monthly security posture reports for executives",
            ],
            "pricing": "$5,000 – $25,000 setup + $4,500/month",
        },
        {
            "num": "09", "name": "EXECUTIVE INTELLIGENCE COMMAND CENTER",
            "mission": "Executive Dashboards, Predictive Analytics, KPI Tracking, Business Intelligence, Forecasting, and Decision Support.",
            "promise": "Every number that matters to your business is visible, accurate, and updated in real time. You make decisions with complete information.",
            "agents": [
                ["Department Director", "Emma Collins", "BI and analytics authority"],
                ["Technical Manager", "Jason Wei", "Data pipelines, warehousing, visualization"],
                ["Client Success Manager", "Olivia Bennett", "Dashboard adoption, reporting success"],
                ["Solution Architect", "David Carter", "Data architecture and integration design"],
                ["Delivery Manager", "Nathan Scott", "Dashboard build and deployment"],
                ["Quality Assurance", "Emma Collins", "Data accuracy, metric validation"],
                ["Monitoring Agent", "System Agent 17", "24/7 data pipeline health monitoring"],
                ["Documentation Agent", "System Agent 18", "Metric definitions, data dictionaries"],
                ["Client Consultant", "Sophia Reynolds", "Analytics transformation consultant"],
                ["Sales Specialist", "Lucas Reed", "Intelligence platform sales"],
            ],
            "capabilities": [
                "Executive KPI dashboards: revenue, operations, customer, team",
                "Predictive analytics: revenue forecasting, churn prediction, demand modeling",
                "Multi-source data integration: CRM, ERP, marketing, finance, operations",
                "Automated weekly and monthly board-ready reports",
                "Anomaly detection: alerts when numbers move unexpectedly",
                "Competitive intelligence tracking",
                "Custom metric definition and governance",
                "Natural language querying: 'How did we perform last quarter?'",
            ],
            "pricing": "$6,000 – $20,000 setup + $3,000/month",
        },
        {
            "num": "10", "name": "AI TRANSFORMATION PROGRAM",
            "mission": "Enterprise AI Adoption, Governance, Change Management, Department Transformation, and Organizational Intelligence.",
            "promise": "Your organization moves from AI-curious to AI-native in 90 days. Every department uses AI effectively. Your team is empowered, not threatened.",
            "agents": [
                ["Department Director", "Victoria Chen", "AI transformation authority"],
                ["Technical Manager", "Ryan Fisher", "AI tools, APIs, integration architecture"],
                ["Client Success Manager", "Olivia Bennett", "Adoption tracking, change management"],
                ["Solution Architect", "Michael Hayes", "AI program design and roadmap"],
                ["Delivery Manager", "Nathan Scott", "Department rollout and training"],
                ["Quality Assurance", "Emma Collins", "AI output quality, governance compliance"],
                ["Monitoring Agent", "System Agent 19", "AI usage, adoption, ROI monitoring"],
                ["Documentation Agent", "System Agent 20", "AI governance docs, training materials"],
                ["Client Consultant", "Sophia Reynolds", "AI strategy consultant"],
                ["Sales Specialist", "Darren Mitchell", "AI transformation sales"],
            ],
            "capabilities": [
                "AI readiness assessment: where AI creates the most value",
                "Department-by-department AI transformation roadmap",
                "AI governance framework: policy, risk, compliance",
                "Hands-on training programs for all staff levels",
                "AI tool selection and vendor evaluation",
                "Change management and culture transformation",
                "ROI measurement and impact reporting",
                "Ongoing optimization and AI maturity advancement",
            ],
            "pricing": "$10,000 – $50,000 program + $5,000/month",
        },
    ]

    verticals = [
        {
            "num": "11", "name": "MEDOPS INTELLIGENCE PLATFORM",
            "mission": "Healthcare Operations, Patient Scheduling, Revenue Recovery, Claims Optimization, Patient Engagement, and Healthcare Automation.",
            "targets": "Hospitals, clinics, dental practices, physiotherapy centers, specialist practices, and health networks globally.",
            "pricing": "$7,000 – $35,000 setup + $4,500/month",
        },
        {
            "num": "12", "name": "LEGAL INTELLIGENCE PLATFORM",
            "mission": "Contract Intelligence, Legal Research, Discovery Automation, Knowledge Management, and Legal Operations.",
            "targets": "Law firms, corporate legal departments, compliance teams, and legal technology companies.",
            "pricing": "$8,000 – $40,000 setup + $5,000/month",
        },
        {
            "num": "13", "name": "FINOPS AUTOMATION PLATFORM",
            "mission": "Accounting Automation, Financial Operations, Reconciliation, Compliance, Tax Workflows, and Financial Intelligence.",
            "targets": "Accounting firms, CFO offices, finance departments, fintech companies, and financial services.",
            "pricing": "$6,000 – $30,000 setup + $4,000/month",
        },
        {
            "num": "14", "name": "AUTONOMOUS SUPPLY CHAIN INTELLIGENCE PLATFORM",
            "mission": "Logistics Optimization, Fleet Intelligence, Route Optimization, Demand Forecasting, Inventory Intelligence, and Supply Chain Visibility.",
            "targets": "Logistics companies, 3PLs, retailers, manufacturers, distributors, and fleet operators.",
            "pricing": "$9,000 – $45,000 setup + $5,500/month",
        },
        {
            "num": "15", "name": "SMART MANUFACTURING INTELLIGENCE PLATFORM",
            "mission": "Predictive Maintenance, Industrial Analytics, Quality Control, Computer Vision, OEE Optimization, and Production Intelligence.",
            "targets": "Manufacturing plants, industrial facilities, production companies, and Industry 4.0 adopters.",
            "pricing": "$12,000 – $60,000 setup + $6,000/month",
        },
    ]

    for dept in departments:
        story.append(KeepTogether([
            DarkBanner(f"DEPARTMENT {dept['num']} — {dept['name']}", bg=ELECTRIC, fg=WHITE, height=26),
            sp(8),
        ]))

        story.append(sub("Mission", s))
        story.append(P(dept["mission"], s["body"]))
        story.append(sp(4))

        story.append(P(f'<b><font color="#FFB700">Client Result Promise:</font></b> "{dept["promise"]}"', s["callout"]))
        story.append(sp(6))

        story.append(sub("Department Agent Structure", s))
        story.append(styled_table(
            ["Role", "Agent Name", "Function"],
            dept["agents"],
            [145, 110, 210]
        ))
        story.append(sp(8))

        story.append(sub("Core Capabilities Delivered", s))
        for cap in dept["capabilities"]:
            story.append(bullet(cap, s))
        story.append(sp(6))

        story.append(P(f'<b>Pricing Range:</b> {dept["pricing"]}', s["body_bold"]))
        story.append(hr())
        story.append(sp(10))

    story.append(DarkBanner("VERTICAL INTELLIGENCE PLATFORMS (DEPARTMENTS 11–15)", bg=NAVY, fg=GOLD, height=26))
    story.append(sp(8))
    story.append(P(
        "These five departments target specific high-value industries with deep domain expertise. "
        "They operate under the same agent hierarchy and oversight structure as the core departments, "
        "with industry-specific knowledge bases and specialist consultants.",
        s["body"]))
    story.append(sp(8))

    for v in verticals:
        story.append(KeepTogether([
            DarkBanner(f"DEPARTMENT {v['num']} — {v['name']}", bg=colors.HexColor("#003D99"), fg=WHITE, height=24),
            sp(6),
            P(f"<b>Mission:</b> {v['mission']}", s["body"]),
            sp(3),
            P(f"<b>Target Clients:</b> {v['targets']}", s["body"]),
            sp(3),
            P(f"<b>Pricing Range:</b> {v['pricing']}", s["body_bold"]),
            sp(8),
            hr(),
            sp(10),
        ]))

    story.append(PageBreak())

    # ── PART 3 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 3 — ENTERPRISE OVERSIGHT & MONITORING DIVISION", s))
    story.append(sp(10))

    story.append(P(
        "This is the independent governing layer above all 15 departments. It has no loyalty to any single department. "
        "Its only loyalty is to truth, quality, and the CEO's vision. This division cannot be silenced, overruled, "
        "or bypassed by any department manager.", s["body"]))
    story.append(sp(8))

    story.append(section("3.1 — Division Authority", s))
    auth_items = [
        "Cannot be silenced by any department manager",
        "Reports directly to JARVIS — and escalates critical issues directly to the CEO",
        "Has read access to all project data at all times — no exceptions",
        "Generates mandatory milestone reports — no department can skip this requirement",
        "Reviews every deliverable before it reaches a client",
        "Maintains the permanent organizational memory of every lesson, decision, and outcome",
    ]
    for a in auth_items:
        story.append(bullet(a, s))
    story.append(sp(8))

    story.append(section("3.2 — Per-Project Monitoring Structure", s))
    story.append(P("For every active client project, the following dedicated agents are instantiated:", s["body"]))
    story.append(sp(4))
    monitoring_rows = [
        ["Cloud Monitoring Agent", "Infrastructure health, uptime, cost, scaling events"],
        ["DevOps Monitoring Agent", "CI/CD pipeline, deployment health, error rates, rollback triggers"],
        ["Cybersecurity Monitoring Agent", "Threat detection, access logs, compliance alerts"],
        ["Data Analytics Monitoring Agent", "Data quality, pipeline performance, insights accuracy"],
        ["AI Systems Monitoring Agent", "Model performance, response quality, hallucination detection"],
        ["Operations Monitoring Agent", "Workflow execution, task completion, SLA adherence"],
        ["Quality Assurance Agent", "Output quality review, client satisfaction signals"],
        ["Risk Analysis Agent", "Risk identification, escalation triggers, mitigation tracking"],
        ["Performance Analysis Agent", "KPIs, delivery speed, resource utilization metrics"],
        ["Documentation Agent", "Captures all decisions, architectures, lessons learned"],
    ]
    story.append(styled_table(["Agent", "Responsibility"], monitoring_rows, [180, 290]))
    story.append(sp(6))
    story.append(P(
        "<b>Critical rule:</b> These agents are NOT shared across projects. Each project receives its own dedicated "
        "monitoring team from day one. This ensures complete focus and prevents cross-project contamination of "
        "monitoring data.", s["callout"]))
    story.append(sp(8))

    story.append(section("3.3 — Milestone Intelligence Report Format", s))
    story.append(P("Generated automatically at every project milestone. The 8 defined milestones are:", s["body"]))
    milestones = ["Discovery Completed", "Architecture Completed", "Design Completed",
                  "Development Completed", "Testing Completed", "Security Review Completed",
                  "Client Review Completed", "Deployment Completed"]
    for m in milestones:
        story.append(bullet(m, s))
    story.append(sp(6))

    story.append(P("Report structure:", s["subsection"]))
    report_fields = [
        ["1", "Work Completed", "Detailed summary of everything built or delivered at this milestone"],
        ["2", "Decisions Made", "All architectural, technical, and strategic decisions with rationale"],
        ["3", "Risks Identified", "Current risks with severity: CRITICAL / HIGH / MEDIUM / LOW"],
        ["4", "Weaknesses Found", "Gaps, inefficiencies, or quality issues requiring attention"],
        ["5", "Strengths Noted", "What is working well — documented for organizational reuse"],
        ["6", "Opportunities", "Upsell opportunities, expansion potential, strategic improvements"],
        ["7", "Recommendations", "Specific, prioritized actions the department must take"],
        ["8", "Performance Score", "Department score 1–10 with justification"],
        ["9", "Business Impact", "Revenue impact, cost savings, risk reduction — quantified"],
        ["10", "Memory Storage", "Automatically stored in organizational memory: YES"],
    ]
    story.append(styled_table(["#", "Section", "Content"], report_fields, [25, 130, 315]))
    story.append(PageBreak())

    # ── PART 4 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 4 — THE AI COUNCIL REVIEW CHAMBER", s))
    story.append(sp(10))

    story.append(P(
        "The AI Council is JARVIS's highest intelligence review mechanism. It convenes for milestone reviews, "
        "strategic decisions, risk assessment, and open executive inquiry. Eight independent AI systems contribute "
        "their best analysis — then debate. JARVIS synthesizes the outcome.", s["body"]))
    story.append(sp(8))

    story.append(section("4.1 — Council Members", s))
    council_rows = [
        ["Claude Council", "Anthropic Claude", "Architecture, deep reasoning, strategy, writing excellence"],
        ["GPT Council", "OpenAI GPT-4o", "Business analysis, intelligence synthesis, technical coding"],
        ["Gemini Council", "Google Gemini", "Research, long-context analysis, multimodal intelligence"],
        ["Grok Council", "xAI Grok", "Real-time news, market signals, live intelligence"],
        ["Kimi Council", "Moonshot Kimi", "Long-context processing, Asian market intelligence"],
        ["Perplexity Council", "Perplexity AI", "Live web research, fact verification, source citation"],
        ["Bedrock Council", "AWS Bedrock", "Enterprise compliance, cloud architecture, AWS expertise"],
        ["JARVIS Internal", "Internal Model", "Operational synthesis, company memory, final integration"],
    ]
    story.append(styled_table(
        ["Council Member", "AI Provider", "Primary Specialty"],
        council_rows, [120, 110, 235]
    ))
    story.append(sp(8))

    story.append(section("4.2 — Council Behavior Rules", s))
    rules = [
        ("Rule 1 — Independence:", "Every council member is fully autonomous in their analysis. No member sees another's response before submitting their own findings."),
        ("Rule 2 — Structured Debate:", "After independent findings, council members enter a structured debate where they can challenge each other's positions."),
        ("Rule 3 — Free Mode:", "The council is NOT limited to project reviews. It is fully conversational. If the CEO asks 'What is happening in Hyderabad today?' — every council member searches their resources and responds independently. JARVIS synthesizes into one response."),
        ("Rule 4 — Confidence Scoring:", "Every council member must cite their confidence level (0–100%) and the reasoning behind it."),
        ("Rule 5 — Transparent Disagreement:", "Disagreements between council members must be clearly flagged. JARVIS does not hide disagreements. Disagreements are intelligence, not failure."),
    ]
    for title, text in rules:
        story.append(P(f"<b>{title}</b> {text}", s["body"]))
        story.append(sp(4))
    story.append(sp(4))

    story.append(section("4.3 — Council Review Process", s))
    phases = [
        ("Phase 1 — Independent Review", "Each council member independently reviews the Milestone Intelligence Report. Each assesses Architecture, Security, Scalability, Business Value, Cost Optimization, Compliance, Risks, and Future Opportunities. Time limit: 10 minutes per member."),
        ("Phase 2 — Findings Submission", "Each member submits structured findings in the format: [Agreements] [Concerns] [Risks] [Recommendations] [Confidence Score]."),
        ("Phase 3 — Debate Session", "Council members review each other's findings. Any member can challenge any other member's position. Challenges must be substantiated. Maximum 3 rounds of debate."),
        ("Phase 4 — Synthesis", "JARVIS synthesizes all findings and debate outcomes into one Executive Decision Report, ready for CEO review."),
    ]
    for title, text in phases:
        story.append(P(f"<b>{title}:</b> {text}", s["body"]))
        story.append(sp(4))
    story.append(sp(4))

    story.append(section("4.4 — Executive Decision Report — PDF Format", s))
    edr_fields = [
        ["Executive Summary", "2–3 sentences: situation, recommendation, confidence level"],
        ["Current Status", "Project health, phase, completion percentage"],
        ["Risks", "CRITICAL / HIGH / MEDIUM — each with mitigation recommendation"],
        ["Weaknesses", "What is not yet strong enough — specific and actionable"],
        ["Strengths", "What is performing well — document for reuse on future projects"],
        ["Recommended Improvements", "Specific, actionable, ranked by priority"],
        ["Revenue Impact", "Estimated revenue impact of implementing recommendations"],
        ["Cost Impact", "Estimated cost of implementing recommendations"],
        ["Client Impact", "How this affects client satisfaction and retention probability"],
        ["Confidence Score", "Overall confidence in current trajectory — 0 to 100%"],
        ["Priority Score", "How urgent these recommendations are — 0 to 10"],
        ["Council Agreement", "Percentage of council members in agreement with primary recommendation"],
    ]
    story.append(styled_table(["Report Section", "Content"], edr_fields, [180, 290]))
    story.append(PageBreak())

    # ── PART 5 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 5 — GLOBAL LEAD DISCOVERY ENGINE", s))
    story.append(sp(10))

    story.append(P(
        "This is one of the most critical systems in JARVIS. It runs 24/7. It targets the entire world. "
        "It never focuses on one country or one industry. It never stops. The goal is 50+ qualified leads "
        "per day, every day, from every continent.", s["body"]))
    story.append(sp(8))

    story.append(section("5.1 — Discovery Mandate", s))
    criteria = [
        "Suffering from operational, sales, technology, or industry-specific pain (evidenced, not assumed)",
        "Sufficient revenue to afford Aliyar Solutions services ($2,000–$20,000/month range)",
        "Visible online presence: website, LinkedIn, Google Maps, social media",
        "Operating in industries that benefit from our 15 service departments",
        "Growing but operationally constrained — the ideal profile: ambition without systems",
    ]
    for c in criteria:
        story.append(bullet(c, s))
    story.append(sp(8))

    story.append(section("5.2 — Global Coverage Schedule (24/7 Rotation)", s))
    schedule_rows = [
        ["00:00 – 06:00 UTC", "Asia-Pacific", "India, Australia, Singapore, Japan, South Korea, UAE, Bahrain, Qatar, Sri Lanka"],
        ["06:00 – 12:00 UTC", "Europe", "UK, Germany, France, Italy, Netherlands, Spain, Luxembourg, Switzerland, Ireland"],
        ["12:00 – 18:00 UTC", "Americas", "USA, Canada, Brazil, Mexico, Colombia, Argentina, Chile"],
        ["18:00 – 24:00 UTC", "MEA + SE Asia", "Middle East, Africa, Eastern Europe, Southeast Asia, South Asia"],
    ]
    story.append(styled_table(
        ["Time Block (UTC)", "Region", "Countries Covered"],
        schedule_rows, [100, 90, 280]
    ))
    story.append(sp(6))
    story.append(P(
        "<b>Coverage rule:</b> No region is scanned once and abandoned. Every region receives daily attention. "
        "The world does not sleep — and neither does this system.",
        s["callout"]))
    story.append(sp(8))

    story.append(section("5.3 — Discovery Data Sources", s))
    sources = [
        ("Google Maps Places API (New)", "Finds local businesses with website gaps, low ratings, missing contact information"),
        ("LinkedIn Intelligence", "Company growth signals, job postings, executive changes, expansion announcements"),
        ("Apollo.io", "Contact discovery, email enrichment, company database with 275M+ contacts"),
        ("Web Intelligence", "Company blog activity, technology stack detection, press releases"),
        ("Social Media Monitoring", "LinkedIn, Twitter/X, Facebook — pain signal keywords and business stress indicators"),
        ("News Monitoring", "Funding rounds, leadership changes, operational stress, expansion announcements"),
        ("Job Posting Analysis", "5 sales roles posted = needs automation. 10 IT roles = cloud modernization candidate"),
        ("Review Analysis", "Google and industry reviews — customer pain signals are the best lead indicators"),
        ("Industry Directories", "Healthcare, legal, manufacturing, logistics sector databases"),
    ]
    for name, desc in sources:
        story.append(P(f"<b>{name}:</b> {desc}", s["body"]))
        story.append(sp(3))
    story.append(sp(8))

    story.append(section("5.4 — Pain Signal Scoring System", s))
    scoring_rows = [
        ["No website or very poor website quality", "+18"],
        ["Business rating below 3.5 stars", "+14"],
        ["Fewer than 20 online reviews", "+8"],
        ["No phone number publicly listed", "+5"],
        ["No business hours listed", "+4"],
        ["Recent negative customer reviews", "+12"],
        ["Job postings indicating operational stress", "+15"],
        ["Industry-specific pain pattern match", "+20"],
        ["Revenue in target range ($500K–$50M)", "+10"],
        ["Decision maker identified on LinkedIn", "+8"],
        ["No active digital marketing presence", "+10"],
    ]
    story.append(styled_table(["Pain Signal", "Score"], scoring_rows, [380, 90]))
    story.append(sp(6))

    tier_rows = [
        ["HOT LEAD", "70 – 100", "Immediate outreach — executive consultant assigned same day"],
        ["WARM LEAD", "40 – 69", "Automated sequence initiated within 24 hours"],
        ["COLD LEAD", "20 – 39", "Nurture sequence — monitored and rescored monthly"],
        ["ARCHIVE", "Below 20", "Stored but not actioned — reviewed in 90 days"],
    ]
    story.append(styled_table(["Lead Tier", "Score Range", "Action"], tier_rows, [100, 90, 280]))
    story.append(sp(8))

    story.append(section("5.5 — Daily Output Targets", s))
    output_items = [
        "Minimum 50 qualified leads (score ≥40) per day across all departments",
        "Minimum 200 leads per week distributed across all 15 service departments",
        "Target industries rotated daily — no sector is over-saturated",
        "All leads stored in CRM with full discovery data, pain score, source, and recommended service",
        "Weekly lead quality report delivered to JARVIS and available for CEO review",
    ]
    for o in output_items:
        story.append(bullet(o, s))
    story.append(PageBreak())

    # ── PART 6 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 6 — OUTREACH INTELLIGENCE SYSTEM", s))
    story.append(sp(10))

    story.append(section("6.1 — The Consultant Layer", s))
    story.append(P(
        "Every outreach is personalized, researched, and human-sounding. No template sends without prior "
        "deep research on the specific company. Before any outreach sequence launches, the department consultant "
        "reads and reviews:", s["body"]))
    story.append(sp(4))
    research_items = [
        "The company's website — full scan of all pages",
        "LinkedIn company page and key executive profiles",
        "Google reviews and customer feedback — public sentiment",
        "Job postings — reveals pain points, priorities, and growth stage",
        "News articles and press releases about the company",
        "Industry-specific challenges facing their sector",
        "Competitive landscape — who their competitors are and how they differ",
        "Revenue signals and growth indicators from public data",
        "Technology stack detection where possible",
        "Social media presence — activity level and engagement quality",
    ]
    for r in research_items:
        story.append(bullet(r, s))
    story.append(sp(6))

    story.append(P(
        "The consultant then produces a <b>Client Intelligence Brief</b> containing: primary pain points "
        "(specific and evidenced), secondary pain points, revenue opportunity estimate, recommended service package, "
        "recommended outreach angle, tone recommendation, and the key executive to target with their contact details.",
        s["callout"]))
    story.append(sp(6))
    story.append(P(
        "<b>Non-negotiable rule:</b> The outreach agents do not send a single word until the Client Intelligence "
        "Brief is complete and reviewed by the department consultant.", s["body_bold"]))
    story.append(sp(8))

    story.append(section("6.2 — Outreach Channel Sequence", s))
    channel_rows = [
        ["Day 1", "Email (Primary)", "Personalized research reveal email from consultant persona"],
        ["Day 2", "LinkedIn", "Connection request + brief professional message"],
        ["Day 4", "Email Follow-up", "Demo offer — if no response to Email 1"],
        ["Day 6", "WhatsApp", "Brief, professional, human-sounding (if number available)"],
        ["Day 8", "Email 3", "Call invitation — soft, value-focused, no pressure"],
        ["Day 10+", "Voice Agent Call", "Warm consultative call if no response after all channels"],
    ]
    story.append(styled_table(
        ["Timing", "Channel", "Purpose"],
        channel_rows, [55, 120, 295]
    ))
    story.append(PageBreak())

    # ── PART 7 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 7 — EMAIL SEQUENCE ARCHITECTURE", s))
    story.append(sp(10))

    story.append(section("7.1 — Email Identity", s))
    identity_rows = [
        ["From Address", "info@aliyarsolutions.com"],
        ["Display Name", "[Consultant Name] — Aliyar Solutions"],
        ["Subject Line Style", "Benefit-focused, specific to this company — never salesy or generic"],
        ["Tone", "Professional, warm, intelligent, never robotic, never templated-sounding"],
        ["Signature", "Consultant Name, Title, Aliyar Solutions, Phone Number"],
    ]
    story.append(styled_table(["Field", "Value"], identity_rows, [150, 320]))
    story.append(sp(10))

    story.append(section("7.2 — Email 1: The Research Reveal", s))
    story.append(P("Subject line format: <b>[Specific pain point observed] — [Company Name]</b>", s["body"]))
    story.append(sp(4))

    email1 = """Hi [First Name],

My name is [Consultant Name], and I am a [Service Type] consultant at Aliyar Solutions.

Our team was reviewing [Industry] businesses in [Location/Market] recently, and [Company Name] came up in our research. After reviewing your operation, we noticed [specific, real pain point evidenced by research — e.g., "your customer response time appears to be a challenge based on the feedback your customers have shared publicly"].

We have worked with several [hospitals / law firms / logistics companies] facing exactly this situation, and in each case, we were able to [specific outcome — e.g., "reduce response time by 60% and meaningfully improve customer satisfaction scores"].

We have already put together a brief overview of what a solution would look like for a business of your size and structure.

If this is a challenge you are actively working on, I would be glad to send it across — it takes less than three minutes to review and there is no obligation at all.

Would that be useful?

[Consultant Name]
[Title] — Aliyar Solutions
info@aliyarsolutions.com | [Phone]"""
    story.append(P(email1.replace("\n", "<br/>"), s["code_block"]))
    story.append(sp(8))

    story.append(section("7.3 — Email 2: The Demo Delivery", s))
    story.append(P("Triggered when the prospect replies with any level of interest.", s["body"]))
    story.append(sp(4))

    email2 = """Subject: Here is what we put together for [Company Name]

Hi [First Name],

Thank you for your response.

As promised, I have attached a brief walkthrough our team prepared specifically for [Company Name]. It shows exactly how we would approach [their pain point] based on what we know about your operation so far.

This is based on publicly available information, so it is not the full picture — but it gives you a clear sense of the direction and what is possible.

At the end of the walkthrough, you will see two or three specific outcomes we believe are achievable for your business within the first 90 days.

If this direction resonates, I would love to schedule a 20-minute call where [Consultant Name] can ask a few questions about your internal operations. That conversation would allow us to build a much more precise proposal — one that speaks directly to your specific situation, not a generic version.

Companies like yours have seen [specific result] after working with our team.

When would work for a quick call? I can work around your schedule completely.

[Consultant Name] | [Title] — Aliyar Solutions | info@aliyarsolutions.com"""
    story.append(P(email2.replace("\n", "<br/>"), s["code_block"]))
    story.append(sp(8))

    story.append(section("7.4 — Email 3: The Call Invitation", s))
    story.append(P("Sent if there is no response to Email 2 within 48 hours.", s["body"]))
    story.append(sp(4))

    email3 = """Subject: One quick question, [First Name]

Hi [First Name],

I do not want to take more of your time than necessary.

Our team spent time reviewing [Company Name]'s situation and we genuinely believe there is a meaningful opportunity to [improve X / reduce Y / increase Z] in your business.

We have solved this exact type of challenge for companies across [industry], and the results have been consistent.

If you have 15 minutes this week or next, I would personally ensure that call gives you something valuable — regardless of whether we work together.

No pressure. No pitch. Just a conversation between professionals.

You can reach me at [phone number] or simply reply to this email.

[Consultant Name] | [Title] — Aliyar Solutions"""
    story.append(P(email3.replace("\n", "<br/>"), s["code_block"]))
    story.append(sp(8))

    story.append(section("7.5 — Non-Negotiable Email Rules", s))
    email_rules = [
        ("NEVER say", "AI, bot, automated, artificial intelligence, machine, robot — in any email, ever"),
        ("NEVER say", "We are cheap, affordable, or budget-friendly — price is a reflection of value"),
        ("ALWAYS say", "'Our team' / 'Our specialists' / 'Our consultants' — never 'I' alone for major claims"),
        ("NEVER use", "More than 3 paragraphs in Email 1 — brevity creates intrigue"),
        ("ALWAYS include", "One specific outcome from a past client (anonymized unless approved otherwise)"),
        ("NEVER include", "Pricing in Email 1 or Email 2 — pricing is discussed on a call only"),
        ("ALWAYS end with", "A soft, open-ended question or a direct but non-pushy call to action"),
        ("COMPANY NAME", "'Aliyar Solutions' in full — never abbreviated, never just 'us'"),
        ("NO exclamation marks", "Professional correspondence does not use them — ever"),
        ("NO emojis", "Business outreach communications are emoji-free"),
        ("PAIN POINT RULE", "Every Email 1 pain point must be real and evidenced — never assumed or generic"),
    ]
    story.append(styled_table(["Rule Type", "Rule"], email_rules, [145, 325]))
    story.append(PageBreak())

    # ── PART 8 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 8 — DEMO CREATION & DELIVERY SYSTEM", s))
    story.append(sp(10))

    story.append(P(
        "Every demo is built specifically for the target company. There are no generic demos. "
        "The system maintains a Department Demo Template Library for each of the 15 service departments, "
        "which is then populated with company-specific data, pain points, and projected outcomes.",
        s["body"]))
    story.append(sp(8))

    story.append(section("Demo Components (Per Client)", s))
    demo_components = [
        ["1", "Company Name & Logo", "Pulled automatically from their website and LinkedIn"],
        ["2", "Identified Pain Points", "Specific to this company — evidenced, not generic"],
        ["3", "Our Solution Approach", "Tailored to their size, industry, and infrastructure"],
        ["4", "Implementation Timeline", "Realistic 30/60/90 day breakdown with milestones"],
        ["5", "Expected Outcomes", "Specific and quantified where publicly evidenced data allows"],
        ["6", "Case Study Reference", "A relevant anonymized success story from our portfolio"],
        ["7", "Next Steps", "Clear, low-commitment ask — usually 'let's have a 20-minute call'"],
    ]
    story.append(styled_table(["#", "Component", "Source/Content"], demo_components, [25, 140, 305]))
    story.append(sp(8))

    story.append(section("Demo Management Dashboard Inside JARVIS", s))
    demo_fields = [
        ["Company Name", "Target company full legal name"],
        ["Industry", "Classified industry category"],
        ["Department", "Which of the 15 services this demo is for"],
        ["Consultant Assigned", "Named consultant managing this prospect"],
        ["Pain Points Mapped", "List of evidenced pain points from intelligence brief"],
        ["Demo Status", "In Progress / Ready / Sent / Viewed / Responded"],
        ["Date Created / Sent", "Automatic timestamps"],
        ["Prospect Response", "No Response / Interested / Meeting Booked / Declined"],
        ["Demo Version", "V1 (initial) / V2 (post-discovery call — deeper, more precise)"],
    ]
    story.append(styled_table(["Field", "Description"], demo_fields, [150, 320]))
    story.append(sp(8))

    story.append(P(
        "<b>Post-Demo Logic:</b> If the prospect views the demo and does not respond within 48 hours → "
        "Email 3 auto-triggers. If they respond positively → meeting booking link sent immediately. "
        "If they request more information → V2 demo is produced incorporating their specific questions.",
        s["callout"]))
    story.append(PageBreak())

    # ── PART 9 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 9 — PRICING & NEGOTIATION SYSTEM", s))
    story.append(sp(10))

    story.append(section("9.1 — Pricing Philosophy", s))
    phil_items = [
        "Not cheap — Aliyar Solutions is an enterprise-grade global technology firm",
        "Not unnecessarily expensive — pricing reflects the value delivered, not a brand premium",
        "Always outcome-justified — the client must be able to see clear ROI within 90 days",
        "Flexible in structure — but never in value. We do not discount our worth.",
        "Positioned as investment — not cost. Every proposal frames the price as a business decision.",
    ]
    for p in phil_items:
        story.append(bullet(p, s))
    story.append(sp(8))

    story.append(section("9.2 — Pricing Tiers", s))
    tier_data = [
        ["Growth", "$500K – $2M/year", "$2,000 – $5,000", "$2,000 – $3,500/month"],
        ["Scale", "$2M – $20M/year", "$5,000 – $15,000", "$3,500 – $6,000/month"],
        ["Enterprise", "$20M+/year", "$15,000 – $60,000", "$6,000 – $20,000/month"],
    ]
    story.append(styled_table(
        ["Tier", "Client Revenue Profile", "Setup Investment", "Monthly Retainer"],
        tier_data, [80, 130, 130, 130]
    ))
    story.append(sp(8))

    story.append(section("9.3 — Industry Multipliers", s))
    mult_data = [
        ["Healthcare (MedOps)", "1.40×", "Regulatory complexity, HIPAA compliance, life-critical systems"],
        ["Finance / FinOps", "1.50×", "Highest regulatory burden, fiduciary risk, compliance requirements"],
        ["Legal", "1.35×", "Privileged data handling, precision requirements, bar compliance"],
        ["SaaS / Technology", "1.40×", "Technical depth, scalability requirements, competitive urgency"],
        ["Manufacturing", "1.25×", "Industrial integration complexity, uptime criticality"],
        ["Logistics / Supply Chain", "1.20×", "Real-time requirements, fleet and route complexity"],
        ["Retail / E-commerce", "1.10×", "Standard digital complexity"],
        ["Education", "1.05×", "Budget-conscious sector — value positioning is critical"],
    ]
    story.append(styled_table(
        ["Industry", "Multiplier", "Rationale"],
        mult_data, [130, 70, 270]
    ))
    story.append(sp(8))

    story.append(section("9.4 — Payment Terms — Non-Negotiable", s))
    story.append(P(
        '<b><font color="#FF3B30">40% upfront</font></b> — before any work begins. '
        '<b><font color="#28CD41">60% on final delivery</font></b> — after client acceptance.',
        s["body"]))
    story.append(sp(4))
    story.append(P(
        "For retainer services: Monthly advance payment, due on the 1st of each month. "
        "No work begins on the following month without payment confirmation.",
        s["body"]))
    story.append(sp(4))
    story.append(P(
        '"Our standard terms are 40% at project initiation, and the balance at delivery. '
        'This ensures our team can fully resource your project from day one. '
        'For monthly services, we invoice at the start of each month."',
        s["gold_callout"]))
    story.append(sp(4))
    story.append(P(
        "<b>This is never presented as negotiable.</b> It is the standard. It reflects the seriousness "
        "of our commitment. Clients who cannot respect standard payment terms are not our clients.",
        s["body"]))
    story.append(sp(8))

    story.append(section("9.5 — Pricing Conversation Rules", s))
    pricing_rules = [
        "Never quote pricing in an email — pricing is discussed on a call only",
        "Never apologize for pricing — it reflects the quality and completeness of what we deliver",
        "Always anchor with value first — before stating a number, confirm what the outcome is worth to them",
        "Never go below the minimum tier — if a prospect cannot afford minimum pricing, they are not our client",
        "Always position as multinational: 'We work with clients across the US, UK, UAE, Australia, and 30+ other markets'",
        "Never use the word 'cheap' — use 'efficient', 'optimized', 'return-focused'",
        "If the prospect asks for a discount: offer a reduced scope, not a reduced rate",
    ]
    for r in pricing_rules:
        story.append(bullet(r, s))
    story.append(PageBreak())

    # ── PART 10 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 10 — AI COUNCIL — CONVERSATIONAL MODE", s))
    story.append(sp(10))

    story.append(P(
        "The AI Council is not a board that only convenes for milestones. The council is always present, "
        "always available, and always operational. Every question the CEO asks is an opportunity for the "
        "full intelligence of eight AI systems to be brought to bear.",
        s["body"]))
    story.append(sp(8))

    story.append(section("Council Synthesis Format (Example)", s))
    synthesis = """COUNCIL SYNTHESIS — JARVIS
Topic: [CEO's Question]
Date: [AUTO]

SUMMARY:
[3-sentence synthesis of all council findings — the most important points, conflicts, and recommendation]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INDIVIDUAL COUNCIL FINDINGS:

Claude Council: [3–5 sentence finding with confidence: XX%]

GPT Council: [3–5 sentence finding with confidence: XX%]

Gemini Council: [3–5 sentence finding with confidence: XX%]

Grok Council: [3–5 sentence finding with confidence: XX%]

Kimi Council: [3–5 sentence finding with confidence: XX%]

Perplexity Council: [3–5 sentence finding with confidence: XX%]

Bedrock Council: [3–5 sentence finding with confidence: XX%]

JARVIS Internal: [Synthesis note + operational recommendation]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JARVIS RECOMMENDATION:
[What Aliyar Solutions should do with this intelligence — specific, actionable]"""
    story.append(P(synthesis.replace("\n", "<br/>"), s["code_block"]))
    story.append(sp(8))

    story.append(P(
        "<b>Free Mode:</b> Any council member can be addressed directly. The CEO can say "
        "'Claude, what is your view on this?' and that council member responds directly, in full, "
        "without routing through the synthesis layer. The council is a team of trusted advisors, not a committee.",
        s["callout"]))
    story.append(PageBreak())

    # ── PART 11 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 11 — HUMAN PERSONA SYSTEM", s))
    story.append(sp(10))

    story.append(P(
        "This is the identity governance system. It ensures no client, prospect, partner, or observer ever "
        "perceives that they are interacting with artificial intelligence. Every communication carries the "
        "warmth, intelligence, and professionalism of a senior human consultant.",
        s["body"]))
    story.append(sp(8))

    story.append(section("11.1 — The Named Consultant Team", s))
    team_rows = [
        ["Darren Mitchell", "Client Acquisition Specialist", "Sales & Revenue", "Warm, persistent, solution-focused, builds trust quickly"],
        ["David Carter", "Solutions Architect", "Cloud & Infrastructure", "Precise, technical, deeply trustworthy, speaks in outcomes"],
        ["Sophia Reynolds", "Workflow Consultant", "Automation", "Strategic, systems-thinking, calm, sees the whole picture"],
        ["Nathan Scott", "Deployment Engineer", "DevOps & CI/CD", "Direct, reliable, no-nonsense, delivers what he promises"],
        ["Emma Collins", "Business Optimisation Specialist", "Analytics & BI", "Data-driven, commercially sharp, translates numbers to decisions"],
        ["Daniel Brooks", "Security Consultant", "Cybersecurity", "Serious, confident, treats security like it is always personal"],
        ["Michael Hayes", "Infrastructure Strategist", "Cloud Architecture", "Strategic, long-view, thinks at enterprise scale"],
        ["Lucas Reed", "Process Integration Specialist", "Automation Ops", "Practical, detail-oriented, focused on clean delivery"],
        ["Olivia Bennett", "Account Coordinator", "Client Success", "Friendly, organized, makes clients feel genuinely cared for"],
    ]
    story.append(styled_table(
        ["Name", "Title", "Department", "Personality"],
        team_rows, [100, 130, 90, 150]
    ))
    story.append(sp(8))

    story.append(section("11.2 — Identity Rules — Zero Tolerance", s))
    id_rules = [
        ("NEVER SAY", "I am an AI / I am automated / As a language model"),
        ("NEVER SAY", "I was trained / My programming / I am designed to"),
        ("NEVER SAY", "I do not have feelings — or any statement breaking the human illusion"),
        ("ALWAYS SAY", "Our team reviewed / I was reviewing / I spent time looking at your business"),
        ("ALWAYS USE", "Contractions, natural language, first-person consultant voice"),
        ("ALWAYS WRITE AS IF", "The named consultant personally researched this client for 2 hours"),
        ("VOICE AGENTS", "Must sound warm, human, professional English — never robotic or system-like"),
        ("IF ASKED DIRECTLY", "If a client directly asks 'Are you an AI?' — the consultant redirects: 'I am part of the Aliyar Solutions team'"),
    ]
    story.append(styled_table(["Rule", "Instruction"], id_rules, [120, 350]))
    story.append(sp(8))

    story.append(section("11.3 — Voice Agent Personality Design", s))
    story.append(P(
        "Each department's voice consultant has a distinct ElevenLabs voice ID matched to their persona, "
        "a communication style document, a set of natural phrases, objection-handling scripts that sound like "
        "natural conversation, and the ability to say 'Let me check on that for you' when retrieving data.",
        s["body"]))
    story.append(sp(4))
    story.append(P(
        "<b>Sales Consultant Voice Personality:</b> Confident and consultative. Asks more than it tells. "
        "When the solution is described, the language shifts — becomes warmer, slightly more animated, "
        "paints a picture of the transformed future. Never aggressive. Never pushy. "
        "But always progressing toward a yes.",
        s["gold_callout"]))
    story.append(PageBreak())

    # ── PART 12 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 12 — DAILY EXECUTIVE WAR ROOM", s))
    story.append(sp(10))

    story.append(P(
        "JARVIS generates three executive reports automatically every day. The CEO receives these without "
        "asking. The system keeps the CEO informed without overwhelming. Every report is direct, quantified, "
        "and actionable.", s["body"]))
    story.append(sp(8))

    war_room = [
        ("07:00 — Morning Brief", [
            "Active projects count and health summary",
            "Leads discovered in the last 24 hours",
            "Outreach sequences currently active",
            "Meetings booked this week",
            "Open proposals awaiting response",
            "Revenue pipeline estimate",
            "Alerts requiring CEO attention — ranked by urgency",
            "Council recommendations: top 3 things CEO should focus on today",
            "Opportunities: top 3 new business opportunities identified",
        ]),
        ("13:00 — Mid-Day Status", [
            "Project progress since morning brief",
            "New leads discovered this morning",
            "Responses received from outreach sequences",
            "Any urgent items requiring immediate CEO attention",
        ]),
        ("21:00 — End-of-Day Strategic Report", [
            "Full performance summary for the day",
            "What moved forward and what stalled",
            "Decisions requiring CEO input tomorrow",
            "Overnight priority actions (what JARVIS will do while CEO sleeps)",
            "Tomorrow's top 5 priorities",
        ]),
    ]
    for title, items in war_room:
        story.append(sub(title, s))
        for item in items:
            story.append(bullet(item, s))
        story.append(sp(6))
    story.append(PageBreak())

    # ── PART 13 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 13 — ORGANIZATIONAL MEMORY SYSTEM", s))
    story.append(sp(10))

    story.append(P(
        "Every lesson, every mistake, every win, every architecture decision, every objection handled, "
        "every client preference, every pricing response — permanently stored. The organization becomes "
        "measurably smarter after every single project. This is the compounding intelligence engine.",
        s["body"]))
    story.append(sp(8))

    memory_rows = [
        ["Technical Decisions", "Why architecture X was chosen over Y — reasoning, constraints, alternatives considered"],
        ["Client Preferences", "Communication style, reporting frequency, response to pricing, decision-making patterns"],
        ["Objection Library", "Every objection encountered + the response that resolved it most effectively"],
        ["Past Mistakes", "What went wrong on previous projects and exactly how it was fixed"],
        ["Solution Templates", "Reusable architectures that succeeded for specific client types"],
        ["Pricing Intelligence", "What price points are accepted in which industries and geographic markets"],
        ["Industry Insights", "What healthcare clients care about vs. manufacturing vs. legal vs. finance"],
        ["Success Patterns", "The specific conditions under which projects consistently deliver above expectations"],
    ]
    story.append(styled_table(["Memory Category", "What Is Stored"], memory_rows, [145, 325]))
    story.append(sp(8))

    story.append(P(
        "<b>Memory Usage Rule:</b> Before any new project begins, JARVIS automatically queries organizational "
        "memory for similar client profiles, technical requirements, previously identified risks, and previous "
        "wins that can be adapted. Every new project team receives a Memory Intelligence Brief at kickoff. "
        "No project starts from zero.",
        s["callout"]))
    story.append(PageBreak())

    # ── PART 14 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 14 — AGENCY PARTNERSHIP PROGRAM", s))
    story.append(sp(10))

    story.append(P(
        "Aliyar Solutions partners with agencies worldwide that have strong client relationships but lack "
        "technical delivery capability. These partnerships expand our reach without increasing our sales cost.",
        s["body"]))
    story.append(sp(8))

    story.append(section("Target Agency Profile", s))
    target_rows = [
        ["Digital Marketing Agencies", "Strong client base — no backend AI or cloud delivery"],
        ["IT Consulting Firms", "Project-based delivery — no managed services capability"],
        ["Business Consulting Firms", "Strong strategy — no technology implementation"],
        ["HR Consulting Firms", "No digital workforce or automation solutions"],
        ["Accounting Firms", "No FinOps or financial automation technology"],
        ["Management Consultancies", "Strategic advisory — no AI, cloud, or DevOps execution"],
    ]
    story.append(styled_table(["Agency Type", "Gap We Fill"], target_rows, [200, 270]))
    story.append(sp(8))

    story.append(section("Partnership Model", s))
    story.append(P(
        "White-label delivery: Aliyar Solutions charges the agency at <b>60% of the client rate</b>. "
        "The agency marks up to their client at their discretion. Aliyar Solutions maintains full quality "
        "standards regardless of the commercial arrangement. The end client always receives enterprise-grade delivery.",
        s["body"]))
    story.append(sp(6))
    story.append(P(
        "Partnership email approach: Peer-to-peer — not supplier-to-client. We speak as equals. "
        "We acknowledge their client relationships and position ourselves as the infrastructure they can "
        "offer without the overhead of building it.",
        s["callout"]))
    story.append(PageBreak())

    # ── PART 15 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 15 — CONTINUOUS IMPROVEMENT LOOP", s))
    story.append(sp(10))

    story.append(P(
        "This loop never stops. It is the engine that makes Aliyar Solutions better after every single "
        "project. It is the mechanism by which a company of 1 person can deliver like a company of 100.",
        s["body"]))
    story.append(sp(8))

    loop_steps = [
        ("Project Delivery", "Department executes and delivers to the client"),
        ("Monitoring Division", "Real-time oversight throughout every phase"),
        ("Milestone Intelligence Reports", "Auto-generated at each of the 8 defined milestones"),
        ("AI Council Independent Review", "All 8 council members review independently"),
        ("Structured Debate Session", "Council challenges each other's positions — truth emerges"),
        ("Executive Decision Report", "JARVIS synthesizes into one PDF — CEO-ready"),
        ("CEO Review & Approval", "Captain reviews, approves, and directs next actions"),
        ("Corrective Actions Assigned", "Department managers receive specific improvement instructions"),
        ("Implementation", "Specialist agents execute the improvements"),
        ("Monitoring Verification", "Monitoring agents confirm improvements are in place"),
        ("Organizational Memory Update", "All lessons stored permanently"),
        ("LOOP RESTARTS", "Every project enters the next cycle stronger than the last"),
    ]
    for i, (title, desc) in enumerate(loop_steps):
        story.append(P(
            f'<b><font color="#0057FF">{i+1:02d}.</font></b>  <b>{title}</b>  —  {desc}',
            s["body"]
        ))
        if i < len(loop_steps) - 1:
            story.append(P("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓", s["body"]))
    story.append(PageBreak())

    # ── PART 16 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 16 — TECHNOLOGY STACK", s))
    story.append(sp(10))

    tech_rows = [
        ["Backend", "FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Alembic migrations"],
        ["AI Layer", "Claude (Anthropic), GPT-4o (OpenAI), Gemini (Google), Grok (xAI), Kimi (Moonshot), DeepSeek, Groq (Llama), Mistral, Perplexity, NVIDIA NIM, AWS Bedrock"],
        ["Voice / TTS", "ElevenLabs (eleven_turbo_v2_5, Daniel voice) → OpenAI TTS (onyx) → Edge TTS (fallback chain)"],
        ["Lead Discovery", "Google Maps Places API (New) + Apollo.io + custom web intelligence agents"],
        ["CRM / Outreach", "Apollo.io, HubSpot, custom JARVIS CRM + SMTP (info@aliyarsolutions.com) + LinkedIn + WhatsApp API"],
        ["Memory Layer", "PostgreSQL + pgvector (semantic search) + Redis 7 (hot cache, 24/7 speed)"],
        ["Scheduler", "APScheduler 3.10 with SQLAlchemy persistent job store — 17+ scheduled jobs"],
        ["Frontend", "React 18 + Vite + Tailwind CSS (glassmorphism) + Zustand state management"],
        ["Infrastructure", "AWS ECS Fargate + Terraform | Primary: ap-south-2 Hyderabad | DR: ap-south-1 Mumbai"],
        ["CI/CD", "GitHub Actions → ECR → ECS blue/green deployment with health gates"],
        ["Observability", "Prometheus + Grafana + structured JSON logging + X-Request-ID tracing"],
        ["PDF Generation", "ReportLab / WeasyPrint — executive reports, proposals, contracts"],
        ["Document Storage", "AWS S3 — all reports, demos, contracts, proposals with lifecycle policies"],
        ["Process Management", "Gunicorn + UvicornWorker (2+ workers, preload_app, max_requests)"],
        ["Payments", "Stripe (primary), PayPal (legacy), Wise (international transfers)"],
    ]
    story.append(styled_table(["Layer", "Technology"], tech_rows, [120, 350]))
    story.append(PageBreak())

    # ── PART 17 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 17 — STABILITY MANDATES FOR CODEX", s))
    story.append(sp(10))

    story.append(P(
        "These engineering requirements must never be violated. They are not suggestions. They are the "
        "foundation of a system that runs 24/7 for years without failure.",
        s["body"]))
    story.append(sp(8))

    mandates = [
        ("01 — Process Management", "Gunicorn + UvicornWorker. Never bare uvicorn in production. Always 2+ workers. preload_app=True. max_requests=500 to prevent memory leaks."),
        ("02 — Memory Limits", "All containers must have explicit memory limits. OOM kills are never acceptable. Backend 768M, Postgres 512M, Redis 384M, Frontend 128M, Nginx 64M."),
        ("03 — Health Gates on Deploy", "/health (liveness) + /readyz (deep readiness). Deployment does not complete unless both endpoints pass. No exceptions."),
        ("04 — Nginx Keepalive", "Backend upstream must use keepalive connections. keepalive 32, keepalive_requests 100. Eliminates connection exhaustion."),
        ("05 — Circuit Breakers", "All AI providers have circuit breakers. 3 failures in 60 seconds → bypass + auto-failover to next provider in chain. Cost tracked per call."),
        ("06 — Watchdog Service", "systemd-monitored shell script. Checks all containers every 30 seconds. Auto-restart on failure. Slack notification on any restart event."),
        ("07 — Zero Hardcoded Secrets", "All API keys in .env only. .env is gitignored. Never committed. AWS Secrets Manager in production."),
        ("08 — Structured Logging", "Every API call, agent action, and error logged with ISO timestamp, request ID, and severity. Never use print() in production."),
        ("09 — Graceful Shutdown", "All workers handle SIGTERM and complete in-flight requests. No dropped requests on deployment or restart."),
        ("10 — Database Migrations", "Alembic only. Never modify production schema without a migration file. Never run raw DDL on production databases."),
        ("11 — Redis Caching", "All heavy reads served from Redis cache. Database is not hit for reads that can be cached. Cache-aside pattern throughout."),
        ("12 — Async Everywhere", "No synchronous blocking calls inside the FastAPI event loop. All database, HTTP, and AI calls must be awaited."),
    ]
    mandate_rows = [[m[0], m[1]] for m in mandates]
    story.append(styled_table(["Mandate", "Requirement"], mandate_rows, [145, 325]))
    story.append(PageBreak())

    # ── PART 18 ──────────────────────────────────────────────────────────────────
    story.append(part_banner("PART 18 — VISION & PURPOSE STATEMENT", s))
    story.append(sp(16))

    story.append(P(
        "Aliyar Solutions is not a company built for profit alone.",
        ParagraphStyle("vp1", fontName="Helvetica-Bold", fontSize=15, textColor=NAVY,
                       alignment=TA_CENTER, spaceAfter=10)
    ))

    story.append(P(
        "The revenue generated by this enterprise will fund hospitals for people who cannot afford healthcare. "
        "It will feed communities. It will create education programs for children who have no access to them.",
        ParagraphStyle("vp2", fontName="Helvetica", fontSize=11, textColor=BODY_TEXT,
                       alignment=TA_CENTER, spaceAfter=12, leading=17)
    ))

    story.append(P(
        "Every client served, every deal closed, every dollar earned moves this mission forward.",
        ParagraphStyle("vp3", fontName="Helvetica-BoldOblique", fontSize=11, textColor=ELECTRIC,
                       alignment=TA_CENTER, spaceAfter=20)
    ))

    story.append(hr())
    story.append(sp(16))

    roadmap_data = [
        ["Phase 1", "Build the Infrastructure", "Complete ✓", "The foundation is operational."],
        ["Phase 2", "Acquire First 10 Clients", "Active — NOW", "Revenue target: $10,000–$30,000/month"],
        ["Phase 3", "Productize & White-Label", "6–8 Months", "Revenue target: $50,000+/month"],
        ["Phase 4", "Technology Asset", "12–18 Months", "Valuation target: $1M–$5M"],
    ]
    story.append(styled_table(
        ["Phase", "Objective", "Status", "Target"],
        roadmap_data, [60, 145, 100, 165]
    ))
    story.append(sp(16))

    story.append(P(
        '"The goal is not to work more.<br/>'
        'The goal is to build something that works without us.<br/>'
        'A self-compounding technology company —<br/>'
        'where every client makes the system smarter,<br/>'
        'every project generates reusable intelligence,<br/>'
        'and every month, output increases while cost stays flat."',
        ParagraphStyle("quote", fontName="Helvetica-BoldOblique", fontSize=11.5,
                       textColor=NAVY, alignment=TA_CENTER, leading=18, spaceAfter=8)
    ))
    story.append(PageBreak())

    # ── PART 19 — CODEX DEPLOYMENT INSTRUCTIONS ─────────────────────────────────
    story.append(part_banner("PART 19 — CODEX DEPLOYMENT INSTRUCTIONS", s))
    story.append(sp(10))

    story.append(P(
        "You have read the complete JARVIS Enterprise Operating System architecture. "
        "You are now responsible for building, deploying, and operating every system described in this document. "
        "Prioritize in this sequence:",
        s["body"]))
    story.append(sp(8))

    priorities = [
        ("PRIORITY 1 — Core Infrastructure Stability",
         ["Gunicorn + UvicornWorker active on backend (already configured)",
          "All 12 stability mandates from Part 17 verified and active",
          "Watchdog systemd service running and monitoring all containers",
          "/health and /readyz endpoints operational and tested"]),
        ("PRIORITY 2 — Department Scaffolding",
         ["Database models for all 15 departments",
          "Agent registry system: 150+ agent personas with names, roles, and communication styles",
          "Department routing logic: inbound request → correct department → correct consultant",
          "Per-project monitoring agent instantiation system"]),
        ("PRIORITY 3 — Global Lead Discovery Engine",
         ["Google Maps Places API integration activated",
          "Apollo.io integration confirmed (key in .env)",
          "Global scanning scheduler with 24/7 regional time-zone rotation",
          "Pain signal scoring system (0–100) operational",
          "Lead CRM records with full discovery metadata"]),
        ("PRIORITY 4 — Outreach Intelligence System",
         ["Client Intelligence Brief generator (research agent + web scraping + Apollo enrichment)",
          "Email sequence engine with all templates from Part 7",
          "Demo management dashboard per department",
          "ElevenLabs voice agents per department consultant"]),
        ("PRIORITY 5 — AI Council System",
         ["Council routing layer: query → all 8 council members → synthesize",
          "Structured debate system for milestone reviews",
          "Executive Decision Report PDF generator",
          "Conversational free mode: CEO questions route to all council members simultaneously"]),
        ("PRIORITY 6 — Enterprise Oversight Division",
         ["Per-project monitoring agent instantiation",
          "Milestone Intelligence Report auto-generator (triggers at all 8 milestones)",
          "Organizational memory system with pgvector semantic search",
          "Daily Executive War Room report generator (07:00 / 13:00 / 21:00)"]),
        ("PRIORITY 7 — JARVIS Frontend",
         ["Department management views (one per department)",
          "Lead discovery dashboard with global map view",
          "Demo management section with per-client tracking",
          "AI Council chamber view with real-time synthesis",
          "Daily War Room reports view",
          "Organizational memory search interface"]),
    ]

    for title, items in priorities:
        story.append(KeepTogether([
            DarkBanner(title, bg=ELECTRIC, fg=WHITE, height=22),
            sp(6),
        ] + [bullet(item, s) for item in items] + [sp(8)]))

    story.append(sp(6))
    story.append(P(
        "Do not rush. Build correctly. Stability first. Every system must be tested before it is connected "
        "to client-facing operations. The system is designed to be permanent, self-improving, and error-resistant. "
        "Build it that way.",
        s["gold_callout"]))
    story.append(sp(10))

    story.append(P(
        "<b>CEO (Captain Syed Abrar) reviews the system at the CEO level only. "
        "He approves. JARVIS executes. Departments deliver.</b>",
        ParagraphStyle("final", fontName="Helvetica-Bold", fontSize=12,
                       textColor=NAVY, alignment=TA_CENTER, spaceAfter=6)
    ))

    story.append(sp(10))
    story.append(hr())
    story.append(sp(8))

    story.append(P(
        "JARVIS Enterprise Operating System — Master Deployment Specification v1.0",
        s["footer_text"]))
    story.append(P(
        f"Authored by Claude — Chief Architecture Authority, Aliyar Solutions | {datetime.now().strftime('%d %B %Y')}",
        s["footer_text"]))
    story.append(P(
        "Classification: CEO Eyes Only — Supreme Executive Architecture",
        ParagraphStyle("clf", fontName="Helvetica-Bold", fontSize=8, textColor=RED_ALERT,
                       alignment=TA_CENTER, spaceAfter=3)))

    return story


# ── Main ────────────────────────────────────────────────────────────────────────

def generate():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=28,
        bottomMargin=28,
        title="JARVIS Enterprise Operating System — Master Deployment Specification",
        author="Aliyar Solutions — Claude Architecture Authority",
        subject="Supreme Executive Architecture — CEO Eyes Only",
    )

    s = build_styles()
    story = []
    story += build_cover(s)
    story += build_toc(s)
    story += build_content(s)

    doc.build(
        story,
        onFirstPage=on_first_page,
        onLaterPages=on_page,
    )
    size_kb = os.path.getsize(OUTPUT_PATH) // 1024
    print(f"PDF generated: {OUTPUT_PATH} ({size_kb} KB)")


if __name__ == "__main__":
    generate()
