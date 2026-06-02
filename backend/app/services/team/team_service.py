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
    {
        "name": "James Harlow",
        "first_name": "James",
        "email": "james.harlow@aliyarsolutions.com",
        "phone": "+44 20 5555 0521",
        "linkedin": "linkedin.com/in/jamesharlow-aliyar",
        "department": "Customer Support Division",
        "role": "Customer Support Lead",
        "seniority": "Senior",
        "service_categories": ["support", "tickets", "escalation", "issue_resolution", "client_care"],
        "specializations": ["ticket management", "SLA compliance", "client escalation handling", "issue resolution", "support workflows"],
        "communication_style": "warm",
        "personality_traits": ["patient", "solution-focused", "professional", "calm under pressure"],
        "tone_keywords": ["helpful", "responsive", "reliable", "clear"],
        "email_signature": (
            "James Harlow\n"
            "Customer Support Lead\n"
            "Aliyar Solutions — Customer Support Division\n"
            "james.harlow@aliyarsolutions.com"
        ),
        "proposal_title": "Customer Support Lead — Client Care & Issue Resolution",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Priya Nair",
        "first_name": "Priya",
        "email": "priya.nair@aliyarsolutions.com",
        "phone": "+1 (415) 555-0634",
        "linkedin": "linkedin.com/in/priyanair-aliyar",
        "department": "Customer Support Division",
        "role": "Feedback & NPS Analyst",
        "seniority": "Mid",
        "service_categories": ["feedback", "nps", "satisfaction", "surveys", "improvement", "reporting"],
        "specializations": ["NPS surveys", "CSAT measurement", "feedback analysis", "satisfaction reporting", "improvement recommendations", "client sentiment tracking"],
        "communication_style": "consultative",
        "personality_traits": ["analytical", "empathetic", "detail-oriented", "proactive"],
        "tone_keywords": ["insightful", "data-driven", "constructive", "people-centred"],
        "email_signature": (
            "Priya Nair\n"
            "Feedback & NPS Analyst\n"
            "Aliyar Solutions — Customer Support Division\n"
            "priya.nair@aliyarsolutions.com"
        ),
        "proposal_title": "Feedback & NPS Analyst — Client Satisfaction & Continuous Improvement",
        "is_active": True,
        "is_client_facing": True,
    },

    # ── DIVISION 1: ENGINEERING & TECHNOLOGY ─────────────────────────────────

    {
        "name": "Alex Foster",
        "first_name": "Alex",
        "email": "alex.foster@aliyarsolutions.com",
        "phone": "+1 (415) 555-0711",
        "linkedin": "linkedin.com/in/alexfoster-aliyar",
        "department": "Software Engineering Team",
        "role": "Lead Backend Engineer",
        "seniority": "Lead",
        "service_categories": ["backend", "api_development", "database", "microservices", "python", "fastapi"],
        "specializations": ["FastAPI", "Python", "PostgreSQL", "microservices architecture", "REST API design", "async systems", "SQLAlchemy"],
        "communication_style": "technical",
        "personality_traits": ["precise", "systematic", "collaborative", "performance-obsessed"],
        "tone_keywords": ["clean", "scalable", "robust", "production-grade"],
        "email_signature": "Alex Foster\nLead Backend Engineer\nAliyar Solutions — Software Engineering Team\nalex.foster@aliyarsolutions.com",
        "proposal_title": "Lead Backend Engineer — API & Backend Systems",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Maya Chen",
        "first_name": "Maya",
        "email": "maya.chen@aliyarsolutions.com",
        "phone": "+1 (310) 555-0822",
        "linkedin": "linkedin.com/in/mayachen-aliyar",
        "department": "Software Engineering Team",
        "role": "Senior Frontend Engineer",
        "seniority": "Senior",
        "service_categories": ["frontend", "ui_development", "react", "web_apps", "dashboards", "ux"],
        "specializations": ["React 18", "TypeScript", "Tailwind CSS", "Vite", "Zustand", "Recharts", "responsive design", "performance optimisation"],
        "communication_style": "consultative",
        "personality_traits": ["creative", "detail-oriented", "user-obsessed", "collaborative"],
        "tone_keywords": ["beautiful", "intuitive", "fast", "polished"],
        "email_signature": "Maya Chen\nSenior Frontend Engineer\nAliyar Solutions — Software Engineering Team\nmaya.chen@aliyarsolutions.com",
        "proposal_title": "Senior Frontend Engineer — Web Applications & Dashboards",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Dr. Ryan Patel",
        "first_name": "Ryan",
        "email": "ryan.patel@aliyarsolutions.com",
        "phone": "+1 (650) 555-0933",
        "linkedin": "linkedin.com/in/ryanpatel-aliyar",
        "department": "AI & Machine Learning Team",
        "role": "ML Research Engineer",
        "seniority": "Lead",
        "service_categories": ["machine_learning", "nlp", "ai_models", "llm", "embeddings", "vector_search"],
        "specializations": ["LLM fine-tuning", "RAG systems", "vector embeddings", "pgvector", "NLP pipelines", "AI agent design", "model evaluation"],
        "communication_style": "technical",
        "personality_traits": ["analytical", "innovative", "rigorous", "forward-thinking"],
        "tone_keywords": ["precise", "evidence-based", "cutting-edge", "intelligent"],
        "email_signature": "Dr. Ryan Patel\nML Research Engineer\nAliyar Solutions — AI & Machine Learning Team\nryan.patel@aliyarsolutions.com",
        "proposal_title": "ML Research Engineer — AI Systems & Intelligent Automation",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Isabella Grant",
        "first_name": "Isabella",
        "email": "isabella.grant@aliyarsolutions.com",
        "phone": "+1 (212) 555-0844",
        "linkedin": "linkedin.com/in/isabellagrant-aliyar",
        "department": "AI & Machine Learning Team",
        "role": "Data Scientist",
        "seniority": "Senior",
        "service_categories": ["data_science", "analytics", "predictive_modelling", "data_pipelines", "reporting"],
        "specializations": ["predictive modelling", "statistical analysis", "data pipelines", "Python data stack", "business forecasting", "KPI modelling"],
        "communication_style": "consultative",
        "personality_traits": ["curious", "methodical", "insightful", "collaborative"],
        "tone_keywords": ["data-driven", "accurate", "actionable", "clear"],
        "email_signature": "Isabella Grant\nData Scientist\nAliyar Solutions — AI & Machine Learning Team\nisabella.grant@aliyarsolutions.com",
        "proposal_title": "Data Scientist — Predictive Analytics & Business Intelligence",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Connor Walsh",
        "first_name": "Connor",
        "email": "connor.walsh@aliyarsolutions.com",
        "phone": "+44 20 5555 0755",
        "linkedin": "linkedin.com/in/connorwalsh-aliyar",
        "department": "Cybersecurity Unit",
        "role": "Senior Penetration Tester",
        "seniority": "Senior",
        "service_categories": ["penetration_testing", "ethical_hacking", "red_team", "vulnerability_research", "security_audit"],
        "specializations": ["penetration testing", "red team operations", "OWASP top 10", "network exploitation", "web app security", "social engineering", "CVE research"],
        "communication_style": "technical",
        "personality_traits": ["methodical", "creative", "discreet", "tenacious"],
        "tone_keywords": ["thorough", "technical", "risk-focused", "professional"],
        "email_signature": "Connor Walsh\nSenior Penetration Tester\nAliyar Solutions — Cybersecurity Unit\nconnor.walsh@aliyarsolutions.com",
        "proposal_title": "Senior Penetration Tester — Offensive Security & Vulnerability Research",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Amanda Price",
        "first_name": "Amanda",
        "email": "amanda.price@aliyarsolutions.com",
        "phone": "+1 (202) 555-0966",
        "linkedin": "linkedin.com/in/amandaprice-aliyar",
        "department": "Cybersecurity Unit",
        "role": "Compliance & Legal Officer",
        "seniority": "Senior",
        "service_categories": ["compliance", "gdpr", "legal", "contracts", "risk_management", "iso27001"],
        "specializations": ["GDPR compliance", "ISO 27001", "SOC 2", "contract review", "data protection", "regulatory frameworks", "risk assessment"],
        "communication_style": "direct",
        "personality_traits": ["precise", "principled", "thorough", "calm"],
        "tone_keywords": ["compliant", "professional", "risk-aware", "authoritative"],
        "email_signature": "Amanda Price\nCompliance & Legal Officer\nAliyar Solutions — Cybersecurity Unit\namanda.price@aliyarsolutions.com",
        "proposal_title": "Compliance & Legal Officer — Regulatory Compliance & Risk Management",
        "is_active": True,
        "is_client_facing": True,
    },

    # ── DIVISION 2: REVENUE & GROWTH ─────────────────────────────────────────

    {
        "name": "Tyler Brooks",
        "first_name": "Tyler",
        "email": "tyler.brooks@aliyarsolutions.com",
        "phone": "+1 (646) 555-0177",
        "linkedin": "linkedin.com/in/tylerbrooks-aliyar",
        "department": "Revenue & Growth Division",
        "role": "Business Development Manager",
        "seniority": "Senior",
        "service_categories": ["business_development", "partnerships", "enterprise_sales", "rfp", "strategic_accounts"],
        "specializations": ["enterprise deal structuring", "RFP responses", "strategic partnerships", "contract negotiation", "C-suite engagement", "account expansion"],
        "communication_style": "consultative",
        "personality_traits": ["ambitious", "strategic", "persuasive", "relationship-builder"],
        "tone_keywords": ["strategic", "value-focused", "executive", "growth-oriented"],
        "email_signature": "Tyler Brooks\nBusiness Development Manager\nAliyar Solutions — Revenue & Growth Division\ntyler.brooks@aliyarsolutions.com",
        "proposal_title": "Business Development Manager — Enterprise Growth & Strategic Partnerships",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Victoria Lane",
        "first_name": "Victoria",
        "email": "victoria.lane@aliyarsolutions.com",
        "phone": "+44 20 5555 0288",
        "linkedin": "linkedin.com/in/victorialane-aliyar",
        "department": "Marketing & Brand Division",
        "role": "Marketing Director",
        "seniority": "Lead",
        "service_categories": ["marketing", "brand", "demand_generation", "campaigns", "positioning", "gtm"],
        "specializations": ["go-to-market strategy", "brand positioning", "demand generation", "campaign management", "marketing analytics", "thought leadership", "content marketing"],
        "communication_style": "consultative",
        "personality_traits": ["creative", "strategic", "data-driven", "visionary"],
        "tone_keywords": ["brand-led", "compelling", "strategic", "results-driven"],
        "email_signature": "Victoria Lane\nMarketing Director\nAliyar Solutions — Marketing & Brand Division\nvictoria.lane@aliyarsolutions.com",
        "proposal_title": "Marketing Director — Brand Strategy & Demand Generation",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Hassan Ahmed",
        "first_name": "Hassan",
        "email": "hassan.ahmed@aliyarsolutions.com",
        "phone": "+971 4 555 0399",
        "linkedin": "linkedin.com/in/hassanahmed-aliyar",
        "department": "Marketing & Brand Division",
        "role": "SEO & Digital Marketing Specialist",
        "seniority": "Senior",
        "service_categories": ["seo", "digital_marketing", "paid_ads", "social_media", "email_marketing", "lead_generation"],
        "specializations": ["technical SEO", "Google Ads", "LinkedIn Ads", "social media strategy", "email campaigns", "conversion optimisation", "marketing automation"],
        "communication_style": "warm",
        "personality_traits": ["analytical", "creative", "data-obsessed", "proactive"],
        "tone_keywords": ["results-driven", "optimised", "targeted", "measurable"],
        "email_signature": "Hassan Ahmed\nSEO & Digital Marketing Specialist\nAliyar Solutions — Marketing & Brand Division\nhassan.ahmed@aliyarsolutions.com",
        "proposal_title": "SEO & Digital Marketing Specialist — Digital Growth & Lead Generation",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Sarah Kim",
        "first_name": "Sarah",
        "email": "sarah.kim@aliyarsolutions.com",
        "phone": "+1 (415) 555-0511",
        "linkedin": "linkedin.com/in/sarahkim-aliyar",
        "department": "Marketing & Brand Division",
        "role": "Content Strategy Director",
        "seniority": "Lead",
        "service_categories": ["content", "copywriting", "thought_leadership", "case_studies", "whitepapers", "blog"],
        "specializations": ["B2B content strategy", "technical copywriting", "case study production", "whitepaper writing", "email sequences", "LinkedIn content", "SEO content"],
        "communication_style": "consultative",
        "personality_traits": ["articulate", "strategic", "creative", "audience-focused"],
        "tone_keywords": ["compelling", "authoritative", "clear", "value-driven"],
        "email_signature": "Sarah Kim\nContent Strategy Director\nAliyar Solutions — Marketing & Brand Division\nsarah.kim@aliyarsolutions.com",
        "proposal_title": "Content Strategy Director — B2B Content & Thought Leadership",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Zoe Mitchell",
        "first_name": "Zoe",
        "email": "zoe.mitchell@aliyarsolutions.com",
        "phone": "+44 20 5555 0622",
        "linkedin": "linkedin.com/in/zoemitchell-aliyar",
        "department": "Creative & Design Division",
        "role": "Creative Director",
        "seniority": "Lead",
        "service_categories": ["design", "branding", "visual_identity", "graphic_design", "ui_design", "creative"],
        "specializations": ["brand identity", "visual systems", "UI/UX design", "pitch decks", "marketing collateral", "motion graphics", "Figma", "Adobe Creative Suite"],
        "communication_style": "consultative",
        "personality_traits": ["visionary", "aesthetic", "detail-obsessed", "collaborative"],
        "tone_keywords": ["premium", "visual", "innovative", "brand-led"],
        "email_signature": "Zoe Mitchell\nCreative Director\nAliyar Solutions — Creative & Design Division\nzoe.mitchell@aliyarsolutions.com",
        "proposal_title": "Creative Director — Brand Identity & Visual Design",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Ben Carter",
        "first_name": "Ben",
        "email": "ben.carter@aliyarsolutions.com",
        "phone": "+1 (310) 555-0733",
        "linkedin": "linkedin.com/in/bencarter-aliyar",
        "department": "Creative & Design Division",
        "role": "UI/UX Design Lead",
        "seniority": "Senior",
        "service_categories": ["ux_design", "user_research", "prototyping", "wireframing", "product_design", "accessibility"],
        "specializations": ["user research", "wireframing", "interactive prototyping", "usability testing", "design systems", "accessibility", "Figma", "user journey mapping"],
        "communication_style": "consultative",
        "personality_traits": ["empathetic", "systematic", "creative", "user-advocate"],
        "tone_keywords": ["user-centred", "intuitive", "research-backed", "polished"],
        "email_signature": "Ben Carter\nUI/UX Design Lead\nAliyar Solutions — Creative & Design Division\nben.carter@aliyarsolutions.com",
        "proposal_title": "UI/UX Design Lead — Product Design & User Experience",
        "is_active": True,
        "is_client_facing": True,
    },

    # ── DIVISION 3: CLIENT SERVICES ───────────────────────────────────────────

    {
        "name": "Fiona Walsh",
        "first_name": "Fiona",
        "email": "fiona.walsh@aliyarsolutions.com",
        "phone": "+44 20 5555 0844",
        "linkedin": "linkedin.com/in/fionawalsh-aliyar",
        "department": "Client Delivery Division",
        "role": "Senior Delivery Manager",
        "seniority": "Lead",
        "service_categories": ["delivery", "project_delivery", "implementation", "milestones", "client_projects"],
        "specializations": ["project delivery", "milestone tracking", "stakeholder management", "risk mitigation", "agile delivery", "resource planning", "client reporting"],
        "communication_style": "direct",
        "personality_traits": ["organised", "accountable", "calm", "decisive"],
        "tone_keywords": ["on-time", "transparent", "structured", "professional"],
        "email_signature": "Fiona Walsh\nSenior Delivery Manager\nAliyar Solutions — Client Delivery Division\nfiona.walsh@aliyarsolutions.com",
        "proposal_title": "Senior Delivery Manager — Project Delivery & Implementation",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Aisha Williams",
        "first_name": "Aisha",
        "email": "aisha.williams@aliyarsolutions.com",
        "phone": "+1 (646) 555-0955",
        "linkedin": "linkedin.com/in/aishawilliams-aliyar",
        "department": "Client Delivery Division",
        "role": "Implementation & Onboarding Specialist",
        "seniority": "Senior",
        "service_categories": ["implementation", "onboarding", "training", "client_setup", "technical_onboarding"],
        "specializations": ["technical onboarding", "client training", "system configuration", "documentation", "workflow setup", "handover protocols", "success planning"],
        "communication_style": "warm",
        "personality_traits": ["patient", "thorough", "encouraging", "organised"],
        "tone_keywords": ["smooth", "guided", "supportive", "clear"],
        "email_signature": "Aisha Williams\nImplementation & Onboarding Specialist\nAliyar Solutions — Client Delivery Division\naisha.williams@aliyarsolutions.com",
        "proposal_title": "Implementation Specialist — Technical Onboarding & Client Setup",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Diana Torres",
        "first_name": "Diana",
        "email": "diana.torres@aliyarsolutions.com",
        "phone": "+1 (512) 555-0166",
        "linkedin": "linkedin.com/in/dianatorres-aliyar",
        "department": "Customer Support Division",
        "role": "Technical Support Engineer",
        "seniority": "Mid",
        "service_categories": ["technical_support", "troubleshooting", "bug_triage", "sla", "helpdesk"],
        "specializations": ["technical troubleshooting", "bug triage", "SLA management", "helpdesk operations", "API debugging", "infrastructure support", "incident response"],
        "communication_style": "direct",
        "personality_traits": ["sharp", "calm", "solution-focused", "reliable"],
        "tone_keywords": ["technical", "responsive", "precise", "helpful"],
        "email_signature": "Diana Torres\nTechnical Support Engineer\nAliyar Solutions — Customer Support Division\ndiana.torres@aliyarsolutions.com",
        "proposal_title": "Technical Support Engineer — Helpdesk & Infrastructure Support",
        "is_active": True,
        "is_client_facing": True,
    },

    # ── DIVISION 4: INTELLIGENCE & RESEARCH ──────────────────────────────────

    {
        "name": "Patrick Moore",
        "first_name": "Patrick",
        "email": "patrick.moore@aliyarsolutions.com",
        "phone": "+44 20 5555 0277",
        "linkedin": "linkedin.com/in/patrickmoore-aliyar",
        "department": "Intelligence & Research Division",
        "role": "Market Intelligence Analyst",
        "seniority": "Senior",
        "service_categories": ["market_research", "competitive_intelligence", "industry_analysis", "trend_analysis", "market_sizing"],
        "specializations": ["competitive landscape analysis", "market sizing", "industry trend reports", "TAM/SAM/SOM modelling", "competitor profiling", "investment thesis research"],
        "communication_style": "consultative",
        "personality_traits": ["inquisitive", "analytical", "thorough", "strategic"],
        "tone_keywords": ["evidence-based", "strategic", "insightful", "comprehensive"],
        "email_signature": "Patrick Moore\nMarket Intelligence Analyst\nAliyar Solutions — Intelligence & Research Division\npatrick.moore@aliyarsolutions.com",
        "proposal_title": "Market Intelligence Analyst — Competitive Research & Industry Analysis",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "Kevin Park",
        "first_name": "Kevin",
        "email": "kevin.park@aliyarsolutions.com",
        "phone": "+1 (415) 555-0388",
        "linkedin": "linkedin.com/in/kevinpark-aliyar",
        "department": "Intelligence & Research Division",
        "role": "Competitive Intelligence Specialist",
        "seniority": "Mid",
        "service_categories": ["competitive_research", "win_loss_analysis", "battlecards", "prospect_research", "lead_intelligence"],
        "specializations": ["win/loss analysis", "battlecard creation", "prospect deep-dives", "technology stack analysis", "pricing intelligence", "sales enablement research"],
        "communication_style": "direct",
        "personality_traits": ["sharp", "resourceful", "strategic", "detail-obsessed"],
        "tone_keywords": ["tactical", "intelligence-led", "precise", "actionable"],
        "email_signature": "Kevin Park\nCompetitive Intelligence Specialist\nAliyar Solutions — Intelligence & Research Division\nkevin.park@aliyarsolutions.com",
        "proposal_title": "Competitive Intelligence Specialist — Win/Loss Analysis & Sales Enablement",
        "is_active": True,
        "is_client_facing": True,
    },

    # ── DIVISION 5: PEOPLE & OPERATIONS ──────────────────────────────────────

    {
        "name": "Marcus Johnson",
        "first_name": "Marcus",
        "email": "marcus.johnson@aliyarsolutions.com",
        "phone": "+1 (212) 555-0499",
        "linkedin": "linkedin.com/in/marcusjohnson-aliyar",
        "department": "Project Management Office",
        "role": "PMO Director",
        "seniority": "Lead",
        "service_categories": ["pmo", "project_management", "programme_management", "governance", "portfolio"],
        "specializations": ["PMO setup", "programme governance", "portfolio management", "Agile/Scrum", "risk management", "resource allocation", "executive reporting", "PMP/Prince2"],
        "communication_style": "direct",
        "personality_traits": ["structured", "accountable", "decisive", "strategic"],
        "tone_keywords": ["governance", "structured", "on-time", "accountable"],
        "email_signature": "Marcus Johnson\nPMO Director\nAliyar Solutions — Project Management Office\nmarcus.johnson@aliyarsolutions.com",
        "proposal_title": "PMO Director — Programme Governance & Portfolio Management",
        "is_active": True,
        "is_client_facing": True,
    },
    {
        "name": "James Chen",
        "first_name": "James",
        "email": "james.chen@aliyarsolutions.com",
        "phone": "+1 (646) 555-0600",
        "linkedin": "linkedin.com/in/jameschen-aliyar",
        "department": "Finance & Operations Division",
        "role": "Finance & Revenue Operations Manager",
        "seniority": "Senior",
        "service_categories": ["finance", "revenue_operations", "invoicing", "forecasting", "financial_reporting", "revops"],
        "specializations": ["revenue operations", "financial modelling", "invoice management", "cash flow forecasting", "pricing strategy", "financial reporting", "SaaS metrics"],
        "communication_style": "direct",
        "personality_traits": ["precise", "analytical", "trustworthy", "strategic"],
        "tone_keywords": ["accurate", "transparent", "financial", "growth-focused"],
        "email_signature": "James Chen\nFinance & Revenue Operations Manager\nAliyar Solutions — Finance & Operations Division\njames.chen@aliyarsolutions.com",
        "proposal_title": "Finance & Revenue Operations Manager — Financial Strategy & RevOps",
        "is_active": True,
        "is_client_facing": False,
    },
    {
        "name": "Natalie Ross",
        "first_name": "Natalie",
        "email": "natalie.ross@aliyarsolutions.com",
        "phone": "+44 20 5555 0711",
        "linkedin": "linkedin.com/in/natalieross-aliyar",
        "department": "People & Feedback Department",
        "role": "Talent Acquisition & L&D Specialist",
        "seniority": "Senior",
        "service_categories": ["talent_acquisition", "recruitment", "learning_development", "training", "culture"],
        "specializations": ["technical recruitment", "talent pipeline building", "learning & development programmes", "performance frameworks", "culture building", "employer branding"],
        "communication_style": "warm",
        "personality_traits": ["people-focused", "energetic", "empathetic", "organised"],
        "tone_keywords": ["people-first", "growth-oriented", "inclusive", "engaging"],
        "email_signature": "Natalie Ross\nTalent Acquisition & L&D Specialist\nAliyar Solutions — People & Feedback Department\nnatalie.ross@aliyarsolutions.com",
        "proposal_title": "Talent Acquisition & L&D Specialist — Recruitment & Team Development",
        "is_active": True,
        "is_client_facing": False,
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
    "nps":                  "Priya Nair",
    "tickets":              "James Harlow",
    "escalation":           "James Harlow",
    "issue_resolution":     "James Harlow",
    "client_care":          "James Harlow",
    "surveys":                      "Priya Nair",
    "improvement":                  "Priya Nair",
    # Engineering
    "backend":                      "Alex Foster",
    "api_development":              "Alex Foster",
    "database":                     "Alex Foster",
    "microservices":                "Alex Foster",
    "python":                       "Alex Foster",
    "fastapi":                      "Alex Foster",
    "frontend":                     "Maya Chen",
    "ui_development":               "Maya Chen",
    "react":                        "Maya Chen",
    "web_apps":                     "Maya Chen",
    "dashboards":                   "Maya Chen",
    "machine_learning":             "Dr. Ryan Patel",
    "nlp":                          "Dr. Ryan Patel",
    "ai_models":                    "Dr. Ryan Patel",
    "llm":                          "Dr. Ryan Patel",
    "embeddings":                   "Dr. Ryan Patel",
    "vector_search":                "Dr. Ryan Patel",
    "data_science":                 "Isabella Grant",
    "predictive_modelling":         "Isabella Grant",
    "data_pipelines":               "Isabella Grant",
    "penetration_testing":          "Connor Walsh",
    "ethical_hacking":              "Connor Walsh",
    "red_team":                     "Connor Walsh",
    "vulnerability_research":       "Connor Walsh",
    "security_audit":               "Connor Walsh",
    "gdpr":                         "Amanda Price",
    "legal":                        "Amanda Price",
    "contracts":                    "Amanda Price",
    "risk_management":              "Amanda Price",
    "iso27001":                     "Amanda Price",
    # Revenue & Growth
    "business_development":         "Tyler Brooks",
    "partnerships":                 "Tyler Brooks",
    "enterprise_sales":             "Tyler Brooks",
    "rfp":                          "Tyler Brooks",
    "strategic_accounts":           "Tyler Brooks",
    "marketing":                    "Victoria Lane",
    "brand":                        "Victoria Lane",
    "demand_generation":            "Victoria Lane",
    "campaigns":                    "Victoria Lane",
    "gtm":                          "Victoria Lane",
    "seo":                          "Hassan Ahmed",
    "digital_marketing":            "Hassan Ahmed",
    "paid_ads":                     "Hassan Ahmed",
    "email_marketing":              "Hassan Ahmed",
    "lead_generation":              "Hassan Ahmed",
    "copywriting":                  "Sarah Kim",
    "thought_leadership":           "Sarah Kim",
    "case_studies":                 "Sarah Kim",
    "whitepapers":                  "Sarah Kim",
    # Creative
    "design":                       "Zoe Mitchell",
    "branding":                     "Zoe Mitchell",
    "visual_identity":              "Zoe Mitchell",
    "graphic_design":               "Zoe Mitchell",
    "ux_design":                    "Ben Carter",
    "user_research":                "Ben Carter",
    "prototyping":                  "Ben Carter",
    "product_design":               "Ben Carter",
    # Delivery
    "delivery":                     "Fiona Walsh",
    "project_delivery":             "Fiona Walsh",
    "implementation":               "Aisha Williams",
    "training":                     "Aisha Williams",
    "technical_onboarding":         "Aisha Williams",
    "technical_support":            "Diana Torres",
    "troubleshooting":              "Diana Torres",
    "helpdesk":                     "Diana Torres",
    # Intelligence
    "market_research":              "Patrick Moore",
    "competitive_intelligence":     "Patrick Moore",
    "industry_analysis":            "Patrick Moore",
    "trend_analysis":               "Patrick Moore",
    "competitive_research":         "Kevin Park",
    "win_loss_analysis":            "Kevin Park",
    "battlecards":                  "Kevin Park",
    "prospect_research":            "Kevin Park",
    # Operations
    "pmo":                          "Marcus Johnson",
    "project_management":           "Marcus Johnson",
    "programme_management":         "Marcus Johnson",
    "portfolio":                    "Marcus Johnson",
    "finance":                      "James Chen",
    "revenue_operations":           "James Chen",
    "invoicing":                    "James Chen",
    "forecasting":                  "James Chen",
    "revops":                       "James Chen",
    "talent_acquisition":           "Natalie Ross",
    "recruitment":                  "Natalie Ross",
    "learning_development":         "Natalie Ross",
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
