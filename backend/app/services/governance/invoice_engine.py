from __future__ import annotations

import asyncio
import logging
import os
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.revenue import Client, ClientStatus, Invoice, InvoiceStatus, RevenueSnapshot
from app.services.notifications.slack import notify_slack
from app.services.notifications.telegram import notify_telegram
from app.services.outreach.email_transport import send_outbound_email

logger = logging.getLogger(__name__)


class InvoiceEngine:
    async def generate(
        self,
        client_id,
        amount_usd: float,
        description: str,
        due_days: int = 14,
        tenant_id=None,
    ) -> Invoice:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                client = await _load_client(session, tenant_uuid, client_id)
                if not client:
                    raise ValueError("Client not found")

                invoice_number = await _next_invoice_number(session, tenant_uuid)
                now = datetime.now(UTC)
                amount = round(float(amount_usd), 2)
                invoice = Invoice(
                    tenant_id=tenant_uuid,
                    client_id=client.id,
                    invoice_number=invoice_number,
                    description=description,
                    amount_usd=amount,
                    subtotal=amount,
                    total=amount,
                    currency="USD",
                    client_name=client.contact_name,
                    client_email=client.email,
                    client_company=client.company_name,
                    items=[
                        {
                            "description": description,
                            "qty": 1,
                            "unit_price": amount,
                            "amount": amount,
                        }
                    ],
                    notes="Payment instructions are included on the invoice.",
                    status=InvoiceStatus.DRAFT,
                    due_date=now + timedelta(days=max(1, int(due_days or 14))),
                )
                session.add(invoice)
                await session.flush()

                pdf_url = await _render_and_store_pdf(invoice, client)
                invoice.pdf_url = pdf_url
                await self._audit(
                    session,
                    tenant_uuid,
                    "invoice_generated",
                    invoice.id,
                    {
                        "invoice_number": invoice.invoice_number,
                        "client_id": str(client.id),
                        "amount_usd": amount,
                        "pdf_url": pdf_url,
                    },
                )
                await _upsert_revenue_snapshot(session, tenant_uuid)
                await session.refresh(invoice)

        await _notify_captain(
            "Invoice generated",
            f"{invoice.invoice_number} for {invoice.client_company or invoice.client_name or 'client'}: ${invoice.total:,.2f}",
        )
        return invoice

    async def send_invoice(self, invoice_id, tenant_id=None) -> bool:
        tenant_uuid = _tenant_uuid(tenant_id)
        sent = False
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                invoice = await _load_invoice(session, tenant_uuid, invoice_id)
                if not invoice:
                    raise ValueError("Invoice not found")
                if not invoice.client_email:
                    await self._audit(
                        session,
                        tenant_uuid,
                        "invoice_send_missing_email",
                        invoice.id,
                        {"invoice_number": invoice.invoice_number},
                    )
                    return False

                sent = await _send_invoice_email(invoice)
                if sent:
                    invoice.status = InvoiceStatus.SENT
                    invoice.sent_at = datetime.now(UTC)
                    await self._audit(
                        session,
                        tenant_uuid,
                        "invoice_sent",
                        invoice.id,
                        {
                            "invoice_number": invoice.invoice_number,
                            "client_email": invoice.client_email,
                        },
                    )
                    await _upsert_revenue_snapshot(session, tenant_uuid)
                else:
                    await self._audit(
                        session,
                        tenant_uuid,
                        "invoice_send_failed",
                        invoice.id,
                        {"invoice_number": invoice.invoice_number},
                    )

        if sent:
            await _notify_captain("Invoice sent", f"{invoice.invoice_number} was sent to {invoice.client_email}.")
        return sent

    async def check_overdue(self, tenant_id=None) -> list[Invoice]:
        tenant_uuid = _tenant_uuid(tenant_id)
        now = datetime.now(UTC)
        overdue_rows: list[Invoice] = []
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(Invoice)
                        .where(
                            Invoice.tenant_id == tenant_uuid,
                            Invoice.due_date < now,
                            Invoice.status != InvoiceStatus.PAID,
                        )
                        .order_by(Invoice.due_date.asc())
                    )
                ).scalars().all()

                for invoice in rows:
                    invoice.status = InvoiceStatus.OVERDUE
                    overdue_rows.append(invoice)
                    should_remind = invoice.reminder_count < 3 and (
                        not invoice.last_reminder_at or invoice.last_reminder_at < now - timedelta(days=2)
                    )
                    if should_remind and invoice.client_email:
                        if await _send_invoice_reminder(invoice):
                            invoice.reminder_count += 1
                            invoice.last_reminder_at = now
                            await self._audit(
                                session,
                                tenant_uuid,
                                "invoice_overdue_reminder_sent",
                                invoice.id,
                                {
                                    "invoice_number": invoice.invoice_number,
                                    "reminder_count": invoice.reminder_count,
                                },
                            )

                    if invoice.due_date and invoice.due_date < now - timedelta(days=7) and not invoice.overdue_alerted_at:
                        invoice.overdue_alerted_at = now
                        await _notify_captain(
                            "Invoice 7 days overdue",
                            f"{invoice.invoice_number} is more than 7 days overdue for {invoice.client_company or invoice.client_name or 'client'}.",
                        )

                if overdue_rows:
                    await _upsert_revenue_snapshot(session, tenant_uuid)

        return overdue_rows

    async def record_payment(self, invoice_id, amount: float, tenant_id=None) -> Invoice:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                invoice = await _load_invoice(session, tenant_uuid, invoice_id)
                if not invoice:
                    raise ValueError("Invoice not found")

                paid_amount = round(float(amount), 2)
                invoice.status = InvoiceStatus.PAID
                invoice.paid_at = datetime.now(UTC)
                invoice.paid_amount_usd = paid_amount

                client = None
                if invoice.client_id:
                    client = await _load_client(session, tenant_uuid, invoice.client_id)
                    if client:
                        client.mrr_usd = max(float(client.mrr_usd or 0), paid_amount)

                snapshot = await _upsert_revenue_snapshot(session, tenant_uuid)
                await self._audit(
                    session,
                    tenant_uuid,
                    "payment_received",
                    invoice.id,
                    {
                        "invoice_number": invoice.invoice_number,
                        "amount_usd": paid_amount,
                        "client_id": str(client.id) if client else None,
                        "snapshot_id": str(snapshot.id),
                    },
                )
                await session.refresh(invoice)

        await _notify_payment_received(invoice, paid_amount)
        return invoice

    async def revenue_snapshot(self, tenant_id=None) -> dict:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                snapshot = await _upsert_revenue_snapshot(session, tenant_uuid)
                await self._audit(
                    session,
                    tenant_uuid,
                    "revenue_snapshot_refreshed",
                    snapshot.id,
                    _serialize_snapshot(snapshot),
                )
                return _serialize_snapshot(snapshot)

    async def mrr_chart(self, tenant_id=None, days: int = 90) -> list[dict]:
        tenant_uuid = _tenant_uuid(tenant_id)
        start_date = date.today() - timedelta(days=max(1, min(int(days or 90), 365)))
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(RevenueSnapshot)
                        .where(
                            RevenueSnapshot.tenant_id == tenant_uuid,
                            RevenueSnapshot.snapshot_date >= start_date,
                        )
                        .order_by(RevenueSnapshot.snapshot_date.asc())
                    )
                ).scalars().all()
                return [_serialize_snapshot(row) for row in rows]

    async def _audit(self, session, tenant_id: uuid.UUID, action: str, entity_id, details: dict) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action=action,
                entity_type="invoice",
                entity_id=uuid.UUID(str(entity_id)),
                actor="InvoiceEngine",
                after_json=details,
                details=details,
            )
        )


