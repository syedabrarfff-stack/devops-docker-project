from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.services.storage.secure import get_credential


def mask_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


@dataclass(frozen=True)
class CredentialSpec:
    key: str
    label: str
    category: str
    description: str
    required_for: tuple[str, ...]
    secret: bool = True


CREDENTIAL_SPECS: tuple[CredentialSpec, ...] = (
    CredentialSpec("GOOGLE_MAPS_API_KEY", "Google Maps / Places", "Discovery", "Local market discovery for clinics, hotels, restaurants, agencies, and other buyers.", ("Local Market Hunter", "Sales War Room")),
    CredentialSpec("APOLLO_API_KEY", "Apollo.io", "Discovery", "Lead enrichment, contacts, buyer roles, and ICP discovery.", ("Local Market Hunter", "Apollo enrichment")),
    CredentialSpec("GMAIL_CLIENT_ID", "Gmail OAuth Client ID", "Communication", "OAuth connection for reading/sending approved Gmail outreach.", ("Gmail OAuth", "Approved outreach send"), False),
    CredentialSpec("GMAIL_CLIENT_SECRET", "Gmail OAuth Client Secret", "Communication", "OAuth secret for Gmail API access.", ("Gmail OAuth", "Approved outreach send")),
    CredentialSpec("GMAIL_ADDRESS", "Gmail Address", "Communication", "Sender address for Aliyar Solutions outreach.", ("Gmail OAuth", "Approved outreach send"), False),
    CredentialSpec("TELEGRAM_BOT_TOKEN", "Telegram Bot Token", "Approvals", "Telegram approval cards and urgent alerts.", ("Captain approvals", "Mobile command")),
    CredentialSpec("TELEGRAM_CHAT_ID", "Telegram Chat ID", "Approvals", "Captain destination chat for approval notifications.", ("Captain approvals", "Mobile command"), False),
    CredentialSpec("N8N_BASE_URL", "n8n Base URL", "Automation", "Self-hosted n8n workspace URL.", ("n8n Tool Army", "Automation Center"), False),
    CredentialSpec("N8N_API_KEY", "n8n API Key", "Automation", "Jarvis imports, triggers, and monitors workflows.", ("n8n Tool Army", "Workflow control")),
    CredentialSpec("N8N_WEBHOOK_BASE_URL", "n8n Webhook Base URL", "Automation", "Webhook base for Jarvis-controlled workflow triggers.", ("n8n Tool Army", "Workflow execution"), False),
    CredentialSpec("OPENAI_API_KEY", "OpenAI API Key", "AI", "General intelligence, file search, future realtime voice, and analysis.", ("Command Brain", "Realtime Voice")),
    CredentialSpec("ANTHROPIC_API_KEY", "Anthropic API Key", "AI", "Strategy and reasoning provider.", ("Command Brain", "Digital Twin")),
    CredentialSpec("AWS_ACCESS_KEY_ID", "AWS Access Key ID", "AWS", "AWS access key for optional Bedrock, SSM, S3, and ECS operations.", ("AWS Bedrock", "Cloud operations"), False),
    CredentialSpec("AWS_SECRET_ACCESS_KEY", "AWS Secret Access Key", "AWS", "AWS secret key for optional Bedrock, SSM, S3, and ECS operations.", ("AWS Bedrock", "Cloud operations")),
    CredentialSpec("AWS_BEDROCK_ENABLED", "AWS Bedrock Enabled", "AI", "Set true to enable AWS-native Bedrock model routing.", ("AWS Bedrock",), False),
    CredentialSpec("AWS_BEDROCK_MODEL_ID", "AWS Bedrock Model", "AI", "Primary Bedrock model ID for JARVIS cloud intelligence.", ("AWS Bedrock",), False),
)


async def credential_status(db) -> list[dict]:
    rows = []
    for spec in CREDENTIAL_SPECS:
        value = await get_credential(db, spec.key)
        rows.append({
            "key": spec.key,
            "label": spec.label,
            "category": spec.category,
            "configured": bool(value),
            "masked_value": mask_secret(value) if spec.secret else value,
            "description": spec.description,
            "required_for": list(spec.required_for),
            "secret": spec.secret,
        })
    return rows


