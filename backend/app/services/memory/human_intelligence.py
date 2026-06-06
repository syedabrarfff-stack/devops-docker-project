from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.memory import MemoryStrategic
from app.services.memory.graph import _upsert_edge, _upsert_node
from app.services.memory.memory_engine import _embed_text

HUMAN_INTELLIGENCE_KB: dict[str, Any] = {
    "name": "jarvis_human_intelligence",
    "stratum": "M2_identity_memory",
    "purpose": "Permanent decision, psychology, communication, and scaling intelligence for all client-facing and strategic agents.",
    "sections": {
        "decision_frameworks": {
            "Bezos": "Work backwards from the customer. What does the client actually want, not what they asked for?",
            "Musk": "First principles. Strip away assumptions. What is the physics of this problem?",
            "Munger": "Inversion. What would guarantee failure? Eliminate that first.",
            "Jobs": "What can be removed? Simplicity is the ultimate sophistication.",
            "Buffett": "What is the moat? What protects this value from competitors?",
            "Tata": "Values as strategy. What decision would we be proud of in 20 years?",
            "Sun Tzu": "Win before the battle. Prepare so thoroughly that victory is inevitable.",
            "Drucker": "What is the theory of the business? Does this action serve the customer or serve us?",
        },
        "client_psychology": {
            "pain_first": "People buy to avoid pain, not to gain benefit. Always lead with the pain.",
            "trust_specificity": "People buy from people they trust. Trust is built through specificity, not claims.",
            "risk_reduction": "People stall when they fear being wrong. Reduce perceived risk, not price.",
            "felt_understood": "People say yes when they feel understood. Prove knowledge of their world before pitching.",
            "price_discipline": "The person who speaks first about price loses. Anchor on value, let the client ask.",
            "pilot_safety": "A 90-day pilot removes the biggest objection: commitment fear.",
        },
        "communication_intelligence": {
            "match_energy": "Match the client's energy level and vocabulary.",
            "silence": "Silence is a tool. After making a strong point, stop talking.",
            "no_pause_filling": "Never fill a pause with more selling. Thinking means interest.",
            "questions": "Questions are more powerful than statements.",
            "bad_news_early": "Bad news early, good news late. Never bury problems at the end.",
            "one_ask": "One ask per communication. Never give someone two decisions at once.",
        },
        "scaling_intelligence": {
            "TCS": "Pilot programs become contracts. Reduce entry barrier, expand after trust.",
            "Accenture": "Industry specialization creates pricing power. Generalists compete on price, specialists set price.",
            "McKinsey": "The insight matters more than the deck. One insight should change how they see the problem.",
            "Amazon": "The flywheel. Every service should feed every other service.",
            "Infosys": "Capability before client. Build the skill before the market asks for it.",
        },
    },
    "agent_usage_rules": {
        "sales_agent": "Read before writing any outreach. Lead with pain, specificity, one question, one soft ask, no pricing unless asked.",
        "call_agent": "Read before every call. Match energy, ask questions, reduce risk, never fill silence with selling.",
        "council": "Read before reviewing decisions. Use inversion, customer-backwards thinking, moat, values, and risk reduction.",
    },
}


def human_intelligence_context(max_chars: int = 2400) -> str:
    parts = [
        "JARVIS Human Intelligence M2:",
        "Lead with client pain and specificity; reduce perceived risk before discussing scope.",
        "Use one ask per message; do not reveal pricing unless the client asks or Captain approves.",
        "Work backwards from what the client actually wants; use first principles and inversion to remove failure points.",
        "For calls: match client energy, ask questions, pause after strong points, and never over-sell.",
    ]
    for section_name, section in HUMAN_INTELLIGENCE_KB["sections"].items():
        values = "; ".join(f"{key}: {value}" for key, value in section.items())
        parts.append(f"{section_name}: {values}")
    return "\n".join(parts)[: max(200, int(max_chars or 2400))]


async def seed_human_intelligence(tenant_id=None) -> dict[str, Any]:
    tenant_uuid = _tenant_uuid(tenant_id)
    content = json.dumps(HUMAN_INTELLIGENCE_KB, indent=2, sort_keys=True)
    nodes_created = 0
    edges_created = 0

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_uuid))
            strategic = await session.scalar(
                select(MemoryStrategic)
                .where(
                    MemoryStrategic.tenant_id == tenant_uuid,
                    MemoryStrategic.category == "m2_identity_human_intelligence",
                )
                .limit(1)
            )
            if strategic and strategic.metadata_json.get("version") == "phase_2_v1":
                return {
                    "knowledge_base": "jarvis_human_intelligence",
                    "stratum": "M2_identity_memory",
                    "strategic_memory_id": str(strategic.id),
                    "nodes_created": 0,
                    "edges_created": 0,
                    "sections": len(HUMAN_INTELLIGENCE_KB["sections"]),
                    "m2_ready": True,
                    "skipped": "already_seeded",
                }

            embedding = await _embed_text(content)
            if not strategic:
                strategic = MemoryStrategic(
                    tenant_id=tenant_uuid,
                    category="m2_identity_human_intelligence",
                    content=content,
                    tags=["m2", "identity", "human_intelligence", "client_psychology", "sales"],
                    embedding=embedding,
                    metadata_json={"name": "jarvis_human_intelligence", "version": "phase_2_v1"},
                )
                session.add(strategic)
            else:
                strategic.content = content
                strategic.tags = ["m2", "identity", "human_intelligence", "client_psychology", "sales"]
                strategic.embedding = embedding
                strategic.metadata_json = {"name": "jarvis_human_intelligence", "version": "phase_2_v1"}
            await session.flush()

            root_node, created = await _upsert_node(
                session,
                tenant_uuid,
                node_type="m2_human_intelligence",
                title="JARVIS Human Intelligence Knowledge Base",
                content=content,
                source_table="memory_strategic",
                source_id="jarvis_human_intelligence",
                metadata={"stratum": "M2_identity_memory", "sections": list(HUMAN_INTELLIGENCE_KB["sections"].keys())},
            )
            nodes_created += int(created)

            for section_key, section in HUMAN_INTELLIGENCE_KB["sections"].items():
                section_content = json.dumps(section, indent=2, sort_keys=True)
                section_node, created = await _upsert_node(
                    session,
                    tenant_uuid,
                    node_type="m2_human_intelligence_section",
                    title=f"Human Intelligence - {section_key.replace('_', ' ').title()}",
                    content=section_content,
                    source_table="memory_strategic",
                    source_id=f"jarvis_human_intelligence:{section_key}",
                    metadata={"stratum": "M2_identity_memory", "section": section_key},
                )
                nodes_created += int(created)
                edges_created += int(
                    await _upsert_edge(session, tenant_uuid, root_node, section_node, "contains_human_intelligence_section", 1.0)
                )

            session.add(
                AuditLog(
                    tenant_id=tenant_uuid,
                    action="human_intelligence_seeded",
                    entity_type="memory_strategic",
                    entity_id=strategic.id,
                    actor="HumanIntelligenceSeeder",
                    details={
                        "nodes_created": nodes_created,
                        "edges_created": edges_created,
                        "stratum": "M2_identity_memory",
                    },
                )
            )

    return {
        "knowledge_base": "jarvis_human_intelligence",
        "stratum": "M2_identity_memory",
        "strategic_memory_id": str(strategic.id),
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "sections": len(HUMAN_INTELLIGENCE_KB["sections"]),
        "m2_ready": True,
    }


def _tenant_uuid(value=None) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        raise ValueError("tenant_id is required")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))
