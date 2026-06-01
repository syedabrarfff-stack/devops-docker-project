from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.memory import CivilizationMemory, MemoryOperational, MemoryStrategic

logger = logging.getLogger(__name__)


class MemoryEngine:
    async def set_working(self, key: str, value: dict, ttl_hours: int = 24, tenant_id=None) -> None:
        tenant_uuid = _tenant_uuid(tenant_id)
        redis = await _redis()
        redis_key = _working_key(tenant_uuid, key)
        payload = {
            "key": key,
            "value": value or {},
            "stored_at": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_uuid),
        }
        await redis.set(redis_key, json.dumps(payload, default=str), ex=max(60, int(ttl_hours or 24) * 3600))

    async def get_working(self, key: str, tenant_id=None) -> dict | None:
        tenant_uuid = _tenant_uuid(tenant_id)
        redis = await _redis()
        raw = await redis.get(_working_key(tenant_uuid, key))
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return data.get("value", data)
        except json.JSONDecodeError:
            return {"raw": raw}

    async def clear_working(self, tenant_id=None) -> None:
        tenant_uuid = _tenant_uuid(tenant_id)
        redis = await _redis()
        keys = [key async for key in redis.scan_iter(_working_pattern(tenant_uuid))]
        if keys:
            await redis.delete(*keys)

    async def store_operational(
        self,
        category: str,
        content: str,
        source: str,
        tenant_id=None,
    ) -> MemoryOperational:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                memory = MemoryOperational(
                    tenant_id=tenant_uuid,
                    category=_clean_category(category),
                    content=content,
                    source=source or "unknown",
                    metadata_json={"ttl_days": 90},
                    expires_at=datetime.now(UTC) + timedelta(days=90),
                )
                session.add(memory)
                await session.flush()
                await _audit(
                    session,
                    tenant_uuid,
                    "memory_operational_stored",
                    "memory_operational",
                    memory.id,
                    {"category": memory.category, "source": memory.source},
                )
                await session.refresh(memory)
                return memory

    async def retrieve_operational(
        self,
        category: str,
        limit: int = 50,
        tenant_id=None,
    ) -> list[MemoryOperational]:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(MemoryOperational)
                        .where(
                            MemoryOperational.tenant_id == tenant_uuid,
                            MemoryOperational.category == _clean_category(category),
                        )
                        .order_by(MemoryOperational.created_at.desc())
                        .limit(max(1, min(int(limit or 50), 500)))
                    )
                ).scalars().all()
                return list(rows)

    async def prune_operational(self, tenant_id=None) -> int:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                result = await session.execute(
                    delete(MemoryOperational).where(
                        MemoryOperational.tenant_id == tenant_uuid,
                        MemoryOperational.created_at < datetime.now(UTC) - timedelta(days=90),
                    )
                )
                deleted = int(result.rowcount or 0)
                await _audit(
                    session,
                    tenant_uuid,
                    "memory_operational_pruned",
                    "memory_operational",
                    None,
                    {"deleted": deleted},
                )
                return deleted

    async def store_strategic(
        self,
        category: str,
        content: str,
        tags: list,
        tenant_id=None,
    ) -> MemoryStrategic:
        tenant_uuid = _tenant_uuid(tenant_id)
        embedding = await _embed_text(content)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                memory = MemoryStrategic(
                    tenant_id=tenant_uuid,
                    category=_clean_category(category),
                    content=content,
                    tags=tags or [],
                    embedding=embedding,
                    metadata_json={"embedding_model": "text-embedding-3-large"},
                )
                session.add(memory)
                await session.flush()
                await _audit(
                    session,
                    tenant_uuid,
                    "memory_strategic_stored",
                    "memory_strategic",
                    memory.id,
                    {"category": memory.category, "tags": memory.tags},
                )
                await session.refresh(memory)
                return memory

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.75,
        tenant_id=None,
    ) -> list[MemoryStrategic]:
        tenant_uuid = _tenant_uuid(tenant_id)
        query_embedding = await _embed_text(query)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                candidates = (
                    await session.execute(
                        select(MemoryStrategic)
                        .where(MemoryStrategic.tenant_id == tenant_uuid)
                        .order_by(MemoryStrategic.created_at.desc())
                        .limit(1000)
                    )
                ).scalars().all()

                scored: list[tuple[float, MemoryStrategic]] = []
                for memory in candidates:
                    score = _cosine_similarity(query_embedding, memory.embedding or [])
                    if score >= float(threshold):
                        setattr(memory, "similarity_score", round(score, 4))
                        scored.append((score, memory))
                scored.sort(key=lambda item: item[0], reverse=True)
                return [memory for _, memory in scored[: max(1, min(int(limit or 10), 100))]]

    async def promote_from_operational(self, memory_id, tenant_id=None) -> MemoryStrategic:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                operational = await session.scalar(
                    select(MemoryOperational).where(
                        MemoryOperational.tenant_id == tenant_uuid,
                        MemoryOperational.id == uuid.UUID(str(memory_id)),
                    )
                )
                if not operational:
                    raise ValueError("Operational memory not found")

        embedding = await _embed_text(operational.content)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                strategic = MemoryStrategic(
                    tenant_id=tenant_uuid,
                    category=operational.category,
                    content=operational.content,
                    tags=[operational.category, "promoted", operational.source],
                    embedding=embedding,
                    source_operational_id=operational.id,
                    metadata_json={
                        "embedding_model": "text-embedding-3-large",
                        "promoted_from": str(operational.id),
                    },
                )
                session.add(strategic)
                await session.flush()
                await _audit(
                    session,
                    tenant_uuid,
                    "memory_operational_promoted",
                    "memory_strategic",
                    strategic.id,
                    {"operational_id": str(operational.id), "category": strategic.category},
                )
                await session.refresh(strategic)
                return strategic

    async def record_milestone(self, event_type: str, content: str, tenant_id=None) -> CivilizationMemory:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                previous_hash = await session.scalar(
                    select(CivilizationMemory.record_hash)
                    .where(CivilizationMemory.tenant_id == tenant_uuid)
                    .order_by(CivilizationMemory.created_at.desc())
                    .limit(1)
                )
                record_hash = _record_hash(tenant_uuid, event_type, content, previous_hash)
                memory = CivilizationMemory(
                    tenant_id=tenant_uuid,
                    event_type=_clean_category(event_type),
                    content=content,
                    previous_hash=previous_hash,
                    record_hash=record_hash,
                    metadata_json={"immutable": True, "hash_algorithm": "sha256"},
                )
                session.add(memory)
                await session.flush()
                await _audit(
                    session,
                    tenant_uuid,
                    "civilization_memory_recorded",
                    "civilization_memory",
                    memory.id,
                    {"event_type": memory.event_type, "record_hash": record_hash},
                )
                await session.refresh(memory)
                return memory

    async def consolidate_working_to_operational(self, tenant_id=None) -> dict:
        tenant_uuid = _tenant_uuid(tenant_id)
        redis = await _redis()
        keys = [key async for key in redis.scan_iter(_working_pattern(tenant_uuid))]
        stored = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                for key in keys:
                    raw = await redis.get(key)
                    if not raw:
                        continue
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        payload = {"raw": raw}
                    memory = MemoryOperational(
                        tenant_id=tenant_uuid,
                        category="working_memory",
                        content=json.dumps(payload.get("value", payload), default=str),
                        source=f"redis:{payload.get('key', key)}",
                        metadata_json={"consolidated_from": "redis_working_memory"},
                        expires_at=datetime.now(UTC) + timedelta(days=90),
                    )
                    session.add(memory)
                    stored += 1
                pruned_result = await session.execute(
                    delete(MemoryOperational).where(
                        MemoryOperational.tenant_id == tenant_uuid,
                        MemoryOperational.created_at < datetime.now(UTC) - timedelta(days=90),
                    )
                )
                pruned = int(pruned_result.rowcount or 0)
                await _audit(
                    session,
                    tenant_uuid,
                    "memory_daily_consolidation",
                    "memory_operational",
                    None,
                    {"working_records_stored": stored, "operational_records_pruned": pruned},
                )
        if keys:
            await redis.delete(*keys)
        return {"working_records_stored": stored, "operational_records_pruned": pruned}

    async def promote_high_relevance_operational(self, tenant_id=None, limit: int = 20) -> dict:
        tenant_uuid = _tenant_uuid(tenant_id)
        promoted = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                candidates = (
                    await session.execute(
                        select(MemoryOperational)
                        .where(MemoryOperational.tenant_id == tenant_uuid)
                        .order_by(MemoryOperational.created_at.desc())
                        .limit(200)
                    )
                ).scalars().all()
                selected = []
                for memory in candidates:
                    if promoted + len(selected) >= max(1, min(int(limit or 20), 100)):
                        break
                    exists = await session.scalar(
                        select(MemoryStrategic.id).where(
                            MemoryStrategic.tenant_id == tenant_uuid,
                            MemoryStrategic.source_operational_id == memory.id,
                        )
                    )
                    if exists:
                        continue
                    if _is_high_relevance(memory):
                        selected.append(memory)

        for memory in selected:
            await self.promote_from_operational(memory.id, tenant_uuid)
            promoted += 1
        return {"promoted": promoted}


