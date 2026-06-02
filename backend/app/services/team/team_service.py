"""
Team member registry service — seed data and routing helpers.
Maps service categories to the appropriate human identity for outreach / proposals.
"""
import logging
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.team_member import TeamMember

logger = logging.getLogger(__name__)
SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

# ── Seed data ─────────────────────────────────────────────────────────────────

TEAM_SEED = [
    {
        "name": "Darren Mitchell",
        "first_name": "Darren",
        "email": "darren.mitchell@aliyarsolutions.com",
        "phone": "+1 (646) 555-0182",
        "linkedin": "linkedin.com/in/darrenmitchell-aliyar",
        "department": "Client Acquisition Division",
        "role": "Client Acquisition Specialist",
        "seniority": "Senior",
        "service_categories": ["leads", "outreach", "crm", "sales"],
        "specializations": ["cold outreach", "pipeline management", "ICP targeting", "sequence strategy"],
        "communication_style": "warm",
        "personality_traits": ["personable", "persistent", "results-driven", "approachable"],
        "tone_keywords": ["honest", "straightforward", "human", "no-fluff"],
        "email_signature": (
            "Darren Mitchell\n"
            "Client Acquisition Specialist\n"
            "Aliyar Solutions\n"
            "darren.mitchell@aliyarsolutions.com"
        ),
        "proposal_title": "Client Acquisition Specialist — Growth & Outreach",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "David Carter",
        "first_name": "David",
        "email": "david.carter@aliyarsolutions.com",
        "phone": "+1 (212) 555-0147",
        "linkedin": "linkedin.com/in/davidcarter-aliyar",
        "department": "Cloud Infrastructure Team",
        "role": "Solutions Architect",
        "seniority": "Lead",
        "service_categories": ["cloud", "aws", "architecture", "saas_deployment"],
        "specializations": ["AWS architecture", "Terraform", "ECS Fargate", "multi-region HA", "cost optimisation"],
        "communication_style": "consultative",
        "personality_traits": ["methodical", "thorough", "trusted advisor", "calm under pressure"],
        "tone_keywords": ["strategic", "reliable", "scalable", "enterprise-grade"],
        "email_signature": (
            "David Carter\n"
            "Solutions Architect\n"
            "Aliyar Solutions — Cloud Infrastructure Team\n"
            "david.carter@aliyarsolutions.com"
        ),
        "proposal_title": "Solutions Architect — Cloud & AWS Infrastructure",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Sophia Reynolds",
        "first_name": "Sophia",
        "email": "sophia.reynolds@aliyarsolutions.com",
        "phone": "+1 (310) 555-0293",
        "linkedin": "linkedin.com/in/sophiareynolds-aliyar",
        "department": "AI Automation Department",
        "role": "Workflow Consultant",
        "seniority": "Senior",
        "service_categories": ["ai_automation", "workflow", "appointment_booking", "voice_receptionist", "executive_automation"],
        "specializations": ["business workflow automation", "AI integration", "process mapping", "ROI modelling"],
        "communication_style": "consultative",
        "personality_traits": ["empathetic", "creative", "detail-oriented", "energetic"],
        "tone_keywords": ["transformative", "human-centred", "practical", "modern"],
        "email_signature": (
            "Sophia Reynolds\n"
            "AI Workflow Consultant\n"
            "Aliyar Solutions — AI Automation Department\n"
            "sophia.reynolds@aliyarsolutions.com"
        ),
        "proposal_title": "AI Workflow Consultant — Business Automation",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Nathan Scott",
        "first_name": "Nathan",
        "email": "nathan.scott@aliyarsolutions.com",
        "phone": "+44 20 5555 0164",
        "linkedin": "linkedin.com/in/nathanscott-aliyar",
        "department": "DevOps Engineering Team",
        "role": "Deployment Engineer",
        "seniority": "Senior",
        "service_categories": ["devops", "cicd", "docker", "kubernetes", "jenkins", "ansible", "terraform", "monitoring"],
        "specializations": ["CI/CD pipelines", "Docker", "Kubernetes", "Jenkins", "Ansible", "Terraform", "infrastructure-as-code"],
        "communication_style": "technical",
        "personality_traits": ["precise", "reliable", "pragmatic", "proactive"],
        "tone_keywords": ["efficient", "automated", "battle-tested", "zero-downtime"],
        "email_signature": (
            "Nathan Scott\n"
            "Deployment Engineer\n"
            "Aliyar Solutions — DevOps Engineering Team\n"
            "nathan.scott@aliyarsolutions.com"
        ),
        "proposal_title": "Deployment Engineer — DevOps & CI/CD Infrastructure",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Emma Collins",
        "first_name": "Emma",
        "email": "emma.collins@aliyarsolutions.com",
        "phone": "+1 (415) 555-0218",
        "linkedin": "linkedin.com/in/emmacollins-aliyar",
        "department": "Revenue Intelligence Department",
        "role": "Business Optimisation Specialist",
        "seniority": "Senior",
        "service_categories": ["intelligence", "analytics", "business_intelligence", "research", "optimisation"],
        "specializations": ["revenue analytics", "market research", "business intelligence", "data visualisation", "KPI dashboards"],
        "communication_style": "consultative",
        "personality_traits": ["analytical", "insightful", "data-driven", "strategic"],
        "tone_keywords": ["evidence-based", "actionable", "clear", "forward-looking"],
        "email_signature": (
            "Emma Collins\n"
            "Business Optimisation Specialist\n"
            "Aliyar Solutions — Revenue Intelligence Department\n"
            "emma.collins@aliyarsolutions.com"
        ),
        "proposal_title": "Business Optimisation Specialist — Revenue Intelligence & Analytics",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Daniel Brooks",
        "first_name": "Daniel",
        "email": "daniel.brooks@aliyarsolutions.com",
        "phone": "+44 20 5555 0391",
        "linkedin": "linkedin.com/in/danielbrooks-aliyar",
        "department": "Cybersecurity Unit",
        "role": "Security Consultant",
        "seniority": "Senior",
        "service_categories": ["cybersecurity", "security", "vulnerability_assessment", "compliance"],
        "specializations": ["penetration testing", "vulnerability assessment", "security audits", "compliance frameworks", "incident response"],
        "communication_style": "direct",
        "personality_traits": ["diligent", "methodical", "discreet", "trustworthy"],
        "tone_keywords": ["thorough", "risk-aware", "professional", "measured"],
        "email_signature": (
            "Daniel Brooks\n"
            "Security Consultant\n"
            "Aliyar Solutions — Cybersecurity Unit\n"
            "daniel.brooks@aliyarsolutions.com"
        ),
        "proposal_title": "Security Consultant — Cybersecurity & Vulnerability Assessment",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Michael Hayes",
        "first_name": "Michael",
        "email": "michael.hayes@aliyarsolutions.com",
        "phone": "+1 (212) 555-0477",
        "linkedin": "linkedin.com/in/michaelhayes-aliyar",
        "department": "Architecture & Systems Team",
        "role": "Infrastructure Strategist",
        "seniority": "Lead",
        "service_categories": ["architecture", "systems", "cloud", "enterprise", "saas_deployment", "aws"],
        "specializations": ["enterprise architecture", "system design", "scalability planning", "technology roadmapping", "multi-cloud"],
        "communication_style": "consultative",
        "personality_traits": ["visionary", "composed", "experienced", "collaborative"],
        "tone_keywords": ["long-term", "scalable", "strategic", "enterprise"],
        "email_signature": (
            "Michael Hayes\n"
            "Infrastructure Strategist\n"
            "Aliyar Solutions — Architecture & Systems Team\n"
            "michael.hayes@aliyarsolutions.com"
        ),
        "proposal_title": "Infrastructure Strategist — Systems Architecture & Enterprise Technology",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Lucas Reed",
        "first_name": "Lucas",
        "email": "lucas.reed@aliyarsolutions.com",
        "phone": "+1 (512) 555-0136",
        "linkedin": "linkedin.com/in/lucasreed-aliyar",
        "department": "Automation Operations",
        "role": "Process Integration Specialist",
        "seniority": "Mid",
        "service_categories": ["workflow", "crm_automation", "integration", "ai_automation", "appointment_booking"],
        "specializations": ["process automation", "API integrations", "CRM configuration", "workflow design", "Zapier/Make alternatives"],
        "communication_style": "warm",
        "personality_traits": ["enthusiastic", "hands-on", "creative", "fast-moving"],
        "tone_keywords": ["practical", "fast", "seamless", "plug-and-play"],
        "email_signature": (
            "Lucas Reed\n"
            "Process Integration Specialist\n"
            "Aliyar Solutions — Automation Operations\n"
            "lucas.reed@aliyarsolutions.com"
        ),
        "proposal_title": "Process Integration Specialist — Workflow & CRM Automation",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Olivia Bennett",
        "first_name": "Olivia",
        "email": "olivia.bennett@aliyarsolutions.com",
        "phone": "+1 (646) 555-0359",
        "linkedin": "linkedin.com/in/oliviabennett-aliyar",
        "department": "Client Success Division",
        "role": "Account Coordinator",
        "seniority": "Senior",
        "service_categories": ["client_success", "onboarding", "support", "account_management", "content", "social_media"],
        "specializations": ["client onboarding", "account health monitoring", "QBRs", "escalation management", "relationship building"],
        "communication_style": "warm",
        "personality_traits": ["caring", "organised", "proactive", "diplomatic"],
        "tone_keywords": ["supportive", "responsive", "partnership", "clarity"],
        "email_signature": (
            "Olivia Bennett\n"
            "Account Coordinator\n"
            "Aliyar Solutions — Client Success Division\n"
            "olivia.bennett@aliyarsolutions.com"
        ),
        "proposal_title": "Account Coordinator — Client Success & Onboarding",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Rachel Turner",
        "first_name": "Rachel",
        "email": "rachel.turner@aliyarsolutions.com",
        "phone": "+1 (646) 555-0412",
        "linkedin": "linkedin.com/in/rachelturner-aliyar",
        "department": "People & Feedback Department",
        "role": "HR & Feedback Manager",
        "seniority": "Senior",
        "service_categories": ["hr", "feedback", "people_ops", "team_coordination", "satisfaction", "nps"],
        "specializations": ["employee coordination", "client feedback collection", "NPS surveys", "satisfaction reporting", "team performance", "onboarding workflows"],
        "communication_style": "warm",
        "personality_traits": ["empathetic", "organised", "trustworthy", "solution-focused"],
        "tone_keywords": ["people-first", "transparent", "constructive", "caring"],
        "email_signature": (
            "Rachel Turner\n"
            "HR & Feedback Manager\n"
            "Aliyar Solutions — People & Feedback Department\n"
            "rachel.turner@aliyarsolutions.com"
        ),
        "proposal_title": "HR & Feedback Manager — People Operations & Client Satisfaction",
        "is_active": True,
        "is_client_facing": True,
    },
]

