"""Add Captain Bridge tables — brain dumps, email intelligence, predicted actions, pushbacks.
Also enriches leads table with psychology_profile and predicted_value columns.

Revision ID: 0010_captain_bridge
Revises: 0009_intelligence_engines
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_captain_bridge"
down_revision = "0009_intelligence_engines"
branch_labels = None
depends_on = None

TABLES = (
    "captain_brain_dumps",
    "captain_email_intelligence",
    "predicted_actions",
    "captain_pushbacks",
)


def upgrade() -> None:
    # ── Captain Brain Dumps ───────────────────────────────────────────────────
    op.create_table(
        "captain_brain_dumps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("action_items", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("leads_mentioned", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("decisions_made", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("follow_ups_needed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("key_insights", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brain_dumps_tenant_id", "captain_brain_dumps", ["tenant_id"])
    op.create_index("ix_brain_dumps_created_at", "captain_brain_dumps", ["created_at"])

    # ── Captain Email Intelligence ────────────────────────────────────────────
    op.create_table(
        "captain_email_intelligence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_thread", sa.Text(), nullable=False),
        sa.Column("sender", sa.String(200), nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("key_asks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("objections", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("buying_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommended_next_step", sa.Text(), nullable=True),
        sa.Column("urgency_score", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_intel_tenant_id", "captain_email_intelligence", ["tenant_id"])
    op.create_index("ix_email_intel_urgency_score", "captain_email_intelligence", ["urgency_score"])
    op.create_index("ix_email_intel_created_at", "captain_email_intelligence", ["created_at"])

    # ── Predicted Actions ─────────────────────────────────────────────────────
    op.create_table(
        "predicted_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("priority", sa.SmallInteger(), nullable=False),
        sa.Column("expected_impact", sa.Text(), nullable=True),
        sa.Column("effort_level", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("deadline_suggestion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predicted_actions_tenant_id", "predicted_actions", ["tenant_id"])
    op.create_index("ix_predicted_actions_priority", "predicted_actions", ["priority"])
    op.create_index("ix_predicted_actions_status", "predicted_actions", ["status"])

    # ── Captain Pushbacks ─────────────────────────────────────────────────────
    op.create_table(
        "captain_pushbacks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_text", sa.Text(), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="0.000"),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("alternatives", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("final_recommendation", sa.Text(), nullable=True),
        sa.Column("captain_overrode", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pushbacks_tenant_id", "captain_pushbacks", ["tenant_id"])
    op.create_index("ix_pushbacks_verdict", "captain_pushbacks", ["verdict"])
    op.create_index("ix_pushbacks_created_at", "captain_pushbacks", ["created_at"])

    # ── RLS policies for all new tables ──────────────────────────────────────
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY rls_{table}_tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
            """
        )

    # ── Enrich leads table ────────────────────────────────────────────────────
    op.add_column(
        "leads",
        sa.Column("psychology_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("predicted_value", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    # Remove leads enrichment columns
    op.drop_column("leads", "predicted_value")
    op.drop_column("leads", "psychology_profile")

    # Drop new tables in reverse order
    for table in reversed(TABLES):
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_pushbacks_created_at", table_name="captain_pushbacks")
    op.drop_index("ix_pushbacks_verdict", table_name="captain_pushbacks")
    op.drop_index("ix_pushbacks_tenant_id", table_name="captain_pushbacks")
    op.drop_table("captain_pushbacks")

    op.drop_index("ix_predicted_actions_status", table_name="predicted_actions")
    op.drop_index("ix_predicted_actions_priority", table_name="predicted_actions")
    op.drop_index("ix_predicted_actions_tenant_id", table_name="predicted_actions")
    op.drop_table("predicted_actions")

    op.drop_index("ix_email_intel_created_at", table_name="captain_email_intelligence")
    op.drop_index("ix_email_intel_urgency_score", table_name="captain_email_intelligence")
    op.drop_index("ix_email_intel_tenant_id", table_name="captain_email_intelligence")
    op.drop_table("captain_email_intelligence")

    op.drop_index("ix_brain_dumps_created_at", table_name="captain_brain_dumps")
    op.drop_index("ix_brain_dumps_tenant_id", table_name="captain_brain_dumps")
    op.drop_table("captain_brain_dumps")
