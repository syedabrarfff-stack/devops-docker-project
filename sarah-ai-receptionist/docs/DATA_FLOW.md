# Personal-Data Flow

Factual map of where a caller's personal data (voice, transcript text,
name, phone number, described symptoms) travels and is stored, end to end.

**This document makes no compliance claim of any kind — Saudi PDPL, HIPAA,
GDPR, or otherwise.** It exists so that claim can be evaluated by someone
qualified to make it (legal counsel), against what the system actually
does rather than what it's assumed to do. Nothing here should be presented
to a customer, regulator, or auditor as a certification. `docs/COMPLIANCE.md`
covers specific HIPAA-audit-response items already closed in the US
architecture; this document is broader and is not a compliance document.

All infrastructure below runs in AWS `us-east-1` unless stated otherwise.
See "Region" section at the end for why this hasn't changed for the Saudi
go-to-market.

---

## 1. A call comes in

**Path:** Caller's phone → the clinic's own carrier network (unchanged by
Sarah) → forwarded (call-forwarding, configured by the clinic with their
own carrier) or dialed directly to a Twilio-held number → Twilio → Sarah's
`/incoming-call` webhook (ECS `voice-service`, `us-east-1`).

- **Twilio** (US-headquartered, global telephony infrastructure) receives
  and switches the raw call. Twilio sees the caller's phone number (caller
  ID) and the call's audio.
- The webhook payload (caller number, called number, Twilio `CallSid`) is
  signature-verified (`_validate_twilio_request`) before Sarah acts on it.
- The called Twilio number is looked up against `clinics.twilio_phone_number`
  in RDS Postgres (`us-east-1`) to resolve which clinic this call belongs to
  and load that clinic's configuration (hours, services, transfer number).

## 2. Live audio during the call

**Path:** Twilio opens a WebSocket (`/media-stream`) to `voice-service` and
streams the caller's raw audio (mulaw/8kHz) in both directions for the
duration of the call.

- Sarah's system unconditionally speaks a recording/transcription consent
  disclosure before the media stream connects (`CONSENT_DISCLOSURE` in
  `call_handler.py`) — every call that reaches persistence has had it played.
- The caller's audio is forwarded in real time to **Deepgram** (STT,
  third-party, US) over a separate WebSocket for live transcription. Deepgram
  receives the raw voice audio and returns text.
- The resulting transcript text (which can include the caller's spoken
  name, phone number, and described symptoms) is sent to **OpenRouter**
  (third-party model routing API), which forwards it on to whichever
  underlying model is configured:
  - Main conversation: `anthropic/claude-sonnet-4-6` (Anthropic)
  - Fast-path replies: `anthropic/claude-haiku-4-5-20251001` (Anthropic)
  - Post-call summary (see §4): `google/gemini-flash-1.5` (Google) — a
    **different** third party than the live conversation model.
- Sarah's generated response text is sent to **ElevenLabs** (TTS,
  third-party, US) for speech synthesis; the returned audio is streamed
  back to the caller via Twilio.
- The full raw call audio is buffered in the `voice-service` process for
  the duration of the call, for the recording upload in §3.

**Third parties that see live call content, per call:** Twilio, Deepgram,
OpenRouter, Anthropic (and/or Google for the summary pass), ElevenLabs, all
outside Aliyar Solutions' own AWS account.

## 3. What gets written to disk after the call ends

On call end (`save_call_transcript` in `call_recorder.py`):

- **RDS Postgres** (`us-east-1`, KMS-encrypted at rest, `storage_encrypted=true`,
  `deletion_protection=true`):
  - `call_logs`: full transcript (every caller/Sarah turn), caller phone
    number, call duration, outcome, transfer result, S3 recording key.
  - `patients`: name, phone number, new/existing-patient flag — created or
    matched on the caller's phone number.
  - `appointments`: service, patient name/phone, appointment time, provider,
    linked back to the call.
- **S3** (`sarah-receptionist-prod-recordings` bucket, `us-east-1`,
  `ServerSideEncryption: aws:kms`): the full call audio, uploaded as a WAV
  file keyed `recordings/{clinic_id}/{call_sid}.wav` — namespaced per
  clinic, never a public object.
- **Redis (ElastiCache, `us-east-1`)**: transient only — the pre-call
  signature-validation handshake (TTL 120s), rate-limit counters, and the
  Arq background-job queue. Not a store of call content; nothing here
  outlives its TTL or the job that consumes it.