async def _load_client(session, tenant_id: uuid.UUID, client_id) -> Client | None:
    return await session.scalar(
        select(Client).where(Client.tenant_id == tenant_id, Client.id == uuid.UUID(str(client_id)))
    )


async def _load_invoice(session, tenant_id: uuid.UUID, invoice_id) -> Invoice | None:
    return await session.scalar(
        select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.id == uuid.UUID(str(invoice_id)))
    )


async def _next_invoice_number(session, tenant_id: uuid.UUID) -> str:
    prefix = f"ALY-{datetime.now(UTC).strftime('%Y%m')}-"
    latest = await session.scalar(
        select(Invoice.invoice_number)
        .where(Invoice.tenant_id == tenant_id, Invoice.invoice_number.like(f"{prefix}%"))
        .order_by(Invoice.invoice_number.desc())
        .limit(1)
    )
    next_number = 1
    if latest:
        match = re.search(r"(\d{4})$", latest)
        if match:
            next_number = int(match.group(1)) + 1
    return f"{prefix}{next_number:04d}"


async def _render_and_store_pdf(invoice: Invoice, client: Client) -> str:
    output_dir = Path(os.getenv("JARVIS_INVOICE_DIR", "/data/invoices"))
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{invoice.invoice_number}_{_safe_slug(client.company_name or client.contact_name or 'client')}.pdf"
    await asyncio.to_thread(_build_invoice_pdf, pdf_path, invoice, client)
    return await _upload_to_s3_if_enabled(pdf_path, invoice.invoice_number)


