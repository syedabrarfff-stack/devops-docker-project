"""
HubSpot Sync — JARVIS → HubSpot CRM bridge.
Pushes qualified leads, deals, and status updates from JARVIS PostgreSQL
to HubSpot automatically. Runs as a scheduled job daily at 08:00.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Optional

import httpx
from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.lead import Lead, LeadStatus

logger = logging.getLogger(__name__)

HUBSPOT_BASE = "https://api.hubapi.com"
SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

# Pipeline stage mapping: JARVIS status → HubSpot deal stage name
STAGE_MAP = {
    LeadStatus.NEW:       "appointmentscheduled",
    LeadStatus.NURTURE:   "appointmentscheduled",
    LeadStatus.CONTACTED: "qualifiedtobuy",
    LeadStatus.REPLIED:   "presentationscheduled",
    LeadStatus.DEMO:      "decisionmakerboughtin",
    LeadStatus.PROPOSAL:  "contractsent",
    LeadStatus.WON:       "closedwon",
    LeadStatus.LOST:      "closedlost",
}


class HubSpotSyncService:
    def __init__(self):
        self.token = getattr(settings, "HUBSPOT_ACCESS_TOKEN", None)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _enabled(self) -> bool:
        if not self.token:
            logger.warning("HubSpot sync skipped — HUBSPOT_ACCESS_TOKEN not set")
            return False
        return True

    async def sync_all_qualified_leads(self, tenant_id: uuid.UUID | None = None) -> dict:
        if not self._enabled():
            return {"synced": 0, "errors": 0, "skipped": 0, "reason": "no_token"}

        target_tenant = tenant_id or SYSTEM_TENANT_ID
        synced = errors = skipped = 0

        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, str(target_tenant))
            rows = (
                await session.execute(
                    select(Lead).where(
                        Lead.tenant_id == target_tenant,
                        Lead.score >= 60,
                        Lead.status.in_([
                            LeadStatus.NURTURE,
                            LeadStatus.CONTACTED,
                            LeadStatus.REPLIED,
                            LeadStatus.DEMO,
                            LeadStatus.PROPOSAL,
                            LeadStatus.WON,
                        ]),
                    ).order_by(Lead.score.desc()).limit(200)
                )
            ).scalars().all()

            for lead in rows:
                already_synced = (lead.enrichment_data or {}).get("hubspot_contact_id")
                try:
                    if already_synced:
                        await self._update_deal_stage(lead)
                        skipped += 1
                    else:
                        contact_id = await self._create_or_find_contact(lead)
                        if contact_id:
                            deal_id = await self._create_deal(lead, contact_id)
                            # Save IDs back to enrichment_data
                            enrichment = dict(lead.enrichment_data or {})
                            enrichment["hubspot_contact_id"] = contact_id
                            enrichment["hubspot_deal_id"] = deal_id
                            enrichment["hubspot_synced_at"] = datetime.now(UTC).isoformat()
                            await session.execute(
                                update(Lead)
                                .where(Lead.id == lead.id)
                                .values(enrichment_data=enrichment)
                            )
                            synced += 1
                except Exception as exc:
                    logger.error("HubSpot sync error for lead %s: %s", lead.id, exc)
                    errors += 1

            await session.commit()

        logger.info("HubSpot sync complete — synced=%d errors=%d skipped=%d", synced, errors, skipped)
        return {"synced": synced, "errors": errors, "skipped": skipped, "timestamp": datetime.now(UTC).isoformat()}

    async def _create_or_find_contact(self, lead: Lead) -> Optional[str]:
        email = lead.email or lead.contact_email
        if not email:
            return None

        async with httpx.AsyncClient(timeout=15) as client:
            # Try to find existing
            search_resp = await client.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search",
                headers=self._headers(),
                json={"filterGroups": [{"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}], "properties": ["email", "hs_object_id"]},
            )
            if search_resp.status_code == 200:
                results = search_resp.json().get("results", [])
                if results:
                    return results[0]["id"]

            # Create new
            name_parts = (lead.contact_name or "").split(" ", 1)
            wa_number = getattr(lead, "whatsapp_number", None) or lead.phone or ""
            linkedin = getattr(lead, "linkedin_url", None) or (lead.enrichment_data or {}).get("linkedin_url", "")
            props = {
                "email": email,
                "firstname": name_parts[0] if name_parts else "",
                "lastname": name_parts[1] if len(name_parts) > 1 else "",
                "company": lead.company_name or lead.company or "",
                "phone": wa_number,
                "hs_lead_status": "NEW",
                "lifecyclestage": "lead",
                "country": lead.country or "",
                "jobtitle": (lead.enrichment_data or {}).get("decision_maker_title", ""),
                "website": lead.website or lead.company_website or "",
                "description": (
                    f"JARVIS ICP Score: {lead.score or 0:.0f}/100 | Source: {lead.source or 'jarvis'} | "
                    f"Industry: {lead.industry or 'unknown'}"
                    + (f" | WhatsApp: {wa_number}" if wa_number else "")
                    + (f" | LinkedIn: {linkedin}" if linkedin else "")
                ),
            }
            create_resp = await client.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts",
                headers=self._headers(),
                json={"properties": props},
            )
            if create_resp.status_code in (200, 201):
                return create_resp.json()["id"]
            logger.error("HubSpot contact create failed: %s", create_resp.text)
            return None

    async def _create_deal(self, lead: Lead, contact_id: str) -> Optional[str]:
        company = lead.company_name or lead.company or "Unknown Company"
        stage = STAGE_MAP.get(lead.status, "appointmentscheduled")
        score = lead.score or 0

        # Estimate deal value from score
        if score >= 85:
            amount = "5500"
        elif score >= 70:
            amount = "3500"
        else:
            amount = "2500"

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/deals",
                headers=self._headers(),
                json={
                    "properties": {
                        "dealname": f"{company} — Aliyar Solutions Retainer",
                        "dealstage": stage,
                        "amount": amount,
                        "deal_currency_code": "USD",
                        "pipeline": "default",
                        "closedate": "",
                        "description": f"JARVIS ICP Score: {score:.0f} | Industry: {lead.industry or 'N/A'} | Country: {lead.country or 'N/A'} | Assigned: {lead.assigned_persona or 'Darren Mitchell'}",
                    },
                    "associations": [{"to": {"id": contact_id}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]}],
                },
            )
            if resp.status_code in (200, 201):
                return resp.json()["id"]
            logger.error("HubSpot deal create failed: %s", resp.text)
            return None

    async def _update_deal_stage(self, lead: Lead) -> None:
        deal_id = (lead.enrichment_data or {}).get("hubspot_deal_id")
        if not deal_id:
            return
        stage = STAGE_MAP.get(lead.status, "appointmentscheduled")
        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{HUBSPOT_BASE}/crm/v3/objects/deals/{deal_id}",
                headers=self._headers(),
                json={"properties": {"dealstage": stage}},
            )

    async def push_single_lead(self, lead_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Push one specific lead to HubSpot immediately."""
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, str(tenant_id))
            lead = await session.scalar(select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id))
            if not lead:
                return {"error": "lead_not_found"}

        try:
            contact_id = await self._create_or_find_contact(lead)
            if contact_id:
                deal_id = await self._create_deal(lead, contact_id)
                return {"contact_id": contact_id, "deal_id": deal_id, "status": "synced"}
        except Exception as exc:
            return {"error": str(exc)}
        return {"status": "no_email"}


hubspot_sync = HubSpotSyncService()
