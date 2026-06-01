"""Add AI council sessions and adaptive member weights.

Revision ID: 0006_ai_council
Revises: 0005_invoice_engine
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_ai_council"
down_revision = "0005_invoice_engine"
branch_labels = None
depends_on = None


TABLES = ("ai_council_sessions", "ai_council_member_weights")


def upgrade() -> None:
    op.create_table(
        "ai_council_sessions",
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("council_type", sa.String(length=80), nullable=False),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.Column("votes_json", sa.JSON(), nullable=False),
        sa.Column("result", sa.String(length=40), nullable=False),
        sa.Column("consensus_score", sa.Float(), nullable=False),
        sa.Column("winner_model", sa.String(length=160), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("quorum_met", sa.Boolean(), nullable=False),
        sa.Column("responses_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("cost_estimate_usd", sa.Float(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_council_sessions_tenant_id", "ai_council_sessions", ["tenant_id"])
    op.create_index("ix_ai_council_sessions_council_type", "ai_council_sessions", ["council_type"])
    op.create_index("ix_ai_council_sessions_result", "ai_council_sessions", ["result"])

    op.create_table(
        "ai_council_member_weights",
        sa.Column("member_id", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("specialty", sa.String(length=120), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("correct_predictions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wrong_predictions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_adjusted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "member_id", name="uq_ai_council_weights_tenant_member"),
    )
    op.create_index("ix_ai_council_member_weights_tenant_id", "ai_council_member_weights", ["tenant_id"])
    op.create_index("ix_ai_council_member_weights_member_id", "ai_council_member_weights", ["member_id"])
    op.create_index("ix_ai_council_member_weights_provider", "ai_council_member_weights", ["provider"])

    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant_isolation ON {table};")
        op.execute(
            f"""
            CREATE POLICY rls_{table}_tenant_isolation
            ON {table}
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
            """
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_ai_council_member_weights_provider", table_name="ai_council_member_weights")
    op.drop_index("ix_ai_council_member_weights_member_id", table_name="ai_council_member_weights")
    op.drop_index("ix_ai_council_member_weights_tenant_id", table_name="ai_council_member_weights")
    op.drop_table("ai_council_member_weights")

    op.drop_index("ix_ai_council_sessions_result", table_name="ai_council_sessions")
    op.drop_index("ix_ai_council_sessions_council_type", table_name="ai_council_sessions")
    op.drop_index("ix_ai_council_sessions_tenant_id", table_name="ai_council_sessions")
    op.drop_table("ai_council_sessions")
