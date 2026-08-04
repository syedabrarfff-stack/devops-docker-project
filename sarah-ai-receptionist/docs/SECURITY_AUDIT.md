# Security & PHI Audit — Sarah AI Receptionist

**Auditor:** Claude Code session
**Date:** 2026-08-03
**Scope:** Full backend + frontend + infra, from HIPAA + operational-risk lens
**Tool assist:** `bandit -r app -ll` (5 low, 1 medium, 0 high), plus manual read
**Method:** Direct code read (not just static analysis), focused on data-flow
paths that touch PHI, third-party subprocessors, and secret material.

---

## Executive summary

The product is meaningfully better than most first-version voice-AI systems on
security posture — consent disclosure hardcoded before recording, KMS at rest,
HIPAA audit logging wired into every PHI-touching route, refresh-token
rotation, HttpOnly cookies with per-endpoint scope. The three findings below
are real gaps that a serious HIPAA review would raise, ordered by severity.

**No high-severity issues found in code.** The dominant risks are (a)
subprocessor contract status you as CEO have to sign for, and (b) PHI leaking
into CloudWatch through log lines. One of those (PHI in logs) is fixed in this
same commit; the rest are documented for you to action.

---

## 🔴 High-priority (contract, not code)

### F1 — No Business Associate Agreements (BAAs) visible for any subprocessor

Every call routes patient audio through **Twilio → Deepgram → OpenRouter →
ElevenLabs → S3**. All four are handling PHI (voice + transcripts) for a US
dental practice, which makes them Business Associates under HIPAA. A HIPAA
covered entity **cannot lawfully use them without a signed BAA**.

I found **no record of a BAA with any of them** in the repo (checked
`docs/`, `README.md`, comments across all services). The following need to
be in place before onboarding a real US clinic:

| Subprocessor | BAA status you need to verify |
|---|---|
| **Twilio** | Requires a BAA request through their compliance portal (self-serve for enterprise; free-tier accounts often can't) |
| **Deepgram** | BAA available on their Growth+ plan and above; not on free/starter |
| **ElevenLabs** | **Uncertain** — check their compliance page or ask sales |
| **OpenRouter** | Aggregator, complicates BAA — Anthropic (Claude) signs BAAs directly; OpenRouter probably doesn't. |
| **AWS** | Signed BAA covers RDS, S3, ECS, ElastiCache, CloudWatch when configured for HIPAA-eligible services |

**Action:** Get the BAAs before the first real patient call. For OpenRouter
specifically — you may need to switch that path to call Anthropic's API
directly to get a signed BAA. That's a config-only change (`ai_brain.py`
constructs the URL), not a rewrite.

**Priority:** Blocking real onboarding.

---

## 🟠 Medium-priority (code)

### F2 — PHI (phone numbers, caller utterances) logged verbatim to CloudWatch

Multiple log lines emit patient PHI into log output that then persists in
CloudWatch Logs. Examples found:

```
backend/app/services/notification_service.py:29,54,83,99
  logger.error(f"Failed to send SMS to {to_phone}: {e}")

backend/app/services/call_manager.py:154
  logger.info(f"[{self.call_sid}] Caller: {transcript}")
```

The full transcript is already stored, KMS-encrypted, in `call_logs.transcript`
with every access audit-logged. Duplicating it into CloudWatch — which has
different access controls, potentially longer retention, and no audit trail
by default — defeats those protections.

**Status:** Fixed in this same commit. `app/core/redact.py` gives one
obvious way to log identifiers safely (`redact_phone("+15551234567")` →
`"+1***4567"`). `notification_service.py` and `call_manager.py`'s Caller log
line updated to use it. Other services still log `call_sid`, which is a
Twilio identifier — sensitive but not PHI. Left as-is.

**Residual gap:** Nothing enforces this at the linter level. Future code
that logs a raw phone will silently regress. A future improvement is a
custom ruff rule or a logging formatter that catches phone-shaped strings —
not done here, worth queuing.

### F3 — Raw Twilio API error messages returned to admin clients

In `admin.py` (port-requests routes), Twilio API errors surface to the HTTP
response body verbatim:

```python
raise HTTPException(status_code=400, detail=str(e))
```

The Twilio API sometimes includes account-scoped identifiers (SIDs,
partial numbers) in its error bodies. Passing them to whoever hit the
endpoint leaks that beyond the log surface. Not a huge risk given the
endpoint requires `platform_admin` role, but still not ideal.

**Action:** Return a safe generic message; keep the raw error in the
server-side log with the request ID from the observability middleware.
Half a day of work, mostly straightforward. Not fixed in this commit
because the surface is small (3 admin-only routes) and the fix wants
consistency across the whole app.

**Priority:** Fix before opening the admin console to anyone other than
you.

---

## 🟡 Low-priority (defense in depth)

### F4 — Refresh-token cookie is `SameSite=None` in production

