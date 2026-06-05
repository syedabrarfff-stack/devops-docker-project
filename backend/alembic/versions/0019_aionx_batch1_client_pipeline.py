"""AIONX Batch 1 client pipeline state.

Revision ID: 0019_aionx_batch1_pipeline
Revises: 0018_aionx_tenant_columns
Create Date: 2026-06-05
"""
from __future__ import annotations

from alembic import op

revision = "0019_aionx_batch1_pipeline"
down_revision = "0018_aionx_tenant_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS client_pipeline_states (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            client_id UUID NOT NULL UNIQUE,
            current_stage SMALLINT NOT NULL DEFAULT 1,
            stage_name TEXT NOT NULL DEFAULT 'Lead discovery',
            phase TEXT NOT NULL DEFAULT 'Lead discovery & qualification',
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            engagement_score DOUBLE PRECISION NOT NULL DEFAULT 50.0,
            previous_engagement_score DOUBLE PRECISION NOT NULL DEFAULT 50.0,
            stage_entered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            mission_id UUID,
            council_gate_status TEXT NOT NULL DEFAULT 'NOT_REQUIRED',
            validation_status TEXT NOT NULL DEFAULT 'PENDING',
            qa_status TEXT NOT NULL DEFAULT 'PENDING',
            repair_loop_count INTEGER NOT NULL DEFAULT 0,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS client_pipeline_milestones (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            client_id UUID NOT NULL,
            pipeline_state_id UUID NOT NULL,
            stage_number SMALLINT NOT NULL,
            milestone_order SMALLINT NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            department TEXT NOT NULL DEFAULT 'JARVIS',
            status TEXT NOT NULL DEFAULT 'PENDING',
            due_at TIMESTAMPTZ,
            evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_states_tenant ON client_pipeline_states(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_states_tenant_stage ON client_pipeline_states(tenant_id, current_stage)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_states_created ON client_pipeline_states(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_milestones_tenant ON client_pipeline_milestones(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_milestones_tenant_stage ON client_pipeline_milestones(tenant_id, stage_number)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_milestones_client_status ON client_pipeline_milestones(client_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_milestones_created ON client_pipeline_milestones(created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS client_pipeline_milestones")
    op.execute("DROP TABLE IF EXISTS client_pipeline_states")
