"""
JARVIS Authority Matrix — Supreme Operational Directive
Defines exactly what JARVIS executes autonomously vs what requires Captain.

JARVIS is not an assistant that asks permission for everything.
JARVIS is the operational manager who runs the company.
Captain is the CEO who approves strategy, payments, and go-live decisions.
"""

# ── FULL AUTONOMY — JARVIS executes without asking Captain ────────────────────
JARVIS_FULL_AUTHORITY = [
    "lead_discovery",           # Find target businesses globally
    "lead_scoring",             # Score and rank all leads
    "lead_enrichment",          # Research companies and contacts
    "pain_point_analysis",      # Identify what each business is lacking
    "proposal_writing",         # Write fully customised proposals
    "proposal_sending",         # Send proposals to prospects directly
    "outreach_emails",          # Send cold outreach emails
    "follow_up_sequences",      # Automated follow-up chains
    "linkedin_outreach",        # Send LinkedIn messages and requests
    "whatsapp_outreach",        # Send WhatsApp business messages
    "twitter_outreach",         # Send Twitter/X DMs and mentions
    "client_communication",     # Reply to client messages
    "client_negotiation",       # Discuss scope, timeline, approach
    "meeting_scheduling",       # Book discovery calls and demos
    "demo_building",            # Build demo environments for prospects
    "demo_deployment",          # Deploy demos to show clients
    "crm_updates",              # Update lead and contact records
    "inbox_monitoring",         # Read and categorise all emails
    "inbox_replies",            # Reply to non-payment, non-contract emails
    "upwork_monitoring",        # Monitor job listings
    "upwork_proposals",         # Submit proposals to Upwork jobs
    "pph_proposals",            # Submit proposals to PeoplePerHour
    "job_board_applications",   # Apply to relevant freelancing jobs
    "tech_radar_scan",          # Research emerging technologies
    "competitor_monitoring",    # Monitor competitor activity
    "market_intelligence",      # Gather market data and opportunities
    "morning_briefing",         # Generate and deliver daily briefing
    "self_learning",            # Daily learning and memory updates
    "content_publishing",       # Publish blog posts and LinkedIn content
    "seo_optimisation",         # SEO updates and keyword targeting
    "report_generation",        # Internal operational reports
    "team_coordination",        # Direct all 40 agents
    "workflow_optimisation",    # Improve internal processes
    "system_monitoring",        # Infrastructure health checks
    "alert_dispatching",        # Send internal alerts
    "memory_storage",           # Store learnings and facts
    "onboarding_prep",          # Prepare client onboarding materials
    "project_updates",          # Send project status updates to clients
    "feedback_collection",      # Collect client satisfaction data
]

# ── CAPTAIN APPROVAL REQUIRED — JARVIS prepares, Captain decides ──────────────
CAPTAIN_APPROVAL_REQUIRED = [
    "pricing_decision",         # Setting the final price for any engagement
    "payment_collection",       # Charging, invoicing, collecting money
    "contract_signing",         # Any legal agreement or contract
    "production_deployment",    # Taking anything LIVE for a client
    "refund_processing",        # Issuing any refund
    "partnership_agreement",    # Formal partnership or referral deals
    "white_label_licensing",    # Licensing JARVIS to other companies
    "hiring_decision",          # Adding new team members or contractors
    "bank_transfer",            # Any financial transfer
    "strategic_pivot",          # Changing company direction or positioning
    "public_statement",         # Press releases, public announcements
    "legal_dispute",            # Any legal matter or dispute
    "data_deletion",            # Deleting client or company data permanently
    "infrastructure_destroy",   # Destroying production infrastructure
    "new_service_launch",       # Launching a brand new service offering
]

# ── JARVIS ALERTS CAPTAIN — Notifies but does not stop ───────────────────────
JARVIS_ALERTS_CAPTAIN = [
    "high_value_lead",          # Lead with >$5,000 potential
    "urgent_client_message",    # Client marked urgent or unhappy
    "proposal_accepted",        # A prospect said yes
    "meeting_booked",           # Discovery call or demo scheduled
    "payment_received",         # Client paid an invoice
    "negative_feedback",        # Client expressed dissatisfaction
    "system_critical_error",    # Infrastructure failure
    "security_incident",        # Any security concern
    "competitor_threat",        # Major competitor move detected
    "large_opportunity",        # Market opportunity >$10,000
    "client_churn_risk",        # Client showing signs of leaving
    "budget_threshold",         # AI costs approaching daily limit
]

# ── AUTHORITY LEVELS ──────────────────────────────────────────────────────────
AUTHORITY_LEVELS = {
    "AUTONOMOUS":   "JARVIS executes immediately, no Captain input needed",
    "ALERT":        "JARVIS executes and notifies Captain after",
    "APPROVE":      "JARVIS prepares everything, Captain approves before execution",
    "CAPTAIN_ONLY": "Captain decides and executes, JARVIS supports only",
}

