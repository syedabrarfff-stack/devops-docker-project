"""Layer 18 — Truth, Validation & Resilience: 10 new tables for self-correcting autonomous company intelligence.

Revision ID: 0030_truth_validation_resilience
Revises: 0029_trust_engine
Create Date: 2026-06-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0030_truth_validation_resilience"
down_revision = "0029_trust_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # truth_events
    # -------------------------------------------------------------------------
    op.create_table(
        "truth_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("prediction_type", sa.String(80), nullable=True, index=True),
        sa.Column("entity_type", sa.String(80), nullable=True),
        sa.Column("entity_id", sa.String(120), nullable=True),
        sa.Column("predicted_value", sa.Float(), nullable=True),
        sa.Column("predicted_label", sa.String(200), nullable=True),
        sa.Column("predicted_by", sa.String(100), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "outcome_recorded",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            index=True,
        ),
        sa.Column("outcome_value", sa.Float(), nullable=True),
        sa.Column("outcome_label", sa.String(200), nullable=True),
        sa.Column("outcome_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accuracy_delta", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_truth_events_tenant_id", "truth_events", ["tenant_id"])
    op.create_index("ix_truth_events_prediction_type", "truth_events", ["prediction_type"])
    op.create_index("ix_truth_events_outcome_recorded", "truth_events", ["outcome_recorded"])

    # -------------------------------------------------------------------------
    # prediction_accuracy
    # -------------------------------------------------------------------------
    op.create_table(
        "prediction_accuracy",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("prediction_type", sa.String(80), nullable=True, index=True),
        sa.Column("period_date", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("total_predictions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("scored_predictions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("mean_absolute_error", sa.Float(), nullable=True),
        sa.Column("accuracy_score", sa.Float(), nullable=True),
        sa.Column("calibration_score", sa.Float(), nullable=True),
        sa.Column("trend", sa.String(20), nullable=True),
        sa.Column("weight_adjustment", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_prediction_accuracy_tenant_id", "prediction_accuracy", ["tenant_id"])
    op.create_index("ix_prediction_accuracy_prediction_type", "prediction_accuracy", ["prediction_type"])
    op.create_index("ix_prediction_accuracy_period_date", "prediction_accuracy", ["period_date"])

    # -------------------------------------------------------------------------
    # reality_checks
    # -------------------------------------------------------------------------
    op.create_table(
        "reality_checks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("check_type", sa.String(80), nullable=True, index=True),
        sa.Column("prediction_summary", sa.JSON(), nullable=True),
        sa.Column("reality_summary", sa.JSON(), nullable=True),
        sa.Column("accuracy_pct", sa.Float(), nullable=True),
        sa.Column("gap_analysis", sa.Text(), nullable=True),
        sa.Column("auto_corrective_actions", sa.JSON(), nullable=True),
        sa.Column(
            "captain_report_sent",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("report_content", sa.Text(), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_reality_checks_tenant_id", "reality_checks", ["tenant_id"])
    op.create_index("ix_reality_checks_check_type", "reality_checks", ["check_type"])

    # -------------------------------------------------------------------------
    # resilience_events
    # -------------------------------------------------------------------------
    op.create_table(
        "resilience_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("incident_type", sa.String(80), nullable=True, index=True),
        sa.Column("severity", sa.String(20), nullable=True, index=True),
        sa.Column("status", sa.String(30), server_default="detected", nullable=False, index=True),
        sa.Column("playbook_used", sa.String(120), nullable=True),
        sa.Column("escalation_path", sa.JSON(), nullable=True),
        sa.Column("fallback_systems_activated", sa.JSON(), nullable=True),
        sa.Column("recovery_steps_taken", sa.JSON(), nullable=True),
        sa.Column("estimated_recovery_minutes", sa.Integer(), nullable=True),
        sa.Column("actual_recovery_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "captain_notified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("impact_summary", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_resilience_events_tenant_id", "resilience_events", ["tenant_id"])
    op.create_index("ix_resilience_events_incident_type", "resilience_events", ["incident_type"])
    op.create_index("ix_resilience_events_severity", "resilience_events", ["severity"])
    op.create_index("ix_resilience_events_status", "resilience_events", ["status"])
    op.create_index("ix_resilience_events_detected_at", "resilience_events", ["detected_at"])

    # -------------------------------------------------------------------------
    # financial_health
    # -------------------------------------------------------------------------
    op.create_table(
        "financial_health",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("mrr", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("arr", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("gross_margin_pct", sa.Float(), nullable=True),
        sa.Column("client_acquisition_cost", sa.Float(), nullable=True),
        sa.Column("avg_lifetime_value", sa.Float(), nullable=True),
        sa.Column("revenue_concentration_risk", sa.Float(), nullable=True),
        sa.Column("cash_flow_30d", sa.Float(), nullable=True),
        sa.Column("runway_months", sa.Float(), nullable=True),
        sa.Column("financial_health_score", sa.Float(), nullable=True),
        sa.Column("active_clients", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("churned_clients_30d", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("new_clients_30d", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("service_line_breakdown", sa.JSON(), nullable=True),
        sa.Column("risk_alerts", sa.JSON(), nullable=True),
        sa.Column("expansion_alerts", sa.JSON(), nullable=True),
        sa.Column("cfo_briefing", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_financial_health_tenant_id", "financial_health", ["tenant_id"])
    op.create_index("ix_financial_health_snapshot_date", "financial_health", ["snapshot_date"])

    # -------------------------------------------------------------------------
    # cashflow_forecasts
    # -------------------------------------------------------------------------
    op.create_table(
        "cashflow_forecasts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("forecast_date", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("horizon_days", sa.Integer(), nullable=True, index=True),
        sa.Column("projected_revenue", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("projected_expenses", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("projected_net", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("confidence_low", sa.Float(), nullable=True),
        sa.Column("confidence_high", sa.Float(), nullable=True),
        sa.Column("assumptions", sa.JSON(), nullable=True),
        sa.Column("risk_factors", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_cashflow_forecasts_tenant_id", "cashflow_forecasts", ["tenant_id"])
    op.create_index("ix_cashflow_forecasts_forecast_date", "cashflow_forecasts", ["forecast_date"])
    op.create_index("ix_cashflow_forecasts_horizon_days", "cashflow_forecasts", ["horizon_days"])

    # -------------------------------------------------------------------------
    # improvement_recommendations
    # -------------------------------------------------------------------------
    op.create_table(
        "improvement_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("recommendation_type", sa.String(80), nullable=True, index=True),
        sa.Column("source_type", sa.String(80), nullable=True),
        sa.Column("source_id", sa.String(120), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), server_default="medium", nullable=False),
        sa.Column(
            "implementation_status",
            sa.String(30),
            server_default="pending",
            nullable=False,
            index=True,
        ),
        sa.Column("estimated_impact", sa.String(200), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", sa.String(100), nullable=True),
        sa.Column("outcome_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_improvement_recommendations_tenant_id",
        "improvement_recommendations",
        ["tenant_id"],
    )
    op.create_index(
        "ix_improvement_recommendations_recommendation_type",
        "improvement_recommendations",
        ["recommendation_type"],
    )
    op.create_index(
        "ix_improvement_recommendations_implementation_status",
        "improvement_recommendations",
        ["implementation_status"],
    )

    # -------------------------------------------------------------------------
    # delivery_lessons
    # -------------------------------------------------------------------------
    op.create_table(
        "delivery_lessons",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("project_type", sa.String(120), nullable=True, index=True),
        sa.Column("client_industry", sa.String(120), nullable=True),
        sa.Column("lesson_category", sa.String(80), nullable=True, index=True),
        sa.Column("lesson_title", sa.String(300), nullable=False),
        sa.Column("lesson_body", sa.Text(), nullable=False),
        sa.Column("what_worked", sa.Text(), nullable=True),
        sa.Column("what_failed", sa.Text(), nullable=True),
        sa.Column("do_next_time", sa.Text(), nullable=True),
        sa.Column("estimated_effort_days", sa.Float(), nullable=True),
        sa.Column("actual_effort_days", sa.Float(), nullable=True),
        sa.Column("effort_accuracy_pct", sa.Float(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_delivery_lessons_tenant_id", "delivery_lessons", ["tenant_id"])
    op.create_index("ix_delivery_lessons_project_type", "delivery_lessons", ["project_type"])
    op.create_index("ix_delivery_lessons_lesson_category", "delivery_lessons", ["lesson_category"])

    # -------------------------------------------------------------------------
    # dependency_scores
    # -------------------------------------------------------------------------
    op.create_table(
        "dependency_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("overall_dependency_score", sa.Float(), nullable=False),
        sa.Column("approval_dependency", sa.Float(), nullable=True),
        sa.Column("revenue_dependency", sa.Float(), nullable=True),
        sa.Column("client_dependency", sa.Float(), nullable=True),
        sa.Column("decision_dependency", sa.Float(), nullable=True),
        sa.Column("operational_dependency", sa.Float(), nullable=True),
        sa.Column("automation_coverage_pct", sa.Float(), nullable=True),
        sa.Column("pending_approval_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("automation_opportunities", sa.JSON(), nullable=True),
        sa.Column("delegation_opportunities", sa.JSON(), nullable=True),
        sa.Column("single_point_alerts", sa.JSON(), nullable=True),
        sa.Column("target_score", sa.Float(), server_default=sa.text("20.0"), nullable=False),
        sa.Column("trend", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_dependency_scores_tenant_id", "dependency_scores", ["tenant_id"])
    op.create_index("ix_dependency_scores_snapshot_date", "dependency_scores", ["snapshot_date"])

    # -------------------------------------------------------------------------
    # moat_metrics
    # -------------------------------------------------------------------------
    op.create_table(
        "moat_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("moat_score", sa.Float(), nullable=True),
        sa.Column("proprietary_data_score", sa.Float(), nullable=True),
        sa.Column("case_study_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("delivery_intelligence_score", sa.Float(), nullable=True),
        sa.Column("relationship_graph_score", sa.Float(), nullable=True),
        sa.Column("institutional_wisdom_score", sa.Float(), nullable=True),
        sa.Column("automation_advantage_score", sa.Float(), nullable=True),
        sa.Column("operational_speed_score", sa.Float(), nullable=True),
        sa.Column("competitive_threat_score", sa.Float(), nullable=True),
        sa.Column("defensibility_report", sa.Text(), nullable=True),
        sa.Column("threats_identified", sa.JSON(), nullable=True),
        sa.Column("strengths_identified", sa.JSON(), nullable=True),
        sa.Column("strategic_actions", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_moat_metrics_tenant_id", "moat_metrics", ["tenant_id"])
    op.create_index("ix_moat_metrics_snapshot_date", "moat_metrics", ["snapshot_date"])


def downgrade() -> None:
    # Drop in reverse creation order
    op.drop_index("ix_moat_metrics_snapshot_date", table_name="moat_metrics")
    op.drop_index("ix_moat_metrics_tenant_id", table_name="moat_metrics")
    op.drop_table("moat_metrics")

    op.drop_index("ix_dependency_scores_snapshot_date", table_name="dependency_scores")
    op.drop_index("ix_dependency_scores_tenant_id", table_name="dependency_scores")
    op.drop_table("dependency_scores")

    op.drop_index("ix_delivery_lessons_lesson_category", table_name="delivery_lessons")
    op.drop_index("ix_delivery_lessons_project_type", table_name="delivery_lessons")
    op.drop_index("ix_delivery_lessons_tenant_id", table_name="delivery_lessons")
    op.drop_table("delivery_lessons")

    op.drop_index(
        "ix_improvement_recommendations_implementation_status",
        table_name="improvement_recommendations",
    )
    op.drop_index(
        "ix_improvement_recommendations_recommendation_type",
        table_name="improvement_recommendations",
    )
    op.drop_index(
        "ix_improvement_recommendations_tenant_id",
        table_name="improvement_recommendations",
    )
    op.drop_table("improvement_recommendations")

    op.drop_index("ix_cashflow_forecasts_horizon_days", table_name="cashflow_forecasts")
    op.drop_index("ix_cashflow_forecasts_forecast_date", table_name="cashflow_forecasts")
    op.drop_index("ix_cashflow_forecasts_tenant_id", table_name="cashflow_forecasts")
    op.drop_table("cashflow_forecasts")

    op.drop_index("ix_financial_health_snapshot_date", table_name="financial_health")
    op.drop_index("ix_financial_health_tenant_id", table_name="financial_health")
    op.drop_table("financial_health")

    op.drop_index("ix_resilience_events_detected_at", table_name="resilience_events")
    op.drop_index("ix_resilience_events_status", table_name="resilience_events")
    op.drop_index("ix_resilience_events_severity", table_name="resilience_events")
    op.drop_index("ix_resilience_events_incident_type", table_name="resilience_events")
    op.drop_index("ix_resilience_events_tenant_id", table_name="resilience_events")
    op.drop_table("resilience_events")

    op.drop_index("ix_reality_checks_check_type", table_name="reality_checks")
    op.drop_index("ix_reality_checks_tenant_id", table_name="reality_checks")
    op.drop_table("reality_checks")

    op.drop_index("ix_prediction_accuracy_period_date", table_name="prediction_accuracy")
    op.drop_index("ix_prediction_accuracy_prediction_type", table_name="prediction_accuracy")
    op.drop_index("ix_prediction_accuracy_tenant_id", table_name="prediction_accuracy")
    op.drop_table("prediction_accuracy")

    op.drop_index("ix_truth_events_outcome_recorded", table_name="truth_events")
    op.drop_index("ix_truth_events_prediction_type", table_name="truth_events")
    op.drop_index("ix_truth_events_tenant_id", table_name="truth_events")
    op.drop_table("truth_events")
