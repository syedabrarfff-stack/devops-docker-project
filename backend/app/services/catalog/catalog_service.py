"""
Aliyar Solutions Service Catalog — 30 service divisions seeded and queryable.
"""
import logging
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.service_catalog import ServiceDivision

logger = logging.getLogger(__name__)
SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

# ─── Seed data ────────────────────────────────────────────────────────────────

SEED_DIVISIONS = [
    # ── Sales & Marketing ──────────────────────────────────────────────────────
    {
        "code": "AI_LEAD_GEN",
        "name": "AI Lead Generation Systems",
        "division_group": "Sales & Marketing",
        "description": "Fully automated lead discovery and qualification pipelines that identify high-intent prospects across LinkedIn, Apollo, and web sources. Our team delivers pre-qualified, enriched lead lists with contact intelligence.",
        "deliverables": ["Enriched lead database", "ICP scoring system", "Weekly lead pipeline", "CRM integration", "Lead quality reports"],
        "technologies": ["Apollo.io", "LinkedIn Sales Navigator", "Python scraping", "PostgreSQL", "AI scoring models"],
        "target_industries": ["SaaS", "Agencies", "Consulting", "B2B Services", "Tech Startups"],
        "pricing_model": "retainer",
        "price_range_usd": {"min": 800, "max": 3000},
        "duration_estimate": "Ongoing monthly",
        "is_featured": True,
        "sort_order": 1,
    },
    {
        "code": "AI_OUTREACH",
        "name": "AI Outreach Automation",
        "division_group": "Sales & Marketing",
        "description": "Intelligent, personalized cold outreach sequences across email and LinkedIn. Automated follow-ups, A/B testing, and reply detection ensure maximum deliverability and response rates without the spam risk.",
        "deliverables": ["Email sequence design", "LinkedIn automation", "A/B testing setup", "Inbox warm-up", "Reply handling workflow", "Analytics dashboard"],
        "technologies": ["Instantly.ai", "Lemlist", "LinkedIn APIs", "SMTP automation", "OpenAI personalization"],
        "target_industries": ["SaaS", "Agencies", "Recruiting", "Real Estate", "Professional Services"],
        "pricing_model": "retainer",
        "price_range_usd": {"min": 600, "max": 2500},
        "duration_estimate": "Ongoing monthly",
        "is_featured": True,
        "sort_order": 2,
    },
    {
        "code": "AI_SALES_SYSTEMS",
        "name": "AI Sales Systems",
        "division_group": "Sales & Marketing",
        "description": "End-to-end intelligent sales infrastructure: from ICP discovery to proposal automation, follow-up sequences, objection handling playbooks, and pipeline intelligence reporting.",
        "deliverables": ["Sales funnel design", "Proposal templates", "Objection playbooks", "Pipeline analytics", "AI follow-up engine"],
        "technologies": ["HubSpot", "CRM integrations", "Claude AI", "OpenAI", "PostgreSQL analytics"],
        "target_industries": ["Agencies", "Consultancies", "SaaS", "Professional Services", "Enterprise"],
        "pricing_model": "project",
        "price_range_usd": {"min": 1500, "max": 8000},
        "duration_estimate": "3–6 weeks",
        "is_featured": False,
        "sort_order": 3,
    },
    {
        "code": "CRM_AUTOMATION",
        "name": "CRM Automation",
        "division_group": "Sales & Marketing",
        "description": "Custom CRM configuration, workflow automation, and data pipeline setup. We transform your CRM from a contact database into an active revenue operations engine with automated scoring and lifecycle triggers.",
        "deliverables": ["CRM workflow setup", "Lead scoring rules", "Automation triggers", "Data cleanup", "Custom dashboards", "Team training"],
        "technologies": ["HubSpot", "Salesforce", "Zoho", "Apollo.io", "Zapier", "Custom APIs"],
        "target_industries": ["SaaS", "E-commerce", "Agencies", "Real Estate", "Healthcare"],
        "pricing_model": "project",
        "price_range_usd": {"min": 1000, "max": 5000},
        "duration_estimate": "2–4 weeks",
        "is_featured": False,
        "sort_order": 4,
    },
    # ── AI Automation ──────────────────────────────────────────────────────────
    {
        "code": "AI_APPT_BOOKING",
        "name": "AI Appointment Booking",
        "division_group": "AI Automation",
        "description": "Fully automated appointment scheduling systems that qualify leads, check availability, send confirmations, handle rescheduling, and send intelligent reminders — all without human intervention.",
        "deliverables": ["Booking flow design", "Calendar integration", "SMS/email confirmations", "Rescheduling logic", "CRM sync", "Analytics"],
        "technologies": ["Calendly API", "Google Calendar", "Twilio SMS", "n8n", "OpenAI NLP"],
        "target_industries": ["Clinics", "Consultancies", "Coaches", "Law Firms", "Hotels", "Restaurants"],
        "pricing_model": "project",
        "price_range_usd": {"min": 800, "max": 3500},
        "duration_estimate": "1–3 weeks",
        "is_featured": True,
        "sort_order": 5,
    },
    {
        "code": "AI_VOICE_RECEPTIONIST",
        "name": "AI Voice Receptionist Systems",
        "division_group": "AI Automation",
        "description": "24/7 intelligent voice receptionist that answers calls, qualifies inquiries, books appointments, handles FAQs, and escalates complex issues to human staff — all with a natural, professional voice.",
        "deliverables": ["Voice agent design", "FAQ knowledge base", "Call routing logic", "CRM integration", "Call recordings & transcripts", "Weekly reports"],
        "technologies": ["ElevenLabs", "Twilio Voice", "OpenAI GPT", "Whisper STT", "Custom NLP pipelines"],
        "target_industries": ["Clinics", "Hotels", "Restaurants", "Law Firms", "Real Estate", "Service Businesses"],
        "pricing_model": "retainer",
        "price_range_usd": {"min": 1200, "max": 5000},
        "duration_estimate": "2–4 weeks setup",
        "is_featured": True,
        "sort_order": 6,
    },
    {
        "code": "BIZ_WORKFLOW_AUTO",
        "name": "Business Workflow Automation",
        "division_group": "AI Automation",
        "description": "Systematic elimination of manual, repetitive business processes. We audit your operations, map workflows, and deploy automated systems that reduce operational overhead and human error.",
        "deliverables": ["Process audit", "Workflow maps", "Automation deployment", "Documentation", "Team handoff training"],
        "technologies": ["n8n", "Zapier", "Make.com", "Python", "REST APIs", "Webhooks"],
        "target_industries": ["E-commerce", "Agencies", "SaaS", "Logistics", "Healthcare", "Finance"],
        "pricing_model": "project",
        "price_range_usd": {"min": 1500, "max": 10000},
        "duration_estimate": "3–8 weeks",
        "is_featured": False,
        "sort_order": 7,
    },
    {
        "code": "EXEC_AUTOMATION",
        "name": "Executive Automation Systems",
        "division_group": "AI Automation",
        "description": "High-level autonomous operational infrastructure for executive teams: automated reporting, decision support systems, strategic briefings, KPI monitoring, and intelligent alert management.",
        "deliverables": ["Executive dashboard", "Automated reporting", "KPI alert system", "Decision briefings", "Operational SOPs"],
        "technologies": ["FastAPI", "PostgreSQL", "Claude AI", "Grafana", "CloudWatch", "Slack integrations"],
        "target_industries": ["Enterprise", "SaaS", "Agencies", "Investment Firms", "Tech Companies"],
        "pricing_model": "retainer",
        "price_range_usd": {"min": 3000, "max": 15000},
        "duration_estimate": "4–8 weeks setup",
        "is_featured": True,
        "sort_order": 8,
    },
    # ── Cloud & DevOps ─────────────────────────────────────────────────────────
    {
        "code": "DEVOPS_INFRA",
        "name": "DevOps Infrastructure Services",
        "division_group": "Cloud & DevOps",
        "description": "Complete DevOps transformation: culture, tooling, pipeline design, environment standardization, and monitoring. We establish engineering best practices that scale with your organization.",
        "deliverables": ["DevOps assessment", "Pipeline design", "Environment setup", "Runbooks", "Team training"],
        "technologies": ["Docker", "GitHub Actions", "Jenkins", "Prometheus", "Grafana", "ELK Stack"],
        "target_industries": ["SaaS", "FinTech", "HealthTech", "E-commerce", "Startups"],
        "pricing_model": "project",
        "price_range_usd": {"min": 2000, "max": 12000},
        "duration_estimate": "4–10 weeks",
        "is_featured": False,
        "sort_order": 9,
    },
    {
        "code": "AWS_ARCHITECTURE",
        "name": "AWS Cloud Architecture",
        "division_group": "Cloud & DevOps",
        "description": "Production-grade AWS infrastructure design and implementation: VPC architecture, ECS/EKS workloads, RDS, Redis, S3, Secrets Manager, Route53, ACM, and multi-region resilience planning.",
        "deliverables": ["Architecture diagram", "Terraform IaC", "VPC + networking", "ECS/EKS setup", "RDS + Redis", "CloudWatch monitoring", "Runbooks"],
        "technologies": ["AWS ECS", "Terraform", "RDS PostgreSQL", "ElastiCache", "ALB", "Route53", "Secrets Manager"],
        "target_industries": ["SaaS", "FinTech", "HealthTech", "E-commerce", "Enterprise"],
        "pricing_model": "project",
        "price_range_usd": {"min": 3000, "max": 20000},
        "duration_estimate": "3–8 weeks",
        "is_featured": True,
        "sort_order": 10,
    },
    {
        "code": "DOCKER_DEPLOY",
        "name": "Docker Deployments",
        "division_group": "Cloud & DevOps",
        "description": "Containerization of applications and services using Docker best practices: multi-stage builds, optimized images, docker-compose environments, and production-ready container orchestration.",
        "deliverables": ["Dockerfiles", "docker-compose configs", "Multi-stage build optimization", "Registry setup", "Deployment documentation"],
        "technologies": ["Docker", "Docker Compose", "ECR", "DockerHub", "Nginx", "Alpine Linux"],
        "target_industries": ["SaaS", "Startups", "Agencies", "Any Software Company"],
        "pricing_model": "project",
        "price_range_usd": {"min": 800, "max": 4000},
        "duration_estimate": "1–3 weeks",
        "is_featured": False,
        "sort_order": 11,
    },
    {
        "code": "CICD_AUTO",
        "name": "CI/CD Automation",
        "division_group": "Cloud & DevOps",
        "description": "Automated build, test, and deployment pipelines that eliminate manual deployments. Every code push triggers automated testing, security scanning, image building, and deployment with rollback capability.",
        "deliverables": ["Pipeline design", "GitHub Actions / Jenkins config", "Test automation hooks", "Deployment gates", "Notification setup"],
        "technologies": ["GitHub Actions", "Jenkins", "Docker", "ECR/DockerHub", "Terraform", "Slack webhooks"],
        "target_industries": ["SaaS", "FinTech", "Startups", "Enterprise", "E-commerce"],
        "pricing_model": "project",
        "price_range_usd": {"min": 1000, "max": 5000},
        "duration_estimate": "1–3 weeks",
        "is_featured": True,
        "sort_order": 12,
    },
    {
        "code": "JENKINS_INFRA",
        "name": "Jenkins Infrastructure",
        "division_group": "Cloud & DevOps",
        "description": "Enterprise Jenkins setup: master-agent architecture, shared libraries, declarative pipelines, plugin management, security hardening, and integration with source control and deployment targets.",
        "deliverables": ["Jenkins server setup", "Pipeline templates", "Shared library", "Agent configuration", "Plugin audit", "Security hardening"],
        "technologies": ["Jenkins", "Docker agents", "Groovy DSL", "GitHub", "AWS", "Kubernetes"],
        "target_industries": ["Enterprise", "FinTech", "Large Engineering Teams"],
        "pricing_model": "project",
        "price_range_usd": {"min": 1500, "max": 7000},
        "duration_estimate": "2–4 weeks",
        "is_featured": False,
        "sort_order": 13,
    },
    {
        "code": "TERRAFORM_AUTO",
        "name": "Terraform Infrastructure Automation",
        "division_group": "Cloud & DevOps",
        "description": "Infrastructure as Code using Terraform: modular, reusable configurations for AWS/GCP/Azure. State management, remote backends, workspace strategies, and GitOps-aligned deployment workflows.",
        "deliverables": ["Terraform modules", "State backend setup", "Variable management", "Workspace strategy", "Documentation"],
        "technologies": ["Terraform", "AWS", "S3 remote state", "Terraform Cloud", "GitHub Actions"],
        "target_industries": ["SaaS", "Enterprise", "FinTech", "Cloud-Native Companies"],
        "pricing_model": "project",
        "price_range_usd": {"min": 2000, "max": 10000},
        "duration_estimate": "2–6 weeks",
        "is_featured": True,
        "sort_order": 14,
    },
    {
        "code": "ANSIBLE_AUTO",
        "name": "Ansible Automation",
        "division_group": "Cloud & DevOps",
        "description": "Server configuration management and deployment automation using Ansible: playbooks, roles, inventory management, secrets handling, and idempotent provisioning for consistent environments.",
        "deliverables": ["Ansible playbooks", "Role library", "Inventory structure", "Secrets management", "Documentation"],
        "technologies": ["Ansible", "Ansible Vault", "AWS EC2", "Linux", "Python"],
        "target_industries": ["Enterprise", "FinTech", "Traditional IT", "Data Centers"],
        "pricing_model": "project",
        "price_range_usd": {"min": 1500, "max": 6000},
        "duration_estimate": "2–4 weeks",
        "is_featured": False,
        "sort_order": 15,
    },
    {
        "code": "KUBERNETES_INFRA",
        "name": "Kubernetes Infrastructure",
        "division_group": "Cloud & DevOps",
        "description": "Production Kubernetes clusters on AWS EKS or self-managed: namespace design, RBAC, Helm chart authoring, autoscaling, persistent storage, ingress controllers, and GitOps with ArgoCD.",
        "deliverables": ["Cluster setup", "Namespace/RBAC design", "Helm charts", "Autoscaling config", "Monitoring stack", "Runbooks"],
        "technologies": ["Kubernetes", "AWS EKS", "Helm", "ArgoCD", "Prometheus", "Grafana", "Istio"],
        "target_industries": ["Enterprise", "SaaS", "FinTech", "HealthTech", "Scale-ups"],
        "pricing_model": "project",
        "price_range_usd": {"min": 5000, "max": 25000},
        "duration_estimate": "4–10 weeks",
        "is_featured": True,
        "sort_order": 16,
    },
    {
        "code": "MONITORING_LOGGING",
        "name": "Monitoring & Logging Systems",
        "division_group": "Cloud & DevOps",
        "description": "Full-stack observability: metrics, logs, traces, and alerting. We deploy Prometheus + Grafana dashboards, centralized logging with ELK/CloudWatch, distributed tracing, and intelligent alerting that pages the right team.",
        "deliverables": ["Monitoring stack", "Custom dashboards", "Alert rules", "Log aggregation", "SLA reports", "Runbooks"],
        "technologies": ["Prometheus", "Grafana", "CloudWatch", "ELK Stack", "OpenTelemetry", "PagerDuty"],
        "target_industries": ["SaaS", "Enterprise", "FinTech", "E-commerce", "Healthcare"],
        "pricing_model": "project",
        "price_range_usd": {"min": 2000, "max": 10000},
        "duration_estimate": "2–5 weeks",
        "is_featured": False,
        "sort_order": 17,
    },
    {
        "code": "SAAS_DEPLOY",
        "name": "SaaS Deployment Services",
        "division_group": "Cloud & DevOps",
        "description": "Complete SaaS product infrastructure: multi-tenant architecture, deployment automation, database provisioning, SSL/TLS, CDN, autoscaling, and production readiness review before every launch.",
        "deliverables": ["Architecture design", "Multi-tenant setup", "Deployment pipeline", "SSL/CDN config", "Load testing", "Launch checklist"],
        "technologies": ["AWS", "Docker", "PostgreSQL", "Redis", "CloudFront", "Route53", "Terraform"],
        "target_industries": ["SaaS Startups", "Product Companies", "Tech Agencies"],
        "pricing_model": "project",
        "price_range_usd": {"min": 3000, "max": 18000},
        "duration_estimate": "4–8 weeks",
        "is_featured": True,
        "sort_order": 18,
    },
    # ── Security ───────────────────────────────────────────────────────────────
    {
        "code": "CYBERSEC_OPS",
        "name": "Cybersecurity Operations",
        "division_group": "Security",
        "description": "Proactive security operations: infrastructure hardening, IAM optimization, access control auditing, threat detection setup, security monitoring, and incident response planning for cloud and application environments.",
        "deliverables": ["Security audit report", "Hardening checklist", "IAM review", "Threat detection rules", "Incident response playbook"],
        "technologies": ["AWS Security Hub", "GuardDuty", "IAM", "VPC security groups", "WAF", "CloudTrail"],
        "target_industries": ["FinTech", "HealthTech", "E-commerce", "Enterprise", "SaaS"],
        "pricing_model": "project",
        "price_range_usd": {"min": 2000, "max": 12000},
        "duration_estimate": "2–6 weeks",
        "is_featured": True,
        "sort_order": 19,
    },
    {
        "code": "VULN_ASSESSMENT",
        "name": "Vulnerability Assessment",
        "division_group": "Security",
        "description": "Systematic identification and prioritization of security vulnerabilities in applications, infrastructure, and APIs. Detailed remediation roadmap with risk-ranked findings and executive summary report.",
        "deliverables": ["Vulnerability report", "Risk matrix", "Remediation roadmap", "Executive summary", "Re-test validation"],
        "technologies": ["OWASP tools", "Nmap", "Trivy", "Snyk", "Semgrep", "AWS Inspector"],
        "target_industries": ["FinTech", "HealthTech", "E-commerce", "Enterprise", "Any Cloud Business"],
        "pricing_model": "project",
        "price_range_usd": {"min": 1500, "max": 8000},
        "duration_estimate": "1–3 weeks",
        "is_featured": False,
        "sort_order": 20,
    },
    # ── Content & Media ────────────────────────────────────────────────────────
    {
        "code": "AI_CONTENT_AUTO",
        "name": "AI Content Automation",
        "division_group": "Content & Media",
        "description": "Scalable content production pipelines: blog articles, LinkedIn posts, email newsletters, and thought leadership content produced at volume with consistent brand voice and SEO optimization.",
        "deliverables": ["Content calendar", "Article templates", "Brand voice guide", "SEO optimization", "Publishing automation", "Analytics"],
        "technologies": ["Claude AI", "OpenAI", "WordPress APIs", "Ghost CMS", "Notion", "Zapier"],
        "target_industries": ["SaaS", "Agencies", "Consulting", "E-commerce", "Personal Brands"],
        "pricing_model": "retainer",
        "price_range_usd": {"min": 500, "max": 3000},
        "duration_estimate": "Ongoing monthly",
        "is_featured": False,
        "sort_order": 21,
    },
    {
        "code": "YOUTUBE_AUTO",
        "name": "YouTube Automation Pipelines",
        "division_group": "Content & Media",
        "description": "End-to-end YouTube channel automation: niche research, AI script writing, voiceover production, thumbnail generation, video editing pipelines, SEO optimization, scheduling, and performance analytics.",
        "deliverables": ["Channel strategy", "Script templates", "Voiceover pipeline", "Thumbnail system", "Upload automation", "Analytics dashboard"],
        "technologies": ["OpenAI", "ElevenLabs", "Runway ML", "YouTube API", "Canva API", "Python pipelines"],
        "target_industries": ["Content Creators", "Agencies", "E-commerce Brands", "SaaS Marketing"],
        "pricing_model": "retainer",
        "price_range_usd": {"min": 800, "max": 4000},
        "duration_estimate": "2 weeks setup + ongoing",
        "is_featured": True,
        "sort_order": 22,
    },
    {
        "code": "SOCIAL_MEDIA_MGMT",
        "name": "Social Media Management",
        "division_group": "Content & Media",
        "description": "AI-powered social media management: content creation, scheduling, engagement monitoring, growth analytics, and multi-platform publishing across LinkedIn, Twitter/X, Instagram, and Facebook.",
        "deliverables": ["Content calendar", "Post templates", "Scheduling setup", "Engagement reports", "Growth analytics"],
        "technologies": ["Buffer", "Hootsuite", "OpenAI", "Canva", "Analytics APIs"],
        "target_industries": ["E-commerce", "Agencies", "Personal Brands", "SaaS", "Retail"],
        "pricing_model": "retainer",
        "price_range_usd": {"min": 400, "max": 2000},
        "duration_estimate": "Ongoing monthly",
        "is_featured": False,
        "sort_order": 23,
    },
    {
        "code": "GRAPHIC_DESIGN",
        "name": "Graphic Design Systems",
        "division_group": "Content & Media",
        "description": "AI-assisted graphic design production: brand identity systems, social media creatives, marketing assets, presentation templates, infographics, and scalable design pipelines for ongoing content needs.",
        "deliverables": ["Brand style guide", "Social media templates", "Marketing collateral", "Presentation deck", "Design asset library"],
        "technologies": ["Figma", "Adobe Creative Suite", "Midjourney", "DALL-E", "Canva Pro"],
        "target_industries": ["Startups", "E-commerce", "Agencies", "Personal Brands", "SaaS"],
        "pricing_model": "project",
        "price_range_usd": {"min": 500, "max": 4000},
        "duration_estimate": "1–4 weeks",
        "is_featured": False,
        "sort_order": 24,
    },
    {
        "code": "VIDEO_EDITING",
        "name": "Video Editing Pipelines",
        "division_group": "Content & Media",
        "description": "Automated and semi-automated video production workflows: editing, captioning, color grading, intro/outro automation, format conversion, and multi-platform export pipelines.",
        "deliverables": ["Editing workflow setup", "Caption automation", "Template library", "Export pipeline", "Multi-platform formats"],
        "technologies": ["Premiere Pro", "DaVinci Resolve", "Runway ML", "Python automation", "FFmpeg"],
        "target_industries": ["Content Creators", "Agencies", "E-commerce", "Corporate Training"],
        "pricing_model": "project",
        "price_range_usd": {"min": 400, "max": 3000},
        "duration_estimate": "1–2 weeks per project",
        "is_featured": False,
        "sort_order": 25,
    },
    # ── Digital Products ───────────────────────────────────────────────────────
    {
        "code": "WEBSITE_DEV",
        "name": "Website Development",
        "division_group": "Digital Products",
        "description": "High-performance, conversion-optimized websites and landing pages. Modern stack (React/Next.js), fast load times, mobile-first design, CMS integration, and SEO foundation.",
        "deliverables": ["Design mockups", "Frontend development", "CMS integration", "SEO setup", "Performance optimization", "Deployment"],
        "technologies": ["Next.js", "React", "Tailwind CSS", "Vercel", "Contentful", "Sanity"],
        "target_industries": ["Any Business Needing Web Presence"],
        "pricing_model": "project",
        "price_range_usd": {"min": 1500, "max": 10000},
        "duration_estimate": "3–6 weeks",
        "is_featured": False,
        "sort_order": 26,
    },
    {
        "code": "CLIENT_PORTAL",
        "name": "Client Portal Systems",
        "division_group": "Digital Products",
        "description": "Custom client portal development: project tracking, deliverable management, invoice viewing, communication threads, document sharing, and reporting dashboards — all under your brand.",
        "deliverables": ["Portal design", "Auth system", "Project tracking", "Document system", "Client dashboards", "Deployment"],
        "technologies": ["React", "FastAPI", "PostgreSQL", "AWS S3", "Stripe billing", "WebSockets"],
        "target_industries": ["Agencies", "Consulting Firms", "Law Firms", "Accounting Firms"],
        "pricing_model": "project",
        "price_range_usd": {"min": 3000, "max": 15000},
        "duration_estimate": "4–8 weeks",
        "is_featured": True,
        "sort_order": 27,
    },
    {
        "code": "OPS_DASHBOARDS",
        "name": "Operational Dashboards",
        "division_group": "Digital Products",
        "description": "Real-time operational intelligence dashboards: live KPI monitoring, infrastructure health, sales pipeline visibility, financial metrics, and custom reporting — all in a premium, cinematic interface.",
        "deliverables": ["Dashboard design", "Data pipeline", "Live metrics", "Alert system", "Export reports", "Deployment"],
        "technologies": ["React", "Grafana", "PostgreSQL", "WebSockets", "CloudWatch", "Recharts"],
        "target_industries": ["SaaS", "Enterprise", "E-commerce", "Logistics", "FinTech"],
        "pricing_model": "project",
        "price_range_usd": {"min": 2000, "max": 12000},
        "duration_estimate": "3–6 weeks",
        "is_featured": False,
        "sort_order": 28,
    },
    # ── Intelligence & Analytics ───────────────────────────────────────────────
    {
        "code": "AI_RESEARCH_OPS",
        "name": "AI Research Operations",
        "division_group": "Intelligence & Analytics",
        "description": "Autonomous market intelligence operations: competitor analysis, niche opportunity mapping, technology landscape reports, pricing intelligence, and strategic asymmetric opportunity discovery.",
        "deliverables": ["Market analysis reports", "Competitor profiles", "Opportunity maps", "Technology radar", "Strategic recommendations"],
        "technologies": ["Claude AI", "GPT-4o", "Web scraping", "Crunchbase", "SimilarWeb", "Google Trends"],
        "target_industries": ["Investment Firms", "Enterprise Strategy", "Startups", "Agencies", "SaaS"],
        "pricing_model": "project",
        "price_range_usd": {"min": 1500, "max": 8000},
        "duration_estimate": "1–3 weeks",
        "is_featured": True,
        "sort_order": 29,
    },
    {
        "code": "BI_ANALYTICS",
        "name": "Business Intelligence Analytics",
        "division_group": "Intelligence & Analytics",
        "description": "Custom business intelligence infrastructure: data warehouse design, ETL pipelines, predictive analytics, revenue forecasting, churn prediction, and executive reporting systems.",
        "deliverables": ["BI architecture", "Data pipelines", "Analytics dashboards", "Forecast models", "Executive reports", "Data documentation"],
        "technologies": ["PostgreSQL", "dbt", "Metabase", "Grafana", "Python pandas", "scikit-learn"],
        "target_industries": ["SaaS", "E-commerce", "FinTech", "Logistics", "Healthcare", "Enterprise"],
        "pricing_model": "project",
        "price_range_usd": {"min": 3000, "max": 20000},
        "duration_estimate": "4–10 weeks",
        "is_featured": False,
        "sort_order": 30,
    },
]


