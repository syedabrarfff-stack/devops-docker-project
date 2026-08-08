"""Billing localization: SAR as the default currency for new subscriptions

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-07

Part of the Saudi Arabia / GCC market pivot. Renames the USD-specific
`monthly_price_usd` column to currency-agnostic `monthly_price` and adds a
`currency` column. Existing rows are explicitly backfilled to 'USD' first --
they were created under the old US-only pricing and must keep reading as
USD, not be silently relabeled SAR by a blanket default. Only the column's
server_default for *future* rows changes to SAR.
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("subscriptions", "monthly_price_usd", new_column_name="monthly_price")
    op.add_column("subscriptions", sa.Column("currency", sa.String(3), nullable=True))

    conn = op.get_bind()
    conn.execute(sa.text("UPDATE subscriptions SET currency = 'USD' WHERE currency IS NULL"))

    op.alter_column("subscriptions", "currency", nullable=False, server_default="SAR")


def downgrade() -> None:
    op.alter_column("subscriptions", "monthly_price", new_column_name="monthly_price_usd")
    op.drop_column("subscriptions", "currency")
