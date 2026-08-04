# Load Testing

## What the tool tests

`scripts/load_test.py` drives N concurrent WebSocket connections to
`/media-stream` that speak Twilio's Media Streams protocol shape (start /
media / stop events, base64-encoded mulaw frames at real-time cadence).
This exercises:

- WebSocket accept path + the Redis-based `call_sid` validation gate
  (which the script bypasses by pre-seeding the Redis key the way
  `/incoming-call` would, so the WS accept path itself is real)
- N concurrent `CallManager` instances holding real DB sessions and
  spinning up STT/TTS/AI-brain
- DB connection pool saturation
- The full end-of-call teardown → `call_recorder.save_call_transcript` path
- Deepgram STT / ElevenLabs TTS / OpenRouter fan-out under load

## What it does NOT test

- **Voice quality, latency, STT accuracy** — the frames are silence, not
  real speech. Deepgram will return empty transcripts, which won't drive
  the AI brain, which won't drive TTS. Good for the WS lifecycle path,
  useless for the voice pipeline itself.
- **Actual Twilio signaling** — we bypass `/incoming-call` and the Twilio
  signature check.
- **Provider outage behavior** — that's a chaos test, separate scope.
- **Twilio's own concurrent-call limits** — that's a Twilio ceiling, not ours.

## Prod-blocker fuse

The script refuses to run against `*.aliyarsolutions.com` without
`SARAH_LOAD_ALLOW=prod` explicitly set. Verified: a `-n 1 -d 1` shot at
prod is refused with the fuse message. Rationale: even a small burst
consumes real Deepgram/ElevenLabs/OpenRouter credits, and there is no way
to un-spend them.

## Recommended use

Point it at a local docker-compose stack first, then a staging
environment, before ever setting the prod override. When you do want to
run it in staging with real providers, cap concurrency at 5–10 for the
first run to bound cost.

```bash
python3 scripts/load_test.py -n 5 -d 3        # local
SARAH_LOAD_TARGET=wss://sarah-staging... python3 scripts/load_test.py -n 5 -d 3
```

## What to watch for in results

- **`ConnectionRefusedError`** — service isn't listening or ALB target group
  is unhealthy.
- **`ConnectionClosedError` with code 4403** — the Redis validation gate
  rejected the WS. Means the pre-seed didn't run (Redis URL wrong?) or
  expired before the WS opened.
- **DB pool exhaustion under N=15+** — expected on the current
  `db.t4g.medium` sizing (see audit finding on `database_pool_size`); if
  it happens at N<10 that's a bug in a service holding a session too long.
- **Latency p95 climbing linearly with N** — CPU pressure on a single
  Fargate task. Fargate autoscaling should kick in around 70% CPU;
  verify that alarm is firing.

## Findings from initial local runs

None yet — this scaffold is new. First real run should be done against a
staging environment, results appended to this file.

## Related risks (from the security audit)

- The DB pool math (5+10 per container × 6 containers) leaves headroom
  under normal deploy, but has never been stress-tested. This load test
  is the first tool to actually measure it.
- The STT reconnect logic (verified by unit test) has never been
  exercised under real concurrent-call pressure. A cascading Deepgram
  outage while N calls are in flight is a separate chaos test.
