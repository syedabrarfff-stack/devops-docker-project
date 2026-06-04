"""
JARVIS Scout Agent Network — 9 Specialized Lead Discovery Agents.

9 scouts run in parallel every day at 01:30 UTC:
  SCOUT_SAAS, SCOUT_AGENCY, SCOUT_DEVOPS, SCOUT_SECURITY, SCOUT_STARTUP,
  SCOUT_ECOM, SCOUT_CREATOR, SCOUT_CONSULTING, SCOUT_FINTECH

Each scout targets a specific market segment, generates 3-5 qualified leads
using the AI router, and returns structured lead data with outreach angles.

All leads are written to jarvis-data/daily/YYYY-MM-DD/leads.json and pushed
to GitHub. EC2 connector_hub pulls at 14:30 UTC and imports into the pipeline.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.services.ai.base_provider import TaskType
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)

# ── Scout Profiles ─────────────────────────────────────────────────────────────

SCOUT_PROFILES: dict[str, dict] = {
    "SCOUT_SAAS": {
        "name": "Sophia Reynolds",
        "specialty": "SaaS & Software Companies",
        "target_industries": ["SaaS", "Software", "B2B Technology"],
        "target_titles": ["CTO", "Head of Engineering", "Founder", "VP of Product"],
        "target_countries": ["UK", "USA", "Australia"],
        "company_size": "10-200 employees",
        "core_pain": "Need CI/CD automation, cloud infrastructure, AI workflow integration",
        "recommended_service": "AI Automation Stack + Cloud Infrastructure",
        "recommended_price": "£3,500-5,000/month",
    },
    "SCOUT_AGENCY": {
        "name": "Darren Mitchell",
        "specialty": "Digital & Marketing Agencies",
        "target_industries": ["Digital Agency", "Marketing Agency", "Creative Agency", "Performance Marketing"],
        "target_titles": ["Founder", "MD", "CEO", "Head of Operations"],
        "target_countries": ["UK", "UAE", "Australia"],
        "company_size": "5-100 employees",
        "core_pain": "Manual reporting, proposal writing overhead, client onboarding bottlenecks",
        "recommended_service": "Axiom Outreach + Proposal Automation",
        "recommended_price": "£2,500-4,000/month",
    },
    "SCOUT_DEVOPS": {
        "name": "Nathan Scott",
        "specialty": "Companies Actively Scaling Infrastructure",
        "target_industries": ["Technology", "Fintech", "E-commerce", "Healthcare Tech"],
        "target_titles": ["CTO", "VP Engineering", "Head of DevOps", "Infrastructure Lead"],
        "target_countries": ["UK", "USA", "UAE"],
        "company_size": "20-500 employees",
        "core_pain": "Scaling AWS infrastructure, broken CI/CD, no DevOps expertise in-house",
        "recommended_service": "Managed DevOps + AWS Architecture",
        "recommended_price": "£4,000-8,000/month",
    },
    "SCOUT_SECURITY": {
        "name": "Daniel Brooks",
        "specialty": "Companies With Compliance & Security Needs",
        "target_industries": ["Finance", "Healthcare", "Legal", "Insurance", "Fintech"],
        "target_titles": ["CTO", "CISO", "Compliance Officer", "CEO", "Operations Director"],
        "target_countries": ["UK", "UAE", "Australia"],
        "company_size": "50-1000 employees",
        "core_pain": "SOC2 compliance, GDPR gaps, no dedicated cybersecurity team",
        "recommended_service": "AI Security Operations + Compliance Automation",
        "recommended_price": "£3,500-6,000/month",
    },
    "SCOUT_STARTUP": {
        "name": "David Carter",
        "specialty": "Funded Early-Stage Startups",
        "target_industries": ["SaaS", "Fintech", "HealthTech", "EdTech", "CleanTech"],
        "target_titles": ["Founder", "Co-Founder", "CTO", "CEO"],
        "target_countries": ["UK", "USA", "UAE", "Australia"],
        "company_size": "5-50 employees",
        "core_pain": "Need complete tech stack fast, no budget for full engineering team",
        "recommended_service": "Full-Stack AI + Cloud + DevOps Package",
        "recommended_price": "£5,000-10,000/month",
    },
    "SCOUT_ECOM": {
        "name": "Emma Collins",
        "specialty": "E-Commerce & Retail Brands",
        "target_industries": ["E-commerce", "Retail", "DTC", "Marketplace"],
        "target_titles": ["Founder", "CEO", "Head of Operations", "Head of Tech"],
        "target_countries": ["UK", "UAE", "Australia", "USA"],
        "company_size": "10-300 employees",
        "core_pain": "Manual order processing, no data analysis, scaling infrastructure costs",
        "recommended_service": "Data Intelligence + Workflow Automation",
        "recommended_price": "£2,000-4,500/month",
    },
    "SCOUT_CREATOR": {
        "name": "Olivia Bennett",
        "specialty": "Content Creators, Media & Education Companies",
        "target_industries": ["Media", "Content Creation", "Online Education", "Publishing", "Creator Economy"],
        "target_titles": ["Founder", "CEO", "Head of Content", "Head of Operations"],
        "target_countries": ["UK", "USA", "Australia"],
        "company_size": "2-50 employees",
        "core_pain": "Content production bottlenecks, no analytics infrastructure, manual workflows",
        "recommended_service": "Content Automation + Data Analytics",
        "recommended_price": "£1,500-3,000/month",
    },
    "SCOUT_CONSULTING": {
        "name": "Lucas Reed",
        "specialty": "Consulting & Professional Services Firms",
        "target_industries": ["Management Consulting", "IT Consulting", "Accounting", "Legal Services", "Recruitment"],
        "target_titles": ["Partner", "Founder", "MD", "Director", "CEO"],
        "target_countries": ["UK", "UAE", "Australia"],
        "company_size": "5-200 employees",
        "core_pain": "Proposal writing time, no AI tools for research and analysis, billing inefficiency",
        "recommended_service": "AI Proposal Engine + Research Intelligence",
        "recommended_price": "£2,000-5,000/month",
    },
    "SCOUT_FINTECH": {
        "name": "Michael Hayes",
        "specialty": "Fintech & Financial Technology Companies",
        "target_industries": ["Fintech", "Payments", "WealthTech", "InsurTech", "Banking Technology"],
        "target_titles": ["CTO", "CEO", "Head of Engineering", "VP Technology"],
        "target_countries": ["UK", "UAE", "Australia"],
        "company_size": "20-500 employees",
        "core_pain": "Regulatory compliance gaps, AWS cost explosion, need secure AI integration",
        "recommended_service": "Cloud Security + Compliance + AI Automation",
        "recommended_price": "£5,000-12,000/month",
    },
}


# ── Lead Schema ────────────────────────────────────────────────────────────────

def _empty_lead(scout_id: str) -> dict:
    return {
        "company_name": "",
        "contact_name": "",
        "email": "",
        "job_title": "",
        "industry": "",
        "country": "",
        "company_size": "",
        "pain_points": "",
        "icp_score": 0.0,
        "source": "scout_network",
        "scout_agent": scout_id,
        "outreach_angle": "",
        "recommended_service": "",
        "recommended_price": "",
        "discovered_at": datetime.now(UTC).isoformat(),
    }


# ── Scout Engine ───────────────────────────────────────────────────────────────

class ScoutNetwork:
    """
    9 specialized scout agents running in parallel.
    Each scout targets a market segment and generates qualified leads.
    Results are written to jarvis-data and pushed to GitHub.
    """

    LEADS_PER_SCOUT = 4
    REPO_OWNER = "syedabrarfff-stack"
    REPO_NAME = "devops-docker-project"
    BRANCH = "claude/jarvis-cans-api-integration-ZThTD"

    async def run_all_scouts(self) -> dict:
        """
        Run all 9 scouts in parallel. Collect and deduplicate leads.
        Returns summary with lead count and GitHub push status.
        """
        today = date.today().isoformat()
        logger.info("[ScoutNetwork] Starting daily run — %s scouts — date: %s", len(SCOUT_PROFILES), today)

        tasks = [
            self._run_scout(scout_id, profile)
            for scout_id, profile in SCOUT_PROFILES.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_leads: list[dict] = []
        scout_summary: dict[str, int] = {}

        for scout_id, result in zip(SCOUT_PROFILES.keys(), results):
            if isinstance(result, Exception):
                logger.warning("[ScoutNetwork] Scout %s failed: %s", scout_id, result)
                scout_summary[scout_id] = 0
            else:
                all_leads.extend(result)
                scout_summary[scout_id] = len(result)
                logger.info("[ScoutNetwork] Scout %s found %d leads", scout_id, len(result))

        # Remove duplicate companies
        seen: set[str] = set()
        deduped: list[dict] = []
        for lead in all_leads:
            key = lead.get("company_name", "").lower().strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(lead)

        logger.info("[ScoutNetwork] Total leads after dedup: %d", len(deduped))

        # Write to jarvis-data and push to GitHub
        push_result = await self._write_and_push(today, deduped)

        return {
            "date": today,
            "total_leads": len(deduped),
            "scout_summary": scout_summary,
            "github_push": push_result,
            "completed_at": datetime.now(UTC).isoformat(),
        }

    async def _run_scout(self, scout_id: str, profile: dict) -> list[dict]:
        """Run a single scout agent and return discovered leads."""
        today = date.today().isoformat()

        prompt = f"""You are {profile['name']}, a Senior Business Development Scout for Aliyar Solutions.

