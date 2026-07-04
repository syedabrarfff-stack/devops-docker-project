"""HQ-1: hq_action_requests table for the Headquarters Orchestrator.

Revision ID: 0041_headquarters_action_requests
Revises: 0040_revenue_activation_columns
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0041_headquarters_action_requests"
down_revision = "0040_revenue_activation_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hq_action_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False, server_default="status_query"),
        sa.Column("operation", sa.Text(), nullable=True),
        sa.Column("tier", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="DRAFTED"),
        sa.Column("plan", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("driver_model", sa.Text(), nullable=True),
        sa.Column("reviewer_model", sa.Text(), nullable=True),
        sa.Column("reviewer_verdict", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("rollback_commit", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_hq_action_requests_session", "hq_action_requests", ["session_id"])
    op.create_index("ix_hq_action_requests_status", "hq_action_requests", ["status"])
    op.create_index("ix_hq_action_requests_created", "hq_action_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_hq_action_requests_created", table_name="hq_action_requests")
    op.drop_index("ix_hq_action_requests_status", table_name="hq_action_requests")
    op.drop_index("ix_hq_action_requests_session", table_name="hq_action_requests")
    op.drop_table("hq_action_requests")
