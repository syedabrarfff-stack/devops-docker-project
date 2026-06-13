"""Add whatsapp_number and linkedin_url columns to leads table.

Revision ID: 0026_leads_whatsapp_linkedin
Revises: 0025_aionx_comm_transport
Create Date: 2026-06-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026_leads_whatsapp_linkedin"
down_revision = "0025_aionx_comm_transport"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'leads' AND column_name = 'whatsapp_number'
            ) THEN
                ALTER TABLE leads ADD COLUMN whatsapp_number VARCHAR(30);
                CREATE INDEX IF NOT EXISTS ix_leads_whatsapp_number ON leads (whatsapp_number);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'leads' AND column_name = 'linkedin_url'
            ) THEN
                ALTER TABLE leads ADD COLUMN linkedin_url VARCHAR(500);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'leads' AND column_name = 'whatsapp_number'
            ) THEN
                DROP INDEX IF EXISTS ix_leads_whatsapp_number;
                ALTER TABLE leads DROP COLUMN whatsapp_number;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'leads' AND column_name = 'linkedin_url'
            ) THEN
                ALTER TABLE leads DROP COLUMN linkedin_url;
            END IF;
        END $$;
        """
    )
