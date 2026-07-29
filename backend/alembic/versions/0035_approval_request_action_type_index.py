"""Add composite tenant_id+action_type+status index to approval_requests table.

Revision ID: 0035_approval_request_action_type_index
Revises: 0034_reply_log_tenant_processed_at_index
Create Date: 2026-06-29

Notes:
  - compliance.py:442-457 filters on (tenant_id, action_type, status) to find
    pending outreach enrollment reviews.  The existing (tenant_id, status) index
    does not cover action_type, requiring an extra filter step.
  - The existing ix_approval_requests_tenant_status index is retained; it still
    accelerates the middleware gauge refresh which only filters on (tenant_id, status).
  - CONCURRENTLY avoids table lock during creation.
"""
from __future__ import annotations

from alembic import op

revision = "0035_approval_request_action_type_index"
down_revision = "0034_reply_log_tenant_processed_at_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_approval_requests_tenant_action_status "
        "ON approval_requests (tenant_id, action_type, status)"
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX CONCURRENTLY IF EXISTS "
        "ix_approval_requests_tenant_action_status"
    )
