"""Add composite tenant_id+status index to clients table.

Revision ID: 0033_clients_tenant_status_index
Revises: 0032_followup_queue_tenant_index
Create Date: 2026-06-29

Notes:
  - invoice_engine.py:517 and economics/tracker.py:102 both filter on
    (tenant_id, status) when computing MRR and active client counts.
  - Without this index those queries perform full table scans, which
    will degrade as the clients table grows across tenants.
  - CONCURRENTLY allows online creation without locking the table.
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0033_clients_tenant_status_index"
down_revision = "0032_followup_queue_tenant_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_clients_tenant_status "
        "ON clients (tenant_id, status)"
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX CONCURRENTLY IF EXISTS "
        "ix_clients_tenant_status"
    )
