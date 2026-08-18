# Compliance Reference

Written justifications for the security choices a HIPAA auditor is likely to
question. Closes the deferred items from `docs/SECURITY_AUDIT.md`.

---

## F4 — Refresh-token cookie: `SameSite=None`

**Setting:** `Set-Cookie: sarah_refresh=<opaque>; HttpOnly; Secure; SameSite=None; Domain=.aliyarsolutions.com; Path=/auth`

**Why it is not `Lax` or `Strict`:**

The clinic dashboard (`app.aliyarsolutions.com`) and the internal admin
console (`admin.aliyarsolutions.com`) both need to call the token-refresh
endpoint at `sarah.aliyarsolutions.com/auth/refresh`. Browsers treat that
as a cross-site request because the eTLD+1 hostname differs from the page
origin. `SameSite=Lax` would drop the cookie on any XHR / fetch to a
sibling subdomain; `SameSite=Strict` would drop it even on top-level
navigations. Both would break refresh.

**Why the risk this normally carries doesn't apply here:**

The classic argument against `SameSite=None` is that a third-party site
can make a state-changing request with the user's cookie attached (CSRF).
That is closed here by two independently sufficient controls:

1. `Domain=.aliyarsolutions.com` scopes the cookie to Aliyar-owned
   subdomains only. A page hosted on `attacker.com` cannot ever cause the
   browser to attach this cookie to a request — the `Domain` attribute
   controls the origin the cookie is sent from, not the origin that reads
   it. Any request from `attacker.com` to `sarah.aliyarsolutions.com`
   arrives without the cookie regardless of `SameSite`.
2. The refresh endpoint accepts only opaque tokens whose SHA-256 hash
   matches a server-side entry that is single-use and rotated on every
   use (see `app/services/refresh_tokens.py`). Even if the token
   somehow leaked, replay is bounded to one call.

**Additional hardening in place:** `HttpOnly` blocks JS access;
`Secure` forces TLS transport; the JWT access token is short-lived
(15 min) and is issued fresh on refresh.

**Auditor's summary line:** *SameSite=None is required for the
cross-subdomain refresh flow. CSRF is mitigated by the Domain-scoped
cookie, the SHA-256-hashed opaque refresh token stored server-side, and
one-shot rotation on use.*

---

## F7 — S3 recordings bucket: MFA-delete and Object Lock

The audit flagged the recordings bucket for two additional controls beyond
KMS encryption + versioning + `DenyInsecureTransport`:

- **MFA-delete** — requires a user to provide an MFA code to delete any
  object version or to permanently delete the bucket.
- **Object Lock (WORM)** — makes objects immutable for a configured
  retention window; even a root user cannot delete them within that window.

### Why these are not applied in terraform

Both controls have operational constraints that terraform cannot satisfy:

1. **MFA-delete can only be enabled by the AWS *root* account via the
   AWS CLI, not via terraform, IAM users, or the console.** This is an
   AWS-side hard requirement, not a project limitation. If terraform
   tries to set `mfa_delete = "Enabled"`, the apply fails with
   `MalformedXML` because the API needs the root-user's serial number
   and current MFA code in the request headers.
2. **Object Lock can only be enabled at bucket-creation time.** The
   existing `sarah-receptionist-prod-recordings` bucket predates this
   change; adding `object_lock_enabled = true` to the existing
   `aws_s3_bucket.recordings` resource would force a bucket
   replacement — which would destroy every recording currently in it.

### Operational procedure to close F7

To be executed by Captain (root-account holder) once real patient
recordings are on the line:

**Step 1 — Enable MFA-delete (5 minutes, requires root credentials):**

```bash
# From a shell with root-account credentials (NOT the app IAM user)
aws s3api put-bucket-versioning \
  --bucket sarah-receptionist-prod-recordings \
  --versioning-configuration Status=Enabled,MFADelete=Enabled \
  --mfa "arn:aws:iam::<ACCOUNT_ID>:mfa/root-account-mfa-device <MFA_CODE>"
```

The last argument is the root user's MFA device ARN followed by a space
and the current 6-digit TOTP code. Once enabled, MFA-delete cannot be
disabled without another root-authenticated call.

**Step 2 — Add Object Lock to future buckets (terraform, ready when needed):**

The `storage` module can be extended with an `enable_object_lock`
variable defaulting to `false`. For any *new* bucket (e.g. a
per-clinic bucket or a cold-archive bucket) set the variable to `true`
to provision it with a WORM retention window. Migrating the existing
bucket requires a create-new + `aws s3 sync` + swap dance and is a
separate change-management ticket.

**Retention window recommendation:** 7 years to align with HIPAA's
retention requirement for records of PHI disclosure, in `GOVERNANCE`
mode (allows admin override with logging) rather than `COMPLIANCE`
mode (nobody can override, including root).

---

## Change log

- 2026-08-04: F4 and F7 written up. F3 (safe error responses on
  port-request admin routes) closed in code — see
  `app/routes/admin.py` handlers on the port-request paths.
