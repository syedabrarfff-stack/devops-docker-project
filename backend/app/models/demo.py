from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy import UUID as SUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class DemoPackage(JarvisBase):
    __tablename__ = "demo_packages"

    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    pain_points: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    demo_script: Mapped[str] = mapped_column(Text, nullable=False)
    roi_projection: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(600), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
