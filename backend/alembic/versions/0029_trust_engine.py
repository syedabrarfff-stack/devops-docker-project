"""Add Trust Engine tables: executive_briefs, lead_engagement_events, referral_requests.

Revision ID: 0029_trust_engine
Revises: 0028_contracts
Create Date: 2026-06-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0029_trust_engine"
down_revision = "0028_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "executive_briefs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "lead_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("company_name", sa.String(300), nullable=False),
        sa.Column("industry", sa.String(150), nullable=True),
        sa.Column("pain_points", sa.JSON(), nullable=True),
        sa.Column("bottlenecks", sa.JSON(), nullable=True),
        sa.Column("opportunities", sa.JSON(), nullable=True),
        sa.Column("quick_wins", sa.JSON(), nullable=True),
        sa.Column("risk_factors", sa.JSON(), nullable=True),
        sa.Column("estimated_roi", sa.String(500), nullable=True),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("trust_score_at_creation", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("status", sa.String(30), server_default="generated", nullable=False, index=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_executive_briefs_lead_id", "executive_briefs", ["lead_id"])
    op.create_index("ix_executive_briefs_status", "executive_briefs", ["status"])

    op.create_table(
        "lead_engagement_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "lead_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("event_type", sa.String(80), nullable=False, index=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_lead_engagement_events_lead_id", "lead_engagement_events", ["lead_id"])
    op.create_index("ix_lead_engagement_events_event_type", "lead_engagement_events", ["event_type"])

    op.create_table(
        "referral_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "client_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False, index=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_referral_requests_client_id", "referral_requests", ["client_id"])
    op.create_index("ix_referral_requests_status", "referral_requests", ["status"])
    op.create_index("ix_referral_requests_request_type", "referral_requests", ["request_type"])


def downgrade() -> None:
    op.drop_index("ix_referral_requests_request_type", table_name="referral_requests")
    op.drop_index("ix_referral_requests_status", table_name="referral_requests")
    op.drop_index("ix_referral_requests_client_id", table_name="referral_requests")
    op.drop_table("referral_requests")

    op.drop_index("ix_lead_engagement_events_event_type", table_name="lead_engagement_events")
    op.drop_index("ix_lead_engagement_events_lead_id", table_name="lead_engagement_events")
    op.drop_table("lead_engagement_events")

    op.drop_index("ix_executive_briefs_status", table_name="executive_briefs")
    op.drop_index("ix_executive_briefs_lead_id", table_name="executive_briefs")
    op.drop_table("executive_briefs")