The cookie needs to be sent from `app.aliyarsolutions.com` and
`admin.aliyarsolutions.com` to `sarah.aliyarsolutions.com`, which are
different subdomains and therefore require `SameSite=None`. That's paired
with `Secure` + `HttpOnly` + explicit `.aliyarsolutions.com` domain scope,
so it never travels cross-site — but a strict CSRF review would still flag
`SameSite=None` as worth documenting. **This is a correct trade-off, not
a bug**, but it deserves a written justification in a compliance review.

### F5 — Bandit medium: `app_host = "0.0.0.0"`

Standard container default (listens on all interfaces). Behind ALB with a
private VPC subnet, this is correct — the internet cannot reach the
container directly. False positive from bandit's default rule; leaving as-is.

### F6 — No automated password rotation for the app admin user

The `platform_admin` user is created once via `create_platform_admin.py`
and never expires. For a system with 1 admin (you), acceptable. As soon
as there's a second human, you want rotation policy + a re-auth-for-sensitive
endpoints pattern (like Stripe uses).

### F7 — Recordings bucket has no MFA-delete or Object Lock

S3 recordings are KMS-encrypted, but the bucket policy does not require
MFA to delete an object, nor is Object Lock configured. A compromised AWS
key could destroy call recordings during their retention window without an
extra factor. Considered defense-in-depth; standard for MVP, worth
revisiting for a HIPAA audit.

---

## ✅ Notable strengths (worth calling out)

- **Consent disclosure is hardcoded, not configurable**, in `call_handler.py`:
  every call plays it before recording starts, `consent_disclosed=True` is
  persisted on every `CallLog`. This is exactly right.
- **Audit logging is real**, not scaffolding — `services/audit.py` is
  actually wired into every PHI-touching route (call detail view, recording
  URL, patient erase, etc.).
- **Refresh-token model is genuinely modern**: opaque token stored server-
  side as SHA-256 hash, one-shot rotation on use, revocable, `HttpOnly Secure`
  cookie, short-lived JWT for the access token. That's better than most
  early-stage SaaS I've seen.
- **Login timing side-channel closed** (`_DUMMY_HASH` runs on the not-found
  path to equalize bcrypt cost).
- **Patient right-to-erasure is implemented, not just a TODO** — `erase_patient`
  in admin.py actually redacts the patient's identifiers out of appointment
  rows and call transcripts, not just deletes the row.
- **Twilio webhook signature validation** on `/incoming-call` and
  `/transfer-status` — no way to spoof a call into the system.
- **Multi-tenant scoping via `clinic_id` on every query** — I could not find
  a data-access path that reads across clinics.
- **Secrets never in code** — every credential comes from AWS Secrets Manager
  in the deployed task defs. `.env` is gitignored.

---

## Prioritized punch list

1. **Get BAAs** with Twilio, Deepgram, ElevenLabs, and AWS (or route Claude
   directly through Anthropic's API and get their BAA). **Do before first
   real patient call.**
2. **Add safe error responses** for the port-request admin routes (F3).
3. **Fix the S3 bucket** to require MFA-delete + enable Object Lock for the
   configured retention window (F7). Terraform change, small.
4. **Add a logging lint rule** or formatter to prevent future PHI-in-logs
   regressions (F2 residual).
5. **Document the SameSite=None trade-off** in this file or a compliance
   folder (F4) — needed for any future audit reviewer.

---

## What was fixed in this same commit
- `redact_phone()` / `redact_email()` helpers added to `app/core/redact.py`.
- `notification_service.py` — all four SMS-failure log lines updated.
- `call_manager.py` — Caller utterance log line now stores length + short
  preview instead of the whole utterance.

## What was NOT fixed (deferred)
- F5 (bandit 0.0.0.0 bind) — verified false positive, `# nosec B104`
  applied on the settings line with a reference to this file.
- F6 (admin password rotation) — deferred until there is a second admin
  human; not needed while the platform_admin count is 1.
- Custom lint rule for future PHI-in-logs — nice-to-have, not blocking.

## Closed in follow-up work
- **F3 — raw exception bodies to admin clients:** the three port-request
  admin routes (`submit`, `refresh`, `cancel`) now return a generic
  `"Port <action> failed. Reference id: <request_id>"` to the HTTP
  client; the raw Twilio error is written to the server log with the
  same `request_id`. Operator lookup is via `req=<id>` in the log stream.
- **F4 — SameSite=None justification:** written up in
  `docs/COMPLIANCE.md#f4`. Confirms the cross-subdomain requirement,
  documents the CSRF mitigation stack (Domain-scoped cookie +
  SHA-256-hashed opaque refresh token + one-shot rotation).
- **F7 — S3 MFA-delete + Object Lock:** operational procedure written up
  in `docs/COMPLIANCE.md#f7` with the exact CLI to run under the root
  account (MFA-delete can only be enabled by root; terraform cannot).
  Terraform path to add Object Lock to new buckets is described; not
  applied to the existing bucket because Object Lock is a
  bucket-creation-time-only flag and enabling it would force a bucket
  replacement, destroying existing recordings.
