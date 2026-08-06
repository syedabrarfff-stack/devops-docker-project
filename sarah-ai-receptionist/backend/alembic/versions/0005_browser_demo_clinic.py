"""is_demo flag + seeded browser-widget demo clinic

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-06

"""
import json

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

DEMO_ORG_ID = "00000000-0000-0000-0000-000000000d01"
DEMO_CLINIC_ID = "00000000-0000-0000-0000-000000000d02"
# Not a real Twilio number -- the browser-call webhook always sets this as
# the synthetic `calledNumber` custom param, so the existing clinic lookup
# in call_handler.py's _load_clinic_config resolves to this row with zero
# special-casing of the real phone-call path.
DEMO_CALLED_NUMBER = "web-demo-widget"


def upgrade() -> None:
    op.add_column("clinics", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO organizations (id, name, slug, plan, is_active, metadata, created_at, updated_at)
            VALUES (:id, 'Aliyar Solutions', 'aliyar-solutions-demo', 'starter', true, '{}', now(), now())
            """
        ),
        {"id": DEMO_ORG_ID},
    )

    demo_config = {
        "name": "Sarah's Demo Practice",
        "hours": "Open every day, 24 hours -- this is a live demo",
        "address": "123 Demo Street",
        "services": ["cleanings", "fillings", "root canals", "crowns", "whitening", "emergency care"],
        "insurance_accepted": ["Delta Dental", "Cigna", "Aetna", "MetLife", "Guardian"],
        "emergency_instructions": "For a real dental emergency, please call your own dentist or 911.",
    }

    conn.execute(
        sa.text(
            """
            INSERT INTO clinics (
                id, organization_id, name, slug, twilio_phone_number, business_hours,
                country, timezone, clinic_config, sarah_name, plan, is_active, is_demo,
                created_at, updated_at
            )
            VALUES (
                :id, :org_id, :name, :slug, :phone, '{}',
                'US', 'America/New_York', CAST(:config AS json), 'Sarah', 'starter', true, true,
                now(), now()
            )
            """
        ),
        {
            "id": DEMO_CLINIC_ID,
            "org_id": DEMO_ORG_ID,
            "name": "Sarah's Demo Practice",
            "slug": "sarah-browser-demo",
            "phone": DEMO_CALLED_NUMBER,
            "config": json.dumps(demo_config),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM clinics WHERE id = :id"), {"id": DEMO_CLINIC_ID})
    conn.execute(sa.text("DELETE FROM organizations WHERE id = :id"), {"id": DEMO_ORG_ID})
    op.drop_column("clinics", "is_demo")
