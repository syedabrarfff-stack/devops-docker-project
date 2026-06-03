from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.intelligence import CompetitorProfile
from app.services.memory.graph import _upsert_node


COMPETITOR_SNAPSHOTS: list[dict[str, Any]] = [
    {
        "name": "Cognitiv+",
        "website_url": "https://www.cognitivplus.com/",
        "region": "UK",
        "category": "AI-native software studio",
        "services": [
            "AI-native product development",
            "AI-assisted architecture, code, testing, and deployment",
            "Human-reviewed software delivery",
            "Outcome-led product studio delivery",
        ],
        "pricing_signals": ["No public pricing found on the reviewed public website"],
        "target_market": [
            "Companies wanting products shipped quickly",
            "Buyers attracted to AI-native software studio positioning",
        ],
        "positioning": (
            "Positions as an AI Factory where intelligent agents and human expertise converge "
            "to deliver products faster than traditional agencies."
        ),
        "weaknesses": [
            "Broad AI-factory positioning, less explicit revenue-operations specialization",
            "No visible service catalog or public fixed-price bands",
            "Less proof of end-to-end sales pipeline, retention, and delivery operating system",
        ],
        "evidence_refs": [
            "https://www.cognitivplus.com/",
        ],
        "aliyar_win_reasons": [
            "Aliyar can sell a wider 30-division operating system, not only AI-native product builds.",
            "Aliyar can lead with revenue workflow, outreach, demo, CRM, delivery, and retention as one spine.",
            "Aliyar can show a live command center, memory graph, audit trail, and daily operating loop.",
        ],
    },
    {
        "name": "The Automation Agency",
        "website_url": "https://www.automation-agency.co.uk/",
        "region": "UK",
        "category": "AI and process automation agency",
        "services": [
            "Workflow process audit",
            "Automation opportunity mapping",
            "Fixed-price automation builds",
            "Handover, support, and monthly retainer",
            "WhatsApp dispatch, predictive analytics, scraping/data dashboards",
        ],
        "pricing_signals": [
            "Free discovery call",
            "Process Audit at £1,500",
            "Automation builds from £3,000",
            "Multi-agent builds from £8,000",
            "Retainer from £1,500/month",
        ],
        "target_market": [
            "UK businesses with manual workflows",
            "Regional businesses around Chesterfield/Derbyshire and broader UK",
            "Buyers who want fixed-price automation and clear process audit deliverables",
        ],
        "positioning": (
            "Strong practical builder positioning: process audit first, fixed-price implementation, "
            "real production examples, and no hidden phases."
        ),
        "weaknesses": [
            "Narrower UK/local positioning",
            "Founder/developer-led message may feel smaller than an international operating company",
            "Less visible breadth across cloud, security, content, revenue operations, finance, and client delivery",
        ],
        "evidence_refs": [
            "https://www.automation-agency.co.uk/",
        ],
        "aliyar_win_reasons": [
            "Aliyar can compete with the same audit-to-build clarity while adding a broader service catalog.",
            "Aliyar can position as international technology operations, not just regional automation delivery.",
            "Aliyar can bundle sales/revenue systems, cloud reliability, dashboards, and memory intelligence into the same engagement.",
        ],
    },
    {
        "name": "SmartSuite AI",
        "website_url": "https://www.smartsuite.com/",
        "pricing_url": "https://www.smartsuite.com/pricing",
        "region": "USA",
        "category": "AI-powered work management and GRC platform",
        "services": [
            "GRC and resilience platform",
            "IT service delivery workflows",
            "Project and portfolio management",
            "Business operations workflows",
            "SmartSuite AI Agent Studio",
            "No-code automation, reporting, templates, integrations, and governance",
        ],
        "pricing_signals": [
            "Team plan: $15/user/month annually or $20 monthly, minimum 3 users",
            "Professional: $32/user/month annually or $36 monthly, minimum 5 users",
            "Enterprise and Signature plans: custom pricing",
        ],
        "target_market": [
            "Teams standardizing workflows",
            "GRC, IT, project, and business operations leaders",
            "Organizations consolidating point tools into one platform",
        ],
        "positioning": (
            "Positions as a connected platform for GRC, IT, projects, and business operations with "
            "AI agents, governance, permissions, dashboards, and templates."
        ),
        "weaknesses": [
            "Platform-first, not done-for-you implementation-first",
            "Buyer still needs workflow design, rollout, adoption, integrations, and operating discipline",
            "Less focused on outbound revenue generation and first-client acquisition",
        ],
        "evidence_refs": [
            "https://www.smartsuite.com/",
            "https://www.smartsuite.com/pricing",
        ],
        "aliyar_win_reasons": [
            "Aliyar can implement and run operating systems for clients instead of selling a self-configured platform.",
            "Aliyar can combine platform choice, custom integrations, dashboards, outreach, demos, and delivery tracking.",
            "Aliyar can target SMBs that need outcomes and execution support before they are ready for enterprise platform ownership.",
        ],
    },
]


