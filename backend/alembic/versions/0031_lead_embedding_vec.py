"""Add embedding_vec column to leads for semantic search.

Revision ID: 0031_lead_embedding_vec
Revises: 0030_truth_validation_resilience
Create Date: 2026-06-26

Notes:
  - Stores embeddings as JSON array of floats (OpenAI text-embedding-3-small, 1536-dim)
  - Cosine similarity computed in Python until pgvector extension is enabled in PostgreSQL
  - To migrate to pgvector later: ALTER COLUMN embedding_vec TYPE vector(1536) USING ...
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0031_lead_embedding_vec"
down_revision = "0030_truth_validation_resilience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("embedding_vec", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "embedding_vec")