## 4. Post-call AI summary

The call transcript (already containing PII) is queued to an Arq
background job (`summarize_call` in `workers/tasks.py`), which sends the
full transcript text to **OpenRouter → Google (`gemini-flash-1.5`)** to
generate a one-sentence dashboard summary. This is a second, separate
third-party model provider from the one used during the live call — the
transcript leaves Aliyar's infrastructure twice, to two different
companies, for two different purposes.

## 5. SMS notifications

Booking confirmations, reschedule/cancellation confirmations, appointment
reminders, and urgent-escalation alerts are sent via **Twilio's SMS API**.
These messages contain the patient's name, appointment time, and service —
not the full transcript, but identifying information. Escalation SMS to
clinic on-call staff also includes the caller's last spoken turn (up to
400 characters), which can include described symptoms.

## 6. Who can see stored data, and what's logged about that

- Clinic dashboard staff (JWT-authenticated, `clinic_id`-scoped — see
  `dashboard.py`) can view call lists, individual call transcripts, and
  play back recordings via a short-lived (300-second) presigned S3 URL —
  recordings are never served as a public link.
- Every transcript view and every recording playback is written to
  `audit_log` (`write_audit_log`): who accessed it, from what IP, when.
  Platform admin (Aliyar) actions (onboarding, clinic config changes) are
  audited the same way.
- Application logs (CloudWatch, `us-east-1`, 30-day retention on the
  relevant log groups) redact phone numbers and emails before writing
  (`app/core/redact.py`) — a log line never carries a full phone number or
  email, only a masked form (`+1***4567`).

## 7. Retention and deletion

- `call_transcript_retention_days` (`Settings`, default 365, overridable
  per clinic contract) governs a periodic Arq job
  (`enforce_call_retention` in `workers/tasks.py`): calls older than the
  window have `transcript`, `ai_summary`, and `recording_s3_key` cleared.
  The `call_logs` row itself (outcome, timing, duration, latency stats) is
  kept afterward for aggregate reporting — it no longer carries PHI/PII
  once redacted.
- Confirmed registered as an actual scheduled job, not just present in
  code: `cron(enforce_call_retention, hour=3, minute=0)` in
  `app/workers/worker.py`, running daily on the `worker-service` ECS task.
- RDS automated backups (7-day, per `docs/COMPLIANCE.md`-adjacent infra)
  and the AWS Backup cross-region copy (35-day retention, `us-west-2`) both
  retain point-in-time copies of the database independent of the
  application-level redaction job above — a restored backup from before a
  redaction would still contain the pre-redaction data. This is a normal
  backup/retention interaction, not a bug, but it means "retention
  window" and "how long a specific patient's data could theoretically
  still exist somewhere" are two different numbers.

## 8. Region

All primary infrastructure is `us-east-1` (with DR backup copies in
`us-west-2`). This was **not changed** for the Saudi go-to-market, per
explicit instruction to keep the current region absent a demonstrated
technical or regulatory reason to move it. No such reason has been
identified or evaluated in this pass — that evaluation (data-localization
requirements under Saudi PDPL, latency, or otherwise) is a legal/regulatory
question, not an engineering one, and is explicitly out of scope for this
document per the same instruction.

---

## Summary table — who/what touches raw call content

| Stage | System | Location | Sees |
|---|---|---|---|
| Call signaling | Twilio | External (US) | Caller number, call metadata |
| Live transcription | Deepgram | External (US) | Raw voice audio |
| Conversation AI | OpenRouter → Anthropic | External (US) | Transcript text, PII spoken by caller |
| Post-call summary | OpenRouter → Google | External (US) | Full transcript text |
| Speech synthesis | ElevenLabs | External (US) | Sarah's response text |
| SMS | Twilio | External (US) | Patient name, phone, appointment details |
| Transcript/PII storage | RDS Postgres | AWS `us-east-1` | Full transcript, patient record, appointments |
| Recording storage | S3 | AWS `us-east-1` | Full call audio |
| Transient state | ElastiCache Redis | AWS `us-east-1` | Call-validation handshake, rate limits, job queue |
| Application logs | CloudWatch | AWS `us-east-1` | Redacted (masked phone/email only) |

## Change log

- 2026-08-10: Initial version, written as part of Saudi go-to-market
  production-readiness review. No compliance claim made or implied.