async def seed_competitor_profiles(tenant_id: uuid.UUID | str) -> dict[str, Any]:
    tenant_uuid = _coerce_tenant_id(tenant_id)
    observed_snapshots = await _observe_public_pages(COMPETITOR_SNAPSHOTS)
    profiles_created = 0
    profiles_updated = 0
    memory_nodes_created = 0

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_uuid))
            for snapshot in observed_snapshots:
                profile = await session.scalar(
                    select(CompetitorProfile).where(
                        CompetitorProfile.tenant_id == tenant_uuid,
                        CompetitorProfile.name == snapshot["name"],
                    )
                )
                body_hash = _hash_snapshot(snapshot)
                if not profile:
                    profile = CompetitorProfile(
                        tenant_id=tenant_uuid,
                        name=snapshot["name"],
                        website_url=snapshot.get("website_url", ""),
                        pricing_url=snapshot.get("pricing_url", ""),
                        last_website_hash=body_hash,
                        last_change_summary="Initial competitor profile created from public website research.",
                        last_checked_at=datetime.now(timezone.utc),
                        is_active=True,
                        metadata_json=snapshot,
                    )
                    session.add(profile)
                    profiles_created += 1
                else:
                    profile.website_url = snapshot.get("website_url", "")
                    profile.pricing_url = snapshot.get("pricing_url", "")
                    profile.last_change_summary = (
                        "Public profile refreshed; structured services, pricing signals, weaknesses, and Aliyar win reasons updated."
                    )
                    profile.last_website_hash = body_hash
                    profile.last_checked_at = datetime.now(timezone.utc)
                    profile.metadata_json = snapshot
                    profiles_updated += 1
                await session.flush()

                node, created = await _upsert_node(
                    session,
                    tenant_uuid,
                    node_type="competitor_gap",
                    title=f"Aliyar win reasons vs {snapshot['name']}",
                    content=_win_reason_content(snapshot),
                    source_table="competitor_profiles",
                    source_id=f"{profile.id}:win_reasons",
                    metadata={
                        "competitor": snapshot["name"],
                        "region": snapshot.get("region"),
                        "category": snapshot.get("category"),
                        "evidence_refs": snapshot.get("evidence_refs", []),
                    },
                )
                memory_nodes_created += int(created)

            session.add(
                AuditLog(
                    tenant_id=tenant_uuid,
                    action="competitor_profiles_seeded",
                    entity_type="competitor_profiles",
                    actor="CompetitorIntelligence",
                    details={
                        "profiles_created": profiles_created,
                        "profiles_updated": profiles_updated,
                        "memory_nodes_created": memory_nodes_created,
                    },
                )
            )

    return {
        "profiles_created": profiles_created,
        "profiles_updated": profiles_updated,
        "memory_nodes_created": memory_nodes_created,
        "competitors_ready": True,
    }


async def list_competitor_profiles(tenant_id: uuid.UUID | str) -> list[dict[str, Any]]:
    tenant_uuid = _coerce_tenant_id(tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_uuid))
            rows = (
                await session.execute(
                    select(CompetitorProfile)
                    .where(CompetitorProfile.tenant_id == tenant_uuid, CompetitorProfile.is_active == True)
                    .order_by(CompetitorProfile.name.asc())
                )
            ).scalars().all()
    return [_serialize_profile(row) for row in rows]


def _serialize_profile(profile: CompetitorProfile) -> dict[str, Any]:
    data = profile.metadata_json or {}
    return {
        "id": profile.id,
        "name": profile.name,
        "website_url": profile.website_url,
        "pricing_url": profile.pricing_url,
        "last_checked_at": profile.last_checked_at.isoformat() if profile.last_checked_at else None,
        "services": data.get("services", []),
        "pricing_signals": data.get("pricing_signals", []),
        "target_market": data.get("target_market", []),
        "positioning": data.get("positioning", ""),
        "weaknesses": data.get("weaknesses", []),
        "aliyar_win_reasons": data.get("aliyar_win_reasons", []),
        "evidence_refs": data.get("evidence_refs", []),
        "gap_analysis": _gap_analysis(data),
    }


def _win_reason_content(snapshot: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Competitor: {snapshot['name']}",
            f"Positioning: {snapshot.get('positioning', '')}",
            f"Services: {', '.join(snapshot.get('services', []))}",
            f"Pricing signals: {', '.join(snapshot.get('pricing_signals', []))}",
            f"Weaknesses: {', '.join(snapshot.get('weaknesses', []))}",
            f"Aliyar win reasons: {', '.join(snapshot.get('aliyar_win_reasons', []))}",
            f"Evidence: {', '.join(snapshot.get('evidence_refs', []))}",
        ]
    )


def _gap_analysis(snapshot: dict[str, Any]) -> str:
    weaknesses = snapshot.get("weaknesses", [])
    wins = snapshot.get("aliyar_win_reasons", [])
    return (
        "Aliyar Solutions should position around operational breadth, revenue execution, live dashboard visibility, "
        "and done-for-you implementation. "
        f"Observed competitor gaps: {'; '.join(weaknesses)}. "
        f"Recommended win path: {'; '.join(wins)}."
    )


def _hash_snapshot(snapshot: dict[str, Any]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _observe_public_pages(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    async with httpx.AsyncClient(
        timeout=12.0,
        follow_redirects=True,
        headers={"User-Agent": "AliyarSolutions-CompetitorIntel/1.0"},
    ) as client:
        for snapshot in snapshots:
            enriched = dict(snapshot)
            urls = list(dict.fromkeys(
                [
                    snapshot.get("website_url"),
                    snapshot.get("pricing_url"),
                    *(snapshot.get("evidence_refs") or []),
                ]
            ))
            enriched["public_page_observations"] = [
                observation
                for observation in [await _observe_url(client, url) for url in urls if url]
                if observation
            ]
            enriched["observed_at"] = datetime.now(timezone.utc).isoformat()
            observed.append(enriched)
    return observed


async def _observe_url(client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
    try:
        response = await client.get(url)
    except Exception:
        return None
    text = " ".join((response.text or "").split())
    return {
        "url": url,
        "status_code": response.status_code,
        "content_hash": hashlib.sha256(text[:50000].encode("utf-8", errors="ignore")).hexdigest(),
        "title": _extract_title(response.text or ""),
        "sampled_chars": min(len(text), 50000),
    }


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return " ".join(match.group(1).split())[:200]


def _coerce_tenant_id(tenant_id: uuid.UUID | str) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
