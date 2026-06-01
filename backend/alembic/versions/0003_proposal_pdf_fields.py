"""Add generated proposal PDF fields.

Revision ID: 0003_proposal_pdf_fields
Revises: 0002_reply_log
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_proposal_pdf_fields"
down_revision = "0002_reply_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("proposals", sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("proposals", sa.Column("package_tier", sa.String(length=50), nullable=True))
    op.add_column("proposals", sa.Column("invoice_number", sa.String(length=50), nullable=True))
    op.add_column("proposals", sa.Column("pdf_path", sa.Text(), nullable=True))
    op.add_column("proposals", sa.Column("pdf_url", sa.Text(), nullable=True))
    op.add_column("proposals", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_proposals_lead_id_leads",
        "proposals",
        "leads",
        ["lead_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_proposals_lead_id", "proposals", ["lead_id"])
    op.create_index("ix_proposals_invoice_number", "proposals", ["invoice_number"])


def downgrade() -> None:
    op.drop_index("ix_proposals_invoice_number", table_name="proposals")
    op.drop_index("ix_proposals_lead_id", table_name="proposals")
    op.drop_constraint("fk_proposals_lead_id_leads", "proposals", type_="foreignkey")
    op.drop_column("proposals", "approved_at")
    op.drop_column("proposals", "pdf_url")
    op.drop_column("proposals", "pdf_path")
    op.drop_column("proposals", "invoice_number")
    op.drop_column("proposals", "package_tier")
    op.drop_column("proposals", "lead_id")
