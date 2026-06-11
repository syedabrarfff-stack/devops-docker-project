from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.communication.client_language import sanitize_client_text, sanitize_subject_body

logger = logging.getLogger(__name__)
AWS_CLIENT_CONFIG = Config(
    connect_timeout=1,
    read_timeout=2,
    retries={"max_attempts": 1},
)


@dataclass(frozen=True)
class ExecutiveIdentity:
    name: str
    title: str
    email: str

    @property
    def display_name(self) -> str:
        return f"{self.name} - {self.title}".strip(" -")


def get_executive_identity() -> ExecutiveIdentity:
    email = (settings.SES_FROM_EMAIL or settings.EXECUTIVE_EMAIL_ADDRESS or "").strip()
    name = (settings.SES_FROM_NAME or settings.EXECUTIVE_EMAIL_NAME or "Joseph David").strip()
    title = (settings.EXECUTIVE_EMAIL_TITLE or "Executive Director").strip()
    return ExecutiveIdentity(name=name, title=title, email=email)


def _aws_session_kwargs() -> dict[str, str]:
    kwargs: dict[str, str] = {}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        if settings.AWS_SESSION_TOKEN:
            kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN
    return kwargs


def _ses_region() -> str:
    return (settings.SES_REGION or settings.AWS_REGION or "ap-south-2").strip()


def _session() -> boto3.session.Session:
    return boto3.session.Session(region_name=_ses_region(), **_aws_session_kwargs())


def _ses_client():
    return _session().client("ses", region_name=_ses_region(), config=AWS_CLIENT_CONFIG)


def _sesv2_client():
    return _session().client("sesv2", region_name=_ses_region(), config=AWS_CLIENT_CONFIG)


def _html_body(body: str) -> str:
    return (
        "<html><body style=\"font-family:Arial,sans-serif;color:#202124;max-width:640px;line-height:1.6\">"
        f"<div style=\"background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px;padding:24px\">"
        f"{sanitize_client_text(body).replace(chr(10), '<br>')}"
        "<hr style=\"border:none;border-top:1px solid #e2e8f0;margin:20px 0\">"
        f"<p style=\"font-size:12px;color:#64748b;margin:0\">{get_executive_identity().display_name}<br>"
        f"<a href=\"https://aliyarsolutions.com\" style=\"color:#0f766e\">aliyarsolutions.com</a></p>"
        "</div></body></html>"
    )


def _build_raw_message(
    to: str,
    subject: str,
    body: str,
    *,
    to_name: str = "",
    reply_to: Optional[str] = None,
    attachments: Optional[list[dict[str, Any]]] = None,
) -> tuple[bytes, str, str]:
    subject, body = sanitize_subject_body(subject, body)
    identity = get_executive_identity()

    mixed = MIMEMultipart("mixed")
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(body, "plain", "utf-8"))
    alternative.attach(MIMEText(_html_body(body), "html", "utf-8"))
    mixed.attach(alternative)

    for attachment in attachments or []:
        filename = (attachment.get("filename") or "attachment").strip()
        payload = attachment.get("content") or b""
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        part = MIMEBase("application", "octet-stream")
        part.set_payload(payload)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        mixed.attach(part)

    mixed["Subject"] = str(Header(subject, "utf-8"))
    mixed["From"] = formataddr((identity.display_name, identity.email))
    mixed["To"] = formataddr((to_name, to)) if to_name else to
    mixed["Reply-To"] = reply_to or formataddr((identity.display_name, identity.email))

    return mixed.as_bytes(), subject, body


