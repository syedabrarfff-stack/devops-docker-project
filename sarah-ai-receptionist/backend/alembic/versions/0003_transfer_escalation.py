"""transfer + after-hours escalation — clinic routing numbers, business hours, transfer outcome

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-02

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Where a live call goes during opening hours, and who gets texted outside
    # them. Both nullable: a clinic that configures neither simply never has a
    # transfer offered, which is the safe default.
    op.add_column("clinics", sa.Column("transfer_phone_number", sa.String(length=20), nullable=True))
    op.add_column(
        "clinics", sa.Column("after_hours_escalation_number", sa.String(length=20), nullable=True)
    )

    # server_default so existing rows get a valid empty object rather than NULL,
    # which is_open_now() would have to special-case.
    op.add_column(
        "clinics",
        sa.Column("business_hours", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )

    op.add_column("call_logs", sa.Column("transfer_result", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("call_logs", "transfer_result")
    op.drop_column("clinics", "business_hours")
    op.drop_column("clinics", "after_hours_escalation_number")
    op.drop_column("clinics", "transfer_phone_number")
