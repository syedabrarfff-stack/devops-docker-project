"""Merge 0013_bootstrap_live_schema_gaps and 0013_connector_hub heads.

Revision ID: 0014_merge_0013_heads
Revises: 0013_bootstrap_live_schema_gaps, 0013_connector_hub
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op

revision = "0014_merge_0013_heads"
down_revision = ("0013_bootstrap_live_schema_gaps", "0013_connector_hub")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
