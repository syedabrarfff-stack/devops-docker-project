"""Add invoice engine tracking and revenue snapshots.

Revision ID: 0005_invoice_engine
Revises: 0004_approval_priority
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_invoice_engine"
down_revision = "0004_approval_priority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("invoices", sa.Column("paid_amount_usd", sa.Float(), nullable=False, server_default="0"))
    op.add_column("invoices", sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("invoices", sa.Column("last_reminder_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("overdue_alerted_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "revenue_snapshots",
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("mrr_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("invoiced_revenue_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("paid_revenue_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("outstanding_revenue_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active_clients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("paid_invoices", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overdue_invoices", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "snapshot_date", name="uq_revenue_snapshots_tenant_date"),
    )
    op.create_index("ix_revenue_snapshots_snapshot_date", "revenue_snapshots", ["snapshot_date"])
    op.create_index("ix_revenue_snapshots_tenant_id", "revenue_snapshots", ["tenant_id"])

    op.execute("ALTER TABLE revenue_snapshots ENABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS rls_revenue_snapshots_tenant_isolation ON revenue_snapshots;")
    op.execute(
        """
        CREATE POLICY rls_revenue_snapshots_tenant_isolation
        ON revenue_snapshots
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_revenue_snapshots_tenant_isolation ON revenue_snapshots;")
    op.execute("ALTER TABLE revenue_snapshots DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_revenue_snapshots_tenant_id", table_name="revenue_snapshots")
    op.drop_index("ix_revenue_snapshots_snapshot_date", table_name="revenue_snapshots")
    op.drop_table("revenue_snapshots")

    op.drop_column("invoices", "overdue_alerted_at")
    op.drop_column("invoices", "last_reminder_at")
    op.drop_column("invoices", "reminder_count")
    op.drop_column("invoices", "paid_amount_usd")
    op.drop_column("invoices", "description")
