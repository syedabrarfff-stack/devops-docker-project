"""K1-1: Create JARVIS v4 Runtime Kernel tables.

Revision ID: 0038_kernel_tables
Revises: 0037_revenue_activation_economics_innovation
Create Date: 2026-07-03

Tables added:
  system_state     — single source of truth for system state (versioned)
  kernel_events    — async event bus persistence layer
  kernel_task_queue — priority task queue (CRITICAL/HIGH/NORMAL/LOW)
  audit_log        — append-only immutable action record
  health_snapshots — 30-second engine health poll results
  kernel_config    — feature flags + dynamic thresholds (hot-reload)
  decision_records — every autonomous decision before execution
  memory_entries   — 5-layer executive memory (strategic/operational/technical/customer/financial)

All tables use IF NOT EXISTS so the migration is idempotent.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0038_kernel_tables"
down_revision = "0037_revenue_activation_economics_innovation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── system_state ──────────────────────────────────────────────────────────
    # Single source of truth for JARVIS system state. Versioned for OCC.
    op.execute("""
        CREATE TABLE IF NOT EXISTS system_state (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            stage               TEXT NOT NULL,
            status              TEXT NOT NULL,
            autonomous_action_id UUID,
            data                JSONB NOT NULL DEFAULT '{}',
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            version             INT NOT NULL DEFAULT 1
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_system_state_stage ON system_state (stage)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_system_state_status ON system_state (status)")

    # ── kernel_events ─────────────────────────────────────────────────────────
    # Event Bus persistence layer. Named kernel_events to avoid collision with
    # other event tables. Append-only — never updated, only inserted.
    op.execute("""
        CREATE TABLE IF NOT EXISTS kernel_events (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type      TEXT NOT NULL,
            source_engine   TEXT NOT NULL,
            payload         JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_kernel_events_type ON kernel_events (event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kernel_events_source ON kernel_events (source_engine)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kernel_events_created ON kernel_events (created_at)")

    # ── kernel_task_queue ─────────────────────────────────────────────────────
    # Priority task queue. priority: 1=CRITICAL, 2=HIGH, 3=NORMAL, 4=LOW.
    op.execute("""
        CREATE TABLE IF NOT EXISTS kernel_task_queue (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            priority        INT NOT NULL DEFAULT 3,
            status          TEXT NOT NULL DEFAULT 'PENDING',
            retry_count     INT NOT NULL DEFAULT 0,
            max_retries     INT NOT NULL DEFAULT 3,
            payload         JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            started_at      TIMESTAMPTZ,
            completed_at    TIMESTAMPTZ,
            error_message   TEXT
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kernel_task_queue_priority_status "
        "ON kernel_task_queue (priority, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kernel_task_queue_status "
        "ON kernel_task_queue (status)"
    )

    # ── audit_log ─────────────────────────────────────────────────────────────
    # Append-only immutable record of every autonomous action. No UPDATE/DELETE.
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            action_type     TEXT NOT NULL,
            actor           TEXT NOT NULL,
            resource_id     UUID,
            details         JSONB NOT NULL DEFAULT '{}',
            outcome         TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_actor ON audit_log (actor)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_action_type ON audit_log (action_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_created ON audit_log (created_at)")

    # ── health_snapshots ──────────────────────────────────────────────────────
    # 30-second poll results from the Health Aggregator for every engine.
    op.execute("""
        CREATE TABLE IF NOT EXISTS health_snapshots (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            engine_name     TEXT NOT NULL,
            status          TEXT NOT NULL,
            details         JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_health_snapshots_engine "
        "ON health_snapshots (engine_name, created_at DESC)"
    )

    # ── kernel_config ─────────────────────────────────────────────────────────
    # Feature flags and dynamic thresholds. Hot-reload without redeploy.
    # Named kernel_config to avoid collision with any future 'config' table.
    op.execute("""
        CREATE TABLE IF NOT EXISTS kernel_config (
            key             TEXT PRIMARY KEY,
            value           JSONB NOT NULL DEFAULT '{}',
            version         INT NOT NULL DEFAULT 1,
            updated_by      TEXT NOT NULL DEFAULT 'system',
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ── decision_records ──────────────────────────────────────────────────────
    # Every autonomous decision captured before execution. Makes every
    # autonomous action explainable and traceable.
    op.execute("""
        CREATE TABLE IF NOT EXISTS decision_records (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            problem_statement       TEXT NOT NULL,
            evidence                JSONB NOT NULL DEFAULT '{}',
            confidence              NUMERIC(4,3),
            business_impact         TEXT,
            risk_score              NUMERIC(4,3),
            rollback_plan           TEXT,
            success_criteria        TEXT,
            outcome                 TEXT,
            verified_at             TIMESTAMPTZ,
            reported_to_captain     BOOLEAN NOT NULL DEFAULT FALSE,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_decision_records_created "
        "ON decision_records (created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_decision_records_captain "
        "ON decision_records (reported_to_captain)"
    )

    # ── memory_entries ────────────────────────────────────────────────────────
    # 5-layer Executive Memory. Every AI Council member reads the SAME snapshot
    # during reasoning. key is unique per layer.
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory_entries (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            layer           TEXT NOT NULL
                            CHECK (layer IN ('strategic','operational','technical','customer','financial')),
            key             TEXT NOT NULL,
            value           JSONB NOT NULL DEFAULT '{}',
            confidence_score NUMERIC(4,3),
            retention_until DATE,
            owner           TEXT NOT NULL DEFAULT 'jarvis',
            version         INT NOT NULL DEFAULT 1,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uix_memory_entries_layer_key "
        "ON memory_entries (layer, key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memory_entries_layer "
        "ON memory_entries (layer)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_entries")
    op.execute("DROP TABLE IF EXISTS decision_records")
    op.execute("DROP TABLE IF EXISTS kernel_config")
    op.execute("DROP TABLE IF EXISTS health_snapshots")
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("DROP TABLE IF EXISTS kernel_task_queue")
    op.execute("DROP TABLE IF EXISTS kernel_events")
    op.execute("DROP TABLE IF EXISTS system_state")
