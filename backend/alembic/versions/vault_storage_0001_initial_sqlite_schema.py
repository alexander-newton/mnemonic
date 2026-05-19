"""Initial SQLite schema for Mnemonic vault-backed storage.

Revision ID: vault_storage_0001
Revises:
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "vault_storage_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduling_state",
        sa.Column("card_id", sa.String, primary_key=True),
        sa.Column("state", sa.String, nullable=False, server_default="new"),
        sa.Column("stability", sa.Float, nullable=False, server_default="0"),
        sa.Column("difficulty", sa.Float, nullable=False, server_default="5"),
        sa.Column("due", sa.DateTime, nullable=True),
        sa.Column("reps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lapses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("leech_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("leech_notified", sa.Integer, nullable=False, server_default="0"),
        sa.Column("suspended", sa.Integer, nullable=False, server_default="0"),
        sa.Column("parent_card_id", sa.String, nullable=True),
        sa.Column("orphan", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("idx_scheduling_due", "scheduling_state", ["due"])
    op.create_index("idx_scheduling_orphan", "scheduling_state", ["orphan"])
    op.create_index("idx_scheduling_suspended", "scheduling_state", ["suspended"])

    op.create_table(
        "review_log",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("card_id", sa.String, nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("response_time_ms", sa.Integer, nullable=False),
        sa.Column("review_time", sa.DateTime, nullable=False),
        sa.Column("state_before", sa.String, nullable=True),
        sa.Column("state_after", sa.String, nullable=True),
        sa.Column("stability_before", sa.Float, nullable=True),
        sa.Column("stability_after", sa.Float, nullable=True),
        sa.Column("difficulty_before", sa.Float, nullable=True),
        sa.Column("difficulty_after", sa.Float, nullable=True),
        sa.Column("variation_id", sa.String, nullable=True),
        sa.Column("variation_helpful", sa.Integer, nullable=True),
    )
    op.create_index("idx_review_card_time", "review_log", ["card_id", "review_time"])
    op.create_index("idx_review_time", "review_log", ["review_time"])

    op.create_table(
        "variation_meta",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("card_id", sa.String, nullable=False),
        sa.Column("strategy", sa.String, nullable=False),
        sa.Column("model", sa.String, nullable=False),
        sa.Column("generated_at", sa.DateTime, nullable=False),
        sa.Column("shown_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("helpful_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String, nullable=False),
        sa.Column("note_path", sa.String, nullable=False),
    )
    op.create_index("idx_variation_card_hash", "variation_meta", ["card_id", "content_hash"])
    op.create_index("idx_variation_card_time", "variation_meta", ["card_id", "generated_at"])

    op.create_table(
        "llm_usage",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("model", sa.String, nullable=False),
        sa.Column("purpose", sa.String, nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cache_read_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cache_creation_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_millicents", sa.Integer, nullable=False),
        sa.Column("card_id", sa.String, nullable=True),
    )
    op.create_index("idx_usage_timestamp", "llm_usage", ["timestamp"])
    op.create_index("idx_usage_card", "llm_usage", ["card_id"])

    op.create_table(
        "training_example",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("card_id", sa.String, nullable=False),
        sa.Column("variation_id", sa.String, nullable=True),
        sa.Column("base_q", sa.Text, nullable=False),
        sa.Column("base_a", sa.Text, nullable=False),
        sa.Column("variation_q", sa.Text, nullable=False),
        sa.Column("variation_a", sa.Text, nullable=False),
        sa.Column("label", sa.Integer, nullable=False),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("note_context", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_training_label", "training_example", ["label"])


def downgrade() -> None:
    op.drop_table("training_example")
    op.drop_table("llm_usage")
    op.drop_table("variation_meta")
    op.drop_table("review_log")
    op.drop_table("scheduling_state")
