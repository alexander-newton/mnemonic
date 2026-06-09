"""Phase 1 prompt-optimization: prompt_version table + attribution columns.

Revision ID: prompt_opt_0002
Revises: vault_storage_0001
Create Date: 2026-06-09
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "prompt_opt_0002"
down_revision = "vault_storage_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_version",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("strategy", sa.String, nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False),
        sa.Column("instruction_text", sa.Text, nullable=False),
        sa.Column("demos", sa.Text, nullable=False, server_default="[]"),
        sa.Column("status", sa.String, nullable=False, server_default="challenger"),
        sa.Column("parent_version_id", sa.String, nullable=True),
        sa.Column("compiled_from_n_examples", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_prompt_version_strategy", "prompt_version", ["strategy", "status"])

    op.add_column("training_example", sa.Column("prompt_version_id", sa.String, nullable=True))
    op.add_column("training_example", sa.Column("reward", sa.Float, nullable=True))
    op.add_column("training_example", sa.Column("maturity", sa.Integer, nullable=False, server_default="0"))
    op.add_column("training_example", sa.Column("finalized", sa.Boolean, nullable=False, server_default="0"))
    op.create_index("idx_training_finalized", "training_example", ["finalized"])

    op.add_column("variation_meta", sa.Column("prompt_version_id", sa.String, nullable=True))
    op.add_column("variation_meta", sa.Column("arm", sa.String, nullable=False, server_default="none"))


def downgrade() -> None:
    op.drop_index("idx_training_finalized", table_name="training_example")
    with op.batch_alter_table("variation_meta") as batch:
        batch.drop_column("arm")
        batch.drop_column("prompt_version_id")
    with op.batch_alter_table("training_example") as batch:
        batch.drop_column("finalized")
        batch.drop_column("maturity")
        batch.drop_column("reward")
        batch.drop_column("prompt_version_id")
    op.drop_index("idx_prompt_version_strategy", table_name="prompt_version")
    op.drop_table("prompt_version")
