#!/usr/bin/env python3
"""
JARVIS vNEXT Pre-Launch Checklist
Run before first client activation.
Usage: python scripts/pre_launch_check.py
All 17 checks must pass before going live.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urlparse, urlunparse


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("JARVIS_PROPOSAL_DIR", str(ROOT / "data" / "prelaunch_proposals"))

import httpx
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db, set_tenant_context
from app.models import register_models
from app.models.approval import AuditLog
from app.models.base import JarvisBase
from app.models.lead import Lead, LeadStatus
from app.models.tenant import Tenant
from app.services.governance.captain_queue import captain_queue
from app.services.governance.proposal_generator import proposal_generator
from app.services.leads.discovery import lead_discovery_engine
from app.services.outreach.engine import outreach_engine
from app.services.tenancy.tenant_manager import TenantManager


CheckFn = Callable[[], Awaitable[str]]


GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
CHECK = "\u2713"
CROSS = "\u2717"

VALIDATION_SLUG = "pre-launch-validation"
VALIDATION_EMAIL = "prelaunch-validation@aliyarsolutions.local"
_SCHEMA_READY = False
_VALIDATION_TENANT_ID: uuid.UUID | None = None
_VALIDATION_LEAD: Lead | None = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    elapsed_ms: int


class PreLaunchFailure(RuntimeError):
    """A pre-launch check failed in a user-actionable way."""


async def test_db_connection() -> str:
    await _ensure_schema()
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return f"SELECT 1 succeeded; {len(JarvisBase.metadata.tables)} tables registered"


async def test_redis_connection() -> str:
    if not settings.REDIS_URL:
        raise PreLaunchFailure("REDIS_URL is not configured")

    import redis.asyncio as aioredis

    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        if not await client.ping():
            raise PreLaunchFailure("Redis PING returned false")
    finally:
        close = getattr(client, "aclose", client.close)
        result = close()
        if asyncio.iscoroutine(result):
            await result
    return "Redis responded to PING"


async def test_bedrock() -> str:
    model_id = (
        os.getenv("BEDROCK_VALIDATION_MODEL_ID")
        or os.getenv("BEDROCK_MODEL_ID")
        or "anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4,
        "messages": [{"role": "user", "content": "Return READY."}],
    }

    def _invoke() -> dict:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        return json.loads(response["body"].read())

    data = await asyncio.to_thread(_invoke)
    text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
    if not text.strip():
        raise PreLaunchFailure(f"Bedrock model {model_id} returned no text")
    return f"Bedrock invoked {model_id}"


async def test_anthropic() -> str:
    if not settings.ANTHROPIC_API_KEY:
        raise PreLaunchFailure("ANTHROPIC_API_KEY is not configured")

    import anthropic

    model_id = os.getenv("ANTHROPIC_VALIDATION_MODEL", "claude-3-5-haiku-20241022")
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model=model_id,
        max_tokens=4,
        messages=[{"role": "user", "content": "Return READY."}],
    )
    content = response.content[0].text if response.content else ""
    if not content.strip():
        raise PreLaunchFailure(f"Anthropic model {model_id} returned no text")
    return f"Anthropic accepted key via {model_id}"


async def test_apollo() -> str:
    if not settings.APOLLO_API_KEY:
        raise PreLaunchFailure("APOLLO_API_KEY is not configured")

    payload = {
        "q_keywords": "SaaS operations",
        "person_titles": ["Founder", "CEO"],
        "organization_num_employees_ranges": ["1,10", "11,50", "51,100"],
        "page": 1,
        "per_page": 1,
        "api_key": settings.APOLLO_API_KEY,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.apollo.io/v1/people/search",
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            json=payload,
        )
    if response.status_code >= 400:
        raise PreLaunchFailure(f"Apollo returned HTTP {response.status_code}: {_compact_response(response)}")
    data = response.json()
    return f"Apollo key accepted; {len(data.get('people', []))} sample people returned"


async def test_gmail() -> str:
    if not settings.GMAIL_ADDRESS or not settings.GMAIL_APP_PASSWORD:
        raise PreLaunchFailure("GMAIL_ADDRESS and GMAIL_APP_PASSWORD are required")

    import aiosmtplib

    smtp = aiosmtplib.SMTP(hostname="smtp.gmail.com", port=587, start_tls=True, timeout=20)
    await smtp.connect()
    try:
        await smtp.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
    finally:
        await smtp.quit()
    return f"Gmail SMTP login succeeded for {settings.GMAIL_ADDRESS}"


async def test_slack() -> str:
    if not settings.SLACK_WEBHOOK_URL:
        raise PreLaunchFailure("SLACK_WEBHOOK_URL is not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            settings.SLACK_WEBHOOK_URL,
            json={"text": "JARVIS pre-launch validation ping. No client action triggered."},
        )
    if response.status_code != 200:
        raise PreLaunchFailure(f"Slack returned HTTP {response.status_code}: {_compact_response(response)}")
    return "Slack webhook accepted validation ping"


async def test_telegram() -> str:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        raise PreLaunchFailure("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")

    base_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        bot_response = await client.get(f"{base_url}/getMe")
        if bot_response.status_code != 200 or not bot_response.json().get("ok"):
            raise PreLaunchFailure(f"Telegram getMe failed: {_compact_response(bot_response)}")
        bot_name = bot_response.json().get("result", {}).get("username") or "bot"

        ping_response = await client.post(
            f"{base_url}/sendMessage",
            json={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": "JARVIS pre-launch validation ping. No client action triggered.",
            },
        )
    if ping_response.status_code != 200 or not ping_response.json().get("ok"):
        raise PreLaunchFailure(f"Telegram sendMessage failed: {_compact_response(ping_response)}")
    return f"Telegram bot @{bot_name} reached Captain chat"


async def test_discovery() -> str:
    records: list[dict] = []
    if settings.APOLLO_API_KEY:
        records = await lead_discovery_engine.search_apollo(
            "SaaS operations",
            {"countries": ["United Kingdom"], "industries": ["software"], "limit": 3},
        )
    if not records and settings.GOOGLE_MAPS_API_KEY:
        records = await lead_discovery_engine.discover_from_google_maps("restaurants", "London, UK")

    if not records:
        raise PreLaunchFailure("Lead discovery returned zero records; configure Apollo or Google Maps")
    return f"Discovery returned {len(records)} live lead candidates"


async def test_email_gen() -> str:
    tenant_id = await _validation_tenant_id()
    lead = await _validation_lead()
    sequence = await outreach_engine.generate_sequence(lead, tenant_id)
    if len(sequence) < 3:
        raise PreLaunchFailure(f"Expected 3 email steps, got {len(sequence)}")
    blocked_terms = [" price ", " pricing ", " claude ", " bot ", " gpt "]
    joined = " ".join(f"{item.subject} {item.body_text}".lower() for item in sequence)
    if any(term in f" {joined} " for term in blocked_terms):
        raise PreLaunchFailure("Generated outreach contains blocked client-facing language")
    return f"Generated {len(sequence)} safe outreach emails for validation lead"


async def test_proposal_gen() -> str:
    tenant_id = await _validation_tenant_id()
    lead = await _validation_lead()
    result = await proposal_generator.generate(lead, "STARTER", tenant_id)
    if result.startswith("s3://"):
        return f"Proposal generated and uploaded: {result}"

    pdf_path = Path(result)
    if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
        raise PreLaunchFailure(f"Proposal PDF was not created at {pdf_path}")
    return f"Proposal PDF created at {pdf_path}"


async def test_approval_queue() -> str:
    tenant_id = await _validation_tenant_id()
    approval = await captain_queue.add_item(
        action_type="pre_launch_validation",
        title="Pre-launch validation approval path",
        summary="This validates the Captain approval queue before the first-client mission.",
        payload={"raised_by": "pre_launch_check", "validation": True, "created_at": datetime.now(UTC).isoformat()},
        risk_level="LOW",
        tenant_id=tenant_id,
    )
    pending = await captain_queue.pending_count(tenant_id)
    return f"Approval item {approval.id} created; {pending} pending for validation tenant"


async def test_websocket() -> str:
    url = os.getenv("JARVIS_WEBSOCKET_URL") or _websocket_url("/api/v1/ws/captain")
    import websockets

    async with websockets.connect(url, open_timeout=10, close_timeout=5) as websocket:
        first = await asyncio.wait_for(websocket.recv(), timeout=10)
        first_data = json.loads(first)
        if first_data.get("type") != "captain_connected":
            raise PreLaunchFailure(f"Unexpected WebSocket greeting: {first_data.get('type')}")
        await websocket.send(json.dumps({"type": "ping"}))
        pong = await asyncio.wait_for(websocket.recv(), timeout=10)
        pong_data = json.loads(pong)
        if pong_data.get("type") != "pong":
            raise PreLaunchFailure(f"Unexpected WebSocket ping response: {pong_data.get('type')}")
    return f"WebSocket captain channel responded at {url}"


async def test_grafana() -> str:
    url = os.getenv("GRAFANA_URL") or _service_url(3000)
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
        response = await client.get(url)
    if response.status_code not in {200, 302, 401}:
        raise PreLaunchFailure(f"Grafana returned HTTP {response.status_code}")
    return f"Grafana reachable at {url} with HTTP {response.status_code}"


async def test_prometheus() -> str:
    base = os.getenv("PROMETHEUS_URL") or _service_url(9090)
    url = base.rstrip("/") + "/-/ready"
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(url)
    if response.status_code != 200:
        raise PreLaunchFailure(f"Prometheus returned HTTP {response.status_code}")
    return f"Prometheus ready endpoint returned HTTP 200 at {url}"


async def test_s3() -> str:
    if not settings.AWS_S3_BUCKET:
        raise PreLaunchFailure("AWS_S3_BUCKET is not configured")

    key = f"prelaunch/pre_launch_check_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.txt"
    body = b"JARVIS pre-launch validation object. No client data."

    def _round_trip() -> None:
        import boto3

        client = boto3.client("s3", region_name=settings.AWS_REGION)
        client.put_object(Bucket=settings.AWS_S3_BUCKET, Key=key, Body=body, ContentType="text/plain")
        client.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)

    await asyncio.to_thread(_round_trip)
    return f"S3 put/delete succeeded in bucket {settings.AWS_S3_BUCKET}"


async def test_domain() -> str:
    parsed = urlparse(settings.APP_BASE_URL)
    host = parsed.hostname
    if not host:
        raise PreLaunchFailure("APP_BASE_URL has no hostname")
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise PreLaunchFailure("APP_BASE_URL points to localhost; set the production domain before launch")

    infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    ips = sorted({info[4][0] for info in infos})
    health_url = settings.APP_BASE_URL.rstrip("/") + "/health"
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(health_url)
    if response.status_code != 200:
        raise PreLaunchFailure(f"{health_url} returned HTTP {response.status_code}")
    return f"{host} resolves to {', '.join(ips[:3])}; /health returned HTTP 200"


CHECKS: list[tuple[str, CheckFn]] = [
    ("Database connection", test_db_connection),
    ("Redis connection", test_redis_connection),
    ("AWS Bedrock reachable", test_bedrock),
    ("Anthropic API key valid", test_anthropic),
    ("Apollo API key valid", test_apollo),
    ("Gmail SMTP working", test_gmail),
    ("Slack webhook working", test_slack),
    ("Telegram bot working", test_telegram),
    ("Lead discovery returning results", test_discovery),
    ("Email generation working", test_email_gen),
    ("Proposal PDF generation working", test_proposal_gen),
    ("Captain approval queue working", test_approval_queue),
    ("WebSocket endpoint working", test_websocket),
    ("Grafana accessible", test_grafana),
    ("Prometheus scraping", test_prometheus),
    ("S3 upload working", test_s3),
    ("Domain resolving correctly", test_domain),
]


async def run_check(name: str, fn: CheckFn) -> CheckResult:
    started = time.monotonic()
    try:
        detail = await fn()
        return CheckResult(name=name, passed=True, detail=detail, elapsed_ms=_elapsed_ms(started))
    except Exception as exc:
        return CheckResult(name=name, passed=False, detail=_redact(str(exc)), elapsed_ms=_elapsed_ms(started))


async def main() -> int:
    print("JARVIS PRE-LAUNCH VALIDATION")
    print("Aliyar Solutions first-client readiness")
    print("")

    results = [await run_check(name, fn) for name, fn in CHECKS]
    for result in results:
        if result.passed:
            print(f"{GREEN}{CHECK}{RESET} {result.name} - {result.detail} ({result.elapsed_ms} ms)")
        else:
            print(f"{RED}{CROSS}{RESET} {result.name} - {result.detail} ({result.elapsed_ms} ms)")

    ready = sum(1 for result in results if result.passed)
    print("")
    print(f"{ready}/{len(CHECKS)} systems ready")
    if ready == len(CHECKS):
        print("JARVIS IS READY. CAPTAIN, BEGIN THE MISSION.")
        return 0
    return 1


async def _ensure_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    register_models()
    await init_db()
    _SCHEMA_READY = True


async def _validation_tenant_id() -> uuid.UUID:
    global _VALIDATION_TENANT_ID
    if _VALIDATION_TENANT_ID:
        return _VALIDATION_TENANT_ID

    await _ensure_schema()
    if settings.JARVIS_DEFAULT_TENANT_ID:
        tenant_id = uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
        async with AsyncSessionLocal() as session:
            existing = await session.scalar(select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active.is_(True)))
        if existing:
            _VALIDATION_TENANT_ID = tenant_id
            return tenant_id

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Tenant).where(Tenant.slug == VALIDATION_SLUG))
        if existing:
            _VALIDATION_TENANT_ID = existing.id
            return existing.id

    tenant, _ = await TenantManager().create_tenant(
        name="Pre-Launch Validation",
        plan_tier="GROWTH",
        admin_email=VALIDATION_EMAIL,
        admin_password=f"Jarvis-Validation-{uuid.uuid4().hex[:12]}!",
    )
    _VALIDATION_TENANT_ID = tenant.id
    return tenant.id


async def _validation_lead() -> Lead:
    global _VALIDATION_LEAD
    if _VALIDATION_LEAD:
        return _VALIDATION_LEAD

    tenant_id = await _validation_tenant_id()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _apply_tenant_context(session, tenant_id)
            existing = await session.scalar(
                select(Lead)
                .where(
                    Lead.tenant_id == tenant_id,
                    Lead.source == "pre_launch_check",
                    Lead.company_name == "Pre-Launch Validation Prospect",
                )
                .limit(1)
            )
            if existing:
                _VALIDATION_LEAD = existing
                return existing

            lead = Lead(
                tenant_id=tenant_id,
                company_name="Pre-Launch Validation Prospect",
                company="Pre-Launch Validation Prospect",
                contact_name="Operations Director",
                email=VALIDATION_EMAIL,
                contact_email=VALIDATION_EMAIL,
                country="United Kingdom",
                industry="SaaS",
                score=72,
                status=LeadStatus.NEW,
                source="pre_launch_check",
                website="https://example.com",
                company_website="https://example.com",
                pain_points=[
                    "manual customer follow-up",
                    "slow operational reporting",
                    "limited workflow visibility",
                ],
                opportunity_type="Revenue workflow automation and operating dashboard",
                enrichment_data={"validation": True, "created_by": "pre_launch_check"},
            )
            session.add(lead)
            await session.flush()
            session.add(
                AuditLog(
                    tenant_id=tenant_id,
                    action="pre_launch_validation_lead_created",
                    entity_type="lead",
                    entity_id=lead.id,
                    actor="pre_launch_check",
                    after_json={"company_name": lead.company_name, "source": lead.source},
                    details={"validation": True},
                )
            )
            await session.refresh(lead)
            _VALIDATION_LEAD = lead
            return lead


async def _apply_tenant_context(session, tenant_id: uuid.UUID) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    await set_tenant_context(session, str(tenant_id))


def _websocket_url(path: str) -> str:
    parsed = urlparse(settings.APP_BASE_URL)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, path, "", "", ""))


def _service_url(port: int) -> str:
    parsed = urlparse(settings.APP_BASE_URL)
    if not parsed.hostname:
        return f"http://localhost:{port}"
    host = parsed.hostname
    scheme = parsed.scheme or "http"
    netloc = f"{host}:{port}"
    return urlunparse((scheme, netloc, "", "", "", ""))


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _compact_response(response: httpx.Response) -> str:
    text = response.text.strip().replace("\n", " ")
    if len(text) > 300:
        text = text[:300] + "..."
    return _redact(text)


def _redact(text: str) -> str:
    redacted = text
    secrets = [
        settings.ANTHROPIC_API_KEY,
        settings.OPENAI_API_KEY,
        settings.GOOGLE_API_KEY,
        settings.DEEPSEEK_API_KEY,
        settings.GROQ_API_KEY,
        settings.MISTRAL_API_KEY,
        settings.MOONSHOT_API_KEY,
        settings.ZHIPUAI_API_KEY,
        settings.DASHSCOPE_API_KEY,
        settings.MINIMAX_API_KEY,
        settings.NVIDIA_API_KEY,
        settings.ELEVENLABS_API_KEY,
        settings.APOLLO_API_KEY,
        settings.GMAIL_APP_PASSWORD,
        settings.SLACK_WEBHOOK_URL,
        settings.TELEGRAM_BOT_TOKEN,
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY,
        settings.STRIPE_SECRET_KEY,
        settings.TWILIO_AUTH_TOKEN,
    ]
    for secret in secrets:
        if secret and len(secret) >= 4:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
