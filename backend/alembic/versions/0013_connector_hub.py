"""Add connector hub ingestion and packages tables.

Revision ID: 0013_connector_hub
Revises: 0012_merge_heads
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op

revision = "0013_connector_hub"
down_revision = "0012_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS connector_hub_ingestions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            date DATE NOT NULL,
            leads_processed INTEGER NOT NULL DEFAULT 0,
            sequences_loaded INTEGER NOT NULL DEFAULT 0,
            decks_matched INTEGER NOT NULL DEFAULT 0,
            intelligence_reports INTEGER NOT NULL DEFAULT 0,
            council_approvals INTEGER NOT NULL DEFAULT 0,
            council_revisions INTEGER NOT NULL DEFAULT 0,
            outreach_triggered INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            summary JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_connector_hub_ingestions_tenant_id "
        "ON connector_hub_ingestions (tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_connector_hub_ingestions_tenant_date "
        "ON connector_hub_ingestions (tenant_id, date)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS connector_hub_packages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            package_date DATE NOT NULL,
            source VARCHAR(50) NOT NULL,
            package_type VARCHAR(50) NOT NULL,
            raw_data JSONB,
            processed BOOLEAN NOT NULL DEFAULT false,
            council_verdict VARCHAR(20),
            processed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_connector_hub_packages_tenant_id "
        "ON connector_hub_packages (tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_connector_hub_packages_tenant_date "
        "ON connector_hub_packages (tenant_id, package_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_connector_hub_packages_source_type "
        "ON connector_hub_packages (source, package_type)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS connector_hub_packages")
    op.execute("DROP TABLE IF EXISTS connector_hub_ingestions")
