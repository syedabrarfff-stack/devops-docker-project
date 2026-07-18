from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.communication import CommunicationChannel, CommunicationDirection, CommunicationEvent
from app.models.lead import Lead
from app.services.aionx import client_digital_twin
from app.services.aionx.orchestration_cortex import fire_event
from app.services.communication.client_language import sanitize_client_text
from app.services.communication.ledger import record_communication_event, update_channel_status
from app.services.memory.manager import store_memory
from app.services.outreach.reply_handler import reply_handler

logger = logging.getLogger(__name__)
EVOLUTION_TIMEOUT_SECONDS = 6.0


def _base_url() -> str:
    return (settings.EVOLUTION_API_URL or "http://evolution:8080").rstrip("/")


def _api_key() -> str:
    return settings.EVOLUTION_API_KEY or ""


def _headers() -> dict[str, str]:
    return {"apikey": _api_key(), "Content-Type": "application/json"}


def _instance() -> str:
    return settings.WHATSAPP_INSTANCE_NAME or "jarvis-main"


def _normalize_number(value: str | None) -> str:
    if not value:
        return ""
    value = str(value).split("@", 1)[0]
    return re.sub(r"\D+", "", value)


def _extract_text(message: dict[str, Any]) -> str:
    if not isinstance(message, dict):
        return ""
    if isinstance(message.get("conversation"), str):
        return message["conversation"]
    extended = message.get("extendedTextMessage") or {}
    if isinstance(extended.get("text"), str):
        return extended["text"]
    image = message.get("imageMessage") or {}
    if isinstance(image.get("caption"), str):
        return image["caption"]
    document = message.get("documentMessage") or {}
    if isinstance(document.get("caption"), str):
        return document["caption"]
    return ""


def normalize_evolution_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    key = data.get("key") if isinstance(data.get("key"), dict) else {}
    message = data.get("message") if isinstance(data.get("message"), dict) else {}

    remote = (
        key.get("remoteJid")
        or data.get("remoteJid")
        or data.get("from")
        or data.get("sender")
        or data.get("number")
        or ""
    )
    from_me = bool(key.get("fromMe") or data.get("fromMe"))
    text = (
        _extract_text(message)
        or data.get("text")
        or data.get("body")
        or payload.get("text")
        or ""
    )
    message_id = key.get("id") or data.get("messageId") or data.get("id") or payload.get("id")
    return {
        "event": payload.get("event") or payload.get("type") or "MESSAGES_UPSERT",
        "instance": payload.get("instance") or data.get("instance") or _instance(),
        "message_id": str(message_id) if message_id else None,
        "thread_id": str(remote) if remote else None,
        "number": _normalize_number(remote),
        "raw_remote": remote,
        "from_me": from_me,
        "direction": "OUTBOUND" if from_me else "INBOUND",
        "contact_name": data.get("pushName") or data.get("name") or payload.get("pushName"),
        "text": sanitize_client_text(text),
        "timestamp": data.get("messageTimestamp") or payload.get("date_time") or payload.get("timestamp"),
        "raw": payload,
    }


