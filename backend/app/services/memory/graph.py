from __future__ import annotations

import asyncio
import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, text

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import ApprovalRequest, ApprovalStatus, AuditLog
from app.models.lead import Lead
from app.models.memory import MemoryGraphEdge, MemoryGraphNode
from app.models.service_catalog import ServiceDivision
from app.services.catalog.catalog_service import SEED_DIVISIONS, SYSTEM_TENANT_ID


EMBEDDING_DIMENSIONS = 1536


ALIYAR_COMPANY_PROFILE = """
Aliyar Solutions is a global technology operations company led by Syed Abrar.
The company sells practical business infrastructure: AI automation, sales systems,
cloud and DevOps, security, client portals, operational dashboards, content systems,
and business intelligence. The first revenue mission is to help small and mid-size
companies remove manual work, recover missed revenue, improve response speed, and
stabilize the systems they run on every day. Client-facing language must present
Aliyar Solutions as a specialist team, never as a bot, AI assistant, or freelancer.
""".strip()


ICP_PROFILE = """
Ideal customer profile: small and mid-size companies with 5-100 employees and
estimated revenue between $500K and $10M. Primary markets are UK, UAE, USA,
Australia, and Canada. Strong fit signals include manual follow-up, appointment
volume, repetitive admin, spreadsheet-based operations, weak CRM usage, slow
customer response, fragile cloud infrastructure, no observability, inconsistent
delivery tracking, or revenue leakage caused by missed communication.
""".strip()


