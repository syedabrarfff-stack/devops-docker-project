"""Add reply log and nurture lead status.

Revision ID: 0002_reply_log
Revises: 0001_rls_setup
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_reply_log"
down_revision = "0001_rls_setup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE lead_status ADD VALUE IF NOT EXISTS 'NURTURE';")

    reply_classification = postgresql.ENUM(
        "INTERESTED",
        "QUESTION",
        "NOT_NOW",
        "NO",
        "OUT_OF_OFFICE",
        "UNKNOWN",
        name="reply_classification",
        create_type=False,
    )
    reply_classification.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reply_log",
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outreach_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_email", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("classification", reply_classification, nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("action_taken", sa.String(length=120), nullable=True),
        sa.Column("response_draft", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outreach_id"], ["outreach_log.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_reply_log_tenant_id", "reply_log", ["tenant_id"])
    op.create_index("ix_reply_log_lead_id", "reply_log", ["lead_id"])
    op.create_index("ix_reply_log_outreach_id", "reply_log", ["outreach_id"])
    op.create_index("ix_reply_log_from_email", "reply_log", ["from_email"])
    op.create_index("ix_reply_log_classification", "reply_log", ["classification"])
    op.create_index("ix_reply_log_action_taken", "reply_log", ["action_taken"])
    op.create_index("ix_reply_log_processed_at", "reply_log", ["processed_at"])

    op.execute('ALTER TABLE "reply_log" ENABLE ROW LEVEL SECURITY;')
    op.execute('DROP POLICY IF EXISTS "rls_reply_log_tenant_isolation" ON "reply_log";')
    op.execute(
        """
        CREATE POLICY "rls_reply_log_tenant_isolation"
        ON "reply_log"
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "rls_reply_log_tenant_isolation" ON "reply_log";')
    op.execute('ALTER TABLE "reply_log" DISABLE ROW LEVEL SECURITY;')
    op.drop_index("ix_reply_log_processed_at", table_name="reply_log")
    op.drop_index("ix_reply_log_action_taken", table_name="reply_log")
    op.drop_index("ix_reply_log_classification", table_name="reply_log")
    op.drop_index("ix_reply_log_from_email", table_name="reply_log")
    op.drop_index("ix_reply_log_outreach_id", table_name="reply_log")
    op.drop_index("ix_reply_log_lead_id", table_name="reply_log")
    op.drop_index("idx_reply_log_tenant_id", table_name="reply_log")
    op.drop_table("reply_log")
    postgresql.ENUM(name="reply_classification").drop(op.get_bind(), checkfirst=True)
