"""Add composite tenant_id+session_id index to conversations table.

Revision ID: 0036_conversation_tenant_session_id_index
Revises: 0035_approval_request_action_type_index
Create Date: 2026-06-29

Notes:
  - chat.py filters conversations by (session_id, tenant_id) on every turn
    to load chat history.  Currently only session_id is indexed, requiring
    an extra filter on tenant_id per matched row.
  - This composite index makes the lookup a single index scan.
  - CONCURRENTLY avoids table lock during creation.
"""
from __future__ import annotations

from alembic import op

revision = "0036_conversation_tenant_session_id_index"
down_revision = "0035_approval_request_action_type_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_conversations_tenant_session_id "
        "ON conversations (tenant_id, session_id)"
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX CONCURRENTLY IF EXISTS "
        "ix_conversations_tenant_session_id"
    )
