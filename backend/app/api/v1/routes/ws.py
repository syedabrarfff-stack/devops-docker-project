"""
WebSocket endpoint — real-time JARVIS updates to frontend.
"""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set

router = APIRouter(tags=["websocket"])

# Connected clients
_clients: Set[WebSocket] = set()


async def broadcast(event_type: str, data: dict):
    """Broadcast an event to all connected frontend clients."""
    payload = json.dumps({"type": event_type, "data": data})
    dead = set()
    for ws in _clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    try:
        await ws.send_text(json.dumps({
            "type": "connected",
            "data": {"message": "JARVIS WebSocket connected, Captain."},
        }))
        while True:
            # Keep alive + handle incoming pings
            data = await asyncio.wait_for(ws.receive_text(), timeout=30)
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        _clients.discard(ws)