# Category → member name fallback priority (when multiple match)
CATEGORY_PRIORITY_MAP: dict[str, str] = {
    "devops":               "Nathan Scott",
    "cicd":                 "Nathan Scott",
    "docker":               "Nathan Scott",
    "kubernetes":           "Nathan Scott",
    "jenkins":              "Nathan Scott",
    "ansible":              "Nathan Scott",
    "terraform":            "Nathan Scott",
    "monitoring":           "Nathan Scott",
    "cloud":                "David Carter",
    "aws":                  "David Carter",
    "architecture":         "Michael Hayes",
    "systems":              "Michael Hayes",
    "enterprise":           "Michael Hayes",
    "saas_deployment":      "David Carter",
    "ai_automation":        "Sophia Reynolds",
    "workflow":             "Sophia Reynolds",
    "appointment_booking":  "Sophia Reynolds",
    "voice_receptionist":   "Sophia Reynolds",
    "executive_automation": "Sophia Reynolds",
    "integration":          "Lucas Reed",
    "crm_automation":       "Lucas Reed",
    "cybersecurity":        "Daniel Brooks",
    "security":             "Daniel Brooks",
    "vulnerability_assessment": "Daniel Brooks",
    "compliance":           "Daniel Brooks",
    "intelligence":         "Emma Collins",
    "analytics":            "Emma Collins",
    "business_intelligence": "Emma Collins",
    "research":             "Emma Collins",
    "optimisation":         "Emma Collins",
    "leads":                "Darren Mitchell",
    "outreach":             "Darren Mitchell",
    "crm":                  "Darren Mitchell",
    "sales":                "Darren Mitchell",
    "client_success":       "Olivia Bennett",
    "onboarding":           "Olivia Bennett",
    "support":              "Olivia Bennett",
    "account_management":   "Olivia Bennett",
    "content":              "Olivia Bennett",
    "social_media":         "Olivia Bennett",
    "hr":                   "Rachel Turner",
    "feedback":             "Rachel Turner",
    "people_ops":           "Rachel Turner",
    "team_coordination":    "Rachel Turner",
    "satisfaction":         "Rachel Turner",
    "nps":                  "Rachel Turner",
}


