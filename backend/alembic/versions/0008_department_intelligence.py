"""Add 6-Layer Autonomous Intelligence System tables.

Revision ID: 0008_department_intelligence
Revises: 0007_memory_tiers
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_department_intelligence"
down_revision = "0007_memory_tiers"
branch_labels = None
depends_on = None

TABLES = (
    "department_intelligence_officers",
    "department_milestones",
    "technology_discoveries",
    "client_call_intelligence",
    "strategy_reports",
)


def upgrade() -> None:
    # Layer 1 — Department Intelligence Officers
    op.create_table(
        "department_intelligence_officers",
        sa.Column("department_code", sa.String(50), nullable=False),
        sa.Column("department_name", sa.String(100), nullable=False),
        sa.Column("division", sa.String(100), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("agent_persona", sa.String(100), nullable=False),
        sa.Column("agent_email", sa.String(150), nullable=False),
        sa.Column("monitored_systems", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("kpi_targets", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("escalation_rules", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("milestones_submitted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("improvements_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("improvements_implemented", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("performance_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("last_report_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_report_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_code", name="uq_dio_department_code"),
    )
    op.create_index("ix_dio_tenant_id", "department_intelligence_officers", ["tenant_id"])
    op.create_index("ix_dio_department_code", "department_intelligence_officers", ["department_code"])
    op.create_index("ix_dio_is_active", "department_intelligence_officers", ["is_active"])

    # Layer 2 — Department Milestones (Council Intelligence Loop)
    op.create_table(
        "department_milestones",
        sa.Column("dio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("milestone_type", sa.String(50), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("evidence_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("impact_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("milestone_pdf_url", sa.String(500), nullable=True),
        sa.Column("improvement_pdf_url", sa.String(500), nullable=True),
        sa.Column("council_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("council_score", sa.Float(), nullable=True),
        sa.Column("council_verdict", sa.Text(), nullable=True),
        sa.Column("council_recommendations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(30), nullable=False, server_default="achieved"),
        sa.Column("implementation_notes", sa.Text(), nullable=True),
        sa.Column("implemented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dio_id"], ["department_intelligence_officers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_milestones_tenant_id", "department_milestones", ["tenant_id"])
    op.create_index("ix_milestones_department_code", "department_milestones", ["department_code"])
    op.create_index("ix_milestones_status", "department_milestones", ["status"])
    op.create_index("ix_milestones_dio_id", "department_milestones", ["dio_id"])

    # Layer 4 — Technology Discoveries (24/7 Evolution Engine)
    op.create_table(
        "technology_discoveries",
        sa.Column("technology_name", sa.String(200), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("integration_feasibility", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("estimated_impact", sa.Text(), nullable=True),
        sa.Column("adoption_guide", sa.Text(), nullable=True),
        sa.Column("council_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("council_strategy", sa.Text(), nullable=True),
        sa.Column("implementation_roadmap", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("council_pdf_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="discovered"),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tech_discoveries_tenant_id", "technology_discoveries", ["tenant_id"])
    op.create_index("ix_tech_discoveries_status", "technology_discoveries", ["status"])
    op.create_index("ix_tech_discoveries_priority", "technology_discoveries", ["priority"])
    op.create_index("ix_tech_discoveries_source", "technology_discoveries", ["source"])
    op.create_index("ix_tech_discoveries_relevance", "technology_discoveries", ["relevance_score"])

    # Layer 5 — Client Call Intelligence (ElevenLabs)
    op.create_table(
        "client_call_intelligence",
        sa.Column("dio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_code", sa.String(50), nullable=False),
        sa.Column("client_name", sa.String(200), nullable=False),
        sa.Column("client_company", sa.String(200), nullable=False),
        sa.Column("client_email", sa.String(200), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("call_topic", sa.String(300), nullable=False),
        sa.Column("call_objective", sa.Text(), nullable=True),
        sa.Column("briefing_pdf_url", sa.String(500), nullable=True),
        sa.Column("briefing_content", sa.Text(), nullable=True),
        sa.Column("what_to_say", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("what_not_to_say", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("objection_handlers", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("context_summary", sa.Text(), nullable=True),
        sa.Column("council_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("council_refinements", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("council_approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("refined_briefing_pdf_url", sa.String(500), nullable=True),
        sa.Column("voice_agent_id", sa.String(100), nullable=True),
        sa.Column("voice_personality", sa.String(200), nullable=True),
        sa.Column("elevenlabs_voice_id", sa.String(100), nullable=True),
        sa.Column("call_script", sa.Text(), nullable=True),
        sa.Column("humanization_notes", sa.Text(), nullable=True),
        sa.Column("call_recording_url", sa.String(500), nullable=True),
        sa.Column("call_transcript", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(50), nullable=True),
        sa.Column("post_call_debrief", sa.Text(), nullable=True),
        sa.Column("council_debrief_pdf_url", sa.String(500), nullable=True),
        sa.Column("improvements_for_next", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dio_id"], ["department_intelligence_officers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_call_intel_tenant_id", "client_call_intelligence", ["tenant_id"])
    op.create_index("ix_call_intel_status", "client_call_intelligence", ["status"])
    op.create_index("ix_call_intel_scheduled_at", "client_call_intelligence", ["scheduled_at"])
    op.create_index("ix_call_intel_dio_id", "client_call_intelligence", ["dio_id"])

    # Layer 6 — Strategy Reports (Strategy Oversight Team)
    op.create_table(
        "strategy_reports",
        sa.Column("report_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False, server_default="daily"),
        sa.Column("operations_summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("kpi_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("alerts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("achievements", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("blockers", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("mrr", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("pipeline_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("leads_this_week", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("demos_scheduled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proposals_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outreach_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reply_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("council_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scaling_strategy", sa.Text(), nullable=True),
        sa.Column("council_directives", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("strategy_pdf_url", sa.String(500), nullable=True),
        sa.Column("cascaded_to_departments", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("cascade_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategy_reports_tenant_id", "strategy_reports", ["tenant_id"])
    op.create_index("ix_strategy_reports_report_date", "strategy_reports", ["report_date"])
    op.create_index("ix_strategy_reports_report_type", "strategy_reports", ["report_type"])

    # Row-Level Security on all 5 tables
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

    op.drop_index("ix_call_intel_dio_id", table_name="client_call_intelligence")
    op.drop_index("ix_call_intel_scheduled_at", table_name="client_call_intelligence")
    op.drop_index("ix_call_intel_status", table_name="client_call_intelligence")
    op.drop_index("ix_call_intel_tenant_id", table_name="client_call_intelligence")
    op.drop_table("client_call_intelligence")

    op.drop_index("ix_tech_discoveries_relevance", table_name="technology_discoveries")
    op.drop_index("ix_tech_discoveries_source", table_name="technology_discoveries")
    op.drop_index("ix_tech_discoveries_priority", table_name="technology_discoveries")
    op.drop_index("ix_tech_discoveries_status", table_name="technology_discoveries")
    op.drop_index("ix_tech_discoveries_tenant_id", table_name="technology_discoveries")
    op.drop_table("technology_discoveries")

    op.drop_index("ix_strategy_reports_report_type", table_name="strategy_reports")
    op.drop_index("ix_strategy_reports_report_date", table_name="strategy_reports")
    op.drop_index("ix_strategy_reports_tenant_id", table_name="strategy_reports")
    op.drop_table("strategy_reports")

    op.drop_index("ix_milestones_dio_id", table_name="department_milestones")
    op.drop_index("ix_milestones_status", table_name="department_milestones")
    op.drop_index("ix_milestones_department_code", table_name="department_milestones")
    op.drop_index("ix_milestones_tenant_id", table_name="department_milestones")
    op.drop_table("department_milestones")

    op.drop_index("ix_dio_is_active", table_name="department_intelligence_officers")
    op.drop_index("ix_dio_department_code", table_name="department_intelligence_officers")
    op.drop_index("ix_dio_tenant_id", table_name="department_intelligence_officers")
    op.drop_table("department_intelligence_officers")
