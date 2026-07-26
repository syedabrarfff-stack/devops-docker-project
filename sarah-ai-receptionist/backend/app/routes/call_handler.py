"""
Twilio webhook + WebSocket handler — entry point for every phone call.
"""

import logging
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy import select
from app.core.database import get_db_context
from app.models.clinic import Clinic
from app.models.call_log import CallLog
from app.services.call_manager import CallManager
from app.services.call_recorder import save_call_transcript
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["calls"])
settings = get_settings()

_active_calls: dict[str, CallManager] = {}


@router.post("/incoming-call")
async def incoming_call(request: Request):
    """Twilio hits this webhook when a call comes in. Returns TwiML to open a media stream."""
    form = await request.form()
    to_number = form.get("To", "")
    call_sid = form.get("CallSid", "")

    ws_scheme = "wss" if settings.is_production else "ws"
    host = request.headers.get("host", request.url.hostname)
    stream_url = f"{ws_scheme}://{host}/media-stream"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{stream_url}">
            <Parameter name="calledNumber" value="{to_number}" />
        </Stream>
    </Connect>
</Response>"""

    logger.info(f"Incoming call {call_sid} to {to_number}")
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Twilio's bidirectional audio WebSocket. One connection per call."""
    await websocket.accept()

    call_manager: CallManager | None = None
    call_sid: str | None = None
    called_number: str | None = None

    try:
        while True:
            message = await websocket.receive_text()
            import json
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                start_data = data.get("start", {})
                call_sid = start_data.get("callSid")
                stream_sid = start_data.get("streamSid")
                custom_params = start_data.get("customParameters", {})
                called_number = custom_params.get("calledNumber")

                clinic_config = await _load_clinic_config(called_number)

                call_manager = CallManager(call_sid, stream_sid, clinic_config)
                _active_calls[call_sid] = call_manager

                import asyncio
                asyncio.create_task(_run_call(call_manager, websocket, called_number))

            elif call_manager:
                await call_manager.handle_twilio_message(message)
                if not call_manager.is_active:
                    break

    except WebSocketDisconnect:
        logger.info(f"Twilio WebSocket disconnected for call {call_sid}")
    finally:
        if call_manager and call_sid:
            result = await call_manager.end_call()
            await save_call_transcript(call_sid, called_number, result)
            _active_calls.pop(call_sid, None)


async def _run_call(call_manager: CallManager, websocket: WebSocket, called_number: str | None):
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
        return config