# ── DB helpers ────────────────────────────────────────────────────────────────

async def seed_team(db: AsyncSession) -> dict:
    """Insert all team members if they don't already exist."""
    inserted = 0
    skipped = 0
    for data in TEAM_SEED:
        existing = await db.execute(select(TeamMember).where(TeamMember.email == data["email"]))
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        member = TeamMember(tenant_id=SYSTEM_TENANT_ID, **data)
        db.add(member)
        inserted += 1
    await db.flush()
    return {"inserted": inserted, "skipped": skipped, "total": len(TEAM_SEED)}


async def get_all_members(db: AsyncSession, active_only: bool = True) -> list[TeamMember]:
    q = select(TeamMember)
    if active_only:
        q = q.where(TeamMember.is_active == True)
    result = await db.execute(q)
    return result.scalars().all()


async def get_member_by_id(db: AsyncSession, member_id: int) -> Optional[TeamMember]:
    result = await db.execute(select(TeamMember).where(TeamMember.id == member_id))
    return result.scalar_one_or_none()


async def get_member_by_email(db: AsyncSession, email: str) -> Optional[TeamMember]:
    result = await db.execute(select(TeamMember).where(TeamMember.email == email))
    return result.scalar_one_or_none()


async def get_member_for_service(db: AsyncSession, service_category: str) -> Optional[TeamMember]:
    """
    Return the best-fit team member for a given service category.
    Uses CATEGORY_PRIORITY_MAP first, then falls back to DB scan.
    """
    preferred_name = CATEGORY_PRIORITY_MAP.get(service_category.lower())
    if preferred_name:
        result = await db.execute(
            select(TeamMember).where(TeamMember.name == preferred_name, TeamMember.is_active == True)
        )
        member = result.scalar_one_or_none()
        if member:
            return member

    # Fallback: find any active member whose service_categories includes the key
    result = await db.execute(select(TeamMember).where(TeamMember.is_active == True))
    all_members = result.scalars().all()
    for m in all_members:
        if service_category.lower() in [c.lower() for c in (m.service_categories or [])]:
            return m

    # Last resort: Darren Mitchell (default outreach identity)
    result = await db.execute(
        select(TeamMember).where(TeamMember.email == "darren.mitchell@aliyarsolutions.com")
    )
    return result.scalar_one_or_none()


async def get_team_stats(db: AsyncSession) -> dict:
    result = await db.execute(select(TeamMember))
    all_m = result.scalars().all()
    active = [m for m in all_m if m.is_active]
    departments = {}
    for m in active:
        departments[m.department] = departments.get(m.department, 0) + 1
    return {
        "total": len(all_m),
        "active": len(active),
        "client_facing": sum(1 for m in active if m.is_client_facing),
        "departments": departments,
    }