async def evolution_request(method: str, path: str, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
    if not _api_key():
        return {"ok": False, "status": "not_configured", "error": "EVOLUTION_API_KEY is not configured."}
    url = f"{_base_url()}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=EVOLUTION_TIMEOUT_SECONDS) as client:
            response = await client.request(method.upper(), url, headers=_headers(), json=json)
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            try:
                data = response.json()
            except ValueError:
                # Evolution API can claim a JSON content-type while returning a
                # truncated/garbled body (e.g. mid-restart during an outage).
                # response.json() raises json.JSONDecodeError (a ValueError) in
                # that case — uncaught here, it propagated past both httpx
                # except clauses below and surfaced as an unhandled 500 from
                # /api/v1/communication/status, which is what turned a normal
                # "WhatsApp unreachable" status into the dashboard's opaque
                # "PROBE DEGRADED" instead of the intended "CHANNELS BLOCKED".
                data = {"raw": response.text[:4000]}
        else:
            data = {"raw": response.text[:4000]}
        return {
            "ok": response.status_code < 400,
            "status_code": response.status_code,
            "data": data,
            "url": url,
        }
    except httpx.TimeoutException as exc:
        return {"ok": False, "status": "timeout", "error": str(exc), "url": url}
    except httpx.HTTPError as exc:
        return {"ok": False, "status": "unreachable", "error": str(exc), "url": url}


async def evolution_status(db: AsyncSession | None = None, tenant_id: uuid.UUID | None = None) -> dict[str, Any]:
    configured = bool(settings.WHATSAPP_ENABLED and _api_key())
    state_result: dict[str, Any] = {"ok": False, "status": "not_configured"}
    connected = False
    blocker_code = None
    required_action = None

    if configured:
        state_result = await evolution_request("GET", f"/instance/connectionState/{_instance()}")
        state_text = str(state_result.get("data", {})).lower()
        connected = state_result.get("ok") and any(word in state_text for word in ("open", "connected", "online"))
        if not state_result.get("ok"):
            blocker_code = "evolution_unreachable"
            required_action = "Start Evolution API and create/connect the WhatsApp instance."
        elif not connected:
            blocker_code = "whatsapp_not_paired"
            required_action = "Open the QR pairing panel and link the Bahrain WhatsApp Business account."
    else:
        blocker_code = "evolution_api_key_missing"
        required_action = "Set EVOLUTION_API_KEY and restart backend/Evolution API."

    status = "connected" if connected else "blocked"
    result = {
        "provider": "evolution",
        "instance": _instance(),
        "configured": configured,
        "connected": connected,
        "status": status,
        "blocker_code": blocker_code,
        "required_action": required_action,
        "api_url": _base_url(),
        "public_url": settings.EVOLUTION_PUBLIC_URL,
        "webhook_url": _webhook_url(),
        "auto_reply_enabled": bool(settings.WHATSAPP_AUTO_REPLY_ENABLED),
        "auto_reply_min_confidence": float(settings.WHATSAPP_AUTO_REPLY_MIN_CONFIDENCE),
        "identity": settings.WHATSAPP_DISPLAY_IDENTITY or "Joseph David",
        "raw": state_result,
    }
    if db and tenant_id:
        await update_channel_status(
            db,
            tenant_id=tenant_id,
            channel=CommunicationChannel.WHATSAPP,
            provider="evolution",
            identity=result["identity"],
            configured=configured,
            connected=connected,
            status=status,
            blocker_code=blocker_code,
            required_action=required_action,
            details=result,
        )
    return result


async def create_instance() -> dict[str, Any]:
    body = {
        "instanceName": _instance(),
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
    }
    result = await evolution_request("POST", "/instance/create", json=body)
    if not result.get("ok"):
        result["fallback"] = await evolution_request("POST", "/instance/create", json={"instanceName": _instance()})
    return result


async def connect_qr(number: str | None = None) -> dict[str, Any]:
    query = ""
    normalized_number = _normalize_number(number)
    if normalized_number:
        query = f"?{urlencode({'number': normalized_number})}"
    result = await evolution_request("GET", f"/instance/connect/{_instance()}{query}")
    payload = result.get("data") if isinstance(result.get("data"), dict) else {}
    result["pairing_ready"] = bool(
        payload.get("base64")
        or payload.get("qrcode")
        or payload.get("code")
        or payload.get("pairingCode")
    )
    if result.get("ok") and not result["pairing_ready"]:
        result["required_action"] = (
            "Evolution is running, but no pairing code was returned yet. "
            "Use Retrieve Pairing Code with the Bahrain WhatsApp number, or restart the instance and retry."
        )
    return result


async def configure_webhook() -> dict[str, Any]:
    webhook_url = _webhook_url()
    body = {
        "webhook": {
            "enabled": True,
            "url": webhook_url,
            "byEvents": False,
            "base64": True,
            "events": [
                "MESSAGES_UPSERT",
                "MESSAGES_UPDATE",
                "SEND_MESSAGE",
                "CONNECTION_UPDATE",
            ],
        }
    }
    return await evolution_request("POST", f"/webhook/set/{_instance()}", json=body)


async def send_text(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    number: str,
    text: str,
    lead_id: uuid.UUID | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_text = sanitize_client_text(text)
    result = await evolution_request(
        "POST",
        f"/message/sendText/{_instance()}",
        json={"number": _normalize_number(number), "text": clean_text},
    )
    event = await record_communication_event(
        db,
        tenant_id=tenant_id,
        channel=CommunicationChannel.WHATSAPP,
        direction=CommunicationDirection.OUTBOUND,
        transport="evolution",
        external_message_id=_extract_message_id_from_send(result),
        from_address=settings.WHATSAPP_DISPLAY_IDENTITY or "Joseph David",
        to_address=_normalize_number(number),
        lead_id=lead_id,
        body_text=clean_text,
        status="sent" if result.get("ok") else "failed",
        processing_summary={"context": context or {}, "evolution": _summarize_transport_result(result)},
        raw_payload=result,
        processed_at=datetime.now(UTC),
    )
    return {"sent": bool(result.get("ok")), "event_id": str(event.id), "transport": result}


async def send_media(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    number: str,
    media_url: str,
    caption: str = "",
    media_type: str = "document",
    lead_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    body = {
        "number": _normalize_number(number),
        "mediatype": media_type,
        "media": media_url,
        "caption": sanitize_client_text(caption),
    }
    result = await evolution_request("POST", f"/message/sendMedia/{_instance()}", json=body)
    event = await record_communication_event(
        db,
        tenant_id=tenant_id,
        channel=CommunicationChannel.WHATSAPP,
        direction=CommunicationDirection.OUTBOUND,
        transport="evolution",
        external_message_id=_extract_message_id_from_send(result),
        from_address=settings.WHATSAPP_DISPLAY_IDENTITY or "Joseph David",
        to_address=_normalize_number(number),
        lead_id=lead_id,
        client_id=lead_id,
        body_text=caption or media_url,
        status="sent" if result.get("ok") else "failed",
        processing_summary={"media_type": media_type, "media_url": media_url, "evolution": _summarize_transport_result(result)},
        raw_payload=result,
        processed_at=datetime.now(UTC),
    )
    return {"sent": bool(result.get("ok")), "event_id": str(event.id), "transport": result}


async def _handle_message_update(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    normalized: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    if normalized.get("message_id"):
        try:
            existing = (await db.execute(
                select(CommunicationEvent).where(
                    CommunicationEvent.external_message_id == normalized["message_id"],
                ).limit(1)
            )).scalars().first()
            if existing:
                data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
                update_type = str(data.get("status") or data.get("update") or "").upper()
                new_status = {
                    "DELIVERY_ACK": "delivered",
                    "READ": "read",
                    "PLAYED": "read",
                    "SERVER_ACK": "sent",
                }.get(update_type, "updated")
                existing.status = new_status
                await db.flush()
                return {"accepted": True, "event_id": str(existing.id), "action": f"status_updated:{new_status}"}
        except Exception as exc:
            logger.warning("MESSAGES_UPDATE patch failed: %s", exc)
    event = await record_communication_event(
        db,
        tenant_id=tenant_id,
        channel=CommunicationChannel.WHATSAPP,
        direction=CommunicationDirection(normalized["direction"]),
        transport="evolution",
        external_message_id=normalized["message_id"],
        thread_id=normalized["thread_id"],
        from_address=normalized["number"],
        body_text="",
        status="delivery_update",
        raw_payload=payload,
        processed_at=datetime.now(UTC),
    )
    return {"accepted": True, "event_id": str(event.id), "action": "delivery_update_logged"}


async def process_inbound_webhook(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    normalized = normalize_evolution_payload(payload)
    event_type = normalized["event"]

    if event_type == "MESSAGES_UPDATE":
        return await _handle_message_update(db, tenant_id, normalized, payload)

    if normalized["direction"] != "INBOUND" or not normalized["text"]:
        event = await record_communication_event(
            db,
            tenant_id=tenant_id,
            channel=CommunicationChannel.WHATSAPP,
            direction=CommunicationDirection(normalized["direction"]),
            transport="evolution",
            external_message_id=normalized["message_id"],
            thread_id=normalized["thread_id"],
            from_address=normalized["number"],
            contact_name=normalized["contact_name"],
            body_text=normalized["text"],
            status="ignored_transport_event",
            raw_payload=payload,
            processed_at=datetime.now(UTC),
        )
        return {"accepted": True, "event_id": str(event.id), "action": "ignored_transport_event"}

    # Idempotency guard — Evolution API retries must not create duplicate records
    if normalized["message_id"]:
        try:
            dup = (await db.execute(
                select(CommunicationEvent).where(
                    CommunicationEvent.external_message_id == normalized["message_id"],
                    CommunicationEvent.direction == CommunicationDirection.INBOUND,
                ).limit(1)
            )).scalars().first()
            if dup:
                return {"accepted": True, "event_id": str(dup.id), "action": "duplicate_ignored"}
        except Exception as exc:
            logger.warning("Idempotency check failed (proceeding): %s", exc)

    lead = await _find_lead_by_number(db, tenant_id, normalized["number"])
    lead_id = lead.id if lead else None
    processing: dict[str, Any] = {
        "normalized": {k: v for k, v in normalized.items() if k != "raw"},
        "lead_matched": bool(lead_id),
        "architecture_route": [
            "WhatsApp",
            "Evolution API",
            "JARVIS webhook",
            "Client Digital Twin",
            "Prospect Psychology",
            "Decision Memory",
            "Council Awareness",
            "Human Interface Agent",
        ],
    }

    if lead_id:
        reply_result: dict[str, Any] = {}
        try:
            reply_result = await asyncio.wait_for(
                reply_handler.process_reply(lead_id, normalized["text"], tenant_id),
                timeout=15.0,
            )
            processing["reply_handler"] = reply_result
        except asyncio.TimeoutError:
            logger.warning("reply_handler timed out for lead %s", lead_id)
            processing["reply_handler"] = {"error": "timeout"}
        except Exception as exc:
            logger.exception("reply_handler failed for lead %s: %s", lead_id, exc)
            processing["reply_handler"] = {"error": str(exc)}

        try:
            interaction = await client_digital_twin.record_interaction(
                db,
                lead_id,
                interaction_type="WHATSAPP",
                hia_agent=settings.WHATSAPP_DISPLAY_IDENTITY or "Joseph David",
                sentiment=_sentiment_from_reply(reply_result.get("classification")),
                trust_delta=_trust_delta_from_reply(reply_result.get("classification")),
                summary=normalized["text"][:500],
                profile_updates={
                    "communication_preferences": {
                        "preferred_channel": "WHATSAPP",
                        "last_whatsapp_number": normalized["number"],
                    },
                    "preferred_hia_agent": settings.WHATSAPP_DISPLAY_IDENTITY or "Joseph David",
                },
                raw_notes=normalized["text"],
            )
            processing["twin_interaction_id"] = str(interaction.id)
        except Exception as exc:
            logger.exception("client_digital_twin failed for lead %s: %s", lead_id, exc)
            processing["twin_error"] = str(exc)

        try:
            cascade = await fire_event(
                db,
                "LEAD_REPLIED",
                {
                    "event_type": "LEAD_REPLIED",
                    "client_id": str(lead_id),
                    "lead_id": str(lead_id),
                    "interaction_type": "WHATSAPP_REPLY",
                    "sentiment": _sentiment_from_reply(reply_result.get("classification")),
                    "summary": normalized["text"][:500],
                    "problem": "Inbound WhatsApp reply requires Human Interface follow-up.",
                    "category": "OUTREACH",
                    "confidence": reply_result.get("confidence_score", 0.7),
                },
            )
            processing["cortex"] = cascade
        except Exception as exc:
            logger.warning("cortex fire_event failed: %s", exc)
            processing["cortex"] = {"error": str(exc)}

        try:
            await store_memory(
                db,
                content=(
                    f"WhatsApp interaction via Joseph David persona with "
                    f"{lead.company_name or lead.company or normalized['number']}: {normalized['text'][:700]}"
                ),
                memory_type="episodic",
                importance=0.75,
                tags=["whatsapp", "client_digital_twin", "decision_memory"],
                key=f"whatsapp:{lead_id}:{normalized['message_id'] or datetime.now(UTC).isoformat()}",
            )
        except Exception as exc:
            logger.warning("store_memory failed: %s", exc)

        response_text = reply_result.get("response_draft")
        if response_text and settings.WHATSAPP_AUTO_REPLY_ENABLED and float(reply_result.get("confidence_score") or 0) >= settings.WHATSAPP_AUTO_REPLY_MIN_CONFIDENCE:
            try:
                auto_send = await send_text(
                    db,
                    tenant_id=tenant_id,
                    number=normalized["number"],
                    text=response_text,
                    lead_id=lead_id,
                    context={"source": "whatsapp_auto_reply", "classification": reply_result.get("classification")},
                )
                processing["auto_reply"] = auto_send
            except Exception as exc:
                logger.warning("auto_reply send failed: %s", exc)
                processing["auto_reply"] = {"error": str(exc)}
        elif response_text:
            processing["draft_ready"] = response_text
            processing["auto_reply"] = "governance_gated"

    event = await record_communication_event(
        db,
        tenant_id=tenant_id,
        channel=CommunicationChannel.WHATSAPP,
        direction=CommunicationDirection.INBOUND,
        transport="evolution",
        external_message_id=normalized["message_id"],
        thread_id=normalized["thread_id"],
        from_address=normalized["number"],
        to_address=settings.WHATSAPP_DISPLAY_IDENTITY or "Joseph David",
        contact_name=normalized["contact_name"],
        lead_id=lead_id,
        client_id=lead_id,
        body_text=normalized["text"],
        status="processed" if lead_id else "unmatched",
        processing_summary=processing,
        raw_payload=payload,
        processed_at=datetime.now(UTC),
    )
    return {
        "accepted": True,
        "event_id": str(event.id),
        "lead_id": str(lead_id) if lead_id else None,
        "action": "processed_existing_pipeline" if lead_id else "logged_unmatched_inbound",
        "auto_reply_enabled": bool(settings.WHATSAPP_AUTO_REPLY_ENABLED),
        "processing_summary": processing,
    }


def _webhook_url() -> str:
    if settings.EVOLUTION_WEBHOOK_URL:
        return settings.EVOLUTION_WEBHOOK_URL
    base = (settings.APP_BASE_URL or "https://aliyarsolutions.com").rstrip("/")
    if base.startswith("http://localhost"):
        base = "https://aliyarsolutions.com"
    return f"{base}/api/v1/webhooks/whatsapp"


async def _find_lead_by_number(db: AsyncSession, tenant_id: uuid.UUID, number: str) -> Lead | None:
    normalized = _normalize_number(number)
    if not normalized:
        return None
    candidates = (
        await db.execute(
            select(Lead).where(
                Lead.tenant_id == tenant_id,
                or_(Lead.phone.is_not(None), Lead.enrichment_data.is_not(None)),
            ).limit(500)
        )
    ).scalars().all()
    for lead in candidates:
        phone_numbers = [lead.phone]
        enrichment = lead.enrichment_data or {}
        for key in ("phone", "mobile", "whatsapp", "whatsapp_number"):
            if enrichment.get(key):
                phone_numbers.append(str(enrichment.get(key)))
        if any(_normalize_number(value).endswith(normalized[-10:]) or normalized.endswith(_normalize_number(value)[-10:]) for value in phone_numbers if _normalize_number(value)):
            return lead
    return None


def _sentiment_from_reply(classification: Any) -> str:
    value = str(classification or "").upper()
    if value in {"INTERESTED", "QUESTION"}:
        return "positive"
    if value in {"NO"}:
        return "negative"
    return "neutral"


def _trust_delta_from_reply(classification: Any) -> float:
    value = str(classification or "").upper()
    if value == "INTERESTED":
        return 3.0
    if value == "QUESTION":
        return 1.0
    if value == "NO":
        return -2.0
    return 0.25


def _extract_message_id_from_send(result: dict[str, Any]) -> str | None:
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    for key in ("key", "message", "data"):
        nested = data.get(key)
        if isinstance(nested, dict):
            for id_key in ("id", "messageId"):
                if nested.get(id_key):
                    return str(nested[id_key])
    for id_key in ("id", "messageId"):
        if data.get(id_key):
            return str(data[id_key])
    return None


def _summarize_transport_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "status_code": result.get("status_code"),
        "status": result.get("status"),
        "error": result.get("error"),
    }
