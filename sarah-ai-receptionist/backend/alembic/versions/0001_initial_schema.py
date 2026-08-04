"""initial schema — organizations, clinics, providers, patients, appointments, call_logs, users, audit_log, subscriptions

Revision ID: 0001
Revises:
Create Date: 2026-07-26

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "clinics",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("twilio_phone_number", sa.String(20), unique=True, nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(50), nullable=True),
        sa.Column("country", sa.String(50), server_default="US"),
        sa.Column("timezone", sa.String(50), server_default="America/New_York"),
        sa.Column("clinic_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("sarah_name", sa.String(50), server_default="Sarah"),
        sa.Column("greeting_audio_s3_key", sa.String(500), nullable=True),
        sa.Column("plan", sa.String(50), server_default="starter"),
        sa.Column("stripe_customer_id", sa.String(100), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_clinics_organization_id", "clinics", ["organization_id"])

    op.create_table(
        "providers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(100), server_default="Dr."),
        sa.Column("speciality", sa.String(100), nullable=True),
        sa.Column("is_accepting_new_patients", sa.Boolean(), server_default=sa.true()),
        sa.Column("availability", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_providers_clinic_id", "providers", ["clinic_id"])

    op.create_table(
        "patients",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("date_of_birth", sa.String(20), nullable=True),
        sa.Column("insurance_provider", sa.String(100), nullable=True),
        sa.Column("insurance_member_id", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_new_patient", sa.Boolean(), server_default=sa.true()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_patients_clinic_id", "patients", ["clinic_id"])
    op.create_index("ix_patients_phone", "patients", ["phone"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.String(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("provider_id", sa.String(), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("call_log_id", sa.String(), nullable=True),
        sa.Column("appointment_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default="60"),
        sa.Column("service_type", sa.String(100), nullable=False),
        sa.Column("patient_name", sa.String(255), nullable=True),
        sa.Column("patient_phone", sa.String(20), nullable=True),
        sa.Column("patient_email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), server_default="scheduled"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(50), server_default="ai_call"),
        sa.Column("confirmation_sms_sent", sa.Boolean(), server_default=sa.false()),
        sa.Column("reminder_sent", sa.Boolean(), server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_appointments_clinic_id", "appointments", ["clinic_id"])
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])

    op.create_table(
        "call_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.String(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("call_sid", sa.String(100), nullable=False, unique=True),
        sa.Column("stream_sid", sa.String(100), nullable=True),
        sa.Column("caller_phone", sa.String(20), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("exchange_count", sa.Integer(), server_default="0"),
        sa.Column("outcome", sa.String(50), nullable=True),
        sa.Column("transferred", sa.Boolean(), server_default=sa.false()),
        sa.Column("appointment_booked", sa.Boolean(), server_default=sa.false()),
        sa.Column("transcript", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("recording_s3_key", sa.String(500), nullable=True),
        sa.Column("recording_duration_seconds", sa.Float(), nullable=True),
        sa.Column("avg_response_ms", sa.Float(), nullable=True),
        sa.Column("first_token_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_call_logs_clinic_id", "call_logs", ["clinic_id"])
    op.create_index("ix_call_logs_patient_id", "call_logs", ["patient_id"])
    op.create_index("ix_call_logs_call_sid", "call_logs", ["call_sid"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="clinic_manager"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_clinic_id", "users", ["clinic_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_clinic_id", "audit_log", ["clinic_id"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False, unique=True),
        sa.Column("stripe_subscription_id", sa.String(100), unique=True, nullable=True),
        sa.Column("stripe_customer_id", sa.String(100), nullable=True),
        sa.Column("plan", sa.String(50), server_default="starter"),
        sa.Column("monthly_price_usd", sa.Float(), server_default="299.0"),
        sa.Column("status", sa.String(50), server_default="trialing"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_subscriptions_clinic_id", "subscriptions", ["clinic_id"])


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("audit_log")
    op.drop_table("users")
    op.drop_table("call_logs")
    op.drop_table("appointments")
    op.drop_table("patients")
    op.drop_table("providers")
    op.drop_table("clinics")
    op.drop_table("organizations")