CAPABILITY_MODULES = [
    {
        "code": "SCOUT",
        "name": "Lead Intelligence",
        "division": "Revenue Operations",
        "human_interface_executive": "James Whitfield",
        "agent_layer": ["Lead discovery", "ICP scoring", "market signal analysis"],
        "kpi_targets": ["20 qualified discoveries/day", "lead quality trend", "source conversion"],
        "description": "Finds, enriches, scores, and prioritizes prospects before outreach begins.",
    },
    {
        "code": "HERALD",
        "name": "Outreach",
        "division": "Revenue Operations",
        "human_interface_executive": "Darren Mitchell",
        "agent_layer": ["Email sequencing", "reply handling", "personalization"],
        "kpi_targets": ["48 emails/day max", "reply rate", "positive intent rate"],
        "description": "Runs governed outreach with compliant sequencing, personalization, and response routing.",
    },
    {
        "code": "NEXUS-R",
        "name": "CRM Intelligence",
        "division": "Revenue Operations",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["CRM hygiene", "pipeline intelligence", "contact history"],
        "kpi_targets": ["clean lifecycle states", "deal velocity", "stale lead reduction"],
        "description": "Maintains revenue truth across CRM, contacts, deals, lifecycle state, and client context.",
    },
    {
        "code": "ORACLE-S",
        "name": "Sales Forecasting",
        "division": "Revenue Operations",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["forecast modeling", "probability scoring", "close-risk analysis"],
        "kpi_targets": ["forecast accuracy", "close probability", "pipeline risk alerts"],
        "description": "Predicts revenue outcomes, deal risk, and next-best commercial actions.",
    },
    {
        "code": "PRISM",
        "name": "Workflow Automation",
        "division": "AI Automation",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["process mapping", "workflow design", "automation deployment"],
        "kpi_targets": ["manual hours removed", "automation uptime", "handoff accuracy"],
        "description": "Turns repeatable business operations into governed automated workflows.",
    },
    {
        "code": "ECHO",
        "name": "Agent Deployment",
        "division": "AI Automation",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["agent design", "tool routing", "capability governance"],
        "kpi_targets": ["agent success rate", "approval compliance", "fallback coverage"],
        "description": "Deploys specialized AI agents with clear tools, memory, permissions, and boundaries.",
    },
    {
        "code": "PULSE",
        "name": "Voice Systems",
        "division": "AI Automation",
        "human_interface_executive": "Lucas Reed",
        "agent_layer": ["voice intake", "call transcription", "speech synthesis"],
        "kpi_targets": ["call coverage", "handoff accuracy", "voice response latency"],
        "description": "Creates voice-first client and operations interfaces for calls, reception, and briefings.",
    },
    {
        "code": "SIGNAL",
        "name": "Communication",
        "division": "AI Automation",
        "human_interface_executive": "Lucas Reed",
        "agent_layer": ["notifications", "message routing", "communication memory"],
        "kpi_targets": ["response SLA", "message clarity", "missed-update prevention"],
        "description": "Coordinates structured communication across Captain, clients, departments, and agents.",
    },
    {
        "code": "BRIDGE",
        "name": "Scheduling",
        "division": "AI Automation",
        "human_interface_executive": "Olivia Bennett",
        "agent_layer": ["calendar orchestration", "call prep", "meeting follow-up"],
        "kpi_targets": ["booking completion", "briefing readiness", "no-show reduction"],
        "description": "Connects calendar events to briefings, client context, reminders, and post-call actions.",
    },
    {
        "code": "ATLAS-CI",
        "name": "AWS Architecture",
        "division": "Cloud & DevOps",
        "human_interface_executive": "David Carter",
        "agent_layer": ["cloud topology", "runtime design", "AWS governance"],
        "kpi_targets": ["uptime", "cost efficiency", "deployment readiness"],
        "description": "Designs AWS runtime foundations, networking, compute, storage, and production governance.",
    },
    {
        "code": "NEXUS-TF",
        "name": "Terraform",
        "division": "Cloud & DevOps",
        "human_interface_executive": "Nathan Scott",
        "agent_layer": ["IaC modules", "state governance", "environment reproducibility"],
        "kpi_targets": ["drift prevention", "rebuild speed", "change auditability"],
        "description": "Turns cloud infrastructure into repeatable, auditable, version-controlled IaC modules.",
    },
    {
        "code": "SIGNAL-CD",
        "name": "CI/CD",
        "division": "Cloud & DevOps",
        "human_interface_executive": "Nathan Scott",
        "agent_layer": ["build pipelines", "deployment gates", "rollback paths"],
        "kpi_targets": ["deploy success", "rollback time", "test gate coverage"],
        "description": "Automates build, test, deployment, rollback, and release governance.",
    },
    {
        "code": "HELM",
        "name": "Kubernetes",
        "division": "Cloud & DevOps",
        "human_interface_executive": "Michael Hayes",
        "agent_layer": ["cluster design", "workload orchestration", "autoscaling"],
        "kpi_targets": ["cluster health", "resource efficiency", "resilience"],
        "description": "Packages scalable workloads for Kubernetes and future cloud-native orchestration.",
    },
    {
        "code": "RADAR",
        "name": "Observability",
        "division": "Cloud & DevOps",
        "human_interface_executive": "Michael Hayes",
        "agent_layer": ["metrics", "logs", "traces", "alerts"],
        "kpi_targets": ["MTTD", "MTTR", "alert precision"],
        "description": "Makes system health visible through telemetry, dashboards, alerts, and operational evidence.",
    },
    {
        "code": "CIPHER",
        "name": "Security Operations",
        "division": "Security & Compliance",
        "human_interface_executive": "Daniel Brooks",
        "agent_layer": ["access review", "threat monitoring", "security posture"],
        "kpi_targets": ["risk reduction", "IAM hygiene", "threat response"],
        "description": "Protects cloud, application, and operational surfaces with continuous security discipline.",
    },
    {
        "code": "GUARDIAN",
        "name": "Vulnerability",
        "division": "Security & Compliance",
        "human_interface_executive": "Daniel Brooks",
        "agent_layer": ["vulnerability scans", "risk ranking", "remediation tracking"],
        "kpi_targets": ["critical findings closed", "scan coverage", "risk aging"],
        "description": "Finds, prioritizes, and tracks security weaknesses before they become incidents.",
    },
    {
        "code": "LEDGER",
        "name": "Compliance",
        "division": "Security & Compliance",
        "human_interface_executive": "Daniel Brooks",
        "agent_layer": ["audit trail", "policy mapping", "approval evidence"],
        "kpi_targets": ["audit completeness", "policy coverage", "approval traceability"],
        "description": "Maintains governance evidence, decision trails, approval logs, and compliance records.",
    },
    {
        "code": "ORACLE-BI",
        "name": "Business Intelligence",
        "division": "Intelligence & Data",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["KPI modeling", "dashboard intelligence", "business reporting"],
        "kpi_targets": ["insight freshness", "report accuracy", "decision usefulness"],
        "description": "Turns operational data into executive reporting, KPI insight, and decision intelligence.",
    },
    {
        "code": "MARKET",
        "name": "Market Intelligence",
        "division": "Intelligence & Data",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["market scans", "competitor tracking", "opportunity mapping"],
        "kpi_targets": ["opportunity quality", "trend detection", "market relevance"],
        "description": "Studies markets, competitors, categories, and opportunity spaces for revenue advantage.",
    },
    {
        "code": "QUANT",
        "name": "Financial Forecasting",
        "division": "Intelligence & Data",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["cash forecasting", "scenario modeling", "revenue simulation"],
        "kpi_targets": ["forecast confidence", "scenario coverage", "financial risk visibility"],
        "description": "Models financial outcomes, cash impact, revenue scenarios, and decision tradeoffs.",
    },
    {
        "code": "QUILL",
        "name": "Executive Briefings",
        "division": "Intelligence & Data",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["briefing synthesis", "meeting packs", "strategic narrative"],
        "kpi_targets": ["briefing quality", "prep time saved", "context completeness"],
        "description": "Packages complex operational context into clear Captain, client, and council briefings.",
    },
    {
        "code": "PORTAL",
        "name": "Client Portals",
        "division": "Digital Products",
        "human_interface_executive": "David Carter",
        "agent_layer": ["client workspace", "project visibility", "secure delivery"],
        "kpi_targets": ["client adoption", "ticket reduction", "delivery transparency"],
        "description": "Builds secure client-facing portals for projects, deliverables, files, and communication.",
    },
    {
        "code": "CANVAS",
        "name": "Dashboards",
        "division": "Digital Products",
        "human_interface_executive": "Michael Hayes",
        "agent_layer": ["dashboard UI", "live metrics", "decision screens"],
        "kpi_targets": ["load speed", "metric accuracy", "executive usability"],
        "description": "Creates operational dashboards that make system, client, and revenue state readable.",
    },
    {
        "code": "VISION",
        "name": "Data Visualization",
        "division": "Digital Products",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["visual analytics", "charts", "storytelling"],
        "kpi_targets": ["clarity", "signal density", "insight discovery"],
        "description": "Transforms raw data into visual stories, charts, maps, and decision-ready interfaces.",
    },
    {
        "code": "COUNCIL",
        "name": "AIONX Strategic Intelligence",
        "division": "Strategic Intelligence",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["council synthesis", "strategic arbitration", "governance memory"],
        "kpi_targets": ["decision quality", "council consensus", "governed autonomy"],
        "description": "Coordinates AIONX strategic reasoning, executive decision support, and governance intelligence.",
    },
]


