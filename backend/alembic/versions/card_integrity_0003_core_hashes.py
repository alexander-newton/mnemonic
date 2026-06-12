"""Card integrity: core-hash columns, invalidated_at columns, core_change_log table.

Revision ID: card_integrity_0003
Revises: prompt_opt_0002
Create Date: 2026-06-11
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "card_integrity_0003"
down_revision = "prompt_opt_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduling_state", sa.Column("core_hash", sa.String, nullable=True))
    op.add_column("scheduling_state", sa.Column("core_hash_normalized", sa.String, nullable=True))
    op.add_column("scheduling_state", sa.Column("cloze_signature", sa.String, nullable=True))
    op.add_column(
        "scheduling_state",
        sa.Column("core_changed", sa.Boolean, nullable=False, server_default="0"),
    )
    op.add_column("scheduling_state", sa.Column("core_changed_at", sa.DateTime, nullable=True))

    op.add_column("variation_meta", sa.Column("invalidated_at", sa.DateTime, nullable=True))
    op.add_column("training_example", sa.Column("invalidated_at", sa.DateTime, nullable=True))

    op.create_table(
        "core_change_log",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("card_id", sa.String, nullable=False),
        sa.Column("change_kind", sa.String, nullable=False),
        sa.Column("old_hash", sa.String, nullable=True),
        sa.Column("new_hash", sa.String, nullable=False),
        sa.Column("old_normalized", sa.String, nullable=True),
        sa.Column("new_normalized", sa.String, nullable=False),
        sa.Column("detected_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_core_change_log_card", "core_change_log", ["card_id"])


def downgrade() -> None:
    op.drop_index("idx_core_change_log_card", table_name="core_change_log")
    op.drop_table("core_change_log")
    with op.batch_alter_table("training_example") as batch:
        batch.drop_column("invalidated_at")
    with op.batch_alter_table("variation_meta") as batch:
        batch.drop_column("invalidated_at")
    with op.batch_alter_table("scheduling_state") as batch:
        batch.drop_column("core_changed_at")
        batch.drop_column("core_changed")
        batch.drop_column("cloze_signature")
        batch.drop_column("core_hash_normalized")
        batch.drop_column("core_hash")
