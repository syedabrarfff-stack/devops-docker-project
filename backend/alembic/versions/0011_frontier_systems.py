"""Add frontier intelligence systems — expert council, red team, relationship graph,
flywheel snapshots, and Cialdini persuasion sessions.

Revision ID: 0011_frontier_systems
Revises: 0010_captain_bridge
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_frontier_systems"
down_revision = "0010_captain_bridge"
branch_labels = None
depends_on = None

TABLES = (
    "expert_council_sessions",
    "red_team_analyses",
    "relationship_nodes",
    "relationship_edges",
    "flywheel_snapshots",
    "cialdini_sessions",
)


def upgrade() -> None:
    # ── Expert Council Sessions ───────────────────────────────────────────────
    op.create_table(
        "expert_council_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("majority_recommendation", sa.Text(), nullable=True),
        sa.Column("key_agreements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("key_disagreements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("final_synthesis", sa.Text(), nullable=True),
        sa.Column("agents_used", sa.Integer(), nullable=True, server_default="5"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_expert_council_tenant_id", "expert_council_sessions", ["tenant_id"]
    )
    op.create_index(
        "ix_expert_council_created_at", "expert_council_sessions", ["created_at"]
    )

    # ── Red Team Analyses ─────────────────────────────────────────────────────
    op.create_table(
        "red_team_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attack_vectors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("overall_risk_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("critical_vulnerabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("defensive_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("next_assessment_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_red_team_analyses_tenant_id", "red_team_analyses", ["tenant_id"]
    )
    op.create_index(
        "ix_red_team_analyses_created_at", "red_team_analyses", ["created_at"]
    )

    # ── Relationship Nodes ────────────────────────────────────────────────────
    op.create_table(
        "relationship_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.UniqueConstraint("tenant_id", "entity_type", "entity_id", name="uq_relationship_nodes_entity"),
    )
    op.create_index(
        "ix_relationship_nodes_tenant_id", "relationship_nodes", ["tenant_id"]
    )
    op.create_index(
        "ix_relationship_nodes_entity_type", "relationship_nodes", ["entity_type"]
    )

    # ── Relationship Edges ────────────────────────────────────────────────────
    op.create_table(
        "relationship_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "from_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("relationship_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("relationship_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("strength", sa.Numeric(3, 2), nullable=True, server_default="1.00"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_relationship_edges_tenant_id", "relationship_edges", ["tenant_id"]
    )
    op.create_index(
        "ix_relationship_edges_from_node_id", "relationship_edges", ["from_node_id"]
    )
    op.create_index(
        "ix_relationship_edges_to_node_id", "relationship_edges", ["to_node_id"]
    )

    # ── Flywheel Snapshots ────────────────────────────────────────────────────
    op.create_table(
        "flywheel_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flywheel_velocity", sa.Numeric(4, 2), nullable=True),
        sa.Column("weakest_link", sa.String(50), nullable=True),
        sa.Column("strongest_segment", sa.String(50), nullable=True),
        sa.Column("momentum_trend", sa.String(20), nullable=True),
        sa.Column("compound_growth_factor", sa.Numeric(6, 4), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_flywheel_snapshots_tenant_id", "flywheel_snapshots", ["tenant_id"]
    )
    op.create_index(
        "ix_flywheel_snapshots_snapshot_date", "flywheel_snapshots", ["snapshot_date"]
    )

    # ── Cialdini Sessions ─────────────────────────────────────────────────────
    op.create_table(
        "cialdini_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_email", sa.Text(), nullable=True),
        sa.Column("enhanced_email", sa.Text(), nullable=True),
        sa.Column("principles_applied", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("persuasion_score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cialdini_sessions_tenant_id", "cialdini_sessions", ["tenant_id"]
    )
    op.create_index(
        "ix_cialdini_sessions_lead_id", "cialdini_sessions", ["lead_id"]
    )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
