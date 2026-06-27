"""Add composite tenant_id+status+scheduled_at index to follow_up_queue.

Revision ID: 0032_followup_queue_tenant_index
Revises: 0031_lead_embedding_vec
Create Date: 2026-06-27

Notes:
  - The existing ix_follow_up_queue_status_scheduled_at covers (status, scheduled_at).
  - The most critical query filters on tenant_id + status + scheduled_at in that order.
  - This index makes execute_due_outreach() efficient for multi-tenant deployments.
  - For the current single-tenant setup the improvement is marginal; included for scale.
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0032_followup_queue_tenant_index"
down_revision = "0031_lead_embedding_vec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_follow_up_queue_tenant_status_scheduled_at "
        "ON follow_up_queue (tenant_id, status, scheduled_at)"
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX CONCURRENTLY IF EXISTS "
        "ix_follow_up_queue_tenant_status_scheduled_at"
    )
