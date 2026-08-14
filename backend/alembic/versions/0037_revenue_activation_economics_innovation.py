"""Create missing tables: speed_to_lead_events, market_pulse_items,
outreach_learnings, ai_cost_ledger, infrastructure_cost_config, innovation_queue.

Revision ID: 0037_revenue_activation_economics_innovation
Revises: 0036_conversation_tenant_session_id_index
Create Date: 2026-06-29

Notes:
  - These tables are defined in models but had no corresponding migration.
  - All use CREATE TABLE IF NOT EXISTS so the migration is safe to run even if
    a table was created manually in an older environment.
  - JarvisBase provides id (UUID pk), tenant_id (UUID), created_at, updated_at.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0037_revenue_activation_economics_innovation"
down_revision = "0036_conversation_tenant_session_id_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── speed_to_lead_events ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS speed_to_lead_events (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL,
            lead_id         UUID REFERENCES leads(id) ON DELETE SET NULL,
            source_type     VARCHAR(80)  NOT NULL,
            source_id       VARCHAR(160) NOT NULL,
            trigger_type    VARCHAR(40)  NOT NULL,
            captain_online  BOOLEAN      NOT NULL DEFAULT FALSE,
            action_taken    VARCHAR(80)  NOT NULL,
            draft_subject   VARCHAR(500),
            draft_body      TEXT,
            scheduled_send_at TIMESTAMPTZ,
            payload         JSONB        NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_speed_to_lead_source
                UNIQUE (tenant_id, source_type, source_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_speed_to_lead_events_tenant_id ON speed_to_lead_events (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_speed_to_lead_events_lead_id ON speed_to_lead_events (lead_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_speed_to_lead_events_source_type ON speed_to_lead_events (source_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_speed_to_lead_events_source_id ON speed_to_lead_events (source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_speed_to_lead_events_trigger_type ON speed_to_lead_events (trigger_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_speed_to_lead_events_action_taken ON speed_to_lead_events (action_taken)")

    # ── market_pulse_items ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS market_pulse_items (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL,
            source          VARCHAR(120) NOT NULL,
            title           VARCHAR(500) NOT NULL,
            url             TEXT         NOT NULL,
            summary         TEXT,
            relevance_score FLOAT        NOT NULL DEFAULT 0.0,
            relevance_reason TEXT,
            published_at    TIMESTAMPTZ,
            content_hash    VARCHAR(64)  NOT NULL,
            payload         JSONB        NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_market_pulse_content_hash
                UNIQUE (tenant_id, content_hash)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_market_pulse_items_tenant_id ON market_pulse_items (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_market_pulse_items_source ON market_pulse_items (source)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_market_pulse_items_relevance_score ON market_pulse_items (relevance_score)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_market_pulse_items_content_hash ON market_pulse_items (content_hash)")

    # ── outreach_learnings ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS outreach_learnings (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID         NOT NULL,
            category    VARCHAR(120) NOT NULL,
            title       VARCHAR(300) NOT NULL,
            learning    TEXT         NOT NULL,
            source_type VARCHAR(100) NOT NULL,
            source_id   VARCHAR(160),
            score       FLOAT        NOT NULL DEFAULT 0.0,
            evidence_json   JSONB    NOT NULL DEFAULT '{}',
            applies_to_json JSONB    NOT NULL DEFAULT '{}',
            created_by  VARCHAR(120) NOT NULL DEFAULT 'TeachingEngine',
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_outreach_learnings_tenant_id ON outreach_learnings (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_outreach_learnings_category ON outreach_learnings (category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_outreach_learnings_source_type ON outreach_learnings (source_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_outreach_learnings_source_id ON outreach_learnings (source_id)")

    # ── ai_cost_ledger ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_cost_ledger (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID         NOT NULL,
            provider        VARCHAR(60)  NOT NULL,
            model           VARCHAR(160) NOT NULL,
            tokens_in       INTEGER      NOT NULL DEFAULT 0,
            tokens_out      INTEGER      NOT NULL DEFAULT 0,
            tokens_total    INTEGER      NOT NULL DEFAULT 0,
            cost_usd        FLOAT        NOT NULL DEFAULT 0.0,
            department      VARCHAR(120) NOT NULL DEFAULT 'general',
            task_type       VARCHAR(80)  NOT NULL DEFAULT 'general',
            latency_ms      INTEGER      NOT NULL DEFAULT 0,
            success         BOOLEAN      NOT NULL DEFAULT TRUE,
            error_message   VARCHAR(500),
            metadata_json   JSONB        NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_cost_ledger_tenant_id ON ai_cost_ledger (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_cost_ledger_provider ON ai_cost_ledger (provider)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_cost_ledger_model ON ai_cost_ledger (model)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_cost_ledger_cost_usd ON ai_cost_ledger (cost_usd)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_cost_ledger_department ON ai_cost_ledger (department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_cost_ledger_task_type ON ai_cost_ledger (task_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_cost_ledger_success ON ai_cost_ledger (success)")

    # ── infrastructure_cost_config ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS infrastructure_cost_config (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID         NOT NULL,
            name            VARCHAR(120) NOT NULL,
            ec2_monthly     FLOAT        NOT NULL DEFAULT 45.0,
            postgres_monthly FLOAT       NOT NULL DEFAULT 0.0,
            redis_monthly   FLOAT        NOT NULL DEFAULT 0.0,
            total_monthly   FLOAT        NOT NULL DEFAULT 45.0,
            effective_from  TIMESTAMPTZ,
            metadata_json   JSONB        NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_infrastructure_cost_config_tenant_id ON infrastructure_cost_config (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_infrastructure_cost_config_name ON infrastructure_cost_config (name)")

    # ── innovation_queue ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS innovation_queue (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID         NOT NULL,
            title               VARCHAR(300) NOT NULL,
            description         TEXT         NOT NULL,
            impact_score        FLOAT        NOT NULL DEFAULT 0.0
                                CONSTRAINT ck_innovation_impact_0_100 CHECK (impact_score >= 0 AND impact_score <= 100),
            feasibility_score   FLOAT        NOT NULL DEFAULT 0.0
                                CONSTRAINT ck_innovation_feasibility_0_100 CHECK (feasibility_score >= 0 AND feasibility_score <= 100),
            priority_score      FLOAT        NOT NULL DEFAULT 0.0
                                CONSTRAINT ck_innovation_priority_0_100 CHECK (priority_score >= 0 AND priority_score <= 100),
            status              VARCHAR(30)  NOT NULL DEFAULT 'proposed',
            proposed_by         VARCHAR(120) NOT NULL DEFAULT 'JARVIS',
            council_approved    BOOLEAN      NOT NULL DEFAULT FALSE,
            review_notes        TEXT,
            created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_innovation_queue_tenant_title UNIQUE (tenant_id, title)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_innovation_queue_tenant_id ON innovation_queue (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_innovation_queue_title ON innovation_queue (title)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_innovation_queue_priority_score ON innovation_queue (priority_score)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_innovation_queue_status ON innovation_queue (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_innovation_queue_council_approved ON innovation_queue (council_approved)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS innovation_queue")
    op.execute("DROP TABLE IF EXISTS infrastructure_cost_config")
    op.execute("DROP TABLE IF EXISTS ai_cost_ledger")
    op.execute("DROP TABLE IF EXISTS outreach_learnings")
    op.execute("DROP TABLE IF EXISTS market_pulse_items")
    op.execute("DROP TABLE IF EXISTS speed_to_lead_events")
