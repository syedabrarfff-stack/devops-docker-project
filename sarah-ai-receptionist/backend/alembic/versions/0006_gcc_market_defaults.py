"""GCC market defaults: default clinic country/timezone -> SA/Asia-Riyadh

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-07

Aliyar Solutions is pivoting Sarah's primary go-to-market from the US to
Saudi Arabia / GCC. New clinics onboarded without an explicit country or
timezone should default to Saudi Arabia rather than the US -- existing
clinics are untouched, this only changes the column default applied to
future inserts that omit the field.
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

DEMO_CLINIC_ID = "00000000-0000-0000-0000-000000000d02"


def upgrade() -> None:
    op.alter_column("clinics", "country", server_default="SA")
    op.alter_column("clinics", "timezone", server_default="Asia/Riyadh")

    demo_config = {
        "name": "Sarah's Demo Practice — Riyadh",
        "hours": "Open every day, 24 hours -- this is a live demo",
        "address": "King Fahd Road, Riyadh, Saudi Arabia",
        "services": ["cleanings", "fillings", "root canals", "crowns", "whitening", "emergency care"],
        "providers": ["Dr. Aslam", "Dr. Al-Rashid", "Dr. Chen"],
        "insurance_accepted": ["Bupa Arabia", "Tawuniya", "MedGulf", "AXA Gulf"],
        "emergency_instructions": "For a real dental emergency, please call your own dentist or the nearest hospital.",
    }
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE clinics
            SET name = :name, country = 'SA', timezone = 'Asia/Riyadh', clinic_config = CAST(:config AS json)
            WHERE id = :id
            """
        ),
        {"id": DEMO_CLINIC_ID, "name": "Sarah's Demo Practice — Riyadh", "config": json.dumps(demo_config)},
    )


def downgrade() -> None:
    op.alter_column("clinics", "country", server_default="US")
    op.alter_column("clinics", "timezone", server_default="America/New_York")

    demo_config = {
        "name": "Sarah's Demo Practice",
        "hours": "Open every day, 24 hours -- this is a live demo",
        "address": "123 Demo Street",
        "services": ["cleanings", "fillings", "root canals", "crowns", "whitening", "emergency care"],
        "insurance_accepted": ["Delta Dental", "Cigna", "Aetna", "MetLife", "Guardian"],
        "emergency_instructions": "For a real dental emergency, please call your own dentist or 911.",
    }
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE clinics
            SET name = :name, country = 'US', timezone = 'America/New_York', clinic_config = CAST(:config AS json)
            WHERE id = :id
            """
        ),
        {"id": DEMO_CLINIC_ID, "name": "Sarah's Demo Practice", "config": json.dumps(demo_config)},
    )
