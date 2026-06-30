from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.routes.auth import get_current_captain
from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.core.rate_limit import limiter
from app.models.demo import DemoPackage
from app.services.demos.builder import demo_builder


router = APIRouter(prefix="/demos", tags=["Demos"])


class DemoGenerateRequest(BaseModel):
    lead_id: Optional[UUID] = None
    industry: Optional[str] = Field(default=None, max_length=100)
    pain_points: list[str] = Field(default_factory=list)
    company_name: Optional[str] = Field(default=None, max_length=300)
    prospect_email: Optional[str] = Field(default=None, max_length=320)
    tenant_id: Optional[UUID] = None


@router.post("/generate", dependencies=[Depends(get_current_captain)])
@limiter.limit("5/minute")
async def generate_demo(body: DemoGenerateRequest, request: Request, bg: BackgroundTasks):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    demo = await demo_builder.generate(
        tenant_id,
        lead_id=body.lead_id,
        industry=body.industry,
        pain_points=body.pain_points,
        company_name=body.company_name,
    )
    payload = _demo_payload(demo)
    if body.prospect_email:
        bg.add_task(_send_demo_email, body.prospect_email, body.company_name or "", payload["pdf_url"])
    return payload


@router.get("/{lead_id}")
@limiter.limit("30/minute")
async def get_demo_for_lead(lead_id: UUID, request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    demo = await _find_demo(resolved_tenant_id, lead_id)
    if not demo:
        raise HTTPException(status_code=404, detail="Demo package not found")
    return _demo_payload(demo)


@router.get("/{lead_id}/pdf")
@limiter.limit("30/minute")
async def get_demo_pdf(lead_id: UUID, request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    demo = await _find_demo(resolved_tenant_id, lead_id)
    if not demo or not demo.pdf_path:
        raise HTTPException(status_code=404, detail="Demo PDF not found")
    path = Path(demo.pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Demo PDF file missing")
    return FileResponse(
        str(path),
        media_type="application/pdf",
        filename=path.name,
    )


async def _find_demo(tenant_id: UUID, identifier: UUID) -> DemoPackage | None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_id))
            return await session.scalar(
                select(DemoPackage)
                .where(
                    DemoPackage.tenant_id == tenant_id,
                    (DemoPackage.lead_id == identifier) | (DemoPackage.id == identifier),
                )
                .order_by(DemoPackage.updated_at.desc())
            )


def _demo_payload(demo: DemoPackage) -> dict:
    return {
        "id": str(demo.id),
        "lead_id": str(demo.lead_id) if demo.lead_id else None,
        "company_name": demo.company_name,
        "industry": demo.industry,
        "pain_points": demo.pain_points,
        "status": demo.status,
        "demo_script": demo.demo_script,
        "roi_projection": demo.roi_projection,
        "pdf_path": demo.pdf_path,
        "pdf_url": f"{settings.APP_BASE_URL.rstrip('/')}/api/v1/demos/{demo.lead_id or demo.id}/pdf",
        "metadata": demo.metadata_json or {},
    }


async def _send_demo_email(email: str, company_name: str, pdf_url: str) -> None:
    import logging
    from app.services.outreach.email_transport import send_outbound_email

    subject = "Your Custom Solution Demo — Aliyar Solutions"
    body = (
        f"Hello,\n\n"
        f"Our team has prepared a personalised solution demonstration"
        f"{' for ' + company_name if company_name else ''}.\n\n"
        f"Access your demo package here:\n{pdf_url}\n\n"
        "We would love to walk you through this on a brief call. "
        "Please reply to schedule 15 minutes at your convenience.\n\n"
        "Warm regards,\nAliyar Solutions Team"
    )
    try:
        await send_outbound_email(to=email, subject=subject, body=body, to_name="")
    except Exception as exc:
        logging.getLogger(__name__).warning("Demo email delivery failed for %s: %s", email, exc)


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