async def seed_memory_graph(tenant_id: uuid.UUID | str) -> dict[str, Any]:
    tenant_uuid = _coerce_tenant_id(tenant_id)
    nodes_created = 0
    edges_created = 0

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_uuid))
            await _ensure_vector_schema(session)
            await _seed_catalog_if_empty(session)

            company_node, created = await _upsert_node(
                session,
                tenant_uuid,
                node_type="company_profile",
                title="Aliyar Solutions company profile",
                content=ALIYAR_COMPANY_PROFILE,
                source_table="system",
                source_id="aliyar_solutions_profile",
                metadata={"memory_seed": "company_profile"},
            )
            nodes_created += int(created)

            icp_node, created = await _upsert_node(
                session,
                tenant_uuid,
                node_type="icp_profile",
                title="Aliyar Solutions ideal customer profile",
                content=ICP_PROFILE,
                source_table="system",
                source_id="icp_profile",
                metadata={
                    "employee_range": "5-100",
                    "revenue_range": "$500K-$10M",
                    "markets": ["UK", "UAE", "USA", "Australia", "Canada"],
                },
            )
            nodes_created += int(created)

            services = (
                await session.execute(
                    select(ServiceDivision)
                    .where(ServiceDivision.is_active == True)
                    .order_by(ServiceDivision.sort_order.asc())
                    .limit(200)
                )
            ).scalars().all()
            service_nodes: list[MemoryGraphNode] = []
            for service in services:
                node, created = await _upsert_node(
                    session,
                    tenant_uuid,
                    node_type="service_catalog",
                    title=service.name,
                    content=_service_content(service),
                    source_table="service_divisions",
                    source_id=str(service.code),
                    metadata={
                        "division_group": service.division_group,
                        "pricing_model": service.pricing_model,
                        "price_range_usd": service.price_range_usd or {},
                        "target_industries": service.target_industries or [],
                    },
                )
                nodes_created += int(created)
                service_nodes.append(node)

            leads = (
                await session.execute(
                    select(Lead)
                    .where(Lead.tenant_id == tenant_uuid)
                    .order_by(Lead.score.desc(), Lead.created_at.desc())
                    .limit(1000)
                )
            ).scalars().all()
            lead_nodes: list[MemoryGraphNode] = []
            for lead in leads:
                node, created = await _upsert_node(
                    session,
                    tenant_uuid,
                    node_type="lead_profile",
                    title=_lead_name(lead),
                    content=_lead_content(lead),
                    source_table="leads",
                    source_id=str(lead.id),
                    metadata={
                        "score": float(lead.score or 0.0),
                        "status": getattr(lead.status, "value", str(lead.status)),
                        "industry": lead.industry,
                        "country": lead.country,
                    },
                )
                nodes_created += int(created)
                lead_nodes.append(node)

            approvals = (
                await session.execute(
                    select(ApprovalRequest)
                    .where(
                        ApprovalRequest.tenant_id == tenant_uuid,
                        ApprovalRequest.status == ApprovalStatus.PENDING,
                    )
                    .order_by(ApprovalRequest.priority.asc(), ApprovalRequest.created_at.asc())
                    .limit(200)
                )
            ).scalars().all()
            approval_nodes: list[MemoryGraphNode] = []
            for approval in approvals:
                node, created = await _upsert_node(
                    session,
                    tenant_uuid,
                    node_type="decision_memory",
                    title=approval.title or approval.action_type or "Pending approval",
                    content=_approval_content(approval),
                    source_table="approval_requests",
                    source_id=str(approval.id),
                    metadata={
                        "action_type": approval.action_type,
                        "risk_level": approval.risk_level,
                        "priority": approval.priority,
                        "status": approval.status.value,
                    },
                )
                nodes_created += int(created)
                approval_nodes.append(node)

            for service_node in service_nodes:
                edges_created += int(
                    await _upsert_edge(session, tenant_uuid, company_node, service_node, "offers_service", 0.95)
                )
                edges_created += int(
                    await _upsert_edge(session, tenant_uuid, icp_node, service_node, "icp_can_buy_service", 0.65)
                )

            for lead_node in lead_nodes:
                edges_created += int(
                    await _upsert_edge(session, tenant_uuid, lead_node, icp_node, "matched_against_icp", 0.8)
                )
                for service_node in _best_service_nodes_for_lead(lead_node, service_nodes):
                    edges_created += int(
                        await _upsert_edge(session, tenant_uuid, lead_node, service_node, "recommended_service", 0.75)
                    )

            for approval_node in approval_nodes:
                edges_created += int(
                    await _upsert_edge(session, tenant_uuid, approval_node, company_node, "requires_captain_decision", 0.9)
                )

            node_count = await session.scalar(
                select(func.count()).select_from(MemoryGraphNode).where(MemoryGraphNode.tenant_id == tenant_uuid)
            )
            edge_count = await session.scalar(
                select(func.count()).select_from(MemoryGraphEdge).where(MemoryGraphEdge.tenant_id == tenant_uuid)
            )
            session.add(
                AuditLog(
                    tenant_id=tenant_uuid,
                    action="memory_graph_seeded",
                    entity_type="memory_graph",
                    actor="MemoryGraphSeeder",
                    details={
                        "nodes_created": nodes_created,
                        "edges_created": edges_created,
                        "total_nodes": int(node_count or 0),
                        "total_edges": int(edge_count or 0),
                    },
                )
            )

    return {
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "total_nodes": int(node_count or 0),
        "total_edges": int(edge_count or 0),
        "memory_ready": True,
    }


async def search_memory_graph(query: str, tenant_id: uuid.UUID | str, limit: int = 5) -> dict[str, Any]:
    tenant_uuid = _coerce_tenant_id(tenant_id)
    query_embedding = _embed(query)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_uuid))
            nodes = (
                await session.execute(
                    select(MemoryGraphNode)
                    .where(MemoryGraphNode.tenant_id == tenant_uuid)
                    .order_by(MemoryGraphNode.updated_at.desc())
                    .limit(2000)
                )
            ).scalars().all()

            ranked = []
            for node in nodes:
                score = _cosine_similarity(query_embedding, node.embedding or [])
                ranked.append((score, node))
            ranked.sort(key=lambda item: item[0], reverse=True)
            top = ranked[: max(1, min(limit, 25))]

    return {
        "query": query,
        "results": [
            {
                "id": str(node.id),
                "node_type": node.node_type,
                "title": node.title,
                "score": round(float(score), 4),
                "content": node.content[:1200],
                "source_table": node.source_table,
                "source_id": node.source_id,
                "metadata": node.metadata_json or {},
            }
            for score, node in top
        ],
    }


