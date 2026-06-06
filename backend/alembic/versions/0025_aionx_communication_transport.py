"""AIONX communication transport ledger.

Revision ID: 0025_aionx_communication_transport
Revises: 0024_aionx_omni
Create Date: 2026-06-06
"""
from __future__ import annotations

from alembic import op

revision = "0025_aionx_communication_transport"
down_revision = "0024_aionx_omni"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'communication_channel') THEN
                CREATE TYPE communication_channel AS ENUM ('EMAIL', 'WHATSAPP');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'communication_direction') THEN
                CREATE TYPE communication_direction AS ENUM ('INBOUND', 'OUTBOUND');
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS communication_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            channel communication_channel NOT NULL,
            direction communication_direction NOT NULL,
            transport VARCHAR(80) NOT NULL,
            external_message_id VARCHAR(255),
            thread_id VARCHAR(255),
            from_address VARCHAR(300),
            to_address VARCHAR(300),
            contact_name VARCHAR(200),
            lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
            client_id UUID,
            contact_id INTEGER,
            subject VARCHAR(500),
            body_text TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'received',
            hia_persona VARCHAR(120) NOT NULL DEFAULT 'Joseph David',
            decision_id UUID,
            twin_interaction_id UUID,
            processing_summary JSON NOT NULL DEFAULT '{}'::json,
            raw_payload JSON NOT NULL DEFAULT '{}'::json,
            processed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_events_tenant ON communication_events(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_events_channel ON communication_events(channel)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_events_direction ON communication_events(direction)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_events_channel_created ON communication_events(channel, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_events_lead_created ON communication_events(lead_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_events_external ON communication_events(transport, external_message_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_events_processed ON communication_events(processed_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS communication_channel_status (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            channel communication_channel NOT NULL,
            provider VARCHAR(80) NOT NULL,
            identity VARCHAR(300),
            configured BOOLEAN NOT NULL DEFAULT false,
            connected BOOLEAN NOT NULL DEFAULT false,
            status VARCHAR(50) NOT NULL DEFAULT 'unknown',
            blocker_code VARCHAR(120),
            required_action TEXT,
            details JSON NOT NULL DEFAULT '{}'::json,
            last_checked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_communication_channel_provider UNIQUE (tenant_id, channel, provider)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_channel_status_tenant ON communication_channel_status(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_channel_status_channel ON communication_channel_status(channel)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_communication_channel_status_status ON communication_channel_status(status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS communication_channel_status")
    op.execute("DROP TABLE IF EXISTS communication_events")
    op.execute("DROP TYPE IF EXISTS communication_direction")
    op.execute("DROP TYPE IF EXISTS communication_channel")
