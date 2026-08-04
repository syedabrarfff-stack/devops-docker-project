"""port_requests table

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "port_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False, index=True),
        sa.Column("phone_number", sa.String(length=20), nullable=False, index=True),
        sa.Column("losing_carrier_name", sa.String(length=120), nullable=True),
        sa.Column("losing_account_number", sa.String(length=60), nullable=True),
        sa.Column("losing_account_pin", sa.String(length=30), nullable=True),
        sa.Column("billing_name", sa.String(length=200), nullable=True),
        sa.Column("billing_address", sa.Text(), nullable=True),
        sa.Column("twilio_port_in_sid", sa.String(length=64), nullable=True, unique=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft", index=True),
        sa.Column("status_details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("target_completion_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("port_requests")