def get_capability_modules() -> dict:
    grouped: dict[str, list[dict]] = {}
    hia_index: dict[str, int] = {}
    for index, module in enumerate(CAPABILITY_MODULES, start=1):
        item = {"sort_order": index, **module}
        grouped.setdefault(module["division"], []).append(item)
        hia = module["human_interface_executive"]
        hia_index[hia] = hia_index.get(hia, 0) + 1

    return {
        "total": len(CAPABILITY_MODULES),
        "division_count": len(grouped),
        "hia_count": len(hia_index),
        "modules": [{"sort_order": index, **module} for index, module in enumerate(CAPABILITY_MODULES, start=1)],
        "groups": [
            {"division": division, "count": len(modules), "modules": modules}
            for division, modules in grouped.items()
        ],
        "governance_model": {
            "internal_owner": "Department Intelligence Officer",
            "client_voice": "Human Interface Executive",
            "execution_layer": "AI agents",
            "cadence": "Weekly Council cycle",
            "visibility": "Real-time health dashboard",
        },
    }


async def seed_catalog(db: AsyncSession) -> int:
    """Seed the catalog if empty. Returns count of records inserted."""
    result = await db.execute(select(ServiceDivision).limit(1))
    if result.scalar_one_or_none():
        return 0

    for item in SEED_DIVISIONS:
        db.add(ServiceDivision(tenant_id=SYSTEM_TENANT_ID, **item))
    await db.commit()
    return len(SEED_DIVISIONS)


