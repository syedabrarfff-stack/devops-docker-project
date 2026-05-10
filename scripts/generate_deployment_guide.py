#!/usr/bin/env python3
"""
JARVIS — Aliyar Solutions
Complete Deployment Guide PDF Generator
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import os

# ── Colours ───────────────────────────────────────────────────────────────────
NAVY       = HexColor("#0A0E1A")
BLUE       = HexColor("#1A2744")
ACCENT     = HexColor("#2D6FE8")
ACCENT2    = HexColor("#00C6FF")
GREEN      = HexColor("#00D68F")
ORANGE     = HexColor("#FF8C42")
RED        = HexColor("#FF4D6D")
LIGHT_GREY = HexColor("#F4F6FA")
MID_GREY   = HexColor("#8892A4")
DARK_GREY  = HexColor("#2A3142")
WHITE      = white

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "JARVIS_Deployment_Guide.pdf")

# ── Custom Flowables ──────────────────────────────────────────────────────────

class CoverPage(Flowable):
    def __init__(self, w, h):
        Flowable.__init__(self)
        self.w = w
        self.h = h

    def draw(self):
        c = self.canv
        # Background
        c.setFillColor(NAVY)
        c.rect(0, 0, self.w, self.h, fill=1, stroke=0)

        # Diagonal accent
        c.setFillColor(BLUE)
        from reportlab.graphics.shapes import Polygon
        p = c.beginPath()
        p.moveTo(0, self.h * 0.55)
        p.lineTo(self.w * 0.6, self.h)
        p.lineTo(self.w, self.h)
        p.lineTo(self.w, self.h * 0.75)
        p.close()
        c.setFillColor(BLUE)
        c.drawPath(p, fill=1, stroke=0)

        # Accent line
        c.setStrokeColor(ACCENT)
        c.setLineWidth(3)
        c.line(40, self.h - 60, 40, self.h - 200)

        # Company
        c.setFillColor(ACCENT2)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(55, self.h - 75, "ALIYAR SOLUTIONS")

        # Title
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 34)
        c.drawString(55, self.h - 130, "JARVIS")
        c.setFont("Helvetica-Bold", 20)
        c.drawString(55, self.h - 158, "Complete Deployment Guide")

        # Subtitle
        c.setFillColor(MID_GREY)
        c.setFont("Helvetica", 12)
        c.drawString(55, self.h - 185, "From EC2 Setup to Fully Live Production System")

        # Divider
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1)
        c.line(55, self.h - 200, self.w - 55, self.h - 200)

        # Stat boxes
        stats = [
            ("6", "Phases"),
            ("40+", "Steps"),
            ("3", "Days"),
            ("24/7", "Uptime"),
        ]
        box_w = 100
        box_h = 60
        start_x = 55
        y = self.h - 290
        for val, label in stats:
            c.setFillColor(DARK_GREY)
            c.roundRect(start_x, y, box_w, box_h, 6, fill=1, stroke=0)
            c.setFillColor(ACCENT2)
            c.setFont("Helvetica-Bold", 22)
            c.drawCentredString(start_x + box_w / 2, y + 30, val)
            c.setFillColor(MID_GREY)
            c.setFont("Helvetica", 9)
            c.drawCentredString(start_x + box_w / 2, y + 14, label)
            start_x += box_w + 14

        # Description
        c.setFillColor(HexColor("#C8D0E0"))
        c.setFont("Helvetica", 10)
        lines = [
            "This guide takes you from your current EC2 + Docker + Terraform foundation",
            "to a fully automated, production-grade JARVIS deployment with CI/CD,",
            "domain, SSL, monitoring, and zero manual intervention on every deploy.",
        ]
        y2 = self.h - 360
        for line in lines:
            c.drawString(55, y2, line)
            y2 -= 16

        # Footer
        c.setFillColor(MID_GREY)
        c.setFont("Helvetica", 9)
        c.drawString(55, 30, "Aliyar Solutions — Confidential Operational Document")
        c.drawRightString(self.w - 55, 30, "JARVIS Infrastructure Division")


class PhaseHeader(Flowable):
    def __init__(self, number, title, subtitle, color=None, width=160*mm):
        Flowable.__init__(self)
        self.number = number
        self.title = title
        self.subtitle = subtitle
        self.color = color or ACCENT
        self.width = width
        self.height = 52

    def draw(self):
        c = self.canv
        c.setFillColor(NAVY)
        c.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=0)
        c.setFillColor(self.color)
        c.roundRect(0, 0, 52, self.height, 8, fill=1, stroke=0)
        c.rect(44, 0, 14, self.height, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(26, 14, self.number)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(64, 30, self.title)
        c.setFillColor(MID_GREY)
        c.setFont("Helvetica", 9)
        c.drawString(64, 14, self.subtitle)


class StepBox(Flowable):
    def __init__(self, number, title, width=160*mm):
        Flowable.__init__(self)
        self.number = number
        self.title = title
        self.width = width
        self.height = 28

    def draw(self):
        c = self.canv
        c.setFillColor(DARK_GREY)
        c.roundRect(0, 0, self.width, self.height, 5, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.circle(14, 14, 10, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(14, 10, str(self.number))
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(30, 9, self.title)


class StatusBadge(Flowable):
    def __init__(self, text, color=None):
        Flowable.__init__(self)
        self.text = text
        self.color = color or GREEN
        self.width = len(text) * 7 + 16
        self.height = 18

    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(self.width / 2, 5, self.text)


class CodeBlock(Flowable):
    def __init__(self, code_lines, width=160*mm):
        Flowable.__init__(self)
        self.code_lines = code_lines if isinstance(code_lines, list) else code_lines.strip().split("\n")
        self.width = width
        self.height = len(self.code_lines) * 14 + 20

    def draw(self):
        c = self.canv
        c.setFillColor(HexColor("#0D1117"))
        c.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=0)
        c.setFillColor(HexColor("#30363D"))
        c.roundRect(0, self.height - 18, self.width, 18, 6, fill=1, stroke=0)
        c.rect(0, self.height - 18, self.width, 9, fill=1, stroke=0)
        for i, dot_x in enumerate([10, 22, 34]):
            colors = [HexColor("#FF5F57"), HexColor("#FFBD2E"), HexColor("#28C940")]
            c.setFillColor(colors[i])
            c.circle(dot_x, self.height - 9, 4, fill=1, stroke=0)
        y = self.height - 32
        for line in self.code_lines:
            if line.startswith("#"):
                c.setFillColor(HexColor("#8B949E"))
            elif line.startswith("$") or line.startswith("sudo"):
                c.setFillColor(ACCENT2)
            elif any(line.strip().startswith(k) for k in ["export", "echo", "cat", "mkdir", "cd", "git", "docker", "terraform", "aws", "make", "curl", "apt", "systemctl", "certbot"]):
                c.setFillColor(GREEN)
            else:
                c.setFillColor(HexColor("#E6EDF3"))
            c.setFont("Courier-Bold" if line.startswith("#") else "Courier", 8)
            c.drawString(12, y, line[:95])
            y -= 14


# ── Styles ────────────────────────────────────────────────────────────────────

def make_styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", fontSize=18, textColor=WHITE, fontName="Helvetica-Bold",
                             spaceAfter=6, backColor=NAVY, leading=24,
                             leftIndent=0, borderPad=8),
        "h2": ParagraphStyle("h2", fontSize=13, textColor=ACCENT2, fontName="Helvetica-Bold",
                             spaceAfter=4, spaceBefore=10),
        "h3": ParagraphStyle("h3", fontSize=11, textColor=WHITE, fontName="Helvetica-Bold",
                             spaceAfter=3, spaceBefore=6),
        "body": ParagraphStyle("body", fontSize=9, textColor=HexColor("#C8D0E0"),
                               fontName="Helvetica", leading=14, spaceAfter=4),
        "note": ParagraphStyle("note", fontSize=8, textColor=HexColor("#8892A4"),
                               fontName="Helvetica-Oblique", leading=12, spaceAfter=3,
                               leftIndent=10),
        "bullet": ParagraphStyle("bullet", fontSize=9, textColor=HexColor("#C8D0E0"),
                                 fontName="Helvetica", leading=13, spaceAfter=2,
                                 leftIndent=16, bulletIndent=6),
        "warn": ParagraphStyle("warn", fontSize=9, textColor=ORANGE,
                               fontName="Helvetica-Bold", leading=13, spaceAfter=3),
        "success": ParagraphStyle("success", fontSize=9, textColor=GREEN,
                                  fontName="Helvetica-Bold", leading=13, spaceAfter=3),
        "toc": ParagraphStyle("toc", fontSize=10, textColor=HexColor("#C8D0E0"),
                              fontName="Helvetica", leading=18, spaceAfter=2),
    }


def sp(n=4):
    return Spacer(1, n * mm)


def hr(color=DARK_GREY):
    return HRFlowable(width="100%", thickness=1, color=color, spaceAfter=4, spaceBefore=4)


# ── Document Builder ──────────────────────────────────────────────────────────

def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    W = A4[0] - 40 * mm
    S = make_styles()
    story = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.append(CoverPage(A4[0], A4[1]))
    story.append(PageBreak())

    # ── Table of Contents ─────────────────────────────────────────────────────
    story.append(Paragraph("Table of Contents", S["h2"]))
    story.append(hr(ACCENT))
    story.append(sp(2))

    toc_items = [
        ("Phase 1", "Prepare Your Codebase", "Deploy-ready configuration"),
        ("Phase 2", "Terraform — Full AWS Infrastructure", "VPC, EC2, Security Groups, RDS, Redis"),
        ("Phase 3", "Deploy JARVIS on EC2", "Docker Compose production deployment"),
        ("Phase 4", "Domain + SSL Setup", "Professional domain, HTTPS, Nginx"),
        ("Phase 5", "CI/CD Automation", "GitHub Actions — zero-touch deploys"),
        ("Phase 6", "Monitoring + Health", "Grafana, Prometheus, alerts"),
        ("Bonus", "Go-Live Checklist", "Final verification before clients"),
        ("Future", "Enterprise Upgrade Path", "ECS Fargate migration roadmap"),
    ]

    for phase, title, sub in toc_items:
        row = Table(
            [[Paragraph(f"<b>{phase}</b>", S["body"]),
              Paragraph(f"<b>{title}</b>", S["body"]),
              Paragraph(sub, S["note"])]],
            colWidths=[W * 0.12, W * 0.38, W * 0.50],
        )
        row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (0, 0), WHITE),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [DARK_GREY]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        story.append(row)
        story.append(sp(1))

    story.append(PageBreak())

    # ── CURRENT STATE ─────────────────────────────────────────────────────────
    story.append(Paragraph("Where You Are Right Now", S["h2"]))
    story.append(hr(ACCENT))
    story.append(sp(2))

    current = [
        ["✅ EC2 Instance", "Live Ubuntu server on AWS"],
        ["✅ Docker", "Installed and running"],
        ["✅ Terraform", "Installed, AWS provider configured"],
        ["✅ AWS CLI", "Configured with credentials"],
        ["✅ Nginx", "Deployed publicly"],
        ["✅ Ports Open", "22, 80, 443, 3000, 8080"],
        ["⏳ JARVIS Code", "Not yet deployed to server"],
        ["⏳ Domain + SSL", "Not yet configured"],
        ["⏳ CI/CD", "Not yet automated"],
        ["⏳ Monitoring", "Not yet running"],
    ]
    t = Table(current, colWidths=[W * 0.35, W * 0.65])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_GREY),
        ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#C8D0E0")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [DARK_GREY, NAVY]),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#2A3142")),
    ]))
    story.append(t)
    story.append(sp(3))
    story.append(Paragraph("By end of this guide: Everything marked ⏳ will be ✅ and JARVIS will be fully live.", S["success"]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PhaseHeader("1", "Prepare Your Codebase", "Configure JARVIS for production deployment", ACCENT, W))
    story.append(sp(3))

    story.append(Paragraph("What this phase does: Makes your JARVIS codebase deployment-ready before it touches the server.", S["body"]))
    story.append(sp(2))

    story.append(StepBox(1, "Create production .env file", W))
    story.append(sp(2))
    story.append(Paragraph("On your local machine, create a .env file with all required keys:", S["body"]))
    story.append(CodeBlock([
        "# On your local machine",
        "cd devops-docker-project",
        "cp .env.example .env",
        "",
        "# Edit .env and fill in these values:",
        "DATABASE_URL=postgresql+asyncpg://jarvis:yourpassword@postgres:5432/jarvis",
        "REDIS_URL=redis://redis:6379/0",
        "SECRET_KEY=your-super-secret-key-minimum-32-chars",
        "ANTHROPIC_API_KEY=sk-ant-...",
        "OPENAI_API_KEY=sk-...",
        "STRIPE_SECRET_KEY=sk_live_...",
        "SLACK_WEBHOOK_URL=https://hooks.slack.com/...",
        "APP_BASE_URL=https://yourdomain.com",
        "DEBUG=false",
        "ENVIRONMENT=production",
    ], W))
    story.append(sp(2))

    story.append(StepBox(2, "Verify Docker Compose works locally", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Test locally first",
        "cd infrastructure",
        "docker compose up -d",
        "docker compose ps",
        "# All services should show: healthy or running",
        "curl http://localhost:8000/health",
        "# Expected: {\"status\": \"ok\", \"system\": \"JARVIS\"}",
    ], W))
    story.append(sp(2))

    story.append(StepBox(3, "Push everything to GitHub", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "git add .",
        "git commit -m 'feat: production-ready configuration'",
        "git push origin claude/jarvis-cans-api-integration-ZThTD",
        "# NEVER push .env — it is in .gitignore",
    ], W))
    story.append(sp(2))
    story.append(Paragraph("⚠️  Never commit your .env file. It contains secrets. It is already in .gitignore.", S["warn"]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 2
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PhaseHeader("2", "Terraform — Full AWS Infrastructure", "Automate your entire cloud setup with one command", GREEN, W))
    story.append(sp(3))

    story.append(Paragraph("What this phase does: Uses Terraform to provision VPC, EC2, Security Groups, Elastic IP, and all networking automatically.", S["body"]))
    story.append(sp(2))

    story.append(StepBox(4, "Navigate to Terraform directory", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "cd infra/terraform",
        "ls",
        "# You should see: main.tf, variables.tf, outputs.tf",
    ], W))
    story.append(sp(2))

    story.append(StepBox(5, "Update Terraform variables", W))
    story.append(sp(2))
    story.append(Paragraph("Edit terraform.tfvars (create if not exists):", S["body"]))
    story.append(CodeBlock([
        "# infra/terraform/terraform.tfvars",
        'region          = "ap-south-2"',
        'instance_type   = "t3.medium"',
        'key_name        = "your-ec2-keypair-name"',
        'db_password     = "your-secure-db-password"',
        'project_name    = "jarvis-production"',
    ], W))
    story.append(sp(2))

    story.append(StepBox(6, "Run Terraform to provision infrastructure", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "terraform init",
        "# Downloads AWS provider",
        "",
        "terraform plan",
        "# Shows exactly what will be created — review carefully",
        "",
        "terraform apply",
        "# Type 'yes' when prompted",
        "# Takes 3-5 minutes",
        "",
        "terraform output",
        "# Copy the EC2 public IP — you will need it",
    ], W))
    story.append(sp(2))

    story.append(StepBox(7, "Save your EC2 IP and SSH key", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Terraform outputs your new server IP",
        "# Save it — example: 13.235.45.112",
        "",
        "# Test SSH connection",
        "ssh -i your-key.pem ubuntu@YOUR_EC2_IP",
        "# You should see Ubuntu welcome message",
    ], W))
    story.append(sp(2))

    story.append(Paragraph("What Terraform creates automatically:", S["h3"]))
    infra_items = [
        ["VPC", "Isolated network for your infrastructure"],
        ["Public Subnet", "Where EC2 runs"],
        ["Internet Gateway", "Connects your VPC to the internet"],
        ["Security Group", "Firewall — ports 22, 80, 443, 8000 open"],
        ["EC2 t3.medium", "Your production server (2 CPU, 4GB RAM)"],
        ["Elastic IP", "Static IP — never changes even after restart"],
        ["Key Pair", "SSH access credentials"],
    ]
    t = Table(infra_items, colWidths=[W * 0.25, W * 0.75])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BLUE),
        ("BACKGROUND", (1, 0), (1, -1), DARK_GREY),
        ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#C8D0E0")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#1A2744")),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 3
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PhaseHeader("3", "Deploy JARVIS on EC2", "Get the full system running on your server", ACCENT2, W))
    story.append(sp(3))

    story.append(Paragraph("What this phase does: SSHs into your EC2, installs dependencies, clones JARVIS, and starts all services.", S["body"]))
    story.append(sp(2))

    story.append(StepBox(8, "SSH into your EC2 server", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "ssh -i your-key.pem ubuntu@YOUR_EC2_IP",
    ], W))
    story.append(sp(2))

    story.append(StepBox(9, "Install Docker on the server", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Update packages",
        "sudo apt update && sudo apt upgrade -y",
        "",
        "# Install Docker",
        "curl -fsSL https://get.docker.com -o get-docker.sh",
        "sudo sh get-docker.sh",
        "",
        "# Add ubuntu user to docker group",
        "sudo usermod -aG docker ubuntu",
        "newgrp docker",
        "",
        "# Install Docker Compose",
        "sudo apt install docker-compose-plugin -y",
        "",
        "# Verify",
        "docker --version",
        "docker compose version",
    ], W))
    story.append(sp(2))

    story.append(StepBox(10, "Clone JARVIS codebase", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Clone your repository",
        "git clone https://github.com/syedabrarfff-stack/devops-docker-project.git",
        "cd devops-docker-project",
    ], W))
    story.append(sp(2))

    story.append(StepBox(11, "Create .env on the server", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Create .env directly on server",
        "nano .env",
        "",
        "# Paste all your environment variables",
        "# Save: Ctrl+X → Y → Enter",
        "",
        "# Verify it saved",
        "cat .env | head -5",
    ], W))
    story.append(sp(2))

    story.append(StepBox(12, "Start JARVIS — one command", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Navigate to infrastructure",
        "cd infrastructure",
        "",
        "# Start everything",
        "docker compose up -d",
        "",
        "# Watch services start",
        "docker compose ps",
        "",
        "# Check backend health",
        "curl http://localhost:8000/health",
        "# Expected: {\"status\": \"ok\", \"system\": \"JARVIS\"}",
        "",
        "# Check deep readiness",
        "curl http://localhost:8000/readyz",
    ], W))
    story.append(sp(2))

    story.append(StepBox(13, "Verify all services running", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "docker compose ps",
        "# Expected output:",
        "# jarvis_postgres    running (healthy)",
        "# jarvis_redis       running (healthy)",
        "# jarvis_backend     running (healthy)",
        "# jarvis_frontend    running",
        "# jarvis_nginx       running",
    ], W))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 4
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PhaseHeader("4", "Domain + SSL Setup", "Make JARVIS accessible at your professional domain", ORANGE, W))
    story.append(sp(3))

    story.append(Paragraph("What this phase does: Points your domain to EC2, configures Nginx, and installs free SSL certificate.", S["body"]))
    story.append(sp(2))

    story.append(StepBox(14, "Buy your domain", W))
    story.append(sp(2))
    story.append(Paragraph("Recommended: Namecheap.com — search for aliyarsolutions.com (~$10/year)", S["body"]))
    story.append(sp(2))

    story.append(StepBox(15, "Point domain to EC2 IP", W))
    story.append(sp(2))
    story.append(Paragraph("In Namecheap DNS settings, add these records:", S["body"]))
    dns_data = [
        ["Type", "Host", "Value", "TTL"],
        ["A Record", "@", "YOUR_EC2_IP", "Auto"],
        ["A Record", "www", "YOUR_EC2_IP", "Auto"],
        ["A Record", "api", "YOUR_EC2_IP", "Auto"],
    ]
    t = Table(dns_data, colWidths=[W * 0.2, W * 0.2, W * 0.4, W * 0.2])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_GREY),
        ("TEXTCOLOR", (0, 1), (-1, -1), HexColor("#C8D0E0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [DARK_GREY, NAVY]),
    ]))
    story.append(t)
    story.append(sp(2))
    story.append(Paragraph("Note: DNS propagation takes 5-30 minutes. Test with: ping yourdomain.com", S["note"]))
    story.append(sp(2))

    story.append(StepBox(16, "Install SSL certificate (free — Certbot)", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Install Certbot",
        "sudo apt install certbot python3-certbot-nginx -y",
        "",
        "# Get SSL certificate (replace with your domain)",
        "sudo certbot --nginx -d aliyarsolutions.com -d www.aliyarsolutions.com",
        "",
        "# Follow prompts:",
        "# Enter email address",
        "# Agree to terms: Y",
        "# Share email with EFF: N",
        "",
        "# Certbot automatically configures Nginx for HTTPS",
        "# Certificate auto-renews every 90 days",
        "",
        "# Test renewal",
        "sudo certbot renew --dry-run",
    ], W))
    story.append(sp(2))

    story.append(StepBox(17, "Update Nginx config for your domain", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Edit Nginx config",
        "sudo nano /etc/nginx/conf.d/default.conf",
        "",
        "# OR update infrastructure/nginx/nginx.conf",
        "# Replace: server_name _;",
        "# With:    server_name aliyarsolutions.com www.aliyarsolutions.com;",
        "",
        "# Test config",
        "sudo nginx -t",
        "",
        "# Reload Nginx",
        "sudo nginx -s reload",
        "",
        "# Test HTTPS",
        "curl https://aliyarsolutions.com/health",
    ], W))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 5
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PhaseHeader("5", "CI/CD Automation", "Every git push deploys automatically — zero manual work", GREEN, W))
    story.append(sp(3))

    story.append(Paragraph("What this phase does: Connects GitHub Actions to your EC2 server. Every push to main branch auto-deploys JARVIS.", S["body"]))
    story.append(sp(2))

    story.append(StepBox(18, "Generate SSH deploy key on EC2", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# On your EC2 server",
        "ssh-keygen -t ed25519 -C 'jarvis-deploy' -f ~/.ssh/deploy_key -N ''",
        "",
        "# Add public key to authorized_keys",
        "cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys",
        "",
        "# Copy the PRIVATE key — you need it for GitHub",
        "cat ~/.ssh/deploy_key",
        "# Copy everything including -----BEGIN... and -----END...",
    ], W))
    story.append(sp(2))

    story.append(StepBox(19, "Add secrets to GitHub repository", W))
    story.append(sp(2))
    story.append(Paragraph("Go to: GitHub → Your Repo → Settings → Secrets → Actions → New Repository Secret", S["body"]))
    story.append(sp(1))
    secrets_data = [
        ["Secret Name", "Value"],
        ["EC2_SSH_KEY", "Paste the private key from Step 18"],
        ["EC2_HOST", "Your EC2 public IP or domain"],
        ["EC2_USER", "ubuntu"],
        ["EC2_DEPLOY_PATH", "/home/ubuntu/devops-docker-project"],
        ["SLACK_WEBHOOK_URL", "Your Slack webhook for notifications"],
        ["APP_BASE_URL", "https://aliyarsolutions.com"],
    ]
    t = Table(secrets_data, colWidths=[W * 0.38, W * 0.62])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_GREY),
        ("TEXTCOLOR", (0, 1), (-1, -1), HexColor("#C8D0E0")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [DARK_GREY, NAVY]),
    ]))
    story.append(t)
    story.append(sp(2))

    story.append(StepBox(20, "Create GitHub Actions deploy workflow", W))
    story.append(sp(2))
    story.append(Paragraph("Create .github/workflows/ec2-deploy.yml:", S["body"]))
    story.append(CodeBlock([
        "name: Deploy JARVIS to EC2",
        "on:",
        "  push:",
        "    branches: [main]",
        "jobs:",
        "  deploy:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "      - name: Deploy to EC2",
        "        uses: appleboy/ssh-action@v1.0.0",
        "        with:",
        "          host: ${{ secrets.EC2_HOST }}",
        "          username: ${{ secrets.EC2_USER }}",
        "          key: ${{ secrets.EC2_SSH_KEY }}",
        "          script: |",
        "            cd ${{ secrets.EC2_DEPLOY_PATH }}",
        "            git pull origin main",
        "            cd infrastructure",
        "            docker compose pull",
        "            docker compose up -d --build",
        "            curl -f http://localhost:8000/health",
    ], W))
    story.append(sp(2))

    story.append(StepBox(21, "Test the automation", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# On local machine — make any small change",
        "echo '# deployed' >> README.md",
        "git add . && git commit -m 'test: CI/CD automation'",
        "git push origin main",
        "",
        "# Go to GitHub → Actions tab",
        "# Watch the deployment run automatically",
        "# Green checkmark = success",
        "",
        "# From this point: every push = automatic deploy",
    ], W))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 6
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PhaseHeader("6", "Monitoring + Health", "Real-time visibility into JARVIS operations", HexColor("#9B59B6"), W))
    story.append(sp(3))

    story.append(Paragraph("What this phase does: Sets up Prometheus metrics collection and Grafana dashboards for full operational visibility.", S["body"]))
    story.append(sp(2))

    story.append(StepBox(22, "Add monitoring to Docker Compose", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Add to infrastructure/docker-compose.yml:",
        "",
        "  prometheus:",
        "    image: prom/prometheus:latest",
        "    container_name: jarvis_prometheus",
        "    volumes:",
        "      - ./prometheus.yml:/etc/prometheus/prometheus.yml",
        "    ports:",
        "      - '9090:9090'",
        "    networks:",
        "      - jarvis_net",
        "",
        "  grafana:",
        "    image: grafana/grafana:latest",
        "    container_name: jarvis_grafana",
        "    ports:",
        "      - '3001:3000'",
        "    environment:",
        "      - GF_SECURITY_ADMIN_PASSWORD=yourpassword",
        "    networks:",
        "      - jarvis_net",
    ], W))
    story.append(sp(2))

    story.append(StepBox(23, "Set up automated health alerts", W))
    story.append(sp(2))
    story.append(CodeBlock([
        "# Install Watchtower — auto-pulls new Docker images",
        "docker run -d --name watchtower \\",
        "  -v /var/run/docker.sock:/var/run/docker.sock \\",
        "  containrrr/watchtower \\",
        "  --interval 300",
        "# Checks for updates every 5 minutes",
        "",
        "# Set up cron for health monitoring",
        "crontab -e",
        "# Add: */5 * * * * curl -f http://localhost:8000/health || ...",
        "# This pings health every 5 minutes",
    ], W))
    story.append(sp(2))

    story.append(StepBox(24, "Configure uptime monitoring (free)", W))
    story.append(sp(2))
    story.append(Paragraph("Use UptimeRobot (free) to monitor your domain 24/7 and alert you via Slack/email if down:", S["body"]))
    steps_uptimerobot = [
        "Go to uptimerobot.com — free account",
        "Add Monitor → HTTP(s) → https://aliyarsolutions.com/health",
        "Set interval: every 5 minutes",
        "Add Slack notification → your JARVIS Slack webhook",
        "You will be alerted within 5 minutes of any downtime",
    ]
    for i, step in enumerate(steps_uptimerobot, 1):
        story.append(Paragraph(f"  {i}. {step}", S["bullet"]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # GO LIVE CHECKLIST
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PhaseHeader("✓", "Go-Live Checklist", "Verify everything before your first client", GREEN, W))
    story.append(sp(3))

    checklist = [
        ("Infrastructure", [
            "EC2 running and accessible via SSH",
            "All Docker containers healthy (docker compose ps)",
            "Elastic IP attached (IP never changes)",
            "Security groups configured correctly",
        ]),
        ("Application", [
            "GET /health returns {\"status\": \"ok\"}",
            "GET /readyz returns all subsystems healthy",
            "Frontend loads at http://YOUR_IP:3000",
            "JARVIS dashboard fully functional",
            "Team registry seeded (9 members visible)",
            "Service catalog seeded (30 divisions)",
        ]),
        ("Domain + SSL", [
            "Domain points to EC2 IP",
            "https://yourdomain.com loads correctly",
            "SSL certificate valid (green padlock in browser)",
            "www.yourdomain.com redirects to yourdomain.com",
        ]),
        ("CI/CD", [
            "GitHub Actions workflow runs on push to main",
            "Test deploy completes successfully",
            "Health check passes after deploy",
            "Slack notification received on deploy",
        ]),
        ("Security", [
            ".env file NOT in git repository",
            "All API keys set as environment variables",
            "SSH access only via key (password disabled)",
            "Ports 3000, 8000 blocked externally (Nginx proxies them)",
        ]),
        ("Monitoring", [
            "UptimeRobot monitoring active",
            "Slack alerts configured",
            "Grafana dashboard accessible",
            "Daily briefing job running (check at 07:00)",
        ]),
    ]

    for section, items in checklist:
        story.append(Paragraph(section, S["h3"]))
        for item in items:
            story.append(Paragraph(f"  ☐  {item}", S["bullet"]))
        story.append(sp(1))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # ENTERPRISE UPGRADE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PhaseHeader("→", "Enterprise Upgrade Path", "After first client — migrate to full AWS managed services", ACCENT2, W))
    story.append(sp(3))

    story.append(Paragraph("Once you have revenue, upgrade to the enterprise architecture. All Terraform is already written in infra/terraform/.", S["body"]))
    story.append(sp(2))

    upgrade_data = [
        ["Current (EC2)", "Enterprise (ECS Fargate)", "Benefit"],
        ["EC2 t3.medium", "ECS Fargate tasks", "No server management"],
        ["Docker Compose", "ECS Task Definitions", "Auto-scaling"],
        ["PostgreSQL in Docker", "AWS RDS PostgreSQL", "Auto-backup, multi-AZ"],
        ["Redis in Docker", "AWS ElastiCache", "Managed, highly available"],
        ["Nginx on EC2", "AWS ALB", "Auto-scaling load balancer"],
        ["Certbot SSL", "AWS ACM", "Auto-renewing, zero config"],
        [".env file", "AWS Secrets Manager", "Encrypted, audited access"],
        ["GitHub Actions → SSH", "GitHub Actions → ECR → ECS", "Blue/green zero-downtime"],
        ["~$20/month", "~$130-140/month", "Enterprise grade"],
    ]
    t = Table(upgrade_data, colWidths=[W * 0.32, W * 0.38, W * 0.30])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_GREY),
        ("TEXTCOLOR", (0, 1), (-1, -1), HexColor("#C8D0E0")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.3, NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [DARK_GREY, NAVY]),
        ("TEXTCOLOR", (2, 1), (2, -1), GREEN),
    ]))
    story.append(t)
    story.append(sp(3))

    story.append(Paragraph("Enterprise upgrade command (when ready):", S["h3"]))
    story.append(CodeBlock([
        "cd infra/terraform",
        "terraform init",
        "terraform plan",
        "terraform apply",
        "# Entire enterprise infrastructure provisioned in ~10 minutes",
        "# ECS Fargate + RDS + ElastiCache + ALB + ACM + Secrets Manager",
    ], W))
    story.append(sp(3))

    # Final summary
    story.append(hr(ACCENT))
    story.append(sp(2))
    summary_data = [
        ["Phase", "What You Get", "Time"],
        ["1 — Prepare", "Codebase production-ready", "30 min"],
        ["2 — Terraform", "Full AWS infrastructure automated", "1 hour"],
        ["3 — Deploy", "JARVIS live on EC2", "1 hour"],
        ["4 — Domain + SSL", "Professional HTTPS domain", "1 hour"],
        ["5 — CI/CD", "Zero-touch automated deploys", "1 hour"],
        ["6 — Monitoring", "24/7 operational visibility", "30 min"],
        ["Total", "Fully live JARVIS production system", "~5-6 hours"],
    ]
    t = Table(summary_data, colWidths=[W * 0.28, W * 0.50, W * 0.22])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), GREEN),
        ("TEXTCOLOR", (0, -1), (-1, -1), NAVY),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -2), DARK_GREY),
        ("TEXTCOLOR", (0, 1), (-1, -2), HexColor("#C8D0E0")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [DARK_GREY, NAVY]),
    ]))
    story.append(t)
    story.append(sp(2))
    story.append(Paragraph("The infrastructure is built. The code is ready. Execute these 6 phases and JARVIS is live. — JARVIS Operations", S["note"]))

    # ── Page template ─────────────────────────────────────────────────────────
    def on_page(canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setFillColor(NAVY)
            canvas.rect(0, A4[1] - 22, A4[0], 22, fill=1, stroke=0)
            canvas.setFillColor(ACCENT2)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(20 * mm, A4[1] - 14, "JARVIS — Aliyar Solutions")
            canvas.setFillColor(MID_GREY)
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 14, "Complete Deployment Guide")
            canvas.setFillColor(DARK_GREY)
            canvas.rect(0, 0, A4[0], 16, fill=1, stroke=0)
            canvas.setFillColor(MID_GREY)
            canvas.setFont("Helvetica", 7)
            canvas.drawString(20 * mm, 5, "Confidential — Aliyar Solutions Internal Document")
            canvas.drawRightString(A4[0] - 20 * mm, 5, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  PDF written to: {OUTPUT}")


if __name__ == "__main__":
    build()
