"""Browser-based "Call Sarah" widget.

Three endpoints:
  WS   /demo-stream    -- the live path. Raw PCM16 in, PCM16 out, over a
                           plain WebSocket, driving the real STT/AI/TTS
                           pipeline directly (see demo_call_manager.py).
                           No Twilio involved at all, so it works even
                           while the Twilio account is still on Trial, and
                           needs nothing but this container running --
                           no RDS, no Redis, no S3.
  POST /token           -- Twilio Voice SDK (WebRTC) path, kept for when
                           Twilio is fully activated and a TwiML App/API
                           Key exist. Mints a short-lived Access Token.
  POST /browser-call     -- Twilio's Voice Request URL for the TwiML
                           Application the token above is scoped to. Always
                           routes into the seeded is_demo clinic since a
                           WebRTC call has no real "To" number to look up.
"""

import logging
import time
import uuid
from collections import defaultdict
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, HTTPException, Request, WebSocket
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

from app.config.settings import get_settings
from app.core.database import get_db_context
from app.core.redis import get_redis_client
from app.models.clinic import Clinic
from app.routes.call_handler import (
    CONSENT_DISCLOSURE,
    _mark_call_validated,
    _validate_twilio_request,
)
from app.services.demo_call_manager import DEMO_CLINIC_CONFIG, DemoCallManager

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
    r = get_redis_client()
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


# ── /demo-stream: the no-Twilio, no-infra-dependency path ──────────────────
#
# In-memory, not Redis-backed: this endpoint's whole point is to run on a
# single lightweight container with nothing else behind it. A per-process
# limiter is not correct across multiple replicas (each container gets its
# own budget), but for a low-traffic marketing demo running on one task,
# that's a fine trade against not needing Redis at all. If this ever runs
# on N>1 replicas, move these back to Redis the same way _check_widget_rate_limit
# does above.
_DEMO_MAX_CONCURRENT_CALLS = 5
_DEMO_RATE_LIMIT_MAX_PER_HOUR = 10
_DEMO_RATE_LIMIT_WINDOW_SECONDS = 3600

_demo_active_calls = 0
_demo_ip_attempts: dict[str, list[float]] = defaultdict(list)


def _demo_rate_limit_ok(client_ip: str) -> bool:
    now = time.monotonic()
    attempts = _demo_ip_attempts[client_ip]
    attempts[:] = [t for t in attempts if now - t < _DEMO_RATE_LIMIT_WINDOW_SECONDS]
    if len(attempts) >= _DEMO_RATE_LIMIT_MAX_PER_HOUR:
        return False
    attempts.append(now)
    return True


@router.websocket("/demo-stream")
async def demo_stream(websocket: WebSocket):
    """The live "Call Sarah" demo. Accepts raw PCM16/16kHz mic frames as
    binary WebSocket messages, streams JSON transcript/action events and
    binary PCM16/16kHz Sarah-speech frames back."""
    global _demo_active_calls

    client_ip = websocket.client.host if websocket.client else "unknown"
    if not _demo_rate_limit_ok(client_ip):
        await websocket.close(code=4429, reason="Too many demo calls from this network. Try again later.")
        return

    if _demo_active_calls >= _DEMO_MAX_CONCURRENT_CALLS:
        await websocket.close(code=4503, reason="Sarah is at capacity for live demos right now. Try again shortly.")
        return

    await websocket.accept()
    _demo_active_calls += 1
    session_id = uuid.uuid4().hex[:12]
    logger.info(f"Demo call {session_id} started from {client_ip} ({_demo_active_calls} active)")

    manager = DemoCallManager(clinic_config=DEMO_CLINIC_CONFIG, session_id=session_id)
    try:
        await manager.run(websocket)
    except Exception as e:
        logger.error(f"Demo call {session_id} crashed: {e}")
    finally:
        _demo_active_calls -= 1
        logger.info(f"Demo call {session_id} ended ({_demo_active_calls} active)")