async def n8n_status(db) -> dict:
    base_url = (await get_credential(db, "N8N_BASE_URL")) or settings.N8N_BASE_URL
    api_key = await get_credential(db, "N8N_API_KEY")
    if not base_url:
        return {"configured": False, "reachable": False, "base_url": None, "message": "N8N_BASE_URL is missing"}

    headers = {"X-N8N-API-KEY": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            response = await client.get(f"{base_url.rstrip('/')}/healthz", headers=headers)
        return {
            "configured": bool(base_url),
            "api_key_configured": bool(api_key),
            "reachable": response.status_code < 500,
            "base_url": base_url,
            "status_code": response.status_code,
            "message": "n8n reachable" if response.status_code < 500 else "n8n returned an error",
        }
    except Exception as exc:
        return {
            "configured": bool(base_url),
            "api_key_configured": bool(api_key),
            "reachable": False,
            "base_url": base_url,
            "message": str(exc),
        }


async def capability_status(db) -> dict:
    creds = await credential_status(db)
    by_key = {row["key"]: row for row in creds}
    n8n = await n8n_status(db)
    gmail_oauth_ready = by_key["GMAIL_CLIENT_ID"]["configured"] and by_key["GMAIL_CLIENT_SECRET"]["configured"]
    gmail_via_n8n_ready = n8n["reachable"] and by_key["GMAIL_ADDRESS"]["configured"]

    capabilities = [
        {
            "id": "command_brain",
            "name": "Jarvis Command Brain",
            "state": "ready",
            "summary": "Live operating dashboard, chat, approvals, CRM, leads, and task context.",
        },
        {
            "id": "aws_bedrock",
            "name": "AWS Bedrock Intelligence",
            "state": "ready" if by_key["AWS_ACCESS_KEY_ID"]["configured"] and by_key["AWS_SECRET_ACCESS_KEY"]["configured"] else "blocked",
            "summary": "Adds AWS-native model routing for cloud operations and resilient AI fallback.",
            "missing": [] if by_key["AWS_ACCESS_KEY_ID"]["configured"] and by_key["AWS_SECRET_ACCESS_KEY"]["configured"] else ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
        },
        {
            "id": "local_market_hunter",
            "name": "Local Market Hunter",
            "state": "ready" if by_key["GOOGLE_MAPS_API_KEY"]["configured"] else "blocked",
            "summary": "Finds clinics, hotels, restaurants, startups, and local buyers through Google Places.",
            "missing": [] if by_key["GOOGLE_MAPS_API_KEY"]["configured"] else ["GOOGLE_MAPS_API_KEY"],
        },
        {
            "id": "apollo_enrichment",
            "name": "Apollo Enrichment",
            "state": "ready" if by_key["APOLLO_API_KEY"]["configured"] else "blocked",
            "summary": "Enriches contacts and buyer roles with Apollo.",
            "missing": [] if by_key["APOLLO_API_KEY"]["configured"] else ["APOLLO_API_KEY"],
        },
        {
            "id": "n8n_tool_army",
            "name": "n8n Tool Army",
            "state": "ready" if n8n["reachable"] and n8n.get("api_key_configured") else "degraded",
            "summary": "Runs workflow tools for discovery, enrichment, drafts, approvals, and reporting.",
            "missing": [] if n8n.get("api_key_configured") else ["N8N_API_KEY"],
        },
        {
            "id": "approval_gate",
            "name": "Captain Approval Gate",
            "state": "ready" if by_key["TELEGRAM_BOT_TOKEN"]["configured"] and by_key["TELEGRAM_CHAT_ID"]["configured"] else "dashboard_only",
            "summary": "Dashboard approvals are available; Telegram cards activate when bot token and chat ID are configured.",
        },
        {
            "id": "gmail_outreach",
            "name": "Gmail Approved Outreach",
            "state": "ready" if gmail_oauth_ready or gmail_via_n8n_ready else "blocked",
            "summary": "Sends approved outreach only after Captain approval. Gmail can run directly through Jarvis OAuth or through the connected n8n Gmail credential.",
            "missing": [] if gmail_oauth_ready or gmail_via_n8n_ready else ["GMAIL_CLIENT_ID/GMAIL_CLIENT_SECRET or connected n8n Gmail workflow"],
            "via": "n8n" if gmail_via_n8n_ready and not gmail_oauth_ready else "jarvis_oauth",
        },
    ]

    return {
        "mode": "auto_safe_work",
        "standing_permission": "Jarvis may research, enrich, score, draft, update CRM, run diagnostics, and prepare workflow actions without asking. External sends, payments, deletes, credential changes, contracts, and high-risk production changes require approval.",
        "credentials": creds,
        "n8n": n8n,
        "capabilities": capabilities,
        "blockers": [cap for cap in capabilities if cap["state"] in ("blocked", "degraded")],
    }


async def build_operating_context(db) -> str:
    status = await capability_status(db)
    ready = [c["name"] for c in status["capabilities"] if c["state"] in ("ready", "dashboard_only")]
    blockers = [
        f"{c['name']}: missing {', '.join(c.get('missing', [])) or c['state']}"
        for c in status["blockers"]
    ]
    return (
        "LIVE JARVIS OPERATING CONTEXT\n"
        f"Autonomy: {status['mode']}.\n"
        f"Standing permission: {status['standing_permission']}\n"
        f"Ready capabilities: {', '.join(ready) or 'none'}.\n"
        f"Current blockers: {'; '.join(blockers) if blockers else 'none'}.\n"
        "Response rule: never ask for broad access. If blocked, name the exact missing credential or approval card. "
        "When safe work is possible, state the next concrete action Jarvis can take."
    )
