"""Add approval priority.

Revision ID: 0004_approval_priority
Revises: 0003_proposal_pdf_fields
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_approval_priority"
down_revision = "0003_proposal_pdf_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("approval_requests", sa.Column("priority", sa.Integer(), nullable=False, server_default="10"))
    op.create_index("ix_approval_requests_priority", "approval_requests", ["priority"])
    op.alter_column("approval_requests", "priority", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_approval_requests_priority", table_name="approval_requests")
    op.drop_column("approval_requests", "priority")
