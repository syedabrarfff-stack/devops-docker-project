"""Add connector hub ingestion and packages tables.

Revision ID: 0013_connector_hub
Revises: 0012_merge_heads
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0013_connector_hub"
down_revision = "0012_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # connector_hub_ingestions — one record per tenant per day
    op.create_table(
        "connector_hub_ingestions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("leads_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sequences_loaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("decks_matched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("intelligence_reports", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("council_approvals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("council_revisions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outreach_triggered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("summary", JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_connector_hub_ingestions_tenant_date",
        "connector_hub_ingestions",
        ["tenant_id", "date"],
    )

    # connector_hub_packages — individual data package records
    op.create_table(
        "connector_hub_packages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("package_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("package_type", sa.String(50), nullable=False),
        sa.Column("raw_data", JSONB(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("council_verdict", sa.String(20), nullable=True),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_connector_hub_packages_tenant_date",
        "connector_hub_packages",
        ["tenant_id", "package_date"],
    )
    op.create_index(
        "ix_connector_hub_packages_source_type",
        "connector_hub_packages",
        ["source", "package_type"],
    )


def downgrade() -> None:
    op.drop_table("connector_hub_packages")
    op.drop_table("connector_hub_ingestions")