def _build_invoice_pdf(pdf_path: Path, invoice: Invoice, client: Client) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title = ParagraphStyle("JarvisInvoiceTitle", parent=styles["Title"], fontSize=24, leading=30, textColor=colors.HexColor("#0F172A"))
    heading = ParagraphStyle("JarvisInvoiceHeading", parent=styles["Heading2"], fontSize=13, leading=17, textColor=colors.HexColor("#0F766E"))
    body = ParagraphStyle("JarvisInvoiceBody", parent=styles["BodyText"], fontSize=10, leading=14, textColor=colors.HexColor("#1F2937"))
    small = ParagraphStyle("JarvisInvoiceSmall", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#64748B"))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    rows = [["Description", "Qty", "Unit", "Amount"]]
    for item in invoice.items or []:
        rows.append(
            [
                _escape(item.get("description", invoice.description or "Aliyar Solutions service")),
                str(item.get("qty", 1)),
                _money(item.get("unit_price", invoice.amount_usd)),
                _money(item.get("amount", invoice.total)),
            ]
        )
    rows.extend([["", "", "Subtotal", _money(invoice.subtotal)], ["", "", "Total", _money(invoice.total)]])

    line_table = Table(rows, colWidths=[260, 45, 75, 75])
    line_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#CCFBF1")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (2, -2), (2, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    details = Table(
        [
            ["Invoice number", invoice.invoice_number],
            ["Invoice date", _date(invoice.created_at)],
            ["Due date", _date(invoice.due_date)],
            ["Prepared by", "Aliyar Solutions Team"],
        ],
        colWidths=[120, 335],
    )
    details.setStyle(_kv_table_style())

    bill_to = Table(
        [
            ["Client", client.company_name or invoice.client_company or "Client"],
            ["Contact", client.contact_name or invoice.client_name or "Client team"],
            ["Email", client.email or invoice.client_email or "Not provided"],
        ],
        colWidths=[120, 335],
    )
    bill_to.setStyle(_kv_table_style())

    story = [
        Paragraph("ALIYAR SOLUTIONS", small),
        Spacer(1, 0.3 * inch),
        Paragraph("Invoice", title),
        Spacer(1, 0.2 * inch),
        details,
        Spacer(1, 0.25 * inch),
        Paragraph("Bill To", heading),
        bill_to,
        Spacer(1, 0.25 * inch),
        line_table,
        Spacer(1, 0.35 * inch),
        Paragraph("Payment Instructions", heading),
        Paragraph(
            "Payment is due by the date listed above. Bank details will be provided through the secure client channel. "
            "Please include the invoice number as the payment reference.",
            body,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("Thank you for working with Aliyar Solutions.", body),
    ]
    doc.build(story)


async def _upload_to_s3_if_enabled(pdf_path: Path, invoice_number: str) -> str:
    if not (settings.USE_AWS and settings.AWS_S3_BUCKET):
        return str(pdf_path)

    key = f"invoices/{invoice_number}/{pdf_path.name}"

    def _upload() -> str:
        import boto3

        client = boto3.client("s3", region_name=settings.AWS_REGION)
        client.upload_file(str(pdf_path), settings.AWS_S3_BUCKET, key)
        return f"s3://{settings.AWS_S3_BUCKET}/{key}"

    try:
        return await asyncio.to_thread(_upload)
    except Exception as exc:
        logger.warning("S3 invoice upload failed, using local path: %s", exc)
        return str(pdf_path)


async def _send_invoice_email(invoice: Invoice) -> bool:
    if not invoice.client_email:
        return False

    html = (
        "<p>Hello,</p>"
        f"<p>Our team has prepared invoice <strong>{escape(invoice.invoice_number)}</strong> "
        f"for <strong>{_money(invoice.total)}</strong>.</p>"
        f"<p>Due date: <strong>{_date(invoice.due_date)}</strong>.</p>"
        "<p>The invoice PDF is attached when available. Payment instructions are included on the invoice.</p>"
        "<p>Aliyar Solutions Team</p>"
    )

    attachment = _local_pdf_path(invoice.pdf_url)
    attachments = []
    if attachment:
        attachments.append(
            {
                "filename": attachment.name,
                "content": attachment.read_bytes(),
            }
        )

    try:
        success, error, _ = await send_outbound_email(
            to=invoice.client_email,
            subject=f"Invoice {invoice.invoice_number} from Aliyar Solutions",
            body=_html_to_text(html),
            to_name=invoice.client_name or "",
            attachments=attachments or None,
        )
        if not success:
            logger.warning("Invoice email send failed for %s: %s", invoice.client_email, error)
        return success
    except Exception as exc:
        logger.warning("Invoice email send failed for %s: %s", invoice.client_email, exc)
        return False


async def _send_invoice_reminder(invoice: Invoice) -> bool:
    if not invoice.client_email:
        return False

    html = (
        "<p>Hello,</p>"
        f"<p>This is a reminder that invoice <strong>{escape(invoice.invoice_number)}</strong> "
        f"for <strong>{_money(invoice.total)}</strong> is now overdue.</p>"
        "<p>Please use the invoice number as the payment reference. Our team is available if anything needs clarification.</p>"
        "<p>Aliyar Solutions Team</p>"
    )

    try:
        success, error, _ = await send_outbound_email(
            to=invoice.client_email,
            subject=f"Reminder: Invoice {invoice.invoice_number}",
            body=_html_to_text(html),
            to_name=invoice.client_name or "",
        )
        if not success:
            logger.warning("Invoice reminder failed for %s: %s", invoice.client_email, error)
        return success
    except Exception as exc:
        logger.warning("Invoice reminder failed for %s: %s", invoice.client_email, exc)
        return False


async def _upsert_revenue_snapshot(session, tenant_id: uuid.UUID) -> RevenueSnapshot:
    today = date.today()
    mrr = await session.scalar(
        select(func.coalesce(func.sum(Client.mrr_usd), 0.0)).where(
            Client.tenant_id == tenant_id,
            Client.status == ClientStatus.ACTIVE,
        )
    )
    invoiced = await session.scalar(
        select(func.coalesce(func.sum(Invoice.total), 0.0)).where(Invoice.tenant_id == tenant_id)
    )
    paid = await session.scalar(
        select(func.coalesce(func.sum(Invoice.paid_amount_usd), 0.0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == InvoiceStatus.PAID,
        )
    )
    active_clients = await session.scalar(
        select(func.count(Client.id)).where(Client.tenant_id == tenant_id, Client.status == ClientStatus.ACTIVE)
    )
    paid_invoices = await session.scalar(
        select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant_id, Invoice.status == InvoiceStatus.PAID)
    )
    overdue_invoices = await session.scalar(
        select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant_id, Invoice.status == InvoiceStatus.OVERDUE)
    )
    snapshot = await session.scalar(
        select(RevenueSnapshot).where(
            RevenueSnapshot.tenant_id == tenant_id,
            RevenueSnapshot.snapshot_date == today,
        )
    )
    if not snapshot:
        snapshot = RevenueSnapshot(tenant_id=tenant_id, snapshot_date=today)
        session.add(snapshot)

    snapshot.mrr_usd = float(mrr or 0)
    snapshot.invoiced_revenue_usd = float(invoiced or 0)
    snapshot.paid_revenue_usd = float(paid or 0)
    snapshot.outstanding_revenue_usd = max(0.0, snapshot.invoiced_revenue_usd - snapshot.paid_revenue_usd)
    snapshot.active_clients = int(active_clients or 0)
    snapshot.paid_invoices = int(paid_invoices or 0)
    snapshot.overdue_invoices = int(overdue_invoices or 0)
    await session.flush()
    return snapshot


