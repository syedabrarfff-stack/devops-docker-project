"""
JARVIS Agent Operations Center
Every AI team, every agent, every action — visible to Captain in real time.
"""
from datetime import datetime
from typing import Optional
import logging

from app.services.agents.liaison_profiles import liaison_agent_cards

logger = logging.getLogger(__name__)

# ── Complete Agent Registry ────────────────────────────────────────────────────
AGENT_TEAMS = {
    "cloud_infrastructure": {
        "team_name": "Cloud Infrastructure Team",
        "manager": "David Carter",
        "icon": "☁️",
        "color": "#2D6FE8",
        "agents": [
            {"id": "cloud_architect", "name": "Alex — Cloud Architect", "role": "Designs AWS architecture for clients", "status": "active"},
            {"id": "devops_engineer", "name": "Ryan — DevOps Engineer", "role": "CI/CD pipelines, Docker, Kubernetes", "status": "active"},
            {"id": "terraform_specialist", "name": "Zara — Terraform Specialist", "role": "Infrastructure as Code, AWS provisioning", "status": "active"},
            {"id": "monitoring_agent", "name": "Kai — Monitoring Specialist", "role": "Grafana, Prometheus, alerting systems", "status": "active"},
        ]
    },
    "ai_automation": {
        "team_name": "AI Automation Team",
        "manager": "Sophia Reynolds",
        "icon": "🤖",
        "color": "#00C6FF",
        "agents": [
            {"id": "workflow_builder", "name": "Nova — Workflow Builder", "role": "Business process automation design", "status": "active"},
            {"id": "integration_specialist", "name": "Leo — Integration Specialist", "role": "API orchestration, system connections", "status": "active"},
            {"id": "ai_trainer", "name": "Aria — AI Systems Trainer", "role": "AI model tuning and optimization", "status": "active"},
            {"id": "voice_agent", "name": "Echo — Voice AI Specialist", "role": "Voice receptionist, speech systems", "status": "active"},
        ]
    },
    "sales_outreach": {
        "team_name": "Sales & Outreach Team",
        "manager": "Darren Mitchell",
        "icon": "📈",
        "color": "#00D68F",
        "agents": [
            {"id": "lead_hunter", "name": "Hunter — Lead Generation Agent", "role": "Finds prospects globally who need our services", "status": "active"},
            {"id": "outreach_writer", "name": "Pen — Outreach Writer", "role": "Writes personalised outreach emails", "status": "active"},
            {"id": "proposal_writer", "name": "Sage — Proposal Specialist", "role": "Researches client, writes tailored proposals", "status": "active"},
            {"id": "followup_agent", "name": "Chase — Follow-Up Agent", "role": "24-hour follow ups, deal progression", "status": "active"},
        ]
    },
    "crm_operations": {
        "team_name": "CRM Operations Team",
        "manager": "Emma Collins",
        "icon": "👥",
        "color": "#FF8C42",
        "agents": [
            {"id": "lead_scorer", "name": "Scout — Lead Scoring Agent", "role": "Scores and ranks all leads by potential", "status": "active"},
            {"id": "pipeline_manager", "name": "Pipe — Pipeline Manager", "role": "Manages deal stages and progression", "status": "active"},
            {"id": "data_enricher", "name": "Rich — Data Enrichment Agent", "role": "Enriches lead data from public sources", "status": "active"},
            {"id": "relationship_manager", "name": "Bond — Relationship Manager", "role": "Nurtures long-term client relationships", "status": "active"},
        ]
    },
    "digital_marketing": {
        "team_name": "Digital Marketing Team",
        "manager": "Lucas Reed",
        "icon": "📣",
        "color": "#9B59B6",
        "agents": [
            {"id": "content_creator", "name": "Verse — Content Creator", "role": "LinkedIn posts, articles, thought leadership", "status": "active"},
            {"id": "seo_specialist", "name": "Rank — SEO Specialist", "role": "Search optimization, keyword strategy", "status": "active"},
            {"id": "social_media_agent", "name": "Buzz — Social Media Agent", "role": "Twitter, LinkedIn, Instagram operations", "status": "active"},
            {"id": "email_marketer", "name": "Mail — Email Marketing Agent", "role": "Newsletter campaigns, drip sequences", "status": "active"},
        ]
    },
    "client_success": {
        "team_name": "Client Success Team",
        "manager": "Olivia Bennett",
        "icon": "🌟",
        "color": "#F39C12",
        "agents": [
            {"id": "onboarding_agent", "name": "Welcome — Onboarding Agent", "role": "New client setup and orientation", "status": "active"},
            {"id": "delivery_manager", "name": "Deliver — Delivery Manager", "role": "Project delivery tracking and reporting", "status": "active"},
            {"id": "retention_agent", "name": "Keep — Retention Specialist", "role": "Client satisfaction and renewal", "status": "active"},
            {"id": "feedback_agent", "name": "Listen — Feedback Agent", "role": "Collects and analyses client feedback", "status": "active"},
        ]
    },
    "cybersecurity": {
        "team_name": "Cybersecurity Team",
        "manager": "Daniel Brooks",
        "icon": "🔒",
        "color": "#E74C3C",
        "agents": [
            {"id": "vulnerability_scanner", "name": "Scan — Vulnerability Scanner", "role": "Scans systems for security weaknesses", "status": "active"},
            {"id": "compliance_agent", "name": "Comply — Compliance Agent", "role": "GDPR, ISO, SOC2 compliance tracking", "status": "active"},
            {"id": "threat_monitor", "name": "Shield — Threat Monitor", "role": "Real-time security threat detection", "status": "active"},
            {"id": "incident_responder", "name": "Response — Incident Responder", "role": "Security incident handling and recovery", "status": "active"},
        ]
    },
    "intelligence": {
        "team_name": "Intelligence & Research Team",
        "manager": "Michael Hayes",
        "icon": "🧠",
        "color": "#1ABC9C",
        "agents": [
            {"id": "market_researcher", "name": "Intel — Market Researcher", "role": "Competitive analysis, market trends", "status": "active"},
            {"id": "tech_radar_agent", "name": "Radar — Tech Radar Agent", "role": "Emerging technology classification", "status": "active"},
            {"id": "business_analyst", "name": "Analyse — Business Analyst", "role": "KPI tracking, performance insights", "status": "active"},
            {"id": "opportunity_spotter", "name": "Spot — Opportunity Agent", "role": "Identifies new market opportunities daily", "status": "active"},
        ]
    },
    "governance": {
        "team_name": "Governance & Finance Team",
        "manager": "Darren Mitchell",
        "icon": "📋",
        "color": "#95A5A6",
        "agents": [
            {"id": "invoice_agent", "name": "Bill — Invoice Agent", "role": "Auto-generates ALY-YYYYMM-XXXX invoices", "status": "active"},
            {"id": "contract_agent", "name": "Legal — Contract Agent", "role": "Contract generation and tracking", "status": "active"},
            {"id": "approval_agent", "name": "Approve — Approval Agent", "role": "Routes decisions to Captain for approval", "status": "active"},
            {"id": "financial_tracker", "name": "Ledger — Financial Tracker", "role": "Revenue tracking, cost analysis", "status": "active"},
        ]
    },
    "system_health": {
        "team_name": "System Health Division",
        "manager": "Nathan Scott",
        "icon": "💚",
        "color": "#2ECC71",
        "agents": [
            {"id": "uptime_monitor", "name": "Watch — Uptime Monitor", "role": "24/7 infrastructure monitoring", "status": "active"},
            {"id": "performance_agent", "name": "Perf — Performance Agent", "role": "Response time, resource optimization", "status": "active"},
            {"id": "backup_agent", "name": "Safe — Backup Agent", "role": "Automated backups and recovery", "status": "active"},
            {"id": "alert_dispatcher", "name": "Alert — Alert Dispatcher", "role": "Notifies Captain of critical issues", "status": "active"},
        ]
    },
    "client_liaison": {
        "team_name": "Client Liaison Team",
        "manager": "Olivia Bennett",
        "icon": "CL",
        "color": "#14B8A6",
        "agents": liaison_agent_cards(),
    },
}


def get_all_teams() -> dict:
    return {
        "total_teams": len(AGENT_TEAMS),
        "total_agents": sum(len(t["agents"]) for t in AGENT_TEAMS.values()),
        "teams": AGENT_TEAMS,
        "generated_at": datetime.now().isoformat()
    }


def get_team(team_id: str) -> Optional[dict]:
    return AGENT_TEAMS.get(team_id)


def get_agent(agent_id: str) -> Optional[dict]:
    for team_id, team in AGENT_TEAMS.items():
        for agent in team["agents"]:
            if agent["id"] == agent_id:
                return {**agent, "team": team["team_name"], "team_id": team_id, "manager": team["manager"]}
    return None


def get_all_agents_flat() -> list:
    agents = []
    for team_id, team in AGENT_TEAMS.items():
        for agent in team["agents"]:
            agents.append({
                **agent,
                "team_id": team_id,
                "team_name": team["team_name"],
                "manager": team["manager"],
                "icon": team["icon"]
            })
    return agents
