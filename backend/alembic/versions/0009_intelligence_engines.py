"""Add Intelligence Engines tables — psychology, forecasting, assessment, pricing, governance.

Revision ID: 0009_intelligence_engines
Revises: 0008_department_intelligence
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_intelligence_engines"
down_revision = "0008_department_intelligence"
branch_labels = None
depends_on = None

TABLES = (
    "prospect_psychology_profiles",
    "revenue_forecasts",
    "self_assessment_reports",
    "client_health_scores",
    "dynamic_pricing_records",
    "autonomous_governance_log",
)


def upgrade() -> None:
    # ── Prospect Psychology Profiles ─────────────────────────────────────────
    op.create_table(
        "prospect_psychology_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("buying_style", sa.String(20), nullable=False),
        sa.Column("risk_tolerance", sa.String(10), nullable=False),
        sa.Column("decision_speed", sa.String(15), nullable=False),
        sa.Column("urgency_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("objection_forecast", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("recommended_approach", sa.Text(), nullable=True),
        sa.Column("personalization_hooks", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_psych_profiles_tenant_id", "prospect_psychology_profiles", ["tenant_id"])
    op.create_index("ix_psych_profiles_lead_id", "prospect_psychology_profiles", ["lead_id"])
    op.create_index("ix_psych_profiles_buying_style", "prospect_psychology_profiles", ["buying_style"])

    # ── Revenue Forecasts ─────────────────────────────────────────────────────
    op.create_table(
        "revenue_forecasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("p10_revenue", sa.Numeric(12, 2), nullable=True),
        sa.Column("p50_revenue", sa.Numeric(12, 2), nullable=True),
        sa.Column("p90_revenue", sa.Numeric(12, 2), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("pipeline_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("simulation_runs", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("forecast_date", sa.Date(), nullable=True),
        sa.Column("recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_revenue_forecasts_tenant_id", "revenue_forecasts", ["tenant_id"])
    op.create_index("ix_revenue_forecasts_forecast_date", "revenue_forecasts", ["forecast_date"])

    # ── Self-Assessment Reports ───────────────────────────────────────────────
    op.create_table(
        "self_assessment_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_grade", sa.String(1), nullable=False),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("dimension_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("weaknesses", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("priority_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_self_assessment_tenant_id", "self_assessment_reports", ["tenant_id"])
    op.create_index("ix_self_assessment_created_at", "self_assessment_reports", ["created_at"])

    # ── Client Health Scores ──────────────────────────────────────────────────
    op.create_table(
        "client_health_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("health_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("health_tier", sa.String(20), nullable=False),
        sa.Column("signals", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("churn_probability", sa.Numeric(4, 3), nullable=True),
        sa.Column("recommended_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("next_touch_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_health_tenant_id", "client_health_scores", ["tenant_id"])
    op.create_index("ix_client_health_client_id", "client_health_scores", ["client_id"])
    op.create_index("ix_client_health_tier", "client_health_scores", ["health_tier"])
    op.create_index("ix_client_health_score", "client_health_scores", ["health_score"])

    # ── Dynamic Pricing Records ───────────────────────────────────────────────
    op.create_table(
        "dynamic_pricing_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_type", sa.String(100), nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("final_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_tier", sa.String(20), nullable=True),
        sa.Column("adjustments", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pricing_records_tenant_id", "dynamic_pricing_records", ["tenant_id"])
    op.create_index("ix_pricing_records_lead_id", "dynamic_pricing_records", ["lead_id"])
    op.create_index("ix_pricing_records_price_tier", "dynamic_pricing_records", ["price_tier"])

    # ── Autonomous Governance Log ─────────────────────────────────────────────
    op.create_table(
        "autonomous_governance_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("auto_executed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("outcome", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_log_tenant_id", "autonomous_governance_log", ["tenant_id"])
    op.create_index("ix_gov_log_action_type", "autonomous_governance_log", ["action_type"])
    op.create_index("ix_gov_log_tier", "autonomous_governance_log", ["tier"])
    op.create_index("ix_gov_log_created_at", "autonomous_governance_log", ["created_at"])

    # ── Row-Level Security ────────────────────────────────────────────────────
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

    op.drop_index("ix_gov_log_created_at", table_name="autonomous_governance_log")
    op.drop_index("ix_gov_log_tier", table_name="autonomous_governance_log")
    op.drop_index("ix_gov_log_action_type", table_name="autonomous_governance_log")
    op.drop_index("ix_gov_log_tenant_id", table_name="autonomous_governance_log")
    op.drop_table("autonomous_governance_log")

    op.drop_index("ix_pricing_records_price_tier", table_name="dynamic_pricing_records")
    op.drop_index("ix_pricing_records_lead_id", table_name="dynamic_pricing_records")
    op.drop_index("ix_pricing_records_tenant_id", table_name="dynamic_pricing_records")
    op.drop_table("dynamic_pricing_records")

    op.drop_index("ix_client_health_score", table_name="client_health_scores")
    op.drop_index("ix_client_health_tier", table_name="client_health_scores")
    op.drop_index("ix_client_health_client_id", table_name="client_health_scores")
    op.drop_index("ix_client_health_tenant_id", table_name="client_health_scores")
    op.drop_table("client_health_scores")

    op.drop_index("ix_self_assessment_created_at", table_name="self_assessment_reports")
    op.drop_index("ix_self_assessment_tenant_id", table_name="self_assessment_reports")
    op.drop_table("self_assessment_reports")

    op.drop_index("ix_revenue_forecasts_forecast_date", table_name="revenue_forecasts")
    op.drop_index("ix_revenue_forecasts_tenant_id", table_name="revenue_forecasts")
    op.drop_table("revenue_forecasts")

    op.drop_index("ix_psych_profiles_buying_style", table_name="prospect_psychology_profiles")
    op.drop_index("ix_psych_profiles_lead_id", table_name="prospect_psychology_profiles")
    op.drop_index("ix_psych_profiles_tenant_id", table_name="prospect_psychology_profiles")
    op.drop_table("prospect_psychology_profiles")
