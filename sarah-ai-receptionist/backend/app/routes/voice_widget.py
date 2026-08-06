"""Browser-based "Call Sarah" widget — Twilio Voice SDK (WebRTC).

Two endpoints:
  POST /token          -- public. Mints a short-lived Twilio Access Token so
                           a marketing-site visitor's browser can place a
                           WebRTC call without ever seeing a real Twilio
                           credential.
  POST /browser-call    -- Twilio's Voice Request URL for the TwiML
                           Application the token above is scoped to. Twilio
                           calls this the same way it calls /incoming-call
                           for a real phone call; the difference is there's
                           no real "To" number, so this always routes into
                           the seeded is_demo clinic instead of doing a
                           phone-number lookup.
"""

import logging
import uuid
from xml.sax.saxutils import escape as xml_escape

import redis.asyncio as redis_lib
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

from app.config.settings import get_settings
from app.core.database import get_db_context
from app.models.clinic import Clinic
from app.routes.call_handler import (
    CONSENT_DISCLOSURE,
    _mark_call_validated,
    _validate_twilio_request,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice-widget"])
settings = get_settings()

_TOKEN_TTL_SECONDS = 3600
_TOKEN_RATE_LIMIT_MAX = 20
_TOKEN_RATE_LIMIT_WINDOW_SECONDS = 3600


class TokenOut(BaseModel):
    token: str
    identity: str


async def _check_widget_rate_limit(client_ip: str) -> None:
    """Caps how many WebRTC access tokens one IP can mint per hour. Each
    token is itself a real, billable Twilio call waiting to happen, so this
    guards against a scripted flood driving up call minutes -- separate from
    (and stricter than) Sarah's own login rate limit, since this endpoint
    has no auth at all."""
    r = redis_lib.from_url(settings.redis_url)
    try:
        key = f"voice-widget:token-attempts:{client_ip}"
        attempts = await r.incr(key)
        if attempts == 1:
            await r.expire(key, _TOKEN_RATE_LIMIT_WINDOW_SECONDS)
        if attempts > _TOKEN_RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Too many demo call requests from this network. Try again later.",
            )
    finally:
        await r.aclose()


@router.post("/token", response_model=TokenOut)
async def get_voice_widget_token(request: Request):
    if not (settings.twilio_voice_api_key_sid and settings.twilio_voice_api_key_secret
            and settings.twilio_voice_twiml_app_sid):
        raise HTTPException(status_code=503, detail="The browser demo call is not configured yet.")

    client_ip = request.client.host if request.client else "unknown"
    await _check_widget_rate_limit(client_ip)

    identity = f"web-visitor-{uuid.uuid4().hex[:12]}"

    token = AccessToken(
        settings.twilio_account_sid,
        settings.twilio_voice_api_key_sid,
        settings.twilio_voice_api_key_secret,
        identity=identity,
        ttl=_TOKEN_TTL_SECONDS,
    )
    # incoming_allow=False: this identity can only place the one outgoing
    # call the widget offers -- it can't be used to receive arbitrary calls
    # routed to it, which would open a second, unintended entry point.
    voice_grant = VoiceGrant(
        outgoing_application_sid=settings.twilio_voice_twiml_app_sid,
        incoming_allow=False,
    )
    token.add_grant(voice_grant)

    return TokenOut(token=token.to_jwt(), identity=identity)


@router.post("/browser-call")
async def browser_call(request: Request):
    """Twilio's Voice Request URL for the demo TwiML Application. Same
    validation + streaming shape as /incoming-call in call_handler.py, but
    always resolves to the seeded is_demo clinic since there's no real
    dialed number to look up."""
    form = await request.form()
    form_dict = dict(form)

    if not _validate_twilio_request(request, form_dict):
        logger.warning("Rejected /browser-call: invalid Twilio signature")
        raise HTTPException(status_code=403, detail="Invalid request signature")

    call_sid = form_dict.get("CallSid", "")
    caller_identity = form_dict.get("From", "web-visitor")

    async with get_db_context() as db:
        result = await db.execute(select(Clinic).where(Clinic.is_demo.is_(True)))
        demo_clinic = result.scalar_one_or_none()
    if not demo_clinic:
        logger.error("No is_demo clinic seeded -- browser widget cannot route this call")
        raise HTTPException(status_code=503, detail="Demo is temporarily unavailable.")

    await _mark_call_validated(call_sid, caller_phone=caller_identity)

    ws_scheme = "wss" if settings.is_production else "ws"
    base_host = settings.app_base_url.split("://", 1)[-1].rstrip("/")
    stream_url = f"{ws_scheme}://{base_host}/media-stream"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{xml_escape(CONSENT_DISCLOSURE)}</Say>
    <Connect>
        <Stream url="{xml_escape(stream_url)}">
            <Parameter name="calledNumber" value="{xml_escape(demo_clinic.twilio_phone_number)}" />
        </Stream>
    </Connect>
</Response>"""

    logger.info(f"Browser demo call {call_sid} from {caller_identity}")
    return Response(content=twiml, media_type="application/xml")