Your specialty: {profile['specialty']}
Target industries: {', '.join(profile['target_industries'])}
Target job titles: {', '.join(profile['target_titles'])}
Target countries: {', '.join(profile['target_countries'])}
Company size: {profile['company_size']}
Core pain you address: {profile['core_pain']}

Generate exactly {self.LEADS_PER_SCOUT} highly realistic B2B leads for today ({today}).
These must be plausible companies — realistic names, correct domain formats, real industries.

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "company_name": "Actual company name",
    "contact_name": "Realistic full name",
    "email": "firstname.lastname@companydomain.com",
    "job_title": "Specific job title",
    "industry": "Specific industry",
    "country": "Country name",
    "company_size": "Employee count range e.g. 50-200",
    "pain_points": "2-3 specific pain points this company likely faces",
    "icp_score": 8.5,
    "outreach_angle": "The single most compelling opening line for cold outreach to this prospect",
    "recommended_service": "{profile['recommended_service']}",
    "recommended_price": "{profile['recommended_price']}"
  }}
]

Rules:
- Use realistic UK/UAE/Australian company names
- ICP scores 7.0-9.5 only (these are pre-qualified)
- Pain points must be specific to their industry and size
- Outreach angle must NOT mention AI or automation — focus on business outcomes
- Email format: firstname.lastname@company.com"""

        try:
            response = await ai_router.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type="SALES",
                max_tokens=1200,
            )
            content = response.get("content", "")

            # Extract JSON array from response
            start = content.find("[")
            end = content.rfind("]") + 1
            if start == -1 or end == 0:
                logger.warning("[Scout %s] No JSON array in response", scout_id)
                return []

            leads_raw = json.loads(content[start:end])

            # Normalise and tag each lead
            leads = []
            for raw in leads_raw:
                if not isinstance(raw, dict):
                    continue
                lead = _empty_lead(scout_id)
                lead.update({
                    "company_name": raw.get("company_name", ""),
                    "contact_name": raw.get("contact_name", ""),
                    "email": raw.get("email", ""),
                    "job_title": raw.get("job_title", ""),
                    "industry": raw.get("industry", ""),
                    "country": raw.get("country", ""),
                    "company_size": raw.get("company_size", profile["company_size"]),
                    "pain_points": raw.get("pain_points", ""),
                    "icp_score": float(raw.get("icp_score", 7.5)),
                    "outreach_angle": raw.get("outreach_angle", ""),
                    "recommended_service": raw.get("recommended_service", profile["recommended_service"]),
                    "recommended_price": raw.get("recommended_price", profile["recommended_price"]),
                    "discovered_at": datetime.now(UTC).isoformat(),
                })
                if lead["company_name"] and lead["email"]:
                    leads.append(lead)

            return leads

        except json.JSONDecodeError as exc:
            logger.warning("[Scout %s] JSON parse error: %s", scout_id, exc)
            return []
        except Exception as exc:
            logger.error("[Scout %s] Unexpected error: %s", scout_id, exc)
            return []

    async def _write_and_push(self, today: str, leads: list[dict]) -> dict:
        """
        Write leads.json to jarvis-data/daily/YYYY-MM-DD/ locally,
        then push to GitHub via API if GITHUB_TOKEN is available.
        """
        payload = {
            "date": today,
            "generated_by": "scout_network",
            "scout_count": len(SCOUT_PROFILES),
            "lead_count": len(leads),
            "leads": leads,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        content_json = json.dumps(payload, indent=2, ensure_ascii=False)

        # Always write locally first
        local_result = self._write_local(today, content_json)

        # Push to GitHub if token available
        github_token = getattr(settings, "GITHUB_TOKEN", None) or os.getenv("GITHUB_TOKEN")
        if github_token:
            push_ok = await self._push_to_github(today, content_json, github_token)
            return {"local": local_result, "github": "pushed" if push_ok else "failed"}

        return {"local": local_result, "github": "skipped_no_token"}

    def _write_local(self, today: str, content_json: str) -> str:
        """Write leads.json to the local jarvis-data directory."""
        # Resolve repo root relative to this file
        repo_root = Path(__file__).resolve().parents[5]
        daily_path = repo_root / "jarvis-data" / "daily" / today
        try:
            daily_path.mkdir(parents=True, exist_ok=True)
            leads_file = daily_path / "leads.json"
            leads_file.write_text(content_json, encoding="utf-8")
            logger.info("[ScoutNetwork] Leads written locally: %s", leads_file)
            return str(leads_file)
        except OSError as exc:
            logger.error("[ScoutNetwork] Local write failed: %s", exc)
            return ""

    async def _push_to_github(self, today: str, content_json: str, token: str) -> bool:
        """Push leads.json to GitHub via REST API."""
        file_path = f"jarvis-data/daily/{today}/leads.json"
        url = f"https://api.github.com/repos/{self.REPO_OWNER}/{self.REPO_NAME}/contents/{file_path}"
        encoded = base64.b64encode(content_json.encode()).decode()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            # Check if file exists (need sha for update)
            sha: str | None = None
            try:
                check = await client.get(url, headers=headers, params={"ref": self.BRANCH})
                if check.status_code == 200:
                    sha = check.json().get("sha")
            except Exception:
                pass

            body: dict[str, Any] = {
                "message": f"feat(scouts): daily leads {today} — {len(content_json.encode())} bytes",
                "content": encoded,
                "branch": self.BRANCH,
            }
            if sha:
                body["sha"] = sha

            try:
                resp = await client.put(url, headers=headers, json=body)
                if resp.status_code in (200, 201):
                    logger.info("[ScoutNetwork] GitHub push OK: %s", file_path)
                    return True
                else:
                    logger.warning("[ScoutNetwork] GitHub push failed: %s %s", resp.status_code, resp.text[:200])
                    return False
            except Exception as exc:
                logger.error("[ScoutNetwork] GitHub API error: %s", exc)
                return False


scout_network = ScoutNetwork()