def _error_message(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        message = exc.response.get("Error", {}).get("Message", text)
        if code in {"MessageRejected", "MailFromDomainNotVerifiedException"}:
            return "AWS SES rejected the message because the sender identity is not verified or SES is still in sandbox mode."
        if code in {"AccessDenied", "AccessDeniedException"}:
            return "AWS SES access was denied. Confirm IAM permissions and SES sending rights."
        if code in {"Throttling", "TooManyRequestsException"}:
            return "AWS SES throttled the send request."
        return message
    if "sandbox" in lowered or "production access" in lowered:
        return "AWS SES is still in sandbox mode. Request production access before sending to real clients."
    if "identity" in lowered and "verified" in lowered:
        return "AWS SES sender identity is not verified."
    if "quota" in lowered:
        return "AWS SES send quota has been reached."
    return text.splitlines()[0][:240]


def _verified_identity_candidates(identity: ExecutiveIdentity) -> list[str]:
    domain = identity.email.split("@", 1)[-1] if "@" in identity.email else ""
    return [identity.email, domain] if domain else [identity.email]


def _identity_details_sync(identity: ExecutiveIdentity) -> list[dict[str, Any]]:
    client = _sesv2_client()
    details: list[dict[str, Any]] = []
    for candidate in _verified_identity_candidates(identity):
        if not candidate:
            continue
        try:
            result = client.get_email_identity(EmailIdentity=candidate)
        except ClientError:
            continue
        dkim = result.get("DkimAttributes", {}) or {}
        tokens = dkim.get("Tokens", []) or []
        details.append(
            {
                "identity": candidate,
                "identity_type": result.get("IdentityType"),
                "verification_status": result.get("VerificationStatus"),
                "verified_for_sending": bool(result.get("VerifiedForSendingStatus")),
                "dkim_status": dkim.get("Status"),
                "dkim_records": [
                    {
                        "type": "CNAME",
                        "name": f"{token}._domainkey.{candidate}",
                        "value": f"{token}.dkim.amazonses.com",
                    }
                    for token in tokens
                    if token and "@" not in candidate
                ],
            }
        )
    return details


def _identity_verified_sync(identity: ExecutiveIdentity) -> bool:
    for result in _identity_details_sync(identity):
        if result.get("VerificationStatus") == "SUCCESS":
            return True
        if result.get("verification_status") == "SUCCESS":
            return True
    return False


def _account_status_sync() -> dict[str, Any]:
    client = _sesv2_client()
    account = client.get_account()
    quota = account.get("SendQuota", {}) or {}
    review = ((account.get("Details") or {}).get("ReviewDetails") or {})
    identity = get_executive_identity()
    identity_details = _identity_details_sync(identity)
    verified = any(item.get("verification_status") == "SUCCESS" for item in identity_details)

    production_access = bool(account.get("ProductionAccessEnabled"))
    sending_enabled = bool(account.get("SendingEnabled", True))
    configured = bool(identity.email and (settings.AWS_ACCESS_KEY_ID or settings.USE_AWS or True))
    live = bool(configured and production_access and sending_enabled and verified and not settings.OUTREACH_PAUSED)

    if live:
        blocker_code = "ses_live"
        human_message = f"AWS SES is live under {identity.display_name}."
        required_action = "Run the outreach engine when the queue is ready."
        setup_steps: list[str] = []
    elif not identity.email:
        blocker_code = "ses_from_email_missing"
        human_message = "No executive from address is configured."
        required_action = "Set SES_FROM_EMAIL or EXECUTIVE_EMAIL_ADDRESS before sending."
        setup_steps = [
            "Set the executive email address in configuration.",
            "Use Joseph David as the sending identity.",
            "Verify the identity in AWS SES.",
        ]
    elif not production_access:
        blocker_code = "ses_sandbox_mode"
        review_status = (review.get("Status") or "").upper()
        if review_status == "DENIED":
            blocker_code = "ses_production_access_denied"
            human_message = "AWS SES production access was denied for this account."
            required_action = "Resolve AWS SES case review, verify domain identity, then re-request production access before sending to real clients."
        else:
            human_message = "AWS SES is configured but the account is still in sandbox mode."
            required_action = "Request SES production access before sending to real clients."
        setup_steps = [
            "Add the DKIM CNAME records for aliyarsolutions.com.",
            "Wait until SES identity verification becomes SUCCESS.",
            "Re-open or re-submit SES production access review.",
            "Confirm outbound delivery is enabled before starting outreach.",
        ]
    elif not verified:
        blocker_code = "ses_identity_not_verified"
        human_message = "AWS SES is live-capable, but the executive identity is not verified yet."
        required_action = "Verify joseph.david@aliyarsolutions.com or aliyarsolutions.com in SES."
        setup_steps = [
            "Verify the executive email address in AWS SES.",
            "Or verify the aliyarsolutions.com domain with DKIM/SPF.",
            "Confirm the identity shows SUCCESS in SES.",
        ]
    elif not sending_enabled:
        blocker_code = "ses_sending_disabled"
        human_message = "AWS SES sending is disabled for this account."
        required_action = "Enable SES sending or clear the account pause."
        setup_steps = [
            "Check SES account status.",
            "Confirm IAM permissions and sending authorization.",
            "Retry validation after enabling sending.",
        ]
    else:
        blocker_code = "ses_not_live"
        human_message = "AWS SES is configured but the engine is still blocked."
        required_action = "Review SES account status and retry validation."
        setup_steps = [
            "Check SES account limits.",
            "Confirm sender identity verification.",
            "Clear any outreach pauses.",
        ]

    return {
        "engine": "ses_outreach",
        "provider": "ses",
        "from_name": identity.name,
        "from_title": identity.title,
        "from_email": identity.email,
        "configured": configured,
        "connected": live,
        "production_access_enabled": production_access,
        "sending_enabled": sending_enabled,
        "identity_verified": verified,
        "daily_cap": int(settings.OUTREACH_DAILY_SEND_CAP or 48),
        "send_method": "ses_raw_email",
        "send_mode": "live" if live else "blocked",
        "outreach_paused": settings.OUTREACH_PAUSED,
        "validation_error": "" if live else human_message,
        "blocker_code": blocker_code,
        "human_message": human_message,
        "required_action": required_action,
        "setup_steps": setup_steps,
        "quota": {
            "max_24_hour_send": float(quota.get("Max24HourSend") or 0.0),
            "max_send_rate": float(quota.get("MaxSendRate") or 0.0),
            "sent_last_24_hours": float(quota.get("SentLast24Hours") or 0.0),
        },
        "account_review": {
            "status": review.get("Status"),
            "case_id": review.get("CaseId"),
        },
        "identity_details": identity_details,
        "safety": {
            "unsubscribe_footer": True,
            "do_not_contact_gate": True,
            "business_hours_gate": True,
            "daily_cap_gate": True,
            "client_language_sanitizer": True,
        },
    }


async def get_outbound_email_status(validate_provider: bool = True) -> dict[str, Any]:
    try:
        if validate_provider:
            return await asyncio.to_thread(_account_status_sync)
    except Exception as exc:
        logger.warning("SES status validation failed: %s", exc)
        return {
            "engine": "ses_outreach",
            "provider": "ses",
            "configured": False,
            "connected": False,
            "send_method": "ses_raw_email",
            "send_mode": "blocked",
            "validation_error": _error_message(exc),
            "blocker_code": "ses_validation_error",
            "human_message": "AWS SES validation failed.",
            "required_action": "Check AWS credentials, SES permissions, and sender identity.",
            "setup_steps": [],
            "safety": {
                "unsubscribe_footer": True,
                "do_not_contact_gate": True,
                "business_hours_gate": True,
                "daily_cap_gate": True,
                "client_language_sanitizer": True,
            },
        }
    return await asyncio.to_thread(_account_status_sync)


async def send_outbound_email(
    to: str,
    subject: str,
    body: str,
    *,
    to_name: str = "",
    reply_to: Optional[str] = None,
    attachments: Optional[list[dict[str, Any]]] = None,
) -> tuple[bool, str, str]:
    raw_bytes, subject, body = await asyncio.to_thread(
        _build_raw_message,
        to,
        subject,
        body,
        to_name=to_name,
        reply_to=reply_to,
        attachments=attachments,
    )

    def _send_sync() -> str:
        client = _ses_client()
        identity = get_executive_identity()
        source = formataddr((identity.display_name, identity.email))
        kwargs: dict[str, Any] = {
            "Source": source,
            "Destinations": [to],
            "RawMessage": {"Data": raw_bytes},
        }
        if settings.SES_CONFIGURATION_SET:
            kwargs["ConfigurationSetName"] = settings.SES_CONFIGURATION_SET
        client.send_raw_email(**kwargs)
        return "ses_raw_email"

    try:
        method = await asyncio.to_thread(_send_sync)
        logger.info("SES email sent to %s: %s", to, subject)
        return True, "", method
    except Exception as exc:
        error = _error_message(exc)
        logger.error("SES error sending to %s: %s", to, error)
        return False, error, "ses_raw_email"
