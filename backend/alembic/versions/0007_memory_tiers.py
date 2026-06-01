"""Add tiered memory architecture tables.

Revision ID: 0007_memory_tiers
Revises: 0006_ai_council
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_memory_tiers"
down_revision = "0006_ai_council"
branch_labels = None
depends_on = None


TABLES = ("memory_operational", "memory_strategic", "civilization_memory")


def upgrade() -> None:
    op.create_table(
        "memory_operational",
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_operational_tenant_id", "memory_operational", ["tenant_id"])
    op.create_index("ix_memory_operational_category", "memory_operational", ["category"])
    op.create_index("ix_memory_operational_source", "memory_operational", ["source"])
    op.create_index("ix_memory_operational_expires_at", "memory_operational", ["expires_at"])

    op.create_table(
        "memory_strategic",
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("source_operational_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_operational_id"], ["memory_operational.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_strategic_tenant_id", "memory_strategic", ["tenant_id"])
    op.create_index("ix_memory_strategic_category", "memory_strategic", ["category"])
    op.create_index("ix_memory_strategic_source_operational_id", "memory_strategic", ["source_operational_id"])

    op.create_table(
        "civilization_memory",
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("record_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_hash"),
    )
    op.create_index("ix_civilization_memory_tenant_id", "civilization_memory", ["tenant_id"])
    op.create_index("ix_civilization_memory_event_type", "civilization_memory", ["event_type"])
    op.create_index("ix_civilization_memory_record_hash", "civilization_memory", ["record_hash"])

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

    op.drop_index("ix_civilization_memory_record_hash", table_name="civilization_memory")
    op.drop_index("ix_civilization_memory_event_type", table_name="civilization_memory")
    op.drop_index("ix_civilization_memory_tenant_id", table_name="civilization_memory")
    op.drop_table("civilization_memory")

    op.drop_index("ix_memory_strategic_source_operational_id", table_name="memory_strategic")
    op.drop_index("ix_memory_strategic_category", table_name="memory_strategic")
    op.drop_index("ix_memory_strategic_tenant_id", table_name="memory_strategic")
    op.drop_table("memory_strategic")

    op.drop_index("ix_memory_operational_expires_at", table_name="memory_operational")
    op.drop_index("ix_memory_operational_source", table_name="memory_operational")
    op.drop_index("ix_memory_operational_category", table_name="memory_operational")
    op.drop_index("ix_memory_operational_tenant_id", table_name="memory_operational")
    op.drop_table("memory_operational")