async def _notify_captain(title: str, summary: str) -> None:
    await notify_slack(f"*{title}*\n{summary}")
    await notify_telegram(f"*{title}*\n{summary}")
    await _broadcast(title.lower().replace(" ", "_"), {"title": title, "summary": summary})


async def _notify_payment_received(invoice: Invoice, amount: float) -> None:
    summary = f"{invoice.invoice_number}: ${amount:,.2f} received from {invoice.client_company or invoice.client_name or 'client'}."
    await notify_slack(f"*Payment received*\n{summary}")
    await notify_telegram(f"*Payment received*\n{summary}")
    await _broadcast("payment_received", {"invoice_id": str(invoice.id), "amount_usd": amount, "summary": summary})


async def _broadcast(event_type: str, data: dict) -> None:
    try:
        from app.api.v1.routes.ws import broadcast, captain_broadcast

        await broadcast(event_type, data, persist=True)
        await captain_broadcast(event_type, data)
    except Exception as exc:
        logger.debug("Invoice websocket broadcast skipped: %s", exc)


def _tenant_uuid(tenant_id) -> uuid.UUID:
    resolved = tenant_id or settings.JARVIS_DEFAULT_TENANT_ID
    if not resolved:
        raise ValueError("tenant_id is required")
    return uuid.UUID(str(resolved))


def _serialize_snapshot(snapshot: RevenueSnapshot) -> dict:
    return {
        "id": str(snapshot.id),
        "tenant_id": str(snapshot.tenant_id),
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "mrr_usd": snapshot.mrr_usd,
        "invoiced_revenue_usd": snapshot.invoiced_revenue_usd,
        "paid_revenue_usd": snapshot.paid_revenue_usd,
        "outstanding_revenue_usd": snapshot.outstanding_revenue_usd,
        "active_clients": snapshot.active_clients,
        "paid_invoices": snapshot.paid_invoices,
        "overdue_invoices": snapshot.overdue_invoices,
    }


def _local_pdf_path(value: str | None) -> Path | None:
    if not value or value.startswith("s3://"):
        return None
    path = Path(value)
    return path if path.exists() and path.is_file() else None


def _safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_")[:80] or "client"


def _money(value: Any) -> str:
    return f"${float(value or 0):,.2f}"


def _date(value: datetime | None) -> str:
    return value.strftime("%B %d, %Y") if value else "Not set"


def _escape(value: Any) -> str:
    return escape(str(value or ""))


def _html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _kv_table_style():
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E0F2FE")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#075985")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]
    )


invoice_engine = InvoiceEngine()
