"""
JARVIS Architecture Blueprint PDF Generator
Aliyar Solutions — Professional Document
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import HexColor
import datetime

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY       = HexColor("#0A0F1E")
DARK_BG    = HexColor("#0D1226")
BLUE       = HexColor("#2563EB")
CYAN       = HexColor("#06B6D4")
PURPLE     = HexColor("#7C3AED")
GREEN      = HexColor("#10B981")
AMBER      = HexColor("#F59E0B")
RED        = HexColor("#EF4444")
WHITE      = HexColor("#FFFFFF")
LIGHT_GRAY = HexColor("#F1F5F9")
MID_GRAY   = HexColor("#94A3B8")
DARK_GRAY  = HexColor("#1E293B")
BORDER     = HexColor("#334155")
TEXT_DARK  = HexColor("#0F172A")
TEXT_MID   = HexColor("#334155")
TEXT_LIGHT = HexColor("#64748B")

W, H = A4  # 210 x 297 mm

# ── Custom flowables ──────────────────────────────────────────────────────────

class ColorBar(Flowable):
    """Horizontal accent bar."""
    def __init__(self, width, height=3, color=BLUE):
        super().__init__()
        self.bar_width = width
        self.bar_height = height
        self.color = color

    def wrap(self, *args):
        return self.bar_width, self.bar_height + 2

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.bar_width, self.bar_height, fill=1, stroke=0)


class SectionHeader(Flowable):
    """Numbered section header block."""
    def __init__(self, number, title, width, color=BLUE):
        super().__init__()
        self.number = number
        self.title = title
        self.w = width
        self.color = color
        self.height = 28

    def wrap(self, *args):
        return self.w, self.height + 6

    def draw(self):
        c = self.canv
        # Background pill
        c.setFillColor(HexColor("#EFF6FF"))
        c.roundRect(0, 2, self.w, self.height, 6, fill=1, stroke=0)
        # Left accent
        c.setFillColor(self.color)
        c.roundRect(0, 2, 5, self.height, 2, fill=1, stroke=0)
        # Number badge
        c.setFillColor(self.color)
        c.circle(22, 2 + self.height / 2, 10, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(22, 2 + self.height / 2 - 3, str(self.number))
        # Title
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, 2 + self.height / 2 - 4, self.title.upper())


class StatusBadge(Flowable):
    """Small inline badge."""
    def __init__(self, text, color=GREEN, text_color=WHITE):
        super().__init__()
        self.text = text
        self.color = color
        self.text_color = text_color
        self.pad = 8

    def wrap(self, *args):
        return len(self.text) * 6 + self.pad * 2, 16

    def draw(self):
        w = len(self.text) * 6 + self.pad * 2
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 1, w, 14, 7, fill=1, stroke=0)
        self.canv.setFillColor(self.text_color)
        self.canv.setFont("Helvetica-Bold", 8)
        self.canv.drawCentredString(w / 2, 4, self.text)


# ── Style definitions ─────────────────────────────────────────────────────────

def build_styles():
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontSize=34, leading=40, textColor=WHITE,
            fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontSize=14, leading=20, textColor=CYAN,
            fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontSize=10, leading=14, textColor=MID_GRAY,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "h1",
            fontSize=18, leading=24, textColor=TEXT_DARK,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontSize=13, leading=18, textColor=BLUE,
            fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontSize=11, leading=15, textColor=TEXT_DARK,
            fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=10, leading=15, textColor=TEXT_MID,
            fontName="Helvetica", spaceBefore=2, spaceAfter=4,
            alignment=TA_JUSTIFY,
        ),
        "body_white": ParagraphStyle(
            "body_white",
            fontSize=10, leading=15, textColor=WHITE,
            fontName="Helvetica", spaceBefore=2, spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontSize=10, leading=15, textColor=TEXT_MID,
            fontName="Helvetica", leftIndent=14, spaceBefore=1, spaceAfter=2,
            bulletIndent=4, bulletFontName="Helvetica", bulletFontSize=10,
        ),
        "bullet_bold": ParagraphStyle(
            "bullet_bold",
            fontSize=10, leading=15, textColor=TEXT_DARK,
            fontName="Helvetica-Bold", leftIndent=14, spaceBefore=1, spaceAfter=2,
        ),
        "code": ParagraphStyle(
            "code",
            fontSize=8.5, leading=13, textColor=CYAN,
            fontName="Courier", spaceBefore=2, spaceAfter=2,
            backColor=HexColor("#0F172A"), leftIndent=8, rightIndent=8,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontSize=8, leading=11, textColor=TEXT_LIGHT,
            fontName="Helvetica-Oblique", alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontSize=9, leading=12, textColor=WHITE,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontSize=9, leading=13, textColor=TEXT_MID,
            fontName="Helvetica",
        ),
        "table_cell_bold": ParagraphStyle(
            "table_cell_bold",
            fontSize=9, leading=13, textColor=TEXT_DARK,
            fontName="Helvetica-Bold",
        ),
        "label": ParagraphStyle(
            "label",
            fontSize=8, leading=10, textColor=MID_GRAY,
            fontName="Helvetica-Bold", spaceBefore=0, spaceAfter=1,
        ),
        "step_num": ParagraphStyle(
            "step_num",
            fontSize=22, leading=26, textColor=BLUE,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "toc": ParagraphStyle(
            "toc",
            fontSize=10, leading=18, textColor=TEXT_MID,
            fontName="Helvetica", leftIndent=0,
        ),
        "toc_section": ParagraphStyle(
            "toc_section",
            fontSize=11, leading=20, textColor=TEXT_DARK,
            fontName="Helvetica-Bold",
        ),
        "callout": ParagraphStyle(
            "callout",
            fontSize=10, leading=15, textColor=WHITE,
            fontName="Helvetica", leftIndent=10, rightIndent=10,
            spaceBefore=4, spaceAfter=4,
        ),
        "tag": ParagraphStyle(
            "tag",
            fontSize=8, leading=10, textColor=BLUE,
            fontName="Helvetica-Bold",
        ),
    }
    return styles


# ── Table helpers ─────────────────────────────────────────────────────────────

def make_table(data, col_widths, header_bg=DARK_GRAY, stripe=True):
    S = build_styles()

    # Wrap header cells
    header = [Paragraph(str(cell), S["table_header"]) for cell in data[0]]
    rows = [[Paragraph(str(cell), S["table_cell"]) for cell in row] for row in data[1:]]

    table_data = [header] + rows

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]

    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle(style))
    return t


def callout_box(text, bg=DARK_GRAY, border_color=BLUE, style_key="callout"):
    S = build_styles()
    content = [[Paragraph(text, S[style_key])]]
    t = Table(content, colWidths=[W - 60 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBEFORE", (0, 0), (0, -1), 4, border_color),
        ("ROUNDEDCORNERS", [0, 4, 4, 0]),
    ]))
    return t


def step_box(number, title, items, color=BLUE):
    S = build_styles()
    items_text = "<br/>".join(f"• {i}" for i in items)
    content = [
        [
            Paragraph(str(number), S["step_num"]),
            [Paragraph(title, S["h3"]), Paragraph(items_text, S["body"])],
        ]
    ]
    t = Table(content, colWidths=[18 * mm, W - 60 * mm - 18 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8FAFC")),
        ("BACKGROUND", (0, 0), (0, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, HexColor("#E2E8F0")),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


# ── Page callbacks ────────────────────────────────────────────────────────────

def cover_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Gradient-ish top strip
    canvas.setFillColor(HexColor("#111827"))
    canvas.rect(0, H - 80 * mm, W, 80 * mm, fill=1, stroke=0)
    # Diagonal accent lines
    canvas.setStrokeColor(HexColor("#1E3A5F"))
    canvas.setLineWidth(0.5)
    for x in range(-10, 220, 18):
        canvas.line(x * mm, 0, (x + 60) * mm, H)
    # Bottom strip
    canvas.setFillColor(BLUE)
    canvas.rect(0, 0, W, 8 * mm, fill=1, stroke=0)
    # Left accent bar
    canvas.setFillColor(CYAN)
    canvas.rect(0, 8 * mm, 4 * mm, H - 8 * mm, fill=1, stroke=0)
    canvas.restoreState()


def content_page(canvas, doc):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(DARK_GRAY)
    canvas.rect(0, H - 14 * mm, W, 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(BLUE)
    canvas.rect(0, H - 14 * mm, 3 * mm, 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(10 * mm, H - 8 * mm, "JARVIS — ALIYAR SOLUTIONS")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MID_GRAY)
    canvas.drawRightString(W - 10 * mm, H - 8 * mm, "PRODUCTION ARCHITECTURE BLUEPRINT v9.0")
    # Footer
    canvas.setFillColor(HexColor("#F1F5F9"))
    canvas.rect(0, 0, W, 10 * mm, fill=1, stroke=0)
    canvas.setFillColor(BLUE)
    canvas.rect(0, 0, 3 * mm, 10 * mm, fill=1, stroke=0)
    canvas.setFillColor(TEXT_LIGHT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(10 * mm, 4 * mm, "CONFIDENTIAL — Aliyar Solutions Internal Document")
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.setFillColor(TEXT_MID)
    canvas.drawRightString(W - 10 * mm, 4 * mm, f"Page {doc.page}")
    canvas.restoreState()


# ── Document builder ──────────────────────────────────────────────────────────

def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=25 * mm, rightMargin=25 * mm,
        topMargin=20 * mm, bottomMargin=16 * mm,
        title="JARVIS — Production Architecture Blueprint",
        author="Aliyar Solutions",
        subject="AI Operating System Architecture",
    )

    S = build_styles()
    story = []
    CONTENT_W = W - 50 * mm

    # ══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════

    story.append(Spacer(1, 28 * mm))
    story.append(Paragraph("JARVIS", S["cover_title"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("AI OPERATING SYSTEM", S["cover_sub"]))
    story.append(Spacer(1, 3 * mm))

    # Accent line
    sep_data = [[""]]
    sep = Table(sep_data, colWidths=[60 * mm])
    sep.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 2, CYAN),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(sep)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("PRODUCTION ARCHITECTURE BLUEPRINT", S["cover_sub"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Complete System Design · Step-by-Step Implementation Guide · Best Practices", S["cover_meta"]))

    story.append(Spacer(1, 16 * mm))

    # Key stats boxes
    stats = [
        ["10", "ARCHITECTURE\nLAYERS"],
        ["9", "BUILD\nPHASES"],
        ["85+", "API\nENDPOINTS"],
        ["11", "AI\nPROVIDERS"],
    ]
    stat_cells = []
    for val, lbl in stats:
        cell_content = [
            Paragraph(f'<font size="22" color="#2563EB"><b>{val}</b></font>', ParagraphStyle("_", alignment=TA_CENTER, leading=26)),
            Spacer(1, 1 * mm),
            Paragraph(f'<font size="7.5" color="#94A3B8">{lbl}</font>', ParagraphStyle("_", alignment=TA_CENTER, leading=10)),
        ]
        stat_cells.append(cell_content)

    stat_row = Table(
        [[stat_cells[0], stat_cells[1], stat_cells[2], stat_cells[3]]],
        colWidths=[35 * mm] * 4,
    )
    stat_row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#111827")),
        ("LINEAFTER", (0, 0), (2, -1), 0.5, HexColor("#1E3A5F")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))
    story.append(stat_row)
    story.append(Spacer(1, 10 * mm))

    story.append(Paragraph(
        "Aliyar Solutions · Hyderabad, India · Global AI Technology Operations",
        S["cover_meta"]
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"Version 9.0 · {datetime.date.today().strftime('%B %Y')} · CONFIDENTIAL",
        S["cover_meta"]
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ══════════════════════════════════════════════════════════════════════════

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("TABLE OF CONTENTS", S["h1"]))
    story.append(ColorBar(CONTENT_W, 3, BLUE))
    story.append(Spacer(1, 4 * mm))

    toc_items = [
        ("01", "Core Vision & Design Principles", "3"),
        ("02", "Architecture Overview — 10 Layers", "4"),
        ("03", "Layer 1 — Cloud Infrastructure (AWS)", "5"),
        ("04", "Layer 2 — Container Orchestration", "6"),
        ("05", "Layer 3 — Ingress, CDN & Security", "7"),
        ("06", "Layer 4 — Backend Orchestrator (FastAPI)", "8"),
        ("07", "Layer 5 — AI Intelligence System", "9"),
        ("08", "Layer 6 — Memory & Data Architecture", "10"),
        ("09", "Layer 7 — Frontend System", "11"),
        ("10", "Layer 8 — Agent & Automation System", "12"),
        ("11", "Layer 9 — Business Operations Integration", "13"),
        ("12", "Layer 10 — Observability Stack", "14"),
        ("13", "Deployment Topology Diagram", "15"),
        ("14", "Step-by-Step Implementation Guide", "16"),
        ("15", "Build Sequence & Priority Matrix", "22"),
        ("16", "Technology Selection Reference", "23"),
        ("17", "Security Architecture", "24"),
        ("18", "Scaling Roadmap", "25"),
        ("19", "Cost Optimisation Strategy", "26"),
    ]

    toc_data = []
    for num, title, page in toc_items:
        row = [
            Paragraph(f'<font color="#2563EB"><b>{num}</b></font>', S["toc"]),
            Paragraph(title, S["toc"]),
            Paragraph(f'<font color="#94A3B8">{page}</font>', S["toc"]),
        ]
        toc_data.append(row)

    toc_table = Table(toc_data, colWidths=[12 * mm, CONTENT_W - 24 * mm, 12 * mm])
    toc_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, HexColor("#F8FAFC")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
        ("LEFTPADDING", (1, 0), (1, -1), 8),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — CORE VISION
    # ══════════════════════════════════════════════════════════════════════════

    story.append(SectionHeader(1, "Core Vision & Design Principles", CONTENT_W, BLUE))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("What JARVIS Actually Is", S["h2"]))
    story.append(Paragraph(
        "JARVIS is not a chatbot. It is not an automation script. It is the central operational "
        "intelligence infrastructure of Aliyar Solutions — a full AI-native business operating system "
        "that reasons, executes, remembers, coordinates agents, manages infrastructure, and "
        "runs client-facing operations 24/7 on AWS without human intervention.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    # Vision cards
    vision_items = [
        ("Cloud Orchestration", "Provisions and manages AWS infrastructure autonomously via Terraform and ECS"),
        ("AI Reasoning", "11-provider router with circuit breakers, cost tracking, and task-type specialisation"),
        ("Business Automation", "Outreach, CRM, proposals, invoicing, scheduling — all automated"),
        ("Human Identity Layer", "9 named team members sign all client communications — professional and trusted"),
        ("Self-Healing", "Circuit breakers, auto-restart, readiness probes, and incident management built in"),
    ]
    for title, desc in vision_items:
        row = Table(
            [[Paragraph(f"✦  {title}", S["bullet_bold"]), Paragraph(desc, S["body"])]],
            colWidths=[42 * mm, CONTENT_W - 42 * mm],
        )
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#E2E8F0")),
        ]))
        story.append(row)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Governing Design Principles", S["h2"]))
    principles = [
        ("Operational Simplicity First",
         "Every component must justify its existence. No complexity without a concrete operational benefit. "
         "Simplicity is not a constraint — it is a quality standard."),
        ("Progressive Enhancement",
         "Build what works today. Add sophistication only when load or capability gaps demand it. "
         "A working system is always better than a perfectly designed unfinished one."),
        ("Infrastructure as Code Always",
         "If it is not in Terraform, it does not exist as far as the team is concerned. "
         "No manual console clicks in production. Ever."),
        ("Secrets Never in Code",
         "AWS Secrets Manager is the only credential store in production. "
         "Credentials are injected at runtime into ECS tasks. No .env files on servers."),
        ("Failure is Expected",
         "Every layer assumes its dependencies will fail and handles it gracefully. "
         "Circuit breakers, retries with backoff, health probes, and auto-recovery are built-in defaults."),
        ("Observability from Day One",
         "Logs, metrics, and health probes are not afterthoughts. They are first-class requirements "
         "from the first line of code. You cannot fix what you cannot see."),
    ]
    for i, (title, desc) in enumerate(principles):
        bg = HexColor("#EFF6FF") if i % 2 == 0 else WHITE
        row = Table(
            [[Paragraph(f"<b>{title}</b>", S["table_cell_bold"]), Paragraph(desc, S["table_cell"])]],
            colWidths=[48 * mm, CONTENT_W - 48 * mm],
        )
        row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#DBEAFE")),
        ]))
        story.append(row)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — ARCHITECTURE OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════

    story.append(SectionHeader(2, "Architecture Overview — 10 Layers", CONTENT_W, PURPLE))
    story.append(Spacer(1, 4 * mm))

    story.append(callout_box(
        "The architecture is designed as a strict separation of concerns across 10 layers. "
        "Each layer has one responsibility, one technology owner, and clear interfaces to adjacent layers. "
        "No layer bypasses another. This makes the system debuggable, replaceable, and independently scalable.",
        bg=HexColor("#1E1B4B"), border_color=PURPLE
    ))
    story.append(Spacer(1, 4 * mm))

    layers = [
        ("1", "Cloud Infrastructure", "AWS ECS Fargate · RDS · ElastiCache · S3 · Route53", BLUE),
        ("2", "Container Orchestration", "Docker · Docker Compose (dev) · ECS Task Definitions (prod)", CYAN),
        ("3", "Ingress & Edge", "CloudFront · Application Load Balancer · ACM SSL · WAF", PURPLE),
        ("4", "Backend Orchestrator", "FastAPI · SQLAlchemy async · Pydantic v2 · APScheduler", BLUE),
        ("5", "AI Intelligence", "11-provider router · Circuit breakers · Cost tracker · Task routing", AMBER),
        ("6", "Memory & Data", "PostgreSQL · pgvector · Redis · S3 · CloudWatch Logs", GREEN),
        ("7", "Frontend", "React 18 · Vite · Tailwind CSS · Zustand · Framer Motion", CYAN),
        ("8", "Agent Automation", "Specialized AI agents · Task queue · Scheduled jobs · Event handlers", PURPLE),
        ("9", "Business Operations", "Gmail · Apollo · HubSpot · Slack · Stripe · Telegram · Notion", AMBER),
        ("10", "Observability", "Prometheus · Grafana · CloudWatch · X-Ray · Alert Manager", GREEN),
    ]

    layer_data = [["#", "Layer", "Core Technologies"]]
    for num, name, tech, _ in layers:
        layer_data.append([num, name, tech])

    layer_table = make_table(
        layer_data,
        col_widths=[10 * mm, 50 * mm, CONTENT_W - 60 * mm],
        header_bg=DARK_GRAY,
    )
    story.append(layer_table)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Full System Data Flow", S["h2"]))
    flow = (
        "USER BROWSER  →  Route53 DNS  →  CloudFront (CDN + SSL termination)  →  "
        "Application Load Balancer  →  [Frontend: React/Nginx] or [Backend: FastAPI]  →  "
        "AI Intelligence Router  →  Memory Layer (PostgreSQL + Redis)  →  "
        "Agent & Automation System  →  Business Operations APIs"
    )
    story.append(callout_box(flow, bg=HexColor("#0F172A"), border_color=CYAN))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "All compute runs in private subnets. No ECS task has a public IP address. "
        "Traffic enters only through the ALB. Outbound AI API calls route through a NAT Gateway. "
        "This is the correct zero-trust production posture.",
        S["body"]
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTIONS 3–12 — THE 10 LAYERS IN DETAIL
    # ══════════════════════════════════════════════════════════════════════════

    layer_details = [
        {
            "num": 3, "title": "Layer 1 — Cloud Infrastructure", "color": BLUE,
            "intro": (
                "The cloud foundation is built on AWS ap-south-2 (Hyderabad) as primary and "
                "ap-south-1 (Mumbai) as disaster recovery. All infrastructure is defined in Terraform "
                "and lives in the infra/terraform/ directory. Nothing is provisioned manually."
            ),
            "why": (
                "ECS Fargate is chosen over raw EC2 because it eliminates all server management overhead: "
                "no OS patching, no capacity planning, no instance health management. You define a task "
                "and AWS runs it. Auto-scaling adds tasks when CPU exceeds 70%, removes them when load drops. "
                "For a 24/7 autonomous system, this is the only defensible choice."
            ),
            "components": [
                ("VPC", "Private subnets for compute, public subnets for ALB only. NAT Gateway for outbound."),
                ("ECS Fargate", "Serverless container runtime. Backend: 0.5 vCPU / 1GB. Frontend: 0.25 vCPU / 512MB."),
                ("RDS PostgreSQL Multi-AZ", "Primary in ap-south-2a, standby in ap-south-2b. Automatic failover <60s."),
                ("ElastiCache Redis", "Single-node t3.micro for dev, cluster mode for production scale."),
                ("S3", "Proposals, invoices, attachments, frontend static assets (CloudFront origin)."),
                ("Secrets Manager", "All API keys, DB passwords, webhook tokens. Injected into ECS at runtime."),
                ("Route53", "DNS management. A records pointing to CloudFront distribution."),
                ("ACM", "Free SSL/TLS certificates. Auto-renewed. Attached to CloudFront and ALB."),
            ],
        },
        {
            "num": 4, "title": "Layer 2 — Container Orchestration", "color": CYAN,
            "intro": (
                "Three environments use the same Docker images but different orchestration strategies. "
                "This ensures what works locally behaves identically in production."
            ),
            "why": (
                "Docker Compose is sufficient for local development and staging validation. "
                "ECS task definitions provide the same container configuration in production. "
                "The critical rule: build images once, promote the same image from dev to staging to production. "
                "Never rebuild in CI for production — tag by git SHA, promote by SHA."
            ),
            "components": [
                ("Development", "docker-compose.yml — postgres, redis, backend, frontend, nginx. All with health checks."),
                ("Production images", "Multi-stage Dockerfile. Build stage installs dependencies, runtime stage is minimal."),
                ("Image registry", "AWS ECR. Images tagged by git SHA. Latest tag also updated on main branch deploys."),
                ("Task definitions", "JSON in infra/terraform/. CPU, memory, port mappings, environment, secrets ARNs."),
                ("Service auto-scaling", "Target tracking — 70% CPU threshold. Min 1 task, max 4 tasks per service."),
                ("Deployment strategy", "Blue/Green rolling. New tasks start, health checks pass, old tasks drain and stop."),
            ],
        },
        {
            "num": 5, "title": "Layer 3 — Ingress, CDN & Security", "color": PURPLE,
            "intro": (
                "All traffic enters through a single controlled path. No service is directly "
                "internet-accessible. This layer handles SSL termination, caching, routing, "
                "and the first line of security defence."
            ),
            "why": (
                "CloudFront in front of everything — not just static files — provides DDoS protection "
                "at the edge, SSL termination closest to the user, and caches API responses that are "
                "safe to cache. The ALB handles path-based routing: /api/* goes to backend, "
                "everything else goes to the React frontend served by Nginx."
            ),
            "components": [
                ("CloudFront", "Global CDN. Caches React static assets. Forces HTTPS. Custom domain with ACM cert."),
                ("ALB", "Layer 7 load balancer. Path routing. Health checks on /health. Sticky sessions for WebSocket."),
                ("WAF", "Block SQL injection, XSS, common scanners. Rate limit by IP (add after launch)."),
                ("Security Groups", "Backend SG: only accepts traffic from ALB SG. DB SG: only accepts from backend SG."),
                ("HTTPS enforcement", "CloudFront redirects HTTP → HTTPS. HSTS headers. TLS 1.2 minimum."),
                ("Cache invalidation", "CloudFront paths invalidated on every frontend deployment via deploy.yml."),
            ],
        },
        {
            "num": 6, "title": "Layer 4 — Backend Orchestrator", "color": BLUE,
            "intro": (
                "FastAPI is the operational core of JARVIS. Every business action, AI call, "
                "agent dispatch, and data operation flows through it. It is asynchronous throughout "
                "— no blocking I/O anywhere in the call stack."
            ),
            "why": (
                "FastAPI with SQLAlchemy 2.0 async and asyncpg achieves ~10,000 requests/second on "
                "a single 0.5 vCPU container for non-AI endpoints. AI endpoints are network-bound "
                "(waiting for OpenAI/Claude), so async is critical — the event loop handles thousands "
                "of concurrent AI requests without blocking."
            ),
            "components": [
                ("19 route modules", "chat, briefing, approvals, agents, crm, leads, outreach, tasks, intelligence, governance, emergency, knowledge, catalog, ai_ops, team, auth, scheduler, calendar, sync."),
                ("Request middleware", "X-Request-ID on every request. X-Response-Time in every response. Structured JSON logs."),
                ("Error handling", "Global exception handlers. Standardised {error, status, path, request_id} envelope."),
                ("Connection pooling", "pool_size=10, max_overflow=20. Add PgBouncer when scaling beyond 2 containers."),
                ("Auto-seed on boot", "Service catalog and team registry seed themselves on first startup. No manual steps."),
                ("/health + /readyz", "Liveness probe (no DB) and readiness probe (DB ping, AI, scheduler, team registry)."),
            ],
        },
        {
            "num": 7, "title": "Layer 5 — AI Intelligence System", "color": AMBER,
            "intro": (
                "The AI router is the primary competitive differentiator of JARVIS. No SaaS product "
                "or off-the-shelf tool provides this level of multi-provider orchestration, cost "
                "awareness, and automatic failover in a single system."
            ),
            "why": (
                "Single-provider AI systems fail when that provider has an outage, rate limits your "
                "account, or raises prices. The 11-provider circuit breaker architecture means JARVIS "
                "never goes down due to an AI provider failure — it simply routes to the next available "
                "provider in the fallback chain, transparently and instantly."
            ),
            "components": [
                ("11 providers", "Anthropic, OpenAI, Google, DeepSeek, Groq, Mistral, Moonshot, ZhipuAI, Qwen, MiniMax, NVIDIA."),
                ("Task-type routing", "CODE→Claude Sonnet, REASONING→Claude Opus, RESEARCH→Gemini, FAST→DeepSeek, REALTIME→Groq."),
                ("Circuit breakers", "3 failures → OPEN state → 5-minute cooldown → HALF_OPEN probe → CLOSED on success."),
                ("Cost tracking", "Per-call USD estimate from 18-entry rate table. Daily aggregation. $50 surge alert."),
                ("AI response caching", "NEXT: Hash prompt+context → check Redis → return cached if found. 20-40% cost reduction."),
                ("Audit log", "Every AI call persisted: provider, model, tokens, latency_ms, cost_usd, success."),
            ],
        },
        {
            "num": 8, "title": "Layer 6 — Memory & Data Architecture", "color": GREEN,
            "intro": (
                "JARVIS's intelligence depends on its memory. A system that cannot remember is a "
                "system that cannot learn. The data architecture is designed to support operational "
                "storage, intelligent retrieval, and high-speed caching simultaneously."
            ),
            "why": (
                "PostgreSQL handles all relational data. pgvector extends it with vector similarity "
                "search — turning the database into a semantic memory store. Redis handles everything "
                "that needs sub-millisecond access: sessions, rate limits, AI response cache, "
                "real-time counters. S3 handles unstructured binary data: PDFs, images, exports."
            ),
            "components": [
                ("PostgreSQL (RDS)", "All operational data. 15 SQLAlchemy models. Multi-AZ. Daily automated backups."),
                ("pgvector", "NEXT: Add to RDS. Generate embeddings for memories, proposals, conversations. Semantic recall."),
                ("Redis (ElastiCache)", "Sessions, AI response cache (TTL 1h), rate limit counters, real-time pub/sub for WS."),
                ("S3", "Proposal PDFs, invoice documents, exported reports, frontend build artifacts."),
                ("CloudWatch Logs", "All container stdout/stderr. 90-day retention. Queryable with CloudWatch Insights."),
                ("Named volumes (dev)", "postgres_data, redis_data — persist across container restarts in local dev."),
            ],
        },
    ]

    for layer in layer_details:
        story.append(SectionHeader(layer["num"], layer["title"], CONTENT_W, layer["color"]))
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(layer["intro"], S["body"]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Why This Technology", S["h3"]))
        story.append(callout_box(layer["why"], bg=HexColor("#0F172A"), border_color=layer["color"]))
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("Components", S["h3"]))
        comp_data = [["Component", "Purpose & Configuration"]]
        for comp, desc in layer["components"]:
            comp_data.append([comp, desc])
        story.append(make_table(comp_data, [48 * mm, CONTENT_W - 48 * mm], header_bg=DARK_GRAY))
        story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # DEPLOYMENT TOPOLOGY
    # ══════════════════════════════════════════════════════════════════════════

    story.append(SectionHeader(13, "Deployment Topology", CONTENT_W, PURPLE))
    story.append(Spacer(1, 4 * mm))

    topology = """
  INTERNET
      │
  ┌───▼────────────────────────────────────────────┐
  │  Route53  (jarvis.aliyarsolutions.com)          │
  └───┬────────────────────────────────────────────┘
      │
  ┌───▼────────────────────────────────────────────┐
  │  CloudFront  (SSL · CDN · DDoS protection)      │
  └───┬────────────────────────────────────────────┘
      │
  ┌───▼────────────────────────────────────────────┐
  │  Application Load Balancer                      │
  │  /api/*  ──►  Backend Target Group              │
  │  /*      ──►  Frontend Target Group             │
  └───┬──────────────────────┬─────────────────────┘
      │ Private Subnet        │ Private Subnet
  ┌───▼──────────────┐  ┌────▼──────────────────┐
  │  ECS Fargate     │  │  ECS Fargate           │
  │  Backend Tasks   │  │  Frontend Tasks        │
  │  FastAPI v9.0    │  │  Nginx + React Build   │
  └───┬──────────────┘  └───────────────────────-┘
      │
  ┌───┼────────────────────────────────────────────┐
  │   │           Data Layer (Private)              │
  │ ┌─▼──────────┐  ┌──────────┐  ┌─────────────┐ │
  │ │  RDS PG    │  │  Redis   │  │     S3      │ │
  │ │  Multi-AZ  │  │  Cache   │  │   Buckets   │ │
  │ └────────────┘  └──────────┘  └─────────────┘ │
  └────────────────────────────────────────────────┘"""

    story.append(Table(
        [[Paragraph(f'<font face="Courier" size="7.5" color="#06B6D4">{topology}</font>',
                    ParagraphStyle("_", leading=10, fontName="Courier"))]],
        colWidths=[CONTENT_W],
    ))

    story.append(Spacer(1, 3 * mm))

    env_data = [
        ["Environment", "Compute", "Database", "Cache", "Purpose"],
        ["Development", "Laptop (uvicorn --reload)", "Docker PostgreSQL", "Docker Redis", "Feature development"],
        ["Local Staging", "docker-compose up", "Docker PostgreSQL", "Docker Redis", "Integration testing"],
        ["Production", "ECS Fargate (Hyderabad)", "RDS Multi-AZ", "ElastiCache", "24/7 live system"],
        ["DR Standby", "ECS (Mumbai)", "RDS Read Replica", "ElastiCache", "Failover target"],
    ]
    story.append(make_table(env_data,
        [30 * mm, 45 * mm, 38 * mm, 30 * mm, CONTENT_W - 143 * mm],
        header_bg=DARK_GRAY))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # STEP-BY-STEP IMPLEMENTATION GUIDE
    # ══════════════════════════════════════════════════════════════════════════

    story.append(SectionHeader(14, "Step-by-Step Implementation Guide", CONTENT_W, GREEN))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "This guide walks through every implementation step from a blank AWS account to a "
        "fully operational JARVIS system. Each step includes the exact commands, expected outputs, "
        "and validation checks. Follow the steps in order — each builds on the previous.",
        S["body"]
    ))
    story.append(Spacer(1, 4 * mm))

    # ── PHASE 1 ───────────────────────────────────────────────────────────────
    story.append(Paragraph("PHASE 1 — AWS FOUNDATION", S["h2"]))
    story.append(ColorBar(CONTENT_W, 2, BLUE))
    story.append(Spacer(1, 3 * mm))

    steps_phase1 = [
        (1, "Create AWS Account & Configure IAM", [
            "Go to aws.amazon.com → Create account (use business email)",
            "Enable MFA on root account immediately — this is non-negotiable",
            "Create IAM user 'jarvis-deploy' with programmatic access",
            "Attach policies: AmazonECS_FullAccess, AmazonEC2FullAccess, AmazonRDSFullAccess,",
            "  AmazonElastiCacheFullAccess, AmazonS3FullAccess, SecretsManagerReadWrite",
            "Download and save the access key CSV — you will not see it again",
            "Install AWS CLI: pip install awscli",
            "Configure: aws configure  (enter key, secret, region: ap-south-2, format: json)",
            "Validate: aws sts get-caller-identity  → should return your account ID",
        ]),
        (2, "Install & Configure Terraform", [
            "Download Terraform 1.9+ from terraform.io/downloads",
            "Add to PATH: sudo mv terraform /usr/local/bin/",
            "Validate: terraform version  → should show 1.9.x",
            "Navigate to infra/terraform/ directory",
            "Create terraform.tfvars with your specific values (never commit this file)",
            "Run: terraform init  → downloads AWS provider",
            "Run: terraform plan  → shows what will be created (no changes made yet)",
            "Review the plan output — verify VPC, subnets, ECS cluster, RDS are listed",
        ]),
        (3, "Provision Core Infrastructure", [
            "Run: terraform apply  → type 'yes' when prompted",
            "Wait 8–12 minutes for RDS to provision (this is the slowest component)",
            "Expected outputs: vpc_id, rds_endpoint, ecs_cluster_arn, alb_dns_name",
            "Save the outputs — you'll need them for environment configuration",
            "Verify in AWS Console: ECS cluster 'jarvis-production-cluster' exists",
            "Verify: RDS instance is 'Available' status in ap-south-2a",
            "Verify: ElastiCache cluster is 'Available'",
            "Verify: S3 bucket 'jarvis-production-assets' exists",
        ]),
        (4, "Configure AWS Secrets Manager", [
            "In AWS Console → Secrets Manager → Store a new secret",
            "Create secret 'jarvis/production/env' with key-value pairs:",
            "  ANTHROPIC_API_KEY = sk-ant-...",
            "  OPENAI_API_KEY = sk-...",
            "  GOOGLE_API_KEY = AIza...",
            "  SLACK_WEBHOOK_URL = https://hooks.slack.com/...",
            "  TELEGRAM_BOT_TOKEN = ...",
            "  (all other API keys)",
            "Note the secret ARN — add it to your ECS task definition in Terraform",
            "Test access: aws secretsmanager get-secret-value --secret-id jarvis/production/env",
        ]),
    ]

    for step_num, title, items in steps_phase1:
        story.append(KeepTogether([
            step_box(step_num, title, items, BLUE),
            Spacer(1, 3 * mm),
        ]))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("PHASE 2 — CONTAINER BUILD & REGISTRY", S["h2"]))
    story.append(ColorBar(CONTENT_W, 2, CYAN))
    story.append(Spacer(1, 3 * mm))

    steps_phase2 = [
        (5, "Create ECR Repositories & Build Images", [
            "Create ECR repos: aws ecr create-repository --repository-name jarvis-production-backend",
            "Create ECR repos: aws ecr create-repository --repository-name jarvis-production-frontend",
            "Get ECR login token: aws ecr get-login-password | docker login --username AWS",
            "  --password-stdin <account-id>.dkr.ecr.ap-south-2.amazonaws.com",
            "Build backend: docker build -t jarvis-backend ./backend",
            "Tag: docker tag jarvis-backend:latest <ecr-uri>/jarvis-production-backend:latest",
            "Push: docker push <ecr-uri>/jarvis-production-backend:latest",
            "Repeat build/tag/push for frontend (./frontend directory)",
            "Validate: both images appear in ECR console with 'latest' tag",
        ]),
        (6, "Configure ECS Task Definitions", [
            "ECS task definitions are in infra/terraform/ecs.tf — review and update image URIs",
            "Ensure the task definition includes secretsFrom pointing to your Secrets Manager ARN",
            "Backend task: 512 CPU units (0.5 vCPU), 1024 MB memory",
            "Frontend task: 256 CPU units (0.25 vCPU), 512 MB memory",
            "Set log configuration: awslogs driver, log group /jarvis/backend, region ap-south-2",
            "Run terraform apply to register the new task definitions",
            "Validate: ECS console shows task definition revisions for both services",
        ]),
    ]

    for step_num, title, items in steps_phase2:
        story.append(KeepTogether([
            step_box(step_num, title, items, CYAN),
            Spacer(1, 3 * mm),
        ]))

    story.append(PageBreak())

    story.append(Paragraph("PHASE 3 — NETWORKING & SSL", S["h2"]))
    story.append(ColorBar(CONTENT_W, 2, PURPLE))
    story.append(Spacer(1, 3 * mm))

    steps_phase3 = [
        (7, "Domain Configuration & SSL Certificate", [
            "Register domain or transfer to Route53 (if not already there)",
            "In Route53: create hosted zone for your domain",
            "In ACM (us-east-1 region — required for CloudFront): request public certificate",
            "  Add domain: aliyarsolutions.com and *.aliyarsolutions.com",
            "Validate via DNS: ACM creates CNAME records — add them to Route53",
            "Wait for certificate status to show 'Issued' (5–15 minutes)",
            "IMPORTANT: ACM certificate for CloudFront MUST be in us-east-1 region",
        ]),
        (8, "Configure CloudFront Distribution", [
            "Create CloudFront distribution with ALB as origin",
            "Set Origin Protocol: HTTPS only (ALB listens on 443)",
            "Cache policy: Managed-CachingDisabled for /api/* paths (API responses must not cache)",
            "Cache policy: Managed-CachingOptimized for /* (static assets — long TTL)",
            "Viewer Protocol: Redirect HTTP to HTTPS",
            "Attach ACM certificate from us-east-1",
            "Set CNAME: jarvis.aliyarsolutions.com",
            "In Route53: Create A record (alias) pointing to CloudFront distribution domain",
            "Wait for CloudFront deployment (15–20 minutes for global propagation)",
            "Validate: https://jarvis.aliyarsolutions.com/health → {status: ok}",
        ]),
        (9, "Configure ALB & Target Groups", [
            "ALB listener on port 443 with ACM certificate (separate from CloudFront cert — use ap-south-2)",
            "Create listener rule: if path starts with /api/ → forward to backend target group",
            "Default rule: forward to frontend target group",
            "Backend target group: health check path /health, port 8000, threshold 2/2",
            "Frontend target group: health check path /, port 80, threshold 2/2",
            "Enable WebSocket: set ALB idle timeout to 300 seconds in load balancer attributes",
            "Add stickiness to backend target group (needed for WebSocket connection persistence)",
        ]),
    ]

    for step_num, title, items in steps_phase3:
        story.append(KeepTogether([
            step_box(step_num, title, items, PURPLE),
            Spacer(1, 3 * mm),
        ]))

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("PHASE 4 — DATABASE & CACHE SETUP", S["h2"]))
    story.append(ColorBar(CONTENT_W, 2, GREEN))
    story.append(Spacer(1, 3 * mm))

    steps_phase4 = [
        (10, "Initialize PostgreSQL Database", [
            "Connect to RDS from a bastion EC2 or via AWS Session Manager (no SSH keys needed)",
            "Alternative: temporarily add your IP to the RDS security group for setup only",
            "Connect: psql -h <rds-endpoint> -U jarvis -d jarvis_db",
            "JARVIS auto-creates all tables on startup via SQLAlchemy init_db()",
            "No manual schema creation required — all models are registered in app/models/__init__.py",
            "Run infrastructure/postgres/init.sql for any custom PostgreSQL extensions",
            "Validate: after first JARVIS startup, run \\dt to see all 15+ tables created",
            "Verify auto-seed: SELECT count(*) FROM service_divisions;  → should return 30",
            "Verify auto-seed: SELECT count(*) FROM team_members;  → should return 9",
        ]),
        (11, "Configure Redis & Test Connectivity", [
            "ElastiCache Redis is provisioned by Terraform — no manual setup needed",
            "Get the Redis endpoint from terraform output or ElastiCache console",
            "Backend receives REDIS_URL via environment: redis://<endpoint>:6379/0",
            "Test from backend container: redis-cli -h <endpoint> ping  → PONG",
            "Validate session storage: make a chat request, check Redis keys: KEYS *",
            "Redis is used for: WebSocket pub/sub, AI response cache, rate limit counters",
        ]),
    ]

    for step_num, title, items in steps_phase4:
        story.append(KeepTogether([
            step_box(step_num, title, items, GREEN),
            Spacer(1, 3 * mm),
        ]))

    story.append(PageBreak())

    story.append(Paragraph("PHASE 5 — CI/CD PIPELINE", S["h2"]))
    story.append(ColorBar(CONTENT_W, 2, AMBER))
    story.append(Spacer(1, 3 * mm))

    steps_phase5 = [
        (12, "Configure GitHub Actions Secrets", [
            "In GitHub repository → Settings → Secrets and Variables → Actions",
            "Add secrets (these are NEVER stored in code):",
            "  AWS_ACCESS_KEY_ID       — from IAM user jarvis-deploy",
            "  AWS_SECRET_ACCESS_KEY   — from IAM user jarvis-deploy",
            "  SLACK_WEBHOOK_URL       — for deployment notifications",
            "  APP_BASE_URL            — https://jarvis.aliyarsolutions.com",
            "Verify: the deploy.yml workflow is in .github/workflows/",
            "The workflow triggers on: push to main branch, or manual workflow_dispatch",
        ]),
        (13, "First Production Deployment", [
            "Merge your branch to main (or trigger manually via GitHub Actions UI)",
            "Watch the Actions tab — build job starts: builds backend + frontend Docker images",
            "Images are tagged with git SHA and pushed to ECR",
            "Deploy job: downloads current ECS task definition, updates image, registers new revision",
            "ECS performs rolling blue/green deployment — new task starts before old task stops",
            "Wait for ECS service to reach 'steady state' (wait-for-service-stability: true)",
            "Post-deploy: workflow hits /health and /readyz — pipeline fails if not 200",
            "Slack notification: ✅ JARVIS deployed + health-validated",
            "Validate: https://jarvis.aliyarsolutions.com → JARVIS dashboard loads",
        ]),
        (14, "Validate Full System Health", [
            "Run: curl https://jarvis.aliyarsolutions.com/health",
            "Expected: {status: ok, system: JARVIS, version: 9.0.0}",
            "Run: curl https://jarvis.aliyarsolutions.com/readyz",
            "Expected: {status: ready, checks: {database: {status: ok}, ai_providers: {available: N}}}",
            "Open dashboard: verify all 18 views load without errors",
            "POST /api/v1/catalog/seed and /api/v1/team/seed (auto-seeded on boot, but verify)",
            "Test chat: send a message, verify AI response with correct provider routing",
            "Check AI Ops dashboard: verify circuit breakers are all CLOSED",
            "Run: make readyz from development machine → should show all green",
        ]),
    ]

    for step_num, title, items in steps_phase5:
        story.append(KeepTogether([
            step_box(step_num, title, items, AMBER),
            Spacer(1, 3 * mm),
        ]))

    story.append(PageBreak())

    story.append(Paragraph("PHASE 6 — MONITORING & OBSERVABILITY", S["h2"]))
    story.append(ColorBar(CONTENT_W, 2, PURPLE))
    story.append(Spacer(1, 3 * mm))

    steps_phase6 = [
        (15, "Configure CloudWatch Logs & Alarms", [
            "ECS Fargate automatically sends container logs to CloudWatch (awslogs driver in task def)",
            "Log groups created: /jarvis/backend, /jarvis/frontend",
            "Set retention: 30 days (cost control — adjust to 90 days if budget allows)",
            "Create CloudWatch Metric Filter for ERROR log pattern → triggers alarm",
            "Create Alarm: 5xx error rate > 1% over 5 minutes → SNS → Slack notification",
            "Create Alarm: ECS CPU > 80% sustained 5 minutes → scale out trigger",
            "Create Alarm: RDS connections > 80% of max → alert (add connection pooler)",
            "Dashboard: create CloudWatch dashboard with key metrics for quick operational view",
        ]),
        (16, "Deploy Grafana & Prometheus", [
            "Deploy Grafana as ECS task (internal ALB only — not public-facing)",
            "Or use Grafana Cloud free tier (recommended — zero operational overhead)",
            "Connect Prometheus remote_write to Grafana Cloud Prometheus endpoint",
            "Import JARVIS dashboard JSON from monitoring/grafana/dashboard.json",
            "Configure alert notification channel: Slack webhook",
            "Set up 7 alert rules from monitoring/alert_rules.yml",
            "Test alerts: manually stop a container, verify alert fires within 2 minutes",
        ]),
    ]

    for step_num, title, items in steps_phase6:
        story.append(KeepTogether([
            step_box(step_num, title, items, PURPLE),
            Spacer(1, 3 * mm),
        ]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD PRIORITY MATRIX
    # ══════════════════════════════════════════════════════════════════════════

    story.append(SectionHeader(15, "Build Sequence & Priority Matrix", CONTENT_W, BLUE))
    story.append(Spacer(1, 4 * mm))

    priority_data = [
        ["Priority", "What to Build", "Why Now", "Time Estimate", "Impact"],
        ["1 — NOW", "Ship to ECS via existing Terraform + deploy.yml", "Foundation everything else depends on", "2–4 hours", "Critical"],
        ["2 — NOW", "Route53 + ACM + CloudFront + ALB on real domain", "Makes system publicly accessible with HTTPS", "2 hours", "Critical"],
        ["3 — NEXT", "Redis semantic AI response caching", "20–40% immediate AI cost reduction", "4 hours", "High ROI"],
        ["4 — NEXT", "pgvector + embedding memory layer", "Transforms keyword search into semantic recall", "6 hours", "High"],
        ["5 — WEEK 1", "Webhook receivers (HubSpot, Gmail, Apollo)", "Real-time data vs polling. Removes cron debt.", "6 hours", "High"],
        ["6 — WEEK 2", "Redis-backed persistent task queue", "Needed only when running 2+ backend containers", "4 hours", "Medium"],
        ["7 — WEEK 2", "AWS X-Ray distributed tracing", "Pinpoints performance bottlenecks with real traffic", "3 hours", "Medium"],
        ["8 — MONTH 1", "WAF rules + rate limiting per endpoint", "Security hardening after system is stable", "3 hours", "Medium"],
        ["9 — MONTH 2", "Multi-region DR (Mumbai failover)", "Business continuity. Only after primary is stable.", "8 hours", "Long-term"],
        ["10 — FUTURE", "EKS migration from ECS Fargate", "Only if ECS cannot handle load (unlikely soon)", "40+ hours", "Low now"],
    ]

    col_widths_p = [22 * mm, 52 * mm, 48 * mm, 24 * mm, CONTENT_W - 146 * mm]

    p_table_data = [priority_data[0]]
    for row in priority_data[1:]:
        p_table_data.append([Paragraph(cell, S["table_cell"]) for cell in row])

    impact_colors = {
        "Critical": RED, "High ROI": GREEN, "High": GREEN,
        "Medium": AMBER, "Long-term": CYAN, "Low now": MID_GRAY,
    }

    pt = Table(
        [[Paragraph(cell, S["table_header"]) for cell in priority_data[0]]] +
        [[Paragraph(row[i], S["table_cell"]) for i in range(len(row))] for row in priority_data[1:]],
        colWidths=col_widths_p
    )

    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_GRAY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#E2E8F0")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Colour the first two rows (Critical)
        ("BACKGROUND", (0, 1), (-1, 2), HexColor("#FFF1F2")),
        ("BACKGROUND", (0, 3), (-1, 4), HexColor("#ECFDF5")),
    ])
    pt.setStyle(ts)
    story.append(pt)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # TECHNOLOGY SELECTION REFERENCE
    # ══════════════════════════════════════════════════════════════════════════

    story.append(SectionHeader(16, "Technology Selection Reference", CONTENT_W, CYAN))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Why Each Technology Was Chosen Over Alternatives", S["h2"]))
    story.append(Spacer(1, 2 * mm))

    tech_decisions = [
        ["Decision", "Chosen", "Alternatives Considered", "Reason for Choice"],
        ["Container runtime", "ECS Fargate", "EC2, EKS, Lambda", "No server management. Auto-scaling. Native AWS integration. EKS is overkill at this scale."],
        ["Database", "PostgreSQL (RDS)", "MySQL, DynamoDB, MongoDB", "ACID compliance. JSON columns. Future pgvector. Relational data model fits business data perfectly."],
        ["Cache/Queue", "Redis", "Memcached, SQS, RabbitMQ", "Multi-purpose: cache + pub/sub + queue. Single dependency instead of three. Native TTL support."],
        ["AI Framework", "Custom router", "LangChain, LlamaIndex", "LangChain adds abstraction cost, debugging complexity, and version instability. Direct SDK calls are simpler, faster, and fully controllable."],
        ["Backend", "FastAPI", "Django, Express, Flask", "Async-native, high performance (~10k req/s), auto-generated OpenAPI docs, Pydantic validation built-in."],
        ["Frontend", "React + Vite", "Next.js, Vue, Angular", "Vite build is 10× faster than CRA. React ecosystem. No SSR needed for an internal ops dashboard."],
        ["IaC", "Terraform", "CDK, CloudFormation, Pulumi", "Provider-agnostic, mature ecosystem, most community resources, readable HCL syntax."],
        ["Reverse proxy", "Nginx", "Caddy, Traefik, HAProxy", "Industry standard. Zero configuration for static file serving. Mature, predictable, minimal."],
        ["Scheduling", "APScheduler", "Celery, Airflow, AWS EventBridge", "Zero additional infrastructure. Persistent jobs via SQLAlchemy. Sufficient for 7 cron jobs."],
        ["Secret storage", "AWS Secrets Manager", ".env files, SSM Parameter Store", "Encrypted, audited, version-controlled, native ECS integration. SSM is cheaper but less featured."],
    ]

    story.append(make_table(
        tech_decisions,
        [28 * mm, 28 * mm, 38 * mm, CONTENT_W - 94 * mm],
        header_bg=HexColor("#0C4A6E"),
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECURITY ARCHITECTURE
    # ══════════════════════════════════════════════════════════════════════════

    story.append(SectionHeader(17, "Security Architecture", CONTENT_W, RED))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Zero-Trust Network Security", S["h2"]))
    story.append(Paragraph(
        "Every component operates on the principle of least privilege. "
        "No service can communicate with another unless an explicit security group rule permits it. "
        "No credentials exist in any codebase, Docker image, or environment file on any server.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    sec_data = [
        ["Security Layer", "Controls", "Threat Mitigated"],
        ["Network (VPC)", "Private subnets, NAT Gateway, security groups", "Direct server access, lateral movement"],
        ["Edge (CloudFront + WAF)", "DDoS protection, bot filtering, geo-blocking", "Volume attacks, scrapers, injection"],
        ["Transport (ACM)", "TLS 1.2+ enforced, HSTS headers", "MITM, traffic interception"],
        ["Authentication (ALB)", "HTTPS-only listener, certificate pinning", "Downgrade attacks"],
        ["Secrets (Secrets Manager)", "KMS-encrypted, rotation-capable, IAM-controlled", "Credential leakage"],
        ["Container (ECS)", "Non-root user, read-only filesystem, no SSH", "Container escape, privilege escalation"],
        ["Code (gitleaks)", "Pre-commit secret scanning, 12 pattern types", "Accidental secret commits"],
        ["API (middleware)", "Request IDs, rate limits, standardised errors", "Enumeration, replay attacks"],
        ["Database (RDS)", "Private subnet, encrypted at rest, IAM auth option", "Unauthorised data access"],
        ["Dependencies", "Pin all versions in requirements.txt", "Supply chain attacks"],
    ]

    story.append(make_table(
        sec_data,
        [36 * mm, 60 * mm, CONTENT_W - 96 * mm],
        header_bg=HexColor("#7F1D1D"),
    ))
    story.append(Spacer(1, 4 * mm))

    story.append(callout_box(
        "CRITICAL RULE: If a secret is ever accidentally committed to git, treat it as compromised "
        "immediately. Rotate it before doing anything else. Then investigate how it happened and "
        "add a gitleaks rule to prevent it. A committed secret is a breached secret.",
        bg=HexColor("#7F1D1D"), border_color=RED
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SCALING ROADMAP
    # ══════════════════════════════════════════════════════════════════════════

    story.append(SectionHeader(18, "Scaling Roadmap", CONTENT_W, AMBER))
    story.append(Spacer(1, 4 * mm))

    scale_data = [
        ["Traffic Level", "Monthly Requests", "Architecture Change", "Expected Cost"],
        ["Stage 0 — Launch", "< 10k / month", "1 ECS task each. Single-AZ Redis.", "~$80–120 / month"],
        ["Stage 1 — Growth", "10k–100k / month", "Min 2 ECS tasks. Enable auto-scaling. Multi-AZ Redis.", "~$200–350 / month"],
        ["Stage 2 — Scale", "100k–1M / month", "Add PgBouncer. Redis cluster. CloudFront edge caching.", "~$500–800 / month"],
        ["Stage 3 — Enterprise", "1M–10M / month", "ECS capacity providers. Read replicas for RDS. CDN aggressive caching.", "~$1,500–3,000 / month"],
        ["Stage 4 — Platform", "> 10M / month", "Evaluate EKS. Multi-region active-active. Aurora Serverless.", "Custom quote"],
    ]

    story.append(make_table(
        scale_data,
        [32 * mm, 34 * mm, 72 * mm, CONTENT_W - 138 * mm],
        header_bg=HexColor("#78350F"),
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "The current architecture comfortably handles Stage 0 through Stage 2 without any "
        "architectural changes — only configuration changes (more tasks, bigger instances). "
        "The first real architectural evolution happens at Stage 3. You will know when you need it "
        "because your monitoring will tell you before it becomes a problem.",
        S["body"]
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # COST OPTIMISATION
    # ══════════════════════════════════════════════════════════════════════════

    story.append(SectionHeader(19, "Cost Optimisation Strategy", CONTENT_W, GREEN))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Infrastructure Cost Control", S["h2"]))

    cost_data = [
        ["Cost Area", "Current Approach", "Optimisation", "Saving Potential"],
        ["AI API calls", "All calls hit provider APIs", "Redis semantic cache (TTL 1h)", "20–40% reduction"],
        ["ECS Fargate", "On-demand pricing", "Fargate Spot for non-critical tasks", "50–70% on eligible tasks"],
        ["RDS", "db.t3.micro initially", "Reserved instance (1-year)", "30–40% vs on-demand"],
        ["Data transfer", "All via NAT Gateway", "VPC endpoints for S3/ECR", "$0.045 → $0 per GB"],
        ["CloudWatch Logs", "Default retention", "Set 30-day retention on all log groups", "70% log storage saving"],
        ["ECR storage", "All image versions", "Lifecycle policy: keep last 10 images only", "Negligible but clean"],
        ["AI model selection", "Expensive models for all tasks", "Task-type routing (FAST→DeepSeek)", "60–80% on FAST tasks"],
    ]

    story.append(make_table(
        cost_data,
        [28 * mm, 44 * mm, 44 * mm, CONTENT_W - 116 * mm],
        header_bg=HexColor("#14532D"),
    ))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Monthly Cost Estimate at Launch", S["h2"]))
    launch_costs = [
        ["Service", "Specification", "Estimated Monthly Cost"],
        ["ECS Fargate — Backend", "0.5 vCPU / 1GB / 730 hours", "~$15"],
        ["ECS Fargate — Frontend", "0.25 vCPU / 512MB / 730 hours", "~$8"],
        ["RDS PostgreSQL", "db.t3.micro, Multi-AZ, 20GB storage", "~$30"],
        ["ElastiCache Redis", "cache.t3.micro, single node", "~$12"],
        ["ALB", "730 hours + LCU charges", "~$18"],
        ["CloudFront", "First 1TB data transfer free", "~$0–5"],
        ["NAT Gateway", "730 hours + data processing", "~$35"],
        ["S3", "10GB storage + requests", "~$2"],
        ["Secrets Manager", "5 secrets × $0.40", "~$2"],
        ["CloudWatch", "Logs + metrics + alarms", "~$5"],
        ["Route53", "1 hosted zone + queries", "~$1"],
        ["TOTAL", "", "~$130–140 / month"],
    ]

    cost_table = Table(
        [[Paragraph(c, S["table_header"]) for c in launch_costs[0]]] +
        [[Paragraph(c, S["table_cell"]) for c in row] for row in launch_costs[1:-1]] +
        [[Paragraph(c, ParagraphStyle("_", fontName="Helvetica-Bold", fontSize=10, textColor=GREEN)) for c in launch_costs[-1]]],
        colWidths=[48 * mm, 80 * mm, CONTENT_W - 128 * mm],
    )
    cost_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, HexColor("#F8FAFC")]),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#ECFDF5")),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#E2E8F0")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BLUE),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(cost_table)

    story.append(Spacer(1, 4 * mm))
    story.append(callout_box(
        "The $130–140/month baseline gives you a production-grade, 24/7 autonomous AI operating "
        "system serving real clients globally. This is less than a single mid-level developer's "
        "daily salary. At Stage 1 growth, the system earns multiples of its infrastructure cost "
        "through automated outreach, proposals, and client operations.",
        bg=HexColor("#022C22"), border_color=GREEN
    ))

    # ══════════════════════════════════════════════════════════════════════════
    # FINAL PAGE
    # ══════════════════════════════════════════════════════════════════════════

    story.append(PageBreak())
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("JARVIS", S["cover_title"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "The foundation is built. The architecture is sound. The path is clear.",
        S["cover_sub"]
    ))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Ship to production. Validate the system is alive. Then build the next layer on top of a "
        "known-good foundation. Everything in this document exists to serve one mission: "
        "making Aliyar Solutions the most operationally efficient AI services company in the world.",
        S["body"]
    ))
    story.append(Spacer(1, 8 * mm))
    story.append(ColorBar(CONTENT_W, 3, CYAN))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"Aliyar Solutions · JARVIS v9.0.0 · {datetime.date.today().strftime('%B %Y')} · CONFIDENTIAL",
        S["cover_meta"]
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=cover_bg,
        onLaterPages=content_page,
    )
    print(f"✅  PDF written to: {output_path}")


if __name__ == "__main__":
    output = "/home/user/devops-docker-project/JARVIS_Architecture_Blueprint.pdf"
    build_pdf(output)
