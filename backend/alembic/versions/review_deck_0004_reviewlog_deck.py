"""Denormalize deck_folder onto review_log for per-deck daily counts.

Revision ID: review_deck_0004
Revises: card_integrity_0003
Create Date: 2026-07-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "review_deck_0004"
down_revision = "card_integrity_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_log", sa.Column("deck_folder", sa.String, nullable=True))
    op.create_index("idx_review_log_deck_time", "review_log", ["deck_folder", "review_time"])


def downgrade() -> None:
    op.drop_index("idx_review_log_deck_time", table_name="review_log")
    with op.batch_alter_table("review_log") as batch:
        batch.drop_column("deck_folder")