async def _redis():
    if not settings.REDIS_URL:
        raise RuntimeError("REDIS_URL is required for working memory")
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def _embed_text(text: str) -> list[float]:
    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.embeddings.create(model="text-embedding-3-large", input=text[:8000])
            return list(response.data[0].embedding)
        except Exception as exc:
            logger.warning("OpenAI embedding failed; using deterministic fallback: %s", exc)
    return await asyncio.to_thread(_fallback_embedding, text)


def _fallback_embedding(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    words = [word.lower() for word in text.split() if word.strip()]
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    size = min(len(a), len(b))
    dot = sum(float(a[i]) * float(b[i]) for i in range(size))
    norm_a = math.sqrt(sum(float(value) * float(value) for value in a[:size]))
    norm_b = math.sqrt(sum(float(value) * float(value) for value in b[:size]))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


async def _audit(session, tenant_id: uuid.UUID, action: str, entity_type: str, entity_id, details: dict) -> None:
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=uuid.UUID(str(entity_id)) if entity_id else None,
            actor="MemoryEngine",
            after_json=details,
            details=details,
        )
    )


def _working_key(tenant_id: uuid.UUID, key: str) -> str:
    return f"jarvis:working:{tenant_id}:{key.strip()}"


def _working_pattern(tenant_id: uuid.UUID) -> str:
    return f"jarvis:working:{tenant_id}:*"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    resolved = tenant_id or settings.JARVIS_DEFAULT_TENANT_ID
    if not resolved:
        raise ValueError("tenant_id is required")
    return uuid.UUID(str(resolved))


def _clean_category(value: str) -> str:
    cleaned = (value or "general").strip().lower().replace(" ", "_")
    return cleaned[:120] or "general"


def _record_hash(tenant_id: uuid.UUID, event_type: str, content: str, previous_hash: str | None) -> str:
    payload = json.dumps(
        {
            "tenant_id": str(tenant_id),
            "event_type": event_type,
            "content": content,
            "previous_hash": previous_hash,
            "recorded_at": datetime.now(UTC).isoformat(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_high_relevance(memory: MemoryOperational) -> bool:
    category = (memory.category or "").lower()
    if category in {"decision", "client", "learning", "proposal", "revenue", "risk", "incident", "captain"}:
        return True
    if len(memory.content or "") >= 300:
        return True
    return any(token in (memory.content or "").lower() for token in ["won", "lost", "approved", "rejected", "client", "revenue"])


memory_engine = MemoryEngine()
