"""Add composite tenant_id+processed_at index to reply_log table.

Revision ID: 0034_reply_log_tenant_processed_at_index
Revises: 0033_clients_tenant_status_index
Create Date: 2026-06-29

Notes:
  - compliance.py filters on (tenant_id, processed_at) to count recent replies.
  - Without this index the query does an index scan on tenant_id then re-filters,
    which becomes slow as reply_log grows.
  - CONCURRENTLY avoids table lock during creation.
"""
from __future__ import annotations

from alembic import op

revision = "0034_reply_log_tenant_processed_at_index"
down_revision = "0033_clients_tenant_status_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_reply_log_tenant_processed_at "
        "ON reply_log (tenant_id, processed_at)"
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX CONCURRENTLY IF EXISTS "
        "ix_reply_log_tenant_processed_at"
    )