async def graph_status(tenant_id: uuid.UUID | str) -> dict[str, Any]:
    tenant_uuid = _coerce_tenant_id(tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_uuid))
            nodes = await session.scalar(
                select(func.count()).select_from(MemoryGraphNode).where(MemoryGraphNode.tenant_id == tenant_uuid)
            )
            edges = await session.scalar(
                select(func.count()).select_from(MemoryGraphEdge).where(MemoryGraphEdge.tenant_id == tenant_uuid)
            )
    return {"nodes": int(nodes or 0), "edges": int(edges or 0), "memory_ready": bool(nodes)}


async def _upsert_node(
    session,
    tenant_id: uuid.UUID,
    *,
    node_type: str,
    title: str,
    content: str,
    source_table: str,
    source_id: str,
    metadata: dict[str, Any],
) -> tuple[MemoryGraphNode, bool]:
    embedding = _embed(f"{title}\n{content}\n{json.dumps(metadata, sort_keys=True, default=str)}")
    node = await session.scalar(
        select(MemoryGraphNode).where(
            MemoryGraphNode.tenant_id == tenant_id,
            MemoryGraphNode.source_table == source_table,
            MemoryGraphNode.source_id == source_id,
        )
    )
    created = False
    if not node:
        node = MemoryGraphNode(
            tenant_id=tenant_id,
            node_type=node_type,
            title=title,
            content=content,
            source_table=source_table,
            source_id=source_id,
            embedding=embedding,
            metadata_json=metadata,
        )
        session.add(node)
        created = True
    else:
        node.node_type = node_type
        node.title = title
        node.content = content
        node.embedding = embedding
        node.metadata_json = metadata
    await session.flush()
    await _write_vector_embedding(session, "memory_graph_nodes", node.id, embedding)
    return node, created


async def _upsert_edge(
    session,
    tenant_id: uuid.UUID,
    source_node: MemoryGraphNode,
    target_node: MemoryGraphNode,
    relationship_type: str,
    weight: float,
) -> bool:
    edge = await session.scalar(
        select(MemoryGraphEdge).where(
            MemoryGraphEdge.tenant_id == tenant_id,
            MemoryGraphEdge.source_node_id == source_node.id,
            MemoryGraphEdge.target_node_id == target_node.id,
            MemoryGraphEdge.relationship_type == relationship_type,
        )
    )
    if edge:
        edge.weight = weight
        edge.metadata_json = {"refreshed_at": datetime.now(timezone.utc).isoformat()}
        return False
    session.add(
        MemoryGraphEdge(
            tenant_id=tenant_id,
            source_node_id=source_node.id,
            target_node_id=target_node.id,
            relationship_type=relationship_type,
            weight=weight,
            metadata_json={"created_by": "memory_graph_seed"},
        )
    )
    return True


async def _ensure_vector_schema(session) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    try:
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        for table_name in (
            "memories",
            "memory_operational",
            "memory_strategic",
            "civilization_memory",
            "memory_graph_nodes",
        ):
            await session.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    "ADD COLUMN IF NOT EXISTS embedding_vector vector(1536)"
                )
            )
    except Exception:
        return


async def _seed_catalog_if_empty(session) -> None:
    existing = await session.scalar(select(func.count()).select_from(ServiceDivision))
    if existing:
        return
    for item in SEED_DIVISIONS:
        session.add(ServiceDivision(tenant_id=SYSTEM_TENANT_ID, **item))
    await session.flush()


_VECTOR_TABLE_WHITELIST = frozenset({
    "memory_graph_nodes",
    "memory_operational",
    "memory_strategic",
    "memories",
    "civilization_memory",
})


