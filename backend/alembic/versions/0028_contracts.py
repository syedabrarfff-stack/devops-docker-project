"""Add contracts table for client agreements and e-delivery.

Revision ID: 0028_contracts
Revises: 0027_performance_indexes
Create Date: 2026-06-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0028_contracts"
down_revision = "0027_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "proposal_id",
            sa.Integer(),
            sa.ForeignKey("proposals.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("client_name", sa.String(200), nullable=True),
        sa.Column("client_email", sa.String(320), nullable=True),
        sa.Column("client_company", sa.String(200), nullable=True),
        sa.Column("service_type", sa.String(200), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("pricing", sa.JSON(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False, index=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_contracts_status", "contracts", ["status"])
    op.create_index("ix_contracts_proposal_id", "contracts", ["proposal_id"])


def downgrade() -> None:
    op.drop_index("ix_contracts_proposal_id", table_name="contracts")
    op.drop_index("ix_contracts_status", table_name="contracts")
    op.drop_table("contracts")
