"""
Synthetic concurrent-call load test for /media-stream.

Drives N websocket clients that talk the Twilio Media Streams protocol
shape (start / media / stop events, base64 mulaw payloads), one per
"call". This exercises:

  - websocket accept + validation gates
  - CallManager lifecycle N times in parallel
  - DB pool saturation (a real risk given how many services share the
    pool math on db.t4g.medium)
  - Deepgram STT + ElevenLabs TTS + OpenRouter fan-out
  - end_call teardown + call_recorder persistence

What it does NOT test:
  - real voice quality, latency, or STT accuracy (needs real audio)
  - actual Twilio signaling (the /incoming-call webhook + Redis
    validation pipeline is skipped here; we bypass it by pre-seeding
    the Redis validation flag)
  - graceful degradation under provider outage (that's a chaos test,
    different scope)

Run against your dev environment first, never against production without
setting SARAH_LOAD_TARGET explicitly -- an accidental blast at prod
would consume real Deepgram/ElevenLabs/OpenRouter credits.
"""

import argparse
import asyncio
import base64
import json
import os
import statistics
import time
import uuid
from dataclasses import dataclass, field

import redis.asyncio as redis_lib
import websockets


@dataclass
class CallStats:
    call_sid: str
    connected_at: float | None = None
    first_media_ack_at: float | None = None
    ended_at: float | None = None
    error: str | None = None
    frames_sent: int = 0

    @property
    def total_time_ms(self) -> float | None:
        if self.connected_at and self.ended_at:
            return (self.ended_at - self.connected_at) * 1000
        return None


@dataclass
class LoadTestReport:
    total_calls: int
    successful: int
    failed: int
    durations_ms: list[float] = field(default_factory=list)
    errors: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Attempted: {self.total_calls}",
            f"Succeeded: {self.successful}",
            f"Failed:    {self.failed}",
        ]
        if self.durations_ms:
            d = sorted(self.durations_ms)
            lines += [
                f"Duration p50: {d[len(d)//2]:.0f}ms",
                f"Duration p95: {d[int(len(d)*0.95)]:.0f}ms" if len(d) > 20 else f"Duration max: {max(d):.0f}ms",
                f"Duration avg: {statistics.mean(d):.0f}ms",
            ]
        if self.errors:
            lines.append("Errors:")
            for k, v in self.errors.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


async def _seed_validation(base_ws_url: str, call_sid: str, redis_url: str, ttl: int = 120):
    """Bypass the /incoming-call webhook by writing the validation flag
    directly. Uses the same key format as call_handler._mark_call_validated
    so we exercise the real WS accept path, not a debug bypass."""
    r = redis_lib.from_url(redis_url)
    try:
        await r.set(f"call:pending:{call_sid}", "+15555550100", ex=ttl)
    finally:
        await r.aclose()


async def drive_one_call(base_ws_url: str, call_sid: str, duration_s: float) -> CallStats:
    """Simulate one Twilio media-streams WebSocket for duration_s seconds."""
    stats = CallStats(call_sid=call_sid)
    stream_sid = f"MZ{uuid.uuid4().hex}"
    # 160 bytes = 20ms of mulaw @ 8kHz, the real Twilio frame size.
    silence_frame = base64.b64encode(b"\xff" * 160).decode()

    try:
        async with websockets.connect(f"{base_ws_url}/media-stream") as ws:
            stats.connected_at = time.monotonic()

            # start event -- matches Twilio's shape closely enough for our handler.
            await ws.send(json.dumps({
                "event": "start",
                "start": {
                    "callSid": call_sid,
                    "streamSid": stream_sid,
                    "customParameters": {"calledNumber": "+15555550001"},
                },
            }))

            # Send 20ms-per-frame silence for duration_s. Sleeping the real
            # 20ms would make the whole thing single-threaded from the
            # driver's side; instead we send in small bursts to stay under
            # Twilio's real rate.
            deadline = time.monotonic() + duration_s
            while time.monotonic() < deadline:
                await ws.send(json.dumps({
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": silence_frame},
                }))
                stats.frames_sent += 1
                # Small sleep so we don't spam a full call's worth of audio
                # in a millisecond. 20ms is the natural real-time cadence.
                await asyncio.sleep(0.02)

            await ws.send(json.dumps({"event": "stop", "streamSid": stream_sid}))
            await asyncio.sleep(0.5)  # give the server a moment to teardown gracefully
            stats.ended_at = time.monotonic()
    except Exception as e:
        stats.error = f"{type(e).__name__}: {e}"

    return stats


async def run_load_test(
    base_ws_url: str, redis_url: str, concurrency: int, duration_s: float
) -> LoadTestReport:
    # Pre-seed all call validations before opening any sockets, so the WS
    # accept isn't racing against Redis.
    call_sids = [f"CAload{uuid.uuid4().hex}" for _ in range(concurrency)]
    await asyncio.gather(*[_seed_validation(base_ws_url, sid, redis_url) for sid in call_sids])

    results = await asyncio.gather(
        *[drive_one_call(base_ws_url, sid, duration_s) for sid in call_sids]
    )

    report = LoadTestReport(total_calls=concurrency, successful=0, failed=0)
    for r in results:
        if r.error:
            report.failed += 1
            key = r.error.split(":")[0]
            report.errors[key] = report.errors.get(key, 0) + 1
        else:
            report.successful += 1
            if r.total_time_ms is not None:
                report.durations_ms.append(r.total_time_ms)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=os.environ.get("SARAH_LOAD_TARGET", "ws://localhost:8000"),
                    help="Base WS URL (e.g. ws://localhost:8000, wss://sarah-staging.example)")
    ap.add_argument("--redis", default=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    ap.add_argument("-n", "--concurrency", type=int, default=5)
    ap.add_argument("-d", "--duration", type=float, default=2.0, help="seconds per call")
    args = ap.parse_args()

    # Explicit fuse: never run against prod without an explicit env var. A
    # burst of even 10 fake calls against prod would consume real
    # Deepgram/ElevenLabs/OpenRouter credits.
    if "aliyarsolutions.com" in args.target and "prod" not in os.environ.get("SARAH_LOAD_ALLOW", ""):
        raise SystemExit(
            "Refusing to load test against a *.aliyarsolutions.com target -- "
            "set SARAH_LOAD_ALLOW=prod to override. This spends real API credits."
        )

    print(f"Load test → {args.target}  n={args.concurrency}  duration={args.duration}s")
    report = asyncio.run(run_load_test(args.target, args.redis, args.concurrency, args.duration))
    print()
    print(report.summary())


if __name__ == "__main__":
    main()