async def _write_vector_embedding(session, table_name: str, row_id: uuid.UUID, embedding: list[float]) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    if table_name not in _VECTOR_TABLE_WHITELIST:
        raise ValueError(f"table_name '{table_name}' is not whitelisted for vector embedding writes")
    try:
        await session.execute(
            text(
                f"UPDATE {table_name} "  # noqa: S608 — table_name whitelisted above
                "SET embedding_vector = CAST(:embedding AS vector) "
                "WHERE id = CAST(:row_id AS uuid)"
            ),
            {"embedding": _vector_literal(embedding), "row_id": str(row_id)},
        )
    except Exception:
        return


def _embed(text_value: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = [token for token in _normalise_text(text_value).split() if token]
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _normalise_text(text_value: str) -> str:
    return "".join(char.lower() if char.isalnum() else " " for char in text_value)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = sum(float(a[i]) * float(b[i]) for i in range(length))
    norm_a = math.sqrt(sum(float(v) * float(v) for v in a[:length]))
    norm_b = math.sqrt(sum(float(v) * float(v) for v in b[:length]))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in embedding[:EMBEDDING_DIMENSIONS]) + "]"


def _service_content(service: ServiceDivision) -> str:
    price = service.price_range_usd or {}
    return "\n".join(
        [
            f"Service: {service.name}",
            f"Code: {service.code}",
            f"Division: {service.division_group}",
            f"Description: {service.description}",
            f"Deliverables: {', '.join(service.deliverables or [])}",
            f"Technologies: {', '.join(service.technologies or [])}",
            f"Target industries: {', '.join(service.target_industries or [])}",
            f"Pricing model: {service.pricing_model}",
            f"Internal price range: ${price.get('min', 0)}-${price.get('max', 0)}",
            f"Duration: {service.duration_estimate}",
        ]
    )


def _lead_name(lead: Lead) -> str:
    return lead.company_name or lead.company or lead.contact_name or lead.email or "Unnamed lead"


def _lead_content(lead: Lead) -> str:
    return "\n".join(
        [
            f"Company: {_lead_name(lead)}",
            f"Contact: {lead.contact_name or 'unknown'}",
            f"Email: {lead.email or lead.contact_email or 'unknown'}",
            f"Industry: {lead.industry or 'unknown'}",
            f"Country: {lead.country or 'unknown'}",
            f"Website: {lead.website or lead.company_website or 'unknown'}",
            f"Score: {float(lead.score or 0.0)}",
            f"Status: {getattr(lead.status, 'value', lead.status)}",
            f"Pain points: {', '.join(lead.pain_points or [])}",
            f"Opportunity type: {lead.opportunity_type or 'unknown'}",
            f"Analysis: {lead.ai_analysis or lead.notes or ''}",
            f"Enrichment: {json.dumps(lead.enrichment_data or {}, default=str)[:1800]}",
        ]
    )


def _approval_content(approval: ApprovalRequest) -> str:
    return "\n".join(
        [
            f"Approval: {approval.title or approval.action_type or 'Pending approval'}",
            f"Summary: {approval.summary or ''}",
            f"Risk: {approval.risk_level or 'MEDIUM'}",
            f"Priority: {approval.priority}",
            f"Raised by: {approval.raised_by or 'JARVIS'}",
            f"Benefits: {approval.benefits or ''}",
            f"Risks: {approval.risks or ''}",
            f"Payload: {json.dumps(approval.payload or {}, default=str)[:1800]}",
        ]
    )


def _best_service_nodes_for_lead(
    lead_node: MemoryGraphNode,
    service_nodes: list[MemoryGraphNode],
    limit: int = 3,
) -> list[MemoryGraphNode]:
    lead_embedding = lead_node.embedding or []
    ranked = [
        (_cosine_similarity(lead_embedding, service_node.embedding or []), service_node)
        for service_node in service_nodes
    ]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [service_node for _score, service_node in ranked[:limit]]


def _coerce_tenant_id(tenant_id: uuid.UUID | str) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
