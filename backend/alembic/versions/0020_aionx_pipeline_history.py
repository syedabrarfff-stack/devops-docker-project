"""AIONX Batch 1 pipeline transition history.

Revision ID: 0020_aionx_pipeline_history
Revises: 0019_aionx_batch1_pipeline
Create Date: 2026-06-05
"""
from __future__ import annotations

from alembic import op

revision = "0020_aionx_pipeline_history"
down_revision = "0019_aionx_batch1_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS client_pipeline_stage_logs (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            client_id UUID NOT NULL,
            pipeline_state_id UUID NOT NULL,
            from_stage SMALLINT NOT NULL,
            to_stage SMALLINT NOT NULL,
            reason TEXT,
            actor TEXT NOT NULL DEFAULT 'JARVIS',
            events_fired JSONB NOT NULL DEFAULT '[]'::jsonb,
            validation_result JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_stage_logs_tenant ON client_pipeline_stage_logs(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_stage_logs_tenant_created ON client_pipeline_stage_logs(tenant_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_stage_logs_client_created ON client_pipeline_stage_logs(client_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_pipeline_stage_logs_pipeline ON client_pipeline_stage_logs(pipeline_state_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS client_pipeline_stage_logs")
