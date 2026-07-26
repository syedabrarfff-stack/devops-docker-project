"""hardening — consent flag, patient uniqueness, composite indexes, real appointment->call_log FK

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "call_logs",
        sa.Column("consent_disclosed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # One patient record per (clinic, phone) — closes the race where concurrent
    # calls from the same number could create duplicate patient rows.
    op.create_unique_constraint("uq_patients_clinic_id_phone", "patients", ["clinic_id", "phone"])

    # Real query patterns are clinic_id + date range / status, not clinic_id alone.
    op.create_index("ix_call_logs_clinic_id_started_at", "call_logs", ["clinic_id", "started_at"])
    op.create_index(
        "ix_appointments_datetime_status_reminder",
        "appointments",
        ["appointment_datetime", "status", "reminder_sent"],
    )

    # appointments.call_log_id existed with no FK constraint — make the
    # call<->appointment link real so it can actually be relied on.
    op.create_foreign_key(
        "fk_appointments_call_log_id", "appointments", "call_logs", ["call_log_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_appointments_call_log_id", "appointments", type_="foreignkey")
    op.drop_index("ix_appointments_datetime_status_reminder", table_name="appointments")
    op.drop_index("ix_call_logs_clinic_id_started_at", table_name="call_logs")
    op.drop_constraint("uq_patients_clinic_id_phone", "patients", type_="unique")
    op.drop_column("call_logs", "consent_disclosed")
