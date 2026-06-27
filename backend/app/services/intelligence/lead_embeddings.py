"""
Lead Semantic Embedding Service.

Generates OpenAI text-embedding-3-small vectors for each Lead record and
stores them in leads.embedding_vec (JSON list[float]).

Cosine similarity search runs in Python — no pgvector extension required.
When pgvector is enabled in PostgreSQL, the column type can be migrated to
vector(1536) and queries replaced with <=> operator for index-backed ANN search.

Public API:
  embed_lead(lead_id, db)       → generates + stores one lead's embedding
  embed_pending_leads(db)       → batch-embeds all leads missing a vector
  semantic_search_leads(query, db, limit, min_similarity)
                                → returns leads ranked by cosine similarity
"""
from __future__ import annotations

import logging
import math
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.lead import Lead

logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-3-small"
_EMBED_DIM = 1536


def _resolve_tenant(tenant_id) -> "UUID | None":
    if tenant_id:
        return tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))
    raw = getattr(settings, "JARVIS_DEFAULT_TENANT_ID", None)
    if raw:
        try:
            return UUID(str(raw))
        except (ValueError, AttributeError):
            pass
    return None


# ── Text representation ───────────────────────────────────────────────────────

def lead_to_text(lead: Lead) -> str:
    """Convert Lead fields into a rich text string for embedding."""
    parts: list[str] = []
    if lead.company_name or lead.company:
        parts.append(f"Company: {lead.company_name or lead.company}")
    if lead.industry:
        parts.append(f"Industry: {lead.industry}")
    if lead.country:
        parts.append(f"Country: {lead.country}")
    if lead.contact_name:
        parts.append(f"Contact: {lead.contact_name}")
    if lead.opportunity_type:
        parts.append(f"Opportunity: {lead.opportunity_type}")
    if lead.pain_points:
        pains = lead.pain_points if isinstance(lead.pain_points, list) else []
        if pains:
            parts.append(f"Pain points: {', '.join(str(p) for p in pains[:5])}")
    if lead.notes:
        parts.append(f"Notes: {lead.notes[:300]}")
    if lead.ai_analysis:
        parts.append(f"AI analysis: {lead.ai_analysis[:300]}")
    enrichment = lead.enrichment_data or {}
    if isinstance(enrichment, dict):
        for key in ("description", "headline", "summary", "job_title", "seniority"):
            val = enrichment.get(key)
            if val:
                parts.append(f"{key.replace('_', ' ').title()}: {str(val)[:200]}")
    return " | ".join(parts) or f"Lead: {lead.email or 'unknown'}"


# ── OpenAI embedding call ─────────────────────────────────────────────────────

async def _embed_text(text: str) -> list[float] | None:
    if not settings.OPENAI_API_KEY:
        return None
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.embeddings.create(model=_EMBED_MODEL, input=text[:8000])
        return resp.data[0].embedding
    except Exception as exc:
        logger.warning("Embedding API error: %s", exc)
        return None


# ── Cosine similarity ─────────────────────────────────────────────────────────

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Public functions ──────────────────────────────────────────────────────────

async def embed_lead(lead_id: str, db: AsyncSession) -> bool:
    """Generate and store embedding for one lead. Returns True on success."""
    try:
        uid = UUID(str(lead_id))
    except ValueError:
        return False

    lead = (await db.execute(select(Lead).where(Lead.id == uid))).scalar_one_or_none()
    if not lead:
        return False

    text = lead_to_text(lead)
    vec = await _embed_text(text)
    if vec is None:
        return False

    lead.embedding_vec = vec
    await db.commit()
    return True


async def embed_pending_leads(
    db: AsyncSession,
    limit: int = 50,
    tenant_id: "UUID | None" = None,
) -> dict[str, Any]:
    """Batch-embed all leads that have no embedding yet. Returns stats dict."""
    _tid = _resolve_tenant(tenant_id)
    q = select(Lead).where(Lead.embedding_vec.is_(None))
    if _tid:
        q = q.where(Lead.tenant_id == _tid)
    rows = (await db.execute(q.limit(limit))).scalars().all()

    succeeded, failed = 0, 0
    for lead in rows:
        text = lead_to_text(lead)
        vec = await _embed_text(text)
        if vec:
            lead.embedding_vec = vec
            succeeded += 1
        else:
            failed += 1

    if succeeded:
        await db.commit()

    return {"processed": len(rows), "succeeded": succeeded, "failed": failed}


async def semantic_search_leads(
    query: str,
    db: AsyncSession,
    limit: int = 10,
    min_similarity: float = 0.3,
    tenant_id: "UUID | None" = None,
) -> list[dict[str, Any]]:
    """
    Return leads ranked by cosine similarity to the query string.
    Only considers leads that already have an embedding vector.
    """
    query_vec = await _embed_text(query)
    if query_vec is None:
        return []

    _tid = _resolve_tenant(tenant_id)
    _q = select(Lead).where(Lead.embedding_vec.isnot(None))
    if _tid:
        _q = _q.where(Lead.tenant_id == _tid)
    rows = (await db.execute(_q)).scalars().all()

    scored: list[tuple[float, Lead]] = []
    for lead in rows:
        vec = lead.embedding_vec
        if not isinstance(vec, list) or len(vec) != _EMBED_DIM:
            continue
        sim = _cosine(query_vec, vec)
        if sim >= min_similarity:
            scored.append((sim, lead))

    scored.sort(key=lambda t: t[0], reverse=True)

    return [
        {
            "score": round(sim, 4),
            "id": str(lead.id),
            "company": lead.company_name or lead.company,
            "contact": lead.contact_name,
            "email": lead.email,
            "industry": lead.industry,
            "country": lead.country,
            "lead_score": lead.score,
            "tier": lead.tier,
            "status": lead.status.value if lead.status else None,
            "pain_points": lead.pain_points or [],
        }
        for sim, lead in scored[:limit]
    ]
