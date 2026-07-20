"""AXIOM commercial operating model.

AXIOM is the client-facing commercial architecture. AIONX remains the internal
intelligence/control-plane name. This module keeps the 25 service departments,
managers, consultants, gateways, diagnosis rules, and escalation doctrine in one
canonical source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


BRAND = {
    "commercial_name": "AXIOM",
    "internal_engine": "AIONX",
    "positioning": "Operational intelligence as integrated business infrastructure",
    "client_visibility": "Clients see diagnosis, outcomes, dashboards, and recommendations - not internal departments.",
}


OPERATING_LAYERS = [
    {"layer": 1, "name": "Captain", "function": "Apex authority, veto, finance, strategic pivots."},
    {"layer": 2, "name": "JARVIS Supreme Core", "function": "Routes work, monitors all departments, controls approvals."},
    {"layer": 3, "name": "Soul", "function": "Consciousness, values, heart, vision, offers, upgrade learning."},
    {"layer": 4, "name": "Council", "function": "Eight-member strategic brain reviewing milestone and risk escalations."},
    {"layer": 5, "name": "25 Department Managers", "function": "One accountable manager per service department."},
    {"layer": 6, "name": "25 Specialized Consultants", "function": "One expert consultant per department executing and reporting milestones."},
    {"layer": 7, "name": "Operational Systems", "function": "Scheduler, memory, CRM, GitHub, notifications, AI router, cost and health monitors."},
]


COMMERCIAL_GATEWAYS = [
    {
        "code": "AXIOM_OUTREACH",
        "name": "AXIOM OUTREACH",
        "entry_point": "Build and diagnose the client's revenue engine.",
        "visible_dashboard": ["pipeline", "outreach performance", "lead quality", "revenue trajectory"],
        "success_metric": "Revenue growth",
        "retainer_range": "$18K-$35K/month",
        "capabilities": ["Lead Intelligence", "Outreach Infrastructure", "CRM", "Sales Forecasting", "Executive Briefings", "Analytics"],
    },
    {
        "code": "AXIOM_CLOUDOPS",
        "name": "AXIOM CLOUDOPS",
        "entry_point": "Audit, optimize, and govern the client's infrastructure.",
        "visible_dashboard": ["cost before/after", "uptime", "deployment velocity", "security score"],
        "success_metric": "Cost reduction and reliability improvement",
        "retainer_range": "$25K-$50K/month",
        "capabilities": ["AWS Architecture", "Terraform", "CI/CD", "Kubernetes", "Monitoring", "Security", "Compliance"],
    },
    {
        "code": "AXIOM_COUNCIL",
        "name": "AXIOM COUNCIL",
        "entry_point": "Strategic intelligence partner for executives and boards.",
        "visible_dashboard": ["quarterly briefing", "competitive landscape", "forecast", "growth recommendations"],
        "success_metric": "Strategic clarity and growth trajectory",
        "retainer_range": "$30K-$75K/month",
        "capabilities": ["Business Intelligence", "Market Research", "Financial Forecasting", "Executive Briefings", "Competitive Intelligence"],
    },
]


AXIOM_DEPARTMENTS = [
    {"number": 1, "code": "AXIOM_OUTREACH", "name": "AXIOM OUTREACH", "group": "Revenue & Sales", "manager": "Darren Mitchell", "consultant": "Alex Thompson", "service": "AI lead generation, cold email, 48/day cap", "gateway": "AXIOM_OUTREACH"},
    {"number": 2, "code": "AXIOM_PROPOSAL", "name": "AXIOM PROPOSAL", "group": "Revenue & Sales", "manager": "Darren Mitchell", "consultant": "Claire Warren", "service": "Proposal generation and closing engine", "gateway": "AXIOM_OUTREACH"},
    {"number": 3, "code": "AXIOM_CRM", "name": "AXIOM CRM", "group": "Revenue & Sales", "manager": "Emma Collins", "consultant": "James Foster", "service": "CRM architecture and sales automation", "gateway": "AXIOM_OUTREACH"},
    {"number": 4, "code": "AXIOM_AGENTS", "name": "AXIOM AGENTS", "group": "AI Automation", "manager": "Sophia Reynolds", "consultant": "Marcus Patel", "service": "Custom multi-agent AI systems", "gateway": "AXIOM_COUNCIL"},
    {"number": 5, "code": "AXIOM_WORKFLOWS", "name": "AXIOM WORKFLOWS", "group": "AI Automation", "manager": "Sophia Reynolds", "consultant": "Rachel Kim", "service": "Business workflow automation", "gateway": "AXIOM_OUTREACH"},
    {"number": 6, "code": "AXIOM_VOICE", "name": "AXIOM VOICE", "group": "AI Automation", "manager": "Lucas Reed", "consultant": "Daniel Osei", "service": "Voice receptionist and appointment booking", "gateway": "AXIOM_OUTREACH"},
    {"number": 7, "code": "AXIOM_BRIEF", "name": "AXIOM BRIEF", "group": "AI Automation", "manager": "Olivia Bennett", "consultant": "Sara Hassan", "service": "Executive AI briefing and daily intelligence", "gateway": "AXIOM_COUNCIL"},
    {"number": 8, "code": "AXIOM_CLOUD_OPS", "name": "AXIOM CLOUD OPS", "group": "Cloud & DevOps", "manager": "David Carter", "consultant": "Tom Bradley", "service": "AWS architecture and managed cloud", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 9, "code": "AXIOM_TERRAFORM", "name": "AXIOM TERRAFORM", "group": "Cloud & DevOps", "manager": "Nathan Scott", "consultant": "Priya Sharma", "service": "Infrastructure as code", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 10, "code": "AXIOM_KUBERNETES", "name": "AXIOM KUBERNETES", "group": "Cloud & DevOps", "manager": "Nathan Scott", "consultant": "Carlos Rivera", "service": "Container orchestration and scaling", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 11, "code": "AXIOM_CICD", "name": "AXIOM CICD", "group": "Cloud & DevOps", "manager": "Nathan Scott", "consultant": "Ben Adeyemi", "service": "CI/CD pipeline engineering", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 12, "code": "AXIOM_COST_OPT", "name": "AXIOM COST OPT", "group": "Cloud & DevOps", "manager": "Michael Hayes", "consultant": "Lin Zhao", "service": "Cloud cost optimization with savings target", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 13, "code": "AXIOM_SECURITY", "name": "AXIOM SECURITY", "group": "Security & Compliance", "manager": "Daniel Brooks", "consultant": "Kate Morrison", "service": "Cybersecurity operations and hardening", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 14, "code": "AXIOM_THREATS", "name": "AXIOM THREATS", "group": "Security & Compliance", "manager": "Daniel Brooks", "consultant": "Rajan Nair", "service": "Managed SOC and threat detection", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 15, "code": "AXIOM_VULN", "name": "AXIOM VULN", "group": "Security & Compliance", "manager": "Daniel Brooks", "consultant": "Fatima Al-Rashid", "service": "Vulnerability assessment, SOC2, HIPAA", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 16, "code": "AXIOM_INTEL", "name": "AXIOM INTEL", "group": "Intelligence & Data", "manager": "Emma Collins", "consultant": "Wei Chen", "service": "Business intelligence and market analysis", "gateway": "AXIOM_COUNCIL"},
    {"number": 17, "code": "AXIOM_DATA_BRAIN", "name": "AXIOM DATA BRAIN", "group": "Intelligence & Data", "manager": "Emma Collins", "consultant": "Aisha Okonkwo", "service": "Data platform and analytics infrastructure", "gateway": "AXIOM_COUNCIL"},
    {"number": 18, "code": "AXIOM_FORECAST", "name": "AXIOM FORECAST", "group": "Intelligence & Data", "manager": "Michael Hayes", "consultant": "Ivan Petrov", "service": "AI-powered predictive forecasting", "gateway": "AXIOM_COUNCIL"},
    {"number": 19, "code": "AXIOM_MONITOR", "name": "AXIOM MONITOR", "group": "Intelligence & Data", "manager": "Michael Hayes", "consultant": "Ana Rodrigues", "service": "Infrastructure monitoring and observability", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 20, "code": "AXIOM_WEB_DEV", "name": "AXIOM WEB DEV", "group": "Digital Products", "manager": "Lucas Reed", "consultant": "Noah Williams", "service": "Web apps, portals, dashboards", "gateway": "AXIOM_COUNCIL"},
    {"number": 21, "code": "AXIOM_SCOUT", "name": "AXIOM SCOUT", "group": "Digital Products", "manager": "Darren Mitchell", "consultant": "Lena Muller", "service": "Lead discovery and market intelligence", "gateway": "AXIOM_OUTREACH"},
    {"number": 22, "code": "AXIOM_COMMAND", "name": "AXIOM COMMAND", "group": "Digital Products", "manager": "David Carter", "consultant": "Omar Abdullah", "service": "Full-stack enterprise operating system package", "gateway": "AXIOM_COUNCIL"},
    {"number": 23, "code": "AXIOM_NEXUS", "name": "AXIOM NEXUS", "group": "Legendary 3", "manager": "David Carter", "consultant": "Elise Laurent", "service": "Operational Command Center from infrastructure to business outcomes", "gateway": "AXIOM_COUNCIL"},
    {"number": 24, "code": "AXIOM_PREDICT", "name": "AXIOM PREDICT", "group": "Legendary 3", "manager": "Michael Hayes", "consultant": "Arjun Mehta", "service": "Predictive infrastructure intelligence and early failure forecasting", "gateway": "AXIOM_CLOUDOPS"},
    {"number": 25, "code": "AXIOM_SHIELD", "name": "AXIOM SHIELD", "group": "Legendary 3", "manager": "Daniel Brooks", "consultant": "Zara Blackwood", "service": "Dynamic infrastructure resilience and autonomous threat response", "gateway": "AXIOM_CLOUDOPS"},
]


@dataclass(frozen=True)
class DiagnosisSignal:
    key: str
    label: str
    gateways: tuple[str, ...]
    departments: tuple[str, ...]


DIAGNOSIS_SIGNALS = [
    DiagnosisSignal("revenue", "Revenue growth or sales pipeline weakness", ("AXIOM_OUTREACH",), ("AXIOM_OUTREACH", "AXIOM_CRM", "AXIOM_PROPOSAL", "AXIOM_SCOUT", "AXIOM_FORECAST")),
    DiagnosisSignal("infrastructure", "Cloud reliability, scaling, cost, or deployment pain", ("AXIOM_CLOUDOPS",), ("AXIOM_CLOUD_OPS", "AXIOM_TERRAFORM", "AXIOM_KUBERNETES", "AXIOM_CICD", "AXIOM_MONITOR", "AXIOM_COST_OPT")),
    DiagnosisSignal("security", "Security, compliance, vulnerability, or risk exposure", ("AXIOM_CLOUDOPS",), ("AXIOM_SECURITY", "AXIOM_THREATS", "AXIOM_VULN", "AXIOM_SHIELD")),
    DiagnosisSignal("strategy", "Strategic clarity, executive intelligence, market uncertainty", ("AXIOM_COUNCIL",), ("AXIOM_BRIEF", "AXIOM_INTEL", "AXIOM_DATA_BRAIN", "AXIOM_FORECAST", "AXIOM_NEXUS")),
    DiagnosisSignal("automation", "Manual processes, operational drag, or agent opportunities", ("AXIOM_OUTREACH", "AXIOM_COUNCIL"), ("AXIOM_AGENTS", "AXIOM_WORKFLOWS", "AXIOM_VOICE", "AXIOM_COMMAND")),
]


def operating_model() -> dict[str, Any]:
    return {
        "status": "operational",
        "brand": BRAND,
        "layers": OPERATING_LAYERS,
        "gateways": COMMERCIAL_GATEWAYS,
        "departments": AXIOM_DEPARTMENTS,
        "counts": {
            "departments": len(AXIOM_DEPARTMENTS),
            "managers": len({item["manager"] for item in AXIOM_DEPARTMENTS}),
            "consultants": len({item["consultant"] for item in AXIOM_DEPARTMENTS}),
            "gateways": len(COMMERCIAL_GATEWAYS),
            "layers": len(OPERATING_LAYERS),
        },
        "communication_topology": [
            "Every consultant reports daily status to their manager.",
            "Every manager reports weekly to JARVIS.",
            "Every consultant can escalate milestones directly to Council.",
            "JARVIS can task any consultant directly.",
            "Council can summon any manager or consultant.",
            "Captain can override any layer.",
        ],
        "client_rule": "Do not expose departments as a menu. Sell diagnosis, prescribed capabilities, and outcome retainers.",
    }


async def _gateway_health_scores(db) -> dict[str, int]:
    """Derive a real health score per commercial gateway from actual system signals.

    There's no per-fictional-department telemetry to draw on (these are 25 catalog
    entries, not 25 real teams), so each gateway's score is computed from the real
    subsystem it fronts rather than invented per department:
      - AXIOM_OUTREACH: outreach send success rate over the last 24h + SES readiness
      - AXIOM_CLOUDOPS:  DB + Redis + scheduler liveness (the same signals /readyz uses)
      - AXIOM_COUNCIL:   AI provider availability across the router's circuit breakers
    """
    from datetime import datetime, timedelta, timezone as _tz
    from sqlalchemy import select, func
    from app.models.outreach import OutreachLog, OutreachStatus
    from app.core.config import settings

    scores = {"AXIOM_OUTREACH": 70, "AXIOM_CLOUDOPS": 70, "AXIOM_COUNCIL": 70}

    # AXIOM_OUTREACH — real send success rate, last 24h
    try:
        since = datetime.now(_tz.utc) - timedelta(hours=24)
        result = await db.execute(
            select(OutreachLog.status, func.count())
            .where(OutreachLog.sent_at.isnot(None), OutreachLog.sent_at >= since)
            .group_by(OutreachLog.status)
        )
        rows = dict(result.all())
        sent = rows.get(OutreachStatus.SENT, 0)
        failed = rows.get(OutreachStatus.FAILED, 0)
        total = sent + failed
        if total > 0:
            scores["AXIOM_OUTREACH"] = round(60 + 40 * (sent / total))
        elif settings.SES_FROM_EMAIL:
            scores["AXIOM_OUTREACH"] = 75  # configured but quiet — not yet proven, not failing
        else:
            scores["AXIOM_OUTREACH"] = 40  # SES unconfigured — outreach structurally can't send
    except Exception:
        pass

    # AXIOM_CLOUDOPS — real DB/Redis/scheduler liveness
    try:
        checks_ok = 0
        checks_total = 3
        await db.execute(select(1))
        checks_ok += 1
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL or "redis://localhost:6379", decode_responses=True)
            await r.ping()
            await r.aclose()
            checks_ok += 1
        except Exception:
            pass
        try:
            from app.services.scheduler.scheduler import get_scheduler
            if get_scheduler().running:
                checks_ok += 1
        except Exception:
            pass
        scores["AXIOM_CLOUDOPS"] = round(40 + 60 * (checks_ok / checks_total))
    except Exception:
        pass

    # AXIOM_COUNCIL — real AI provider availability (configured + circuit breaker open)
    try:
        from app.services.ai.router import ai_router
        status = ai_router.get_provider_status()
        if status:
            available = sum(1 for p in status.values() if p["available"])
            scores["AXIOM_COUNCIL"] = round(40 + 60 * (available / len(status)))
    except Exception:
        pass

    return scores


async def pulse_snapshot(db) -> dict[str, Any]:
    gateway_scores = await _gateway_health_scores(db)
    departments = []
    for department in AXIOM_DEPARTMENTS:
        score = gateway_scores.get(department["gateway"], 70)
        departments.append({
            **department,
            "health_score": score,
            "status": "operational" if score >= 70 else ("degraded" if score >= 40 else "at_risk"),
            "escalation": escalation_for_health(score),
            "milestone_path": "consultant -> council -> jarvis -> captain when authority threshold is crossed",
        })
    return {
        "status": "operational",
        "pulse_interval_minutes": 15,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "manager_alert": 70,
            "council_escalation": 50,
            "captain_notification": 30,
        },
        "departments": departments,
        "summary": {
            "total": len(departments),
            "operational": len([d for d in departments if d["health_score"] >= 70]),
            "manager_alerts": len([d for d in departments if d["health_score"] < 70]),
            "council_escalations": len([d for d in departments if d["health_score"] < 50]),
            "captain_notifications": len([d for d in departments if d["health_score"] < 30]),
        },
    }


def diagnose_client(profile: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(str(value).lower() for value in profile.values())
    matched = [
        signal for signal in DIAGNOSIS_SIGNALS
        if signal.key in text or any(word in text for word in signal.label.lower().split()[:3])
    ]
    if not matched:
        matched = [DIAGNOSIS_SIGNALS[0], DIAGNOSIS_SIGNALS[3]]

    gateway_codes = sorted({code for signal in matched for code in signal.gateways})
    department_codes = sorted({code for signal in matched for code in signal.departments})
    gateways = [gateway for gateway in COMMERCIAL_GATEWAYS if gateway["code"] in gateway_codes]
    departments = [department for department in AXIOM_DEPARTMENTS if department["code"] in department_codes]
    return {
        "status": "diagnosed",
        "diagnosis_id": f"axiom-{int(datetime.now(timezone.utc).timestamp())}",
        "client_visibility": "diagnosis_and_outcomes_only",
        "matched_signals": [{"key": signal.key, "label": signal.label} for signal in matched],
        "recommended_gateways": gateways,
        "prescribed_departments": departments,
        "deployment_summary": {
            "capability_count": len(departments),
            "primary_gateway": gateways[0]["name"] if gateways else "AXIOM OUTREACH",
            "commercial_model": "outcome-based retainer",
            "internal_orchestration": "AXIOM departments execute invisibly through AIONX/JARVIS.",
        },
    }


def consultant_prompts() -> list[dict[str, str]]:
    return [
        {
            "department_code": department["code"],
            "consultant": department["consultant"],
            "manager": department["manager"],
            "system_prompt": (
                f"You are {department['consultant']}, specialist consultant for {department['name']}. "
                f"Your service domain is: {department['service']}. Report daily to {department['manager']}. "
                "Escalate milestone completion, risk, or strategic uncertainty directly to Council. "
                "Never expose internal AI/departments to clients; communicate as Aliyar Solutions."
            ),
        }
        for department in AXIOM_DEPARTMENTS
    ]


def milestone_report(payload: dict[str, Any]) -> dict[str, Any]:
    department_code = str(payload.get("department_code", "")).upper()
    department = next((item for item in AXIOM_DEPARTMENTS if item["code"] == department_code), None)
    if not department:
        return {"status": "rejected", "reason": "unknown_department_code", "known_departments": [d["code"] for d in AXIOM_DEPARTMENTS]}
    return {
        "status": "queued_for_council",
        "department": department,
        "milestone": {
            "title": payload.get("title", "Untitled milestone"),
            "summary": payload.get("summary", ""),
            "impact": payload.get("impact", "medium"),
            "evidence": payload.get("evidence", {}),
        },
        "routing": {
            "consultant": department["consultant"],
            "manager": department["manager"],
            "council": "strategic_review",
            "captain_required": bool(payload.get("captain_required", False)),
        },
    }


def escalation_for_health(score: float) -> str:
    if score < 30:
        return "captain_notification"
    if score < 50:
        return "council_escalation"
    if score < 70:
        return "manager_alert"
    return "none"
