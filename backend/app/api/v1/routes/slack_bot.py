"""R6-1 Route: Slack Bot incoming webhook endpoint.

Slack Events API + Slash Commands handler.
Install the Slack App, point Slash Command URL + Events URL to:
  POST /api/v1/webhooks/slack/events
  POST /api/v1/webhooks/slack/command
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from app.services.notifications.slack_bot import (
    verify_slack_signature,
    handle_slash_command,
    handle_event,
)

router = APIRouter(prefix="/webhooks/slack", tags=["Slack Bot"])


@router.post("/command")
async def slack_slash_command(request: Request):
    """Receive /jarvis slash commands from Slack."""
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    form = await request.form()
    command = str(form.get("command", "/jarvis"))
    text = str(form.get("text", ""))
    channel_id = str(form.get("channel_id", ""))
    user_id = str(form.get("user_id", ""))
    response_url = str(form.get("response_url", ""))

    result = await handle_slash_command(command, text, channel_id, user_id, response_url)
    return result


@router.post("/events")
async def slack_events(request: Request):
    """Handle Slack Events API (mentions, app_home, etc.)."""
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    payload = await request.json()

    # URL verification challenge (Slack sends this when you first configure the Events URL)
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    event = payload.get("event", {})
    if event:
        import asyncio
        asyncio.create_task(handle_event(event))

    return Response(status_code=200)
