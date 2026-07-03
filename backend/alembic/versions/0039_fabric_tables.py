"""F3-1: Create JARVIS v4 AI Fabric tables.

Revision ID: 0039_fabric_tables
Revises: 0038_kernel_tables
Create Date: 2026-07-03

Tables added:
  ai_model_registry    — every provider/model with role, status, latency metrics, costs
  ai_model_metrics     — per-execution-date aggregate metrics per model
  ai_council_assemblies — high-stakes decision sessions with model selection and outcomes

All tables use IF NOT EXISTS so the migration is idempotent.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039_fabric_tables"
down_revision = "0038_kernel_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ai_model_registry ─────────────────────────────────────────────────────
    # Every provider/model with its role, live health status, and cost/performance
    # metrics. Health-checked continuously by the Model Registry.
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_model_registry (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider            TEXT NOT NULL,
            model_name          TEXT NOT NULL,
            role                TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'active',
            latency_p50         NUMERIC(10, 2),
            latency_p95         NUMERIC(10, 2),
            error_rate          NUMERIC(6, 4) DEFAULT 0.0,
            cost_per_mtok       NUMERIC(10, 6) DEFAULT 0.0,
            availability_pct    NUMERIC(5, 2) DEFAULT 100.0,
            last_health_check   TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uix_model_registry_provider_model "
        "ON ai_model_registry (provider, model_name)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_model_registry_role "
        "ON ai_model_registry (role)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_model_registry_status "
        "ON ai_model_registry (status)"
    )

    # ── ai_model_metrics ──────────────────────────────────────────────────────
    # Daily aggregate metrics per model, keyed to ai_model_registry.
    # One row per (model_id, execution_date). Updated by the Routing Optimizer job.
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_model_metrics (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            model_id            UUID NOT NULL REFERENCES ai_model_registry(id) ON DELETE CASCADE,
            execution_date      DATE NOT NULL,
            total_calls         INT NOT NULL DEFAULT 0,
            successful_calls    INT NOT NULL DEFAULT 0,
            failed_calls        INT NOT NULL DEFAULT 0,
            avg_latency_ms      NUMERIC(10, 2),
            total_tokens        BIGINT NOT NULL DEFAULT 0,
            total_cost_usd      NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
            hallucination_rate  NUMERIC(6, 4) DEFAULT 0.0,
            quality_score       NUMERIC(4, 3),
            reliability_score   NUMERIC(4, 3)
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uix_model_metrics_model_date "
        "ON ai_model_metrics (model_id, execution_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_model_metrics_date "
        "ON ai_model_metrics (execution_date)"
    )

    # ── ai_council_assemblies ─────────────────────────────────────────────────
    # Records every Council session for high-stakes decisions.
    # selected_models is a UUID array referencing ai_model_registry rows.
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_council_assemblies (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            decision_id          UUID,
            task_category        TEXT NOT NULL,
            selected_models      UUID[] NOT NULL DEFAULT '{}',
            task_context         JSONB NOT NULL DEFAULT '{}',
            assembled_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            confidence_score     NUMERIC(4, 3),
            final_recommendation JSONB,
            outcome              JSONB,
            outcome_verified     BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_council_assemblies_decision "
        "ON ai_council_assemblies (decision_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_council_assemblies_category "
        "ON ai_council_assemblies (task_category)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_council_assemblies_assembled "
        "ON ai_council_assemblies (assembled_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_council_assemblies")
    op.execute("DROP TABLE IF EXISTS ai_model_metrics")
    op.execute("DROP TABLE IF EXISTS ai_model_registry")