async def get_all_divisions(
    db: AsyncSession,
    group: Optional[str] = None,
    featured_only: bool = False,
    active_only: bool = True,
) -> List[ServiceDivision]:
    q = select(ServiceDivision)
    if active_only:
        q = q.where(ServiceDivision.is_active == True)
    if group:
        q = q.where(ServiceDivision.division_group == group)
    if featured_only:
        q = q.where(ServiceDivision.is_featured == True)
    q = q.order_by(ServiceDivision.sort_order)
    result = await db.execute(q)
    return result.scalars().all()


async def get_division_by_code(db: AsyncSession, code: str) -> Optional[ServiceDivision]:
    result = await db.execute(
        select(ServiceDivision).where(ServiceDivision.code == code)
    )
    return result.scalar_one_or_none()


async def get_groups(db: AsyncSession) -> List[str]:
    result = await db.execute(
        select(ServiceDivision.division_group).distinct().order_by(ServiceDivision.division_group)
    )
    return [row[0] for row in result.fetchall()]


async def update_division(
    db: AsyncSession,
    code: str,
    **kwargs,
) -> Optional[ServiceDivision]:
    await db.execute(
        update(ServiceDivision).where(ServiceDivision.code == code).values(**kwargs)
    )
    await db.commit()
    return await get_division_by_code(db, code)


async def get_catalog_stats(db: AsyncSession) -> dict:
    divisions = await get_all_divisions(db, active_only=False)
    total = len(divisions)
    active = sum(1 for d in divisions if d.is_active)
    featured = sum(1 for d in divisions if d.is_featured)
    groups: dict = {}
    for d in divisions:
        groups[d.division_group] = groups.get(d.division_group, 0) + 1
    return {
        "total": total,
        "active": active,
        "featured": featured,
        "groups": groups,
    }
