"""
WebSocket endpoint — real-time JARVIS updates to frontend.
Supports typed events, client subscriptions, and notification persistence.
"""
import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set, Optional

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

_clients: Set[WebSocket] = set()
_captain_clients: Set[WebSocket] = set()


async def broadcast(event_type: str, data: dict, persist: bool = False) -> None:
    """Broadcast an event to all connected frontend clients."""
    payload = json.dumps({"type": event_type, "data": data})
    dead = set()
    for ws in _clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)

    if persist:
        asyncio.create_task(_persist_notification(event_type, data))


async def captain_broadcast(event_type: str, data: dict) -> None:
    payload = json.dumps({"type": event_type, "data": data})
    dead = set()
    for ws in _captain_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _captain_clients.difference_update(dead)


async def broadcast_notification(title: str, body: str, level: str = "info",
                                   category: Optional[str] = None,
                                   reference: Optional[str] = None) -> None:
    """Broadcast a notification event and persist it."""
    data = {"title": title, "body": body, "level": level,
            "category": category, "reference": reference}
    await broadcast("notification", data, persist=True)


async def _persist_notification(event_type: str, data: dict) -> None:
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.notifications import NotificationLog
        async with AsyncSessionLocal() as db:
            async with db.begin():
                notif = NotificationLog(
                    channel="websocket",
                    title=data.get("title", event_type),
                    body=str(data.get("body", "")),
                    level=data.get("level", "info"),
                    category=data.get("category"),
                    reference=data.get("reference"),
                    delivered=len(_clients) > 0,
                )
                db.add(notif)
    except Exception as exc:
        logger.warning("WebSocket notification persistence failed: %s", exc)


def get_client_count() -> int:
    return len(_clients)


def get_captain_client_count() -> int:
    return len(_captain_clients)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    try:
        await ws.send_text(json.dumps({
            "type": "connected",
            "data": {
                "message": "JARVIS WebSocket connected, Captain.",
                "clients": len(_clients),
            },
        }))
        while True:
            data = await asyncio.wait_for(ws.receive_text(), timeout=30)
            msg = json.loads(data)
            t = msg.get("type")
            if t == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
            elif t == "subscribe":
                # Client requesting specific event types (future: per-client filters)
                await ws.send_text(json.dumps({
                    "type": "subscribed",
                    "data": {"events": msg.get("events", ["*"])},
                }))
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        _clients.discard(ws)


@router.websocket("/ws/captain")
async def captain_websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _captain_clients.add(ws)
    try:
        await ws.send_text(json.dumps({
            "type": "captain_connected",
            "data": await _captain_snapshot(),
        }))
        while True:
            data = await asyncio.wait_for(ws.receive_text(), timeout=30)
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong", "data": await _captain_snapshot()}))
            elif msg.get("type") == "subscribe":
                await ws.send_text(json.dumps({
                    "type": "captain_subscribed",
                    "data": {"events": msg.get("events", ["approval_created", "approval_decided"])},
                }))
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        _captain_clients.discard(ws)


async def _captain_snapshot() -> dict:
    from app.core.config import settings

    pending = 0
    if settings.JARVIS_DEFAULT_TENANT_ID:
        try:
            from app.services.governance.captain_queue import captain_queue

            pending = await captain_queue.pending_count(settings.JARVIS_DEFAULT_TENANT_ID)
        except Exception:
            pending = 0
    return {
        "pending_approvals": pending,
        "system_health": "online",
        "captain_sessions": len(_captain_clients),
        "general_sessions": len(_clients),
    }
