from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.revenue import Client, ClientStatus

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientCreateRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    contact_name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=255)
    package_tier: Optional[str] = Field(default=None, max_length=80)
    mrr_usd: float = Field(default=0.0, ge=0)
    status: ClientStatus = ClientStatus.ACTIVE
    tenant_id: Optional[UUID] = None


class ClientUpdateRequest(BaseModel):
    company_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    contact_name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=255)
    package_tier: Optional[str] = Field(default=None, max_length=80)
    mrr_usd: Optional[float] = Field(default=None, ge=0)
    status: Optional[ClientStatus] = None
    tenant_id: Optional[UUID] = None


@router.post("")
async def create_client(request: Request, body: ClientCreateRequest):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_id))
            client = Client(
                tenant_id=tenant_id,
                company_name=body.company_name.strip(),
                contact_name=(body.contact_name or "").strip() or None,
                email=_clean_email(body.email),
                package_tier=(body.package_tier or "").strip() or None,
                mrr_usd=float(body.mrr_usd or 0.0),
                status=body.status,
            )
            session.add(client)
            await session.flush()
            _audit(
                session,
                tenant_id,
                "client_created",
                client.id,
                {
                    "company_name": client.company_name,
                    "contact_name": client.contact_name,
                    "email": client.email,
                    "package_tier": client.package_tier,
                    "mrr_usd": client.mrr_usd,
                    "status": client.status.value,
                },
            )
            await session.refresh(client)
            serialized = _serialize_client(client)

    try:
        from app.services.notifications.telegram import notify_telegram
        mrr = float(body.mrr_usd or 0)
        tier = (body.package_tier or "").capitalize() or "Growth"
        mrr_text = f"\n💰 *MRR:* ${mrr:,.0f}/mo" if mrr else ""
        await notify_telegram(
            f"🚀 *New Client Activated — {body.company_name.strip()}*"
            f"{mrr_text}\n"
            f"*Package:* {tier}\n\n"
            "Client is live in the Revenue Dashboard."
        )
    except Exception:
        pass

    return {"client": serialized}


@router.get("")
async def list_clients(
    request: Request,
    status: Optional[ClientStatus] = None,
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: Optional[UUID] = None,
):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(resolved_tenant_id))
            query = (
                select(Client)
                .where(Client.tenant_id == resolved_tenant_id)
                .order_by(Client.created_at.desc())
                .limit(limit)
            )
            if status:
                query = query.where(Client.status == status)
            rows = (await session.execute(query)).scalars().all()
            return {"clients": [_serialize_client(row) for row in rows]}


@router.get("/{client_id}")
async def get_client(client_id: UUID, request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    client = await _load_client(resolved_tenant_id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": _serialize_client(client)}


@router.patch("/{client_id}")
async def update_client(client_id: UUID, request: Request, body: ClientUpdateRequest):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_id))
            client = await session.scalar(
                select(Client).where(Client.tenant_id == tenant_id, Client.id == client_id)
            )
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

            before = _serialize_client(client)
            for field in ("company_name", "contact_name", "package_tier"):
                value = getattr(body, field)
                if value is not None:
                    setattr(client, field, value.strip() or None)
            if body.email is not None:
                client.email = _clean_email(body.email)
            if body.mrr_usd is not None:
                client.mrr_usd = float(body.mrr_usd)
            if body.status is not None:
                client.status = body.status

            await session.flush()
            after = _serialize_client(client)
            _audit(session, tenant_id, "client_updated", client.id, {"before": before, "after": after})
            await session.refresh(client)
            return {"client": _serialize_client(client)}


@router.post("/{client_id}/status")
async def update_client_status(
    client_id: UUID,
    request: Request,
    body: ClientUpdateRequest,
):
    if body.status is None:
        raise HTTPException(status_code=400, detail="status is required")
    return await update_client(client_id, request, body)


async def _load_client(tenant_id: UUID, client_id: UUID) -> Client | None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_id))
            return await session.scalar(select(Client).where(Client.tenant_id == tenant_id, Client.id == client_id))


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID]) -> UUID:
    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc


def _audit(session, tenant_id: UUID, action: str, entity_id: UUID, details: dict) -> None:
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            action=action,
            entity_type="client",
            entity_id=entity_id,
            actor="ClientLifecycleAPI",
            details=details,
            after_json=details,
        )
    )


def _clean_email(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    if "@" not in cleaned or "." not in cleaned.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=400, detail="email must be valid")
    return cleaned


def _serialize_client(client: Client) -> dict:
    return {
        "id": str(client.id),
        "tenant_id": str(client.tenant_id),
        "company_name": client.company_name,
        "contact_name": client.contact_name,
        "email": client.email,
        "package_tier": client.package_tier,
        "mrr_usd": float(client.mrr_usd or 0.0),
        "status": client.status.value if hasattr(client.status, "value") else str(client.status),
        "started_at": client.started_at.isoformat() if client.started_at else None,
        "created_at": client.created_at.isoformat() if client.created_at else None,
        "updated_at": client.updated_at.isoformat() if client.updated_at else None,
    }
