"""AIONX operational integrity layer.

This is the production-safe implementation of the recovered "final
architecture" batch: operational integrity teams, mission control, milestone
governance, QA, repair, fallback, HIA personas, and the full 18-stage pipeline.
It exposes the system as live doctrine plus callable operational simulations.
Irreversible execution remains governed by the existing Captain approval layer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


OPERATIONAL_INTEGRITY_TEAMS: list[dict[str, Any]] = [
    {
        "code": "MISSION_CONTROL",
        "name": "Mission Control",
        "purpose": "Turn every signed client into a governed Mission File with milestones, dependencies, owners, and success metrics.",
        "outputs": ["mission_files", "milestone_plans", "dependency_maps", "status_dashboards"],
        "escalation": "48h milestone delay -> JARVIS; 72h delay -> Captain notification.",
        "sla": "Mission file created immediately after client acceptance.",
    },
    {
        "code": "CROSS_REVIEW_BOARD",
        "name": "Cross-Department Review Board",
        "purpose": "Validate every milestone from another department's perspective before it advances.",
        "outputs": ["cross_review_reports", "alignment_findings", "integration_risk_flags"],
        "escalation": "Any fail routes to Repair and Recovery before QA.",
        "sla": "No milestone advances without written pass or conditional pass.",
    },
    {
        "code": "QUALITY_ASSURANCE",
        "name": "Quality Assurance Team",
        "purpose": "Independently test every deliverable against success criteria, technical accuracy, brand standard, and completeness.",
        "outputs": ["qa_certificates", "defect_lists", "delivery_readiness_verdicts"],
        "escalation": "QA fail activates Repair and Recovery.",
        "sla": "Client delivery blocked until QA certificate is clean.",
    },
    {
        "code": "REPAIR_RECOVERY",
        "name": "Repair and Recovery Team",
        "purpose": "Convert failures into exact repair instructions with root cause, fix, verification, and priority.",
        "outputs": ["repair_instructions", "root_cause_records", "recurring_defect_alerts"],
        "escalation": "Same defect 3+ times -> structural improvement proposal.",
        "sla": "Critical defect instruction produced immediately.",
    },
    {
        "code": "FALLBACK_CONTINUITY",
        "name": "Fallback and Continuity Team",
        "purpose": "Guarantee no single point of failure survives across agents, jobs, APIs, and departments.",
        "outputs": ["fallback_assignments", "backup_execution_plans", "continuity_drills"],
        "escalation": "Primary failure activates backup path without human intervention.",
        "sla": "Fallback activation target under 120 seconds.",
    },
    {
        "code": "DEPARTMENT_HEALTH",
        "name": "Department Health Monitoring Team",
        "purpose": "Continuously score the 25 capability modules across execution, quality, response, collaboration, utilization, and trend.",
        "outputs": ["weekly_health_reports", "red_flag_reviews", "department_scorecards"],
        "escalation": "60-74 Council review; 40-59 JARVIS intervention; below 40 Captain notification.",
        "sla": "15-minute pulse plus weekly Council report.",
    },
    {
        "code": "KNOWLEDGE_SYNTHESIS",
        "name": "Knowledge Synthesis Team",
        "purpose": "Turn every completed milestone, outcome, and failure into institutional memory and reusable operating doctrine.",
        "outputs": ["knowledge_updates", "case_studies", "sop_updates", "civilization_memory"],
        "escalation": "Uncaptured lesson after completed milestone is treated as operational leakage.",
        "sla": "Learning synthesis after every completed milestone.",
    },
    {
        "code": "HIA_GOVERNANCE",
        "name": "Human Interface Agent Governance",
        "purpose": "Certify, monitor, and protect the client-facing human-quality communication layer.",
        "outputs": ["hia_profiles", "certification_scores", "communication_reviews"],
        "escalation": "Failed HIA certification activates backup HIA with client context preloaded.",
        "sla": "Only certified HIAs may deliver client-facing milestone updates.",
    },
]


FULL_AIONX_PIPELINE: list[dict[str, Any]] = [
    {"stage": 1, "name": "World Scan", "owner": "SCOUT", "output": "leads table populated"},
    {"stage": 2, "name": "Lead Enrichment", "owner": "SCOUT", "output": "contact, company, stack, and pain signals"},
    {"stage": 3, "name": "Lead Scoring", "owner": "ORACLE-S", "output": "0-100 score and qualified flag"},
    {"stage": 4, "name": "Business Diagnosis", "owner": "MARKET", "output": "capability gap profile"},
    {"stage": 5, "name": "Case Study Matching", "owner": "QUILL", "output": "most relevant proof narrative"},
    {"stage": 6, "name": "Council Outreach Review", "owner": "AXIOM COUNCIL", "output": "improvement report"},
    {"stage": 7, "name": "Outreach Draft and Optimization", "owner": "HERALD", "output": "sequence ready"},
    {"stage": 8, "name": "Email Dispatch", "owner": "HERALD", "output": "outreach log event"},
    {"stage": 9, "name": "Reply Monitoring", "owner": "NEXUS-R", "output": "reply classification"},
    {"stage": 10, "name": "Lead Learning", "owner": "SELF_LEARN", "output": "outreach learning records"},
    {"stage": 11, "name": "Proposal", "owner": "HERALD", "output": "proposal or Captain approval queue"},
    {"stage": 12, "name": "Client Acceptance", "owner": "JARVIS", "output": "client record and mission trigger"},
    {"stage": 13, "name": "Mission Creation", "owner": "MISSION_CONTROL", "output": "mission file and milestones"},
    {"stage": 14, "name": "Milestone Execution", "owner": "DEPARTMENTS", "output": "governed milestone outputs"},
    {"stage": 15, "name": "Client Delivery", "owner": "HIA_GOVERNANCE", "output": "client-facing delivery record"},
    {"stage": 16, "name": "Learning Synthesis", "owner": "KNOWLEDGE_SYNTHESIS", "output": "memory, SOP, case study updates"},
    {"stage": 17, "name": "Continuous Evolution", "owner": "ADAPTIVE_INTELLIGENCE", "output": "improvement and expansion proposals"},
    {"stage": 18, "name": "Flywheel Acceleration", "owner": "JARVIS", "output": "referral, reputation, and proof compounding"},
]


MILESTONE_GOVERNANCE_WORKFLOW: list[dict[str, Any]] = [
    {"stage": 1, "name": "Mission Created", "gate": "Mission Control captures goals, constraints, success metrics, timeline, and budget."},
    {"stage": 2, "name": "Milestone Generated", "gate": "Objective, deliverable, owner, deadline, dependencies, success criteria, and risk register."},
    {"stage": 3, "name": "Department Planning", "gate": "Department DIO signs off execution plan and resources."},
    {"stage": 4, "name": "Council Review", "gate": "Strategic alignment, technical soundness, commercial impact, client perception risk."},
    {"stage": 5, "name": "Council Improvement Report", "gate": "3-7 recommendations implemented before work proceeds."},
    {"stage": 6, "name": "Department Execution", "gate": "Real-time Mission Control progress tracking."},
    {"stage": 7, "name": "Cross-Department Validation", "gate": "Alignment, interface assumptions, client objective fit."},
    {"stage": 8, "name": "Quality Assurance Review", "gate": "Success criteria, completeness, accuracy, brand standard."},
    {"stage": 9, "name": "Repair and Recovery", "gate": "If needed, precise defect repair loop until QA passes."},
    {"stage": 10, "name": "Council Final Validation", "gate": "Completed QA-certified milestone needs >80 Council approval."},
    {"stage": 11, "name": "JARVIS Executive Review", "gate": "Mission-file alignment and client-experience consistency."},
    {"stage": 12, "name": "Captain Approval If Required", "gate": "Only Tier 3 milestones require Captain."},
    {"stage": 13, "name": "Client Delivery", "gate": "Certified HIA delivers in natural professional language."},
    {"stage": 14, "name": "Learning and Memory Update", "gate": "Knowledge synthesis updates memory, SOPs, lessons, case studies."},
]


HIA_PROFILES: list[dict[str, Any]] = [
    {
        "code": "DARREN_MITCHELL",
        "name": "Darren Mitchell",
        "role": "Client Acquisition Lead",
        "gateway": "AIONX OUTREACH",
        "voice": "Warm, direct, commercially sharp, never robotic.",
        "strengths": ["pipeline diagnosis", "outreach strategy", "client reassurance", "revenue framing"],
        "backup": "Claire Warren",
    },
    {
        "code": "CLAIRE_WARREN",
        "name": "Claire Warren",
        "role": "Proposal and Closing Specialist",
        "gateway": "AIONX OUTREACH",
        "voice": "Precise, confident, risk-aware, outcome-led.",
        "strengths": ["proposal quality", "objection handling", "offer structure", "risk reversal"],
        "backup": "Darren Mitchell",
    },
    {
        "code": "DAVID_CARTER",
        "name": "David Carter",
        "role": "Solutions Architect",
        "gateway": "AIONX CLOUDOPS",
        "voice": "Senior architect to peer, calm under incidents.",
        "strengths": ["cloud architecture", "mission planning", "technical translation", "client trust"],
        "backup": "Nathan Scott",
    },
    {
        "code": "NATHAN_SCOTT",
        "name": "Nathan Scott",
        "role": "Infrastructure Delivery Lead",
        "gateway": "AIONX CLOUDOPS",
        "voice": "Operational, specific, reliable, no drama.",
        "strengths": ["IaC", "CI/CD", "Kubernetes", "delivery governance"],
        "backup": "David Carter",
    },
    {
        "code": "DANIEL_BROOKS",
        "name": "Daniel Brooks",
        "role": "Security Consultant",
        "gateway": "AIONX CLOUDOPS",
        "voice": "Protective, clear, evidence-first.",
        "strengths": ["security posture", "incident handling", "compliance translation", "risk briefings"],
        "backup": "Kate Morrison",
    },
    {
        "code": "EMMA_COLLINS",
        "name": "Emma Collins",
        "role": "Business Optimisation Specialist",
        "gateway": "AIONX COUNCIL",
        "voice": "Analytical, practical, executive-readable.",
        "strengths": ["BI", "forecasting", "client health", "commercial analytics"],
        "backup": "Michael Hayes",
    },
    {
        "code": "SOPHIA_REYNOLDS",
        "name": "Sophia Reynolds",
        "role": "Strategic Intelligence Advisor",
        "gateway": "AIONX COUNCIL",
        "voice": "Curious, strategic, polished, board-ready.",
        "strengths": ["strategy", "automation design", "market intelligence", "executive briefings"],
        "backup": "Emma Collins",
    },
    {
        "code": "MICHAEL_HAYES",
        "name": "Michael Hayes",
        "role": "Infrastructure Strategist",
        "gateway": "AIONX COUNCIL",
        "voice": "Systems thinker, numbers-oriented, calm.",
        "strengths": ["observability", "cost modeling", "predictive infrastructure", "SLOs"],
        "backup": "David Carter",
    },
    {
        "code": "OLIVIA_BENNETT",
        "name": "Olivia Bennett",
        "role": "Executive Briefing Lead",
        "gateway": "AIONX COUNCIL",
        "voice": "Concise, reassuring, decision-focused.",
        "strengths": ["briefings", "client memory", "communication quality", "weekly reports"],
        "backup": "Sophia Reynolds",
    },
]


FALLBACK_MATRIX: list[dict[str, Any]] = [
    {"component": "Gmail API", "failure_mode": "rate_limit_or_oauth_error", "fallback": "queue emails and retry with exponential backoff"},
    {"component": "Apollo API", "failure_mode": "quota_exceeded", "fallback": "switch to HubSpot, Clearbit, then Google Maps/free discovery"},
    {"component": "Primary AI Provider", "failure_mode": "provider_outage", "fallback": "AI router failover through configured providers"},
    {"component": "DIO Agent", "failure_mode": "unresponsive", "fallback": "backup DIO activates with inherited context"},
    {"component": "Human Interface Agent", "failure_mode": "certification_failure", "fallback": "backup HIA with client context preloaded"},
    {"component": "Council Session", "failure_mode": "quorum_not_reached", "fallback": "async review with lowered quorum and extended window"},
    {"component": "Scheduler Job", "failure_mode": "job_failure", "fallback": "dead-letter queue, retry, Telegram alert"},
    {"component": "Database", "failure_mode": "connection_loss", "fallback": "Redis recent-data cache and queued writes for replay"},
    {"component": "EC2 Instance", "failure_mode": "host_failure", "fallback": "container restart and future ECS/Fargate migration path"},
    {"component": "AWS Region", "failure_mode": "regional_outage", "fallback": "future Route53 failover and DR region activation"},
]


OPERATIONAL_INTEGRITY_TABLE_PLAN: list[dict[str, str]] = [
    {"table": "mission_files", "purpose": "Client mission objectives, constraints, success metrics, and owner map."},
    {"table": "milestone_plans", "purpose": "Milestone objectives, deadlines, dependencies, risks, and status."},
    {"table": "cross_review_reports", "purpose": "Cross-department validation verdicts and findings."},
    {"table": "quality_certificates", "purpose": "QA pass/fail certificates with test criteria."},
    {"table": "repair_instructions", "purpose": "Defects, root causes, required fixes, verification steps."},
    {"table": "fallback_assignments", "purpose": "Primary and backup ownership across agents, jobs, APIs, and departments."},
    {"table": "department_health_snapshots", "purpose": "15-minute and weekly health scores for 25 modules."},
    {"table": "knowledge_synthesis_records", "purpose": "Post-milestone learnings and institutional memory updates."},
    {"table": "hia_profiles", "purpose": "Certified client-facing personas, voice standards, and backups."},
    {"table": "hia_certification_records", "purpose": "Certification scores, renewal status, and failure actions."},
    {"table": "flywheel_snapshots", "purpose": "Lead quality, outreach precision, conversion, satisfaction, referrals, reputation."},
    {"table": "operational_integrity_audit", "purpose": "Tamper-evident governance log for integrity gates."},
]


def operational_integrity_status() -> dict[str, Any]:
    return {
        "status": "operational_integrity_surface_live",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "team_count": len(OPERATIONAL_INTEGRITY_TEAMS),
        "pipeline_stage_count": len(FULL_AIONX_PIPELINE),
        "milestone_governance_stage_count": len(MILESTONE_GOVERNANCE_WORKFLOW),
        "hia_count": len(HIA_PROFILES),
        "fallback_rule_count": len(FALLBACK_MATRIX),
        "schema_plan_table_count": len(OPERATIONAL_INTEGRITY_TABLE_PLAN),
        "teams": OPERATIONAL_INTEGRITY_TEAMS,
        "pipeline": FULL_AIONX_PIPELINE,
        "milestone_governance": MILESTONE_GOVERNANCE_WORKFLOW,
        "hia_profiles": HIA_PROFILES,
        "fallback_matrix": FALLBACK_MATRIX,
        "schema_plan": OPERATIONAL_INTEGRITY_TABLE_PLAN,
        "governance_boundary": (
            "This layer can plan, validate, certify, route, and recommend. "
            "Tier 3 production actions still require Captain approval."
        ),
    }


def create_mission_plan(payload: dict[str, Any]) -> dict[str, Any]:
    client = payload.get("client_name") or payload.get("company") or "Unknown Client"
    objective = payload.get("objective") or "Operational improvement mission"
    gateway = payload.get("gateway") or "AIONX COUNCIL"
    mission_id = f"mission-{int(datetime.now(timezone.utc).timestamp())}"
    milestones = [
        {
            "number": 1,
            "title": "Diagnosis and Success Criteria",
            "owner": "MISSION_CONTROL",
            "success_criteria": ["client goals confirmed", "risk register created", "capability map approved"],
        },
        {
            "number": 2,
            "title": "Execution Plan and Council Review",
            "owner": "AXIOM COUNCIL",
            "success_criteria": ["Council score above 80", "improvement report applied", "dependencies mapped"],
        },
        {
            "number": 3,
            "title": "Department Delivery Sprint",
            "owner": gateway,
            "success_criteria": ["cross-review pass", "QA certificate pass", "HIA delivery ready"],
        },
        {
            "number": 4,
            "title": "Client Delivery and Learning",
            "owner": "HIA_GOVERNANCE",
            "success_criteria": ["client delivery completed", "knowledge synthesis recorded", "flywheel updated"],
        },
    ]
    return {
        "status": "mission_plan_created",
        "mission_id": mission_id,
        "client": client,
        "objective": objective,
        "gateway": gateway,
        "milestones": milestones,
        "workflow": MILESTONE_GOVERNANCE_WORKFLOW,
        "captain_required": bool(payload.get("tier3", False)),
    }


def issue_qa_certificate(payload: dict[str, Any]) -> dict[str, Any]:
    criteria = payload.get("criteria") or ["accuracy", "completeness", "brand_standard", "client_success_fit"]
    failures = payload.get("failures") or []
    verdict = "fail" if failures else "pass"
    return {
        "status": "qa_certificate_issued",
        "certificate_id": f"qa-{int(datetime.now(timezone.utc).timestamp())}",
        "milestone_id": payload.get("milestone_id", "unassigned"),
        "criteria": criteria,
        "verdict": verdict,
        "client_delivery_allowed": verdict == "pass",
        "failures": failures,
        "next_route": "repair_recovery" if failures else "council_final_validation",
    }


def create_repair_instruction(payload: dict[str, Any]) -> dict[str, Any]:
    defect = payload.get("defect") or "Unspecified defect"
    return {
        "status": "repair_instruction_created",
        "repair_id": f"repair-{int(datetime.now(timezone.utc).timestamp())}",
        "defect": defect,
        "root_cause": payload.get("root_cause") or "Requires department review",
        "fix_required": payload.get("fix_required") or "Correct the defect and resubmit to QA.",
        "verification": payload.get("verification") or "QA reruns the original failed criterion.",
        "priority": payload.get("priority", "HIGH"),
        "route": "responsible_department -> qa_revalidation -> council_final_validation",
    }


def run_fallback_drill(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    target = (payload or {}).get("component", "DIO Agent")
    match = next((item for item in FALLBACK_MATRIX if item["component"].lower() == str(target).lower()), FALLBACK_MATRIX[3])
    return {
        "status": "fallback_drill_ready",
        "component": match["component"],
        "failure_mode": match["failure_mode"],
        "fallback": match["fallback"],
        "target_activation_seconds": 120 if "Agent" in match["component"] else 15 * 60,
        "captain_notification_required": match["component"] in {"Database", "EC2 Instance", "AWS Region"},
    }


def synthesize_milestone_learning(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "knowledge_synthesis_created",
        "synthesis_id": f"learn-{int(datetime.now(timezone.utc).timestamp())}",
        "milestone_id": payload.get("milestone_id", "unassigned"),
        "what_worked": payload.get("what_worked") or ["Reusable pattern pending operator notes"],
        "what_was_harder": payload.get("what_was_harder") or ["Unknown until delivery evidence is attached"],
        "client_response": payload.get("client_response") or "not_recorded",
        "memory_targets": ["knowledge_base", "civilization_memory", "learning_records", "memory_operational"],
        "case_study_candidate": bool(payload.get("case_study_candidate", False)),
    }
