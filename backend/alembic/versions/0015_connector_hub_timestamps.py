"""Add JarvisBase timestamps to connector hub tables.

Revision ID: 0015_connector_hub_timestamps
Revises: 0014_merge_0013_heads
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op

revision = "0015_connector_hub_timestamps"
down_revision = "0014_merge_0013_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE connector_hub_ingestions "
        "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE connector_hub_packages "
        "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE connector_hub_packages DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE connector_hub_ingestions DROP COLUMN IF EXISTS updated_at")
