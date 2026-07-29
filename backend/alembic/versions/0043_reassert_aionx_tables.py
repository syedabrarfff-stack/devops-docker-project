"""Re-assert AIONX tables missing on production despite 0021/0024 existing.

Revision ID: 0043_reassert_aionx_tables
Revises: 0042_engineering_org_tables

Production's scheduler logs show UndefinedTableError for aionx_event_spine,
aionx_omni_system_registry, and aionx_system_state_snapshots — tables defined
in migrations 0021 and 0024 — while alembic_version sits at the head. The
version table was evidently stamped past those revisions at some point without
their DDL running, so every `alembic upgrade head` since has been a no-op for
them. Both source migrations are written entirely with IF NOT EXISTS, so the
safe fix is a new head revision that re-invokes their upgrade() bodies:
environments that already have the tables are untouched; production finally
gets them created.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

revision = "0043_reassert_aionx_tables"
down_revision = "0042_engineering_org_tables"
branch_labels = None
depends_on = None

_VERSIONS_DIR = Path(__file__).parent


def _load(module_filename: str):
    spec = importlib.util.spec_from_file_location(
        module_filename.removesuffix(".py"), _VERSIONS_DIR / module_filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upgrade() -> None:
    _load("0021_aionx_operational_persistence.py").upgrade()
    _load("0024_aionx_omni_mission_control.py").upgrade()


def downgrade() -> None:
    # Re-assertion only — dropping here could destroy tables that 0021/0024
    # legitimately own in healthy environments.
    pass
