"""
Twilio webhook + WebSocket handler — entry point for every phone call.
"""

import asyncio
import json
import logging
from xml.sax.saxutils import escape as xml_escape

import redis.asyncio as redis_lib
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy import select
from twilio.request_validator import RequestValidator

from app.config.settings import get_settings
from app.core.database import get_db_context
from app.models.clinic import Clinic
from app.services.call_manager import CallManager
from app.services.call_recorder import save_call_transcript

logger = logging.getLogger(__name__)
router = APIRouter(tags=["calls"])
settings = get_settings()

_active_calls: dict[str, CallManager] = {}

# Callers must be told a call may be recorded before Sarah starts talking —
# several US states require affirmative consent before recording begins.
CONSENT_DISCLOSURE = (
    "This call may be recorded and transcribed for quality, training, and "
    "appointment-booking purposes."
)

_PENDING_CALL_TTL_SECONDS = 120


def _redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.redis_url)


async def _mark_call_validated(call_sid: str, caller_phone: str | None = None) -> None:
    """Records that this call_sid passed Twilio signature validation on /incoming-call,
    so the WebSocket handler can confirm the stream that follows is legitimate."""
    r = _redis()
    try:
        await r.set(f"call:pending:{call_sid}", caller_phone or "unknown", ex=_PENDING_CALL_TTL_SECONDS)
    finally:
        await r.aclose()


async def _consume_call_validation(call_sid: str) -> str | None:
    """Atomically checks and clears the validated flag. Returns None for any
    call_sid that didn't go through the validated webhook (or is being replayed);
    otherwise returns the caller's phone number."""
    if not call_sid:
        return None
    r = _redis()
    try:
        pipe = r.pipeline()
        await pipe.get(f"call:pending:{call_sid}")
        await pipe.delete(f"call:pending:{call_sid}")
        results = await pipe.execute()
        caller_phone = results[0]
        deleted = results[1]
        if not deleted:
            return None
        return caller_phone.decode() if isinstance(caller_phone, bytes) else caller_phone
    finally:
        await r.aclose()


def _validate_twilio_request(request: Request, form: dict) -> bool:
    validator = RequestValidator(settings.twilio_auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    # Twilio signs the public webhook URL it was configured with — never the
    # raw Host header, which a client can spoof to redirect the audio stream.
    url = f"{settings.app_base_url.rstrip('/')}{request.url.path}"
    return validator.validate(url, form, signature)


@router.post("/incoming-call")
async def incoming_call(request: Request):
    """Twilio hits this webhook when a call comes in. Returns TwiML to open a media stream."""
    form = await request.form()
    form_dict = dict(form)

    if not _validate_twilio_request(request, form_dict):
        logger.warning("Rejected /incoming-call: invalid Twilio signature")
        raise HTTPException(status_code=403, detail="Invalid request signature")

    to_number = form_dict.get("To", "")
    from_number = form_dict.get("From", "")
    call_sid = form_dict.get("CallSid", "")

    await _mark_call_validated(call_sid, caller_phone=from_number)

    ws_scheme = "wss" if settings.is_production else "ws"
    base_host = settings.app_base_url.split("://", 1)[-1].rstrip("/")
    stream_url = f"{ws_scheme}://{base_host}/media-stream"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{xml_escape(CONSENT_DISCLOSURE)}</Say>
    <Connect>
        <Stream url="{xml_escape(stream_url)}">
            <Parameter name="calledNumber" value="{xml_escape(to_number)}" />
        </Stream>
    </Connect>
</Response>"""

    logger.info(f"Incoming call {call_sid} to {to_number}")
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Twilio's bidirectional audio WebSocket. One connection per call.

    Only accepts streams whose call_sid was validated by a genuine, signature-checked
    /incoming-call webhook — this is what stops an attacker from opening the socket
    directly and driving any clinic's AI/voice pipeline for free.
    """
    await websocket.accept()

    call_manager: CallManager | None = None
    call_sid: str | None = None
    called_number: str | None = None
    caller_phone: str | None = None
    clinic_config: dict | None = None
    call_task: asyncio.Task | None = None

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                start_data = data.get("start", {})
                call_sid = start_data.get("callSid")
                stream_sid = start_data.get("streamSid")
                custom_params = start_data.get("customParameters", {})
                called_number = custom_params.get("calledNumber")

                caller_phone = await _consume_call_validation(call_sid)
                if caller_phone is None:
                    logger.warning(f"Rejected /media-stream: unvalidated call_sid {call_sid}")
                    await websocket.close(code=4403)
                    return

                clinic_config = await _load_clinic_config(called_number)

                call_manager = CallManager(call_sid, stream_sid, clinic_config)
                _active_calls[call_sid] = call_manager

                call_task = asyncio.create_task(_run_call(call_manager, websocket))

            elif call_manager:
                await call_manager.handle_twilio_message(message)
                if not call_manager.is_active:
                    break

    except WebSocketDisconnect:
        logger.info(f"Twilio WebSocket disconnected for call {call_sid}")
    finally:
        if call_manager and call_sid:
            # If the call ends before call_manager.start()'s own setup (STT
            # connect + greeting) has finished, that background task must be
            # cancelled here — otherwise it keeps running after end_call()
            # has already torn down the STT/TTS clients and closed the
            # websocket, and ends up erroring against already-closed
            # resources (confirmed by a real fast-hangup test).
            if call_task and not call_task.done():
                call_task.cancel()
                try:
                    await call_task
                except (asyncio.CancelledError, Exception):
                    pass
            result = await call_manager.end_call()
            result["caller_phone"] = caller_phone
            await save_call_transcript(call_sid, clinic_config, result)
            _active_calls.pop(call_sid, None)


async def _run_call(call_manager: CallManager, websocket: WebSocket):
    try:
        await call_manager.start(websocket)
    except Exception as e:
        logger.error(f"Call loop crashed: {e}")
    finally:
        if call_manager.is_active:
            call_manager.is_active = False


async def _load_clinic_config(twilio_number: str | None) -> dict | None:
    if not twilio_number:
        return None
    async with get_db_context() as db:
        result = await db.execute(select(Clinic).where(Clinic.twilio_phone_number == twilio_number))
        clinic = result.scalar_one_or_none()
        if not clinic:
            logger.warning(f"No clinic found for Twilio number {twilio_number}")
            return None
        config = dict(clinic.clinic_config or {})
        config["name"] = clinic.name
        config["sarah_name"] = clinic.sarah_name
        config["_clinic_id"] = clinic.id
        # Booking and SMS confirmation both resolve caller-spoken times against
        # this — without it they'd fall back to UTC and be hours off.
        config["_timezone"] = clinic.timezone
        return config