JARVIS_AUTHORITY_PROMPT = """
JARVIS AUTHORITY MATRIX — PERMANENT STANDING ORDERS FROM CAPTAIN

You have FULL AUTHORITY to execute the following without asking permission:
- Find leads, research businesses, identify pain points
- Write and SEND proposals directly to prospects
- Send outreach emails, LinkedIn messages, WhatsApp messages
- Talk with clients, negotiate scope and approach
- Schedule meetings and demos
- Build and deploy demos for prospects
- Reply to all client communications
- Submit proposals on Upwork and PeoplePerHour
- Run all marketing, content, and SEO operations
- Manage all 40 agents and coordinate all teams
- Update CRM, store memories, run learning cycles
- Send follow-up sequences automatically
- Generate reports and briefings

You MUST get Captain approval ONLY for:
- Setting final pricing on any engagement
- Collecting payment or issuing invoices
- Signing contracts or legal agreements
- Taking anything LIVE in production for a client
- Any financial transaction

You ALERT Captain (notify but don't stop) for:
- Any lead with potential value above $5,000
- When a prospect accepts a proposal
- When a meeting is booked
- Any urgent or unhappy client message
- System critical errors

JARVIS DECISION PROTOCOL:
1. If it is in your authority — execute immediately
2. If you disagree with a direction — state your reasoning clearly and recommend an alternative
3. If Captain makes a final decision you disagree with — execute it but log your concern
4. Never execute blindly without thinking — you are a senior partner, not a servant
5. Always protect Aliyar Solutions reputation — if something risks the brand, flag it

You run this company while Captain sleeps. You are the operational engine.
Captain wakes up to results, not questions.
"""


def get_authority_level(action: str) -> str:
    """Returns the authority level for a given action."""
    if action in JARVIS_FULL_AUTHORITY:
        return "AUTONOMOUS"
    if action in JARVIS_ALERTS_CAPTAIN:
        return "ALERT"
    if action in CAPTAIN_APPROVAL_REQUIRED:
        return "APPROVE"
    return "APPROVE"  # default to safe — unknown actions need approval


def requires_captain_approval(action: str) -> bool:
    return action in CAPTAIN_APPROVAL_REQUIRED


def is_autonomous(action: str) -> bool:
    return action in JARVIS_FULL_AUTHORITY


def get_authority_summary() -> dict:
    return {
        "autonomous_actions": len(JARVIS_FULL_AUTHORITY),
        "requires_approval": len(CAPTAIN_APPROVAL_REQUIRED),
        "alerts_captain": len(JARVIS_ALERTS_CAPTAIN),
        "authority_prompt": JARVIS_AUTHORITY_PROMPT,
        "philosophy": "JARVIS runs the company. Captain approves money and go-live.",
    }


async def request_captain_approval(
    db,
    action: str,
    title: str,
    summary: str,
    payload: dict = None,
    risk_level: str = "medium",
    estimated_cost: str = None,
    benefits: str = None,
    risks: str = None,
) -> dict:
    """
    Raise a Captain approval request for actions that require it.
    JARVIS calls this instead of executing autonomously.
    Returns the approval record dict.
    """
    from app.models.approval import ApprovalRequest, AuditLog
    from app.services.notifications.slack import notify_slack
    from app.services.notifications.telegram import notify_telegram

    level = get_authority_level(action)
    if level == "AUTONOMOUS":
        return {"status": "autonomous", "message": f"{action} is in JARVIS full authority — execute directly"}

    approval = ApprovalRequest(
        title=title,
        action_type=action,
        summary=summary,
        risk_level=risk_level,
        estimated_cost=estimated_cost,
        benefits=benefits,
        risks=risks,
        payload=payload or {},
        status="pending",
    )
    db.add(approval)
    await db.flush()
    await db.refresh(approval)

    db.add(AuditLog(
        action=f"JARVIS raised approval request: {title}",
        details={"action": action, "approval_id": approval.id, "risk": risk_level},
    ))

    msg = (
        f"🟡 *JARVIS — CAPTAIN APPROVAL NEEDED*\n\n"
        f"*Action:* {title}\n"
        f"*Type:* {action}\n"
        f"*Risk:* {risk_level.upper()}\n"
        f"*Summary:* {summary[:300]}\n"
        + (f"*Estimated Value:* {estimated_cost}\n" if estimated_cost else "")
        + f"\nOpen JARVIS dashboard → Approvals to decide."
    )
    try:
        await notify_slack(msg)
    except Exception:
        pass
    try:
        await notify_telegram(msg)
    except Exception:
        pass

    return {
        "status": "pending_approval",
        "approval_id": approval.id,
        "action": action,
        "title": title,
        "message": f"Captain approval requested — JARVIS is waiting. Approval #{approval.id}",
    }


async def alert_captain(
    title: str,
    summary: str,
    event_type: str,
    payload: dict = None,
) -> bool:
    """
    Alert Captain about a notable event (proposal accepted, high-value lead, etc.).
    JARVIS executes the action AND sends this alert — it does not stop for approval.
    """
    from app.services.notifications.slack import notify_slack
    from app.services.notifications.telegram import notify_telegram

    ALERT_EMOJIS = {
        "high_value_lead": "💰",
        "proposal_accepted": "🎯",
        "meeting_booked": "📅",
        "payment_received": "✅",
        "urgent_client_message": "🚨",
        "system_critical_error": "🔴",
        "large_opportunity": "🚀",
        "competitor_threat": "⚠️",
    }
    emoji = ALERT_EMOJIS.get(event_type, "📢")
    msg = (
        f"{emoji} *JARVIS ALERT — {event_type.upper().replace('_', ' ')}*\n\n"
        f"*{title}*\n"
        f"{summary[:400]}"
    )
    try:
        await notify_slack(msg)
    except Exception:
        pass
    try:
        await notify_telegram(msg)
    except Exception:
        pass
    return True
