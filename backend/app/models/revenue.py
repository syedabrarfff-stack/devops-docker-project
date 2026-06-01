from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy import UUID as SUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class ClientStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CHURNED = "CHURNED"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PAID = "PAID"
    OVERDUE = "OVERDUE"


class Client(JarvisBase):
    __tablename__ = "clients"

    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    package_tier: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mrr_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus, name="client_status"),
        nullable=False,
        default=ClientStatus.ACTIVE,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Invoice(JarvisBase):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoices_tenant_invoice_number"),
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"),
        nullable=False,
        default=InvoiceStatus.DRAFT,
        index=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Compatibility fields used by the existing document generation service.
    client_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    client_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
